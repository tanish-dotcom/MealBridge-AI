import { useState, type FormEvent } from "react";
import { useAuth } from "../auth/AuthContext";
import { useToast } from "../auth/ToastContext";
import { api } from "../lib/api";
import { formatDate, initials } from "../lib/format";
import { ButtonSpinner } from "../components/Spinner";

export function ProfilePage() {
  const { user, refreshUser } = useAuth();
  const { success, error: showError } = useToast();
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState(() => ({
    first_name: user?.first_name ?? "",
    last_name: user?.last_name ?? "",
    email: user?.email ?? "",
    phone: user?.phone ?? "",
  }));

  if (!user) return null;

  const set = (key: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [key]: e.target.value }));

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await api.updateMe({
        first_name: form.first_name.trim() || undefined,
        last_name: form.last_name.trim() || undefined,
        email: form.email.trim(),
        phone: form.phone.trim() || undefined,
      });
      await refreshUser();
      success("Profile updated.");
    } catch (err) {
      showError(err instanceof Error ? err.message : "Failed to update profile.");
    } finally {
      setSubmitting(false);
    }
  };

  const roleName =
    user.role === "donor" ? user.donor_profile?.restaurant_name
    : user.role === "ngo" ? user.ngo_profile?.org_name
    : "Administrator";

  const verification = user.role === "ngo" ? user.ngo_profile?.verification_status : null;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h2>Profile</h2>
          <p className="muted">Manage your account and organisation details.</p>
        </div>
      </div>

      <div className="detail-grid">
        <div className="card profile-card">
          <div className="profile-avatar-lg">
            {user.avatar_url ? <img src={user.avatar_url} alt="Avatar" /> : initials(user.first_name || user.email)}
          </div>
          <h3>{user.first_name || roleName}</h3>
          <p className="muted">{roleName}</p>
          {verification && (
            <span className={`badge ${verification === "verified" ? "badge-green" : verification === "pending" ? "badge-amber" : "badge-red"}`}>
              {verification === "verified" ? "Verified NGO" : `${verification} verification`}
            </span>
          )}
          <dl className="detail-list">
            <dt>Role</dt>
            <dd className="cap">{user.role}</dd>
            <dt>Member since</dt>
            <dd>{formatDate(user.created_at)}</dd>
            <dt>Email notifications</dt>
            <dd>{user.preferences?.email_notifications ? "On" : "Off"}</dd>
            <dt>SMS alerts</dt>
            <dd>{user.preferences?.sms_alerts ? "On" : "Off"}</dd>
          </dl>
        </div>

        <div className="card">
          <div className="card-header">
            <h3>Edit details</h3>
          </div>
          <form onSubmit={handleSubmit} className="auth-form">
            <div className="form-grid">
              <label className="field">
                <span>First name</span>
                <input value={form.first_name} onChange={set("first_name")} />
              </label>
              <label className="field">
                <span>Last name</span>
                <input value={form.last_name} onChange={set("last_name")} />
              </label>
              <label className="field">
                <span>Email</span>
                <input type="email" value={form.email} onChange={set("email")} required />
              </label>
              <label className="field">
                <span>Phone</span>
                <input value={form.phone} onChange={set("phone")} />
              </label>
            </div>
            <div className="form-actions">
              <button className="btn btn-primary" type="submit" disabled={submitting}>
                {submitting && <ButtonSpinner />} Save changes
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
