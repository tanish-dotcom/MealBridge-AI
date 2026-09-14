import type {
  AcceptedDonation,
  AdminDonation,
  AdminNgo,
  AdminOverview,
  AdminRestaurant,
  AuthResponse,
  AvailableDonation,
  Directions,
  Donation,
  DonationCreatePayload,
  DonationStats,
  DonorSignupPayload,
  ImpactReport,
  MatchResult,
  NgoSignupPayload,
  NgoStats,
  NotificationItem,
  PendingVerification,
  TokenPair,
  User,
} from "./types";

const BASE_URL =
  import.meta.env.VITE_API_URL || (import.meta.env.DEV ? "/api/v1" : "/api/v1");

const ACCESS_KEY = "mb_access_token";
const REFRESH_KEY = "mb_refresh_token";

export const tokens = {
  get access() {
    return localStorage.getItem(ACCESS_KEY);
  },
  get refresh() {
    return localStorage.getItem(REFRESH_KEY);
  },
  set(access: string, refresh: string) {
    localStorage.setItem(ACCESS_KEY, access);
    localStorage.setItem(REFRESH_KEY, refresh);
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown) {
    super(errorMessage(status, detail));
    this.status = status;
    this.detail = detail;
  }
}

function errorMessage(status: number, detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as { msg?: unknown };
    if (typeof first.msg === "string") {
      return first.msg.replace(/^Value error, /, "");
    }
  }
  return status === 422 ? "Please check the form details and try again." : "Request failed";
}

let refreshing: Promise<string> | null = null;

async function refreshAccessToken(): Promise<string> {
  const refresh = tokens.refresh;
  if (!refresh) throw new ApiError(401, "No refresh token");

  const res = await fetch(`${BASE_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
  });
  if (!res.ok) {
    tokens.clear();
    throw new ApiError(res.status, await readDetail(res));
  }
  const data = (await res.json()) as TokenPair;
  tokens.set(data.access_token, data.refresh_token);
  return data.access_token;
}

async function readDetail(res: Response): Promise<unknown> {
  try {
    const body = await res.json();
    return body.detail ?? body;
  } catch {
    return res.statusText;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const doFetch = (token: string | null): Promise<Response> => {
    if (token) headers.set("Authorization", `Bearer ${token}`);
    return fetch(url, { ...options, headers });
  };

  let res = await doFetch(tokens.access);

  if (res.status === 401 && tokens.refresh) {
    const token = tokens.refresh ? await getRefreshedToken() : null;
    if (token) {
      res = await doFetch(token);
    }
  }

  if (!res.ok) {
    throw new ApiError(res.status, await readDetail(res));
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

function getRefreshedToken(): Promise<string> {
  if (!refreshing) {
    refreshing = refreshAccessToken().finally(() => {
      refreshing = null;
    });
  }
  return refreshing;
}

function get(path: string, init?: RequestInit) {
  return request<unknown>(path, { method: "GET", ...init });
}

function post<T = unknown>(path: string, body?: unknown, init?: RequestInit) {
  return request<T>(path, {
    method: "POST",
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    ...init,
  });
}

function patch<T = unknown>(path: string, body: unknown) {
  return request<T>(path, { method: "PATCH", body: JSON.stringify(body) });
}

export const api = {
  // ---- Auth ----
  login: (payload: { email: string; password: string; remember_me?: boolean }) =>
    post<AuthResponse>("/auth/login", payload),
  signupDonor: (payload: DonorSignupPayload) =>
    post<AuthResponse>("/auth/signup/donor", payload),
  signupNgo: (payload: NgoSignupPayload) =>
    post<AuthResponse>("/auth/signup/ngo", payload),
  logout: () =>
    post("/auth/logout", { refresh_token: tokens.refresh ?? "" }).catch(() => undefined),
  me: () => get("/auth/me") as Promise<{ id: string; email: string; role: string }>,

  // ---- Users ----
  getMe: () => get("/users/me") as Promise<User>,
  updateMe: (payload: {
    first_name?: string;
    last_name?: string;
    phone?: string;
    email?: string;
    avatar_url?: string;
  }) => patch<User>("/users/me", payload),
  changePassword: (payload: { current_password: string; new_password: string }) =>
    post("/users/me/password", payload),
  updatePreferences: (payload: { email_notifications: boolean; sms_alerts: boolean }) =>
    patch<{ preferences: Record<string, unknown> }>("/users/me/preferences", payload),

  // ---- Donations (donor) ----
  createDonation: (payload: DonationCreatePayload) =>
    post<{ donation_id: string; status: string }>("/donations", payload),
  myDonationStats: () => get("/donations/mine") as Promise<DonationStats>,
  myDonations: () => get("/donations/mine/list") as Promise<Donation[]>,
  getDonation: (id: string) => get(`/donations/${id}`) as Promise<Donation>,
  cancelDonation: (id: string) =>
    post<{ message: string }>(`/donations/${id}/cancel`),
  donationMatches: (id: string) =>
    get(`/donations/${id}/matches`) as Promise<MatchResult>,
  donationDirections: (id: string) =>
    get(`/donations/${id}/directions`) as Promise<Directions>,
  confirmPickup: (id: string) =>
    post<{ message: string; status: string; side: string }>(`/donations/${id}/confirm-pickup`),

  // ---- NGO ----
  ngoStats: () => get("/ngo/dashboard/stats") as Promise<NgoStats>,
  ngoAvailable: () => get("/ngo/available-donations") as Promise<AvailableDonation[]>,
  ngoAccepted: () => get("/ngo/accepted-donations") as Promise<AcceptedDonation[]>,
  ngoRespond: (matchRequestId: string, action: "accept" | "reject") =>
    post<{ message: string; donation_id: string; status: string }>(
      `/ngo/matches/${matchRequestId}/respond`,
      { action },
    ),

  // ---- Admin ----
  adminOverview: () => get("/admin/dashboard/overview") as Promise<AdminOverview>,
  adminImpact: () => get("/admin/analytics/impact") as Promise<ImpactReport>,
  pendingVerifications: () =>
    get("/admin/verifications/pending") as Promise<PendingVerification[]>,
  approveNgo: (id: string) =>
    post<{ message: string }>(`/admin/verifications/${id}/approve`),
  rejectNgo: (id: string) =>
    post<{ message: string }>(`/admin/verifications/${id}/reject`),
  adminRestaurants: () => get("/admin/restaurants") as Promise<AdminRestaurant[]>,
  adminNgos: () => get("/admin/ngos") as Promise<AdminNgo[]>,
  adminDonations: () => get("/admin/donations") as Promise<AdminDonation[]>,

  // ---- Notifications ----
  notifications: () => get("/notifications") as Promise<NotificationItem[]>,
  markNotificationRead: (id: string) =>
    patch<{ message: string }>(`/notifications/${id}/read`, {}),
};
