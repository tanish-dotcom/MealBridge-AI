import { statusLabel } from "../lib/format";

const TONE: Record<string, string> = {
  completed: "badge-green",
  verified: "badge-green",
  accepted: "badge-green",
  matched: "badge-green",
  picked_up: "badge-blue",
  awaiting_response: "badge-amber",
  pending: "badge-amber",
  pending_match: "badge-amber",
  offered: "badge-amber",
  active: "badge-green",
  cancelled: "badge-red",
  rejected: "badge-red",
  expired: "badge-gray",
  unmatched: "badge-gray",
  suspended: "badge-red",
};

export function StatusBadge({ status }: { status: string }) {
  const tone = TONE[status] ?? "badge-gray";
  return <span className={`badge ${tone}`}>{statusLabel(status)}</span>;
}
