import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { api } from "../lib/api";
import type { AdminOverview, Donation, DonationStats, NgoStats } from "../lib/types";
import { categoryLabel, quantityLabel, timeAgo } from "../lib/format";
import { StatCard } from "../components/StatCard";
import { StatusBadge } from "../components/StatusBadge";
import { EmptyState } from "../components/EmptyState";
import { PageSpinner } from "../components/Spinner";

function DonorDashboard() {
  const navigate = useNavigate();
  const [stats, setStats] = useState<DonationStats | null>(null);
  const [donations, setDonations] = useState<Donation[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.myDonationStats(), api.myDonations()])
      .then(([s, d]) => {
        setStats(s);
        setDonations(d);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <PageSpinner />;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h2>Donor Dashboard</h2>
          <p className="muted">Post surplus food and let matching find the right NGO.</p>
        </div>
        <button className="btn btn-primary" onClick={() => navigate("/donations/new")}>
          ＋ Post a donation
        </button>
      </div>

      <div className="stat-grid">
        <StatCard label="Active donations" value={stats?.active_donations ?? 0} accent="amber" />
        <StatCard label="Completed" value={stats?.completed_donations ?? 0} accent="blue" />
        <StatCard label="Meals donated" value={stats?.meals_donated ?? 0} accent="green" />
        <StatCard label="People helped" value={stats?.people_helped ?? 0} accent="violet" />
      </div>

      <div className="card">
        <div className="card-header">
          <h3>Recent donations</h3>
          <Link to="/donations" className="link">
            View all →
          </Link>
        </div>
        {donations.length === 0 ? (
          <EmptyState
            title="No donations yet"
            body="Post your first surplus food donation to start matching."
            action={
              <button className="btn btn-primary" onClick={() => navigate("/donations/new")}>
                Post a donation
              </button>
            }
          />
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Food</th>
                  <th>Quantity</th>
                  <th>Status</th>
                  <th>Posted</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {donations.slice(0, 6).map((d) => (
                  <tr key={d.id} className="clickable" onClick={() => navigate(`/donations/${d.id}`)}>
                    <td>
                      <strong>{d.food_name}</strong>
                      <div className="muted small">{categoryLabel(d.food_category)}</div>
                    </td>
                    <td>{quantityLabel(d.quantity_value, d.quantity_unit)}</td>
                    <td>
                      <StatusBadge status={d.status} />
                    </td>
                    <td>{timeAgo(d.created_at)}</td>
                    <td className="td-arrow">→</td>
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

function NgoDashboard() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [stats, setStats] = useState<NgoStats | null>(null);
  const [available, setAvailable] = useState<Awaited<ReturnType<typeof api.ngoAvailable>>>([]);
  const [loading, setLoading] = useState(true);

  const verified = user?.ngo_profile?.verification_status === "verified";

  useEffect(() => {
    if (!verified) {
      setLoading(false);
      return;
    }
    Promise.all([api.ngoStats(), api.ngoAvailable()])
      .then(([s, a]) => {
        setStats(s);
        setAvailable(a);
      })
      .catch(() => undefined)
      .finally(() => setLoading(false));
  }, [verified]);

  if (loading) return <PageSpinner />;

  if (!verified) {
    return (
      <div className="page">
        <h2>NGO Dashboard</h2>
        <div className="card banner-warn">
          <h3>Your NGO is pending verification</h3>
          <p className="muted">
            An admin needs to verify your organisation before you can view and accept
            donations. Check back shortly.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h2>NGO Dashboard</h2>
          <p className="muted">Browse available donations matched to your capacity.</p>
        </div>
        <button className="btn btn-primary" onClick={() => navigate("/ngo/available")}>
          Browse available
        </button>
      </div>

      <div className="stat-grid">
        <StatCard label="Available donations" value={stats?.available_donations ?? 0} accent="amber" />
        <StatCard label="Accepted" value={stats?.accepted_donations ?? 0} accent="blue" />
        <StatCard label="Meals received" value={stats?.meals_received ?? 0} accent="green" />
        <StatCard label="People served" value={stats?.people_served ?? 0} accent="violet" />
      </div>

      <div className="card">
        <div className="card-header">
          <h3>Offered donations</h3>
          <Link to="/ngo/available" className="link">
            View all →
          </Link>
        </div>
        {available.length === 0 ? (
          <EmptyState title="No offers right now" body="New donations will appear here as they're posted." />
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Food</th>
                  <th>Quantity</th>
                  <th>Donor</th>
                  <th>Distance</th>
                  <th>Match</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {available.slice(0, 6).map((a) => (
                  <tr key={a.match_request_id} className="clickable" onClick={() => navigate("/ngo/available")}>
                    <td>
                      <strong>{a.food_name}</strong>
                      <div className="muted small">{categoryLabel(a.food_category)}</div>
                    </td>
                    <td>{quantityLabel(a.quantity_value, a.quantity_unit)}</td>
                    <td>{a.donor_name ?? "—"}</td>
                    <td>{a.distance_km} km</td>
                    <td>{a.match_percent}%</td>
                    <td className="td-arrow">→</td>
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

function AdminDashboard() {
  const [overview, setOverview] = useState<AdminOverview | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .adminOverview()
      .then(setOverview)
      .catch(() => undefined)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <PageSpinner />;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h2>Admin Dashboard</h2>
          <p className="muted">Platform overview at a glance.</p>
        </div>
      </div>

      <div className="stat-grid">
        <StatCard label="Restaurants" value={overview?.stats.total_restaurants ?? 0} accent="amber" />
        <StatCard label="Verified NGOs" value={overview?.stats.verified_ngos ?? 0} accent="green" />
        <StatCard label="Pending NGOs" value={overview?.stats.pending_ngos ?? 0} accent="violet" />
        <StatCard label="Total donations" value={overview?.stats.total_donations ?? 0} accent="blue" />
        <StatCard label="Meals redistributed" value={overview?.stats.meals_redistributed ?? 0} accent="green" />
      </div>

      <div className="card">
        <div className="card-header">
          <h3>Donation volume (6 months)</h3>
        </div>
        <BarChart data={overview?.donation_volume ?? []} />
      </div>

      <div className="card">
        <div className="card-header">
          <h3>Recent activity</h3>
        </div>
        {!overview || overview.recent_activity.length === 0 ? (
          <EmptyState title="No activity yet" />
        ) : (
          <ul className="activity-list">
            {overview.recent_activity.slice(0, 10).map((a) => (
              <li key={`${a.type}-${a.id}`}>
                <div className="activity-dot" data-type={a.type} />
                <div className="activity-text">
                  <span>
                    <strong>{a.actor}</strong> · {a.subject}
                  </span>
                  <StatusBadge status={a.status} />
                </div>
                <span className="muted small">{timeAgo(a.created_at)}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export function BarChart({ data }: { data: { label: string; value: number }[] }) {
  const max = Math.max(1, ...data.map((d) => d.value));
  return (
    <div className="bar-chart">
      {data.map((d) => (
        <div className="bar-col" key={d.label} title={`${d.label}: ${d.value}`}>
          <div className="bar-fill" style={{ height: `${Math.max(3, (d.value / max) * 100)}%` }} />
          <div className="bar-label">{d.label}</div>
        </div>
      ))}
    </div>
  );
}

export function DashboardPage() {
  const { user } = useAuth();
  if (!user) return null;
  if (user.role === "donor") return <DonorDashboard />;
  if (user.role === "ngo") return <NgoDashboard />;
  return <AdminDashboard />;
}
