"use client";

import { useEffect, useState, useCallback } from "react";
import AppShell from "@/components/AppShell";
import { api, Profile } from "@/lib/api";

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState("");
  const [dragOver, setDragOver] = useState(false);

  useEffect(() => {
    api
      .getProfile()
      .then(setProfile)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handleUpload = useCallback(async (file: File) => {
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setMessage("[ERROR] Only PDF files are supported");
      return;
    }

    setUploading(true);
    setMessage("");

    try {
      const result = await api.uploadResume(file);
      setProfile(result.profile);
      setMessage(`[SUCCESS] ${result.message}`);
    } catch (e) {
      setMessage(`[ERROR] Upload failed: ${e instanceof Error ? e.message : "Unknown error"}`);
    } finally {
      setUploading(false);
    }
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) handleUpload(file);
    },
    [handleUpload]
  );

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleUpload(file);
    },
    [handleUpload]
  );

  const structured = profile?.resume_structured;

  return (
    <AppShell>
      <div className="page-header">
        <h1>~/profile</h1>
        <p>Manage your resume profile parsed by Gemini AI</p>
      </div>

      <div className="grid-2" style={{ alignItems: "start", gap: "var(--space-lg)", marginBottom: "var(--space-lg)" }}>
        {/* Left Column: Console Upload Drop Area */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div className="console-container">
            <div className="console-header">
              <div style={{ display: "flex", gap: 6 }}>
                <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#ef4444" }} />
                <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#f59e0b" }} />
                <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#10b981" }} />
              </div>
              <div className="console-title">upload_resume.sh</div>
            </div>

            <label
              className={`file-upload ${dragOver ? "active" : ""}`}
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              style={{ border: "none", background: "transparent", padding: 48 }}
            >
              <input
                type="file"
                accept=".pdf"
                onChange={handleFileInput}
                style={{ display: "none" }}
                id="resume-upload"
              />
              <div className="upload-icon">
                {uploading ? (
                  <div className="loading-spinner" />
                ) : (
                  <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ display: "inline-block" }}>
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                    <polyline points="14 2 14 8 20 8" />
                    <line x1="16" y1="13" x2="8" y2="13" />
                    <line x1="16" y1="17" x2="8" y2="17" />
                    <line x1="10" y1="9" x2="8" y2="9" />
                  </svg>
                )}
              </div>
              <div className="upload-text">
                {uploading
                  ? "$ executing gemini-parser-api..."
                  : "$ drop resume.pdf here or click to browse"}
              </div>
              <div className="upload-hint">
                [SUPPORTED: PDF FILES ONLY]
              </div>
            </label>
          </div>

          {message && (
            <div
              style={{
                padding: "10px 14px",
                borderRadius: "var(--radius-md)",
                border: "1px solid var(--border-subtle)",
                fontFamily: "var(--font-mono)",
                fontSize: "0.8rem",
                background: message.startsWith("[SUCCESS]") ? "rgba(0, 255, 102, 0.05)" : "rgba(255, 62, 62, 0.05)",
                color: message.startsWith("[SUCCESS]") ? "var(--accent-success)" : "var(--accent-danger)",
              }}
            >
              {message}
            </div>
          )}

          {/* Profile Overview Card */}
          {structured && (
            <div className="card">
              <div className="card-header">
                <h3 className="card-title">Identity Details</h3>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 12, fontFamily: "var(--font-mono)", fontSize: "0.85rem" }}>
                <div>
                  <span style={{ color: "var(--text-tertiary)" }}>NAME:</span>{" "}
                  <span style={{ fontWeight: 600 }}>{profile?.name || "Not extracted"}</span>
                </div>
                <div>
                  <span style={{ color: "var(--text-tertiary)" }}>EMAIL:</span>{" "}
                  <span style={{ fontWeight: 600 }}>{profile?.email || "Not extracted"}</span>
                </div>
                <div>
                  <span style={{ color: "var(--text-tertiary)" }}>FILE:</span>{" "}
                  <span style={{ color: "var(--accent-secondary)" }}>
                    {profile?.resume_pdf_path?.split("/").pop() || "None"}
                  </span>
                </div>
                <div>
                  <span style={{ color: "var(--text-tertiary)" }}>UPDATED:</span>{" "}
                  <span>{profile?.updated_at ? new Date(profile.updated_at).toLocaleString() : "Never"}</span>
                </div>
              </div>
            </div>
          )}

          {/* Active Session Control */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Session Configuration</h3>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 12, fontFamily: "var(--font-mono)", fontSize: "0.85rem" }}>
              <div>
                <span style={{ color: "var(--text-tertiary)" }}>ACTIVE PASSCODE:</span>{" "}
                <span style={{ color: "var(--accent-primary)", textShadow: "0 0 8px var(--accent-primary-glow)", fontWeight: "bold" }}>
                  {typeof window !== "undefined" ? localStorage.getItem("api_token") || "default" : "default"}
                </span>
              </div>
              <p style={{ color: "var(--text-secondary)", fontSize: "0.75rem", lineHeight: 1.4, margin: "4px 0" }}>
                Workspace data is completely isolated by this passcode. Use another passcode to create/access a separate dashboard.
              </p>
              <button
                onClick={() => {
                  localStorage.removeItem("api_token");
                  window.location.reload();
                }}
                className="btn btn-primary"
                style={{ 
                  alignSelf: "flex-start",
                  borderColor: "var(--accent-danger)",
                  color: "var(--accent-danger)",
                  background: "rgba(255, 62, 62, 0.05)",
                  fontSize: "0.75rem",
                  padding: "8px 14px",
                  cursor: "pointer",
                }}
              >
                [SWITCH PROFILE / LOG OUT]
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: Console JSON Log Inspector */}
        <div className="console-container">
          <div className="console-header">
            <div className="console-title">sande@employment:~/profile/resume_data.json</div>
            {structured && <span className="tag tag-success">Active</span>}
          </div>
          <div
            className="console-logs"
            style={{
              minHeight: 460,
              maxHeight: 600,
              background: "#181817",
              color: "#e2e8f0",
              overflowY: "auto",
              padding: "16px",
              fontFamily: "var(--font-mono)",
              fontSize: "0.8rem",
            }}
          >
            {loading ? (
              <div style={{ color: "#a8a29e" }}>Loading resume profile...</div>
            ) : structured ? (
              <pre style={{ whiteSpace: "pre-wrap" }}>
                {JSON.stringify(structured, null, 2)}
              </pre>
            ) : (
              <div style={{ color: "#a8a29e" }}>
                No resume data parsed.<br />
                Run drop-resume.sh on the left panel to populate AI profile configurations.
              </div>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
