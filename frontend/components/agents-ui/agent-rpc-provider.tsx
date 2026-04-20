'use client';

import React, { createContext, useContext, useEffect, useRef, useState } from 'react';
import type { RpcInvocationData } from 'livekit-client';
import { useRoomContext } from '@livekit/components-react';

export type WidgetStatus = 'success' | 'warning' | 'info';

export interface WidgetField {
  label: string;
  value: string;
}

export interface Widget {
  id: string;
  type: string;
  title: string;
  status: WidgetStatus;
  description: string;
  data: WidgetField[];
  highlights: string[];
}

export interface FlashCard {
  id: string;
  question: string;
  answer: string;
  index: number;
  isFlipped: boolean;
}

export interface QuizAnswer {
  id: string;
  text: string;
}

export interface QuizQuestion {
  id: string;
  text: string;
  answers: QuizAnswer[];
}

export interface Quiz {
  id: string;
  questions: QuizQuestion[];
}

interface AgentRpcContextValue {
  /** All active widgets keyed by id, in insertion/update order */
  widgets: Widget[];
  flashCards: FlashCard[];
  quiz: Quiz | null;
}

const AgentRpcContext = createContext<AgentRpcContextValue>({
  widgets: [],
  flashCards: [],
  quiz: null,
});

export function useAgentRpc() {
  return useContext(AgentRpcContext);
}

/**
 * Registers LiveKit RPC handlers for all three methods used by the server agents:
 * - client.widget  (FrontDesk, MedicalOfficer, Restaurant)
 * - client.flashcard (StudyPartner)
 * - client.quiz     (StudyPartner)
 *
 * Must be mounted inside LiveKitRoom/RoomContext so that useRoomContext() resolves.
 * Mount this early (before isConnected) so handlers are ready before the first RPC arrives.
 */
export function AgentRpcProvider({ children }: { children: React.ReactNode }) {
  const room = useRoomContext();

  // Keep widgets in a Map so upserts by id replace in-place without duplicates.
  const widgetMapRef = useRef<Map<string, Widget>>(new Map());
  const [widgets, setWidgets] = useState<Widget[]>([]);
  const [flashCards, setFlashCards] = useState<FlashCard[]>([]);
  const [quiz, setQuiz] = useState<Quiz | null>(null);

  useEffect(() => {
    if (!room) return;

    const widgetHandler = async (data: RpcInvocationData): Promise<string> => {
      try {
        const payload = JSON.parse(data.payload);
        if (payload.action === 'clear') {
          widgetMapRef.current.clear();
          setWidgets([]);
        } else if (payload.action === 'upsert' && payload.widget) {
          const w = payload.widget as Widget;
          widgetMapRef.current.set(w.id, w);
          setWidgets(Array.from(widgetMapRef.current.values()));
        }
      } catch {
        // Swallow parse errors — a malformed payload should not break the agent session.
      }
      return '';
    };

    const flashcardHandler = async (data: RpcInvocationData): Promise<string> => {
      try {
        const payload = JSON.parse(data.payload);
        if (payload.action === 'show') {
          const card: FlashCard = {
            id: payload.id,
            question: payload.question,
            answer: payload.answer,
            index: payload.index ?? 0,
            isFlipped: false,
          };
          setFlashCards((prev) => {
            const idx = prev.findIndex((c) => c.id === payload.id);
            if (idx >= 0) {
              const next = [...prev];
              next[idx] = card;
              return next;
            }
            return [...prev, card];
          });
        } else if (payload.action === 'flip') {
          setFlashCards((prev) =>
            prev.map((c) => (c.id === payload.id ? { ...c, isFlipped: !c.isFlipped } : c))
          );
        }
      } catch {
        // Swallow parse errors.
      }
      return '';
    };

    const quizHandler = async (data: RpcInvocationData): Promise<string> => {
      try {
        const payload = JSON.parse(data.payload);
        if (payload.action === 'show') {
          setQuiz({ id: payload.id, questions: payload.questions });
        }
      } catch {
        // Swallow parse errors.
      }
      return '';
    };

    room.registerRpcMethod('client.widget', widgetHandler);
    room.registerRpcMethod('client.flashcard', flashcardHandler);
    room.registerRpcMethod('client.quiz', quizHandler);

    return () => {
      room.unregisterRpcMethod('client.widget');
      room.unregisterRpcMethod('client.flashcard');
      room.unregisterRpcMethod('client.quiz');
    };
  }, [room]);

  return (
    <AgentRpcContext.Provider value={{ widgets, flashCards, quiz }}>
      {children}
    </AgentRpcContext.Provider>
  );
}
