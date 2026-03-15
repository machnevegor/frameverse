import { queryOptions, useQuery } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { motion } from "motion/react";
import { parseAsString, useQueryState } from "nuqs";
import { SearchBar } from "#/features/search-scenes/SearchBar";
import { SearchResults } from "#/features/search-scenes/SearchResults";
import { searchScenes } from "#/shared/api/client";
import { SEARCH_SCENES_LIMIT } from "#/shared/config/constants";
import { FrameverseLogo } from "#/shared/ui/FrameverseLogo";
import { ShinyText } from "#/shared/ui/ShinyText";

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

const searchScenesQueryOptions = (q: string) =>
  queryOptions({
    queryKey: ["search", "scenes", q],
    queryFn: () => searchScenes({ query: q, limit: SEARCH_SCENES_LIMIT }),
    enabled: q.length > 0,
    staleTime: 30_000,
  });

export const Route = createFileRoute("/")({ component: HomePage });

function HomePage() {
  const [q] = useQueryState("q", parseAsString.withDefault(""));
  const { data: hits, isFetching } = useQuery(searchScenesQueryOptions(q));

  const hasQuery = q.trim().length > 0;

  return (
    <main className="pb-16">
      <div className="content-container">
      {hasQuery ? (
        <>
          <div className="py-6">
            <SearchBar compact isLoading={isFetching} />
          </div>
          <SearchResults hits={hits ?? []} isLoading={isFetching} />
        </>
      ) : (
        <motion.div
          animate="show"
          className="flex min-h-[calc(100vh-8rem)] flex-col items-center justify-center gap-10 py-16"
          initial="hidden"
          variants={pageVariants}
        >
          {/* Hero text */}
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

          {/* Search bar */}
          <motion.div className="w-full max-w-2xl" variants={blockVariants}>
            <SearchBar isLoading={isFetching} />
          </motion.div>

          {/* Hint chips */}
          <motion.div
            className="flex flex-wrap justify-center gap-2"
            variants={chipsContainerVariants}
          >
            {HINT_QUERIES.map((hint) => (
              <HintChip key={hint} text={hint} />
            ))}
          </motion.div>
        </motion.div>
      )}
      </div>
    </main>
  );
}

const HINT_QUERIES = [
  "герой спорит с боссом в офисе",
  "напряжённая сцена в подвале",
  "погоня по ночному городу",
  "прощание на вокзале под дождём",
];

function HintChip({ text }: { text: string }) {
  const [, setQ] = useQueryState("q", parseAsString.withDefault(""));
  return (
    <motion.button
      className="rounded-full border border-border bg-background px-3 py-1.5 text-muted-foreground text-sm transition hover:border-primary/40 hover:text-foreground"
      onClick={() => void setQ(text)}
      type="button"
      variants={chipVariants}
      whileHover={{ scale: 1.04, transition: { duration: 0.18 } }}
      whileTap={{ scale: 0.97, transition: { duration: 0.1 } }}
    >
      {text}
    </motion.button>
  );
}
