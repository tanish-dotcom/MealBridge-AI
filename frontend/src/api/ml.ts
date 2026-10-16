
import { tokens } from "../lib/api";
import type { MlRecommendation, MlTopResponse } from "../lib/types";

// VITE_API_URL points at the v1 API (e.g. http://localhost:8000/api/v1).
// The ML router is mounted at /api/ml on the same origin, so strip the /api/v1
// suffix (in dev the Vite proxy forwards relative /api/* to the backend).
const RAW_BASE = import.meta.env.VITE_API_URL || "";
const API_ORIGIN = RAW_BASE.replace(/\/api\/v1\/?$/, "");

export interface DonationFeatures {
  food_quantity: number;
  hours_remaining: number;
  food_type: "Cooked" | "Packaged" | "Fruits" | "Vegetables";
}

export interface NGOFeatures {
  id: number;
  name: string;
  distance_km: number;
  ngo_capacity: number;
  ngo_demand: number;
  acceptance_rate: number;
}

export interface NGORecommendation {
  ngo_id: number;
  ngo_name: string;
  match_score: number;
}

function authHeaders(): Record<string, string> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = tokens.access;
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

/**
 * Live ML pipeline for a posted donation: the backend builds features from the
 * donation + nearby verified NGOs and returns the top 5 by predicted acceptance
 * probability (Random Forest, backend/storage/mealbridge_random_forest.pkl).
 */
export async function fetchTopNgoRecommendations(
  donationId: string
): Promise<MlRecommendation[]> {
  const response = await fetch(
    `${API_ORIGIN}/api/ml/donations/${donationId}/top-ngos`,
    { headers: authHeaders() }
  );

  const result = (await response.json().catch(() => ({}))) as
    | MlTopResponse
    | { detail?: unknown };

  if (!response.ok) {
    const detail = (result as { detail?: unknown }).detail;
    throw new Error(typeof detail === "string" ? detail : "Could not load AI suggestions");
  }

  return (result as MlTopResponse).recommendations ?? [];
}

/** Direct model endpoint (score a caller-supplied NGO feature list). */
export async function fetchNGORecommendations(
  donation: DonationFeatures,
  ngos: NGOFeatures[]
): Promise<NGORecommendation[]> {
  const response = await fetch(`${API_ORIGIN}/api/ml/recommendations`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ donation, ngos }),
  });

  const result = await response.json();

  if (!response.ok) {
    throw new Error(result.detail || "Could not fetch recommendations");
  }

  return result.recommendations;
}
