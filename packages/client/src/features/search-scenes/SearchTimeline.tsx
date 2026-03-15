import { Loader2 } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import type { SearchStatus, SeqEvent } from "./useAgentSearch";

interface SearchTimelineProps {
  events: SeqEvent[];
  status: SearchStatus;
}

export function SearchTimeline({ events, status }: SearchTimelineProps) {
  const visible = events.filter(
    (e) => e.type !== "conclusion" && e.type !== "search_started",
  );
  const show =
    (status === "streaming" || status === "done") && visible.length > 0;

  return (
    <AnimatePresence>
      {show && (
        <motion.div
          animate={{ opacity: 1, height: "auto" }}
          className="mb-6 overflow-hidden rounded-xl border border-border"
          exit={{ opacity: 0, height: 0 }}
          initial={{ opacity: 0, height: 0 }}
          transition={{ duration: 0.3 }}
        >
          {status === "streaming" && (
            <div className="flex items-center gap-2 border-b bg-muted/30 px-4 py-2.5">
              <Loader2 className="size-3.5 shrink-0 animate-spin text-muted-foreground" />
              <span className="font-medium text-muted-foreground text-xs">
                Агент анализирует запрос
              </span>
            </div>
          )}
          <div className="divide-y divide-border">
            {visible.map((event) => (
              <motion.div
                animate={{ opacity: 1 }}
                className="px-4 py-2.5"
                initial={{ opacity: 0 }}
                key={event._seq}
                transition={{ duration: 0.2 }}
              >
                <EventRow event={event} />
              </motion.div>
            ))}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function EventRow({ event }: { event: SeqEvent }) {
  switch (event.type) {
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
        <p className="text-muted-foreground text-sm">
          Найдено{" "}
          <span className="font-medium text-foreground">
            {event.data.count}
          </span>{" "}
          кандидатов
        </p>
      );
    case "error":
      return <p className="text-destructive text-sm">{event.data.message}</p>;
    default:
      return null;
  }
}
