import {
  ControlBar as LiveKitControlBar,
  MediaDeviceMenu,
  VoiceAssistantControlBar,
} from "@livekit/components-react";

export function ControlBar(props: {
  mediaMode: "audio" | "video";
}) {
  return (
    <div className="flex flex-wrap items-center justify-center gap-3 rounded-2xl border border-white/10 bg-white/5 p-3">
      {props.mediaMode === "video" ? (
        <LiveKitControlBar
          variation="verbose"
          controls={{
            chat: false,
            screenShare: false,
            settings: false,
          }}
        />
      ) : (
        <VoiceAssistantControlBar />
      )}
      <MediaDeviceMenu
        kind="audiooutput"
        className="lk-button"
        aria-label="Select speaker output"
      >
        Speaker
      </MediaDeviceMenu>
    </div>
  );
}
