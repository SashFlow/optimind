import type { ScenarioDetails } from '@/types';

export const scenarios = {
  'general-purpose': {
    sessionType: ['audio', 'avatar'],
    title: 'General Purpose',
    description:
      'General-purpose agent for handling a wide range of tasks. Provides general assistance and support.',
    highlights: ['General assistance and support', 'Handles a variety of tasks'],
  },
  'medical-officer': {
    sessionType: ['audio', 'avatar'],
    title: 'Medical Officer',
    description:
      'Support patient intake, appointment coordination, symptom collection, and general healthcare communication.',
    highlights: [
      'Collect patient details and reason for visit',
      'Guide callers through appointment scheduling',
      'Answer common healthcare workflow questions',
      'Escalate urgent cases to the right team',
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
  },
  'help-desk-partner': {
    sessionType: ['avatar'],
    title: 'Help Desk Partner',
    description:
      'A visual support assistant for troubleshooting workflows, answering user questions, and guiding people through common issues.',
    highlights: [
      'Walk users through troubleshooting steps',
      'Answer product and support questions clearly',
      'Provide a friendly first-line support experience',
    ],
  },
} satisfies Record<string, ScenarioDetails>;
