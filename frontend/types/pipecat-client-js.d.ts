declare module "@pipecat-ai/client-js" {
  export interface Participant {
    local?: boolean;
  }

  export interface TranscriptEvent {
    text: string;
    final?: boolean;
  }

  export interface RTVIActionArgument {
    name: string;
    value: unknown;
  }

  export interface RTVIActionPayload {
    service: string;
    action: string;
    arguments?: RTVIActionArgument[];
  }

  export interface RTVIClientCallbacks {
    onTransportStateChanged?: (state: string) => void;
    onConnected?: () => void;
    onDisconnected?: () => void;
    onBotReady?: () => void;
    onUserStartedSpeaking?: () => void;
    onUserStoppedSpeaking?: () => void;
    onBotStartedSpeaking?: () => void;
    onBotStoppedSpeaking?: () => void;
    onUserTranscript?: (transcript: TranscriptEvent) => void;
    onBotTranscript?: (transcript: TranscriptEvent) => void;
    onTrackStarted?: (
      track: MediaStreamTrack,
      participant?: Participant,
    ) => void;
    onServerMessage?: (message: unknown) => void;
  }

  export interface RTVIClientOptions {
    transport: unknown;
    params?: Record<string, unknown>;
    enableMic?: boolean;
    enableCam?: boolean;
    callbacks?: RTVIClientCallbacks;
    customConnectHandler?: () => Promise<void>;
  }

  export class RTVIClient {
    constructor(options: RTVIClientOptions);
    initDevices(): Promise<void>;
    getAllMics(): Promise<MediaDeviceInfo[]>;
    getAllCams(): Promise<MediaDeviceInfo[]>;
    enableMic(enabled: boolean): void;
    enableCam(enabled: boolean): void;
    connect(): Promise<void>;
    disconnect(): Promise<void>;
    updateMic(deviceId: string): Promise<void>;
    updateCam(deviceId: string): Promise<void>;
    action(payload: RTVIActionPayload): Promise<void>;
  }
}
