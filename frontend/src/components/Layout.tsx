import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { api } from "../lib/api";
import { initials } from "../lib/format";
import type { NotificationItem } from "../lib/types";

const NAV: { to: string; label: string; roles: string[]; icon: string }[] = [
  { to: "/", label: "Dashboard", roles: ["donor", "ngo", "admin"], icon: "▦" },
  { to: "/donations/new", label: "Post Donation", roles: ["donor"], icon: "＋" },
  { to: "/donations", label: "My Donations", roles: ["donor"], icon: "◫" },
  { to: "/ngo/available", label: "Available Donations", roles: ["ngo"], icon: "◫" },
  { to: "/ngo/accepted", label: "Accepted Donations", roles: ["ngo"], icon: "✓" },
  { to: "/admin/verifications", label: "Verifications", roles: ["admin"], icon: "🛡" },
  { to: "/admin/impact", label: "Impact Analytics", roles: ["admin"], icon: "📊" },
  { to: "/admin/restaurants", label: "Restaurants", roles: ["admin"], icon: "🍽" },
  { to: "/admin/ngos", label: "NGOs", roles: ["admin"], icon: "🤝" },
  { to: "/admin/donations", label: "All Donations", roles: ["admin"], icon: "◫" },
  { to: "/notifications", label: "Notifications", roles: ["donor", "ngo", "admin"], icon: "🔔" },
  { to: "/settings", label: "Settings", roles: ["donor", "ngo", "admin"], icon: "⚙" },
];

export function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    if (!user) return;
    api
      .notifications()
      .then(setNotifications)
      .catch(() => setNotifications([]));
  }, [user, location.pathname]);

  const unread = notifications.filter((n) => !n.read_at).length;
  const roleLabel = user ? `${user.role[0]?.toUpperCase()}${user.role.slice(1)}` : "";

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  if (!user) return null;

  const items = NAV.filter((n) => n.roles.includes(user.role));

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <span className="brand-mark">MB</span>
          <div>
            <div className="brand-name">MealBridge AI</div>
            <div className="brand-sub">Surplus food rescue</div>
          </div>
        </div>
        <nav className="sidebar-nav">
          {items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}
              end={item.to === "/"}
            >
              <span className="nav-icon">{item.icon}</span>
              <span className="nav-label">{item.label}</span>
              {item.to === "/notifications" && unread > 0 && (
                <span className="nav-count">{unread}</span>
              )}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className="sidebar-role">Signed in as {roleLabel}</div>
        </div>
      </aside>

      <div className="main-area">
        <header className="topbar">
          <div className="topbar-title">
            <span className="role-chip">{roleLabel}</span>
          </div>
          <div className="topbar-actions">
            <button
              className="icon-btn"
              onClick={() => navigate("/notifications")}
              aria-label="Notifications"
              title="Notifications"
            >
              <span className="bell">🔔</span>
              {unread > 0 && <span className="bell-dot">{unread}</span>}
            </button>
            <div className="user-menu">
              <button
                className="avatar-btn"
                onClick={() => setMenuOpen((v) => !v)}
                aria-label="Account menu"
              >
                {user.avatar_url ? (
                  <img src={user.avatar_url} alt="Avatar" className="avatar-img" />
                ) : (
                  <span className="avatar">{initials(user.first_name || user.email)}</span>
                )}
              </button>
              {menuOpen && (
                <div className="user-dropdown">
                  <div className="dropdown-user">
                    <strong>{user.first_name || user.email}</strong>
                    <span>{user.email}</span>
                  </div>
                  <button
                    onClick={() => {
                      setMenuOpen(false);
                      navigate("/settings");
                    }}
                  >
                    Profile &amp; Settings
                  </button>
                  <button onClick={handleLogout} className="danger">
                    Sign out
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        <main className="content">
          <Outlet />
        </main>
      </div>

    </div>
  );
}
