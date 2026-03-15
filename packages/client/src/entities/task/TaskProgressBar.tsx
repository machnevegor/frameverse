import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from "#/components/ui/hover-card";
import { Progress } from "#/components/ui/progress";
import { cn } from "#/lib/utils";
import type { MovieStatus, Progress as ProgressData } from "#/shared/api/types";
import { PIPELINE_STAGE_LABELS } from "#/shared/config/constants";

const PROCESSING_STAGES = PIPELINE_STAGE_LABELS.slice(1);

function clamp(value: number, total: number) {
  return Math.min(Math.max(value, 0), total);
}

function computeAvgPct(progress: ProgressData): number {
  const total = progress.scenes_detected;
  if (total === 0) return 0;
  const sum = PROCESSING_STAGES.reduce(
    (acc, stage) => acc + clamp(progress[stage.key] ?? 0, total),
    0,
  );
  return Math.round((sum / PROCESSING_STAGES.length / total) * 100);
}

function barColorClass(status: MovieStatus): string {
  if (status === "completed") return "bg-emerald-500";
  if (status === "cancelled" || status.startsWith("failed_"))
    return "bg-destructive";
  return "bg-primary";
}
interface TaskProgressBarProps {
  progress: ProgressData;
}

export function TaskProgressBar({ progress }: TaskProgressBarProps) {
  const total = progress.scenes_detected;
  if (total === 0)
    return <span className="text-muted-foreground text-sm">0 сцен</span>;

  const stages = PIPELINE_STAGE_LABELS.map((stage) => {
    const raw = progress[stage.key] ?? 0;
    const clamped = clamp(raw, total);
    return { label: stage.label, value: clamped, overflowed: raw > total };
  });

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

// ---------------------------------------------------------------------------
// Compact — used in the task table cell
// ---------------------------------------------------------------------------

interface TaskProgressCompactProps {
  progress: ProgressData;
  status: MovieStatus;
}

export function TaskProgressCompact({
  progress,
  status,
}: TaskProgressCompactProps) {
  const total = progress.scenes_detected;
  const pct = computeAvgPct(progress);
  const color = barColorClass(status);

  const rows = PIPELINE_STAGE_LABELS.map((stage) => {
    const raw = progress[stage.key] ?? 0;
    return { label: stage.label, value: clamp(raw, total) };
  });

  return (
    <HoverCard openDelay={120}>
      <HoverCardTrigger asChild>
        <div className="flex w-fit cursor-default items-center gap-2">
          <div className="h-1.5 w-24 overflow-hidden rounded-full bg-primary/15">
            <div
              className={cn("h-full rounded-full transition-all", color)}
              style={{ width: `${pct}%` }}
            />
          </div>
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
                Среднее по всем стадиям
              </p>
            </div>
            <div
              className={cn(
                "rounded-md px-2 py-1 font-semibold text-xs tabular-nums",
                status === "completed" &&
                  "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
                (status === "cancelled" || status.startsWith("failed_")) &&
                  "bg-destructive/10 text-destructive",
                status !== "completed" &&
                  status !== "cancelled" &&
                  !status.startsWith("failed_") &&
                  "bg-primary/10 text-primary",
              )}
            >
              {pct}%
            </div>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-primary/15">
            <div
              className={cn("h-full rounded-full transition-all", color)}
              style={{ width: `${pct}%` }}
            />
          </div>
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
          <span className="text-muted-foreground text-xs">Всего сцен</span>
          <span className="font-medium text-xs tabular-nums">{total}</span>
        </div>
      </HoverCardContent>
    </HoverCard>
  );
}
