import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "#/components/ui/accordion";
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
    <div className="rounded-lg border bg-background px-4">
      <Accordion className="w-full" defaultValue={["scene"]} type="multiple">
        <AccordionItem value="before">
          <AccordionTrigger className="text-muted-foreground">
            Транскрипт до
          </AccordionTrigger>
          <AccordionContent>
            {hasLeft ? (
              <SegmentGroup muted segments={transcript.left_segments ?? []} />
            ) : (
              <p className="text-muted-foreground text-sm">Нет данных</p>
            )}
          </AccordionContent>
        </AccordionItem>

        <AccordionItem value="scene">
          <AccordionTrigger>Транскрипт</AccordionTrigger>
          <AccordionContent>
            {hasScene ? (
              <SegmentGroup segments={transcript.scene_segments ?? []} />
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
              <SegmentGroup muted segments={transcript.right_segments ?? []} />
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
}

function SegmentGroup({ segments, label, muted }: SegmentGroupProps) {
  return (
    <div>
      {label && (
        <p className="mb-2 font-medium text-muted-foreground text-xs uppercase tracking-wide">
          {label}
        </p>
      )}
      <div className="space-y-2">
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
