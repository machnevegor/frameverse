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
        <div className="flex cursor-default items-center gap-2 rounded-md border border-border/60 bg-background/60 px-2 py-1">
          <Progress className="h-1.5 w-24" value={pct} />
          <span className="text-[11px] text-muted-foreground tabular-nums">
            {pct}%
          </span>
        </div>
      </HoverCardTrigger>
      <HoverCardContent
        align="start"
        className="w-80 border-border/60 bg-popover/90 p-0 shadow-xl backdrop-blur-md"
        side="top"
      >
        <div className="space-y-3 p-3">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-xs uppercase tracking-wide">
                Прогресс
              </p>
              <p className="text-muted-foreground text-xs">
                Обработка сцен фильма
              </p>
            </div>
            <div className="rounded-md bg-primary/10 px-2 py-1 font-semibold text-primary text-xs tabular-nums">
              {done}/{total}
            </div>
          </div>
          <Progress className="h-2" value={pct} />
          <div className="space-y-2">
            {rows.map((row) => (
              <div
                className="flex items-center justify-between gap-4"
                key={row.label}
              >
                <span className="text-xs opacity-80">{row.label}</span>
                <div className="flex items-center gap-1.5">
                  <div className="h-1.5 w-20 overflow-hidden rounded-full bg-primary/15">
                    <div
                      className="h-full rounded-full bg-primary/80"
                      style={{
                        width: `${total > 0 ? Math.round((row.value / total) * 100) : 0}%`,
                      }}
                    />
                  </div>
                  <span className="w-7 text-right text-xs tabular-nums">
                    {row.value}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
        <div className="flex items-center justify-between border-border/60 border-t bg-muted/20 px-3 py-2">
          <span className="text-muted-foreground text-xs">Готовность</span>
          <span className="font-medium text-xs tabular-nums">{pct}%</span>
        </div>
      </HoverCardContent>
    </HoverCard>
  );
}
