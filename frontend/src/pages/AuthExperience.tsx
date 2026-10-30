import { Link, useLocation } from "react-router-dom";
import { LoginPage } from "./LoginPage";
import { SignupPage } from "./SignupPage";

export function AuthExperience() {
  const location = useLocation();
  const signupActive = location.pathname === "/signup";

  return (
    <div className={`auth-page auth-experience ${signupActive ? "auth-signup-active" : ""}`}>
      <div className="auth-experience-header">
        <img className="auth-experience-logo" src="/logo.png" alt="MealBridge AI logo" />
        <div
          className={`auth-switcher ${signupActive ? "auth-switcher-signup" : ""}`}
          role="tablist"
          aria-label="Authentication"
        >
          <span className="auth-switcher-indicator" aria-hidden="true" />
          <Link
            to="/login"
            className={!signupActive ? "active" : ""}
            role="tab"
            aria-selected={!signupActive}
          >
            Sign in
          </Link>
          <Link
            to="/signup"
            className={signupActive ? "active" : ""}
            role="tab"
            aria-selected={signupActive}
          >
            Create account
          </Link>
        </div>
      </div>
      <div className="auth-slider-viewport">
        <div className="auth-slider">
          <section className="auth-panel" aria-hidden={signupActive}>
            <LoginPage embedded />
          </section>
          <section className="auth-panel auth-panel-signup" aria-hidden={!signupActive}>
            <SignupPage embedded />
          </section>
        </div>
      </div>
    </div>
  );
}
