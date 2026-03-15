import { createFileRoute } from "@tanstack/react-router";
import { motion } from "motion/react";
import { parseAsString, useQueryState } from "nuqs";
import { useEffect, useRef } from "react";
import { SearchBar } from "#/features/search-scenes/SearchBar";
import { SearchResults } from "#/features/search-scenes/SearchResults";
import { SearchTimeline } from "#/features/search-scenes/SearchTimeline";
import { useAgentSearch } from "#/features/search-scenes/useAgentSearch";
import { FrameverseLogo } from "#/shared/ui/FrameverseLogo";
import { ShinyText } from "#/shared/ui/ShinyText";
import { SceneSidebar } from "#/widgets/scene-sidebar/SceneSidebar";

// Shared easing — expo-out feel, organic deceleration
const EASE: [number, number, number, number] = [0.25, 0.46, 0.45, 0.94];

// Parent orchestrates children sequentially
const pageVariants = {
  hidden: {},
  show: {
    transition: {
      staggerChildren: 0.11,
      delayChildren: 0.05,
    },
  },
};

// Each direct child of the page: fade + gentle rise
const blockVariants = {
  hidden: { opacity: 0, y: 18 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.55, ease: EASE },
  },
};

// Chips stagger within their container
const chipsContainerVariants = {
  hidden: {},
  show: {
    transition: {
      staggerChildren: 0.07,
      delayChildren: 0,
    },
  },
};

const chipVariants = {
  hidden: { opacity: 0, y: 6 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.38, ease: EASE },
  },
};

// Logo spins in as part of the hero block
const logoVariants = {
  hidden: { opacity: 0, rotate: -18, scale: 0.72 },
  show: {
    opacity: 1,
    rotate: 0,
    scale: 1,
    transition: { duration: 0.48, ease: EASE },
  },
};

export const Route = createFileRoute("/")({ component: HomePage });

function HomePage() {
  const [q, setQ] = useQueryState("q", parseAsString.withDefault(""));
  const { status, events, groups, summary, error, search, reset } =
    useAgentSearch();

  const isStreaming = status === "streaming";
  const isDone = status === "done";
  const isError = status === "error";

  const initialSearchDoneRef = useRef(false);
  useEffect(() => {
    if (!initialSearchDoneRef.current && q.trim()) {
      initialSearchDoneRef.current = true;
      search(q);
    }
  }, [q, search]);

  useEffect(() => {
    if (!q.trim()) reset();
  }, [q, reset]);

  const showSearchMode = q.trim().length > 0 || status !== "idle";

  function handleSearch(query: string) {
    void setQ(query);
    search(query);
  }

  function handleCancel() {
    reset();
    void setQ(null);
  }

  return (
    <main className="pb-16">
      <div className="content-container">
        {showSearchMode ? (
          <>
            <div className="py-6">
              <SearchBar
                compact
                isLoading={isStreaming}
                onCancel={handleCancel}
                onSearch={handleSearch}
              />
            </div>
            <SearchTimeline events={events} status={status} />
            {isDone && <SearchResults groups={groups} summary={summary} />}
            {isError && (
              <div className="py-8 text-center text-destructive text-sm">
                {error ?? "Произошла ошибка поиска"}
              </div>
            )}
          </>
        ) : (
          <motion.div
            animate="show"
            className="flex min-h-[calc(100vh-8rem)] flex-col items-center justify-center gap-10 py-16"
            initial="hidden"
            variants={pageVariants}
          >
            <motion.div className="text-center" variants={blockVariants}>
              <div className="mb-3 flex items-center justify-center gap-2">
                <motion.div
                  className="text-foreground/60"
                  variants={logoVariants}
                >
                  <FrameverseLogo size={18} />
                </motion.div>
                <ShinyText
                  className="island-kicker text-base"
                  speed={8}
                  text="фрейм вёрс"
                />
              </div>
              <h1 className="display-title mb-4 font-bold text-(--sea-ink) text-4xl leading-tight tracking-tight sm:text-5xl">
                Найди фильм по содержанию
              </h1>
              <p className="mx-auto max-w-md text-(--sea-ink-soft) text-base leading-relaxed sm:text-lg">
                Опишите сцену, реплику или атмосферу — система найдёт нужный
                момент по смыслу, а не по словам
              </p>
            </motion.div>

            <motion.div className="w-full max-w-2xl" variants={blockVariants}>
              <SearchBar isLoading={isStreaming} onSearch={handleSearch} />
            </motion.div>

            <motion.div
              className="flex flex-wrap justify-center gap-2"
              variants={chipsContainerVariants}
            >
              {HINT_QUERIES.map((hint) => (
                <HintChip key={hint} onSearch={handleSearch} text={hint} />
              ))}
            </motion.div>
          </motion.div>
        )}
      </div>

      {isDone && groups.length > 0 && (
        <SceneSidebar scenes={groups.flatMap((g) => g.scenes)} />
      )}
    </main>
  );
}

const HINT_QUERIES = [
  "брокеры обсуждают визитки",
  "драка в тёмном подвале",
  "машина выезжает из трейлера",
  "нью-йорк",
  "квартира, вечер, диалог мужчины и женщины, сигарета",
];

function HintChip({
  text,
  onSearch,
}: {
  text: string;
  onSearch: (q: string) => void;
}) {
  return (
    <motion.button
      className="rounded-full border border-border bg-background px-3 py-1.5 text-muted-foreground text-sm transition hover:border-primary/40 hover:text-foreground"
      onClick={() => onSearch(text)}
      type="button"
      variants={chipVariants}
      whileHover={{ scale: 1.04, transition: { duration: 0.18 } }}
      whileTap={{ scale: 0.97, transition: { duration: 0.1 } }}
    >
      {text}
    </motion.button>
  );
}
