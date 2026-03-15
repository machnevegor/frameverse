import type { CSSProperties } from "react";

interface ShinyTextProps {
  text: string;
  className?: string;
  /** Sweep speed in seconds. Default: 3 */
  speed?: number;
  disabled?: boolean;
}

/**
 * Shiny sweep text — inspired by reactbits.dev/text-animations/shiny-text
 *
 * Uses a two-layer gradient clipped to text:
 *   1. base color layer (matches foreground)
 *   2. bright shimmer band that sweeps across
 */
export function ShinyText({
  text,
  className = "",
  speed = 3,
  disabled = false,
}: ShinyTextProps) {
  const style: CSSProperties = {
    // The shimmer band sweeps over a base that reads as normal text color
    backgroundImage:
      "linear-gradient(120deg, var(--color-foreground) 40%, oklch(0.95 0 0 / 0.9) 50%, var(--color-foreground) 60%)",
    backgroundSize: "250% 100%",
    WebkitBackgroundClip: "text",
    backgroundClip: "text",
    color: "transparent",
    animationDuration: `${speed}s`,
  };

  return (
    <span
      className={`inline-block ${disabled ? "text-foreground" : "animate-shiny"} ${className}`}
      style={disabled ? undefined : style}
    >
      {text}
    </span>
  );
}
