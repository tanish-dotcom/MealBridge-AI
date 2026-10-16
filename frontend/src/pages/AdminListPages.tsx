import { useCallback, useEffect, useState } from "react";
import { api } from "../lib/api";
import { useToast } from "../auth/ToastContext";
import type { AdminDonation, AdminNgo, AdminRestaurant } from "../lib/types";
import { categoryLabel, formatDate, quantityLabel, timeAgo } from "../lib/format";
import { StatusBadge } from "../components/StatusBadge";
import { EmptyState } from "../components/EmptyState";
import { PageSpinner, ButtonSpinner } from "../components/Spinner";

function useAdminData<T>(fetcher: () => Promise<T>) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(() => fetcher().then(setData).catch(() => setData(null)), [fetcher]);

  useEffect(() => {
    let active = true;
    setLoading(true);
    fetcher()
      .then((result) => active && setData(result))
      .catch(() => active && setData(null))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [fetcher]);

  return { data, loading, reload };
}

export function AdminRestaurantsPage() {
  const { error: showError, success } = useToast();
  const { data, loading, reload } = useAdminData(api.adminRestaurants);
  const [busyId, setBusyId] = useState<string | null>(null);

  const decide = async (restaurant: AdminRestaurant, verified: boolean) => {
    setBusyId(restaurant.id);
    try {
      if (verified) {
        await api.verifyRestaurant(restaurant.id);
        success("Restaurant verified.");
      } else {
        await api.unverifyRestaurant(restaurant.id);
        success("Restaurant unverified.");
      }
      await reload();
    } catch (err) {
      showError(err instanceof Error ? err.message : "Action failed.");
    } finally {
      setBusyId(null);
    }
  };

  if (loading) return <PageSpinner />;
  const rows = data ?? [];
  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h2>Restaurants</h2>
          <p className="muted">Registered donor restaurants on the platform.</p>
        </div>
      </div>
      <div className="card">
        {rows.length === 0 ? (
          <EmptyState title="No restaurants registered" />
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Restaurant</th>
                  <th>Owner</th>
                  <th>Email</th>
                  <th>Phone</th>
                  <th>City</th>
                  <th>Status</th>
                  <th>Joined</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r: AdminRestaurant) => (
                  <tr key={r.id}>
                    <td>
                      <strong>{r.restaurant_name}</strong>
                    </td>
                    <td>{r.owner_name}</td>
                    <td>{r.email}</td>
                    <td>{r.phone}</td>
                    <td>{r.city ?? "—"}</td>
                    <td>
                      <span className={`badge ${r.is_verified ? "badge-green" : "badge-gray"}`}>
                        {r.is_verified ? "Verified" : "Unverified"}
                      </span>
                    </td>
                    <td>{formatDate(r.created_at)}</td>
                    <td>
                      <div className="donation-actions">
                        {r.is_verified ? (
                          <button
                            className="btn btn-ghost btn-sm"
                            onClick={() => decide(r, false)}
                            disabled={busyId !== null}
                          >
                            {busyId === r.id && <ButtonSpinner />} Unverify
                          </button>
                        ) : (
                          <button
                            className="btn btn-primary btn-sm"
                            onClick={() => decide(r, true)}
                            disabled={busyId !== null}
                          >
                            {busyId === r.id && <ButtonSpinner />} Verify
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

export function AdminNgosPage() {
  const { error: showError, success } = useToast();
  const { data, loading, reload } = useAdminData(api.adminNgos);
  const [busyId, setBusyId] = useState<string | null>(null);

  const decide = async (ngo: AdminNgo, action: "approve" | "reject") => {
    setBusyId(ngo.id);
    try {
      if (action === "approve") {
        await api.approveNgo(ngo.id);
        success("NGO verified.");
      } else {
        await api.rejectNgo(ngo.id);
        success("NGO rejected.");
      }
      await reload();
    } catch (err) {
      showError(err instanceof Error ? err.message : "Action failed.");
    } finally {
      setBusyId(null);
    }
  };

  if (loading) return <PageSpinner />;
  const rows = data ?? [];
  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h2>NGOs</h2>
          <p className="muted">All registered partner organisations.</p>
        </div>
      </div>
      <div className="card">
        {rows.length === 0 ? (
          <EmptyState title="No NGOs registered" />
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Organisation</th>
                  <th>Contact</th>
                  <th>Email</th>
                  <th>Capacity</th>
                  <th>Reliability</th>
                  <th>City</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((n: AdminNgo) => (
                  <tr key={n.id}>
                    <td>
                      <strong>{n.org_name}</strong>
                      <div className="muted small">{n.registration_number}</div>
                    </td>
                    <td>{n.contact_person}</td>
                    <td>{n.email}</td>
                    <td>{n.capacity_meals_per_day ? `${n.capacity_meals_per_day}/day` : "—"}</td>
                    <td>{n.reliability_score ? n.reliability_score.toFixed(1) : "—"}</td>
                    <td>{n.city ?? "—"}</td>
                    <td>
                      <StatusBadge status={n.verification_status} />
                    </td>
                    <td>
                      <div className="donation-actions">
                        {n.verification_status !== "verified" && (
                          <button
                            className="btn btn-primary btn-sm"
                            onClick={() => decide(n, "approve")}
                            disabled={busyId !== null}
                          >
                            {busyId === n.id && <ButtonSpinner />} Verify
                          </button>
                        )}
                        {n.verification_status !== "rejected" && (
                          <button
                            className="btn btn-danger btn-sm"
                            onClick={() => decide(n, "reject")}
                            disabled={busyId !== null}
                          >
                            Reject
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

export function AdminDonationsPage() {
  const { data, loading } = useAdminData(api.adminDonations);
  if (loading) return <PageSpinner />;
  const rows = data ?? [];
  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h2>All Donations</h2>
          <p className="muted">Every donation posted across the platform.</p>
        </div>
      </div>
      <div className="card">
        {rows.length === 0 ? (
          <EmptyState title="No donations yet" />
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Food</th>
                  <th>Category</th>
                  <th>Quantity</th>
                  <th>Donor</th>
                  <th>Status</th>
                  <th>City</th>
                  <th>Posted</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((d: AdminDonation) => (
                  <tr key={d.id}>
                    <td>
                      <strong>{d.food_name}</strong>
                    </td>
                    <td className="muted">{categoryLabel(d.food_category)}</td>
                    <td>{quantityLabel(d.quantity_value, d.quantity_unit)}</td>
                    <td>{d.donor ?? "—"}</td>
                    <td>
                      <StatusBadge status={d.status} />
                    </td>
                    <td>{d.city ?? "—"}</td>
                    <td>{timeAgo(d.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
