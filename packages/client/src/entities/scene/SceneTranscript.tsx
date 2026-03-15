import { ScrollArea } from "#/components/ui/scroll-area";
import { Separator } from "#/components/ui/separator";
import type {
  SceneTranscript as SceneTranscriptType,
  TranscriptSegment,
} from "#/shared/api/types";
import { formatTimestamp } from "#/shared/lib/format";

interface SceneTranscriptProps {
  transcript: SceneTranscriptType;
}

export function SceneTranscript({ transcript }: SceneTranscriptProps) {
  const hasLeft = (transcript.left_segments?.length ?? 0) > 0;
  const hasScene = (transcript.scene_segments?.length ?? 0) > 0;
  const hasRight = (transcript.right_segments?.length ?? 0) > 0;
  const hasAny = hasLeft || hasScene || hasRight;

  if (!hasAny) {
    return (
      <p className="text-muted-foreground text-sm">Транскрипт недоступен</p>
    );
  }

  return (
    <ScrollArea className="h-64 rounded border">
      <div className="space-y-4 p-3">
        {hasLeft && (
          <SegmentGroup
            label="Контекст до сцены"
            muted
            segments={transcript.left_segments ?? []}
          />
        )}
        {hasLeft && hasScene && <Separator />}
        {hasScene && (
          <SegmentGroup
            label="Реплики сцены"
            segments={transcript.scene_segments ?? []}
          />
        )}
        {hasRight && (hasLeft || hasScene) && <Separator />}
        {hasRight && (
          <SegmentGroup
            label="Контекст после сцены"
            muted
            segments={transcript.right_segments ?? []}
          />
        )}
      </div>
    </ScrollArea>
  );
}

interface SegmentGroupProps {
  segments: TranscriptSegment[];
  label: string;
  muted?: boolean;
}

function SegmentGroup({ segments, label, muted }: SegmentGroupProps) {
  return (
    <div>
      <p className="mb-2 font-medium text-muted-foreground text-xs uppercase tracking-wide">
        {label}
      </p>
      <div className="space-y-1.5">
        {segments.map((seg, i) => (
          <div
            className={`flex gap-2 text-sm ${muted ? "text-muted-foreground" : ""}`}
            // stable enough: transcript segments are immutable, ordered list
            // biome-ignore lint/suspicious/noArrayIndexKey: transcript segments are ordered and have no stable id
            key={`${seg.start}-${i}`}
          >
            <span className="mt-0.5 shrink-0 text-muted-foreground text-xs tabular-nums">
              {formatTimestamp(seg.start)}
            </span>
            <div className="min-w-0">
              {seg.speaker && (
                <span className="mr-1 font-medium text-xs">{seg.speaker}:</span>
              )}
              {seg.text}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
