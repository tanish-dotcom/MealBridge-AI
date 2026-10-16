"""ML service: loads the trained Random Forest pipeline and turns a donation +
candidate NGOs into a ranked top-N recommendation list.

Model file: backend/storage/mealbridge_random_forest.pkl
(scikit-learn Pipeline: ColumnTransformer(OneHotEncoder 'food_type' + passthrough
numerics) -> RandomForestClassifier, binary target: 1 = NGO accepts the donation).

Feature contract (must match training):
    food_quantity, distance_km, ngo_capacity, ngo_demand,
    hours_remaining, acceptance_rate, food_type
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import joblib
import pandas as pd

logger = logging.getLogger(__name__)

# backend/app/services/ml_service.py -> parents[2] resolves to the backend directory.
MODEL_PATH = (
    Path(__file__).resolve().parents[2]
    / "storage"
    / "mealbridge_random_forest.pkl"
)

MODEL_NAME = MODEL_PATH.name

FEATURE_COLUMNS = [
    "food_quantity",
    "distance_km",
    "ngo_capacity",
    "ngo_demand",
    "hours_remaining",
    "acceptance_rate",
    "food_type",
]

NUMERIC_COLUMNS = [
    "food_quantity",
    "distance_km",
    "ngo_capacity",
    "ngo_demand",
    "hours_remaining",
    "acceptance_rate",
]

ALLOWED_FOOD_TYPES = {
    "Cooked",
    "Packaged",
    "Fruits",
    "Vegetables",
}

# Fallbacks used when a live DB value is missing (keeps the pipeline usable
# for NGOs that never filled in capacity / have no offer history yet).
DEFAULT_CAPACITY_MEALS = 100.0
DEFAULT_ACCEPTANCE_RATE = 0.7
DEFAULT_HOURS_REMAINING = 4.0
ACCEPTANCE_HISTORY_DAYS = 30
# Wider pool than the offer flow: the model needs enough candidates to pick a
# real top 5 after the capacity/demand eligibility filter.
ML_MIN_CANDIDATES = 15

# donation food_category -> model food_type vocabulary
CATEGORY_TO_FOOD_TYPE = {
    "hot_meals": "Cooked",
    "cooked": "Cooked",
    "fruits_vegetables": "Fruits",
    "packaged_food": "Packaged",
    "bakery": "Packaged",
    "dairy": "Packaged",
    "beverages": "Packaged",
    "grains": "Packaged",
    "snacks": "Packaged",
    "other": "Packaged",
}

FRUIT_KEYWORDS = ("fruit", "banana", "apple", "mango", "orange", "grape", "watermelon", "papaya")
VEG_KEYWORDS = ("vegetable", "spinach", "carrot", "beans", "cabbage", "cauliflower", "okra", "brinjal")


class ModelUnavailableError(RuntimeError):
    """Raised when the pickle cannot be loaded or is not usable."""


def _load_model():
    """Load once at import; never crash the API if the file is broken."""
    try:
        if not MODEL_PATH.exists():
            logger.error("ML model file not found: %s", MODEL_PATH)
            return None
        loaded = joblib.load(MODEL_PATH)
        logger.info("Loaded ML model from %s", MODEL_PATH)
        return loaded
    except Exception:
        logger.exception("Failed to load ML model from %s", MODEL_PATH)
        return None


# Load only a trusted model file.
model = _load_model()


def model_available() -> bool:
    return model is not None and hasattr(model, "predict_proba")


def map_food_type(food_category: str | None, food_name: str | None = None) -> str:
    """Map a donation category/name onto the model's food_type vocabulary."""
    name = (food_name or "").lower()
    category = (food_category or "").lower()

    has_fruit = any(k in name for k in FRUIT_KEYWORDS)
    has_veg = any(k in name for k in VEG_KEYWORDS)
    if has_veg and not has_fruit:
        return "Vegetables"
    if has_fruit:
        return "Fruits"
    if category in ("fruits_vegetables", "fruits", "vegetables"):
        return "Fruits" if category != "vegetables" else "Vegetables"
    return CATEGORY_TO_FOOD_TYPE.get(category, "Packaged")


def hours_remaining(donation) -> float:
    """Hours until the food expires (min 0.1 so the feature stays > 0)."""
    best_before = getattr(donation, "best_before", None)
    if best_before is None:
        return DEFAULT_HOURS_REMAINING
    if best_before.tzinfo is None:
        best_before = best_before.replace(tzinfo=timezone.utc)
    hours = (best_before - datetime.now(timezone.utc)).total_seconds() / 3600.0
    return round(max(hours, 0.1), 2)


def get_recommendations(donation: dict, ngos: list) -> list:
    """Score NGO feature dicts for one donation and return them sorted by
    P(accept) descending. `donation` holds food_quantity/hours_remaining/
    food_type; each ngo dict holds the NGO-side features + id/name."""
    if model is None:
        raise ModelUnavailableError("ML model is not loaded")

    quantity = donation["food_quantity"]
    hours = donation["hours_remaining"]
    food_type = donation["food_type"]

    # Filter impossible matches before ML ranking.
    eligible_ngos = [
        ngo for ngo in ngos
        if ngo["ngo_capacity"] >= quantity
        and ngo["ngo_demand"] >= quantity
    ]

    if not eligible_ngos:
        return []

    rows = []

    for ngo in eligible_ngos:
        rows.append({
            "food_quantity": quantity,
            "distance_km": ngo["distance_km"],
            "ngo_capacity": ngo["ngo_capacity"],
            "ngo_demand": ngo["ngo_demand"],
            "hours_remaining": hours,
            "acceptance_rate": ngo["acceptance_rate"],
            "food_type": food_type,
        })

    X = pd.DataFrame(rows, columns=FEATURE_COLUMNS)

    if not hasattr(model, "predict_proba"):
        raise ModelUnavailableError(
            "Loaded model does not support predict_proba"
        )

    probabilities = model.predict_proba(X)
    classes = list(model.classes_)

    if 1 not in classes:
        raise ModelUnavailableError(
            "Model must contain positive target class 1"
        )

    positive_index = classes.index(1)

    results = []

    for ngo, probability_row in zip(
        eligible_ngos, probabilities
    ):
        score = float(probability_row[positive_index])

        results.append({
            "ngo_id": ngo["id"],
            "ngo_name": ngo["name"],
            "match_score": round(score * 100, 2),
        })

    results.sort(
        key=lambda item: item["match_score"],
        reverse=True,
    )

    return results


async def _acceptance_rates(session, ngo_ids: list[str]) -> dict[str, float]:
    """Accepted / (accepted + rejected) offers over the last N days per NGO."""
    from sqlalchemy import func, select

    from app.models import MatchRequest

    if not ngo_ids:
        return {}

    ids = []
    for raw in ngo_ids:
        try:
            ids.append(uuid.UUID(str(raw)))
        except (ValueError, TypeError):
            continue
    if not ids:
        return {}

    cutoff = datetime.now(timezone.utc) - timedelta(days=ACCEPTANCE_HISTORY_DAYS)
    stmt = (
        select(
            MatchRequest.ngo_id.label("ngo_id"),
            MatchRequest.status.label("status"),
            func.count().label("n"),
        )
        .where(MatchRequest.ngo_id.in_(ids))
        .where(MatchRequest.offered_at >= cutoff)
        .group_by(MatchRequest.ngo_id, MatchRequest.status)
    )
    rows = (await session.execute(stmt)).all()

    tallies: dict[str, dict[str, int]] = {}
    for row in rows:
        bucket = tallies.setdefault(str(row.ngo_id), {"accepted": 0, "rejected": 0})
        if row.status == "accepted":
            bucket["accepted"] += int(row.n)
        elif row.status == "rejected":
            bucket["rejected"] += int(row.n)

    rates: dict[str, float] = {}
    for ngo_id, bucket in tallies.items():
        accepted, rejected = bucket["accepted"], bucket["rejected"]
        total = accepted + rejected
        rates[ngo_id] = round(accepted / total, 3) if total else DEFAULT_ACCEPTANCE_RATE
    return rates


def _build_ngo_features(
    donation,
    ranked,
    loads,
    rates,
    distance_overrides: dict[str, float] | None = None,
) -> list[dict]:
    """Turn matching.run_matching() candidates into model feature dicts.

    `distance_overrides` maps ngo_id -> real driving distance (km), used in place
    of the straight-line distance returned by the matcher when available."""
    quantity = float(donation.quantity_in_meals)
    hours = hours_remaining(donation)
    food_type = map_food_type(donation.food_category, donation.food_name)
    overrides = distance_overrides or {}

    features: list[dict] = []
    for ngo, distance_km, _headroom, _rel, _raw in ranked:
        ngo_key = str(ngo.id)
        capacity_meals = float(ngo.capacity_meals_per_day) if ngo.capacity_meals_per_day else None
        load = loads.get(ngo_key, 0.0)
        # Prefer the actual driving distance for the model feature.
        distance_km = overrides.get(ngo_key, distance_km)

        if capacity_meals is not None:
            capacity = capacity_meals
            demand = max(capacity_meals - load, 0.0)
        else:
            # Unknown capacity: assume at least the default, and never
            # auto-reject an NGO just because capacity was left blank.
            capacity = max(DEFAULT_CAPACITY_MEALS, quantity)
            demand = capacity

        features.append({
            "id": ngo.id,
            "name": ngo.org_name,
            "distance_km": round(float(distance_km), 3),
            "ngo_capacity": round(capacity, 2),
            "ngo_demand": round(demand, 2),
            "hours_remaining": hours,
            "acceptance_rate": rates.get(ngo_key, DEFAULT_ACCEPTANCE_RATE),
            "food_type": food_type,
            "reliability_score": float(ngo.reliability_score or 0.0),
            "capacity_meals_per_day": capacity_meals,
            "load_meals": round(load, 2),
        })
    return features


def _reasons(feature: dict) -> list[str]:
    """Short human-readable justifications shown next to each suggestion."""
    reasons: list[str] = []
    reliability = feature["reliability_score"]
    # reliability_score is stored on a 0-5 scale in production data.
    reliability_norm = min(reliability / 5.0, 1.0) if reliability > 1.0 else max(reliability, 0.0)
    if feature["distance_km"] < 3.0:
        reasons.append("Nearby pickup")
    elif feature["distance_km"] < 8.0:
        reasons.append("Close by")
    if feature["ngo_capacity"] >= feature.get("load_meals", 0) * 2:
        reasons.append("Plenty of capacity")
    if feature["acceptance_rate"] >= 0.8:
        reasons.append("High acceptance rate")
    if feature["ngo_demand"] >= feature["ngo_capacity"] * 0.5:
        reasons.append("High demand")
    if reliability_norm >= 0.8:
        reasons.append("Reliable partner")
    return reasons[:3]


async def _driving_distance_overrides(session, donation, ranked) -> dict[str, float]:
    """Real road distance (km) from the donation pickup to each candidate NGO,
    resolved in a single OSRM table request. Best-effort: NGOs OSRM can't reach
    (or when OSRM is unavailable) are omitted so the matcher's straight-line
    distance is used instead."""
    from sqlalchemy import select

    from app.models import Address, NGOProfile
    from app.services import directions as directions_service

    if donation.pickup_lat is None or donation.pickup_lng is None:
        return {}

    ngo_uuids = [ngo.id for ngo, *_ in ranked]
    if not ngo_uuids:
        return {}

    stmt = (
        select(NGOProfile.id, Address.lat, Address.lng)
        .join(Address, NGOProfile.address_id == Address.id)
        .where(NGOProfile.id.in_(ngo_uuids))
    )
    try:
        rows = (await session.execute(stmt)).all()
    except Exception:  # noqa: BLE001 - override is optional
        logger.exception("Failed to load NGO coordinates for driving distances")
        return {}

    coords: dict[str, tuple[float, float]] = {
        str(row.id): (float(row.lat), float(row.lng))
        for row in rows
        if row.lat is not None and row.lng is not None
    }
    ordered_ids = [str(ngo.id) for ngo, *_ in ranked if str(ngo.id) in coords]
    if not ordered_ids:
        return {}

    origin = (float(donation.pickup_lat), float(donation.pickup_lng))
    destinations = [coords[i] for i in ordered_ids]
    distances = await directions_service.driving_distances(origin, destinations)
    return {i: d for i, d in zip(ordered_ids, distances) if d is not None}


async def recommend_top_ngos_for_donation(
    session, donation, limit: int = 5
) -> list[dict]:
    """Full ML pipeline for a donation:
    candidates (geo + eligibility) -> feature engineering -> model.predict_proba
    -> top-N sorted by acceptance probability."""
    from app.services import matching

    if not model_available():
        raise ModelUnavailableError("ML model is not loaded")
    if donation.pickup_lat is None or donation.pickup_lng is None:
        logger.warning("Donation %s has no geocoded pickup coords", donation.id)
        return []

    ranked, _radius = await matching.run_matching(
        session, donation, min_candidates=ML_MIN_CANDIDATES
    )
    if not ranked:
        return []

    # Cap the candidate set so a single request never builds a huge matrix.
    ranked = ranked[:200]

    ngo_ids = [str(ngo.id) for ngo, *_ in ranked]
    loads = await matching._load_per_ngo(session, ngo_ids)
    rates = await _acceptance_rates(session, ngo_ids)

    # Use real driving distance for the model feature where OSRM can resolve it.
    distance_overrides = await _driving_distance_overrides(session, donation, ranked)

    features = _build_ngo_features(donation, ranked, loads, rates, distance_overrides)
    donation_features = {
        "food_quantity": float(donation.quantity_in_meals),
        "hours_remaining": hours_remaining(donation),
        "food_type": map_food_type(donation.food_category, donation.food_name),
    }

    scored = get_recommendations(
        donation=donation_features, ngos=features
    )

    by_id = {f["id"]: f for f in features}
    top: list[dict] = []
    for item in scored[:limit]:
        feature = by_id.get(item["ngo_id"])
        if feature is None:
            continue
        eta = matching.estimated_pickup_minutes(feature["distance_km"])
        top.append({
            "ngo_id": item["ngo_id"],
            "ngo_name": item["ngo_name"],
            "match_score": item["match_score"],
            "distance_km": feature["distance_km"],
            "capacity_meals_per_day": feature["capacity_meals_per_day"],
            "ngo_demand": feature["ngo_demand"],
            "acceptance_rate": feature["acceptance_rate"],
            "reliability_score": round(feature["reliability_score"], 2),
            "estimated_pickup_minutes": eta,
            "reasons": _reasons(feature),
        })
    return top
