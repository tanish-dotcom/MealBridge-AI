import { useCallback, useEffect, useState } from "react";
import { api } from "../lib/api";
import { useToast } from "../auth/ToastContext";
import type { AvailableDonation } from "../lib/types";
import { categoryLabel, quantityLabel, timeAgo } from "../lib/format";
import { EmptyState } from "../components/EmptyState";
import { PageSpinner, ButtonSpinner } from "../components/Spinner";

export function NgoAvailablePage() {
  const { error: showError, success } = useToast();
  const [items, setItems] = useState<AvailableDonation[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(() => {
    return api
      .ngoAvailable()
      .then(setItems)
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const respond = async (matchRequestId: string, action: "accept" | "reject") => {
    setBusyId(matchRequestId);
    try {
      const res = await api.ngoRespond(matchRequestId, action);
      success(action === "accept" ? "Donation accepted!" : "Offer declined.");
      void res;
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
          <h2>Available Donations</h2>
          <p className="muted">Donations offered to you by the matching engine.</p>
        </div>
      </div>

      {items.length === 0 ? (
        <div className="card">
          <EmptyState
            title="Nothing available right now"
            body="When a donor posts surplus food near you, it will appear here."
          />
        </div>
      ) : (
        <div className="donation-grid">
          {items.map((a) => (
            <div className="donation-card" key={a.match_request_id}>
              <div className="donation-card-top">
                <div>
                  <h3>{a.food_name}</h3>
                  <div className="muted small">{categoryLabel(a.food_category)}</div>
                </div>
                <span className="match-pct">{a.match_percent}%</span>
              </div>
              <div className="donation-meta">
                <span>🍽 {quantityLabel(a.quantity_value, a.quantity_unit)}</span>
                <span>📍 {a.distance_km} km</span>
                <span>⏳ {timeAgo(a.created_at)}</span>
              </div>
              <div className="donation-meta small muted">
                <span>Donor: {a.donor_name ?? "—"}</span>
                <span>~{a.quantity_in_meals} meals</span>
              </div>
              {a.notes && <p className="donation-notes">“{a.notes}”</p>}
              <div className="donation-actions">
                <button
                  className="btn btn-primary btn-sm"
                  onClick={() => respond(a.match_request_id, "accept")}
                  disabled={busyId !== null}
                >
                  {busyId === a.match_request_id && <ButtonSpinner />} Accept
                </button>
                <button
                  className="btn btn-ghost btn-sm"
                  onClick={() => respond(a.match_request_id, "reject")}
                  disabled={busyId !== null}
                >
                  Decline
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
