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

// Compact inline variant for table cells
interface TaskProgressCompactProps {
  progress: ProgressData;
}

export function TaskProgressCompact({ progress }: TaskProgressCompactProps) {
  const total = progress.scenes_detected;
  const done = progress.scenes_embedded ?? 0;
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;

  return (
    <div className="flex items-center gap-2">
      <Progress className="h-1.5 w-20" value={pct} />
      <span className="text-muted-foreground text-xs tabular-nums">{pct}%</span>
    </div>
  );
}
