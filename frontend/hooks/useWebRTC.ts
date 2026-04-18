import { useEffect, useRef, useState } from "react";
import { SmallWebRTCTransport } from "@pipecat-ai/small-webrtc-transport";
import {
  Participant,
  RTVIClient,
  RTVIClientOptions,
} from "@pipecat-ai/client-js";

interface UseWebRTCProps {
  onLog?: (message: string, type?: string) => void;
  onChatLog?: (message: string, type: string) => void;
}

export function useWebRTC({ onLog, onChatLog }: UseWebRTCProps = {}) {
  const [connected, setConnected] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [micMuted, setMicMuted] = useState(false);
  const [cameraMuted, setCameraMuted] = useState(true);
  const [audioDevices, setAudioDevices] = useState<MediaDeviceInfo[]>([]);
  const [videoDevices, setVideoDevices] = useState<MediaDeviceInfo[]>([]);
  const [remainingTime, setRemainingTime] = useState<number | null>(null);
  const [transportState, setTransportState] = useState<string>("");
  const [isBotReady, setIsBotReady] = useState(false);

  const rtviClientRef = useRef<RTVIClient | null>(null);
  const transportRef = useRef<SmallWebRTCTransport | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const selfViewVideoRef = useRef<HTMLVideoElement | null>(null);
  const inactivityTimerRef = useRef<NodeJS.Timeout | null>(null);
  const countdownIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const startCountdown = () => {
    onLog?.("Starting countdown");
    setRemainingTime(15);
    if (countdownIntervalRef.current) {
      clearInterval(countdownIntervalRef.current);
    }
    countdownIntervalRef.current = setInterval(() => {
      setRemainingTime((prev) => {
        if (prev === null || prev <= 1) {
          if (countdownIntervalRef.current) {
            clearInterval(countdownIntervalRef.current);
          }
          return null;
        }
        return prev - 1;
      });
    }, 1000);
  };

  const clearCountdown = () => {
    if (countdownIntervalRef.current) {
      clearInterval(countdownIntervalRef.current);
      countdownIntervalRef.current = null;
    }
    setRemainingTime(null);
  };

  const initializeRTVIClient = () => {
    const transport = new SmallWebRTCTransport();
    transportRef.current = transport;

    const RTVIConfig: RTVIClientOptions = {
      transport,
      params: {
        baseUrl: process.env.NEXT_PUBLIC_API_URL + "/api/offer",
	waitForCandidates: true,
        gatheringTimeout: 5000,
        iceGatheringPolicy: "all",
        debug: true,
      },
      enableMic: true,
      enableCam: !cameraMuted,
      callbacks: {
        onTransportStateChanged: (state) => {
          setTransportState(state);
          onLog?.(`Transport state: ${state}`);
        },
        onConnected: () => {
          setConnected(true);
          setConnecting(false);
          onLog?.("Connected", "status");
        },
        onDisconnected: () => {
          setConnected(false);
          setConnecting(false);
          setIsBotReady(false);
          onLog?.("Disconnected", "status");
        },
        onBotReady: () => {
          setIsBotReady(true);
          onLog?.("Bot is ready.");
        },
        onUserStartedSpeaking: () => {
          if (inactivityTimerRef.current) {
            clearTimeout(inactivityTimerRef.current);
            inactivityTimerRef.current = null;
          }
          clearCountdown();
          onLog?.("User started speaking.");
        },
        onUserStoppedSpeaking: () => {
          onLog?.("User stopped speaking.");
        },
        onBotStartedSpeaking: () => {
          onLog?.("Bot started speaking.");
        },
        onBotStoppedSpeaking: () => {
          onLog?.("Bot stopped speaking.");
          // Start 15 second timer
          startCountdown();
          inactivityTimerRef.current = setTimeout(() => {
            onLog?.(
              "No user response detected for 15 seconds, stopping session."
            );
            clearCountdown();
            stop();
          }, 15000);
        },
        onUserTranscript: (transcript) => {
          if (transcript.final) {
            onLog?.(`User transcript: ${transcript.text}`);
            onChatLog?.(transcript.text.trim(), "User");
          }
        },
        onBotTranscript: (transcript) => {
          onLog?.(`Bot transcript: ${transcript.text}`);
          onChatLog?.(transcript.text.trim(), "Bot");
        },
        onTrackStarted: (
          track: MediaStreamTrack,
          participant?: Participant
        ) => {
          if (participant?.local) {
            if (track.kind === "video" && selfViewVideoRef.current) {
              selfViewVideoRef.current.srcObject = new MediaStream([track]);
            }
            return;
          }
          handleBotTrack(track);
        },
        onServerMessage: (msg) => {
          onLog?.(`Server message: ${JSON.stringify(msg)}`);
        },
      },
    };

    RTVIConfig.customConnectHandler = () => Promise.resolve();
    rtviClientRef.current = new RTVIClient(RTVIConfig);
  };

  const handleBotTrack = (track: MediaStreamTrack) => {
    if (track.kind === "video" && videoRef.current) {
      videoRef.current.srcObject = new MediaStream([track]);

      const checkVideoResolution = () => {
        if (!videoRef.current) return;
        const hasValidResolution =
          videoRef.current.videoWidth > 0 && videoRef.current.videoHeight > 0;
        // Update UI based on video visibility
        if (!track.muted && hasValidResolution) {
          videoRef.current.style.display = "block";
        } else {
          videoRef.current.style.display = "none";
        }
      };

      videoRef.current.addEventListener("loadedmetadata", checkVideoResolution);
      videoRef.current.addEventListener("resize", checkVideoResolution);

      track.onmute = () => {
        if (videoRef.current) videoRef.current.style.display = "none";
      };
      track.onunmute = () => {
        if (videoRef.current && videoRef.current.readyState >= 1) {
          checkVideoResolution();
        }
      };

      if (videoRef.current.readyState >= 1) {
        checkVideoResolution();
      }
    } else if (track.kind === "audio" && audioRef.current) {
      audioRef.current.srcObject = new MediaStream([track]);
    }
  };

  const populateDevices = async () => {
    try {
      if (!rtviClientRef.current) return;
      await rtviClientRef.current.initDevices();
      const audioDevices = await rtviClientRef.current.getAllMics();
      const videoDevices = await rtviClientRef.current.getAllCams();
      setAudioDevices(audioDevices);
      setVideoDevices(videoDevices);
      onLog?.(`Detected ${audioDevices.length} audio input devices`);
      onLog?.(`Detected ${videoDevices.length} video input devices`);
    } catch (e) {
      const error = e as Error;
      onLog?.(`Error getting devices: ${error.message}`, "error");
      console.error("Device initialization error:", e);
    }
  };

  const start = async () => {
    if (connecting || !rtviClientRef.current) return;

    setConnecting(true);
    onLog?.("Connecting...", "status");

    try {
      rtviClientRef.current.enableMic(!micMuted);
      rtviClientRef.current.enableCam(!cameraMuted);
      await rtviClientRef.current.connect();
    } catch (e) {
      const error = e as Error;
      onLog?.(`Failed to connect: ${error.message}`, "error");
      console.error("Connection error:", e);
      setConnecting(false);
      await stop();
    }
  };

  const stop = async () => {
    try {
      if (inactivityTimerRef.current) {
        clearTimeout(inactivityTimerRef.current);
        inactivityTimerRef.current = null;
      }
      clearCountdown();
      if (!rtviClientRef.current) return;
      await rtviClientRef.current.disconnect();

      if (videoRef.current?.srcObject) {
        videoRef.current.srcObject = null;
      }
      if (audioRef.current?.srcObject) {
        audioRef.current.srcObject = null;
      }
      if (selfViewVideoRef.current?.srcObject) {
        selfViewVideoRef.current.srcObject = null;
      }
    } catch (e) {
      const error = e as Error;
      onLog?.(`Error during disconnect: ${error.message}`, "error");
      console.error("Disconnect error:", e);
    }
  };

  const toggleMicrophone = async () => {
    if (!connected || !rtviClientRef.current) {
      onLog?.("Cannot toggle microphone when not connected", "error");
      return;
    }

    const newMicState = !micMuted;
    setMicMuted(newMicState);
    rtviClientRef.current.enableMic(!newMicState);
    onLog?.(newMicState ? "Microphone muted" : "Microphone unmuted");
  };

  const toggleCamera = async () => {
    if (!connected || !rtviClientRef.current) {
      onLog?.("Cannot toggle camera when not connected", "error");
      return;
    }

    const newCameraState = !cameraMuted;
    setCameraMuted(newCameraState);
    rtviClientRef.current.enableCam(!newCameraState);
    onLog?.(newCameraState ? "Camera turned off" : "Camera turned on");
  };

  const updateDevice = async (deviceId: string, type: "audio" | "video") => {
    if (!rtviClientRef.current) return;
    if (type === "audio") {
      await rtviClientRef.current.updateMic(deviceId);
    } else {
      await rtviClientRef.current.updateCam(deviceId);
    }
  };

  const handleTextSubmit = async (message: string) => {
    if (!rtviClientRef.current || !message.trim()) return;

    try {
      await rtviClientRef.current.action({
        service: "llm",
        action: "append_to_messages",
        arguments: [
          {
            name: "messages",
            value: [
              {
                role: "user",
                content: message,
              },
            ],
          },
        ],
      });
      onChatLog?.(message.trim(), "User");
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    initializeRTVIClient();
    populateDevices();

    return () => {
      if (inactivityTimerRef.current) {
        clearTimeout(inactivityTimerRef.current);
      }
      clearCountdown();
      stop();
    };
  }, []);

  useEffect(() => {
    if (!isBotReady && !micMuted && rtviClientRef.current) {
      setMicMuted(true);
      rtviClientRef.current.enableMic(false);
      onLog?.("Microphone muted - bot not ready");
    }
  }, [isBotReady]);

  return {
    connected,
    connecting,
    micMuted,
    cameraMuted,
    audioDevices,
    videoDevices,
    videoRef,
    audioRef,
    selfViewVideoRef,
    start,
    stop,
    toggleMicrophone,
    toggleCamera,
    updateDevice,
    handleTextSubmit,
    remainingTime,
    transportState,
    isBotReady,
  };
}
