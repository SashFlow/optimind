from __future__ import annotations

from typing import Any

from livekit.agents import RunContext, function_tool

from .base import ScenarioAgent
from .common import WidgetPayload, normalize_lookup_key, rows_from_mapping
from .prompts import get_prompts

DEFAULT_SUBJECT = "biology"
DEFAULT_TOPIC = "photosynthesis"

STUDY_PLANS = {
    "biology": {
        "subject": "Biology",
        "focus_block_1": "Cell structure recap for 25 minutes",
        "focus_block_2": "Photosynthesis concept map for 20 minutes",
        "focus_block_3": "Past-paper questions for 15 minutes",
        "break_pattern": "5-minute break after each focus block",
    }
}

FLASHCARD_SETS = {
    "photosynthesis": {
        "topic": "Photosynthesis",
        "cards": [
            "Chlorophyll captures light energy in chloroplasts",
            "Light-dependent reactions produce ATP and NADPH",
            "The Calvin cycle uses carbon dioxide to form glucose",
        ],
        "memory_tip": "Remember Light first, Sugar second",
    }
}

PRACTICE_QUIZZES = {
    "photosynthesis": {
        "topic": "Photosynthesis",
        "question_1": "Why is chlorophyll essential in photosynthesis?",
        "question_2": "What are the outputs of the light-dependent stage?",
        "question_3": "How does the Calvin cycle use ATP and NADPH?",
        "coaching_tip": "Answer in short steps: purpose, process, outcome.",
    }
}


class StudyPartnerAgent(ScenarioAgent):
    def __init__(self) -> None:
        super().__init__(
            instructions=get_prompts(
                "Study Partner",
                """
Help users study effectively by answering quick concept questions, building simple study structure, and guiding short practice sessions.
Use the study plan, flashcard, and quiz tools when the user wants structured revision or topic-based practice.
Keep the interaction supportive, concise, and easy to follow.
""",
                """
## Opening
Always start with:
"Hello! This is Sai, can you hear me okay?"

## Flow
- Answer quick concept questions directly when possible
- Use the study plan tool for structured subject review
- Use the flashcard tool for quick recall practice
- Use the quiz tool for short mock drills
- Ask only one follow-up question when a missing topic or subject blocks progress

## Teaching Style
- Sound like a supportive tutor: upbeat, concise, and lightly conversational
- Keep explanations short and clear
- End with the next useful practice step only when it helps

## Fallback
- If the requested subject or topic is not in the demo data, explain the nearest available option naturally

## Closing
- When the learner seems done:
    "Nice work — keep going, and you’ll build momentum fast."
""",
                """
User: "Can you help me revise biology?"
Assistant: "Absolutely — I can help with a study plan, flashcards, or a quick quiz. Which would you like?"

User: "Quiz me on photosynthesis"
Assistant: "Sure — I can do that. Ready for the first question?"

User: "Explain photosynthesis quickly"
Assistant: "Photosynthesis is how plants use light, water, and carbon dioxide to make glucose and oxygen."

User: "I don't know where to start"
Assistant: "No problem — I can set up a short study plan first. What subject are you focusing on?"
""",
                """
- Use the available tools before giving specific structured study content from demo data.
- Prefer one tool at a time unless the user clearly asks for multiple things.
""",
            ),
        )

    @function_tool()
    async def get_study_plan(
        self, context: RunContext, subject: str = DEFAULT_SUBJECT
    ) -> dict[str, Any]:
        """Fetch a study plan before guiding the learner through a subject review session.

        Args:
            subject: Subject name such as biology.
        """

        plan = STUDY_PLANS.get(normalize_lookup_key(subject))
        if plan is None:
            result = {
                "found": False,
                "requested_subject": subject,
                "available_subjects": list(STUDY_PLANS.keys()),
            }
            await self.push_widget(
                WidgetPayload(
                    id="study-plan",
                    type="study-plan",
                    title="Study plan not found",
                    status="warning",
                    description="That subject is not available in the demo study planner.",
                    data=rows_from_mapping(
                        {
                            "Requested": subject,
                            "Available": result["available_subjects"],
                        }
                    ),
                )
            )
            return result

        await self.push_widget(
            WidgetPayload(
                id="study-plan",
                type="study-plan",
                title=f"{plan['subject']} study plan",
                status="success",
                description="Structured review blocks for the next session.",
                data=rows_from_mapping(
                    {
                        "Focus block 1": plan["focus_block_1"],
                        "Focus block 2": plan["focus_block_2"],
                        "Focus block 3": plan["focus_block_3"],
                        "Break pattern": plan["break_pattern"],
                    }
                ),
            )
        )
        return plan

    @function_tool()
    async def review_flashcards(
        self, context: RunContext, topic: str = DEFAULT_TOPIC
    ) -> dict[str, Any]:
        """Retrieve a flashcard set before quizzing or reviewing a topic.

        Args:
            topic: Topic name such as photosynthesis.
        """

        flashcards = FLASHCARD_SETS.get(normalize_lookup_key(topic))
        if flashcards is None:
            result = {
                "found": False,
                "requested_topic": topic,
                "available_topics": list(FLASHCARD_SETS.keys()),
            }
            await self.push_widget(
                WidgetPayload(
                    id="study-flashcards",
                    type="flashcards",
                    title="Flashcards not found",
                    status="warning",
                    description="That topic does not have a boilerplate flashcard set.",
                    data=rows_from_mapping(
                        {
                            "Requested": topic,
                            "Available": result["available_topics"],
                        }
                    ),
                )
            )
            return result

        await self.push_widget(
            WidgetPayload(
                id="study-flashcards",
                type="flashcards",
                title=f"{flashcards['topic']} flashcards",
                status="success",
                description="Quick recall prompts for revision.",
                data=rows_from_mapping(
                    {
                        "Card 1": flashcards["cards"][0],
                        "Card 2": flashcards["cards"][1],
                        "Card 3": flashcards["cards"][2],
                        "Memory tip": flashcards["memory_tip"],
                    }
                ),
            )
        )
        return flashcards

    @function_tool()
    async def create_practice_quiz(
        self, context: RunContext, topic: str = DEFAULT_TOPIC
    ) -> dict[str, Any]:
        """Create a short practice quiz before running a mock study drill.

        Args:
            topic: Topic name such as photosynthesis.
        """

        quiz = PRACTICE_QUIZZES.get(normalize_lookup_key(topic))
        if quiz is None:
            result = {
                "found": False,
                "requested_topic": topic,
                "available_topics": list(PRACTICE_QUIZZES.keys()),
            }
            await self.push_widget(
                WidgetPayload(
                    id="study-quiz",
                    type="quiz",
                    title="Practice quiz not found",
                    status="warning",
                    description="That topic does not have a boilerplate quiz set.",
                    data=rows_from_mapping(
                        {
                            "Requested": topic,
                            "Available": result["available_topics"],
                        }
                    ),
                )
            )
            return result

        await self.push_widget(
            WidgetPayload(
                id="study-quiz",
                type="quiz",
                title=f"{quiz['topic']} practice quiz",
                status="success",
                description="Three voice-friendly practice questions.",
                data=rows_from_mapping(
                    {
                        "Question 1": quiz["question_1"],
                        "Question 2": quiz["question_2"],
                        "Question 3": quiz["question_3"],
                        "Coaching tip": quiz["coaching_tip"],
                    }
                ),
            )
        )
        return quiz
