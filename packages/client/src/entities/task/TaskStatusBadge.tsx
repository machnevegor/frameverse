import { Badge } from "#/components/ui/badge";
import type { MovieStatus } from "#/shared/api/types";
import {
  MOVIE_STATUS_LABEL,
  MOVIE_STATUS_VARIANT,
} from "#/shared/config/constants";

interface TaskStatusBadgeProps {
  status: MovieStatus;
}

export function TaskStatusBadge({ status }: TaskStatusBadgeProps) {
  return (
    <Badge variant={MOVIE_STATUS_VARIANT[status]}>
      {MOVIE_STATUS_LABEL[status]}
    </Badge>
  );
}
