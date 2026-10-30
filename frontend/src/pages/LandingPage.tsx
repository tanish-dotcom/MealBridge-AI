import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import type { ReactNode } from "react";
import { useTheme } from "../theme/ThemeContext";
import { MoonIcon, SunIcon } from "../components/Icons";

/* ------------------------------------------------------------------ */
/* Helpers                                                             */
/* ------------------------------------------------------------------ */

function useReveal<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("revealed");
            obs.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.15 },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);
  return ref;
}

function Reveal({
  children,
  delay = 0,
  className = "",
}: {
  children: ReactNode;
  delay?: number;
  className?: string;
}) {
  const ref = useReveal<HTMLDivElement>();
  return (
    <div ref={ref} className={`reveal ${className}`} style={{ transitionDelay: `${delay}ms` }}>
      {children}
    </div>
  );
}

function Counter({
  value,
  suffix = "",
  prefix = "",
  decimals = 0,
}: {
  value: number;
  suffix?: string;
  prefix?: string;
  decimals?: number;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const [started, setStarted] = useState(false);
  const [display, setDisplay] = useState(0);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setStarted(true);
            obs.disconnect();
          }
        });
      },
      { threshold: 0.5 },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  useEffect(() => {
    if (!started) return;
    const duration = 1800;
    const start = performance.now();
    let raf = 0;
    const tick = (now: number) => {
      const progress = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplay(value * eased);
      if (progress < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [started, value]);

  const formatted =
    decimals > 0
      ? display.toFixed(decimals)
      : Math.round(display).toLocaleString("en-US");

  return (
    <span ref={ref} className="counter">
      {prefix}
      {formatted}
      {suffix}
    </span>
  );
}

/* ------------------------------------------------------------------ */
/* Icons (inline SVG)                                                  */
/* ------------------------------------------------------------------ */

function Icon({ name }: { name: string }) {
  const paths: Record<string, ReactNode> = {
    plate: (
      <>
        <circle cx="12" cy="12" r="8" />
        <path d="M4 4v2M20 4v2M4 18v2M20 18v2" />
      </>
    ),
    target: (
      <>
        <circle cx="12" cy="12" r="9" />
        <circle cx="12" cy="12" r="5" />
        <circle cx="12" cy="12" r="1" />
      </>
    ),
    bell: <path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18S18 15 18 8M13.7 21a2 2 0 0 1-3.4 0" />,
    shield: (
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    ),
    chart: (
      <>
        <path d="M3 3v18h18" />
        <path d="M7 15l4-4 3 3 5-6" />
      </>
    ),
    handshake: (
      <>
        <path d="M11 17l-6-6m0 0l3-3 4 4m-7-1l7 7m7-6l3 0-2 5-5-1" />
        <path d="M4 17h5l2 2h7" />
      </>
    ),
    bolt: <path d="M13 2 3 14h7l-1 8 10-12h-7l1-8z" />,
    leaf: (
      <path d="M5 21c.5-7 4-13 15-14-1 11-7 14.5-14 14.5" />
    ),
    truck: (
      <>
        <path d="M1 3h15v13H1zM16 8h4l3 3v5h-7z" />
        <circle cx="5.5" cy="18.5" r="1.5" />
        <circle cx="18.5" cy="18.5" r="1.5" />
      </>
    ),
    users: (
      <>
        <circle cx="9" cy="8" r="3" />
        <path d="M2 21v-2a7 7 0 0 1 14 0v2M17 8a3 3 0 1 0-2-5.2M22 21v-2a7 7 0 0 0-5-6.7" />
      </>
    ),
    check: <path d="M20 6 9 17l-5-5" />,
    arrow: <path d="M5 12h14M13 6l6 6-6 6" />,
  };
  return (
    <svg
      viewBox="0 0 24 24"
      width="24"
      height="24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {paths[name]}
    </svg>
  );
}

/* ------------------------------------------------------------------ */
/* Content                                                             */
/* ------------------------------------------------------------------ */

const HERO_STATS = [
  { value: 48600, suffix: "+", label: "Meals rescued", icon: "plate" },
  { value: 320, suffix: "+", label: "Restaurants onboard", icon: "truck" },
  { value: 148, suffix: "", label: "Verified NGOs", icon: "handshake" },
  { value: 92, suffix: "%", label: "Match accuracy", icon: "target" },
];

const FEATURES = [
  {
    icon: "target",
    title: "AI-powered matching",
    desc: "Our intelligent engine pairs surplus food with the ideal NGO — by cuisine, dietary needs, distance and pickup windows — in seconds.",
    tint: "green",
  },
  {
    icon: "bell",
    title: "Real-time alerts",
    desc: "Donors and NGOs get instant notifications the moment a donation is posted, matched or en route. No more missed pickups.",
    tint: "amber",
  },
  {
    icon: "shield",
    title: "Verified partners",
    desc: "Every NGO is identity-checked and certified before joining. Trust is at the core of every hand-off we broker.",
    tint: "violet",
  },
  {
    icon: "chart",
    title: "Impact analytics",
    desc: "Track meals rescued, CO₂ avoided and waste diverted on a living, actionable dashboard for admins.",
    tint: "blue",
  },
];

const STEPS = [
  {
    icon: "plate",
    step: "01",
    title: "Post surplus food",
    desc: "Restaurants list excess meals with a few taps — quantity, type, dietary tags and a pickup window.",
    tint: "green",
  },
  {
    icon: "target",
    step: "02",
    title: "AI matches an NGO",
    desc: "The engine scores every nearby NGO and proposes the best match, complete with directions and timing.",
    tint: "amber",
  },
  {
    icon: "truck",
    step: "03",
    title: "Pickup & impact",
    desc: "The NGO confirms, picks up, serves those in need — and the impact is logged automatically.",
    tint: "violet",
  },
];

const ROLES = [
  {
    icon: "truck",
    role: "For restaurants",
    title: "Turn waste into goodwill",
    desc: "Reduce disposal costs, strengthen your community reputation and get tax-friendly documentation — all in minutes.",
    point: "Post a donation in under a minute",
    tint: "green",
  },
  {
    icon: "handshake",
    role: "For NGOs",
    title: "Food, when you need it",
    desc: "Never miss an opportunity to feed. AI-selected donations arrive proactively, matched to what your community eats.",
    point: "Zero cold-calling, purely warm leads",
    tint: "amber",
  },
  {
    icon: "bolt",
    role: "For admins",
    title: "Keep every hand-off honest",
    desc: "Approve partners, audit the pipeline and watch live impact metrics across your entire city network.",
    point: "Full visibility, one dashboard",
    tint: "violet",
  },
];

const TESTIMONIALS = [
  {
    quote:
      "We used to throw away 40kg of daily. Now a local children’s home picks it up before we close. MealBridge changed our kitchen.",
    name: "Chef Ananya Rao",
    org: "Spice Junction",
    tint: "green",
  },
  {
    quote:
      "Donations now arrive pre-matched and ready. Our volunteers spend time feeding, not searching for food.",
    name: "Rajesh Menon",
    org: "Akshaya Trust",
    tint: "amber",
  },
  {
    quote:
      "The impact dashboard is beautiful. I can show our board exactly what we rescued, every week, in real time.",
    name: "Priya Nath",
    org: "City Food Council",
    tint: "violet",
  },
];

const STATUS_TICKS = [
  { label: "Donation posted", at: "9:42 AM" },
  { label: "AI matched NGO", at: "9:44 AM" },
  { label: "Accepted · en route", at: "9:51 AM" },
  { label: "Delivered · 38 meals", at: "10:05 AM" },
];

const MARQUEE_ITEMS = [
  "Fresh daily",
  "Zero waste",
  "Fair matchmaking",
  "Verified partners",
  "Real-time tracking",
  "Community impact",
];

/* ------------------------------------------------------------------ */
/* Page                                                                */
/* ------------------------------------------------------------------ */

export function LandingPage() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="landing">
      {/* ---------- Nav ---------- */}
      <header className={`lp-nav ${mobileOpen ? "open" : ""}`}>
        <Link to="/" className="lp-brand">
          <img className="brand-mark" src="/logo.png" alt="MealBridge AI logo" />
          <span className="lp-brand-text">
            <strong>MealBridge AI</strong>
            <small>Surplus food rescue</small>
          </span>
        </Link>
        <nav className="lp-links">
          <a href="#features">Features</a>
          <a href="#how">How it works</a>
          <a href="#roles">Who it&apos;s for</a>
          <a href="#impact">Impact</a>
        </nav>
        <div className="lp-cta">
          <button
            className="lp-theme-toggle"
            onClick={toggleTheme}
            aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
            title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
          >
            {theme === "dark" ? <SunIcon /> : <MoonIcon />}
            <span>{theme === "dark" ? "Light" : "Dark"}</span>
          </button>
          <Link to="/login" className="lp-link-btn">
            Sign in
          </Link>
          <Link to="/signup" className="btn btn-primary">
            Get started
          </Link>
        </div>
        <button
          className="lp-burger"
          aria-label="Toggle menu"
          onClick={() => setMobileOpen((v) => !v)}
        >
          <span />
          <span />
          <span />
        </button>
      </header>

      {/* ---------- Hero ---------- */}
      <section className="lp-hero">
        <div className="orb orb-a" />
        <div className="orb orb-b" />
        <div className="orb orb-c" />
        <div className="lp-hero-inner">
          <div className="lp-hero-copy">
            <Reveal>
              <div className="lp-pill">
                <span className="lp-pill-dot" />
                AI-powered surplus food rescue
              </div>
            </Reveal>
            <Reveal delay={100}>
              <h1>
                Surplus food, <span className="grad-text">brilliantly</span> rerouted.
              </h1>
            </Reveal>
            <Reveal delay={200}>
              <p className="lp-lead">
                MealBridge AI connects restaurants with verified NGOs in seconds —
                an intelligent engine that turns leftover meals into life-changing
                donations, instead of landfill.
              </p>
            </Reveal>
            <Reveal delay={300}>
              <div className="lp-hero-actions">
                <Link to="/signup" className="btn btn-primary btn-lg">
                  Start donating <Icon name="arrow" />
                </Link>
                <Link to="/login" className="btn btn-glass btn-lg">
                  Explore the platform
                </Link>
              </div>
            </Reveal>
            <Reveal delay={400}>
              <div className="lp-hero-trust">
                <span className="lp-trust-avatars">
                  <span>SA</span>
                  <span>AR</span>
                  <span>PK</span>
                  <span>+</span>
                </span>
                <span>
                  Trusted by <strong>470+</strong> organizations across the city
                </span>
              </div>
            </Reveal>
          </div>

          <Reveal delay={200} className="lp-hero-visual">
            <div className="lp-demo">
              <div className="lp-demo-head">
                <span className="lp-demo-title">
                  <Icon name="bolt" /> Live pickup
                </span>
                <span className="lp-demo-badge">AI MATCHED</span>
              </div>
              <div className="lp-demo-meal">
                <div className="lp-demo-emoji">🍛</div>
                <div>
                  <strong>Vegetable Thali &amp; Rice</strong>
                  <span>Spice Junction · 38 meals available</span>
                </div>
              </div>
              <div className="lp-demo-match">
                <div className="lp-demo-match-pct">96%</div>
                <div>
                  <span>Best match</span>
                  <strong>Akshaya Trust</strong>
                </div>
                <span className="lp-demo-pickup">
                  Pickup in <b>42 min</b>
                </span>
              </div>
              <div className="lp-demo-timeline">
                {STATUS_TICKS.map((t, i) => (
                  <div className="lp-demo-tick" key={t.label}>
                    <span className={`lp-demo-dot step-${i + 1}`} />
                    <span>{t.label}</span>
                    <em>{t.at}</em>
                  </div>
                ))}
              </div>
              <div className="lp-demo-ring" />
            </div>
          </Reveal>
        </div>

        {/* Hero stats band */}
        <div className="lp-hero-stats">
          {HERO_STATS.map((s) => (
            <div className="lp-hero-stat" key={s.label}>
              <Icon name={s.icon} />
              <Counter value={s.value} suffix={s.suffix} />
              <span>{s.label}</span>
            </div>
          ))}
        </div>
      </section>

      {/* ---------- Marquee ---------- */}
      <div className="lp-marquee">
        <div className="lp-marquee-track">
          {[0, 1].map((dup) => (
            <div className="lp-marquee-group" key={dup} aria-hidden={dup === 1}>
              {MARQUEE_ITEMS.map((item) => (
                <span className="lp-marquee-item" key={`${dup}-${item}`}>
                  <Icon name="leaf" /> {item}
                </span>
              ))}
            </div>
          ))}
        </div>
      </div>

      {/* ---------- Features ---------- */}
      <section className="lp-section" id="features">
        <div className="lp-head">
          <Reveal>
            <span className="lp-eyebrow">Why MealBridge</span>
          </Reveal>
          <Reveal delay={80}>
            <h2>
              Food rescue, <span className="grad-text">engineered to scale</span>
            </h2>
          </Reveal>
          <Reveal delay={160}>
            <p>
              Every feature is built around one goal: getting good food to good
              people with zero friction.
            </p>
          </Reveal>
        </div>
        <div className="lp-features">
          {FEATURES.map((f, i) => (
            <Reveal delay={i * 90} key={f.title}>
              <article className="lp-feature-card">
                <span className={`lp-feature-icon tint-${f.tint}`}>
                  <Icon name={f.icon} />
                </span>
                <h3>{f.title}</h3>
                <p>{f.desc}</p>
              </article>
            </Reveal>
          ))}
        </div>
      </section>

      {/* ---------- How it works ---------- */}
      <section className="lp-section lp-alt" id="how">
        <div className="lp-head">
          <Reveal>
            <span className="lp-eyebrow">How it works</span>
          </Reveal>
          <Reveal delay={80}>
            <h2>
              From kitchen surplus to <span className="grad-text">served plates</span>
            </h2>
          </Reveal>
        </div>
        <div className="lp-steps">
          {STEPS.map((s, i) => (
            <Reveal delay={i * 120} key={s.step}>
              <article className="lp-step">
                <span className={`lp-step-icon tint-${s.tint}`}>
                  <Icon name={s.icon} />
                </span>
                <span className={`lp-step-num tint-${s.tint}`}>{s.step}</span>
                <h3>{s.title}</h3>
                <p>{s.desc}</p>
              </article>
            </Reveal>
          ))}
        </div>
      </section>

      {/* ---------- Roles ---------- */}
      <section className="lp-section" id="roles">
        <div className="lp-head">
          <Reveal>
            <span className="lp-eyebrow">Built for everyone</span>
          </Reveal>
          <Reveal delay={80}>
            <h2>
              One platform, <span className="grad-text">three communities</span>
            </h2>
          </Reveal>
        </div>
        <div className="lp-roles">
          {ROLES.map((r, i) => (
            <Reveal delay={i * 100} key={r.role}>
              <article className="lp-role-card">
                <span className={`lp-role-icon tint-${r.tint}`}>
                  <Icon name={r.icon} />
                </span>
                <span className={`lp-role-tag tint-${r.tint}`}>{r.role}</span>
                <h3>{r.title}</h3>
                <p>{r.desc}</p>
                <span className={`lp-role-point`}>
                  <Icon name="check" /> {r.point}
                </span>
              </article>
            </Reveal>
          ))}
        </div>
      </section>

      {/* ---------- Impact ---------- */}
      <section className="lp-impact" id="impact">
        <div className="orb orb-d" />
        <div className="lp-impact-inner">
          <Reveal>
            <div className="lp-impact-copy">
              <span className="lp-eyebrow light">Measurable impact</span>
              <h2>
                Every plate counted. <br />
                Every journey <span className="grad-text">tracked.</span>
              </h2>
              <ul className="lp-impact-list">
                <li>
                  <Icon name="check" /> Food waste down an average of <b>61%</b> per partner kitchen
                </li>
                <li>
                  <Icon name="check" /> Median match-to-pickup time of <b>38 minutes</b>
                </li>
                <li>
                  <Icon name="check" /> Every hand-off verified by both parties
                </li>
              </ul>
            </div>
          </Reveal>
          <Reveal delay={150}>
            <div className="lp-impact-card">
              <div className="lp-impact-metric">
                <Icon name="leaf" />
                <span>
                  <Counter value={48600} suffix="+" />
                  meals rescued
                </span>
              </div>
              <div className="lp-impact-metric">
                <Icon name="chart" />
                <span>
                  <Counter value={2.7} decimals={1} suffix="k" prefix="~" />
                  tonnes CO₂ avoided
                </span>
              </div>
              <div className="lp-impact-card-bars">
                <div className="lp-bar-row">
                  <span>Donations listed</span>
                  <div className="lp-bar-track">
                    <div className="lp-bar-fill" style={{ width: "100%" }} />
                  </div>
                  <b>12.4k</b>
                </div>
                <div className="lp-bar-row">
                  <span>Successfully matched</span>
                  <div className="lp-bar-track">
                    <div className="lp-bar-fill" style={{ width: "87%" }} />
                  </div>
                  <b>10.8k</b>
                </div>
                <div className="lp-bar-row">
                  <span>Delivered &amp; verified</span>
                  <div className="lp-bar-track">
                    <div className="lp-bar-fill" style={{ width: "79%" }} />
                  </div>
                  <b>9.8k</b>
                </div>
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      {/* ---------- Testimonials ---------- */}
      <section className="lp-section">
        <div className="lp-head">
          <Reveal>
            <span className="lp-eyebrow">Loved on the ground</span>
          </Reveal>
          <Reveal delay={80}>
            <h2>
              Real words from the <span className="grad-text">bridge community</span>
            </h2>
          </Reveal>
        </div>
        <div className="lp-testimonials">
          {TESTIMONIALS.map((t, i) => (
            <Reveal delay={i * 100} key={t.name}>
              <figure className="lp-quote">
                <span className={`lp-quote-icon tint-${t.tint}`}>“</span>
                <blockquote>{t.quote}</blockquote>
                <figcaption>
                  <strong>{t.name}</strong>
                  <span>{t.org}</span>
                </figcaption>
              </figure>
            </Reveal>
          ))}
        </div>
      </section>

      {/* ---------- CTA ---------- */}
      <section className="lp-section">
        <Reveal>
          <div className="lp-cta-band">
            <div className="lp-cta-glow" />
            <h2>Ready to bridge the plate gap?</h2>
            <p>
              Join restaurants and NGOs already moving thousands of meals a month.
              It takes less than a minute to sign up.
            </p>
            <div className="lp-hero-actions">
              <Link to="/signup" className="btn btn-primary btn-lg">
                Create your account
              </Link>
              <Link to="/login" className="btn btn-glass btn-lg">
                I already have one
              </Link>
            </div>
          </div>
        </Reveal>
      </section>

      {/* ---------- Footer ---------- */}
      <footer className="lp-footer">
        <div className="lp-footer-inner">
          <Link to="/" className="lp-brand">
            <img className="brand-mark" src="/logo.png" alt="MealBridge AI logo" />
            <span className="lp-brand-text">
              <strong>MealBridge AI</strong>
              <small>Surplus food rescue</small>
            </span>
          </Link>
          <div className="lp-footer-links">
            <a href="#features">Features</a>
            <a href="#how">How it works</a>
            <a href="#roles">Who it&apos;s for</a>
            <a href="#impact">Impact</a>
            <Link to="/login">Sign in</Link>
            <Link to="/signup">Sign up</Link>
          </div>
          <p className="lp-footer-note">
            © {new Date().getFullYear()} MealBridge AI · Connecting surplus food with those who need it most.
          </p>
        </div>
      </footer>
    </div>
  );
}