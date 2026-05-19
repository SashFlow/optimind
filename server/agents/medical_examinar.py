from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any
from client.storage import gcp_storage_client
from datetime import datetime, timezone
from livekit.agents import RunContext, function_tool, get_job_context

from agents.tools import hangup_call

from .base import ScenarioAgent


logger = logging.getLogger(__name__)


QUESTION_CATALOG: dict[str, dict[str, Any]] = {
    "user_name": {
        "label": "What is your name?",
        "aliases": ("what is your name", "ask for user's name", "ask for user name"),
        "required": "always",
    },
    "id_dob": {
        "label": "Could you confirm your date of birth?",
        "aliases": ("date of birth", "dob", "confirm your date of birth"),
        "required": "always",
    },
    "id_gender": {
        "label": "What is your gender?",
        "aliases": ("what is your gender", "gender"),
        "required": "always",
    },
    "id_height_weight": {
        "label": "What is your Height and Weight?",
        "aliases": ("height and weight", "height", "weight"),
        "required": "always",
    },
    "pmh_current_complaints": {
        "label": "Do you have currently any health complaints or under any treatment or past medication?",
        "aliases": (
            "health complaints",
            "under any treatment",
            "past medication",
        ),
        "required": "always",
        "detail_on_yes": True,
    },
    "pmh_hospitalization_surgery": {
        "label": "Have you been hospitalized or undergone any surgery till date?",
        "aliases": ("hospitalized", "undergone any surgery", "surgery till date"),
        "required": "always",
        "detail_on_yes": True,
        "detail_keywords": ("date", "hospital"),
    },
    "pmh_major_tests": {
        "label": "Have you ever had major tests like blood test, ECG, CT, or MRI?",
        "aliases": ("major tests", "blood test", "ecg", "ct", "mri"),
        "required": "always",
        "detail_on_yes": True,
    },
    "pmh_chronic_conditions": {
        "label": "Any history of diabetes, BP, heart issues, cancer, thyroid, respiratory, kidney, bone or joint, or neurological conditions?",
        "aliases": (
            "history of diabetes",
            "heart issues",
            "cancer",
            "thyroid",
            "respiratory",
            "neurological conditions",
        ),
        "required": "always",
        "detail_on_yes": True,
    },
    "pmh_blood_thyroid_respiratory": {
        "label": "Do you have any history of Blood disorder, Thyroid disorder or Respiratory disorder?",
        "aliases": (
            "blood disorder",
            "thyroid disorder",
            "respiratory disorder",
        ),
        "required": "always",
        "detail_on_yes": True,
    },
    "pmh_brain_psych_hiv_hcv": {
        "label": "Do you have any history of Brain disorder like seizures, paralysis, stroke or any mental/psychiatric illness or tested positive for HIV/HCV?",
        "aliases": (
            "brain disorder",
            "seizures",
            "paralysis",
            "stroke",
            "mental/psychiatric",
            "hiv/hcv",
        ),
        "required": "always",
        "detail_on_yes": True,
    },
    "pmh_recent_symptoms": {
        "label": "In the last 2 months, have you had fever, cough, breathlessness, fatigue, or stomach issues?",
        "aliases": (
            "last 2 months",
            "fever",
            "cough",
            "breathlessness",
            "fatigue",
            "stomach issues",
        ),
        "required": "always",
        "detail_on_yes": True,
    },
    "pmh_tobacco": {
        "label": "Have you consumed Tobacco in any form?",
        "aliases": ("consumed tobacco", "tobacco in any form"),
        "required": "always",
        "detail_on_yes": True,
    },
    "pmh_alcohol": {
        "label": "Have you consumed Alcohol in any form?",
        "aliases": ("consumed alcohol", "alcohol in any form"),
        "required": "always",
        "detail_on_yes": True,
    },
    "pmh_family_history": {
        "label": "Any family history of heart disease, cancer, diabetes, or stroke before age 60?",
        "aliases": (
            "family history",
            "heart disease",
            "stroke before age 60",
        ),
        "required": "always",
        "detail_on_yes": True,
    },
    "pmh_overseas_travel_since_2020": {
        "label": "Have you or your family members travelled overseas post 1st Jan 2020?",
        "aliases": ("travelled overseas post 1st jan 2020", "travelled overseas"),
        "required": "always",
        "detail_on_yes": True,
    },
    "pmh_overseas_travel_next_6_months": {
        "label": "Do you have any plan to travel overseas during the next 6 months?",
        "aliases": ("plan to travel overseas", "next 6 months"),
        "required": "always",
        "detail_on_yes": True,
    },
    "covid_positive_history": {
        "label": "Have you or your family members ever tested positive for the novel coronavirus?",
        "aliases": (
            "tested positive for the novel coronavirus",
            "tested positive for coronavirus",
            "covid positive",
        ),
        "required": "always",
        "detail_on_yes": True,
        "detail_keywords": ("date",),
    },
    "covid_vaccinated": {
        "label": "Have you been vaccinated for COVID-19?",
        "aliases": ("vaccinated for covid", "covid-19 vaccinated", "covid vaccine"),
        "required": "always",
        "detail_on_yes": True,
        "detail_keywords": ("dose 1", "dose 2", "date"),
    },
    "female_gynecological": {
        "label": "Have you suffered from any gynecological problem related to Breast, Uterus, cervix?",
        "aliases": ("gynecological problem", "breast", "uterus", "cervix"),
        "required": "female_only",
        "detail_on_yes": True,
    },
    "female_pregnant": {
        "label": "Are you pregnant?",
        "aliases": ("are you pregnant", "pregnant"),
        "required": "female_only",
        "detail_on_yes": True,
    },
}


class MedicalExaminationAgent(ScenarioAgent):
    def __init__(self, name, gender, language) -> None:
        super().__init__(
            instructions=f"""
            ROLE:
            You are {name}, a {gender} Medical Examination Assistant, You can help complete peoples insurance Application.
            You are based out of India and talk to Indian native people so you must make sure you sound like an Indian Doctor with a thick accent.
            User has selected {language} as their primary language. YOU MUST CONVERSE IN {language}.
            
            RULES:
            - YOU MUST NEVER CALL END_CALL FUNCTION WITHOUT CALLING GOODBYE FUNCTION FIRST. ALWAYS CALL GOODBYE FUNCTION TO SAY FAREWELL MESSAGES TO THE USER AND THEN CALL END_CALL TO HANG UP THE CALL. DO NOT END THE CALL UNLESS THE USER HAS INDICATED THEY HAVE NO MORE QUESTIONS OR NEEDS, SUCH AS BY SAYING "NO THANKS", "THAT'S ALL", "GOODBYE", "THANK YOU", OR SIMILAR PHRASES.
            - YOU MUST REPEAT THE RESPONSE FROM GOODBYE FUNCTION IN YOUR OWN WORDS TO THE USER IN A FRIENDLY MANNER AND THEN CALL END_CALL TO END THE CALL AFTER THAT. DO NOT CALL END_CALL WITHOUT SAYING GOODBYE MESSAGES TO THE USER.
            - You must go through all the questions.
            - Please respond in a friendly, conversational tone but not too zesty.
            - Use everyday simple vocabulary that easy to understand for people of all ages.
            - Paragraphs are only 1-2 sentences long.
            - User can provide or correct information in any order, so be sure to ask all the questions and confirm the answers at the end.
            - Make sure the wordings are less predictable, has high burstiness, and high stylometric.
            - Wait after each question, and give ample time for user to respond to your questions and dont group the questions together.
            - Avoid translating abbreviations unless medically required; preserve global consistency.
            - YOU MUST NOT translate day to day terms like quality, date of birth, audit, gender, height, weight, diabetes, heart issues, family history etc. and use the English terms even when conversing in other languages.
            - Ensure that key medical terms (e.g., BP for Blood Pressure) remain consistent across all supported languages.
            - Provide confirmation after each question and once completed conclude the call after greeting the user.
            - Incase the answer is not clear, ask one brief clarifying question to get the answer. Do not ask more than one clarifying question.
            - You must use grammatically correct native-language gender forms based on your own gender ({gender}).
            - When speaking Hindi or other Indian languages, all verbs, pronouns, honorifics, and sentence endings MUST match the assistant's gender naturally.
            - NEVER mix masculine and feminine forms incorrectly.

            - If gender = female:
            - Use feminine verb forms and feminine self-references.
            - Examples:
                - "मैं पूछूंगी"
                - "मैं आपकी मदद करूंगी"
                - "मैं आई हूँ"
                - "मैं समझ गई"
                - "मैं तैयार हूँ"

            - If gender = male:
            - Use masculine verb forms and masculine self-references.
            - Examples:
                - "मैं पूछूंगा"
                - "मैं आपकी मदद करूंगा"
                - "मैं आया हूँ"
                - "मैं समझ गया"
                - "मैं तैयार हूँ"

            ADDITIONAL INSTRUCTIONS FOR PERSONAL MEDICAL HISTORY CATEGORY:- 
            - If answer is yes for the following questions, 
                - inquire as much details as possible about the origin, duration, treatment and current status of the condition, 
                - if hospitalized or surgery, ask for the date of hospitalization/surgery and the name of the hospital
                - ask mulitple follow up questions to get the details of the condition and make sure to get all the details of the condition
                - do not move to next question until you have all the details of the condition

            ADDITIONAL TOOL INFORMATION AND GUIDELINES:
            - Data capture and reporting:
            - After user responds to each question, call log_response tool immediately.
            - In each log_response tool call, pass: `question_id`, `answer`, and `reason` (if needed).
            - Use stable question IDs for reliable validation. Example IDs:
                - user_name, id_dob, id_gender, id_height_weight,
                - pmh_current_complaints, pmh_hospitalization_surgery, pmh_major_tests,
                - pmh_chronic_conditions, pmh_blood_thyroid_respiratory, pmh_brain_psych_hiv_hcv,
                - pmh_recent_symptoms, pmh_tobacco, pmh_alcohol, pmh_family_history,
                - pmh_overseas_travel_since_2020, pmh_overseas_travel_next_6_months,
                - covid_positive_history, covid_vaccinated, female_gynecological, female_pregnant.
            - Once all mandatory questions are completed, call send_medical_report tool exactly once before ending the call.
            - If send_medical_report returns a validation failure, DO NOT end the call.
            - Instead, ask only the missing or clarifying follow-up questions requested by the tool output, log the new response with log_response, and call send_medical_report again.
            - If any answer is Yes for medical history conditions, include detailed reason covering origin, duration, treatment, and current status.
            - If hospitalization or surgery answer is Yes, reason MUST include surgery/hospitalization date and hospital name.

            - If the user has no more questions or needs, call the `goodbye` tool and then call the end the call.
                       

            CONVERSATION GUIDELINES:

            "Hi, this is Doctor {name}, calling regarding your insurance application."

            Ask for user's name.

            "Thanks, [Name]. This call will be recorded for audit purposes."

            "I'll ask a few quick questions to complete your application. 
            This will take about 3 to 5 minutes. 
            Please answer accurately, as incorrect information may affect your policy."

            ID VERIFICATION CATEGORY:

            1. Could you confirm your date of birth (dd mm yyyy)?
            2. What is your gender? (Male, Female, you must remember this throughout the conversation as it will determine some of the follow up questions you will ask) 
            3. What is your Height and Weight?

            PERSONAL MEDICAL HISTORY CATEGORY: 
    
            1. Do you have currently any health complaints or under any treatment or past medication?
            2. Have you been hospitalized or undergone any surgery till date?
            3. Have you ever had major tests like blood test, ECG, CT, or MRI?
            4. Any history of diabetes, BP, heart issues, cancer, thyroid, respiratory, kidney, bone or joint, or neurological conditions?
            5. Do you have any history of Blood disorder, Thyroid disorder or Respiratory disorder ?
            6. Do you have any history of Brain disorder like seizures, paralysis, stroke or any mental/psychiatric illness or tested positive for HIV/HCV?
            7. In the last 2 months, have you had fever, cough, breathlessness, fatigue, or stomach issues?
            8. Have you consumed Tobacco in any form?
            9. Have you consumed Alcohol in any form?
            10. Any family history of heart disease, cancer, diabetes, or stroke before age 60?            
            11. Have you or our family members travelled overseas post 1st Jan 2020?
            12. Do you have any plan to travel overseas during the next 6 months? 

            
            ADDITIONAL DISEASE CATEGORY:

            1. Have you or your family members ever tested positive for the novel coronavirus? 
                - If yes, provide the date of positive diagnosis?
            2. Have you been vaccinated for COVID-19? 
                - If yes, What are the dates for dose 1 and dose 2?
            
            Ask the following questions only if the user mentions they of the female gender or similar in other languages:

            1. Have you suffered from any gynecological problem related to Breast, Uterus, cervix?
            2. Are you pregnant?

            END
 """
        )

        self._report_sent = False
        self._session_answers: dict[str, dict[str, str]] = {}

    @staticmethod
    def _clean_text(value: str) -> str:
        return " ".join(value.split()).strip()

    @staticmethod
    def _normalize_for_match(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()

    def _infer_question_id(self, question_text: str) -> str:
        normalized_question = self._normalize_for_match(question_text)
        if not normalized_question:
            return ""

        for question_id, meta in QUESTION_CATALOG.items():
            aliases = [meta.get("label", ""), *meta.get("aliases", ())]
            for alias in aliases:
                normalized_alias = self._normalize_for_match(str(alias))
                if not normalized_alias:
                    continue
                if (
                    normalized_alias in normalized_question
                    or normalized_question in normalized_alias
                ):
                    return question_id
        return ""

    @staticmethod
    def _is_yes_answer(answer: str) -> bool:
        normalized = answer.lower().strip()
        alpha_words = set(re.findall(r"[a-z]+", normalized))
        return bool(
            alpha_words
            & {
                "yes",
                "y",
                "yeah",
                "yep",
                "true",
                "affirmative",
                "haan",
                "han",
                "ji",
                "jihaan",
            }
        )

    @staticmethod
    def _count_date_mentions(text: str) -> int:
        numeric_date_patterns = (
            r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
            r"\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b",
        )
        month_name_pattern = (
            r"\b\d{1,2}\s+"
            r"(?:jan|january|feb|february|mar|march|apr|april|may|jun|june|"
            r"jul|july|aug|august|sep|sept|september|oct|october|nov|november|"
            r"dec|december)\s+\d{2,4}\b"
        )

        count = 0
        for pattern in numeric_date_patterns:
            count += len(re.findall(pattern, text.lower()))
        count += len(re.findall(month_name_pattern, text.lower()))
        return count

    @staticmethod
    def _is_female_gender(answer: str) -> bool:
        normalized = answer.lower()
        return any(
            token in normalized
            for token in (
                "female",
                "woman",
                "f",
                "mahila",
                "lady",
            )
        )

    @staticmethod
    def _has_meaningful_reason(reason: str) -> bool:
        normalized_reason = reason.strip().lower()
        if len(normalized_reason) < 12:
            return False
        generic_reasons = {
            "general response",
            "yes",
            "details shared",
            "not sure",
            "n/a",
            "na",
            "unknown",
        }
        return normalized_reason not in generic_reasons

    def _validate_answers(
        self, answers_by_id: dict[str, dict[str, str]]
    ) -> tuple[list[str], list[str]]:
        required_ids = [
            question_id
            for question_id, meta in QUESTION_CATALOG.items()
            if meta.get("required") == "always"
        ]

        gender_answer = answers_by_id.get("id_gender", {}).get("answer", "")
        if self._is_female_gender(gender_answer):
            required_ids.extend(
                [
                    question_id
                    for question_id, meta in QUESTION_CATALOG.items()
                    if meta.get("required") == "female_only"
                ]
            )

        missing_required: list[str] = []
        detail_gaps: list[str] = []

        for question_id in required_ids:
            if question_id not in answers_by_id:
                missing_required.append(question_id)

        for question_id, row in answers_by_id.items():
            meta = QUESTION_CATALOG.get(question_id)
            if not meta:
                continue
            answer_text = row.get("answer", "")
            if not meta.get("detail_on_yes") or not self._is_yes_answer(answer_text):
                continue

            reason_text = row.get("reason", "")
            if not self._has_meaningful_reason(reason_text):
                detail_gaps.append(
                    f"{question_id}: detailed reason is required for Yes answers"
                )
                continue

            reason_lower = reason_text.lower()

            if question_id == "covid_positive_history":
                if self._count_date_mentions(reason_text) < 1:
                    detail_gaps.append(
                        "covid_positive_history: reason must include date of positive diagnosis"
                    )
                continue

            if question_id == "covid_vaccinated":
                dose1_present = any(
                    token in reason_lower
                    for token in ("dose 1", "dose1", "first dose", "1st dose")
                )
                dose2_present = any(
                    token in reason_lower
                    for token in ("dose 2", "dose2", "second dose", "2nd dose")
                )
                if not dose1_present:
                    detail_gaps.append(
                        "covid_vaccinated: reason must include dose 1 details"
                    )
                if not dose2_present:
                    detail_gaps.append(
                        "covid_vaccinated: reason must include dose 2 details"
                    )
                if self._count_date_mentions(reason_text) < 2:
                    detail_gaps.append(
                        "covid_vaccinated: reason must include dates for dose 1 and dose 2"
                    )
                continue

            # for keyword in meta.get("detail_keywords", ()):
            #     if keyword not in reason_lower:
            #         detail_gaps.append(
            #             f"{question_id}: reason must include '{keyword}' details"
            #         )

        return missing_required, detail_gaps

    def _build_follow_up_prompts(
        self, missing_required: list[str], detail_gaps: list[str]
    ) -> list[str]:
        prompts: list[str] = []
        for question_id in missing_required:
            question_meta = QUESTION_CATALOG.get(question_id)
            if question_meta is not None:
                prompts.append(question_meta["label"])

        for gap in detail_gaps:
            if gap.startswith("pmh_hospitalization_surgery:"):
                prompts.append(
                    "Please tell me the hospitalization or surgery date and the hospital name."
                )
            elif gap.startswith("covid_positive_history:"):
                prompts.append(
                    "Please tell me the date of the positive coronavirus diagnosis."
                )
            elif gap.startswith("covid_vaccinated: reason must include dose 1 details"):
                prompts.append(
                    "Please tell me the date for dose 1 of the COVID-19 vaccine."
                )
            elif gap.startswith("covid_vaccinated: reason must include dose 2 details"):
                prompts.append(
                    "Please tell me the date for dose 2 of the COVID-19 vaccine."
                )
            elif gap.startswith("covid_vaccinated: reason must include dates"):
                prompts.append(
                    "Please tell me both dose 1 and dose 2 dates for the COVID-19 vaccine."
                )
            else:
                question_id = gap.split(":", 1)[0]
                question_meta = QUESTION_CATALOG.get(question_id)
                if question_meta is not None:
                    prompts.append(
                        f"Please share more details for: {question_meta['label']}"
                    )

        deduped_prompts: list[str] = []
        for prompt in prompts:
            if prompt not in deduped_prompts:
                deduped_prompts.append(prompt)
        return deduped_prompts

    def _store_session_answer(
        self,
        question_id: str,
        answer: str,
        reason: str,
        room_name: str,
    ) -> None:
        cleaned_question_id = self._clean_text(question_id)
        cleaned_answer = self._clean_text(answer)
        cleaned_reason = self._clean_text(reason) or "General response"

        cleaned_question = ""
        if cleaned_question_id in QUESTION_CATALOG:
            cleaned_question = QUESTION_CATALOG[cleaned_question_id]["label"]

        if not cleaned_question_id or not cleaned_question or not cleaned_answer:
            return

        self._session_answers[cleaned_question_id] = {
            "question": cleaned_question,
            "answer": cleaned_answer,
            "reason": cleaned_reason,
            "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        logger.info(
            "medical_qa_captured room=%s question_id=%s question=%s answer=%s reason=%s",
            room_name,
            cleaned_question_id,
            cleaned_question,
            cleaned_answer,
            cleaned_reason,
        )

    @staticmethod
    def _write_local_report(
        csv_bytes: bytes,
        safe_room_name: str,
        timestamp: str,
    ) -> str:
        reports_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "reports"
        )
        os.makedirs(reports_dir, exist_ok=True)
        local_path = os.path.join(
            reports_dir,
            f"medical_examination_report_{safe_room_name}_{timestamp}.csv",
        )
        with open(local_path, "wb") as report_file:
            report_file.write(csv_bytes)
        return local_path

    def _parse_combined_answers(self, combined_answers: str) -> list[dict[str, str]]:
        """Parse one-shot answers payload into normalized rows."""
        payload = combined_answers.strip()
        if not payload:
            return []

        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            parsed_rows: list[dict[str, str]] = []
            for line in payload.splitlines():
                line = line.strip().lstrip("-").strip()
                if not line:
                    continue
                parts = [
                    part.strip() for part in re.split(r"\s*\|\s*", line, maxsplit=3)
                ]
                if len(parts) >= 2:
                    question_id = ""
                    question = ""
                    answer = ""
                    reason = "General response"
                    if len(parts) == 4:
                        question_id, question, answer, reason = parts
                    elif len(parts) == 3:
                        question, answer, reason = parts
                    elif len(parts) == 2:
                        question, answer = parts

                    question = self._clean_text(question)
                    answer = self._clean_text(answer)
                    reason = self._clean_text(reason)
                    question_id = self._clean_text(
                        question_id
                    ) or self._infer_question_id(question)

                    if not question and question_id in QUESTION_CATALOG:
                        question = QUESTION_CATALOG[question_id]["label"]
                    if not question or not answer:
                        continue

                    parsed_rows.append(
                        {
                            "question_id": question_id
                            or f"unmapped_{self._normalize_for_match(question).replace(' ', '_')[:40]}",
                            "question": question,
                            "answer": answer,
                            "reason": reason or "General response",
                        }
                    )
            if parsed_rows:
                return parsed_rows
            return [
                {
                    "question_id": "combined_responses",
                    "question": "Combined Responses",
                    "answer": "Captured",
                    "reason": self._clean_text(payload),
                }
            ]

        if isinstance(parsed, dict):
            parsed = parsed.get("answers", [parsed])

        if not isinstance(parsed, list):
            return []

        rows: list[dict[str, str]] = []
        for item in parsed:
            if not isinstance(item, dict):
                continue
            question_id = self._clean_text(str(item.get("question_id", "")))
            question = self._clean_text(str(item.get("question", "")))
            answer = self._clean_text(str(item.get("answer", "")))
            reason = self._clean_text(
                str(item.get("reason", ""))) or "General response"

            if not question_id:
                question_id = self._infer_question_id(question)
            if not question and question_id in QUESTION_CATALOG:
                question = QUESTION_CATALOG[question_id]["label"]
            if not question or not answer:
                continue
            rows.append(
                {
                    "question_id": question_id
                    or f"unmapped_{self._normalize_for_match(question).replace(' ', '_')[:40]}",
                    "question": question,
                    "answer": answer,
                    "reason": reason,
                }
            )

        return rows

    @function_tool()
    async def log_response(
        self,
        context: RunContext,
        question_id: str,
        answer: str,
        reason: str = "",
    ) -> str:
        """Log one question response in session state.

        Call this immediately after each user answer.
        """
        del context

        job_ctx = get_job_context()
        room_name = "unknown-room"
        if job_ctx is not None and job_ctx.room is not None:
            room_name = job_ctx.room.name

        self._store_session_answer(
            question_id=question_id,
            answer=answer,
            reason=reason,
            room_name=room_name,
        )

        cleaned_question_id = self._clean_text(question_id)
        if not cleaned_question_id:
            return "Response not logged: question_id is required."
        if cleaned_question_id not in self._session_answers:
            return "Response not logged: provide valid question_id and answer."
        return f"Response logged for question_id '{cleaned_question_id}'."

    @function_tool()
    async def send_medical_report(
        self,
        context: RunContext,
    ) -> str:
        """Generate a report from one combined answer payload and upload it to GCS.

        Call this once all required medical examination questions are complete,
        before using end_call.
        """
        del context

        if self._report_sent:
            return "Medical report has already been sent for this session."

        job_ctx = get_job_context()
        room_name = "unknown-room"
        if job_ctx is not None and job_ctx.room is not None:
            room_name = job_ctx.room.name

        if not self._session_answers:
            return (
                "No logged responses found. Call log_response after each question "
                "before sending the report."
            )

        # missing_required, detail_gaps = self._validate_answers(self._session_answers)
        # if missing_required or detail_gaps:
        #     missing_text = ", ".join(sorted(set(missing_required))) or "none"
        #     detail_text = "; ".join(detail_gaps) or "none"
        #     follow_up_prompts = self._build_follow_up_prompts(
        #         missing_required, detail_gaps
        #     )
        #     follow_up_text = (
        #         " | ".join(follow_up_prompts) or "Please verify the missing answers."
        #     )
        #     return (
        #         "Medical report validation failed. Do not end the call. "
        #         f"Missing required question_ids: {missing_text}. "
        #         f"Detail gaps: {detail_text}. "
        #         f"Ask these follow-up questions next: {follow_up_text}."
        #     )

        import csv
        import io

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        safe_room_name = re.sub(r"[^A-Za-z0-9_-]+", "_", room_name).strip("_")
        safe_room_name = safe_room_name or "unknown-room"

        object_key = f"{room_name}/mer.csv"

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["Question", "Answer", "Reason"])
        for question_id in QUESTION_CATALOG:
            row = self._session_answers.get(question_id)
            if not row:
                continue
            writer.writerow(
                [
                    QUESTION_CATALOG[question_id]["label"],
                    row["answer"],
                    row.get("reason", "General response"),
                ]
            )
        for question_id, row in self._session_answers.items():
            if question_id in QUESTION_CATALOG:
                continue
            writer.writerow(
                [
                    row.get("question", question_id),
                    row["answer"],
                    row.get("reason", "General response"),
                ]
            )
        writer.writerow([])
        writer.writerow(
            ["Generated At (UTC)", datetime.now(timezone.utc).isoformat()])

        csv_bytes = buffer.getvalue().encode("utf-8")
        gcp_bucket = os.getenv("GCP_BUCKET_NAME", "").strip()

        if not gcp_bucket:
            local_path = self._write_local_report(
                csv_bytes=csv_bytes,
                safe_room_name=safe_room_name,
                timestamp=timestamp,
            )
            self._report_sent = True
            return (
                "Medical report generated successfully. GCS upload skipped because "
                f"GCP_BUCKET_NAME is not configured. Saved locally at {local_path}."
            )

        try:
            bucket = gcp_storage_client.bucket(gcp_bucket)
            blob = bucket.blob(object_key)
            blob.upload_from_file(io.BytesIO(csv_bytes),
                                  content_type="text/csv")
        except Exception as exc:
            logger.exception("Failed to upload medical report to GCS: %s", exc)
            local_path = self._write_local_report(
                csv_bytes=csv_bytes,
                safe_room_name=safe_room_name,
                timestamp=timestamp,
            )
            self._report_sent = True
            return (
                "Medical report generated successfully, but GCS upload failed. "
                f"Saved locally at {local_path}."
            )

        self._report_sent = True
        return (
            "Medical report generated and uploaded successfully. "
            f"GCS: gs://{gcp_bucket}/{object_key}."
        )

    @function_tool()
    async def goodbye(
        self,
        context: RunContext,
    ) -> str:
        """
        You should call this function when the user indicates they have no more questions or needs, such as by saying "no thanks", "that's all", "goodbye", "thank you", or similar phrases. When you call this function, you should first generate a friendly goodbye message to the user, such as "Thank you for your time. Have a great day ahead!" and then end the call cleanly.
         - Generate a friendly goodbye message to the user.
         - Do not call this function unless the user has indicated they have no more questions or needs
         - After generating the goodbye message, end the call cleanly.
        """

        async def _end_after_delay():
            await asyncio.sleep(9)
            context.session.shutdown()
            await hangup_call()

        asyncio.ensure_future(_end_after_delay())
        return "Say have a nice day to the user in a friendly manner and end the call."
