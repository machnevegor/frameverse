"use client";

import { Link, useRouterState } from "@tanstack/react-router";
import ThemeToggle from "./ThemeToggle";

export default function Header() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  const isHome = pathname === "/";
  const isDashboard = pathname.startsWith("/dashboard");

  return (
    <header className="sticky top-0 z-50 border-b bg-background/80 px-4 text-muted-foreground backdrop-blur-md">
      {/* Desktop: logo left | nav center | theme right
          Mobile:  logo left + theme right | nav full-width row below */}
      <div className="page-wrap grid grid-cols-[1fr_auto] items-center gap-x-3 gap-y-1 py-3 sm:grid-cols-[1fr_auto_1fr] sm:py-4">
        {/* Logo — left */}
        <div className="flex items-center">
          <Link
            className="inline-flex items-center gap-2 font-medium text-foreground text-sm no-underline transition hover:opacity-80"
            to="/"
          >
            <span className="h-2 w-2 rounded-full bg-[linear-gradient(90deg,#56c6be,#7ed3bf)]" />
            фрейм вёрс
          </Link>
        </div>

        {/* Nav — center (desktop only, hidden on mobile) */}
        <nav className="order-3 col-span-2 flex w-full items-center gap-4 pb-1 text-sm sm:order-2 sm:col-span-1 sm:w-auto sm:justify-center sm:pb-0">
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

        {/* Theme toggle — right */}
        <div className="flex items-center justify-end">
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
