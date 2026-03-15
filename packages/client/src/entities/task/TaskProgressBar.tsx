import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from "#/components/ui/hover-card";
import { Progress } from "#/components/ui/progress";
import type { Progress as ProgressData } from "#/shared/api/types";
import { PIPELINE_STAGE_LABELS } from "#/shared/config/constants";

interface TaskProgressBarProps {
  progress: ProgressData;
}

export function TaskProgressBar({ progress }: TaskProgressBarProps) {
  const total = progress.scenes_detected;
  if (total === 0)
    return <span className="text-muted-foreground text-sm">0 сцен</span>;

  const stages = PIPELINE_STAGE_LABELS.map((stage) => ({
    label: stage.label,
    value: progress[stage.key] ?? 0,
  }));

  return (
    <div className="space-y-2">
      {stages.map((stage) => (
        <div className="space-y-1" key={stage.label}>
          <div className="flex justify-between text-xs">
            <span className="text-muted-foreground">{stage.label}</span>
            <span className="tabular-nums">
              {stage.value} / {total}
            </span>
          </div>
          <Progress
            className="h-1.5"
            value={Math.round((stage.value / total) * 100)}
          />
        </div>
      ))}
    </div>
  );
}

// Compact inline variant for table cells — with tooltip breakdown
interface TaskProgressCompactProps {
  progress: ProgressData;
}

export function TaskProgressCompact({ progress }: TaskProgressCompactProps) {
  const total = progress.scenes_detected;
  const done = progress.scenes_embedded ?? 0;
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;

  const rows = PIPELINE_STAGE_LABELS.map((stage) => ({
    label: stage.label,
    value: progress[stage.key] ?? 0,
  }));

  return (
    <HoverCard openDelay={120}>
      <HoverCardTrigger asChild>
        <div className="flex cursor-default items-center gap-2">
          <Progress className="h-1.5 w-20" value={pct} />
          <span className="text-muted-foreground text-xs tabular-nums">
            {pct}%
          </span>
        </div>
      </HoverCardTrigger>
      <HoverCardContent
        align="start"
        className="w-64 space-y-2 border-border/60 bg-popover/85 p-3 shadow-xl backdrop-blur-md"
        side="top"
      >
        {rows.map((row) => (
          <div
            className="flex items-center justify-between gap-4"
            key={row.label}
          >
            <span className="text-xs opacity-70">{row.label}</span>
            <div className="flex items-center gap-1.5">
              <div className="h-1 w-16 overflow-hidden rounded-full bg-primary/15">
                <div
                  className="h-full rounded-full bg-primary/80"
                  style={{
                    width: `${total > 0 ? Math.round((row.value / total) * 100) : 0}%`,
                  }}
                />
              </div>
              <span className="w-6 text-right text-xs tabular-nums">
                {row.value}
              </span>
            </div>
          </div>
        ))}
        <hr className="border-border/70" />
        <div className="pt-0.5 text-center text-xs tabular-nums opacity-60">
          {total} сцен всего
        </div>
      </HoverCardContent>
    </HoverCard>
  );
}
