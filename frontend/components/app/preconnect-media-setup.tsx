'use client';

import { useEffect, useRef } from 'react';
import { CameraIcon, MicIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { usePreconnectMedia } from '@/hooks/use-preconnect-media';
import { cn } from '@/lib/shadcn/utils';

interface PreconnectMediaSetupProps {
  requireMicrophone?: boolean;
  requireCamera?: boolean;
  showCameraPreview?: boolean;
  onReadinessChange?: (canStart: boolean) => void;
  onRegisterBeforeStart?: (beforeStart: () => void) => void;
}

export function PreconnectMediaSetup({
  requireMicrophone = true,
  requireCamera = true,
  showCameraPreview = true,
  onReadinessChange,
  onRegisterBeforeStart,
}: PreconnectMediaSetupProps) {
  const videoPreviewRef = useRef<HTMLVideoElement>(null);
  const {
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
  } = usePreconnectMedia({ requireMicrophone, requireCamera });

  useEffect(() => {
    onReadinessChange?.(canStart);
  }, [canStart, onReadinessChange]);

  useEffect(() => {
    onRegisterBeforeStart?.(stopPreview);
  }, [onRegisterBeforeStart, stopPreview]);

  useEffect(() => {
    const videoElement = videoPreviewRef.current;
    if (!videoElement) return;

    videoElement.srcObject = previewStream;
  }, [previewStream]);

  return (
    <div className="border-border/70 bg-card w-full rounded-2xl border p-6 shadow-sm">
      <h2 className="text-center text-sm font-semibold tracking-wide uppercase">Media setup</h2>

      {showCameraPreview && (
        <div className="bg-muted mt-4 overflow-hidden rounded-xl border">
          <video
            ref={videoPreviewRef}
            muted
            autoPlay
            playsInline
            className={cn('aspect-video w-full object-cover', !previewStream && 'opacity-50')}
          />
        </div>
      )}
      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <div className="space-y-2">
          <p className="text-muted-foreground text-xs font-semibold tracking-wide uppercase">
            Microphone
          </p>
          <Select
            value={selectedAudioDeviceId}
            onValueChange={(value) => void setSelectedAudioDeviceId(value)}
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Select microphone" />
            </SelectTrigger>
            <SelectContent>
              {audioDevices.length === 0 ? (
                <SelectItem value="no-audio-devices" disabled>
                  No microphones found
                </SelectItem>
              ) : (
                audioDevices.map((device, index) => (
                  <SelectItem key={device.deviceId} value={device.deviceId}>
                    {device.label || `Microphone ${index + 1}`}
                  </SelectItem>
                ))
              )}
            </SelectContent>
          </Select>
          <Button
            type="button"
            variant={isMicrophoneEnabled ? 'default' : 'secondary'}
            onClick={() => void (isMicrophoneEnabled ? disableMicrophone() : enableMicrophone())}
            className="w-full"
          >
            <MicIcon className="size-4" />
            {isMicrophoneEnabled ? 'Microphone enabled' : 'Enable microphone'}
          </Button>
        </div>

        <div className="space-y-2">
          <p className="text-muted-foreground text-xs font-semibold tracking-wide uppercase">
            Camera
          </p>
          <Select
            value={selectedVideoDeviceId}
            onValueChange={(value) => void setSelectedVideoDeviceId(value)}
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Select camera" />
            </SelectTrigger>
            <SelectContent>
              {videoDevices.length === 0 ? (
                <SelectItem value="no-video-devices" disabled>
                  No cameras found
                </SelectItem>
              ) : (
                videoDevices.map((device, index) => (
                  <SelectItem key={device.deviceId} value={device.deviceId}>
                    {device.label || `Camera ${index + 1}`}
                  </SelectItem>
                ))
              )}
            </SelectContent>
          </Select>
          <Button
            type="button"
            variant={isCameraEnabled ? 'default' : 'secondary'}
            onClick={() => void (isCameraEnabled ? disableCamera() : enableCamera())}
            className="w-full"
          >
            <CameraIcon className="size-4" />
            {isCameraEnabled ? 'Camera enabled' : 'Enable camera'}
          </Button>
        </div>
      </div>
      {error && <p className="text-destructive mt-3 text-xs">{error}</p>}
    </div>
  );
}
