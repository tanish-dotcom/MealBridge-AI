import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../lib/api";
import { fetchTopNgoRecommendations } from "../api/ml";
import { useToast } from "../auth/ToastContext";
import type {
  Directions,
  Donation,
  MatchCandidate,
  MatchResult,
  MlRecommendation,
} from "../lib/types";
import { categoryLabel, formatDateTime, quantityLabel } from "../lib/format";
import { StatusBadge } from "../components/StatusBadge";
import { EmptyState } from "../components/EmptyState";
import { PageSpinner, ButtonSpinner } from "../components/Spinner";

const CANCELABLE = new Set(["pending_match", "awaiting_response", "unmatched"]);
const PICKABLE = new Set(["matched", "picked_up"]);

interface RecommendedNgo {
  ngo_id: string;
  ngo_name: string;
  contact_person?: string | null;
  score: number;
  distance_km: number;
  eta?: number;
  reasons: string[];
  acceptance_rate?: number;
  demand?: number;
  ml: boolean;
  offerStatus?: "offered" | "accepted";
}

export function DonationDetailPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const { error: showError, success } = useToast();
  const [donation, setDonation] = useState<Donation | null>(null);
  const [matches, setMatches] = useState<MatchResult | null>(null);
  const [mlSuggestions, setMlSuggestions] = useState<MlRecommendation[] | null>(null);
  const [directions, setDirections] = useState<Directions | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const d = await api.getDonation(id);
      setDonation(d);
      // Suggestions are only useful before a donation has been matched or closed.
      if (CANCELABLE.has(d.status)) {
        const [matchesResult, mlResult] = await Promise.allSettled([
          api.donationMatches(id),
          fetchTopNgoRecommendations(id),
        ]);
        setMatches(matchesResult.status === "fulfilled" ? matchesResult.value : null);
        setMlSuggestions(mlResult.status === "fulfilled" ? mlResult.value : null);
      } else {
        setMatches(null);
        setMlSuggestions(null);
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

  const doSendOffer = async (rec: RecommendedNgo) => {
    setBusy(`offer:${rec.ngo_id}`);
    try {
      await api.sendOffer(id, { ngo_id: rec.ngo_id, match_score: rec.score });
      success(`Offer sent to ${rec.ngo_name}.`);
      await load();
    } catch (err) {
      showError(err instanceof Error ? err.message : "Could not send offer.");
    } finally {
      setBusy(null);
    }
  };

  if (loading || !donation) return <PageSpinner />;

  const completed = donation.completed_by_donor;

  // The ML top-5 (already sorted by predicted acceptance) is the priority list.
  // Existing offers are merged in so "offer sent"/"accepted" state stays visible.
  const offerByNgo = new Map<string, MatchCandidate>();
  if (matches) {
    for (const candidate of [matches.top_match, ...matches.alternatives]) {
      offerByNgo.set(candidate.ngo_id, candidate);
    }
  }
  const acceptedNgoId = donation.matched_ngo_id ?? null;

  const withOfferState = (rec: Omit<RecommendedNgo, "contact_person" | "offerStatus">): RecommendedNgo => {
    const offer = offerByNgo.get(rec.ngo_id);
    return {
      ...rec,
      contact_person: offer?.contact_person ?? null,
      offerStatus: offer ? (rec.ngo_id === acceptedNgoId ? "accepted" : "offered") : undefined,
    };
  };

  const recommended: RecommendedNgo[] = [];
  const seenNgos = new Set<string>();

  for (const rec of mlSuggestions ?? []) {
    recommended.push(
      withOfferState({
        ngo_id: rec.ngo_id,
        ngo_name: rec.ngo_name,
        score: rec.match_score,
        distance_km: rec.distance_km,
        eta: rec.estimated_pickup_minutes,
        reasons: rec.reasons.length > 0 ? rec.reasons : offerByNgo.get(rec.ngo_id)?.quality_tags ?? [],
        acceptance_rate: rec.acceptance_rate,
        demand: rec.ngo_demand,
        ml: true,
      })
    );
    seenNgos.add(rec.ngo_id);
  }

  // Keep any outstanding offer visible even if it fell outside the ML top-5.
  for (const candidate of offerByNgo.values()) {
    if (seenNgos.has(candidate.ngo_id)) continue;
    recommended.push(
      withOfferState({
        ngo_id: candidate.ngo_id,
        ngo_name: candidate.ngo_name,
        score: candidate.match_percent,
        distance_km: candidate.distance_km,
        eta: candidate.estimated_pickup_minutes,
        reasons: candidate.quality_tags,
        ml: false,
      })
    );
    seenNgos.add(candidate.ngo_id);
  }

  const hasOffers = recommended.some((r) => r.offerStatus !== undefined);
  const hasMl = recommended.some((r) => r.ml);

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
            <h3>Recommended NGOs</h3>
            {hasMl && <span className="muted small">Top 5 by AI acceptance probability</span>}
          </div>

          {CANCELABLE.has(donation.status) ? (
            recommended.length > 0 ? (
              <>
                <ul className="alt-list">
                  {recommended.map((rec, index) => (
                    <li key={rec.ngo_id}>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div className="chip-row">
                          <strong>
                            {index + 1}. {rec.ngo_name}
                          </strong>
                          <span className="match-pct">{rec.score}% match</span>
                          {rec.offerStatus === "accepted" && (
                            <span className="badge badge-green">Accepted</span>
                          )}
                          {rec.offerStatus === "offered" && (
                            <span className="badge badge-blue">Offer sent</span>
                          )}
                          {rec.offerStatus === undefined && (
                            <button
                              className="btn btn-primary btn-sm"
                              onClick={() => doSendOffer(rec)}
                              disabled={busy !== null}
                            >
                              {busy === `offer:${rec.ngo_id}` && <ButtonSpinner />}
                              Send offer
                            </button>
                          )}
                        </div>
                        <div className="muted small">
                          {rec.distance_km} km away
                          {rec.eta !== undefined ? ` · ~${rec.eta} min pickup` : ""}
                          {rec.acceptance_rate !== undefined
                            ? ` · ${Math.round(rec.acceptance_rate * 100)}% acceptance`
                            : ""}
                          {rec.demand !== undefined ? ` · demand ${Math.round(rec.demand)} meals` : ""}
                        </div>
                        <div className="h-bar-track" style={{ marginTop: 6 }}>
                          <div className="h-bar-fill" style={{ width: `${rec.score}%` }} />
                        </div>
                        {rec.reasons.length > 0 && (
                          <div className="tag-row" style={{ marginTop: 6 }}>
                            {rec.reasons.map((reason) => (
                              <span key={reason} className="tag">
                                {reason}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </li>
                  ))}
                </ul>
                <p className="muted small" style={{ marginTop: 12 }}>
                  {hasOffers
                    ? "Offer sent — the first verified NGO to accept takes it. You can still send offers to others."
                    : "Pick an NGO above and send an offer — the first verified NGO to accept takes this donation."}
                  {hasMl ? " Match % is the model's predicted chance each NGO accepts." : ""}
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
