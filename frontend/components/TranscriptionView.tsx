import useCombinedTranscriptions from "@/hooks/useCombinedTranscriptions";
import * as React from "react";

export default function TranscriptionView(props: { disconnectTrack: () => void }) {
  const combinedTranscriptions = useCombinedTranscriptions();
  const containerRef = React.useRef<HTMLDivElement>(null);
  const timeoutRef = React.useRef<NodeJS.Timeout | null>(null);

  // scroll to bottom when new transcription is added
  React.useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [combinedTranscriptions]);

  // Handle 30-second timeout after last agent transcription
  React.useEffect(() => {
    // Clear any existing timeout
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }

    // Find the last agent transcription
    const lastAgentTranscription = [...combinedTranscriptions]
      .reverse()
      .find(segment => segment.role === "assistant");

    if (lastAgentTranscription) {
      // Check if there's any user transcription after the last agent transcription
      const lastAgentTime = lastAgentTranscription.firstReceivedTime;
      const hasUserInputAfterAgent = combinedTranscriptions.some(
        segment => segment.role === "user" && segment.firstReceivedTime > lastAgentTime
      );

      // Only set timeout if there's no user input after the last agent transcription
      if (!hasUserInputAfterAgent) {
        timeoutRef.current = setTimeout(() => {
          props.disconnectTrack();
        }, 30000); // 30 seconds
      }
    }

    // Cleanup function to clear timeout on unmount
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [combinedTranscriptions, props]);

  return (
    <div className="relative h-[200px] w-[512px] max-w-[90vw] mx-auto">
      {/* Fade-out gradient mask */}
      <div className="absolute top-0 left-0 right-0 h-8 bg-gradient-to-b from-[var(--lk-bg)] to-transparent z-10 pointer-events-none" />
      <div className="absolute bottom-0 left-0 right-0 h-8 bg-gradient-to-t from-[var(--lk-bg)] to-transparent z-10 pointer-events-none" />

      {/* Scrollable content */}
      <div
        ref={containerRef}
        className="h-full flex flex-col gap-2 overflow-y-auto px-4 py-8"
      >
        {combinedTranscriptions.map((segment) => (
          <div
            id={segment.id}
            key={segment.id}
            className={
              segment.role === "assistant"
                ? "p-2 self-start fit-content"
                : "bg-gray-800 rounded-md p-2 self-end fit-content"
            }
          >
            {segment.text}
          </div>
        ))}
      </div>
    </div>
  );
}
