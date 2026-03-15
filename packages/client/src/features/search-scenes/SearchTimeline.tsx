import { Loader2 } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { SEARCH_EVENT_LABEL } from "#/shared/config/constants";
import type { SearchStatus, SeqEvent } from "./useAgentSearch";

interface SearchTimelineProps {
  events: SeqEvent[];
  status: SearchStatus;
}

export function SearchTimeline({ events, status }: SearchTimelineProps) {
  const visible = events.filter((e) => e.type !== "conclusion");
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
                {SEARCH_EVENT_LABEL.searching}
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
          {SEARCH_EVENT_LABEL.thinking}: {event.data.message}
        </p>
      );
    case "search_started":
      return (
        <p className="text-muted-foreground text-sm">
          {SEARCH_EVENT_LABEL.search_started}:{" "}
          <span className="font-medium text-foreground">{event.data.query}</span>
        </p>
      );
    case "searching":
      return (
        <p className="text-muted-foreground text-sm">
          {SEARCH_EVENT_LABEL.searching}:{" "}
          <span className="font-medium text-foreground">{event.data.query}</span>
        </p>
      );
    case "results_found":
      return (
        <p className="text-muted-foreground text-sm">
          {SEARCH_EVENT_LABEL.results_found}:{" "}
          <span className="font-medium text-foreground">
            {event.data.count}
          </span>
        </p>
      );
    case "error":
      return (
        <p className="text-destructive text-sm">
          {SEARCH_EVENT_LABEL.error}: {event.data.message}
        </p>
      );
    default:
      return null;
  }
}
