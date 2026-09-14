import { useCallback, useEffect, useState } from "react";
import { api } from "../lib/api";
import { useToast } from "../auth/ToastContext";
import type { PendingVerification } from "../lib/types";
import { timeAgo } from "../lib/format";
import { EmptyState } from "../components/EmptyState";
import { PageSpinner, ButtonSpinner } from "../components/Spinner";

export function AdminVerificationsPage() {
  const { error: showError, success } = useToast();
  const [items, setItems] = useState<PendingVerification[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(() => {
    return api
      .pendingVerifications()
      .then(setItems)
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const decide = async (id: string, action: "approve" | "reject") => {
    setBusyId(id);
    try {
      if (action === "approve") {
        await api.approveNgo(id);
        success("NGO approved.");
      } else {
        await api.rejectNgo(id);
        success("NGO rejected.");
      }
      await load();
    } catch (err) {
      showError(err instanceof Error ? err.message : "Action failed.");
    } finally {
      setBusyId(null);
    }
  };

  if (loading) return <PageSpinner />;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h2>NGO Verifications</h2>
          <p className="muted">Review organisations requesting to join the platform.</p>
        </div>
      </div>

      {items.length === 0 ? (
        <div className="card">
          <EmptyState title="No pending verifications" body="All NGO requests have been reviewed." />
        </div>
      ) : (
        <div className="verif-grid">
          {items.map((n) => (
            <div className="card verif-card" key={n.id}>
              <div className="card-header">
                <h3>{n.org_name}</h3>
                <span className="badge badge-amber">Pending</span>
              </div>
              <dl className="detail-list">
                <dt>Registration</dt>
                <dd>{n.registration_number}</dd>
                <dt>Contact</dt>
                <dd>
                  {n.contact_person}
                  <div className="muted small">
                    {n.email} · {n.phone}
                  </div>
                </dd>
                <dt>Capacity</dt>
                <dd>{n.capacity_meals_per_day ? `${n.capacity_meals_per_day} meals/day` : "—"}</dd>
                <dt>Address</dt>
                <dd>
                  {n.address?.line1 ? `${n.address.line1}, ${n.address.city ?? ""}` : "—"}
                </dd>
                <dt>Requested</dt>
                <dd>{timeAgo(n.created_at)}</dd>
              </dl>
              {n.food_requirements.length > 0 && (
                <div className="tag-row" style={{ marginBottom: 12 }}>
                  {n.food_requirements.map((r) => (
                    <span key={r} className="tag">
                      {r}
                    </span>
                  ))}
                </div>
              )}
              <div className="donation-actions">
                <button
                  className="btn btn-primary btn-sm"
                  onClick={() => decide(n.id, "approve")}
                  disabled={busyId !== null}
                >
                  {busyId === n.id && <ButtonSpinner />} Approve
                </button>
                <button
                  className="btn btn-danger btn-sm"
                  onClick={() => decide(n.id, "reject")}
                  disabled={busyId !== null}
                >
                  Reject
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
