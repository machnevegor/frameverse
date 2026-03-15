"use client";

import { Link, useRouterState } from "@tanstack/react-router";
import ThemeToggle from "./ThemeToggle";

export default function Header() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  const isHome = pathname === "/";
  const isDashboard = pathname.startsWith("/dashboard");

  return (
    <header className="sticky top-0 z-50 border-b bg-background/80 px-4 text-muted-foreground backdrop-blur-md">
      {/*
        Desktop (sm+): 3-column grid — logo | nav | theme
        Mobile:        row 1: logo + theme  |  row 2: nav (full width)
      */}
      <div className="page-wrap grid grid-cols-[1fr_auto] items-center gap-x-3 py-3 sm:grid-cols-[1fr_auto_1fr] sm:py-4">
        {/* Col 1 — Logo (both) */}
        <div className="flex items-center">
          <Link
            className="inline-flex items-center rounded-full border border-border bg-background px-3 py-1.5 font-medium text-foreground text-sm no-underline shadow-[0_8px_22px_rgba(0,0,0,0.04)] transition hover:border-foreground/25"
            search={(prev) => ({ ...prev, q: undefined })}
            to="/"
          >
            фрейм вёрс
          </Link>
        </div>

        {/* Col 3 — ThemeToggle right (both) */}
        <div className="flex items-center justify-end sm:order-3">
          <ThemeToggle />
        </div>

        {/* Col 2 — Nav: center on desktop, full-width second row on mobile */}
        <nav className="col-span-2 flex items-center gap-4 py-1 text-sm sm:order-2 sm:col-span-1 sm:justify-center sm:py-0">
          {!isHome && (
            <Link
              activeOptions={{ exact: true }}
              activeProps={{ className: "text-foreground font-medium" }}
              className="transition hover:text-foreground"
              to="/"
            >
              Поиск
            </Link>
          )}
          {!isDashboard && (
            <Link
              activeProps={{ className: "text-foreground font-medium" }}
              className="transition hover:text-foreground"
              to="/dashboard"
            >
              Дашборд
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}
