import { Loader2, Search, X } from "lucide-react";
import { parseAsString, useQueryState } from "nuqs";
import { useRef } from "react";
import { Button } from "#/components/ui/button";

interface SearchBarProps {
  isLoading?: boolean;
  /** Compact mode when query is active — smaller vertical padding. */
  compact?: boolean;
  /** Called when user submits a search query. */
  onSearch?: (query: string) => void;
  /** Called when user cancels an active search. */
  onCancel?: () => void;
}

export function SearchBar({
  isLoading,
  compact,
  onSearch,
  onCancel,
}: SearchBarProps) {
  const [q, setQ] = useQueryState("q", parseAsString.withDefault(""));
  const inputRef = useRef<HTMLInputElement>(null);

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const value = inputRef.current?.value.trim() ?? "";
    void setQ(value || null);
    if (value) onSearch?.(value);
  }

  function handleCancel() {
    void setQ(null);
    if (inputRef.current) inputRef.current.value = "";
    onCancel?.();
  }

  return (
    <div className={compact ? "" : "flex flex-col items-center"}>
      <form
        className={`w-full ${compact ? "max-w-none" : "max-w-2xl"}rounded-2xl border border-border bg-background shadow-[0_4px_24px_rgba(0,0,0,0.08)] transition-shadow hover:shadow-[0_4px_32px_rgba(0,0,0,0.12)] dark:shadow-[0_4px_24px_rgba(0,0,0,0.32)] dark:hover:shadow-[0_4px_32px_rgba(0,0,0,0.44)]`}
        onSubmit={handleSubmit}
      >
        <div className="flex items-center gap-2 px-4 py-3">
          {isLoading ? (
            <Loader2 className="size-5 shrink-0 animate-spin text-muted-foreground" />
          ) : (
            <Search className="size-5 shrink-0 text-muted-foreground" />
          )}
          <input
            autoComplete="off"
            className="min-w-0 flex-1 bg-transparent text-base outline-none placeholder:text-muted-foreground"
            defaultValue={q}
            name="q"
            placeholder="Опишите момент, мотив или сцену..."
            ref={inputRef}
          />
          {isLoading && onCancel ? (
            <Button
              className="shrink-0 rounded-xl"
              onClick={handleCancel}
              size="sm"
              type="button"
              variant="ghost"
            >
              <X className="mr-1 size-4" />
              Стоп
            </Button>
          ) : (
            <Button
              className="shrink-0 rounded-xl"
              disabled={isLoading}
              size="sm"
              type="submit"
            >
              Найти
            </Button>
          )}
        </div>
      </form>
    </div>
  );
}
