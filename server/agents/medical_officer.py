from __future__ import annotations

from typing import Any

from livekit.agents import RunContext, function_tool

from .base import ScenarioAgent
from .common import WidgetPayload, normalize_lookup_key, rows_from_mapping
from .prompts import get_prompts

DEFAULT_PATIENT = "Sarah Johnson"
DEFAULT_SYMPTOM = "migraine"
DEFAULT_VISUAL_CONCERN = "visible rash"

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

SYMPTOM_GUIDANCE = {
    "migraine": {
        "symptom": "Migraine-like headache",
        "urgency": "Routine unless sudden severe worsening, neurological symptoms, or persistent vomiting are present",
        "possible_next_step": "Review triggers, hydration, current medication use, and recent symptom pattern",
        "care_advice": "Use prescribed migraine medication as directed and arrange clinician follow-up if symptoms are recurring",
        "red_flags": "Sudden worst headache, weakness, confusion, fainting, chest pain, or trouble speaking",
    },
    "fever": {
        "symptom": "Fever",
        "urgency": "Moderate; higher if fever is persistent, very high, or paired with breathing issues or dehydration",
        "possible_next_step": "Check duration, measured temperature, associated symptoms, and hydration status",
        "care_advice": "Rest, hydration, and routine clinical review if symptoms continue or worsen",
        "red_flags": "Difficulty breathing, severe weakness, confusion, seizure, or inability to keep fluids down",
    },
    "cough": {
        "symptom": "Cough",
        "urgency": "Routine to moderate depending on duration and breathing difficulty",
        "possible_next_step": "Check onset, fever, mucus, wheezing, and whether breathing feels restricted",
        "care_advice": "Monitor hydration and seek routine review if the cough persists or becomes more severe",
        "red_flags": "Shortness of breath, blue lips, chest pain, coughing blood, or rapid worsening",
    },
}

VISUAL_GUIDANCE = {
    "visible rash": {
        "observation": "Visible rash or skin irritation",
        "safe_language": "Describe location, color change, spread, and whether it looks raised or patchy",
        "recommended_action": "Ask about itchiness, pain, fever, and any recent new medication or exposure",
        "escalation": "Escalate quickly if swelling, breathing issues, widespread blistering, or facial involvement are present",
    },
    "labored breathing": {
        "observation": "Visible breathing difficulty",
        "safe_language": "Acknowledge the visible breathing effort without claiming a diagnosis",
        "recommended_action": "Direct the user to immediate human medical help right away",
        "escalation": "Treat as urgent and advise emergency care",
    },
    "facial swelling": {
        "observation": "Visible facial swelling",
        "safe_language": "State that visible swelling can be concerning and should be assessed by a clinician",
        "recommended_action": "Ask whether the swelling is new and whether breathing or swallowing feels affected",
        "escalation": "Escalate immediately if breathing, swallowing, or rapid worsening is involved",
    },
}


class MedicalOfficerAgent(ScenarioAgent):
    def __init__(self) -> None:
        super().__init__(
            instructions=get_prompts(
                "Medical Officer",
                """
Your primary function is to help users with how-they-feel check-ins, safe diagnostic guidance, patient record lookups, appointment coordination, prescription summaries, and routine clinic questions.
You should sound calm, clear, and reassuring without becoming overly formal.
Do not diagnose emergencies or minimize urgent symptoms; instead, direct the user to immediate human medical care when needed.
Use symptom, patient, appointment, prescription, and visual-guidance tools before giving tool-backed medical workflow details.
""",
                """
## Opening
Always start with:
"Hello! This is Sai, can you hear me okay?"

## Flow
- Help with symptom check-ins, safe diagnostic guidance, patient profiles, appointments, prescription summaries, and routine clinic questions
- Use symptom, patient, appointment, prescription, and visual-guidance tools before giving specific answers
- If the request is unclear, ask one brief clarifying question
- Keep responses short, warm, and practical

## Safety
- If the user describes urgent or emergency symptoms, direct them to immediate human medical care
- Do not diagnose, prescribe new treatment, or downplay emergencies
- If live video is available, you may acknowledge visible observations, but you must not overstate certainty or claim a definitive diagnosis from appearance alone

## Diagnostic Support
- Use the symptom guidance tool for "how are you feeling" and routine diagnostic support questions
- Use the visual guidance tool when the user asks about something visible on camera or when the session clearly includes video context
- Use patient, appointment, and prescription tools for chart-backed clinic details

## Closing
- When the task is complete:
    "You're all set. Take care."
""",
                """
User: "Can you check Sarah Johnson's next appointment?"
Assistant: "Sure, I can help with that."

User: "What prescription is on file for Sarah Johnson?"
Assistant: "I can check the current prescription summary."

User: "I've had a bad migraine since morning"
Assistant: "I can help with some safe next-step guidance."

User: "Can you look at this rash on video?"
Assistant: "I can help with general guidance based on what I can observe, but I won't replace a clinician."

User: "I'm having severe chest pain right now"
Assistant: "Please seek immediate medical care right away."

""",
                """
- Tool mapping:
  - get_symptom_guidance: use for how-they-feel questions, routine symptom triage, and non-emergency diagnostic support
  - get_visual_assessment_guidance: use for visible symptoms, camera-based concerns, or observations from a live video stream
  - get_patient_profile: use for demographics, allergies, and general chart profile information
  - get_appointment_schedule: use for visit timing, clinician, and check-in details
  - get_prescription_summary: use for medication, dosage, refill, and follow-up summary details
                """,
            ),
        )

    @function_tool()
    async def get_patient_profile(
        self, context: RunContext, patient_name: str = DEFAULT_PATIENT
    ) -> dict[str, Any]:
        """Look up patient demographics, allergies, and insurance details.

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
        """Fetch the next appointment details for a patient.

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
        """Retrieve a prescription summary before discussing medication details.

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

    @function_tool()
    async def get_symptom_guidance(
        self, context: RunContext, symptom: str = DEFAULT_SYMPTOM
    ) -> dict[str, Any]:
        """Provide safe, non-diagnostic guidance for a reported symptom.

        Use this when the user describes how they are feeling, asks for help
        understanding a routine symptom, or wants next-step guidance that should stay
        within triage-style support rather than definitive diagnosis.

        Args:
            symptom: Main symptom or concern, such as migraine, fever, or cough.
        """

        guidance = SYMPTOM_GUIDANCE.get(normalize_lookup_key(symptom))
        if guidance is None:
            result = {
                "found": False,
                "requested_symptom": symptom,
                "available_symptoms": list(SYMPTOM_GUIDANCE.keys()),
            }
            await self.push_widget(
                WidgetPayload(
                    id="medical-symptom-guidance",
                    type="triage",
                    title="Symptom guidance unavailable",
                    status="warning",
                    description="That symptom does not have a preset guidance card in the demo clinic data.",
                    data=rows_from_mapping(
                        {
                            "Requested symptom": symptom,
                            "Available symptoms": result["available_symptoms"],
                        }
                    ),
                )
            )
            return result

        await self.push_widget(
            WidgetPayload(
                id="medical-symptom-guidance",
                type="triage",
                title=f"{guidance['symptom']} guidance",
                status="success",
                description="Routine, non-diagnostic symptom support guidance from the demo clinic workflow.",
                data=rows_from_mapping(
                    {
                        "Urgency": guidance["urgency"],
                        "Possible next step": guidance["possible_next_step"],
                        "Care advice": guidance["care_advice"],
                        "Red flags": guidance["red_flags"],
                    }
                ),
            )
        )
        return guidance

    @function_tool()
    async def get_visual_assessment_guidance(
        self, context: RunContext, visual_concern: str = DEFAULT_VISUAL_CONCERN
    ) -> dict[str, Any]:
        """Provide safe guidance for something that may be visible on a live video stream.

        Use this when the user asks whether something seen on camera looks concerning,
        or when a visible symptom should shape the triage response. This tool is for
        observational guidance and escalation language, not diagnosis.

        Args:
            visual_concern: Visible issue such as visible rash, labored breathing, or facial swelling.
        """

        guidance = VISUAL_GUIDANCE.get(normalize_lookup_key(visual_concern))
        if guidance is None:
            result = {
                "found": False,
                "requested_visual_concern": visual_concern,
                "available_visual_concerns": list(VISUAL_GUIDANCE.keys()),
            }
            await self.push_widget(
                WidgetPayload(
                    id="medical-visual-guidance",
                    type="visual-triage",
                    title="Visual guidance unavailable",
                    status="warning",
                    description="That visible concern does not have a preset visual guidance card in the demo data.",
                    data=rows_from_mapping(
                        {
                            "Requested concern": visual_concern,
                            "Available concerns": result["available_visual_concerns"],
                        }
                    ),
                )
            )
            return result

        await self.push_widget(
            WidgetPayload(
                id="medical-visual-guidance",
                type="visual-triage",
                title=f"{guidance['observation']} guidance",
                status="success",
                description="Safe phrasing and escalation guidance for camera-based support.",
                data=rows_from_mapping(
                    {
                        "How to phrase it": guidance["safe_language"],
                        "Recommended action": guidance["recommended_action"],
                        "Escalation": guidance["escalation"],
                    }
                ),
            )
        )
        return guidance
