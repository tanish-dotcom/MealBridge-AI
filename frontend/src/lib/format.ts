// API values use stable keys; these maps keep their display names consistent.
const CATEGORY_LABELS: Record<string, string> = {
  hot_meals: "Hot Meals",
  packaged_food: "Packaged Food",
  bakery: "Bakery",
  fruits_vegetables: "Fruits & Vegetables",
  dairy: "Dairy",
  beverages: "Beverages",
  grains: "Grains",
  snacks: "Snacks",
  other: "Other",
};

const STATUS_LABELS: Record<string, string> = {
  pending_match: "Pending Match",
  awaiting_response: "Awaiting Response",
  matched: "Matched",
  picked_up: "Picked Up",
  completed: "Completed",
  unmatched: "Unmatched",
  cancelled: "Cancelled",
  expired: "Expired",
  pending: "Pending",
  verified: "Verified",
  rejected: "Rejected",
  suspended: "Suspended",
  offered: "Offered",
  accepted: "Accepted",
};

const UNIT_LABELS: Record<string, string> = {
  meals: "meals",
  kg: "kg",
  packets: "packets",
};

export function categoryLabel(value?: string | null): string {
  return (value && CATEGORY_LABELS[value]) || value || "Other";
}

export function statusLabel(value?: string | null): string {
  return (value && STATUS_LABELS[value]) || value || "Unknown";
}

export function unitLabel(value?: string | null): string {
  return (value && UNIT_LABELS[value]) || value || "";
}

const NAIVE_DATETIME = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/;
const HAS_OFFSET = /(?:Z|[+-]\d{2}:?\d{2})$/i;

/**
 * Parse an API timestamp into a Date. The backend stores times in UTC and may
 * serialize them without an explicit offset (SQLite); browsers would otherwise
 * read such strings as local time, showing the wrong "posted" time. Treat
 * offset-less datetimes as UTC so they localize correctly.
 */
export function parseApiDate(iso?: string | null): Date | null {
  if (!iso) return null;
  const normalized = NAIVE_DATETIME.test(iso) && !HAS_OFFSET.test(iso) ? `${iso}Z` : iso;
  const d = new Date(normalized);
  return Number.isNaN(d.getTime()) ? null : d;
}

export function formatDate(iso?: string | null): string {
  const d = parseApiDate(iso);
  if (!d) return "—";
  return d.toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export function formatDateTime(iso?: string | null): string {
  const d = parseApiDate(iso);
  if (!d) return "—";
  return d.toLocaleString(undefined, {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function timeAgo(iso?: string | null): string {
  const d = parseApiDate(iso);
  if (!d) return "—";
  const diff = Date.now() - d.getTime();
  const minutes = Math.floor(diff / 60000);
  // Use compact labels for recent activity and a calendar date for older items.
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  return formatDate(iso);
}

export function quantityLabel(value: number, unit: string): string {
  const v = Number(value);
  const fmt = v % 1 === 0 ? v.toFixed(0) : v.toFixed(2);
  return `${fmt} ${unitLabel(unit)}`;
}

export function initials(name?: string | null): string {
  if (!name) return "?";
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]!.toUpperCase())
    .join("");
}
