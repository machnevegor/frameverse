import { Link } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";

export function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 px-4">
      <p className="text-muted-foreground text-sm">Страница не найдена</p>
      <div className="flex gap-2">
        <Button
          onClick={() => window.history.back()}
          size="sm"
          type="button"
          variant="outline"
        >
          Назад
        </Button>
        <Button asChild size="sm">
          <Link to="/">На главную</Link>
        </Button>
      </div>
    </div>
  );
}
