import { useVoiceAssistant } from "@livekit/components-react";
import { VideoTrack } from "@livekit/components-react";
import { BarVisualizer } from "@livekit/components-react";

export function AgentVisualizer() {
  const { state: agentState, videoTrack, audioTrack } = useVoiceAssistant();

  if (videoTrack) {
    return (
      <div className="h-full max-h-[78vh] max-w-[90vw] w-full aspect-square rounded-lg overflow-hidden">
        <VideoTrack trackRef={videoTrack} />
      </div>
    );
  }

  return (
    <div className="h-full max-h-[80vh] max-w-[90vw] w-full aspect-video">
      <BarVisualizer
        state={agentState}
        barCount={5}
        trackRef={audioTrack}
        className="agent-visualizer"
        options={{ minHeight: 24 }}
      />
    </div>
  );
}
