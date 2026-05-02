import type { ScenarioDetails } from '@/types';

export const scenarios = {
  'medical-examination': {
    sessionType: ['avatar', 'Audio'],
    title: 'Medical Examination Assistant',
    description:
      'An avatar assistant that guides users through a structured medical examination process for insurance applications.',
    highlights: [
      'Guide users through a structured medical examination process',
      'Collect necessary information for insurance applications',
      'Provide a clear and supportive user experience',
    ],
    firstTimeGuidance: [],
    suggestedQuestions: [],
  },
} satisfies Record<string, ScenarioDetails>;
