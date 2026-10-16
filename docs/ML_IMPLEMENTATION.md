# MealBridge AI — ML Implementation Guide (Backend + Frontend)

This document explains how the trained Random Forest model
(`backend/storage/mealbridge_random_forest.pkl`) is wired into MealBridge AI so
that **when a restaurant posts a food donation, the app suggests the top 5 best
NGOs** for that donation.

The ML ranking is **additive**: the existing heuristic matching/offer engine
(`app/services/matching.py`) is untouched and keeps running exactly as before.
The model provides an extra "AI top 5 NGO suggestions" view for the donor.

---

## 1. High-level flow

```
Restaurant picks the pickup point on a map (POST /api/v1/donations with lat/lng)
        │
        ▼
Donation row saved + exact pickup coords stored, or geocoded from text if no coords
        │
        ▼
Frontend redirects to /donations/{id}
        │
        ▼
DonationDetailPage mounts and calls
GET /api/ml/donations/{id}/top-ngos           (new)
        │
        ▼
Backend ML pipeline (app/services/ml_service.py)
  1. Candidate NGOs  → matching.run_matching()  (geo radius + eligibility)
  2. Driving distance → OSRM table (fallback: Haversine)
  3. Feature building → donation + NGO features
  4. model.predict_proba() → P(NGO accepts)
  5. Sort desc, take top 5
        │
        ▼
JSON response → "Recommended NGOs" card on the donation page
```

---

## 2. The model

| Item | Value |
| --- | --- |
| File | `backend/storage/mealbridge_random_forest.pkl` |
| Type | `sklearn.pipeline.Pipeline` |
| Preprocessing | `ColumnTransformer` → `OneHotEncoder` on `food_type`; numeric passthrough |
| Estimator | `RandomForestClassifier(n_estimators=200, max_depth=10, class_weight="balanced", random_state=42)` |
| Target | Binary `1 = NGO accepts the donation`, `0 = not accepted` |
| Output used | `predict_proba(X)[:, index_of_class_1]` × 100 = **match score %** |

### Feature contract (must stay in this order/name)

| Feature | Meaning | Source in MealBridge |
| --- | --- | --- |
| `food_quantity` | Donation size in meal-equivalents | `Donation.quantity_in_meals` |
| `distance_km` | Pickup → NGO distance | Real road (driving) distance via OSRM `table` service (`directions.driving_distances`), falling back to Haversine from `matching.run_matching()` when OSRM is unavailable |
| `ngo_capacity` | NGO daily meal capacity | `NGOProfile.capacity_meals_per_day` |
| `ngo_demand` | NGO remaining need today | `capacity_meals_per_day − today's matched load` |
| `hours_remaining` | Time until food expires | `Donation.best_before − now` |
| `acceptance_rate` | Historical accept ratio | `match_requests` (accepted ÷ accepted+rejected, last 30 days) |
| `food_type` | Categorical food class | Derived from `Donation.food_category` + `food_name` |

Allowed `food_type` values: `Cooked`, `Packaged`, `Fruits`, `Vegetables`
(`app/schemas/ml.py` → `FoodType`).

---

## 3. Backend implementation

### 3.1 Files

| File | Role |
| --- | --- |
| `backend/storage/mealbridge_random_forest.pkl` | Trained model artifact (loaded with `joblib`) |
| `backend/app/services/ml_service.py` | Loads the model + full pipeline (features → scores → top 5) |
| `backend/app/api/ml.py` | HTTP endpoints |
| `backend/app/schemas/ml.py` | Request/response schemas |
| `backend/app/main.py` | Mounts the ML router at `/api/ml` |
| `backend/app/services/matching.py` | Reused for candidate selection (`run_matching`) — one optional `min_candidates` argument was added |
| `backend/requirements.txt` | Added `scikit-learn`, `pandas`, `joblib` |

### 3.2 Loading the model

`ml_service.py` resolves the path relative to the backend directory
(`parents[2] / "storage" / "mealbridge_random_forest.pkl"`), so it works no
matter which CWD the server starts from. Loading happens once at import time
inside a `try/except`:

* If the file is missing/corrupt, the API still boots; `model_available()`
  returns `False` and the ML endpoint answers `503`.
* Only trusted, repo-local pickle files are loaded.

### 3.3 Pipeline steps (`recommend_top_ngos_for_donation`)

1. **Candidate selection** — reuse `matching.run_matching(session, donation, min_candidates=15)`.
   This applies the same production rules as the offer flow:
   * donation must be geocoded (`pickup_lat`/`pickup_lng`),
   * only `verification_status = "verified"` NGOs,
   * radius expansion `MATCH_INITIAL_RADIUS_KM → MATCH_MAX_RADIUS_KM`,
   * capacity headroom > 0 and food-requirement compatibility.
   `min_candidates=15` widens the pool so a real top 5 survives the next step
   (the normal offer flow stops at `MATCH_MIN_CANDIDATES`, default 3).
2. **Feature engineering** (`_build_ngo_features`) — turns each candidate into
   the model's feature row. Missing values fall back to documented defaults:
   * no capacity set → `max(100 meals, donation size)`,
   * no offer history → `acceptance_rate = 0.7`,
   * no `best_before` → `hours_remaining = 4.0`.
3. **Eligibility filter** — drop NGOs whose capacity/demand is smaller than the
   donation (they physically cannot take it).
4. **Prediction** — `model.predict_proba(DataFrame)`; score = `P(class 1) × 100`.
5. **Ranking** — sort by score descending, keep the top `limit` (5).
6. **Enrichment** — add distance, ETA (`matching.estimated_pickup_minutes`) and
   short human "reasons" (Nearby, Plenty of capacity, High demand, Reliable…).

### 3.4 Endpoints

**`GET /api/ml/donations/{donation_id}/top-ngos`** (new)

* Auth: Bearer JWT (`get_current_user`). Donor owner or admin only; others get `403`.
* `404` if the donation does not exist.
* `503` if the model is unavailable.
* `200` response:

```json
{
  "donation_id": "16b7aa41-7022-4bb4-b31e-8e945d675ebe",
  "model_name": "mealbridge_random_forest.pkl",
  "recommendations": [
    {
      "ngo_id": "10f972dd-bd47-48d2-ba0e-3841b8d9b41f",
      "ngo_name": "Akshaya Trust",
      "match_score": 76.12,
      "distance_km": 3.386,
      "capacity_meals_per_day": 1500.0,
      "ngo_demand": 1500.0,
      "acceptance_rate": 0.7,
      "reliability_score": 3.9,
      "estimated_pickup_minutes": 7,
      "reasons": ["Close by", "Plenty of capacity", "High demand"]
    }
  ]
}
```

Empty `recommendations` is a valid response (no geocoded pickup or no eligible
NGO) — the UI simply hides the card.

**`POST /api/ml/recommendations`** (existing, unchanged)

Raw endpoint that scores a caller-supplied list of NGO feature vectors. Handy
for testing the model in isolation.

### 3.5 Manual test

```powershell
# from D:\MEALBRIDGE-AI
& .\.venv\Scripts\python.exe -c "import app.main; print('ok')"   # workdir: backend

# with a valid donor access token:
curl -H "Authorization: Bearer <TOKEN>" ^
     http://localhost:8000/api/ml/donations/<DONATION_ID>/top-ngos
```

---

## 4. Frontend implementation

### 4.1 Files

| File | Role |
| --- | --- |
| `frontend/src/api/ml.ts` | Typed client for the ML endpoints (Bearer token attached) |
| `frontend/src/lib/types.ts` | `MlRecommendation`, `MlTopResponse` types |
| `frontend/src/pages/DonationDetailPage.tsx` | Renders the "AI top N NGO suggestions" card |

### 4.2 API client

`api/ml.ts` derives the ML origin from the existing config:

* `VITE_API_URL` (e.g. `http://localhost:8000/api/v1`) → strips the `/api/v1`
  suffix → calls `http://localhost:8000/api/ml/...`.
* If `VITE_API_URL` is unset (dev default), it calls the relative
  `/api/ml/...`, which Vite proxies to `http://localhost:8000` via
  `vite.config.ts`.

`fetchTopNgoRecommendations(donationId)` is the function used by the UI. The
access token is read from the same `tokens` store used by `lib/api.ts`, so
expired sessions behave exactly like the rest of the app.

### 4.3 UI behaviour

In `DonationDetailPage.load()`:

* For active donations (`pending_match`, `awaiting_response`, `unmatched`) the
  page fetches the heuristic matches **and** the ML suggestions in parallel
  (`Promise.allSettled`). An ML failure never blocks the page — the card is
  just hidden.
* For matched/completed/cancelled donations no ML call is made.

The card (below the detail grid) lists up to 5 NGOs, each with:

* rank + NGO name,
* `match_score` badge and progress bar,
* distance, estimated pickup time, historical acceptance rate, remaining demand,
* "reasons" tags.

Copy shown to the user: *"Scores are the model's predicted probability that each
NGO accepts this donation."*

---

## 5. Why the model and the matching engine coexist

| Concern | Heuristic matcher (`matching.py`) | ML recommender (`ml_service.py`) |
| --- | --- | --- |
| Purpose | Create real `MatchRequest` offers and drive the accept/reject lifecycle | Explain *which NGOs are most likely to accept* a specific donation |
| Score | Weighted distance/capacity/reliability | `P(accept)` from the Random Forest |
| Visible where | "Matching NGOs" card, NGO inbox | "AI top N NGO suggestions" card |
| Changed by this work | No (only an optional `min_candidates` kwarg added) | New |

Because the model only *reads* donors/NGOs/match history and never mutates
state, it cannot break the existing offer workflow.

---

## 6. Tuning & limitations

* `ml_service.py` constants control fallbacks: `DEFAULT_CAPACITY_MEALS`,
  `DEFAULT_ACCEPTANCE_RATE`, `DEFAULT_HOURS_REMAINING`, `ACCEPTANCE_HISTORY_DAYS`,
  `ML_MIN_CANDIDATES`.
* `ngo_demand` is a **daily**, load-based estimate (capacity minus today's
  matched/picked-up meals); it is not a stored column.
* `acceptance_rate` is unknown for new NGOs → default `0.7`.
* Scores are the model's confidence, so several NGOs often share near-identical
  scores when their features are similar.
* If the training feature set ever changes, update both the model artifact and
  `FEATURE_COLUMNS` in `ml_service.py`, and the `DonationFeatures`/`NGOFeatures`
  types in `frontend/src/api/ml.ts`.

---

## 7. Quick verification checklist

1. `backend/storage/mealbridge_random_forest.pkl` exists.
2. Backend boots (`python -c "import app.main"`) and logs
   `Loaded ML model from ...`.
3. A donor posts a donation, then `GET /api/ml/donations/{id}/top-ngos` returns
   200 with ≤ 5 recommendations.
4. The donation detail page shows the "AI top N NGO suggestions" card with
   match scores and reason tags.
5. Existing matching/offer flow and all other endpoints behave exactly as
   before.
