"""Constants for the support agent."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from dataclasses import dataclass

EmotionMode = Literal["warm", "calm", "empathetic", "uplifting", "playful", "steady"]
VoiceGender = Literal["male", "female"]
SarvamLanguage = Literal[
    "bn-IN",
    "en-IN",
    "gu-IN",
    "hi-IN",
    "kn-IN",
    "ml-IN",
    "mr-IN",
    "od-IN",
    "pa-IN",
    "ta-IN",
    "te-IN",
]

TTS_LANGUAGES: set[str] = {
    "bn-IN",
    "en-IN",
    "gu-IN",
    "hi-IN",
    "kn-IN",
    "ml-IN",
    "mr-IN",
    "od-IN",
    "pa-IN",
    "ta-IN",
    "te-IN",
}

MALE_SPEAKER = "shubh"
FEMALE_SPEAKER = "priya"

EMOTION_PROFILES: dict[EmotionMode, dict[str, float | str]] = {
    "warm": {
        "pace": 1.0,
        "temperature": 0.6,
        "style": "Be open, caring, and lightly conversational. Make the user feel welcome and safe.",
    },
    "calm": {
        "pace": 0.85,
        "temperature": 0.45,
        "style": "Speak slowly and grounding. Use short sentences. Help the user settle their breath and body.",
    },
    "empathetic": {
        "pace": 0.9,
        "temperature": 0.55,
        "style": "Offer soft validation. Sit with their feelings. Avoid toxic positivity or rushing to fix things.",
    },
    "uplifting": {
        "pace": 1.05,
        "temperature": 0.7,
        "style": "Offer gentle encouragement while staying grounded. Celebrate small strengths without dismissing pain.",
    },
    "playful": {
        "pace": 1.1,
        "temperature": 0.75,
        "style": "Match light, joking energy with warm humor. Never mock or minimize what matters to them.",
    },
    "steady": {
        "pace": 0.95,
        "temperature": 0.5,
        "style": "Stay calm and firm. De-escalate anger or frustration without matching intensity or blaming.",
    },
}


@dataclass
class SupportState:
    emotion: EmotionMode = "warm"
    language: SarvamLanguage = "hi-IN"
    voice: VoiceGender = "male"
    last_heard_language: str | None = None


DEFAULT_SCENARIO = "medical-examination"
DEFAULT_LANGUAGE = "English"
DEFAULT_NAME = "Sanjay"
DEFAULT_PERSONA = "9876543210"
PERSONAS = {
    "9876543210": {
        "phone_number": "9876543210",
        "full_name": "Mr. Rohit Sharma",
        "dob": "1992-08-15",
    },
    "9876500001": {
        "phone_number": "9876500001",
        "full_name": "Ms. Priya Nair",
        "dob": "1995-01-20",
    },
    "9876500002": {
        "phone_number": "9876500002",
        "full_name": "Mr. Arjun Mehta",
        "dob": "1990-03-11",
    },
    "9876500003": {
        "phone_number": "9876500003",
        "full_name": "Ms. Sneha Kapoor",
        "dob": "1993-07-24",
    },
    "9876500004": {
        "phone_number": "9876500004",
        "full_name": "Mr. Vikram Singh",
        "dob": "1988-12-02",
    },
    "9876500005": {
        "phone_number": "9876500005",
        "full_name": "Ms. Ananya Reddy",
        "dob": "1996-09-18",
    },
    "9876500006": {
        "phone_number": "9876500006",
        "full_name": "Mr. Karan Malhotra",
        "dob": "1991-05-14",
    },
    "9876500007": {
        "phone_number": "9876500007",
        "full_name": "Ms. Neha Verma",
        "dob": "1994-02-28",
    },
    "9876500008": {
        "phone_number": "9876500008",
        "full_name": "Mr. Rahul Khanna",
        "dob": "1989-11-10",
    },
    "9876500009": {
        "phone_number": "9876500009",
        "full_name": "Ms. Pooja Iyer",
        "dob": "1997-06-06",
    },
    "9876500010": {
        "phone_number": "9876500010",
        "full_name": "Mr. Amit Joshi",
        "dob": "1992-01-17",
    },
    "9876500011": {
        "phone_number": "9876500011",
        "full_name": "Ms. Divya Menon",
        "dob": "1993-10-03",
    },
    "9876500012": {
        "phone_number": "9876500012",
        "full_name": "Mr. Siddharth Rao",
        "dob": "1987-04-22",
    },
    "9876500013": {
        "phone_number": "9876500013",
        "full_name": "Ms. Meera Pillai",
        "dob": "1998-08-09",
    },
    "9876500014": {
        "phone_number": "9876500014",
        "full_name": "Mr. Yash Patel",
        "dob": "1991-12-30",
    },
    "9876500015": {
        "phone_number": "9876500015",
        "full_name": "Ms. Kavya Shetty",
        "dob": "1995-03-26",
    },
    "9876500016": {
        "phone_number": "9876500016",
        "full_name": "Mr. Aditya Kulkarni",
        "dob": "1990-07-01",
    },
    "9876500017": {
        "phone_number": "9876500017",
        "full_name": "Ms. Ritika Bansal",
        "dob": "1994-11-19",
    },
    "9876500018": {
        "phone_number": "9876500018",
        "full_name": "Mr. Nikhil Jain",
        "dob": "1988-02-13",
    },
    "9876500019": {
        "phone_number": "9876500019",
        "full_name": "Ms. Shreya Das",
        "dob": "1996-05-29",
    },
    "9876500020": {
        "phone_number": "9876500020",
        "full_name": "Mr. Manish Tiwari",
        "dob": "1992-09-07",
    },
    "9876500021": {
        "phone_number": "9876500021",
        "full_name": "Ms. Aisha Khan",
        "dob": "1997-01-12",
    },
    "9876500022": {
        "phone_number": "9876500022",
        "full_name": "Mr. Rajat Arora",
        "dob": "1989-06-21",
    },
    "9876500023": {
        "phone_number": "9876500023",
        "full_name": "Ms. Simran Kaur",
        "dob": "1993-04-04",
    },
    "9876500024": {
        "phone_number": "9876500024",
        "full_name": "Mr. Harsh Vardhan",
        "dob": "1991-08-25",
    },
    "9876500025": {
        "phone_number": "9876500025",
        "full_name": "Ms. Ishita Roy",
        "dob": "1995-12-08",
    },
    "9876500026": {
        "phone_number": "9876500026",
        "full_name": "Mr. Deepak Yadav",
        "dob": "1987-10-16",
    },
    "9876500027": {
        "phone_number": "9876500027",
        "full_name": "Ms. Tanvi Mishra",
        "dob": "1998-02-01",
    },
    "9876500028": {
        "phone_number": "9876500028",
        "full_name": "Mr. Akash Choudhary",
        "dob": "1990-11-23",
    },
    "9876500029": {
        "phone_number": "9876500029",
        "full_name": "Ms. Nandini Rao",
        "dob": "1994-06-14",
    },
    "9876500030": {
        "phone_number": "9876500030",
        "full_name": "Mr. Varun Bhatia",
        "dob": "1992-03-05",
    },
    "9876500031": {
        "phone_number": "9876500031",
        "full_name": "Ms. Rhea Thomas",
        "dob": "1996-09-27",
    },
    "9876500032": {
        "phone_number": "9876500032",
        "full_name": "Mr. Abhishek Sinha",
        "dob": "1988-01-31",
    },
    "9876500033": {
        "phone_number": "9876500033",
        "full_name": "Ms. Mitali Ghosh",
        "dob": "1995-07-13",
    },
    "9876500034": {
        "phone_number": "9876500034",
        "full_name": "Mr. Sameer Puri",
        "dob": "1991-04-18",
    },
    "9876500035": {
        "phone_number": "9876500035",
        "full_name": "Ms. Lavanya Krishnan",
        "dob": "1997-11-09",
    },
    "9876500036": {
        "phone_number": "9876500036",
        "full_name": "Mr. Gaurav Saxena",
        "dob": "1989-05-02",
    },
    "9876500037": {
        "phone_number": "9876500037",
        "full_name": "Ms. Bhavna Chopra",
        "dob": "1993-08-20",
    },
    "9876500038": {
        "phone_number": "9876500038",
        "full_name": "Mr. Rohan Desai",
        "dob": "1990-12-11",
    },
    "9876500039": {
        "phone_number": "9876500039",
        "full_name": "Ms. Sanya Mallick",
        "dob": "1996-03-15",
    },
    "9876500040": {
        "phone_number": "9876500040",
        "full_name": "Mr. Tushar Anand",
        "dob": "1992-10-28",
    },
    "9876500041": {
        "phone_number": "9876500041",
        "full_name": "Ms. Keerthi Narayan",
        "dob": "1994-01-07",
    },
    "9876500042": {
        "phone_number": "9876500042",
        "full_name": "Mr. Mohit Sehgal",
        "dob": "1987-06-26",
    },
    "9876500043": {
        "phone_number": "9876500043",
        "full_name": "Ms. Pallavi Sen",
        "dob": "1998-04-12",
    },
    "9876500044": {
        "phone_number": "9876500044",
        "full_name": "Mr. Naveen Kumar",
        "dob": "1991-09-03",
    },
    "9876500045": {
        "phone_number": "9876500045",
        "full_name": "Ms. Anjali Bhat",
        "dob": "1995-02-22",
    },
    "9876500046": {
        "phone_number": "9876500046",
        "full_name": "Mr. Prateek Agarwal",
        "dob": "1989-07-30",
    },
    "9876500047": {
        "phone_number": "9876500047",
        "full_name": "Ms. Shruti Kulshrestha",
        "dob": "1993-11-14",
    },
    "9876500048": {
        "phone_number": "9876500048",
        "full_name": "Mr. Devansh Gupta",
        "dob": "1990-05-19",
    },
    "9876500049": {
        "phone_number": "9876500049",
        "full_name": "Ms. Aarushi Bedi",
        "dob": "1997-08-06",
    },
    "9876500050": {
        "phone_number": "9876500050",
        "full_name": "Mr. Chirag Oberoi",
        "dob": "1992-12-24",
    },
}
CURRENT_DATE = datetime.now(tz=timezone.utc).date().isoformat()
INTERACTION_MODES = {"audio", "video"}
INTERACTION_MODE_BY_SCENARIO_TYPE = {
    "audio": "audio",
    "avatar": "video",
    "calls": "audio",
    "phone": "audio",
    "video": "video",
}
