import { Badge } from "#/components/ui/badge";
import type { Movie } from "#/shared/api/types";
import {
  MOVIE_STATUS_LABEL,
  MOVIE_STATUS_VARIANT,
} from "#/shared/config/constants";

interface MovieStatusBadgeProps {
  movie: Movie;
}

export function MovieStatusBadge({ movie }: MovieStatusBadgeProps) {
  const status = movie.last_task?.status;
  if (!status) return null;

  return (
    <Badge variant={MOVIE_STATUS_VARIANT[status]}>
      {MOVIE_STATUS_LABEL[status]}
    </Badge>
  );
}
