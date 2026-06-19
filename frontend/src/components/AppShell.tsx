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
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);

  useEffect(() => {
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
      disconnect();
    };
  }, []);

  return (
    <div className="app-layout">
      {/* Mobile Top Bar */}
      <header className="mobile-header">
        <button className="hamburger-btn" onClick={() => setIsMobileNavOpen(!isMobileNavOpen)} aria-label="Toggle Navigation">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="3" y1="12" x2="21" y2="12" />
            <line x1="3" y1="6" x2="21" y2="6" />
            <line x1="3" y1="18" x2="21" y2="18" />
          </svg>
        </button>
        <div className="mobile-brand">
          <span>employment</span>
        </div>
        <div style={{ width: 36 }} /> {/* spacer to balance hamburger */}
      </header>

      {/* Sidebar Overlay for Mobile Backdrop */}
      {isMobileNavOpen && (
        <div className="sidebar-overlay" onClick={() => setIsMobileNavOpen(false)} />
      )}

      {/* Sidebar */}
      <aside className={`sidebar ${isMobileNavOpen ? "open" : ""}`}>
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
              onClick={() => setIsMobileNavOpen(false)}
            >
              <span className="nav-icon">{item.icon}</span>
              <span>{item.label}</span>
            </Link>
          ))}
        </nav>

        <div style={{ padding: "0 16px 16px", marginTop: "auto" }}>
          <div
            className="glass-card"
            style={{ 
              padding: "12px", 
              marginBottom: 12, 
              borderLeft: "3px solid var(--accent-primary)",
              background: "rgba(0, 255, 102, 0.02)",
              textAlign: "left"
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
              <span style={{ fontSize: "0.7rem", color: "var(--text-tertiary)", fontFamily: "var(--font-mono)" }}>
                AGENT_DAEMON
              </span>
              <span className="pulse" style={{ display: "inline-block", width: 6, height: 6, borderRadius: "50%", background: "var(--accent-primary)", boxShadow: "0 0 8px var(--accent-primary)" }} />
            </div>
            
            <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.72rem", color: "var(--text-secondary)", display: "flex", flexDirection: "column", gap: 3 }}>
              <div>
                <span style={{ color: "var(--text-tertiary)" }}>STATE:</span>{" "}
                <span style={{ color: "var(--accent-primary)", fontWeight: "bold" }}>ACTIVE (24/7)</span>
              </div>
              <div>
                <span style={{ color: "var(--text-tertiary)" }}>CYCLE:</span>{" "}
                <span>DAEMON_IDLE_POLL</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", marginTop: 4, paddingTop: 4, borderTop: "1px dashed var(--border-subtle)" }}>
                <span><span style={{ color: "var(--text-tertiary)" }}>LOAD:</span> 0.08</span>
                <span><span style={{ color: "var(--text-tertiary)" }}>PING:</span> 12ms</span>
              </div>
            </div>
          </div>
          <div 
            style={{ 
              fontFamily: "var(--font-mono)", 
              fontSize: "0.72rem", 
              color: "var(--text-tertiary)", 
              textAlign: "center",
              borderTop: "1px dashed var(--border-subtle)",
              paddingTop: 12,
              marginTop: 16,
              letterSpacing: "1px",
              textTransform: "uppercase"
            }}
          >
            <span style={{ color: "var(--accent-primary)", textShadow: "0 0 10px var(--accent-primary)" }}>⚡</span> SYSTEM CRAFTED BY <a href="https://github.com/sandeeproyy" target="_blank" rel="noopener noreferrer" style={{ color: "var(--text-primary)", fontWeight: "bold", textDecoration: "none", borderBottom: "1px dashed var(--accent-primary)", transition: "var(--transition-fast)" }} className="footer-link">SANDY</a>
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
