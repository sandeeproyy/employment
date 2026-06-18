"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import { useEffect, useState } from "react";
import { connectNotifications } from "@/lib/api";

const NAV_ITEMS = [
  {
    href: "/",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
        <line x1="9" y1="9" x2="15" y2="9" />
        <line x1="9" y1="13" x2="13" y2="13" />
        <line x1="9" y1="17" x2="11" y2="17" />
      </svg>
    ),
    label: "~/dashboard"
  },
  {
    href: "/profile",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
        <circle cx="12" cy="7" r="4" />
      </svg>
    ),
    label: "~/profile"
  },
  {
    href: "/jobs",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="11" cy="11" r="8" />
        <line x1="21" y1="21" x2="16.65" y2="16.65" />
      </svg>
    ),
    label: "~/jobs",
    badge: true
  },
  {
    href: "/applications",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
        <line x1="16" y1="2" x2="16" y2="6" />
        <line x1="8" y1="2" x2="8" y2="6" />
        <line x1="3" y1="10" x2="21" y2="10" />
      </svg>
    ),
    label: "~/applications"
  }
];

interface Notification {
  id: number;
  title: string;
  body: string;
  notification_type: string;
  timestamp: string;
}

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [showNotif, setShowNotif] = useState(false);
  const [isAuthorized, setIsAuthorized] = useState(true);
  const [passcode, setPasscode] = useState("");

  useEffect(() => {
    // Check if we need auth by attempting a test dashboard fetch
    const checkAuth = async () => {
      try {
        const { api } = await import("@/lib/api");
        await api.getDashboard();
        setIsAuthorized(true);
      } catch (e: any) {
        if (e.message === "unauthorized") {
          setIsAuthorized(false);
        }
      }
    };

    checkAuth();

    // Listen for unauthorized events dispatched by apiFetch
    const handleUnauthorized = () => {
      setIsAuthorized(false);
    };

    window.addEventListener("unauthorized", handleUnauthorized);

    const disconnect = connectNotifications((data) => {
      const notif: Notification = {
        id: Date.now(),
        title: data.title,
        body: data.body,
        notification_type: data.notification_type,
        timestamp: data.timestamp,
      };
      setNotifications((prev) => [notif, ...prev].slice(0, 20));
      setShowNotif(true);
      setTimeout(() => setShowNotif(false), 5000);
    });

    return () => {
      window.removeEventListener("unauthorized", handleUnauthorized);
      disconnect();
    };
  }, []);

  if (!isAuthorized) {
    const handleAuthenticate = (e: React.FormEvent) => {
      e.preventDefault();
      if (!passcode.trim()) return;
      localStorage.setItem("api_token", passcode.trim());
      window.location.reload();
    };

    return (
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          background: "linear-gradient(135deg, #050505 0%, #101015 100%)",
          height: "100vh",
          fontFamily: "var(--font-mono)",
        }}
      >
        <form
          onSubmit={handleAuthenticate}
          className="card"
          style={{
            maxWidth: 420,
            width: "90%",
            border: "1px solid var(--accent-primary)",
            padding: "var(--space-xl)",
            display: "flex",
            flexDirection: "column",
            gap: "var(--space-md)",
            background: "rgba(10, 10, 15, 0.9)",
            backdropFilter: "blur(8px)",
            boxShadow: "0 0 30px rgba(37, 99, 235, 0.2)",
            borderRadius: "var(--radius-lg)",
          }}
        >
          <div style={{ textAlign: "center" }}>
            <div style={{ display: "inline-block", background: "rgba(37, 99, 235, 0.1)", padding: "10px", borderRadius: "50%", marginBottom: 12 }}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--accent-primary)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                <path d="M7 11V7a5 5 0 0 1 10 0v4" />
              </svg>
            </div>
            <h2 style={{ color: "var(--accent-primary)", fontSize: "1.3rem", fontWeight: 700, letterSpacing: "2px", marginBottom: 8 }}>
              SYS_SECURE_WALL_v1.2
            </h2>
            <p style={{ color: "var(--text-secondary)", fontSize: "0.8rem", lineHeight: 1.6, marginBottom: 16 }}>
              Dashboard access restricted. Please enter the passcode to authenticate.
            </p>
          </div>
          
          <input
            type="password"
            className="input"
            placeholder="ENTER ACCESS PASSCODE..."
            value={passcode}
            onChange={(e) => setPasscode(e.target.value)}
            style={{
              textAlign: "center",
              letterSpacing: "3px",
              fontFamily: "var(--font-mono)",
              fontSize: "0.95rem",
              background: "var(--bg-secondary)",
              border: "1px solid var(--border-subtle)",
              color: "var(--accent-primary)",
              padding: "12px",
              borderRadius: "var(--radius-md)",
            }}
            autoFocus
          />

          <button type="submit" className="btn btn-primary" style={{ width: "100%", fontFamily: "var(--font-mono)", fontWeight: 700, padding: "12px" }}>
            [DECRYPT & AUTHENTICATE]
          </button>

          {process.env.NODE_ENV !== "production" && (
            <div style={{ 
              marginTop: 16, 
              padding: 12, 
              background: "rgba(255, 255, 255, 0.03)", 
              borderRadius: "var(--radius-sm)", 
              borderLeft: "2px solid var(--accent-secondary)",
              fontSize: "0.75rem",
              color: "var(--text-tertiary)",
              lineHeight: 1.5
            }}>
              <strong style={{ color: "var(--text-secondary)" }}>HOW TO LOG IN (DEV MODE):</strong><br />
              Enter the value of <code>API_TOKEN</code> located inside your backend <code>.env</code> file (by default, it is set to <code>supersecret</code>).
            </div>
          )}
        </form>
      </div>
    );
  }

  return (
    <div className="app-layout">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-brand">
          <h1>employment</h1>
          <p>Autonomous Agent</p>
        </div>

        <nav className="sidebar-nav">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`nav-link ${pathname === item.href ? "active" : ""}`}
            >
              <span className="nav-icon">{item.icon}</span>
              <span>{item.label}</span>
            </Link>
          ))}
          <button
            onClick={() => {
              localStorage.removeItem("api_token");
              window.location.reload();
            }}
            className="nav-link"
            style={{
              width: "100%",
              background: "none",
              border: "none",
              cursor: "pointer",
              textAlign: "left",
              color: "var(--accent-danger)",
              fontFamily: "var(--font-mono)",
              display: "flex",
              alignItems: "center",
              gap: "12px",
              padding: "10px 16px",
            }}
          >
            <span className="nav-icon" style={{ display: "flex", alignItems: "center" }}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                <path d="M7 11V7a5 5 0 0 1 10 0v4" />
              </svg>
            </span>
            <span>~/lock_session</span>
          </button>
        </nav>

        <div style={{ padding: "0 16px", marginTop: "auto" }}>
          <div
            className="glass-card pulse"
            style={{ padding: "12px", textAlign: "center" }}
          >
            <div style={{ fontSize: "0.75rem", color: "var(--text-tertiary)" }}>
              Agent Status
            </div>
            <div
              style={{
                fontSize: "0.85rem",
                fontWeight: 600,
                color: "var(--accent-success)",
                marginTop: "4px",
              }}
            >
              Running 24/7
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="main-content">{children}</main>

      {/* Notification Toast */}
      {showNotif && notifications.length > 0 && (
        <div className="notification-toast">
          <div style={{ fontWeight: 600, marginBottom: "4px" }}>
            {notifications[0].title}
          </div>
          <div
            style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}
          >
            {notifications[0].body}
          </div>
        </div>
      )}
    </div>
  );
}
