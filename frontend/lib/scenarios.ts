import type { ScenarioDetails } from "@/types";

export const audioScenarios = {
  "medical-officer": {
    title: "Medical Officer",
    description:
      "Support patient intake, appointment coordination, symptom collection, and general healthcare communication.",
    highlights: [
      "Collect patient details and reason for visit",
      "Guide callers through appointment scheduling",
      "Answer common healthcare workflow questions",
      "Escalate urgent cases to the right team",
    ],
  },
  "front-desk-agent": {
    title: "Front Desk Agent",
    description:
      "Handle greetings, visitor support, booking requests, and day-to-day front desk conversations.",
    highlights: [
      "Welcome callers and identify their needs",
      "Manage bookings and appointment confirmations",
      "Share office hours, directions, and policies",
      "Route requests to the correct department",
    ],
  },
  "resturant-agent": {
    title: "Resturant Agent",
    description:
      "Assist guests with reservations, menu questions, order support, and restaurant service interactions.",
    highlights: [
      "Take and update table reservations",
      "Answer menu and dietary questions",
      "Support takeaway and delivery inquiries",
      "Handle guest requests with a friendly tone",
    ],
  },
} satisfies Record<string, ScenarioDetails>;

export const avatarScenarios = {
  "medical-officer": {
    title: "Medical Officer",
    description:
      "A visual healthcare assistant designed to support patient guidance, intake conversations, and care-related interactions.",
    highlights: [
      "Guide patients through intake and onboarding steps",
      "Answer common healthcare support questions",
      "Assist with appointment preparation and follow-up context",
    ],
  },
  "study-partner": {
    title: "Study Partner",
    description:
      "An interactive avatar companion that helps learners review concepts, practice responses, and stay on track with study goals.",
    highlights: [
      "Explain concepts in a conversational format",
      "Support mock practice and revision sessions",
      "Encourage structured learning and study planning",
    ],
  },
  "help-desk-partner": {
    title: "Help Desk Partner",
    description:
      "A visual support assistant for troubleshooting workflows, answering user questions, and guiding people through common issues.",
    highlights: [
      "Walk users through troubleshooting steps",
      "Answer product and support questions clearly",
      "Provide a friendly first-line support experience",
    ],
  },
} satisfies Record<string, ScenarioDetails>;
