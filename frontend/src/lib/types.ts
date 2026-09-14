export type Role = "donor" | "ngo" | "admin";

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  expires_in: number;
}

export interface AuthResponse {
  token_pair: TokenPair;
  user_id: string;
  email: string;
  role: Role;
  profile_status?: string | null;
}

export interface Address {
  id: string;
  line1?: string | null;
  line2?: string | null;
  city?: string | null;
  state?: string | null;
  postal_code?: string | null;
  country?: string | null;
  lat?: number | null;
  lng?: number | null;
}

export interface DonorProfile {
  restaurant_name: string;
  owner_name: string;
  donor_type: string;
  is_verified: boolean;
  address?: Address | null;
}

export interface NgoProfile {
  id: string;
  org_name: string;
  registration_number: string;
  contact_person: string;
  verification_status: string;
  capacity_meals_per_day?: number | null;
  food_requirements: string[];
  reliability_score: number;
  address?: Address | null;
}

export interface User {
  id: string;
  email: string;
  phone?: string | null;
  role: Role;
  first_name?: string | null;
  last_name?: string | null;
  avatar_url?: string | null;
  preferences: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  donor_profile?: DonorProfile | null;
  ngo_profile?: NgoProfile | null;
}

export interface DonationStats {
  active_donations: number;
  completed_donations: number;
  meals_donated: number;
  people_helped: number;
}

export interface NgoStats {
  available_donations: number;
  accepted_donations: number;
  meals_received: number;
  people_served: number;
}

export interface Donation {
  id: string;
  donor_id: string;
  food_name: string;
  food_category: string;
  quantity_value: number;
  quantity_unit: string;
  preparation_time?: string | null;
  best_before?: string | null;
  notes?: string | null;
  status: string;
  pickup_lat?: number | null;
  pickup_lng?: number | null;
  matched_ngo_id?: string | null;
  completed_by_donor: boolean;
  completed_by_ngo: boolean;
  created_at: string;
  updated_at: string;
  address?: Address | null;
  photos: { id: string; url: string }[];
  donor_name?: string | null;
  donor_email?: string | null;
  donor_type?: string | null;
  quantity_in_meals?: number;
}

export interface MatchCandidate {
  match_request_id?: string | null;
  ngo_id: string;
  ngo_name: string;
  contact_person?: string | null;
  distance_km: number;
  match_percent: number;
  estimated_pickup_minutes: number;
  capacity_headroom_ratio: number;
  reliability_score: number;
  quality_tags: string[];
  lat?: number | null;
  lng?: number | null;
}

export interface MatchResult {
  donation_id: string;
  top_match: MatchCandidate;
  alternatives: MatchCandidate[];
}

export interface Directions {
  distance_km: number;
  duration_minutes: number;
  polyline: { lat: number; lng: number }[];
  steps: string[];
  provider: string;
}

export interface AvailableDonation {
  match_request_id: string;
  donation_id: string;
  food_name: string;
  food_category: string;
  quantity_value: number;
  quantity_unit: string;
  quantity_in_meals: number;
  donor_name?: string | null;
  distance_km: number;
  time_since_posted_minutes: number;
  match_percent: number;
  notes?: string | null;
  created_at: string;
}

export interface AcceptedDonation {
  donation_id: string;
  food_name: string;
  food_category: string;
  quantity_value: number;
  quantity_unit: string;
  status: string;
  donor_name?: string | null;
  best_before?: string | null;
  created_at: string;
  completed_by_donor: boolean;
  completed_by_ngo: boolean;
}

export interface NotificationItem {
  id: string;
  type: string;
  title: string;
  body: string;
  payload?: Record<string, unknown> | null;
  read_at?: string | null;
  created_at: string;
}

export interface AdminOverviewStats {
  total_restaurants: number;
  verified_ngos: number;
  pending_ngos: number;
  total_donations: number;
  meals_redistributed: number;
}

export interface SeriesPoint {
  label: string;
  value: number;
}

export interface RecentActivityItem {
  id: string;
  type: string;
  actor: string;
  subject: string;
  status: string;
  created_at: string;
}

export interface AdminOverview {
  stats: AdminOverviewStats;
  donation_volume: SeriesPoint[];
  food_categories: SeriesPoint[];
  recent_activity: RecentActivityItem[];
}

export interface ImpactStats {
  meals_redistributed: number;
  food_saved_kg: number;
  people_served: number;
  co2_reduced_kg: number;
  co2_is_estimate: boolean;
}

export interface TopContributor {
  name: string;
  meals: number;
  food_kg: number;
}

export interface GoalProgress {
  key: string;
  label: string;
  current: number;
  target: number;
  percent: number;
}

export interface ImpactReport {
  stats: ImpactStats;
  monthly_redistribution: SeriesPoint[];
  food_categories: SeriesPoint[];
  top_contributors: TopContributor[];
  goals: GoalProgress[];
}

export interface PendingVerification {
  id: string;
  org_name: string;
  registration_number: string;
  contact_person: string;
  email: string;
  phone: string;
  capacity_meals_per_day?: number | null;
  food_requirements: string[];
  verification_doc_url?: string | null;
  created_at: string;
  address?: { line1?: string | null; city?: string | null } | null;
}

export interface AdminRestaurant {
  id: string;
  restaurant_name: string;
  owner_name: string;
  email: string;
  phone: string;
  city?: string | null;
  is_verified: boolean;
  created_at: string;
}

export interface AdminNgo {
  id: string;
  org_name: string;
  registration_number: string;
  contact_person: string;
  email: string;
  verification_status: string;
  capacity_meals_per_day?: number | null;
  reliability_score: number;
  city?: string | null;
  created_at: string;
}

export interface AdminDonation {
  id: string;
  food_name: string;
  food_category: string;
  quantity_value: number;
  quantity_unit: string;
  status: string;
  donor?: string | null;
  city?: string | null;
  created_at: string;
}

export interface DonorSignupPayload {
  restaurant_name: string;
  owner_name: string;
  email: string;
  phone: string;
  address: string;
  city: string;
  password: string;
}

export interface NgoSignupPayload {
  org_name: string;
  registration_number: string;
  contact_person: string;
  email: string;
  phone: string;
  address: string;
  city: string;
  food_requirements: string[];
  capacity_meals_per_day?: number | null;
  password: string;
}

export interface DonationCreatePayload {
  food_name: string;
  food_category: string;
  quantity_value: number;
  quantity_unit: string;
  preparation_time?: string | null;
  best_before?: string | null;
  notes?: string | null;
  address: string;
  city: string;
}
