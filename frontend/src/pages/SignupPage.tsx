import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { useToast } from "../auth/ToastContext";
import { ApiError } from "../lib/api";
import { ButtonSpinner } from "../components/Spinner";
import { LocationPicker, type PickedLocation } from "../components/LocationPicker";

type Mode = "donor" | "ngo";

export function SignupPage({ embedded = false }: { embedded?: boolean }) {
  const { signupDonor, signupNgo } = useAuth();
  const { error: showError, success } = useToast();
  const navigate = useNavigate();
  const [mode, setMode] = useState<Mode>("donor");
  const [submitting, setSubmitting] = useState(false);
  const [coords, setCoords] = useState<{ lat: number | null; lng: number | null }>({
    lat: null,
    lng: null,
  });
  const [form, setForm] = useState({
    restaurant_name: "",
    owner_name: "",
    org_name: "",
    registration_number: "",
    contact_person: "",
    email: "",
    phone: "",
    address: "",
    city: "Bengaluru",
    food_requirements: "",
    capacity_meals_per_day: "",
    password: "",
  });

  const set = (key: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [key]: e.target.value }));

  const handlePick = (location: PickedLocation) => {
    setCoords({ lat: location.lat, lng: location.lng });
    setForm((f) => ({
      ...f,
      address: location.address?.trim() || f.address,
      city: location.city?.trim() || f.city,
    }));
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    // Keep this aligned with the password rule shown in the signup form.
    if (!/[a-zA-Z]/.test(form.password) || !/\d/.test(form.password)) {
      showError("Password must contain at least one letter and one number.");
      return;
    }
    setSubmitting(true);
    try {
      const payload = {
        email: form.email.trim(),
        phone: form.phone.trim(),
        address: form.address.trim(),
        city: form.city.trim(),
        lat: coords.lat,
        lng: coords.lng,
        password: form.password,
      };
      if (mode === "donor") {
        await signupDonor({
          ...payload,
          restaurant_name: form.restaurant_name.trim(),
          owner_name: form.owner_name.trim(),
        });
        success("Donor account created. Welcome!");
      } else {
        await signupNgo({
          ...payload,
          org_name: form.org_name.trim(),
          registration_number: form.registration_number.trim(),
          contact_person: form.contact_person.trim(),
          food_requirements: form.food_requirements
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean),
          capacity_meals_per_day: form.capacity_meals_per_day
            ? Number(form.capacity_meals_per_day)
            : null,
        });
        success("NGO account created. Your profile is pending verification by an admin.");
      }
      navigate("/", { replace: true });
    } catch (err) {
      showError(
        err instanceof ApiError ? err.message : "Signup failed. Please try again.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  const card = (
    <div className="auth-card auth-card-wide">
        <div className="auth-brand auth-brand-signup">
          <img className="brand-mark brand-mark-lg" src="/logo.png" alt="MealBridge AI logo" />
          <h1>Create an account</h1>
          <p>Join the movement against food waste.</p>
        </div>

        <div className="segmented">
          <button
            className={mode === "donor" ? "seg-active" : ""}
            onClick={() => setMode("donor")}
            type="button"
          >
            Restaurant / Donor
          </button>
          <button
            className={mode === "ngo" ? "seg-active" : ""}
            onClick={() => setMode("ngo")}
            type="button"
          >
            NGO
          </button>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="form-grid">
            {mode === "donor" ? (
              <>
                <label className="field">
                  <span>Restaurant name</span>
                  <input value={form.restaurant_name} onChange={set("restaurant_name")} required minLength={2} />
                </label>
                <label className="field">
                  <span>Owner name</span>
                  <input value={form.owner_name} onChange={set("owner_name")} required minLength={2} />
                </label>
              </>
            ) : (
              <>
                <label className="field">
                  <span>Organisation name</span>
                  <input value={form.org_name} onChange={set("org_name")} required minLength={2} />
                </label>
                <label className="field">
                  <span>Registration number</span>
                  <input value={form.registration_number} onChange={set("registration_number")} required minLength={3} />
                </label>
                <label className="field">
                  <span>Contact person</span>
                  <input value={form.contact_person} onChange={set("contact_person")} required minLength={2} />
                </label>
                <label className="field">
                  <span>Capacity (meals/day)</span>
                  <input
                    type="number"
                    min={1}
                    value={form.capacity_meals_per_day}
                    onChange={set("capacity_meals_per_day")}
                    placeholder="e.g. 500"
                  />
                </label>
                <label className="field field-full">
                  <span>Food requirements (comma separated)</span>
                  <input
                    value={form.food_requirements}
                    onChange={set("food_requirements")}
                    placeholder="e.g. Perishable meals OK, Halal"
                  />
                </label>
              </>
            )}
            <label className="field">
              <span>Email</span>
              <input type="email" value={form.email} onChange={set("email")} required />
            </label>
            <label className="field">
              <span>Phone</span>
              <input value={form.phone} onChange={set("phone")} required minLength={7} />
            </label>
            <div className="field field-full">
              <span>{mode === "donor" ? "Restaurant location" : "Organisation location"}</span>
              <LocationPicker lat={coords.lat} lng={coords.lng} onPick={handlePick} />
            </div>
            <label className="field field-full">
              <span>Pickup address</span>
              <input
                value={form.address}
                onChange={set("address")}
                required
                minLength={5}
                placeholder="Auto-filled from the map — edit if needed"
              />
            </label>
            <label className="field">
              <span>City</span>
              <input value={form.city} onChange={set("city")} required />
            </label>
            <label className="field">
              <span>Password</span>
              <input
                type="password"
                value={form.password}
                onChange={set("password")}
                required
                minLength={8}
                placeholder="8+ chars, letters &amp; numbers"
              />
            </label>
          </div>
          <button className="btn btn-primary btn-block" type="submit" disabled={submitting}>
            {submitting && <ButtonSpinner />}
            {submitting ? "Creating account…" : "Create account"}
          </button>
        </form>
        <p className="auth-alt">
          Already have an account?{" "}
          <Link to="/login" className="link">
            Sign in
          </Link>
        </p>
    </div>
  );

  return embedded ? card : <div className="auth-page">{card}</div>;
}
