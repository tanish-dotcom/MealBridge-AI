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

export function formatDate(iso?: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export function formatDateTime(iso?: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString(undefined, {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function timeAgo(iso?: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  const diff = Date.now() - d.getTime();
  const minutes = Math.floor(diff / 60000);
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
