from __future__ import annotations

import json
import logging
import os
import re
from client.storage import gcp_storage_client
from datetime import datetime, timezone
from livekit.agents import RunContext, function_tool, get_job_context

from .base import ScenarioAgent


logger = logging.getLogger(__name__)


class MedicalExaminationAgent(ScenarioAgent):
    def __init__(self, name, gender, language) -> None:
        super().__init__(
            instructions=f"""
            ROLE:
            You are {name}, a {gender} Medical Examination Assistant, You can help complete peoples insurance Application.
            You are based out of India and talk to Indian native people so you must make sure you sound like an Indian Doctor with a thick accent.
            User has selected {language} as their primary language. YOU MUST CONVERSE IN {language}.
            
            RULES:
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

            TOOLS:
            - Data capture and reporting:
            - Do not call any per-question capture tool.
            - Once all mandatory questions are completed, call send_medical_report tool exactly once before ending the call.
            - In the send_medical_report tool call, pass all collected Q/A in `combined_answers` as JSON array.
            - JSON format:
                    [
                        {{"question": "...", "answer": "Yes/No", "reason": "...details..."}},
                        {{"question": "...", "answer": "Yes/No", "reason": "...details..."}}
                    ]

            - Greet the user and then call the end_call tool to end the call. 
            
            - YOU MUST NEVER CALL THE END_CALL TOOL WITHOUT GREETING THE USER "Thank You". ALWAYS MAKE SURE TO END THE CONVERSATION ONCE THE QUESTIONS ARE ANSWERED AND ON A GOOD NOTE WITH A POLITE GREETING.
           

            CONVERSATION GUIDELINES:

            "Hi, this is Doctor {name}, calling regarding your insurance application."

            Ask for user's name.

            "Thanks, [Name]. This call will be recorded for audit purposes."

            "I'll ask a few quick questions to complete your application. 
            This will take about 3 to 5 minutes. 
            Please answer accurately, as incorrect information may affect your policy."

            Category ID verification:

            1. Could you confirm your date of birth?
            2. What is your gender? (Male, Female, you must remember this throughout the conversation as it will determine some of the follow up questions you will ask) 
            3. What is your Height and Weight?

            Category Personal Medical History: 
    
            ADDITIONAL INSTRUCTIONS FOR MEDICAL HISTORY:- 
            - If answer is yes for the following questions, 
                - inquire as much details as possible about the origin, duration, treatment and current status of the condition, 
                - if hospitalized or surgery, ask for the date of hospitalization/surgery and the name of the hospital
                - ask mulitple follow up questions to get the details of the condition and make sure to get all the details of the condition
                - do not move to next question until you have all the details of the condition

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

            
            Category Additional Disease:

            1. Have you or your family members ever tested positive for the novel coronavirus? 
                - If yes, provide the date of positive diagnosis?
            2. Have you been vaccinated for COVID-19? 
                - If yes, What are the dates for dose 1 and dose 2?
            
            Ask the following questions only if the user mentions they of the female gender or similar in other languages:

            1. Have you suffered from any gynecological problem related to Breast, Uterus, cervix?
            2. Are you pregnant?

            Say: "Thank You"
 """
        )

        self._report_sent = False

    @staticmethod
    def _clean_text(value: str) -> str:
        return " ".join(value.split()).strip()

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
                    part.strip() for part in re.split(r"\s*\|\s*", line, maxsplit=2)
                ]
                if len(parts) >= 2:
                    parsed_rows.append(
                        {
                            "question": self._clean_text(parts[0]),
                            "answer": self._clean_text(parts[1]),
                            "reason": self._clean_text(parts[2])
                            if len(parts) == 3
                            else "General response",
                        }
                    )
            if parsed_rows:
                return parsed_rows
            return [
                {
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
            question = self._clean_text(str(item.get("question", "")))
            answer = self._clean_text(str(item.get("answer", "")))
            reason = self._clean_text(str(item.get("reason", ""))) or "General response"
            if not question or not answer:
                continue
            rows.append({"question": question, "answer": answer, "reason": reason})

        return rows

    @function_tool()
    async def send_medical_report(
        self,
        context: RunContext,
        patient_name: str = "Unknown",
        combined_answers: str = "",
    ) -> str:
        """Generate a report from one combined answer payload and upload it to GCS.

        Call this once all required medical examination questions are complete,
        before using end_call.

        Args:
            patient_name: Name of the user, if known.
            combined_answers: Stringified JSON array of answer rows.
        """
        del context

        if self._report_sent:
            return "Medical report has already been sent for this session."

        answers = self._parse_combined_answers(combined_answers)
        if not answers:
            return (
                "No combined answers found. Provide all Q/A in `combined_answers` "
                "as JSON array before sending the report."
            )

        import csv
        import io

        safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", self._clean_text(patient_name))
        safe_name = safe_name.strip("_") or "unknown"
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        job_ctx = get_job_context()
        room_name = "unknown-room"
        if job_ctx is not None and job_ctx.room is not None:
            room_name = job_ctx.room.name
        safe_room_name = re.sub(r"[^A-Za-z0-9_-]+", "_", room_name).strip("_")
        safe_room_name = safe_room_name or "unknown-room"

        object_key = f"{room_name}/{safe_name}_{safe_room_name}_{timestamp}.csv"

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["Question", "Answer", "Reason"])
        for row in answers:
            writer.writerow(
                [row["question"], row["answer"], row.get("reason", "General response")]
            )
        writer.writerow([])
        writer.writerow(["Field", "Value"])
        writer.writerow(["Patient Name", self._clean_text(patient_name) or "Unknown"])
        writer.writerow(["Room", room_name])
        writer.writerow(["Generated At (UTC)", datetime.now(timezone.utc).isoformat()])

        gcp_bucket = os.getenv("GCP_BUCKET_NAME", "").strip()
        if not gcp_bucket:
            return "GCP_BUCKET_NAME is not configured. Unable to upload medical report."

        csv_bytes = buffer.getvalue().encode("utf-8")
        bucket = gcp_storage_client.bucket(gcp_bucket)
        blob = bucket.blob(object_key)
        blob.upload_from_file(io.BytesIO(csv_bytes), content_type="text/csv")

        self._report_sent = True
        return (
            "Medical report generated and uploaded successfully. "
            f"GCS: gs://{gcp_bucket}/{object_key}."
        )
