import { useState, type FormEvent } from "react";
import { useAuth } from "../auth/AuthContext";
import { useToast } from "../auth/ToastContext";
import { api } from "../lib/api";
import { ButtonSpinner } from "../components/Spinner";

export function SettingsPage() {
  const { user, refreshUser, logout } = useAuth();
  const { success, error: showError } = useToast();
  const [prefsSubmitting, setPrefsSubmitting] = useState(false);
  const [pwSubmitting, setPwSubmitting] = useState(false);
  const [prefs, setPrefs] = useState(() => ({
    email_notifications: Boolean(user?.preferences?.email_notifications),
    sms_alerts: Boolean(user?.preferences?.sms_alerts),
  }));
  const [pw, setPw] = useState({ current_password: "", new_password: "", confirm: "" });

  if (!user) return null;

  const savePrefs = async () => {
    setPrefsSubmitting(true);
    try {
      const res = await api.updatePreferences(prefs);
      await refreshUser();
      void res;
      success("Notification preferences saved.");
    } catch (err) {
      showError(err instanceof Error ? err.message : "Failed to save preferences.");
    } finally {
      setPrefsSubmitting(false);
    }
  };

  const changePassword = async (e: FormEvent) => {
    e.preventDefault();
    if (pw.new_password.length < 8) {
      showError("New password must be at least 8 characters.");
      return;
    }
    if (pw.new_password !== pw.confirm) {
      showError("Passwords do not match.");
      return;
    }
    setPwSubmitting(true);
    try {
      await api.changePassword({ current_password: pw.current_password, new_password: pw.new_password });
      success("Password changed. Please sign in again.");
      await logout();
    } catch (err) {
      showError(err instanceof Error ? err.message : "Failed to change password.");
    } finally {
      setPwSubmitting(false);
    }
  };

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h2>Settings</h2>
          <p className="muted">Notification preferences and security.</p>
        </div>
      </div>

      <div className="detail-grid">
        <div className="card">
          <div className="card-header">
            <h3>Notifications</h3>
          </div>
          <div className="setting-row">
            <div>
              <strong>Email notifications</strong>
              <div className="muted small">Receive updates about matches and pickups by email.</div>
            </div>
            <label className="switch">
              <input
                type="checkbox"
                checked={prefs.email_notifications}
                onChange={(e) => setPrefs((p) => ({ ...p, email_notifications: e.target.checked }))}
              />
              <span className="slider" />
            </label>
          </div>
          <div className="setting-row">
            <div>
              <strong>SMS alerts</strong>
              <div className="muted small">Get time-sensitive pickup alerts by SMS.</div>
            </div>
            <label className="switch">
              <input
                type="checkbox"
                checked={prefs.sms_alerts}
                onChange={(e) => setPrefs((p) => ({ ...p, sms_alerts: e.target.checked }))}
              />
              <span className="slider" />
            </label>
          </div>
          <div className="form-actions">
            <button className="btn btn-primary" onClick={savePrefs} disabled={prefsSubmitting}>
              {prefsSubmitting && <ButtonSpinner />} Save preferences
            </button>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h3>Change password</h3>
          </div>
          <form onSubmit={changePassword} className="auth-form">
            <label className="field">
              <span>Current password</span>
              <input
                type="password"
                value={pw.current_password}
                onChange={(e) => setPw((p) => ({ ...p, current_password: e.target.value }))}
                required
              />
            </label>
            <label className="field">
              <span>New password</span>
              <input
                type="password"
                value={pw.new_password}
                onChange={(e) => setPw((p) => ({ ...p, new_password: e.target.value }))}
                required
                minLength={8}
              />
            </label>
            <label className="field">
              <span>Confirm new password</span>
              <input
                type="password"
                value={pw.confirm}
                onChange={(e) => setPw((p) => ({ ...p, confirm: e.target.value }))}
                required
              />
            </label>
            <div className="form-actions">
              <button className="btn btn-primary" type="submit" disabled={pwSubmitting}>
                {pwSubmitting && <ButtonSpinner />} Change password
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
