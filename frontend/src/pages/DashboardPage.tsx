import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { api } from "../lib/api";
import type { AdminOverview, Donation, DonationStats, NgoStats, User } from "../lib/types";
import { categoryLabel, quantityLabel, timeAgo } from "../lib/format";
import { StatCard } from "../components/StatCard";
import { StatusBadge } from "../components/StatusBadge";
import { EmptyState } from "../components/EmptyState";
import { PageSpinner } from "../components/Spinner";
import {
  ArrowRightIcon,
  BellIcon,
  CheckCircleIcon,
  ClockIcon,
  HeartIcon,
  InboxIcon,
  LeafIcon,
  ListIcon,
  MapPinIcon,
  PackageIcon,
  PlusIcon,
  ShieldCheckIcon,
  SparklesIcon,
  StoreIcon,
  UsersIcon,
  UtensilsIcon,
} from "../components/Icons";

function greeting() {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

function displayName(user: User | null) {
  if (!user) return "there";
  return user.first_name || user.email?.split("@")[0] || "there";
}

function ImpactRing({ percent, label }: { percent: number; label: string }) {
  const safe = Math.max(0, Math.min(100, Math.round(percent)));
  return (
    <div
      className="impact-ring"
      style={{
        background: `conic-gradient(var(--green-600) ${safe}%, var(--ring-track) ${safe}% 100%)`,
      }}
    >
      <div className="impact-ring-inner">
        <strong>{safe}%</strong>
        <span>{label}</span>
      </div>
    </div>
  );
}

function ImpactMeter({
  label,
  value,
  max,
  tone = "green",
}: {
  label: string;
  value: number;
  max: number;
  tone?: "green" | "violet" | "blue";
}) {
  const percent = max > 0 ? Math.max(4, Math.min(100, Math.round((value / max) * 100))) : 4;
  return (
    <div className="impact-meter">
      <div className="impact-meter-head">
        <span>{label}</span>
        <strong>{value.toLocaleString()}</strong>
      </div>
      <div className="impact-meter-track">
        <span className={`impact-meter-fill tone-${tone}`} style={{ width: `${percent}%` }} />
      </div>
    </div>
  );
}

function DonorDashboard() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [stats, setStats] = useState<DonationStats | null>(null);
  const [donations, setDonations] = useState<Donation[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Fetch the donor's summary and recent activity together for one loading state.
    Promise.all([api.myDonationStats(), api.myDonations()])
      .then(([s, d]) => {
        setStats(s);
        setDonations(d);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <PageSpinner />;

  const active = stats?.active_donations ?? 0;
  const completed = stats?.completed_donations ?? 0;
  const meals = stats?.meals_donated ?? 0;
  const people = stats?.people_helped ?? 0;
  const total = active + completed;
  const completion = total > 0 ? (completed / total) * 100 : 0;

  return (
    <div className="page dashboard-page">
      <section className="dash-hero donor-hero anim-up">
        <span className="hero-glow hero-glow-a" aria-hidden />
        <span className="hero-glow hero-glow-b" aria-hidden />
        <div className="dash-hero-content">
          <span className="dash-eyebrow">
            <SparklesIcon width={14} height={14} /> {greeting()}, {displayName(user)}
          </span>
          <h1>
            Turn surplus into <span className="grad-text">shared meals</span>
          </h1>
          <p>
            Post today&apos;s surplus and let MealBridge AI connect it with the right verified
            NGO nearby.
          </p>
          <div className="dash-hero-actions">
            <button className="btn btn-primary btn-lg" onClick={() => navigate("/donations/new")}>
              <PlusIcon /> Post a donation
            </button>
            <Link to="/donations" className="btn btn-hero-ghost">
              View my donations <ArrowRightIcon />
            </Link>
          </div>
        </div>
        <div className="hero-art" aria-hidden>
          <div className="hero-plate">
            <UtensilsIcon width={32} height={32} />
          </div>
          <span className="hero-chip hero-chip-1">
            <LeafIcon width={13} height={13} /> Fresh surplus
          </span>
          <span className="hero-chip hero-chip-2">
            <HeartIcon width={13} height={13} /> NGO matched
          </span>
          <span className="hero-chip hero-chip-3">
            <CheckCircleIcon width={13} height={13} /> Pickup ready
          </span>
        </div>
      </section>

      <div className="stat-grid">
        <StatCard
          label="Active donations"
          value={active}
          accent="amber"
          icon={<ClockIcon />}
          delay={0}
          hint="Live now"
        />
        <StatCard
          label="Completed"
          value={completed}
          accent="blue"
          icon={<CheckCircleIcon />}
          delay={70}
          hint="Pickups finished"
        />
        <StatCard
          label="Meals donated"
          value={meals}
          accent="green"
          icon={<UtensilsIcon />}
          delay={140}
          hint="All time"
        />
        <StatCard
          label="People helped"
          value={people}
          accent="violet"
          icon={<UsersIcon />}
          delay={210}
          hint="Reached via NGOs"
        />
      </div>

      <div className="dash-grid">
        <div className="card anim-up" style={{ animationDelay: "120ms" }}>
          <div className="card-header">
            <h3>Recent donations</h3>
            <Link to="/donations" className="link">
              View all <ArrowRightIcon width={14} height={14} />
            </Link>
          </div>
          {donations.length === 0 ? (
            <EmptyState
              title="No donations yet"
              body="Post your first surplus food donation to start rescuing meals."
              action={
                <button className="btn btn-primary" onClick={() => navigate("/donations/new")}>
                  Post a donation
                </button>
              }
            />
          ) : (
            <ul className="dash-feed">
              {donations.slice(0, 6).map((donation, index) => (
                <li
                  key={donation.id}
                  className="dash-feed-item"
                  style={{ animationDelay: `${index * 55}ms` }}
                  onClick={() => navigate(`/donations/${donation.id}`)}
                >
                  <span className="feed-icon">
                    <UtensilsIcon />
                  </span>
                  <div className="feed-main">
                    <strong>{donation.food_name}</strong>
                    <span>
                      {categoryLabel(donation.food_category)} ·{" "}
                      {quantityLabel(donation.quantity_value, donation.quantity_unit)}
                    </span>
                  </div>
                  <StatusBadge status={donation.status} />
                  <span className="feed-time">{timeAgo(donation.created_at)}</span>
                  <ArrowRightIcon className="feed-arrow" />
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="dash-side">
          <div className="card impact-card anim-up" style={{ animationDelay: "200ms" }}>
            <div className="card-header">
              <h3>Your impact</h3>
              <span className="live-pill">Live</span>
            </div>
            <div className="impact-top">
              <ImpactRing percent={completion} label="completed" />
              <div className="impact-copy">
                <strong>{meals.toLocaleString()} meals</strong>
                <span>donated so far</span>
                <p className="muted small">
                  Every completed pickup becomes a warm meal for someone nearby.
                </p>
              </div>
            </div>
            <div className="impact-meters">
              <ImpactMeter label="People helped" value={people} max={Math.max(meals, people, 1)} />
              <ImpactMeter
                label="Completed pickups"
                value={completed}
                max={Math.max(total, 1)}
                tone="blue"
              />
            </div>
          </div>

          <div className="card quick-card anim-up" style={{ animationDelay: "280ms" }}>
            <div className="card-header">
              <h3>Quick actions</h3>
            </div>
            <div className="quick-list">
              <Link to="/donations/new" className="quick-item">
                <span className="quick-icon">
                  <PlusIcon />
                </span>
                <div>
                  <strong>Post new donation</strong>
                  <span>List surplus in under a minute</span>
                </div>
                <ArrowRightIcon />
              </Link>
              <Link to="/donations" className="quick-item">
                <span className="quick-icon">
                  <ListIcon />
                </span>
                <div>
                  <strong>Track donations</strong>
                  <span>Follow every pickup in real time</span>
                </div>
                <ArrowRightIcon />
              </Link>
              <Link to="/notifications" className="quick-item">
                <span className="quick-icon">
                  <BellIcon />
                </span>
                <div>
                  <strong>Notifications</strong>
                  <span>Stay on top of NGO responses</span>
                </div>
                <ArrowRightIcon />
              </Link>
            </div>
            <div className="ai-tip">
              <SparklesIcon />
              <p>
                <strong>AI tip:</strong> the model ranks NGOs by predicted acceptance, so your
                top match is always first.
              </p>
            </div>
          </div>
        </div>
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
      <div className="page dashboard-page">
        <section className="dash-hero verify-hero anim-up">
          <span className="hero-glow hero-glow-a" aria-hidden />
          <span className="hero-glow hero-glow-b" aria-hidden />
          <div className="dash-hero-content">
            <span className="dash-eyebrow">
              <ShieldCheckIcon width={14} height={14} /> Verification in progress
            </span>
            <h1>
              Almost there, <span className="grad-text">{displayName(user)}</span>
            </h1>
            <p>
              Our team is reviewing your organisation. Once verified you can browse and accept
              surplus food in your area.
            </p>
          </div>
          <div className="hero-art" aria-hidden>
            <div className="hero-plate">
              <ShieldCheckIcon width={34} height={34} />
            </div>
          </div>
        </section>

        <div className="card anim-up" style={{ animationDelay: "100ms" }}>
          <div className="verify-row">
            <span className="verify-icon">
              <ClockIcon width={26} height={26} />
            </span>
            <div>
              <h3>Your NGO is pending verification</h3>
              <p className="muted">
                An admin needs to verify your organisation before donations appear here. You
                will get a notification as soon as it is done.
              </p>
            </div>
          </div>
          <div className="verify-steps">
            <span className="verify-step done">
              <CheckCircleIcon /> Account created
            </span>
            <span className="verify-step active">
              <ClockIcon /> Admin review
            </span>
            <span className="verify-step">
              <InboxIcon /> Start accepting donations
            </span>
          </div>
        </div>
      </div>
    );
  }

  const openOffers = stats?.available_donations ?? 0;
  const accepted = stats?.accepted_donations ?? 0;
  const mealsReceived = stats?.meals_received ?? 0;
  const peopleServed = stats?.people_served ?? 0;
  const total = openOffers + accepted;
  const acceptRate = total > 0 ? (accepted / total) * 100 : 0;

  return (
    <div className="page dashboard-page">
      <section className="dash-hero ngo-hero anim-up">
        <span className="hero-glow hero-glow-a" aria-hidden />
        <span className="hero-glow hero-glow-b" aria-hidden />
        <div className="dash-hero-content">
          <span className="dash-eyebrow">
            <SparklesIcon width={14} height={14} /> {greeting()}, {displayName(user)}
          </span>
          <h1>
            Rescue food. <span className="grad-text">Feed more people.</span>
          </h1>
          <p>
            Fresh surplus matched to your capacity, distance and acceptance history by
            MealBridge AI.
          </p>
          <div className="dash-hero-actions">
            <button className="btn btn-primary btn-lg" onClick={() => navigate("/ngo/available")}>
              <InboxIcon /> Browse available
            </button>
            <Link to="/ngo/accepted" className="btn btn-hero-ghost">
              Accepted donations <ArrowRightIcon />
            </Link>
          </div>
        </div>
        <div className="hero-art" aria-hidden>
          <div className="hero-plate">
            <InboxIcon width={32} height={32} />
          </div>
          <span className="hero-chip hero-chip-1">
            <SparklesIcon width={13} height={13} /> AI ranked
          </span>
          <span className="hero-chip hero-chip-2">
            <MapPinIcon width={13} height={13} /> Nearby pickup
          </span>
          <span className="hero-chip hero-chip-3">
            <HeartIcon width={13} height={13} /> Ready to serve
          </span>
        </div>
      </section>

      <div className="stat-grid">
        <StatCard
          label="Open offers"
          value={openOffers}
          accent="amber"
          icon={<InboxIcon />}
          delay={0}
          hint="Waiting for you"
        />
        <StatCard
          label="Accepted"
          value={accepted}
          accent="blue"
          icon={<CheckCircleIcon />}
          delay={70}
          hint="Rescues confirmed"
        />
        <StatCard
          label="Meals received"
          value={mealsReceived}
          accent="green"
          icon={<PackageIcon />}
          delay={140}
          hint="All time"
        />
        <StatCard
          label="People served"
          value={peopleServed}
          accent="violet"
          icon={<UsersIcon />}
          delay={210}
          hint="Through your kitchens"
        />
      </div>

      <div className="dash-grid">
        <div className="card anim-up" style={{ animationDelay: "120ms" }}>
          <div className="card-header">
            <h3>Live offers</h3>
            <Link to="/ngo/available" className="link">
              View all <ArrowRightIcon width={14} height={14} />
            </Link>
          </div>
          {available.length === 0 ? (
            <EmptyState
              title="No offers right now"
              body="New donations will appear here as nearby restaurants post surplus."
            />
          ) : (
            <ul className="dash-feed">
              {available.slice(0, 6).map((offer, index) => (
                <li
                  key={offer.match_request_id}
                  className="dash-feed-item ngo-feed-item"
                  style={{ animationDelay: `${index * 55}ms` }}
                  onClick={() => navigate("/ngo/available")}
                >
                  <span className="feed-icon">
                    <InboxIcon />
                  </span>
                  <div className="feed-main">
                    <strong>{offer.food_name}</strong>
                    <span>
                      {categoryLabel(offer.food_category)} ·{" "}
                      {quantityLabel(offer.quantity_value, offer.quantity_unit)} ·{" "}
                      {offer.distance_km} km · {offer.donor_name ?? "Donor"}
                    </span>
                  </div>
                  <span className="match-pct">{offer.match_percent}%</span>
                  <span className="feed-time">{timeAgo(offer.created_at)}</span>
                  <ArrowRightIcon className="feed-arrow" />
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="dash-side">
          <div className="card impact-card anim-up" style={{ animationDelay: "200ms" }}>
            <div className="card-header">
              <h3>Community impact</h3>
              <span className="live-pill">Live</span>
            </div>
            <div className="impact-top">
              <ImpactRing percent={acceptRate} label="accept rate" />
              <div className="impact-copy">
                <strong>{mealsReceived.toLocaleString()} meals</strong>
                <span>received so far</span>
                <p className="muted small">
                  Your team turns rescued surplus into meals for people who need them most.
                </p>
              </div>
            </div>
            <div className="impact-meters">
              <ImpactMeter
                label="People served"
                value={peopleServed}
                max={Math.max(mealsReceived, peopleServed, 1)}
                tone="violet"
              />
              <ImpactMeter
                label="Accepted pickups"
                value={accepted}
                max={Math.max(total, 1)}
                tone="blue"
              />
            </div>
          </div>

          <div className="card quick-card anim-up" style={{ animationDelay: "280ms" }}>
            <div className="card-header">
              <h3>Quick actions</h3>
            </div>
            <div className="quick-list">
              <Link to="/ngo/available" className="quick-item">
                <span className="quick-icon">
                  <InboxIcon />
                </span>
                <div>
                  <strong>Browse offers</strong>
                  <span>Claim surplus near your kitchen</span>
                </div>
                <ArrowRightIcon />
              </Link>
              <Link to="/ngo/accepted" className="quick-item">
                <span className="quick-icon">
                  <CheckCircleIcon />
                </span>
                <div>
                  <strong>Accepted donations</strong>
                  <span>Track pickups and completion</span>
                </div>
                <ArrowRightIcon />
              </Link>
              <Link to="/settings" className="quick-item">
                <span className="quick-icon">
                  <StoreIcon />
                </span>
                <div>
                  <strong>Capacity settings</strong>
                  <span>Keep your profile fresh for better matches</span>
                </div>
                <ArrowRightIcon />
              </Link>
            </div>
            <div className="ai-tip">
              <SparklesIcon />
              <p>
                <strong>AI tip:</strong> offers are ranked by predicted acceptance probability,
                so the best-fit donation is always on top.
              </p>
            </div>
          </div>
        </div>
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
    <div className="page dashboard-page">
      <div className="page-header">
        <div>
          <h2>Admin Dashboard</h2>
          <p className="muted">Platform overview at a glance.</p>
        </div>
      </div>

      <div className="stat-grid">
        <StatCard
          label="Restaurants"
          value={overview?.stats.total_restaurants ?? 0}
          accent="amber"
          icon={<StoreIcon />}
          delay={0}
        />
        <StatCard
          label="Verified NGOs"
          value={overview?.stats.verified_ngos ?? 0}
          accent="green"
          icon={<ShieldCheckIcon />}
          delay={70}
        />
        <StatCard
          label="Pending NGOs"
          value={overview?.stats.pending_ngos ?? 0}
          accent="violet"
          icon={<ClockIcon />}
          delay={140}
        />
        <StatCard
          label="Total donations"
          value={overview?.stats.total_donations ?? 0}
          accent="blue"
          icon={<ListIcon />}
          delay={210}
        />
        <StatCard
          label="Meals redistributed"
          value={overview?.stats.meals_redistributed ?? 0}
          accent="green"
          icon={<UtensilsIcon />}
          delay={280}
        />
      </div>

      <div className="card anim-up" style={{ animationDelay: "120ms" }}>
        <div className="card-header">
          <h3>Donation volume (6 months)</h3>
        </div>
        <BarChart data={overview?.donation_volume ?? []} />
      </div>

      <div className="card anim-up" style={{ animationDelay: "200ms" }}>
        <div className="card-header">
          <h3>Recent activity</h3>
        </div>
        {!overview || overview.recent_activity.length === 0 ? (
          <EmptyState title="No activity yet" />
        ) : (
          <ul className="activity-list">
            {overview.recent_activity.slice(0, 10).map((activity) => (
              <li key={`${activity.type}-${activity.id}`}>
                <div className="activity-dot" data-type={activity.type} />
                <div className="activity-text">
                  <span>
                    <strong>{activity.actor}</strong> · {activity.subject}
                  </span>
                  <StatusBadge status={activity.status} />
                </div>
                <span className="muted small">{timeAgo(activity.created_at)}</span>
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
