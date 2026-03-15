import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "#/components/ui/accordion";
import { Badge } from "#/components/ui/badge";
import type {
  SceneTranscript as SceneTranscriptType,
  TranscriptSegment,
} from "#/shared/api/types";
import { formatTimestamp } from "#/shared/lib/format";

interface SceneTranscriptProps {
  transcript: SceneTranscriptType;
  sceneStartInMovie?: number;
  currentSceneTime?: number;
}

export function SceneTranscript({
  transcript,
  sceneStartInMovie,
  currentSceneTime,
}: SceneTranscriptProps) {
  const hasLeft = (transcript.left_segments?.length ?? 0) > 0;
  const hasScene = (transcript.scene_segments?.length ?? 0) > 0;
  const hasRight = (transcript.right_segments?.length ?? 0) > 0;
  const hasAny = hasLeft || hasScene || hasRight;

  if (!hasAny) {
    return (
      <p className="text-muted-foreground text-sm">Транскрипт недоступен</p>
    );
  }

  const activeTimeInMovie =
    sceneStartInMovie !== undefined && currentSceneTime !== undefined
      ? sceneStartInMovie + currentSceneTime
      : null;

  return (
    <div className="rounded-lg border bg-background px-4">
      <Accordion className="w-full" defaultValue={["scene"]} type="multiple">
        <AccordionItem value="before">
          <AccordionTrigger className="text-muted-foreground">
            Транскрипт до
          </AccordionTrigger>
          <AccordionContent>
            {hasLeft ? (
              <SegmentGroup
                activeTimeInMovie={activeTimeInMovie}
                muted
                segments={transcript.left_segments ?? []}
              />
            ) : (
              <p className="text-muted-foreground text-sm">Нет данных</p>
            )}
          </AccordionContent>
        </AccordionItem>

        <AccordionItem value="scene">
          <AccordionTrigger>Транскрипт</AccordionTrigger>
          <AccordionContent>
            {hasScene ? (
              <SegmentGroup
                activeTimeInMovie={activeTimeInMovie}
                segments={transcript.scene_segments ?? []}
              />
            ) : (
              <p className="text-muted-foreground text-sm">
                Транскрипт сцены недоступен
              </p>
            )}
          </AccordionContent>
        </AccordionItem>

        <AccordionItem value="after">
          <AccordionTrigger className="text-muted-foreground">
            Транскрипт после
          </AccordionTrigger>
          <AccordionContent>
            {hasRight ? (
              <SegmentGroup
                activeTimeInMovie={activeTimeInMovie}
                muted
                segments={transcript.right_segments ?? []}
              />
            ) : (
              <p className="text-muted-foreground text-sm">Нет данных</p>
            )}
          </AccordionContent>
        </AccordionItem>
      </Accordion>
    </div>
  );
}

interface SegmentGroupProps {
  segments: TranscriptSegment[];
  label?: string;
  muted?: boolean;
  activeTimeInMovie?: number | null;
}

function SegmentGroup({
  segments,
  label,
  muted,
  activeTimeInMovie,
}: SegmentGroupProps) {
  return (
    <div className="space-y-2">
      {label && (
        <p className="mb-2 font-medium text-muted-foreground text-xs uppercase tracking-wide">
          {label}
        </p>
      )}
      <div className="space-y-1.5">
        {segments.map((seg) => (
          <TranscriptSegmentRow
            activeTimeInMovie={activeTimeInMovie}
            key={seg.start}
            muted={muted}
            segment={seg}
          />
        ))}
      </div>
    </div>
  );
}

function TranscriptSegmentRow({
  segment,
  muted,
  activeTimeInMovie,
}: {
  segment: TranscriptSegment;
  muted?: boolean;
  activeTimeInMovie?: number | null;
}) {
  const isActive =
    activeTimeInMovie !== null &&
    activeTimeInMovie !== undefined &&
    activeTimeInMovie >= segment.start &&
    activeTimeInMovie <= segment.end;

  return (
    <div
      className={`rounded-md border px-3 py-2 transition-colors ${
        isActive
          ? "border-primary/40 bg-primary/10"
          : muted
            ? "border-border/60 bg-muted/20"
            : "border-border bg-background"
      }`}
    >
      <div className="flex items-start gap-3">
        <span className="mt-0.5 shrink-0 text-muted-foreground text-xs tabular-nums">
          {formatTimestamp(segment.start)}
        </span>
        <div className="min-w-0 space-y-1">
          {segment.speaker && (
            <Badge className="h-5 px-1.5 text-[10px]" variant="secondary">
              {segment.speaker}
            </Badge>
          )}
          <p
            className={`text-sm leading-relaxed ${muted ? "text-muted-foreground" : ""}`}
          >
            {segment.text}
          </p>
        </div>
      </div>
    </div>
  );
}
