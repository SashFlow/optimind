"use client";

import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { LiveWidget, ScenarioDetails } from "@/types";

const statusClassNames: Record<LiveWidget["status"], string> = {
  info: "bg-sky-500/15 text-sky-100 border border-sky-300/20",
  success: "bg-emerald-500/15 text-emerald-100 border border-emerald-300/20",
  warning: "bg-amber-500/15 text-amber-100 border border-amber-300/20",
};

function WidgetStatusBadge(props: { status: LiveWidget["status"] }) {
  return (
    <span
      className={`rounded-full px-2.5 py-1 text-[11px] font-medium uppercase tracking-wide ${statusClassNames[props.status]}`}
    >
      {props.status}
    </span>
  );
}

export function LiveWidgetsPanel(
  props: ScenarioDetails & {
    connectionState: string;
    widgets: LiveWidget[];
  },
) {
  return (
    <aside className="flex min-h-[70vh] flex-col gap-4">
      <Card className="border-white/10 bg-white/5 text-white shadow-xl backdrop-blur">
        <CardHeader>
          <CardTitle>{props.title}</CardTitle>
          <CardDescription className="text-white/70">
            {props.description}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-[0.2em] text-white/60">
              Assistant state
            </p>
            <WidgetStatusBadge
              status={
                props.connectionState === "connecting"
                  ? "warning"
                  : props.connectionState === "disconnected"
                    ? "info"
                    : "success"
              }
            />
          </div>
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-[0.2em] text-white/60">
              Highlights
            </p>
            <ul className="space-y-2 text-sm text-white/85">
              {props.highlights.map((highlight) => (
                <li key={highlight} className="flex gap-2">
                  <span className="text-sky-300">•</span>
                  <span>{highlight}</span>
                </li>
              ))}
            </ul>
          </div>
        </CardContent>
      </Card>

      <div className="flex-1 space-y-4 overflow-y-auto pr-1">
        {props.widgets.length === 0 ? (
          <Card className="border-dashed border-white/10 bg-white/5 text-white/80 shadow-none">
            <CardHeader>
              <CardTitle className="text-base">Waiting for live data</CardTitle>
              <CardDescription className="text-white/60">
                Widget cards will appear here when the backend agent uses its
                tools.
              </CardDescription>
            </CardHeader>
          </Card>
        ) : (
          props.widgets.map((widget) => (
            <Card
              key={widget.id}
              className="border-white/10 bg-white/5 text-white shadow-lg"
            >
              <CardHeader>
                <CardTitle className="text-base">{widget.title}</CardTitle>
                <CardAction>
                  <WidgetStatusBadge status={widget.status} />
                </CardAction>
                {widget.description ? (
                  <CardDescription className="text-white/65">
                    {widget.description}
                  </CardDescription>
                ) : null}
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-3 text-sm">
                  {widget.data.map((field) => (
                    <div
                      key={`${widget.id}-${field.label}`}
                      className="grid gap-1 rounded-lg border border-white/8 bg-black/10 p-3"
                    >
                      <span className="text-xs font-semibold uppercase tracking-[0.18em] text-white/45">
                        {field.label}
                      </span>
                      <span className="leading-6 text-white/90">
                        {field.value}
                      </span>
                    </div>
                  ))}
                </div>
                {widget.highlights.length > 0 ? (
                  <div>
                    <p className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-white/45">
                      Notes
                    </p>
                    <ul className="space-y-2 text-sm text-white/80">
                      {widget.highlights.map((highlight) => (
                        <li key={highlight} className="flex gap-2">
                          <span className="text-sky-300">•</span>
                          <span>{highlight}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </aside>
  );
}
