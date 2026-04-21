from __future__ import annotations

from typing import Any

from livekit.agents import RunContext, function_tool

from .base import ScenarioAgent
from .common import WidgetPayload, normalize_lookup_key, rows_from_mapping
from .prompts import get_prompts

DEFAULT_CONCERN = "headache"
DEFAULT_VISUAL_CONCERN = "skin rash"

GENERIC_INTAKE_QUESTIONS = (
    "When did it start, and is it getting better, worse, or staying the same?",
    "How severe is it right now, and what makes it better or worse?",
    "Are there other symptoms such as fever, vomiting, shortness of breath, or dizziness?",
    "Is there any major medical history, pregnancy, recent injury, or new medication involved?",
)

GENERIC_RED_FLAGS = (
    "trouble breathing",
    "severe chest pain or chest pressure",
    "fainting, new confusion, or seizure",
    "one-sided weakness, trouble speaking, or sudden severe headache",
    "heavy bleeding, severe dehydration, or a rapidly worsening condition",
)

SYMPTOM_GUIDANCE: dict[str, dict[str, Any]] = {
    "chest pain": {
        "label": "Chest pain or pressure",
        "keywords": (
            "chest pain",
            "chest pressure",
            "tight chest",
            "tightness in chest",
            "heart pain",
            "pain in chest",
            "pressure in chest",
        ),
        "care_setting": "Same-day urgent evaluation, or emergency care right away if the pain is severe or paired with breathing trouble, sweating, fainting, or spreading pain.",
        "triage_level": "Urgent to emergency",
        "questions_to_cover": (
            "When did it start, and is it constant or intermittent?",
            "Does it spread to the arm, jaw, back, or stomach?",
            "Is there shortness of breath, sweating, nausea, faintness, or palpitations?",
            "Did it begin after exercise, injury, or eating?",
        ),
        "possible_causes": "Can range from muscle strain or reflux to heart or lung causes, so severity and associated symptoms matter.",
        "recommended_next_step": "Limit exertion and arrange urgent medical review. If severe pressure, radiating pain, or breathing difficulty is present, seek emergency help immediately.",
        "red_flags": (
            "severe crushing or squeezing pain",
            "pain spreading to the arm, jaw, back, or stomach",
            "shortness of breath, sweating, or fainting",
            "new confusion or sudden weakness",
        ),
    },
    "breathing problems": {
        "label": "Breathing difficulty or cough",
        "keywords": (
            "shortness of breath",
            "breathless",
            "difficulty breathing",
            "wheezing",
            "cough",
            "chest congestion",
            "can't breathe",
            "trouble breathing",
        ),
        "care_setting": "Prompt medical review is appropriate, with emergency care for severe breathing difficulty, blue lips, chest pain, or rapidly worsening symptoms.",
        "triage_level": "Moderate to emergency",
        "questions_to_cover": (
            "Is the problem mainly cough, wheezing, chest tightness, or fast breathing?",
            "How long has it been happening, and is there fever or mucus?",
            "Can the person speak full sentences comfortably?",
            "Any asthma, COPD, allergy, smoke exposure, or recent infection history?",
        ),
        "possible_causes": "May relate to infection, asthma, allergy, irritation, or more serious heart or lung issues.",
        "recommended_next_step": "Assess breathing effort and associated symptoms quickly. Escalate urgently if breathing is labored or the person cannot speak normally.",
        "red_flags": (
            "severe shortness of breath",
            "blue lips or face",
            "new chest pain",
            "confusion, drowsiness, or rapid worsening",
        ),
    },
    "fever or infection": {
        "label": "Fever or suspected infection",
        "keywords": (
            "fever",
            "temperature",
            "infection",
            "flu",
            "viral",
            "chills",
            "sore throat",
            "body ache",
        ),
        "care_setting": "Routine to urgent review depending on duration, temperature, and hydration; urgent care is needed sooner for weakness, dehydration, or mental-status changes.",
        "triage_level": "Routine to urgent",
        "questions_to_cover": (
            "What is the highest measured temperature, and for how many days?",
            "Are there localizing symptoms such as cough, sore throat, burning urine, rash, or abdominal pain?",
            "Is the person drinking fluids and urinating normally?",
            "Any pregnancy, immune suppression, or recent surgery?",
        ),
        "possible_causes": "Commonly viral or bacterial infections, but severity depends on the pattern and any vulnerable-risk context.",
        "recommended_next_step": "Track temperature, hydration, and associated symptoms. Arrange clinician review if the fever is persistent, very high, or paired with concerning symptoms.",
        "red_flags": (
            "stiff neck or severe headache",
            "confusion or seizure",
            "trouble breathing",
            "unable to keep fluids down or signs of dehydration",
        ),
    },
    "headache or neurologic symptoms": {
        "label": "Headache or neurologic concern",
        "keywords": (
            "headache",
            "migraine",
            "dizzy",
            "dizziness",
            "vertigo",
            "numbness",
            "weakness",
            "trouble speaking",
            "blurred vision",
        ),
        "care_setting": "Routine review for familiar mild headaches, but urgent or emergency review for sudden severe headache or neurologic changes.",
        "triage_level": "Routine to emergency",
        "questions_to_cover": (
            "Was the headache sudden or gradual, and how severe is it?",
            "Any fever, neck stiffness, vomiting, visual change, weakness, numbness, or trouble speaking?",
            "Is this similar to prior headaches or clearly different?",
            "Was there recent head injury or major dehydration?",
        ),
        "possible_causes": "Could reflect migraine, tension headache, dehydration, infection, or neurologic emergencies depending on the pattern.",
        "recommended_next_step": "Clarify whether this feels like a typical recurrent issue or a new severe event. Escalate immediately for stroke-like symptoms or sudden worst headache.",
        "red_flags": (
            "sudden worst headache of life",
            "one-sided weakness or numbness",
            "trouble speaking or walking",
            "confusion, seizure, or fainting",
        ),
    },
    "abdominal symptoms": {
        "label": "Abdominal pain, vomiting, or diarrhea",
        "keywords": (
            "stomach pain",
            "abdominal pain",
            "belly pain",
            "vomiting",
            "diarrhea",
            "nausea",
            "constipation",
            "food poisoning",
        ),
        "care_setting": "Routine to urgent review depending on pain severity, hydration, and persistence.",
        "triage_level": "Routine to urgent",
        "questions_to_cover": (
            "Where is the pain, and is it cramping, sharp, or constant?",
            "How many times has vomiting or diarrhea happened, and is there blood?",
            "Can the person keep down fluids and pass urine normally?",
            "Any fever, pregnancy, recent travel, or abdominal surgery history?",
        ),
        "possible_causes": "May relate to infection, gastritis, food-related illness, constipation, gallbladder issues, or surgical causes depending on the pattern.",
        "recommended_next_step": "Check hydration and pain severity. Same-day review is safer for persistent severe pain, blood, or inability to keep fluids down.",
        "red_flags": (
            "severe or worsening abdominal pain",
            "blood in vomit or stool",
            "persistent vomiting with dehydration",
            "rigid abdomen, fainting, or pregnancy-related severe pain",
        ),
    },
    "urinary symptoms": {
        "label": "Urinary symptoms",
        "keywords": (
            "burning urine",
            "burning when peeing",
            "urine",
            "uti",
            "pee pain",
            "frequent urination",
            "blood in urine",
            "flank pain",
        ),
        "care_setting": "Routine to same-day review depending on fever, flank pain, vomiting, or pregnancy.",
        "triage_level": "Routine to urgent",
        "questions_to_cover": (
            "Is there burning, frequency, urgency, blood, or lower abdominal discomfort?",
            "Any fever, back or flank pain, or vomiting?",
            "How long has it been happening, and has it happened before?",
            "Any pregnancy, kidney disease, or catheter history?",
        ),
        "possible_causes": "Often urinary infection or irritation, though kidney involvement is more concerning when fever or flank pain is present.",
        "recommended_next_step": "Arrange medical review for likely infection, especially if symptoms are new or worsening. Escalate sooner if fever or back pain is involved.",
        "red_flags": (
            "fever with back or flank pain",
            "vomiting or inability to keep fluids down",
            "pregnancy with urinary symptoms",
            "marked weakness or confusion",
        ),
    },
    "skin or rash": {
        "label": "Skin rash or irritation",
        "keywords": (
            "rash",
            "itching",
            "hives",
            "skin redness",
            "eczema",
            "blister",
            "spots",
            "skin irritation",
        ),
        "care_setting": "Routine review for mild stable rashes; urgent review for facial involvement, pain, fever, or rapid spread.",
        "triage_level": "Routine to urgent",
        "questions_to_cover": (
            "Where is it located, and how fast is it spreading?",
            "Is it itchy, painful, blistering, or peeling?",
            "Any fever, swelling, new medication, food, or product exposure?",
            "Is the face, eyes, mouth, or genitals involved?",
        ),
        "possible_causes": "Can reflect allergy, irritation, infection, eczema, or medication reaction depending on appearance and associated symptoms.",
        "recommended_next_step": "Document distribution and associated symptoms. Prompt clinician review is safer if the rash is painful, widespread, or linked to swelling or fever.",
        "red_flags": (
            "trouble breathing or facial swelling",
            "widespread blistering or skin peeling",
            "rash with high fever or severe illness",
            "eye or mouth involvement",
        ),
    },
    "allergic reaction": {
        "label": "Allergic reaction or swelling",
        "keywords": (
            "allergy",
            "allergic reaction",
            "swelling",
            "face swelling",
            "lip swelling",
            "tongue swelling",
            "anaphylaxis",
            "hives",
        ),
        "care_setting": "Urgent to emergency, especially if swelling affects the face, tongue, throat, or breathing.",
        "triage_level": "Urgent to emergency",
        "questions_to_cover": (
            "What triggered it, and how quickly did it start?",
            "Is there lip, tongue, throat, or facial swelling?",
            "Any wheezing, breathing difficulty, vomiting, or dizziness?",
            "Has this happened before, and is emergency allergy medication available?",
        ),
        "possible_causes": "May be a mild allergy or a severe reaction; airway symptoms change the risk immediately.",
        "recommended_next_step": "Treat any airway, breathing, or faintness symptoms as an emergency and seek urgent human medical care right away.",
        "red_flags": (
            "tongue or throat swelling",
            "trouble breathing or wheezing",
            "faintness or collapse",
            "rapidly worsening hives with systemic symptoms",
        ),
    },
    "injury or musculoskeletal pain": {
        "label": "Injury, back pain, or joint pain",
        "keywords": (
            "back pain",
            "neck pain",
            "joint pain",
            "sprain",
            "injury",
            "fall",
            "twisted ankle",
            "muscle pain",
        ),
        "care_setting": "Routine to urgent review depending on severity, mobility, and neurologic symptoms.",
        "triage_level": "Routine to urgent",
        "questions_to_cover": (
            "What happened, and when did it happen?",
            "Can the person move the area or bear weight?",
            "Is there numbness, weakness, deformity, or severe swelling?",
            "Was there head injury, neck injury, or loss of consciousness?",
        ),
        "possible_causes": "Could be strain, sprain, fracture, nerve irritation, or more serious trauma based on mechanism and function loss.",
        "recommended_next_step": "Resting an obviously strained area may help, but urgent review is needed for deformity, major swelling, or inability to use the limb normally.",
        "red_flags": (
            "severe deformity or heavy swelling",
            "unable to bear weight or move the limb",
            "numbness, weakness, or loss of bladder/bowel control",
            "head or neck injury with confusion or severe pain",
        ),
    },
    "mental health crisis": {
        "label": "Mental health or behavioral crisis",
        "keywords": (
            "panic attack",
            "anxiety",
            "depressed",
            "suicidal",
            "self harm",
            "harm myself",
            "harm others",
            "mental health",
        ),
        "care_setting": "Urgent support is recommended, with immediate emergency or crisis support for self-harm, violence risk, or inability to stay safe.",
        "triage_level": "Urgent to emergency",
        "questions_to_cover": (
            "Is the concern mainly panic, low mood, confusion, or safety risk?",
            "Is there any thought of self-harm or harm to others right now?",
            "Is the person alone, safe, and able to reach a trusted human?",
            "Any substance use, severe sleep loss, or sudden behavior change?",
        ),
        "possible_causes": "May reflect anxiety, panic, depression, substance effects, or an acute behavioral emergency depending on safety risk and functioning.",
        "recommended_next_step": "If there is any active safety risk, connect to emergency or crisis support immediately and involve a trusted person if possible.",
        "red_flags": (
            "thoughts of self-harm or harming others",
            "extreme agitation, confusion, or hallucinations",
            "not able to stay safe alone",
            "collapse or overdose concern",
        ),
    },
}

VISUAL_GUIDANCE: dict[str, dict[str, Any]] = {
    "skin rash": {
        "label": "Visible rash or skin irritation",
        "keywords": ("rash", "spots", "hives", "skin", "redness", "blister"),
        "safe_language": "Describe the visible pattern, color change, spread, and whether the area looks raised, blistered, or swollen without claiming a diagnosis.",
        "recommended_action": "Ask about itch, pain, fever, new medications, recent foods, and whether the rash is spreading.",
        "escalation": "Escalate faster if there is facial swelling, eye or mouth involvement, widespread blistering, or breathing trouble.",
    },
    "swelling": {
        "label": "Visible swelling",
        "keywords": ("swelling", "puffy", "face swelling", "lip swelling", "tongue swelling"),
        "safe_language": "State that visible swelling can be concerning and that appearance alone is not enough to diagnose the cause.",
        "recommended_action": "Ask when it started, whether it is painful, and whether breathing, swallowing, or speaking feels affected.",
        "escalation": "Treat breathing, throat, tongue, or rapidly worsening facial swelling as urgent emergency care.",
    },
    "breathing distress": {
        "label": "Visible breathing difficulty",
        "keywords": ("breathing", "wheezing", "gasping", "labored", "short of breath"),
        "safe_language": "Acknowledge the visible increased breathing effort without naming a definitive condition.",
        "recommended_action": "Focus immediately on whether the person can speak comfortably, and direct them to urgent human care if not.",
        "escalation": "Treat severe labored breathing, blue discoloration, or inability to speak as an emergency.",
    },
    "wound or injury": {
        "label": "Visible wound or injury",
        "keywords": ("cut", "bleeding", "bruise", "wound", "injury", "burn"),
        "safe_language": "Describe bleeding, bruising, swelling, or deformity in plain language without estimating severity beyond what is visible.",
        "recommended_action": "Ask about pain, movement, sensation, and whether bleeding is controlled.",
        "escalation": "Escalate for heavy bleeding, visible deformity, major burns, or loss of feeling or movement.",
    },
    "eye concern": {
        "label": "Visible eye redness or swelling",
        "keywords": ("eye", "eyelid", "red eye", "swollen eye"),
        "safe_language": "Note visible redness, swelling, or discharge carefully and avoid labeling it as an infection or allergy just from appearance.",
        "recommended_action": "Ask about pain, vision change, contact lens use, discharge, and injury.",
        "escalation": "Urgent in-person review is safer when there is severe pain, vision change, trauma, or marked swelling.",
    },
}


def _match_guidance(
    query: str, guidance_map: dict[str, dict[str, Any]]
) -> tuple[str | None, dict[str, Any] | None]:
    normalized_query = normalize_lookup_key(query)
    for key, guidance in guidance_map.items():
        if normalized_query == key:
            return key, guidance

        keywords = guidance.get("keywords", ())
        if any(keyword in normalized_query for keyword in keywords):
            return key, guidance

    return None, None


def _default_intake_result(chief_concern: str) -> dict[str, Any]:
    return {
        "category": "General medical consultation",
        "chief_concern": chief_concern,
        "triage_level": "Needs clarification",
        "care_setting": "Depends on severity and red flags. Same-day review is safer if symptoms are worsening or limiting normal activity.",
        "questions_to_cover": GENERIC_INTAKE_QUESTIONS,
        "recommended_next_step": "Clarify timing, severity, associated symptoms, and medical context before estimating likely urgency.",
        "possible_causes": "There is not enough detail yet to estimate likely causes safely.",
        "red_flags": GENERIC_RED_FLAGS,
    }


class MedicalOfficerAgent(ScenarioAgent):
    def __init__(self) -> None:
        super().__init__(
            instructions=get_prompts(
                "general medical consultation and diagnostic support",
                """
Your primary function is to act as a general-purpose medical consultation and diagnostic-support assistant for routine, non-emergency medical questions across common symptoms and body systems.
You can help users organize their symptoms, understand what details matter clinically, compare likely care settings, and think through cautious next steps.
Do not present a definitive diagnosis, prescribe medication, replace a clinician, or minimize emergencies.
Use the consultation-intake, symptom-guidance, and visual-guidance tools before giving tool-backed medical guidance.
Use web search only when the user needs recent or public medical guidance that is not already covered by your tools.
""",
                """
## Opening
Always start with:
"Hello! This is Sai, can you hear me okay?"

## Flow
- Support broad medical consultations, symptom check-ins, care-navigation questions, and cautious video-based observations
- Use the consultation intake tool when the user is describing a problem or asking what details matter
- Use the symptom guidance tool when the user wants likely urgency, safe next steps, or general diagnostic support
- Use the visual guidance tool when the concern is visible on camera or image context is central
- If the request is unclear, ask one brief clarifying question
- Keep responses short, warm, practical, and medically cautious

## Safety
- If the user describes emergency symptoms, tell them to seek immediate human medical care right away
- Never claim certainty, never say appearance alone confirms a diagnosis, and never downplay urgent symptoms
- Do not advise starting, stopping, or changing prescription treatment without clinician guidance
- If the user mentions self-harm, harm to others, overdose, severe allergic reaction, stroke symptoms, severe chest pain, or major breathing difficulty, treat it as urgent or emergency escalation

## Diagnostic Support
- You may discuss likely categories or common possibilities in careful language such as "could be" or "can sometimes be related to"
- Focus on triage, key history questions, monitoring, and the safest care setting
- If live video is available, describe only obvious observations and pair them with a caution that visual assessment is limited

## Closing
- When the task is complete:
    "You're all set. Take care."
""",
                """
User: "I've had fever, cough, and body aches for two days."
Assistant: "I can help with safe next-step guidance."

User: "Do I need urgent care for this stomach pain?"
Assistant: "I can help you think through the likely urgency."

User: "Can you look at this rash on video?"
Assistant: "I can give cautious visual guidance, but I won't treat appearance alone as a diagnosis."

User: "I'm having severe chest pressure and I'm sweating."
Assistant: "Please seek emergency medical care right away."

User: "My face is swelling and it's harder to breathe."
Assistant: "This needs immediate emergency care right now."

""",
                """
- Tool mapping:
  - get_consultation_intake: use first for broad symptom descriptions, "what should I mention to a doctor?", and general intake structuring
  - get_symptom_guidance: use for likely urgency, common symptom-category guidance, and safe diagnostic support
  - get_visual_guidance: use for camera-based or appearance-based concerns
                """,
            ),
        )

    @function_tool()
    async def get_consultation_intake(
        self,
        context: RunContext,
        chief_concern: str = DEFAULT_CONCERN,
        duration: str = "not provided",
        age_group: str = "adult",
        additional_details: str = "not provided",
    ) -> dict[str, Any]:
        """Create a structured intake summary for a medical consultation.

        Use this when the user is describing symptoms, asking what information
        matters, or needs a concise intake-style summary before discussing likely
        urgency or next steps.

        Args:
            chief_concern: Main symptom or medical concern.
            duration: How long the concern has been present.
            age_group: Age group such as child, teen, adult, or older adult.
            additional_details: Optional associated symptoms or context.
        """

        _, guidance = _match_guidance(chief_concern, SYMPTOM_GUIDANCE)
        result = (
            {
                "category": guidance["label"],
                "chief_concern": chief_concern,
                "duration": duration,
                "age_group": age_group,
                "additional_details": additional_details,
                "triage_level": guidance["triage_level"],
                "care_setting": guidance["care_setting"],
                "questions_to_cover": guidance["questions_to_cover"],
                "recommended_next_step": guidance["recommended_next_step"],
                "possible_causes": guidance["possible_causes"],
                "red_flags": guidance["red_flags"],
            }
            if guidance is not None
            else {
                **_default_intake_result(chief_concern),
                "duration": duration,
                "age_group": age_group,
                "additional_details": additional_details,
            }
        )

        await self.push_widget(
            WidgetPayload(
                id="medical-consultation-intake",
                type="triage",
                title=f"{result['category']} intake",
                status="info",
                description="Structured intake guidance for a broad medical consultation.",
                data=rows_from_mapping(
                    {
                        "Chief concern": result["chief_concern"],
                        "Duration": result["duration"],
                        "Age group": result["age_group"],
                        "Triage level": result["triage_level"],
                        "Suggested care setting": result["care_setting"],
                        "Ask next": result["questions_to_cover"],
                    }
                ),
            )
        )
        return result

    @function_tool()
    async def get_symptom_guidance(
        self, context: RunContext, symptom: str = DEFAULT_CONCERN
    ) -> dict[str, Any]:
        """Provide broad, non-diagnostic guidance for common medical complaints.

        Use this for questions about likely urgency, safe next steps, common
        possibilities, or whether a concern sounds routine, urgent, or emergent.

        Args:
            symptom: Main symptom or concern in plain language.
        """

        _, guidance = _match_guidance(symptom, SYMPTOM_GUIDANCE)
        result = (
            {
                "found": True,
                "requested_symptom": symptom,
                "category": guidance["label"],
                "triage_level": guidance["triage_level"],
                "care_setting": guidance["care_setting"],
                "questions_to_cover": guidance["questions_to_cover"],
                "possible_causes": guidance["possible_causes"],
                "recommended_next_step": guidance["recommended_next_step"],
                "red_flags": guidance["red_flags"],
            }
            if guidance is not None
            else {
                "found": False,
                "requested_symptom": symptom,
                **_default_intake_result(symptom),
            }
        )

        await self.push_widget(
            WidgetPayload(
                id="medical-symptom-guidance",
                type="triage",
                title=f"{result['category']} guidance",
                status="success" if result["found"] else "warning",
                description="Safe, non-diagnostic triage guidance for a medical consultation.",
                data=rows_from_mapping(
                    {
                        "Concern": result["requested_symptom"],
                        "Triage level": result["triage_level"],
                        "Suggested care setting": result["care_setting"],
                        "Possible causes": result["possible_causes"],
                        "Next step": result["recommended_next_step"],
                        "Emergency red flags": result["red_flags"],
                    }
                ),
            )
        )
        return result

    @function_tool()
    async def get_visual_guidance(
        self, context: RunContext, observation: str = DEFAULT_VISUAL_CONCERN
    ) -> dict[str, Any]:
        """Provide cautious visual-observation guidance for visible concerns.

        Use this when the user asks about something visible on camera or wants
        general guidance based on a rash, swelling, wound, eye issue, or visible
        breathing difficulty.

        Args:
            observation: Plain-language description of what is visible.
        """

        _, guidance = _match_guidance(observation, VISUAL_GUIDANCE)
        if guidance is None:
            result = {
                "found": False,
                "requested_observation": observation,
                "category": "General visual concern",
                "safe_language": "Describe only visible features in plain language and avoid claiming a diagnosis from appearance alone.",
                "recommended_action": "Ask about onset, pain, fever, breathing issues, vision change, and any rapid worsening.",
                "escalation": "Escalate urgently if there is breathing trouble, severe pain, heavy bleeding, or rapid progression.",
            }
        else:
            result = {
                "found": True,
                "requested_observation": observation,
                "category": guidance["label"],
                "safe_language": guidance["safe_language"],
                "recommended_action": guidance["recommended_action"],
                "escalation": guidance["escalation"],
            }

        await self.push_widget(
            WidgetPayload(
                id="medical-visual-guidance",
                type="visual-triage",
                title=f"{result['category']} review",
                status="success" if result["found"] else "warning",
                description="Cautious guidance for visible medical concerns during a live session.",
                data=rows_from_mapping(
                    {
                        "Observation": result["requested_observation"],
                        "How to describe it": result["safe_language"],
                        "Ask next": result["recommended_action"],
                        "Escalate when": result["escalation"],
                    }
                ),
            )
        )
        return result
