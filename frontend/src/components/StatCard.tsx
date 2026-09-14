import type { ReactNode } from "react";

interface StatCardProps {
  label: string;
  value: ReactNode;
  icon?: ReactNode;
  accent?: "green" | "amber" | "blue" | "violet";
}

const ACCENTS: Record<string, string> = {
  green: "stat-green",
  amber: "stat-amber",
  blue: "stat-blue",
  violet: "stat-violet",
};

export function StatCard({ label, value, icon, accent = "green" }: StatCardProps) {
  return (
    <div className="stat-card">
      {icon && <div className={`stat-icon ${ACCENTS[accent] ?? ACCENTS.green}`}>{icon}</div>}
      <div className="stat-body">
        <div className="stat-value">{value}</div>
        <div className="stat-label">{label}</div>
      </div>
    </div>
  );
}
