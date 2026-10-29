import { useEffect, useState, type ReactNode } from "react";

interface StatCardProps {
  label: string;
  value: ReactNode;
  icon?: ReactNode;
  accent?: "green" | "amber" | "blue" | "violet";
  delay?: number;
  hint?: ReactNode;
}

const ACCENTS: Record<string, string> = {
  green: "stat-green",
  amber: "stat-amber",
  blue: "stat-blue",
  violet: "stat-violet",
};

function useCountUp(value: number, duration = 850) {
  const [display, setDisplay] = useState(0);

  useEffect(() => {
    if (!Number.isFinite(value)) return;
    const reduceMotion =
      typeof window !== "undefined" &&
      window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (reduceMotion) {
      setDisplay(value);
      return;
    }

    let frame = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplay(value * eased);
      if (progress < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [value, duration]);

  return display;
}

export function StatCard({
  label,
  value,
  icon,
  accent = "green",
  delay = 0,
  hint,
}: StatCardProps) {
  const isNumber = typeof value === "number";
  const animated = useCountUp(isNumber ? (value as number) : 0);
  const rendered = isNumber ? Math.round(animated).toLocaleString() : value;

  return (
    <div
      className={`stat-card stat-card-${accent} anim-up`}
      style={{ animationDelay: `${delay}ms` }}
    >
      {icon && <div className={`stat-icon ${ACCENTS[accent] ?? ACCENTS.green}`}>{icon}</div>}
      <div className="stat-body">
        <div className="stat-value">{rendered}</div>
        <div className="stat-label">{label}</div>
        {hint && <div className="stat-hint">{hint}</div>}
      </div>
    </div>
  );
}
