import type { ScenarioDetails } from '@/types';

export const scenarios = {
  'general-purpose': {
    sessionType: ['audio', 'avatar'],
    title: 'General Purpose',
    description:
      'General-purpose agent for handling a wide range of tasks. Provides general assistance and support.',
    highlights: ['General assistance and support', 'Handles a variety of tasks'],
    firstTimeGuidance: [
      'Use this bot when you want a flexible assistant for open-ended conversations, quick research, or general problem-solving.',
      'You can ask factual questions, brainstorm ideas, get step-by-step guidance, or have it help you think through a task.',
      'If your request needs recent public information, the bot can use web search during the conversation.',
    ],
    suggestedQuestions: [
      'What can you help me with?',
      'Can you summarize a topic for me in simple terms?',
      'Help me brainstorm ideas for improving customer onboarding.',
      'What are some practical ways to stay productive this week?',
    ],
  },
  'medical-officer': {
    sessionType: ['audio', 'avatar'],
    title: 'Medical Consultation Assistant',
    description:
      'Support broad medical consultations with symptom intake, diagnostic guidance, care-setting recommendations, and cautious visual review.',
    highlights: [
      'Organize symptom intake across common body systems',
      'Offer cautious diagnostic support without claiming certainty',
      'Help users compare home care, clinic, urgent care, and emergency needs',
      'Use live video carefully for visible concerns such as rash, swelling, or breathing effort',
    ],
    firstTimeGuidance: [
      'Use this bot for general medical consultations when you want help describing symptoms, understanding likely urgency, or preparing for a clinician visit.',
      'It can discuss common symptom categories, likely care settings, and red flags, but it does not replace a clinician or emergency care.',
      'In video sessions, it can also give cautious guidance about visible concerns without claiming a diagnosis from appearance alone.',
    ],
    suggestedQuestions: [
      'I have had fever, cough, and body aches for two days. What should I watch for?',
      'Does this stomach pain sound like urgent care or something I can monitor?',
      'Can you help me explain these symptoms clearly before I speak to a doctor?',
      'Can you give cautious guidance for this visible rash?',
    ],
  },
  'front-desk-agent': {
    sessionType: ['audio'],
    title: 'Front Desk Agent',
    description:
      'Handle greetings, visitor support, booking requests, and day-to-day front desk conversations.',
    highlights: [
      'Welcome callers and identify their needs',
      'Manage bookings and appointment confirmations',
      'Share office hours, directions, and policies',
      'Route requests to the correct department',
    ],
    firstTimeGuidance: [
      'Use this bot for front-desk style tasks like checking visitor arrivals, finding free slots, booking meetings, and explaining available services.',
      'It can share office logistics such as hours, parking, and visitor policy, and it can confirm appointments from the demo schedule.',
      'For anything that needs identity verification or staff approval, it will route the user to a human or reception team.',
    ],
    suggestedQuestions: [
      'Has Aarav Mehta arrived?',
      'Do you have any free booking slots today?',
      'Can you book me for a product demo at 2:30 PM?',
      'What services do you offer?',
    ],
  },
  'resturant-agent': {
    sessionType: ['audio'],
    title: 'Resturant Agent',
    description:
      'Assist guests with reservations, menu questions, order support, and restaurant service interactions.',
    highlights: [
      'Take and update table reservations',
      'Answer menu and dietary questions',
      'Support takeaway and delivery inquiries',
      'Handle guest requests with a friendly tone',
    ],
    firstTimeGuidance: [
      'Use this bot to manage reservation lookups, browse menu items, get recommendations, place orders, and check current order status.',
      'It can show featured dishes with image links, guide guests based on dietary preferences, and surface active-order details for known guests.',
      'For booking changes or staff-only actions, it will explain the limitation and route the request appropriately.',
    ],
    suggestedQuestions: [
      'Can you check Maya Kapoor’s reservation?',
      'Show me the featured menu.',
      'What do you recommend for a vegetarian?',
      'What is in my active order right now?',
    ],
  },
  'study-partner': {
    sessionType: ['avatar'],
    title: 'Study Partner',
    description:
      'An interactive avatar companion that helps learners review concepts, practice responses, and stay on track with study goals.',
    highlights: [
      'Explain concepts in a conversational format',
      'Support mock practice and revision sessions',
      'Encourage structured learning and study planning',
    ],
    firstTimeGuidance: [
      'Use this bot as a guided study coach that explains concepts, asks follow-up questions, and keeps the learner actively engaged.',
      'It can create flash cards and quizzes during the session so learning becomes interactive instead of being only a lecture.',
      'This experience works best when the user answers out loud, asks for clarification, and treats it like a live tutor conversation.',
    ],
    suggestedQuestions: [
      'Can you quiz me on the Fall of the Roman Empire?',
      'Explain the political causes of Rome’s decline.',
      'Create a few flash cards for the key dates I should remember.',
      'Ask me one question at a time and coach me through the answer.',
    ],
  },
} satisfies Record<string, ScenarioDetails>;
