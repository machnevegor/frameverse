"use client";

import { Link, useRouterState } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import ThemeToggle from "./ThemeToggle";

export default function Header() {
  const [visible, setVisible] = useState(true);
  const [lastY, setLastY] = useState(0);
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  const isHome = pathname === "/";
  const isDashboard = pathname.startsWith("/dashboard");

  useEffect(() => {
    function onScroll() {
      const y = window.scrollY;
      setVisible(y < lastY || y < 60);
      setLastY(y);
    }
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [lastY]);

  return (
    <header
      className={`sticky top-0 z-50 border-b bg-background/80 px-4 text-muted-foreground backdrop-blur-md transition-transform duration-300 ${
        visible ? "translate-y-0" : "-translate-y-full"
      }`}
    >
      <nav className="page-wrap flex flex-wrap items-center gap-x-3 gap-y-2 py-3 sm:py-4">
        <h2 className="m-0 shrink-0 font-medium text-sm">
          <Link
            className="inline-flex items-center gap-2 text-foreground no-underline transition hover:opacity-80"
            to="/"
          >
            <span className="h-2 w-2 rounded-full bg-[linear-gradient(90deg,#56c6be,#7ed3bf)]" />
            фрейм вёрс
          </Link>
        </h2>

        <div className="ml-auto flex items-center gap-1.5 sm:ml-0 sm:gap-2">
          <ThemeToggle />
        </div>

        <div className="order-3 flex w-full flex-wrap items-center gap-x-4 gap-y-1 pb-1 text-sm sm:order-2 sm:w-auto sm:flex-nowrap sm:pb-0">
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
        </div>
      </nav>
    </header>
  );
}
