"use client";

import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const sections = [
  {
    title: "Audio",
    items: [
      {
        title: "Medical Officer",
        href: "/audio/medical-officer",
        description:
          "Handle patient intake, appointment coordination, and basic healthcare support conversations.",
      },
      {
        title: "Front Desk Agent",
        href: "/audio/front-desk-agent",
        description:
          "Assist callers with greetings, bookings, visitor questions, and front desk workflows.",
      },
      {
        title: "Resturant Agent",
        href: "/audio/resturant-agent",
        description:
          "Manage reservations, menu questions, order support, and restaurant guest interactions.",
      },
    ],
  },
  {
    title: "Avatar",
    items: [
      {
        title: "Medical Officer",
        href: "/avatar/medical-officer",
        description:
          "A visual healthcare assistant for patient guidance, intake support, and care-related help.",
      },
      {
        title: "Study Partner",
        href: "/avatar/study-partner",
        description:
          "An interactive learning companion for practice sessions, explanations, and study planning.",
      },
      {
        title: "Help Desk Partner",
        href: "/avatar/help-desk-partner",
        description:
          "A visual support assistant for troubleshooting, answering questions, and user guidance.",
      },
    ],
  },
  {
    title: "Inbound/Outbound Calls",
    items: [
      {
        title: "AI Calling/Answering Agent",
        href: "/calls/inbound-outbound",
        description:
          "Guide callers through smart voice menus, routing, and automated call handling flows.",
      },
    ],
  },
];

export default function Page() {
  return (
    <main className="min-h-screen bg-background">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-12 px-6 py-10 md:px-10">
        <div className="space-y-3">
          <h1 className="text-4xl font-semibold tracking-tight">Sashflow</h1>
          <p className="max-w-2xl text-muted-foreground">
            Explore audio and avatar experiences for different assistant
            scenarios.
          </p>
        </div>

        {sections.map((section) => (
          <section key={section.title} className="space-y-5">
            <div className="space-y-1">
              <h2 className="text-2xl font-semibold tracking-tight">
                {section.title}
              </h2>
            </div>

            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {section.items.map((item) => (
                <Link key={item.href} href={item.href} className="group block">
                  <Card className="h-full border-border/70 transition-all duration-200 group-hover:-translate-y-1 group-hover:shadow-md">
                    <CardHeader>
                      <CardTitle className="text-lg">{item.title}</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="text-sm leading-6 text-muted-foreground">
                        {item.description}
                      </p>
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
