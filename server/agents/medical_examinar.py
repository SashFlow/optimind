from __future__ import annotations

import logging
import os
import re
from client.storage import s3_client
from datetime import datetime, timezone
from livekit.agents import RunContext, function_tool, get_job_context

from .base import ScenarioAgent


logger = logging.getLogger(__name__)


class MedicalExaminationAgent(ScenarioAgent):
    def __init__(self, name, gender, language) -> None:
        super().__init__(
            instructions=f"""
            You are {name}, a {gender} Medical Examination Assistant, You can help complete peoples insurance Application.
            You are based out of India and talk to Indian native people so you must make sure you sound like an Indian Doctor with a thick accent.
            User has selected {language} as their primary language. YOU MUST CONVERSE IN {language}.
            
            CRITICAL LANGUAGE AND GRAMMAR RULES:
            - You must use grammatically correct native-language gender forms based on your own gender ({gender}).
            - When speaking Hindi or other Indian languages, all verbs, pronouns, honorifics, and sentence endings MUST match the assistant's gender naturally.
            - NEVER mix masculine and feminine forms incorrectly.

            Rules:
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

            Always maintain natural native fluency.
            Please respond in a friendly, conversational tone but not too zesty.
            Use everyday simple vocabulary that easy to understand for people of all ages.
            Incorporate paragraphs with concise sentences.
            Paragraphs are only 1-2 sentences long.
            User can provide or correct information in any order, so be sure to ask all the questions and confirm the answers at the end.
            Make sure the wordings are less predictable, has high burstiness, and high stylometric.
            Wait after each question, and give ample time for user to respond to your questions and dont group the questions together.
            You must go through all the questions.
            Avoid translating abbreviations unless medically required; preserve global consistency.
            YOU MUST NOT translate day to day terms like quality, date of birth, audit, gender, height, weight, diabetes, heart issues, family history etc. and use the English terms even when conversing in other languages.
            Ensure that key medical terms (e.g., BP for Blood Pressure) remain consistent across all supported languages.
            Provide confirmation after each question and once completed conclude the call after greeting the user.
            Incase the answer is not clear, ask one brief clarifying question to get the answer. Do not ask more than one clarifying question.
            
            Conversation flow:

            "Hi, this is Doctor {name}, calling regarding your insurance application."

            Ask for user's name.

            "Thanks, [Name]. This call will be recorded for audit purposes."

            "I'll ask a few quick questions to complete your application. 
            This will take about 3 to 5 minutes. 
            Please answer accurately, as incorrect information may affect your policy."

            Questions you must ask:

            Category ID verification:

            1. Could you confirm your date of birth?
            2. What is your gender? (Male, Female, you must remember this throughout the conversation as it will determine some of the follow up questions you will ask) 
            3. What is your Height and Weight?

            Category Personal Medical History: 
    
            ADDITIONAL INSTRUCTIONS:- If answer is yes for the following questions, inquire as much details as possible about the origin, duration, treatment,
            and current status of the condition, if hospitalized or surgery, ask for the date of 
            hospitalization/surgery and the name of the hospital, ask mulitple follow up questions to get 
            the details of the condition and make sure to get all the details of the condition, do not move 
            to next question until you have all the details of the condition

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

            Data capture and reporting rules:

            1. After each user answer, call record_medical_answer with:
               - question: The exact question you asked.
               - answer: Yes or No.
               - reason: All the additional details captured for the questions or further clarification.
            2. Once all mandatory questions are completed, call send_medical_report before ending the call.

            Greet the user and then call the end_call function to end the call. 
            
            YOU MUST NEVER CALL THE END_CALL FUNCTION WITHOUT GREETING THE USER "Thank You". ALWAYS MAKE SURE TO END THE CONVERSATION ONCE THE QUESTIONS ARE ANSWERED AND ON A GOOD NOTE WITH A POLITE GREETING.
            """
        )

        self._medical_answers: list[dict[str, str]] = []
        self._report_sent = False

    @staticmethod
    def _clean_text(value: str) -> str:
        return " ".join(value.split()).strip()

    @function_tool()
    async def record_medical_answer(
        self,
        context: RunContext,
        question: str,
        answer: str,
        reason: str = "General response",
    ) -> str:
        """Save one medical-exam answer with reasoning for later reporting.

        Call this immediately after every user answer so the final report is complete.

        Args:
            question: The exact question asked to the user.
            answer: Yes or No.
            reason: All the additional details captured for the questions or further clarification.
        """

        del context

        normalized_question = self._clean_text(question)
        normalized_answer = self._clean_text(answer)
        normalized_reason = self._clean_text(reason) or "General response"

        if not normalized_question or not normalized_answer:
            return "Skipped saving answer because question or answer was empty."

        for row in self._medical_answers:
            if row["question"].casefold() == normalized_question.casefold():
                row["answer"] = normalized_answer
                row["reason"] = normalized_reason
                row["captured_at_utc"] = datetime.now(timezone.utc).isoformat()
                return "Updated previously saved answer."

        self._medical_answers.append(
            {
                "question": normalized_question,
                "answer": normalized_answer,
                "reason": normalized_reason,
                "captured_at_utc": datetime.now(timezone.utc).isoformat(),
            }
        )
        return f"Saved answer. Total captured answers: {len(self._medical_answers)}."

    @function_tool()
    async def send_medical_report(
        self,
        context: RunContext,
        patient_name: str = "Unknown",
    ) -> str:
        """Generate an Excel report of captured answers and upload it to S3.

        Call this once all required medical examination questions are complete,
        before using end_call.

        Args:
            patient_name: Name of the user, if known.
        """
        del context

        if self._report_sent:
            return "Medical report has already been sent for this session."

        if not self._medical_answers:
            return "No captured answers found. Save answers first using record_medical_answer."

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

        s3_key = f"{room_name}/{safe_name}_{safe_room_name}_{timestamp}.csv"

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["Question", "Answer", "Reason"])
        for row in self._medical_answers:
            writer.writerow(
                [row["question"], row["answer"], row.get("reason", "General response")]
            )
        writer.writerow([])
        writer.writerow(["Field", "Value"])
        writer.writerow(["Patient Name", self._clean_text(patient_name) or "Unknown"])
        writer.writerow(["Room", room_name])
        writer.writerow(["Generated At (UTC)", datetime.now(timezone.utc).isoformat()])

        s3_bucket = os.getenv("S3_BUCKET", "").strip()
        csv_bytes = buffer.getvalue().encode("utf-8")
        s3_client.upload_fileobj(
            io.BytesIO(csv_bytes),
            s3_bucket,
            s3_key,
            ExtraArgs={"ContentType": "text/csv"},
        )

        self._report_sent = True
        return (
            "Medical report generated and uploaded successfully. "
            f"S3: s3://{s3_bucket}/{s3_key}."
        )
