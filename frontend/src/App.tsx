import { Navigate, Route, Routes } from "react-router-dom";
import type { ReactNode } from "react";
import { useAuth } from "./auth/AuthContext";
import { Layout } from "./components/Layout";
import { ProtectedRoute } from "./components/ProtectedRoute";
import type { Role } from "./lib/types";
import { LoginPage } from "./pages/LoginPage";
import { SignupPage } from "./pages/SignupPage";
import { DashboardPage } from "./pages/DashboardPage";
import { CreateDonationPage } from "./pages/CreateDonationPage";
import { DonationsPage } from "./pages/DonationsPage";
import { DonationDetailPage } from "./pages/DonationDetailPage";
import { NgoAvailablePage } from "./pages/NgoAvailablePage";
import { NgoAcceptedPage } from "./pages/NgoAcceptedPage";
import {
  AdminDonationsPage,
  AdminNgosPage,
  AdminRestaurantsPage,
} from "./pages/AdminListPages";
import { AdminVerificationsPage } from "./pages/AdminVerificationsPage";
import { AdminImpactPage } from "./pages/AdminImpactPage";
import { NotificationsPage } from "./pages/NotificationsPage";
import { ProfilePage } from "./pages/ProfilePage";
import { SettingsPage } from "./pages/SettingsPage";

function RequireRole({ roles, children }: { roles: Role[]; children: ReactNode }) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  if (!roles.includes(user.role)) return <Navigate to="/" replace />;
  return <>{children}</>;
}

function HomeRedirect() {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  return <DashboardPage />;
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />

      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<HomeRedirect />} />

        <Route
          path="/donations/new"
          element={
            <RequireRole roles={["donor"]}>
              <CreateDonationPage />
            </RequireRole>
          }
        />
        <Route
          path="/donations"
          element={
            <RequireRole roles={["donor"]}>
              <DonationsPage />
            </RequireRole>
          }
        />
        <Route
          path="/donations/:id"
          element={
            <RequireRole roles={["donor"]}>
              <DonationDetailPage />
            </RequireRole>
          }
        />

        <Route
          path="/ngo/available"
          element={
            <RequireRole roles={["ngo"]}>
              <NgoAvailablePage />
            </RequireRole>
          }
        />
        <Route
          path="/ngo/accepted"
          element={
            <RequireRole roles={["ngo"]}>
              <NgoAcceptedPage />
            </RequireRole>
          }
        />

        <Route
          path="/admin/verifications"
          element={
            <RequireRole roles={["admin"]}>
              <AdminVerificationsPage />
            </RequireRole>
          }
        />
        <Route
          path="/admin/impact"
          element={
            <RequireRole roles={["admin"]}>
              <AdminImpactPage />
            </RequireRole>
          }
        />
        <Route
          path="/admin/restaurants"
          element={
            <RequireRole roles={["admin"]}>
              <AdminRestaurantsPage />
            </RequireRole>
          }
        />
        <Route
          path="/admin/ngos"
          element={
            <RequireRole roles={["admin"]}>
              <AdminNgosPage />
            </RequireRole>
          }
        />
        <Route
          path="/admin/donations"
          element={
            <RequireRole roles={["admin"]}>
              <AdminDonationsPage />
            </RequireRole>
          }
        />

        <Route path="/notifications" element={<NotificationsPage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/settings" element={<SettingsPage />} />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
