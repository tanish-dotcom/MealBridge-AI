import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, ApiError } from "../lib/api";
import { useToast } from "../auth/ToastContext";
import type { Directions, Donation, MatchResult } from "../lib/types";
import { categoryLabel, formatDateTime, quantityLabel } from "../lib/format";
import { StatusBadge } from "../components/StatusBadge";
import { EmptyState } from "../components/EmptyState";
import { PageSpinner, ButtonSpinner } from "../components/Spinner";

const CANCELABLE = new Set(["pending_match", "awaiting_response", "unmatched"]);
const PICKABLE = new Set(["matched", "picked_up"]);

export function DonationDetailPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const { error: showError, success } = useToast();
  const [donation, setDonation] = useState<Donation | null>(null);
  const [matches, setMatches] = useState<MatchResult | null>(null);
  const [directions, setDirections] = useState<Directions | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const d = await api.getDonation(id);
      setDonation(d);
      if (CANCELABLE.has(d.status)) {
        try {
          setMatches(await api.donationMatches(id));
        } catch (err) {
          if (err instanceof ApiError && err.status === 404) setMatches(null);
          else setMatches(null);
        }
      }
      if (PICKABLE.has(d.status)) {
        try {
          setDirections(await api.donationDirections(id));
        } catch {
          setDirections(null);
        }
      }
    } catch (err) {
      showError(err instanceof Error ? err.message : "Failed to load donation.");
      navigate("/donations");
    } finally {
      setLoading(false);
    }
  }, [id, navigate, showError]);

  useEffect(() => {
    void load();
  }, [load]);

  const doCancel = async () => {
    setBusy("cancel");
    try {
      await api.cancelDonation(id);
      success("Donation cancelled.");
      await load();
    } catch (err) {
      showError(err instanceof Error ? err.message : "Could not cancel.");
    } finally {
      setBusy(null);
    }
  };

  const doConfirmPickup = async () => {
    setBusy("pickup");
    try {
      const res = await api.confirmPickup(id);
      success(res.status === "completed" ? "Donation completed!" : "Pickup confirmed.");
      await load();
    } catch (err) {
      showError(err instanceof Error ? err.message : "Could not confirm pickup.");
    } finally {
      setBusy(null);
    }
  };

  if (loading || !donation) return <PageSpinner />;

  const completed = donation.completed_by_donor;

  return (
    <div className="page">
      <button className="btn btn-ghost btn-sm" onClick={() => navigate("/donations")}>
        ← Back to my donations
      </button>

      <div className="page-header">
        <div>
          <h2>{donation.food_name}</h2>
          <div className="chip-row">
            <StatusBadge status={donation.status} />
            <span className="muted">{categoryLabel(donation.food_category)}</span>
            <span className="muted">{quantityLabel(donation.quantity_value, donation.quantity_unit)}</span>
          </div>
        </div>
        <div className="chip-row">
          {CANCELABLE.has(donation.status) && (
            <button className="btn btn-danger" onClick={doCancel} disabled={busy !== null}>
              {busy === "cancel" && <ButtonSpinner />} Cancel donation
            </button>
          )}
          {PICKABLE.has(donation.status) && !completed && (
            <button className="btn btn-primary" onClick={doConfirmPickup} disabled={busy !== null}>
              {busy === "pickup" && <ButtonSpinner />} Confirm pickup
            </button>
          )}
          {PICKABLE.has(donation.status) && completed && (
            <span className="badge badge-green">You confirmed pickup ✓</span>
          )}
        </div>
      </div>

      <div className="detail-grid">
        <div className="card">
          <div className="card-header">
            <h3>Donation details</h3>
          </div>
          <dl className="detail-list">
            <dt>Posted</dt>
            <dd>{formatDateTime(donation.created_at)}</dd>
            <dt>Best before</dt>
            <dd>{formatDateTime(donation.best_before)}</dd>
            <dt>Pickup address</dt>
            <dd>
              {donation.address?.line1 || "—"}
              {donation.address?.city ? `, ${donation.address.city}` : ""}
            </dd>
            <dt>Notes</dt>
            <dd>{donation.notes || "—"}</dd>
          </dl>
          {donation.photos.length > 0 && (
            <div className="photo-strip">
              {donation.photos.map((p) => (
                <img key={p.id} src={p.url} alt="Food" />
              ))}
            </div>
          )}
        </div>

        <div className="card">
          <div className="card-header">
            <h3>Matching NGOs</h3>
          </div>
          {CANCELABLE.has(donation.status) ? (
            matches ? (
              <>
                <div className="top-match">
                  <div className="top-match-rank">TOP MATCH</div>
                  <div className="top-match-body">
                    <h4>{matches.top_match.ngo_name}</h4>
                    <div className="muted">{matches.top_match.contact_person ?? "—"}</div>
                    <div className="match-meta">
                      <span>{matches.top_match.match_percent}% match</span>
                      <span>{matches.top_match.distance_km} km away</span>
                      <span>~{matches.top_match.estimated_pickup_minutes} min pickup</span>
                    </div>
                    <div className="tag-row">
                      {matches.top_match.quality_tags.map((t) => (
                        <span key={t} className="tag">
                          {t}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
                {matches.alternatives.length > 0 && (
                  <>
                    <h4 className="alt-title">Alternatives</h4>
                    <ul className="alt-list">
                      {matches.alternatives.map((c) => (
                        <li key={c.ngo_id}>
                          <div>
                            <strong>{c.ngo_name}</strong>
                            <div className="muted small">
                              {c.distance_km} km · ~{c.estimated_pickup_minutes} min · {c.match_percent}% match
                            </div>
                          </div>
                          <div className="tag-row">
                            {c.quality_tags.slice(0, 2).map((t) => (
                              <span key={t} className="tag">
                                {t}
                              </span>
                            ))}
                          </div>
                        </li>
                      ))}
                    </ul>
                  </>
                )}
                <p className="muted small" style={{ marginTop: 12 }}>
                  Awaiting NGO responses. The first verified NGO to accept takes this donation.
                </p>
              </>
            ) : (
              <EmptyState title="No active matches yet" body="Matching is in progress. Check back soon." />
            )
          ) : (
            <EmptyState
              title={donation.status === "matched" || donation.status === "picked_up" || donation.status === "completed" ? "Match confirmed" : "No longer accepting offers"}
              body={
                donation.matched_ngo_id
                  ? "An NGO has accepted this donation. Track pickup below."
                  : "This donation is not currently accepting new offers."
              }
            />
          )}

          {directions && (
            <div className="directions-card">
              <h4>Directions</h4>
              <div className="match-meta">
                <span>🚗 {directions.distance_km} km</span>
                <span>⏱ ~{directions.duration_minutes} min</span>
                <span className="muted small">{directions.provider}</span>
              </div>
              {directions.steps.length > 0 && (
                <ol className="step-list">
                  {directions.steps.slice(0, 6).map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ol>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
