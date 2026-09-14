import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { useToast } from "../auth/ToastContext";
import { ApiError } from "../lib/api";
import { ButtonSpinner } from "../components/Spinner";

export function LoginPage() {
  const { login } = useAuth();
  const { error: showError } = useToast();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const user = await login(email.trim(), password);
      const from = (location.state as { from?: string } | null)?.from;
      navigate(from || "/", { replace: true });
      void user;
    } catch (err) {
      showError(err instanceof ApiError ? err.message : "Login failed. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-brand">
          <span className="brand-mark brand-mark-lg">MB</span>
          <h1>MealBridge AI</h1>
          <p>Connecting surplus food with those who need it most.</p>
        </div>
        <form onSubmit={handleSubmit} className="auth-form">
          <label className="field">
            <span>Email</span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
              autoComplete="email"
            />
          </label>
          <label className="field">
            <span>Password</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              autoComplete="current-password"
            />
          </label>
          <button className="btn btn-primary btn-block" type="submit" disabled={submitting}>
            {submitting && <ButtonSpinner />}
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>
        <p className="auth-alt">
          New here?{" "}
          <Link to="/signup" className="link">
            Create an account
          </Link>
        </p>
        <div className="auth-hint">
          Demo accounts (seeded):
          <br />
          Restaurant donor: <code>spice.junction@restaurant.demo / Donor@12345</code>
          <br />
          NGO: <code>akshaya.trust@ngo.demo / Ngo@12345</code>
          <br />
          Admin: <code>admin@mealbridge.ai / Admin@12345</code>
        </div>
      </div>
    </div>
  );
}
