import { Monitor, Moon, Sun } from "lucide-react";
import { useEffect } from "react";
import type { TernaryDarkMode } from "usehooks-ts";
import { useTernaryDarkMode } from "usehooks-ts";
import { ToggleGroup, ToggleGroupItem } from "#/components/ui/toggle-group";

interface Mode {
  value: TernaryDarkMode;
  Icon: React.ElementType;
  label: string;
}

const MODES: Mode[] = [
  { value: "system", Icon: Monitor, label: "Системная тема" },
  { value: "light", Icon: Sun, label: "Светлая тема" },
  { value: "dark", Icon: Moon, label: "Тёмная тема" },
];

export default function ThemeToggle() {
  const { isDarkMode, ternaryDarkMode, setTernaryDarkMode } =
    useTernaryDarkMode({
      initializeWithValue: false,
      localStorageKey: "theme",
    });

  useEffect(() => {
    document.documentElement.classList.toggle("dark", isDarkMode);
  }, [isDarkMode]);

  return (
    <ToggleGroup
      aria-label="Переключение темы"
      className="rounded-full border border-border bg-background p-1 shadow-[0_8px_22px_rgba(0,0,0,0.04)] print:hidden"
      onValueChange={(value: TernaryDarkMode) => {
        if (value) setTernaryDarkMode(value);
      }}
      spacing={1}
      type="single"
      value={ternaryDarkMode}
    >
      {MODES.map(({ value, Icon, label }) => (
        <ToggleGroupItem
          aria-label={label}
          className="size-8 rounded-full px-0 text-muted-foreground hover:text-foreground data-[state=on]:bg-muted data-[state=on]:text-foreground"
          key={value}
          value={value}
        >
          <Icon className="size-4" />
        </ToggleGroupItem>
      ))}
    </ToggleGroup>
  );
}
