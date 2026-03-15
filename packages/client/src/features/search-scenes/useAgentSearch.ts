import { useCallback, useEffect, useReducer, useRef } from "react";
import type { SearchEvent, SearchResultGroup } from "#/shared/api/types";
import { API_BASE } from "#/shared/config/constants";

export type SearchStatus = "idle" | "streaming" | "done" | "error";

// SSE events have no inherent ID — attach a monotonic seq number for stable React keys
export type SeqEvent = SearchEvent & { _seq: number };

interface SearchState {
  status: SearchStatus;
  events: SeqEvent[];
  groups: SearchResultGroup[];
  summary: string | null;
  error: string | null;
  _seq: number;
}

type SearchAction =
  | { type: "START" }
  | { type: "EVENT"; event: SearchEvent }
  | { type: "DONE"; groups: SearchResultGroup[]; summary: string }
  | { type: "ERROR"; message: string }
  | { type: "RESET" };

const initialState: SearchState = {
  status: "idle",
  events: [],
  groups: [],
  summary: null,
  error: null,
  _seq: 0,
};

function reducer(state: SearchState, action: SearchAction): SearchState {
  switch (action.type) {
    case "START":
      return { ...initialState, status: "streaming" };
    case "EVENT":
      return {
        ...state,
        events: [...state.events, { ...action.event, _seq: state._seq }],
        _seq: state._seq + 1,
      };
    case "DONE":
      return {
        ...state,
        status: "done",
        groups: action.groups,
        summary: action.summary,
      };
    case "ERROR":
      return { ...state, status: "error", error: action.message };
    case "RESET":
      return initialState;
    default:
      return state;
  }
}

export function useAgentSearch() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const esRef = useRef<EventSource | null>(null);

  const closeEs = useCallback(() => {
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
  }, []);

  const search = useCallback(
    (query: string) => {
      closeEs();
      dispatch({ type: "START" });

      const es = new EventSource(
        `${API_BASE}/search/scenes?q=${encodeURIComponent(query)}`,
      );
      esRef.current = es;

      function handleEvent(
        eventType: SearchEvent["type"],
        rawData: string,
      ): void {
        try {
          // biome-ignore lint/suspicious/noExplicitAny: SSE data is untyped
          const data = JSON.parse(rawData) as any;
          const event = { type: eventType, data } as SearchEvent;

          if (eventType === "conclusion") {
            dispatch({ type: "EVENT", event });
            dispatch({
              type: "DONE",
              groups: (data.result?.groups as SearchResultGroup[]) ?? [],
              summary: (data.result?.summary as string) ?? "",
            });
            closeEs();
          } else if (eventType === "error") {
            dispatch({ type: "EVENT", event });
            dispatch({
              type: "ERROR",
              message: (data.message as string) ?? "Произошла ошибка",
            });
            closeEs();
          } else {
            dispatch({ type: "EVENT", event });
          }
        } catch {
          // malformed SSE payload — skip silently
        }
      }

      es.addEventListener("search_started", (e) =>
        handleEvent("search_started", (e as MessageEvent).data as string),
      );
      es.addEventListener("thinking", (e) =>
        handleEvent("thinking", (e as MessageEvent).data as string),
      );
      es.addEventListener("searching", (e) =>
        handleEvent("searching", (e as MessageEvent).data as string),
      );
      es.addEventListener("results_found", (e) =>
        handleEvent("results_found", (e as MessageEvent).data as string),
      );
      es.addEventListener("conclusion", (e) =>
        handleEvent("conclusion", (e as MessageEvent).data as string),
      );
      es.addEventListener("error", (e) =>
        handleEvent("error", (e as MessageEvent).data ?? "{}"),
      );

      es.onerror = () => {
        dispatch({ type: "ERROR", message: "Соединение прервано" });
        closeEs();
      };
    },
    [closeEs],
  );

  const reset = useCallback(() => {
    closeEs();
    dispatch({ type: "RESET" });
  }, [closeEs]);

  useEffect(() => {
    return closeEs;
  }, [closeEs]);

  return { ...state, search, reset };
}
