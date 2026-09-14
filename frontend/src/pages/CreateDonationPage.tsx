import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { useToast } from "../auth/ToastContext";
import { ButtonSpinner } from "../components/Spinner";

const CATEGORIES = [
  "hot_meals",
  "packaged_food",
  "bakery",
  "fruits_vegetables",
  "dairy",
  "beverages",
  "grains",
  "snacks",
  "other",
];

export function CreateDonationPage() {
  const navigate = useNavigate();
  const { error: showError, success } = useToast();
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({
    food_name: "",
    food_category: "hot_meals",
    quantity_value: "",
    quantity_unit: "meals",
    notes: "",
    address: "",
    city: "Bengaluru",
    best_before: "",
  });

  const set = (key: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [key]: e.target.value }));

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const qty = Number(form.quantity_value);
    if (!Number.isFinite(qty) || qty <= 0) {
      showError("Quantity must be a positive number.");
      return;
    }
    setSubmitting(true);
    try {
      const res = await api.createDonation({
        food_name: form.food_name.trim(),
        food_category: form.food_category,
        quantity_value: qty,
        quantity_unit: form.quantity_unit,
        notes: form.notes.trim() || null,
        address: form.address.trim(),
        city: form.city.trim(),
        best_before: form.best_before ? new Date(form.best_before).toISOString() : null,
      });
      success("Donation posted! Matching with NGOs now…");
      navigate(`/donations/${res.donation_id}`);
    } catch (err) {
      showError(err instanceof Error ? err.message : "Failed to post donation.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h2>Post a donation</h2>
          <p className="muted">Provide details and nearby NGOs will be matched automatically.</p>
        </div>
      </div>

      <div className="card form-card">
        <form onSubmit={handleSubmit} className="auth-form">
          <div className="form-grid">
            <label className="field field-full">
              <span>Food name</span>
              <input value={form.food_name} onChange={set("food_name")} required minLength={2} placeholder="e.g. Veg Biryani (50 portions)" />
            </label>
            <label className="field">
              <span>Category</span>
              <select value={form.food_category} onChange={set("food_category")}>
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>
                    {c.replace(/_/g, " ").replace(/\b\w/g, (m) => m.toUpperCase())}
                  </option>
                ))}
              </select>
            </label>
            <div className="field-row">
              <label className="field">
                <span>Quantity</span>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  value={form.quantity_value}
                  onChange={set("quantity_value")}
                  required
                  placeholder="e.g. 50"
                />
              </label>
              <label className="field">
                <span>Unit</span>
                <select value={form.quantity_unit} onChange={set("quantity_unit")}>
                  <option value="meals">meals</option>
                  <option value="kg">kg</option>
                  <option value="packets">packets</option>
                </select>
              </label>
            </div>
            <label className="field field-full">
              <span>Pickup address</span>
              <input value={form.address} onChange={set("address")} required minLength={5} placeholder="Street, area" />
            </label>
            <label className="field">
              <span>City</span>
              <input value={form.city} onChange={set("city")} required />
            </label>
            <label className="field">
              <span>Best before</span>
              <input type="datetime-local" value={form.best_before} onChange={set("best_before")} />
            </label>
            <label className="field field-full">
              <span>Notes</span>
              <textarea value={form.notes} onChange={set("notes")} rows={3} placeholder="Packaging, storage needs, pickup instructions…" />
            </label>
          </div>
          <div className="form-actions">
            <button type="button" className="btn btn-ghost" onClick={() => navigate("/donations")}>
              Cancel
            </button>
            <button className="btn btn-primary" type="submit" disabled={submitting}>
              {submitting && <ButtonSpinner />}
              {submitting ? "Posting…" : "Post donation"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
