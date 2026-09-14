import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import type { Donation } from "../lib/types";
import { categoryLabel, formatDate, quantityLabel, timeAgo } from "../lib/format";
import { StatusBadge } from "../components/StatusBadge";
import { EmptyState } from "../components/EmptyState";
import { PageSpinner } from "../components/Spinner";

export function DonationsPage() {
  const navigate = useNavigate();
  const [donations, setDonations] = useState<Donation[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .myDonations()
      .then(setDonations)
      .catch(() => undefined)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <PageSpinner />;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h2>My Donations</h2>
          <p className="muted">Track the lifecycle of every donation you've posted.</p>
        </div>
        <button className="btn btn-primary" onClick={() => navigate("/donations/new")}>
          ＋ Post a donation
        </button>
      </div>

      {donations.length === 0 ? (
        <div className="card">
          <EmptyState
            title="No donations yet"
            body="Post surplus food and our matching engine will connect you with verified NGOs."
            action={
              <button className="btn btn-primary" onClick={() => navigate("/donations/new")}>
                Post a donation
              </button>
            }
          />
        </div>
      ) : (
        <div className="card">
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Food</th>
                  <th>Category</th>
                  <th>Quantity</th>
                  <th>Status</th>
                  <th>Best before</th>
                  <th>Posted</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {donations.map((d) => (
                  <tr key={d.id} className="clickable" onClick={() => navigate(`/donations/${d.id}`)}>
                    <td>
                      <strong>{d.food_name}</strong>
                    </td>
                    <td className="muted">{categoryLabel(d.food_category)}</td>
                    <td>{quantityLabel(d.quantity_value, d.quantity_unit)}</td>
                    <td>
                      <StatusBadge status={d.status} />
                    </td>
                    <td>{formatDate(d.best_before)}</td>
                    <td>{timeAgo(d.created_at)}</td>
                    <td className="td-arrow">→</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
