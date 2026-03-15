import { Progress } from "#/components/ui/progress";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "#/components/ui/tooltip";
import type { Progress as ProgressData } from "#/shared/api/types";
import { PIPELINE_STAGE_LABELS } from "#/shared/config/constants";

interface TaskProgressBarProps {
  progress: ProgressData;
}

export function TaskProgressBar({ progress }: TaskProgressBarProps) {
  const total = progress.scenes_detected;
  if (total === 0)
    return <span className="text-muted-foreground text-sm">0 сцен</span>;

  const stages = [
    { label: PIPELINE_STAGE_LABELS[0].label, value: progress.scenes_detected },
    {
      label: PIPELINE_STAGE_LABELS[1].label,
      value: progress.scenes_extracted ?? 0,
    },
    {
      label: PIPELINE_STAGE_LABELS[2].label,
      value: progress.scenes_annotated ?? 0,
    },
    {
      label: PIPELINE_STAGE_LABELS[3].label,
      value: progress.scenes_embedded ?? 0,
    },
  ];

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

  const rows: { label: string; value: number }[] = [
    { label: "Обнаружено сцен", value: total },
    { label: "Извлечено", value: progress.scenes_extracted ?? 0 },
    { label: "Аннотировано", value: progress.scenes_annotated ?? 0 },
    { label: "Эмбеддинг", value: progress.scenes_embedded ?? 0 },
  ];

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <div className="flex cursor-default items-center gap-2">
          <Progress className="h-1.5 w-20" value={pct} />
          <span className="text-muted-foreground text-xs tabular-nums">
            {pct}%
          </span>
        </div>
      </TooltipTrigger>
      <TooltipContent className="w-52 space-y-2 p-3" side="top">
        {rows.map((row) => (
          <div
            className="flex items-center justify-between gap-4"
            key={row.label}
          >
            <span className="text-xs opacity-70">{row.label}</span>
            <div className="flex items-center gap-1.5">
              <div className="h-1 w-16 overflow-hidden rounded-full bg-background/20">
                <div
                  className="h-full rounded-full bg-background/80"
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
        <hr className="border-background/20" />
        <div className="pt-0.5 text-center text-xs tabular-nums opacity-60">
          {total} сцен всего
        </div>
      </TooltipContent>
    </Tooltip>
  );
}
