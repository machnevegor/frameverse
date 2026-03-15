// Inline SVG component derived from public/favicon.svg (lucide-send-to-back)
// Uses currentColor so it always matches the surrounding text color.
export function FrameverseLogo({
  className = "",
  size = 18,
}: {
  className?: string;
  size?: number;
}) {
  return (
    <svg
      aria-hidden="true"
      className={className}
      fill="none"
      height={size}
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth="2"
      viewBox="0 0 24 24"
      width={size}
      xmlns="http://www.w3.org/2000/svg"
    >
      <rect height="8" rx="2" width="8" x="14" y="14" />
      <rect height="8" rx="2" width="8" x="2" y="2" />
      <path d="M7 14v1a2 2 0 0 0 2 2h1" />
      <path d="M14 7h1a2 2 0 0 1 2 2v1" />
    </svg>
  );
}
