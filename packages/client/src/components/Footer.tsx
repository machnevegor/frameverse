import { GithubIcon } from "lucide-react";
import { FrameverseLogo } from "#/shared/ui/FrameverseLogo";

export default function Footer() {
  return (
    <footer className="border-t px-4 py-5 text-muted-foreground">
      <div className="page-wrap flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FrameverseLogo className="opacity-40" size={16} />
          <span className="font-medium text-foreground text-sm">
            фрейм вёрс
          </span>
        </div>
        <a
          aria-label="GitHub"
          className="transition hover:text-foreground"
          href="https://github.com/machnevegor/frameverse"
          rel="noreferrer"
          target="_blank"
        >
          <GithubIcon className="size-4" />
        </a>
      </div>
    </footer>
  );
}
