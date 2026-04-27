'use client';

import Link from 'next/link';
import { BookOpenCheck, BriefcaseMedicalIcon, MicIcon, User2Icon } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

const sections = [
  {
    title: 'Use Cases',
    items: [
      {
        title: 'General Purpose (Audio)',
        href: '/audio/general-purpose',
        icon: MicIcon,
        description:
          'A general purpose Voice Assistant for handling a variety of interactions across different scenarios.',
      },
      {
        title: 'Medical Examination (Avatar)',
        href: '/avatar/medical-examination',
        icon: BookOpenCheck,
        description:
          'A Medical Examination Avatar Assistant for handling medical consultation interactions.',
      },
      {
        title: 'General Purpose (Avatar)',
        href: '/avatar/general-purpose',
        icon: User2Icon,
        description:
          'A general purpose Avatar Assistant for handling a variety of interactions across different scenarios.',
      },
      {
        title: 'Medical Consultation Assistant',
        href: '/audio/medical-officer',
        icon: BriefcaseMedicalIcon,
        description:
          'Guide general medical consultations with symptom intake, triage support, care-navigation, and cautious video-based observations.',
      },
    ],
  },
  // {
  //   title: 'Audio',
  //   items: [
  //     {
  //       title: 'Front Desk Agent',
  //       href: '/audio/front-desk-agent',
  //       description:
  //         'Assist callers with greetings, bookings, visitor questions, and front desk workflows.',
  //     },
  //     {
  //       title: 'Resturant Agent',
  //       href: '/audio/resturant-agent',
  //       description:
  //         'Manage reservations, menu questions, order support, and restaurant guest interactions.',
  //     },
  //     {
  //       title: 'Medical Consultation Assistant',
  //       href: '/audio/medical-officer',
  //       description:
  //         'Guide general medical consultations with symptom intake, triage support, care-navigation, and cautious video-based observations.',
  //     },
  //   ],
  // },
  // {
  //   title: 'Avatar',
  //   items: [
  //     {
  //       title: 'Study Partner',
  //       href: '/avatar/study-partner',
  //       description:
  //         'An interactive learning companion for practice sessions, explanations, and study planning.',
  //     },
  //   ],
  // },
  // {
  //   title: 'Inbound/Outbound Calls',
  //   items: [
  //     {
  //       title: 'AI Calling/Answering Agent',
  //       href: '/calls/inbound-outbound',
  //       description:
  //         'Guide callers through smart voice menus, routing, and automated call handling flows.',
  //     },
  //   ],
  // },
];

export default function Page() {
  return (
    <main className="bg-background min-h-screen">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-12 px-6 py-10 md:px-10">
        <div className="space-y-3">
          <h1 className="text-4xl font-semibold tracking-tight">Sashflow</h1>
          <p className="text-muted-foreground max-w-2xl">
            Explore audio and avatar experiences for different assistant scenarios.
          </p>
        </div>

        {sections.map((section) => (
          <section key={section.title} className="space-y-5">
            <div className="space-y-1">
              <h2 className="text-2xl font-semibold tracking-tight">{section.title}</h2>
            </div>

            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {section.items.map((item) => (
                <Link key={item.href} href={item.href} className="group block">
                  <Card className="border-border/70 h-full transition-all duration-200 group-hover:-translate-y-1 group-hover:shadow-md">
                    <CardHeader className="flex items-center gap-4">
                      <div className="flex items-center rounded-lg bg-slate-200 p-2">
                        <item.icon className="h-4 w-4 text-zinc-950" />
                      </div>
                      <CardTitle className="text-lg">{item.title}</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="text-muted-foreground text-sm leading-6">{item.description}</p>
                    </CardContent>
                  </Card>
                </Link>
              ))}
            </div>
          </section>
        ))}
      </div>
    </main>
  );
}
