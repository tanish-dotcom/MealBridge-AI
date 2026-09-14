import { useCallback, useEffect, useState } from "react";
import { api } from "../lib/api";
import { useToast } from "../auth/ToastContext";
import type { AcceptedDonation } from "../lib/types";
import { categoryLabel, formatDate, quantityLabel, timeAgo } from "../lib/format";
import { StatusBadge } from "../components/StatusBadge";
import { EmptyState } from "../components/EmptyState";
import { PageSpinner, ButtonSpinner } from "../components/Spinner";

export function NgoAcceptedPage() {
  const { error: showError, success } = useToast();
  const [items, setItems] = useState<AcceptedDonation[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(() => {
    return api
      .ngoAccepted()
      .then(setItems)
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const confirmPickup = async (donationId: string) => {
    setBusyId(donationId);
    try {
      const res = await api.confirmPickup(donationId);
      success(res.status === "completed" ? "Donation completed!" : "Pickup confirmed.");
      await load();
    } catch (err) {
      showError(err instanceof Error ? err.message : "Could not confirm pickup.");
    } finally {
      setBusyId(null);
    }
  };

  if (loading) return <PageSpinner />;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h2>Accepted Donations</h2>
          <p className="muted">Donations your NGO has committed to picking up.</p>
        </div>
      </div>

      {items.length === 0 ? (
        <div className="card">
          <EmptyState title="No accepted donations yet" body="Accept an offer from the Available tab to see it here." />
        </div>
      ) : (
        <div className="card">
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Food</th>
                  <th>Quantity</th>
                  <th>Donor</th>
                  <th>Status</th>
                  <th>Best before</th>
                  <th>Accepted</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {items.map((d) => {
                  const done = d.completed_by_donor && d.completed_by_ngo;
                  const needsConfirm = (d.status === "matched" || d.status === "picked_up") && !d.completed_by_ngo;
                  return (
                    <tr key={d.donation_id}>
                      <td>
                        <strong>{d.food_name}</strong>
                        <div className="muted small">{categoryLabel(d.food_category)}</div>
                      </td>
                      <td>{quantityLabel(d.quantity_value, d.quantity_unit)}</td>
                      <td>{d.donor_name ?? "—"}</td>
                      <td>
                        <StatusBadge status={d.status} />
                        {d.completed_by_donor && !d.completed_by_ngo && (
                          <div className="muted small">Donor confirmed ✓</div>
                        )}
                      </td>
                      <td>{formatDate(d.best_before)}</td>
                      <td>{timeAgo(d.created_at)}</td>
                      <td>
                        {done ? (
                          <span className="badge badge-green">Completed ✓</span>
                        ) : needsConfirm ? (
                          <button
                            className="btn btn-primary btn-sm"
                            onClick={() => confirmPickup(d.donation_id)}
                            disabled={busyId !== null}
                          >
                            {busyId === d.donation_id && <ButtonSpinner />} Confirm pickup
                          </button>
                        ) : (
                          <span className="badge badge-gray">Pending</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
