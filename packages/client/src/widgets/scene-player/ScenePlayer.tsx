import {
  ChevronLeft,
  ChevronRight,
  Loader2,
  Maximize,
  Pause,
  Play,
  Volume2,
  VolumeX,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Button } from "#/components/ui/button";
import { Slider } from "#/components/ui/slider";
import { formatDuration } from "#/shared/lib/format";

interface ScenePlayerProps {
  videoUrl: string;
  onPrev?: () => void;
  onNext?: () => void;
  hasPrev?: boolean;
  hasNext?: boolean;
}

export function ScenePlayer({
  videoUrl,
  onPrev,
  onNext,
  hasPrev,
  hasNext,
}: ScenePlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [playing, setPlaying] = useState(false);
  const [buffering, setBuffering] = useState(true);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [muted, setMuted] = useState(false);

  // Reset and autoplay when video source changes
  // biome-ignore lint/correctness/useExhaustiveDependencies: reset player state when video source changes
  useEffect(() => {
    const v = videoRef.current;
    if (!v) return;
    setPlaying(false);
    setBuffering(true);
    setCurrentTime(0);
    setDuration(0);
    v.load();
    void v.play().catch(() => {
      // autoplay may be blocked — user can click manually
    });
  }, [videoUrl]);

  function togglePlay() {
    const v = videoRef.current;
    if (!v) return;
    if (v.paused) void v.play();
    else v.pause();
  }

  function handleLoadedMetadata() {
    const v = videoRef.current;
    if (v) setDuration(v.duration);
  }

  function handleCanPlay() {
    setBuffering(false);
  }

  function handleWaiting() {
    setBuffering(true);
  }

  function handleTimeUpdate() {
    const v = videoRef.current;
    if (v) setCurrentTime(v.currentTime);
  }

  function handleSeek(value: number[]) {
    const v = videoRef.current;
    if (!v) return;
    v.currentTime = value[0] ?? 0;
    setCurrentTime(value[0] ?? 0);
  }

  function toggleMute() {
    const v = videoRef.current;
    if (!v) return;
    v.muted = !v.muted;
    setMuted((m) => !m);
  }

  function handleFullscreen() {
    const v = videoRef.current;
    if (v?.requestFullscreen) void v.requestFullscreen();
  }

  return (
    <div className="overflow-hidden rounded-lg bg-black">
      <div className="relative aspect-video w-full">
        <video
          className="h-full w-full"
          onCanPlay={handleCanPlay}
          onEnded={() => setPlaying(false)}
          onLoadedMetadata={handleLoadedMetadata}
          onPause={() => setPlaying(false)}
          onPlay={() => {
            setPlaying(true);
            setBuffering(false);
          }}
          onTimeUpdate={handleTimeUpdate}
          onWaiting={handleWaiting}
          playsInline
          ref={videoRef}
          src={videoUrl}
        >
          <track kind="captions" />
        </video>

        {buffering && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/40">
            <Loader2 className="size-8 animate-spin text-white/80" />
          </div>
        )}
      </div>

      <div className="space-y-2 bg-muted/40 p-2">
        <Slider
          className="h-1"
          max={duration || 1}
          min={0}
          onValueChange={handleSeek}
          step={0.1}
          value={[currentTime]}
        />

        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-1">
            {onPrev && (
              <Button
                disabled={!hasPrev}
                onClick={onPrev}
                size="icon-sm"
                variant="ghost"
              >
                <ChevronLeft className="size-4" />
              </Button>
            )}

            <Button onClick={togglePlay} size="icon-sm" variant="ghost">
              {playing && !buffering ? (
                <Pause className="size-4" />
              ) : (
                <Play className="size-4" />
              )}
            </Button>

            {onNext && (
              <Button
                disabled={!hasNext}
                onClick={onNext}
                size="icon-sm"
                variant="ghost"
              >
                <ChevronRight className="size-4" />
              </Button>
            )}

            <Button onClick={toggleMute} size="icon-sm" variant="ghost">
              {muted ? (
                <VolumeX className="size-4" />
              ) : (
                <Volume2 className="size-4" />
              )}
            </Button>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-muted-foreground text-xs tabular-nums">
              {formatDuration(currentTime)} / {formatDuration(duration)}
            </span>
            <Button onClick={handleFullscreen} size="icon-sm" variant="ghost">
              <Maximize className="size-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
