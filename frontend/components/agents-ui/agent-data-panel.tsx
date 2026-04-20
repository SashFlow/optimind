'use client';

import React from 'react';
import { AnimatePresence, motion } from 'motion/react';
import {
  Buildings,
  Calendar,
  CheckCircle,
  Eye,
  FirstAid,
  ForkKnife,
  Images,
  Info,
  ListBullets,
  Package,
  Pill,
  Stethoscope,
  User,
} from '@phosphor-icons/react';
import { cn } from '@/lib/shadcn/utils';
import {
  type FlashCard,
  type Quiz,
  type Widget,
  type WidgetStatus,
  useAgentRpc,
} from './agent-rpc-provider';

// ---------------------------------------------------------------------------
// Icon + colour maps
// ---------------------------------------------------------------------------

const WIDGET_TYPE_ICON: Record<string, React.ElementType> = {
  visitor: User,
  schedule: Calendar,
  'patient-profile': FirstAid,
  prescription: Pill,
  triage: Stethoscope,
  'visual-triage': Eye,
  'booking-confirmation': CheckCircle,
  'service-info': Info,
  'office-info': Buildings,
  reservation: ForkKnife,
  menu: ListBullets,
  'menu-showcase': Images,
  order: Package,
};

const STATUS_STYLES: Record<WidgetStatus, { border: string; badge: string; dot: string }> = {
  success: {
    border: 'border-l-emerald-500',
    badge: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400',
    dot: 'bg-emerald-500',
  },
  warning: {
    border: 'border-l-amber-400',
    badge: 'bg-amber-400/10 text-amber-600 dark:text-amber-400',
    dot: 'bg-amber-400',
  },
  info: {
    border: 'border-l-blue-500',
    badge: 'bg-blue-500/10 text-blue-600 dark:text-blue-400',
    dot: 'bg-blue-500',
  },
};

// ---------------------------------------------------------------------------
// WidgetCard
// ---------------------------------------------------------------------------

function WidgetCard({ widget }: { widget: Widget }) {
  const status = (widget.status as WidgetStatus) in STATUS_STYLES ? widget.status : 'info';
  const styles = STATUS_STYLES[status as WidgetStatus];
  const IconComponent = WIDGET_TYPE_ICON[widget.type] ?? Info;
  const isMenuShowcase = widget.type === 'menu-showcase';

  return (
    <div
      className={cn(
        'bg-background/95 rounded-lg border border-l-2 p-3 shadow-md backdrop-blur-sm',
        styles.border
      )}
    >
      {/* Header */}
      <div className="mb-2 flex items-start gap-2">
        <IconComponent className="text-muted-foreground mt-0.5 size-4 shrink-0" weight="regular" />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-foreground truncate text-xs leading-tight font-semibold">
              {widget.title}
            </span>
            <span
              className={cn(
                'inline-flex shrink-0 items-center gap-1 rounded-full px-1.5 py-0.5 text-[10px] font-medium',
                styles.badge
              )}
            >
              <span className={cn('size-1.5 rounded-full', styles.dot)} />
              {widget.status}
            </span>
          </div>
          {widget.description && (
            <p className="text-muted-foreground mt-0.5 line-clamp-2 text-[10px]">
              {widget.description}
            </p>
          )}
        </div>
      </div>

      {/* Data rows */}
      {widget.data.length > 0 && (
        <div className="space-y-1">
          {widget.data.map((field, i) => (
            <div key={i} className="flex items-start justify-between gap-2">
              <span className="text-muted-foreground shrink-0 text-[10px] font-medium">
                {field.label}
              </span>
              <span className="text-foreground truncate text-right text-[10px]">{field.value}</span>
            </div>
          ))}
        </div>
      )}

      {/* Image grid for menu-showcase */}
      {isMenuShowcase && widget.highlights.length > 0 && (
        <div className="mt-2 grid grid-cols-3 gap-1">
          {widget.highlights.map((url, i) => (
            /* eslint-disable-next-line @next/next/no-img-element */
            <img
              key={i}
              src={url}
              alt={`Menu item ${i + 1}`}
              className="aspect-square w-full rounded object-cover"
              loading="lazy"
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// FlashCardView
// ---------------------------------------------------------------------------

function FlashCardView({ card }: { card: FlashCard }) {
  return (
    <div className="bg-background/95 rounded-lg border p-3 shadow-md backdrop-blur-sm">
      <div className="text-muted-foreground mb-1.5 flex items-center justify-between text-[10px] font-medium">
        <span>Flashcard {card.index + 1}</span>
        <span className="rounded-full bg-violet-500/10 px-1.5 py-0.5 text-violet-600 dark:text-violet-400">
          {card.isFlipped ? 'Answer' : 'Question'}
        </span>
      </div>
      <p className="text-foreground text-xs leading-snug">
        {card.isFlipped ? card.answer : card.question}
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// QuizView
// ---------------------------------------------------------------------------

function QuizView({ quiz }: { quiz: Quiz }) {
  return (
    <div className="bg-background/95 rounded-lg border p-3 shadow-md backdrop-blur-sm">
      <div className="text-muted-foreground mb-2 flex items-center justify-between text-[10px] font-medium">
        <span>Quiz · {quiz.questions.length} questions</span>
        <span className="rounded-full bg-sky-500/10 px-1.5 py-0.5 text-sky-600 dark:text-sky-400">
          Answer verbally
        </span>
      </div>
      <div className="space-y-2.5">
        {quiz.questions.map((q, qi) => (
          <div key={q.id}>
            <p className="text-foreground mb-1 text-[11px] leading-snug font-semibold">
              {qi + 1}. {q.text}
            </p>
            <ul className="space-y-0.5">
              {q.answers.map((a, ai) => (
                <li
                  key={a.id}
                  className="text-muted-foreground flex items-start gap-1.5 text-[10px]"
                >
                  <span className="text-muted-foreground/50 shrink-0 font-medium">
                    {String.fromCharCode(65 + ai)}.
                  </span>
                  {a.text}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// AgentDataPanel
// ---------------------------------------------------------------------------

/**
 * Reads RPC state from AgentRpcContext and renders a compact overlay panel
 * in the top-right corner of whatever positioned parent it lives in.
 *
 * - Widgets (FrontDesk / MedicalOfficer / Restaurant): stacked cards, newest last
 * - FlashCards (StudyPartner): shows the last card sent by the agent
 * - Quiz (StudyPartner): shows full question list with answer options
 *
 * The panel is non-interactive (pointer-events-none on the outer wrapper) so
 * it does not block clicks on the session controls beneath it.
 */
export function AgentDataPanel() {
  const { widgets, flashCards, quiz } = useAgentRpc();

  const hasContent = widgets.length > 0 || flashCards.length > 0 || quiz !== null;

  return (
    <AnimatePresence>
      {hasContent && (
        <motion.div
          key="agent-data-panel"
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: 20 }}
          transition={{ duration: 0.25, ease: 'easeOut' }}
          className="pointer-events-none absolute top-16 right-3 z-[60] flex w-72 flex-col gap-2 md:right-6"
          style={{ maxHeight: 'calc(100% - 10rem)' }}
        >
          {/* Inner scroll container */}
          <div className="flex flex-col gap-2 overflow-y-auto pb-2">
            {/* Widget cards */}
            {widgets.map((w) => (
              <WidgetCard key={w.id} widget={w} />
            ))}

            {/* Latest flashcard */}
            {flashCards.length > 0 && <FlashCardView card={flashCards[flashCards.length - 1]} />}

            {/* Quiz */}
            {quiz && <QuizView quiz={quiz} />}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
