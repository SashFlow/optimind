from __future__ import annotations

from typing import Any

from livekit.agents import RunContext, function_tool

from .base import ScenarioAgent
from .common import WidgetPayload, normalize_lookup_key, rows_from_mapping
from .prompts import get_prompts

DEFAULT_PATIENT = "Sarah Johnson"

PATIENTS = {
    "sarah johnson": {
        "name": "Sarah Johnson",
        "patient_id": "PT-1042",
        "age": "34",
        "last_visit": "2026-04-08",
        "primary_concern": "Recurring migraines",
        "allergies": "Penicillin",
        "insurance": "Apex Health Plus",
    }
}

APPOINTMENTS = {
    "sarah johnson": {
        "date": "2026-04-21",
        "time": "10:30 AM",
        "clinician": "Dr. Priya Menon",
        "status": "Confirmed",
        "check_in": "10:10 AM",
        "location": "Exam Room 3",
    }
}

PRESCRIPTIONS = {
    "sarah johnson": {
        "medication": "Sumatriptan 50mg",
        "dosage": "1 tablet as needed for migraine onset",
        "refills_remaining": "2",
        "prescribed_by": "Dr. Priya Menon",
        "follow_up": "Review symptoms in 2 weeks",
    }
}


class MedicalOfficerAgent(ScenarioAgent):
    def __init__(self) -> None:
        super().__init__(
            instructions=get_prompts(
                "Medical Officer",
                """
Your primary function is to help users with patient intake details, appointment coordination, prescription summaries, and routine clinic workflow questions.
You should sound calm, clear, and reassuring without becoming overly formal.
Do not diagnose emergencies or minimize urgent symptoms; instead, direct the user to immediate human medical care when needed.
Check patient, appointment, and prescription details before giving specific clinic information.
""",
                """
## Opening
Always start with:
"Hello! This is Sai, can you hear me okay?"

## Flow
- Help with patient profiles, appointments, prescription summaries, and routine clinic questions
- Use patient, appointment, and prescription details before giving specific answers
- If the request is unclear, ask one brief clarifying question
- Keep responses short, warm, and practical

## Safety
- If the user describes urgent or emergency symptoms, direct them to immediate human medical care
- Do not diagnose, prescribe new treatment, or downplay emergencies

## Closing
- When the task is complete:
    "You're all set. Take care."
""",
                """
User: "Can you check Sarah Johnson's next appointment?"
Assistant: "Sure, I can help with that."

User: "What prescription is on file for Sarah Johnson?"
Assistant: "I can check the current prescription summary."

User: "I'm having severe chest pain right now"
Assistant: "Please seek immediate medical care right away."

""",
                "",
            ),
        )

    @function_tool()
    async def get_patient_profile(
        self, context: RunContext, patient_name: str = DEFAULT_PATIENT
    ) -> dict[str, Any]:
        """Look up patient demographics, allergies, and insurance before answering intake or profile questions.

        Args:
            patient_name: Full patient name for the profile lookup.
        """

        patient = PATIENTS.get(normalize_lookup_key(patient_name))
        if patient is None:
            result = {
                "found": False,
                "requested_patient": patient_name,
                "available_patients": [entry["name"] for entry in PATIENTS.values()],
            }
            await self.push_widget(
                WidgetPayload(
                    id="medical-patient-profile",
                    type="patient-profile",
                    title="Patient not found",
                    status="warning",
                    description="No boilerplate patient record matched that name.",
                    data=rows_from_mapping(
                        {
                            "Requested": patient_name,
                            "Available": result["available_patients"],
                        }
                    ),
                )
            )
            return result

        await self.push_widget(
            WidgetPayload(
                id="medical-patient-profile",
                type="patient-profile",
                title=f"{patient['name']} profile",
                status="success",
                description="Latest patient intake snapshot from the demo clinic records.",
                data=rows_from_mapping(
                    {
                        "Patient ID": patient["patient_id"],
                        "Age": patient["age"],
                        "Last visit": patient["last_visit"],
                        "Primary concern": patient["primary_concern"],
                        "Allergies": patient["allergies"],
                        "Insurance": patient["insurance"],
                    }
                ),
            )
        )
        return patient

    @function_tool()
    async def get_appointment_schedule(
        self, context: RunContext, patient_name: str = DEFAULT_PATIENT
    ) -> dict[str, Any]:
        """Fetch the next appointment details for a patient before discussing visit timing or check-in.

        Args:
            patient_name: Full patient name for the appointment lookup.
        """

        appointment = APPOINTMENTS.get(normalize_lookup_key(patient_name))
        if appointment is None:
            result = {
                "found": False,
                "requested_patient": patient_name,
                "message": "No upcoming appointment exists in the demo data.",
            }
            await self.push_widget(
                WidgetPayload(
                    id="medical-appointment",
                    type="schedule",
                    title="No appointment found",
                    status="warning",
                    description="The demo records do not have an upcoming visit for that patient.",
                    data=rows_from_mapping({"Requested": patient_name}),
                )
            )
            return result

        await self.push_widget(
            WidgetPayload(
                id="medical-appointment",
                type="schedule",
                title=f"{patient_name} appointment",
                status="success",
                description="Next scheduled clinic visit.",
                data=rows_from_mapping(
                    {
                        "Date": appointment["date"],
                        "Time": appointment["time"],
                        "Clinician": appointment["clinician"],
                        "Status": appointment["status"],
                        "Check-in": appointment["check_in"],
                        "Location": appointment["location"],
                    }
                ),
            )
        )
        return appointment

    @function_tool()
    async def get_prescription_summary(
        self, context: RunContext, patient_name: str = DEFAULT_PATIENT
    ) -> dict[str, Any]:
        """Retrieve a prescription summary before discussing medication, dosage, or follow-up instructions.

        Args:
            patient_name: Full patient name for the prescription lookup.
        """

        prescription = PRESCRIPTIONS.get(normalize_lookup_key(patient_name))
        if prescription is None:
            result = {
                "found": False,
                "requested_patient": patient_name,
                "message": "No active prescription summary exists in the demo data.",
            }
            await self.push_widget(
                WidgetPayload(
                    id="medical-prescription",
                    type="prescription",
                    title="No prescription found",
                    status="warning",
                    description="The demo records do not show an active prescription for that patient.",
                    data=rows_from_mapping({"Requested": patient_name}),
                )
            )
            return result

        await self.push_widget(
            WidgetPayload(
                id="medical-prescription",
                type="prescription",
                title=f"{patient_name} prescription",
                status="success",
                description="Current medication summary from the demo chart.",
                data=rows_from_mapping(
                    {
                        "Medication": prescription["medication"],
                        "Dosage": prescription["dosage"],
                        "Refills remaining": prescription["refills_remaining"],
                        "Prescribed by": prescription["prescribed_by"],
                        "Follow-up": prescription["follow_up"],
                    }
                ),
            )
        )
        return prescription
