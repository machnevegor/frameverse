import { AnimatePresence, motion } from "motion/react";
import { Badge } from "#/components/ui/badge";
import type { SearchEvent } from "#/shared/api/types";
import type { SearchStatus } from "./useAgentSearch";

interface SearchTimelineProps {
  events: SearchEvent[];
  status: SearchStatus;
}

export function SearchTimeline({ events, status }: SearchTimelineProps) {
  // Filter out conclusion event — it has no visible representation in the timeline
  const visible = events.filter((e) => e.type !== "conclusion");

  const show =
    (status === "streaming" || status === "done") && visible.length > 0;

  return (
    <AnimatePresence>
      {show && (
        <motion.div
          animate={{ opacity: 1, height: "auto" }}
          className="mb-6 overflow-hidden"
          exit={{ opacity: 0, height: 0 }}
          initial={{ opacity: 0, height: 0 }}
          transition={{ duration: 0.3 }}
        >
          <div className="space-y-3 border-border border-l-2 pl-4">
            {visible.map((event, i) => (
              <TimelineItem
                event={event}
                isLast={i === visible.length - 1 && status === "streaming"}
                // biome-ignore lint/suspicious/noArrayIndexKey: SSE events have no stable ID
                key={i}
              />
            ))}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

interface TimelineItemProps {
  event: SearchEvent;
  isLast: boolean;
}

function TimelineItem({ event, isLast }: TimelineItemProps) {
  return (
    <motion.div
      animate={{ opacity: 1, x: 0 }}
      className="relative flex items-start gap-3"
      initial={{ opacity: 0, x: -8 }}
      transition={{ duration: 0.25 }}
    >
      {/* Dot on the timeline line */}
      <div className="absolute top-1.5 -left-[21px]">
        {isLast ? (
          <span className="block h-2.5 w-2.5 animate-pulse rounded-full bg-primary" />
        ) : (
          <span className="block h-2 w-2 rounded-full bg-muted-foreground/30" />
        )}
      </div>

      <EventContent event={event} />
    </motion.div>
  );
}

function EventContent({ event }: { event: SearchEvent }) {
  switch (event.type) {
    case "search_started":
      return (
        <p className="text-muted-foreground text-sm">
          Начинаю поиск:{" "}
          <span className="font-medium text-foreground">
            «{event.data.query}»
          </span>
        </p>
      );
    case "thinking":
      return (
        <p className="text-muted-foreground text-sm italic">
          {event.data.message}
        </p>
      );
    case "searching":
      return (
        <p className="text-muted-foreground text-sm">
          Уточняю запрос:{" "}
          <span className="font-medium text-foreground">
            {event.data.text_query}
          </span>
        </p>
      );
    case "results_found":
      return (
        <div className="flex items-center gap-2">
          <p className="text-muted-foreground text-sm">Найдено кандидатов:</p>
          <Badge variant="secondary">{event.data.count}</Badge>
        </div>
      );
    case "error":
      return <p className="text-destructive text-sm">{event.data.message}</p>;
    default:
      return null;
  }
}
