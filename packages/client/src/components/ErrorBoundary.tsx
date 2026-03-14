import type { ErrorComponentProps } from "@tanstack/react-router";
import {
  ErrorComponent,
  Link,
  rootRouteId,
  useMatch,
  useRouter,
} from "@tanstack/react-router";
import { Button } from "@/components/ui/button";

export function ErrorBoundary(props: ErrorComponentProps) {
  const router = useRouter();
  const isRoot = useMatch({
    strict: false,
    select: (state) => state.id === rootRouteId,
  });

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 px-4">
      <ErrorComponent error={props.error} />
      <div className="flex gap-2">
        <Button
          onClick={() => router.invalidate()}
          size="sm"
          type="button"
          variant="outline"
        >
          Попробовать ещё раз
        </Button>
        {isRoot ? (
          <Button asChild size="sm">
            <Link to="/">На главную</Link>
          </Button>
        ) : (
          <Button onClick={() => window.history.back()} size="sm" type="button">
            Назад
          </Button>
        )}
      </div>
    </div>
  );
}
