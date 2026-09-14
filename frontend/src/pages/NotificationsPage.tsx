import { useCallback, useEffect, useState } from "react";
import { api } from "../lib/api";
import type { NotificationItem } from "../lib/types";
import { timeAgo } from "../lib/format";
import { EmptyState } from "../components/EmptyState";
import { PageSpinner } from "../components/Spinner";

export function NotificationsPage() {
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    return api
      .notifications()
      .then(setItems)
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const markRead = async (id: string) => {
    await api.markNotificationRead(id).catch(() => undefined);
    setItems((prev) => prev.map((n) => (n.id === id ? { ...n, read_at: new Date().toISOString() } : n)));
  };

  if (loading) return <PageSpinner />;

  const unread = items.filter((n) => !n.read_at).length;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h2>Notifications</h2>
          <p className="muted">
            {unread > 0 ? `${unread} unread` : "You're all caught up"}
          </p>
        </div>
      </div>

      {items.length === 0 ? (
        <div className="card">
          <EmptyState title="No notifications" body="Updates about your donations and matches will appear here." />
        </div>
      ) : (
        <div className="card">
          <ul className="notif-list">
            {items.map((n) => (
              <li
                key={n.id}
                className={`notif-item ${n.read_at ? "" : "unread"}`}
                onClick={() => !n.read_at && markRead(n.id)}
              >
                <div className="notif-icon">{(n.type ?? "info").slice(0, 1).toUpperCase()}</div>
                <div className="notif-body">
                  <strong>{n.title}</strong>
                  <p>{n.body}</p>
                </div>
                <span className="muted small">{timeAgo(n.created_at)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
