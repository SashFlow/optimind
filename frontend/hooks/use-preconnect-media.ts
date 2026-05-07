'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { usePersistentUserChoices } from '@livekit/components-react';

interface UsePreconnectMediaOptions {
  requireMicrophone?: boolean;
  requireCamera?: boolean;
}

interface UsePreconnectMediaReturn {
  audioDevices: MediaDeviceInfo[];
  videoDevices: MediaDeviceInfo[];
  selectedAudioDeviceId: string;
  selectedVideoDeviceId: string;
  isMicrophoneEnabled: boolean;
  isCameraEnabled: boolean;
  previewStream: MediaStream | null;
  error: string | null;
  canStart: boolean;
  setSelectedAudioDeviceId: (deviceId: string) => Promise<void>;
  setSelectedVideoDeviceId: (deviceId: string) => Promise<void>;
  enableMicrophone: () => Promise<void>;
  disableMicrophone: () => void;
  enableCamera: () => Promise<void>;
  disableCamera: () => void;
  stopPreview: () => void;
}

function stopStream(stream: MediaStream | null) {
  if (!stream) return;
  stream.getTracks().forEach((track) => track.stop());
}

export function usePreconnectMedia({
  requireMicrophone = true,
  requireCamera = true,
}: UsePreconnectMediaOptions = {}): UsePreconnectMediaReturn {
  const [audioDevices, setAudioDevices] = useState<MediaDeviceInfo[]>([]);
  const [videoDevices, setVideoDevices] = useState<MediaDeviceInfo[]>([]);
  const [selectedAudioDeviceId, setSelectedAudioDeviceIdState] = useState('default');
  const [selectedVideoDeviceId, setSelectedVideoDeviceIdState] = useState('default');
  const [isMicrophoneEnabled, setIsMicrophoneEnabled] = useState(false);
  const [isCameraEnabled, setIsCameraEnabled] = useState(false);
  const [previewStream, setPreviewStream] = useState<MediaStream | null>(null);
  const [error, setError] = useState<string | null>(null);

  const micProbeStreamRef = useRef<MediaStream | null>(null);

  const {
    saveAudioInputEnabled,
    saveVideoInputEnabled,
    saveAudioInputDeviceId,
    saveVideoInputDeviceId,
  } = usePersistentUserChoices();

  const enumerateDevices = useCallback(async () => {
    if (!navigator?.mediaDevices?.enumerateDevices) {
      setError('Media device APIs are not available in this browser.');
      return;
    }

    const devices = await navigator.mediaDevices.enumerateDevices();
    const nextAudio = devices.filter((device) => device.kind === 'audioinput' && device.deviceId);
    const nextVideo = devices.filter((device) => device.kind === 'videoinput' && device.deviceId);

    setAudioDevices(nextAudio);
    setVideoDevices(nextVideo);

    if (nextAudio.length > 0 && !nextAudio.some((d) => d.deviceId === selectedAudioDeviceId)) {
      const firstAudioDevice = nextAudio[0]?.deviceId ?? 'default';
      setSelectedAudioDeviceIdState(firstAudioDevice);
      saveAudioInputDeviceId(firstAudioDevice);
    }

    if (nextVideo.length > 0 && !nextVideo.some((d) => d.deviceId === selectedVideoDeviceId)) {
      const firstVideoDevice = nextVideo[0]?.deviceId ?? 'default';
      setSelectedVideoDeviceIdState(firstVideoDevice);
      saveVideoInputDeviceId(firstVideoDevice);
    }
  }, [saveAudioInputDeviceId, saveVideoInputDeviceId, selectedAudioDeviceId, selectedVideoDeviceId]);

  const disableMicrophone = useCallback(() => {
    stopStream(micProbeStreamRef.current);
    micProbeStreamRef.current = null;
    setIsMicrophoneEnabled(false);
    saveAudioInputEnabled(false);
  }, [saveAudioInputEnabled]);

  const stopPreview = useCallback(() => {
    stopStream(previewStream);
    setPreviewStream(null);
    setIsCameraEnabled(false);
    saveVideoInputEnabled(false);
  }, [previewStream, saveVideoInputEnabled]);

  const enableMicrophone = useCallback(async (deviceId?: string) => {
    try {
      setError(null);
      stopStream(micProbeStreamRef.current);

      const activeDeviceId = deviceId ?? selectedAudioDeviceId;

      const stream = await navigator.mediaDevices.getUserMedia({
        audio:
          activeDeviceId && activeDeviceId !== 'default'
            ? { deviceId: { exact: activeDeviceId } }
            : true,
      });

      micProbeStreamRef.current = stream;
      setIsMicrophoneEnabled(true);
      saveAudioInputEnabled(true);
      saveAudioInputDeviceId(activeDeviceId || 'default');
      await enumerateDevices();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unable to access microphone.';
      setError(message);
      disableMicrophone();
    }
  }, [
    disableMicrophone,
    enumerateDevices,
    saveAudioInputDeviceId,
    saveAudioInputEnabled,
    selectedAudioDeviceId,
  ]);

  const enableCamera = useCallback(async (deviceId?: string) => {
    try {
      setError(null);
      stopStream(previewStream);

      const activeDeviceId = deviceId ?? selectedVideoDeviceId;

      const stream = await navigator.mediaDevices.getUserMedia({
        video:
          activeDeviceId && activeDeviceId !== 'default'
            ? { deviceId: { exact: activeDeviceId } }
            : true,
        audio: false,
      });

      setPreviewStream(stream);
      setIsCameraEnabled(true);
      saveVideoInputEnabled(true);
      saveVideoInputDeviceId(activeDeviceId || 'default');
      await enumerateDevices();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unable to access camera.';
      setError(message);
      stopPreview();
    }
  }, [enumerateDevices, previewStream, saveVideoInputDeviceId, saveVideoInputEnabled, selectedVideoDeviceId, stopPreview]);

  const setSelectedAudioDeviceId = useCallback(
    async (deviceId: string) => {
      setSelectedAudioDeviceIdState(deviceId);
      saveAudioInputDeviceId(deviceId || 'default');
      if (isMicrophoneEnabled) {
        await enableMicrophone(deviceId);
      }
    },
    [enableMicrophone, isMicrophoneEnabled, saveAudioInputDeviceId]
  );

  const setSelectedVideoDeviceId = useCallback(
    async (deviceId: string) => {
      setSelectedVideoDeviceIdState(deviceId);
      saveVideoInputDeviceId(deviceId || 'default');
      if (isCameraEnabled) {
        await enableCamera(deviceId);
      }
    },
    [enableCamera, isCameraEnabled, saveVideoInputDeviceId]
  );

  const disableCamera = useCallback(() => {
    stopPreview();
  }, [stopPreview]);

  useEffect(() => {
    void enumerateDevices();

    const onDeviceChange = () => {
      void enumerateDevices();
    };

    navigator.mediaDevices?.addEventListener?.('devicechange', onDeviceChange);

    return () => {
      navigator.mediaDevices?.removeEventListener?.('devicechange', onDeviceChange);
      stopStream(micProbeStreamRef.current);
      stopStream(previewStream);
    };
  }, [enumerateDevices, previewStream]);

  const canStart = useMemo(() => {
    const isMicReady = !requireMicrophone || isMicrophoneEnabled;
    const isCameraReady = !requireCamera || isCameraEnabled;
    return isMicReady && isCameraReady;
  }, [isCameraEnabled, isMicrophoneEnabled, requireCamera, requireMicrophone]);

  return {
    audioDevices,
    videoDevices,
    selectedAudioDeviceId,
    selectedVideoDeviceId,
    isMicrophoneEnabled,
    isCameraEnabled,
    previewStream,
    error,
    canStart,
    setSelectedAudioDeviceId,
    setSelectedVideoDeviceId,
    enableMicrophone,
    disableMicrophone,
    enableCamera,
    disableCamera,
    stopPreview,
  };
}
