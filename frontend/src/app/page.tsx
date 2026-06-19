"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import AppShell from "@/components/AppShell";
import { api, DashboardStats, Profile, connectNotifications } from "@/lib/api";
import Link from "next/link";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionMessage, setActionMessage] = useState("");
  const [showResetConfirm, setShowResetConfirm] = useState(false);

  // Chatbot State
  const [messages, setMessages] = useState<Message[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const [suggestedReplies, setSuggestedReplies] = useState<string[]>([]);

  // Helper to fetch statistics
  const fetchStats = useCallback(() => {
    api
      .getDashboard()
      .then((data) => {
        setStats(data);
        setError("");
      })
      .catch((e) => {
        setError("Failed to fetch dashboard statistics");
      });
  }, []);

  // Fetch initial profile and stats
  const loadProfileAndStats = useCallback(async () => {
    try {
      const prof = await api.getProfile();
      setProfile(prof);
      
      const dashboardStats = await api.getDashboard();
      setStats(dashboardStats);

      // Initialize chat based on profile state
      if (prof.resume_pdf_path) {
        setMessages([
          {
            role: "assistant",
            content: `Welcome, ${prof.name || "candidate"}. Your professional profile has been successfully integrated. Let's configure your search parameters. What type of roles are you seeking?`
          }
        ]);
        setSuggestedReplies(["Full-time", "Internship", "Both"]);
      } else {
        setMessages([
          {
            role: "assistant",
            content: "Systems online. Please upload your resume (PDF) to begin, and I will target matching roles for you."
          }
        ]);
        setSuggestedReplies([]);
      }
    } catch (e: any) {
      setError(e.message || "Failed to load dashboard data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    setLoading(true);
    loadProfileAndStats();

    // Listen for WebSocket notifications
    const disconnect = connectNotifications((data) => {
      fetchStats();
    });

    return disconnect;
  }, [loadProfileAndStats, fetchStats]);

  // Periodic polling for scanner/scoring status and updates
  useEffect(() => {
    let intervalId: NodeJS.Timeout;
    
    const poll = () => {
      api.getDashboard().then((data) => {
        setStats(data);
      }).catch(console.error);
    };

    // Determine poll interval based on status (3s if active, 15s if idle)
    const intervalTime = (stats?.is_scanning || stats?.is_scoring) ? 3000 : 15000;
    
    intervalId = setInterval(poll, intervalTime);
    
    return () => clearInterval(intervalId);
  }, [stats?.is_scanning, stats?.is_scoring]);

  // Autoscroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Handle Resume Upload directly from Chat
  const handleResumeUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setMessages((prev) => [...prev, { role: "user", content: `[Uploaded Resume: ${file.name}]` }]);
    
    try {
      const result = await api.uploadResume(file);
      const updatedProfile = result.profile;
      setProfile(updatedProfile);

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Curriculum vitae successfully parsed. Confirmed candidate profile: ${updatedProfile.name}. To formulate a precise pipeline, please specify your desired locations, domains of interest, and employment types (internships or full-time roles).`
        }
      ]);
      fetchStats();
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Upload failed: ${err.message || "Could not parse file"}. Please try again.`
        }
      ]);
    } finally {
      setUploading(false);
    }
  };

  // Submit Chat Message
  const handleChatSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const input = chatInput.trim();
    if (!input || chatLoading) return;

    const userMessage: Message = { role: "user", content: input };
    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);
    setChatInput("");
    setChatLoading(true);

    try {
      // Call LLM conversational preferences endpoint
      const result = await api.chatbotChat(updatedMessages);
      
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: result.response }
      ]);
      setSuggestedReplies(result.suggested_replies || []);

      if (result.preference_update) {
        setActionMessage("[PREFERENCES_UPDATED] Scanner criteria calibrated.");
        setTimeout(() => setActionMessage(""), 3000);
        fetchStats();
      }
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "I encountered a processing error. Please try again." }
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  // Handle Suggested Reply Click
  const handleSuggestedReplyClick = async (reply: string) => {
    if (chatLoading) return;

    const userMessage: Message = { role: "user", content: reply };
    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);
    setChatLoading(true);

    try {
      const result = await api.chatbotChat(updatedMessages);
      
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: result.response }
      ]);
      setSuggestedReplies(result.suggested_replies || []);

      if (result.preference_update) {
        setActionMessage("[PREFERENCES_UPDATED] Scanner criteria calibrated.");
        setTimeout(() => setActionMessage(""), 3000);
        fetchStats();
      }
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "I encountered a processing error. Please try again." }
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  // Run Discovery Crawler Scan
  const triggerScan = async () => {
    setActionMessage("Initiating job board crawler daemon...");
    try {
      const res = await api.triggerDiscovery();
      setActionMessage(`[SUCCESS] Discovery triggered (Task: ${res.task_id || "Active"})`);
      setTimeout(() => setActionMessage(""), 3000);
    } catch (err) {
      setActionMessage("[ERROR] Discovery trigger failed.");
    }
  };

  // Score newly scraped jobs
  const triggerScoring = async () => {
    setActionMessage("Recalculating job match weights...");
    try {
      const res = await api.triggerScoring();
      setActionMessage(`[SUCCESS] Matching triggered (Task: ${res.task_id || "Active"})`);
      setTimeout(() => setActionMessage(""), 3000);
    } catch (err) {
      setActionMessage("[ERROR] Matching trigger failed.");
    }
  };

  // Reset database completely
  const handleResetData = async () => {
    setShowResetConfirm(false);
    setActionMessage("Erasing database and files...");
    try {
      await api.resetAllData();
      window.location.reload();
    } catch (err) {
      setActionMessage("[ERROR] Database purge failed.");
    }
  };

  if (loading) {
    return (
      <AppShell>
        <div className="empty-state">
          <div className="loading-spinner" />
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="page-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h1>~/dashboard</h1>
          <p>Conversational assistant & pipeline controller for your search agent</p>
        </div>
        {actionMessage && (
          <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.8rem", color: "var(--accent-primary)" }}>
            {actionMessage}
          </span>
        )}
      </div>

      <div className="dashboard-grid">
        {/* Left Column: Conversational AI Onboarding Assistant */}
        <div className="card" style={{ display: "flex", flexDirection: "column", height: "550px", padding: 0, overflow: "hidden" }}>
          <div className="card-header" style={{ borderBottom: "1px solid var(--border-subtle)", padding: "12px 16px" }}>
            <h3 className="card-title" style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span className="pulse-dot" style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--accent-success)" }} />
              AI Search Assistant
            </h3>
            {profile?.resume_pdf_path && (
              <span className="tag tag-success" style={{ fontSize: "0.7rem" }}>Resume Structured</span>
            )}
          </div>

          {/* Messages Container */}
          <div style={{ flex: 1, padding: "16px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "12px" }}>
            {messages.map((msg, i) => (
              <div
                key={i}
                style={{
                  display: "flex",
                  justifyContent: msg.role === "user" ? "flex-end" : "flex-start",
                }}
              >
                <div
                  style={{
                    maxWidth: "80%",
                    background: msg.role === "user" ? "rgba(37, 99, 235, 0.15)" : "var(--bg-secondary)",
                    border: msg.role === "user" ? "1px solid var(--accent-primary)" : "1px solid var(--border-subtle)",
                    padding: "10px 14px",
                    borderRadius: "var(--radius-md)",
                    fontSize: "0.85rem",
                    lineHeight: 1.5,
                    fontFamily: msg.role === "assistant" ? "var(--font-mono)" : "inherit",
                    color: msg.role === "user" ? "var(--text-primary)" : "var(--text-secondary)",
                    whiteSpace: "pre-wrap",
                  }}
                >
                  {msg.content}
                </div>
              </div>
            ))}
            {chatLoading && (
              <div style={{ display: "flex", justifyContent: "flex-start" }}>
                <div style={{ background: "var(--bg-secondary)", border: "1px solid var(--border-subtle)", padding: "10px 14px", borderRadius: "var(--radius-md)" }}>
                  <div className="loading-spinner" style={{ width: 16, height: 16, borderWidth: 2 }} />
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Prompt Upload overlay or Input */}
          <div style={{ padding: "12px 16px", borderTop: "1px solid var(--border-subtle)", background: "var(--bg-primary)", display: "flex", flexDirection: "column", gap: 8 }}>
            {!profile?.resume_pdf_path && (
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "6px 10px", background: "rgba(255, 176, 0, 0.05)", border: "1px dashed var(--accent-warning)", borderRadius: "var(--radius-sm)", marginBottom: 4 }}>
                <span style={{ fontSize: "0.72rem", color: "var(--accent-warning)", fontFamily: "var(--font-mono)" }}>
                  Resume missing: scoring & tailoring disabled
                </span>
                <input
                  type="file"
                  id="chat-resume-upload"
                  accept=".pdf"
                  onChange={handleResumeUpload}
                  style={{ display: "none" }}
                  disabled={uploading}
                />
                <label
                  htmlFor="chat-resume-upload"
                  style={{
                    cursor: uploading ? "not-allowed" : "pointer",
                    fontSize: "0.72rem",
                    color: "var(--accent-primary)",
                    fontWeight: 700,
                    textDecoration: "underline",
                    fontFamily: "var(--font-mono)"
                  }}
                >
                  {uploading ? "Uploading..." : "[UPLOAD RESUME]"}
                </label>
              </div>
            )}
            {suggestedReplies.length > 0 && (
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 8 }}>
                {suggestedReplies.map((reply) => (
                  <button
                    key={reply}
                    type="button"
                    className="btn btn-sm btn-ghost"
                    onClick={() => handleSuggestedReplyClick(reply)}
                    disabled={chatLoading}
                    style={{
                      fontSize: "0.75rem",
                      padding: "4px 10px",
                      background: "var(--bg-secondary)",
                      border: "1px solid var(--border-subtle)",
                      color: "var(--accent-secondary)",
                      cursor: "pointer",
                    }}
                  >
                    {reply}
                  </button>
                ))}
              </div>
            )}
            <form onSubmit={handleChatSubmit} style={{ display: "flex", gap: 8 }}>
              <input
                className="input"
                placeholder={profile?.resume_pdf_path ? "Ask Assistant or specify target parameters..." : "Configure preferences or type here..."}
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                disabled={chatLoading}
                style={{ flex: 1, fontSize: "0.85rem", padding: "8px 12px" }}
              />
              <button type="submit" className="btn btn-primary" disabled={chatLoading} style={{ fontSize: "0.85rem", padding: "8px 16px" }}>
                Send
              </button>
            </form>
          </div>
        </div>

        {/* Right Column: Console Stats & Controls */}
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-md)" }}>
          {/* Active Search/Scoring Pipeline Status (Loading Indicator) */}
          {(stats?.is_scanning || stats?.is_scoring) && (
            <div className="pipeline-status-card">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                <h4 style={{ fontSize: "0.85rem", color: "var(--accent-primary)", margin: 0, fontFamily: "var(--font-mono)", fontWeight: 700, display: "flex", alignItems: "center", gap: 8 }}>
                  <div className="loading-spinner" style={{ width: 12, height: 12, borderWidth: "1.5px" }} />
                  ACTIVE SEARCH PIPELINE
                </h4>
                <span className="tag tag-primary" style={{ fontSize: "0.65rem", textTransform: "uppercase" }}>
                  {stats.is_scanning && stats.is_scoring ? "SCAN & SCORE" : stats.is_scanning ? "SCANNING" : "SCORING"}
                </span>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                <div className={`pipeline-step ${stats.is_scanning ? "active" : "completed"}`}>
                  <span className={`pipeline-step-icon ${stats.is_scanning ? "active animate-pulse" : "completed"}`}>
                    {stats.is_scanning ? "⚡" : "✓"}
                  </span>
                  <span>Scanning job boards & LinkedIn posts...</span>
                </div>
                <div className={`pipeline-step ${stats.is_scoring ? "active" : stats.is_scanning ? "pending" : "completed"}`}>
                  <span className={`pipeline-step-icon ${stats.is_scoring ? "active animate-pulse" : stats.is_scanning ? "pending" : "completed"}`}>
                    {stats.is_scoring ? "🧠" : stats.is_scanning ? "⋯" : "✓"}
                  </span>
                  <span>Evaluating match relevance via Gemini AI...</span>
                </div>
              </div>
              <div className="log-terminal-mini">
                <div className="log-line active">&gt; daemon process active [OK]</div>
                {stats.is_scanning && <div className="log-line">&gt; crawling public feeds...</div>}
                {stats.is_scoring && <div className="log-line">&gt; mapping profile skills with weights...</div>}
              </div>
            </div>
          )}

          {/* Quick Metrics */}
          {stats && (
            <div className="stats-grid" style={{ gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              <div className="stat-card" style={{ padding: "12px 16px" }}>
                <div className="stat-value" style={{ fontSize: "1.4rem" }}>{stats.total_jobs_discovered}</div>
                <div className="stat-label" style={{ fontSize: "0.7rem" }}>discovered</div>
              </div>
              <div className="stat-card" style={{ padding: "12px 16px" }}>
                <div className="stat-value" style={{ fontSize: "1.4rem" }}>{stats.high_match_jobs}</div>
                <div className="stat-label" style={{ fontSize: "0.7rem" }}>high match</div>
              </div>
              <div className="stat-card" style={{ padding: "12px 16px" }}>
                <div className="stat-value" style={{ fontSize: "1.4rem" }}>{stats.applications_by_status?.applied ?? 0}</div>
                <div className="stat-label" style={{ fontSize: "0.7rem" }}>applied</div>
              </div>
              <div className="stat-card" style={{ padding: "12px 16px" }}>
                <div className="stat-value" style={{ fontSize: "1.4rem" }}>{stats.applications_by_status?.interview ?? 0}</div>
                <div className="stat-label" style={{ fontSize: "0.7rem" }}>interviews</div>
              </div>
            </div>
          )}

          {/* Quick Dashboard Action Controls */}
          <div className="card" style={{ padding: "16px" }}>
            <h3 style={{ fontSize: "0.85rem", fontWeight: 700, fontFamily: "var(--font-mono)", marginBottom: 16 }}>
              SYSTEM_PIPELINE_CONTROLLER
            </h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <button className="btn-controller btn-controller-primary" style={{ width: "100%" }} onClick={triggerScan}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <polygon points="5 3 19 12 5 21 5 3" />
                </svg>
                RUN SCANNER DAEMON
              </button>
              
              <button className="btn-controller btn-controller-success" style={{ width: "100%" }} onClick={triggerScoring}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="4" y="4" width="16" height="16" rx="2" ry="2" />
                  <rect x="9" y="9" width="6" height="6" />
                  <line x1="9" y1="1" x2="9" y2="4" />
                  <line x1="15" y1="1" x2="15" y2="4" />
                  <line x1="9" y1="20" x2="9" y2="23" />
                  <line x1="15" y1="20" x2="15" y2="23" />
                  <line x1="20" y1="9" x2="23" y2="9" />
                  <line x1="20" y1="15" x2="23" y2="15" />
                  <line x1="1" y1="9" x2="4" y2="9" />
                  <line x1="1" y1="15" x2="4" y2="15" />
                </svg>
                EVALUATE MATCHES (SCORE)
              </button>
              
              {!showResetConfirm ? (
                <button className="btn-controller btn-controller-danger" style={{ width: "100%" }} onClick={() => setShowResetConfirm(true)}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="3 6 5 6 21 6" />
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                    <line x1="10" y1="11" x2="10" y2="17" />
                    <line x1="14" y1="11" x2="14" y2="17" />
                  </svg>
                  RESET DATABASE & RESTART FRESH
                </button>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 10, padding: 12, border: "1px solid var(--accent-danger)", background: "rgba(255, 62, 62, 0.05)", borderRadius: "4px" }}>
                  <div style={{ fontSize: "0.75rem", color: "var(--accent-danger)", textAlign: "center", fontFamily: "var(--font-mono)", fontWeight: 700 }}>
                    CONFIRM COMPLETE ERASURE?
                  </div>
                  <div style={{ display: "flex", gap: 8 }}>
                    <button className="btn btn-danger btn-sm" style={{ flex: 1, padding: "8px", borderRadius: "2px" }} onClick={handleResetData}>
                      [YES, RESET]
                    </button>
                    <button className="btn btn-ghost btn-sm" style={{ flex: 1, padding: "8px", borderRadius: "2px" }} onClick={() => setShowResetConfirm(false)}>
                      [CANCEL]
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Top Discoveries */}
          <div className="card" style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: "180px" }}>
            <div className="card-header" style={{ marginBottom: 12 }}>
              <h3 className="card-title">Top Matching Jobs</h3>
              <Link href="/jobs" className="tag tag-primary" style={{ fontSize: "0.7rem", textDecoration: "none" }}>
                See All
              </Link>
            </div>
            {stats?.recent_jobs && stats.recent_jobs.length > 0 ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 8, flex: 1 }}>
                {stats.recent_jobs.slice(0, 3).map((job) => (
                  <Link
                    key={job.id}
                    href={`/jobs`}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: "8px 12px",
                      borderRadius: "var(--radius-md)",
                      border: "1px solid var(--border-subtle)",
                      background: "var(--bg-secondary)",
                      textDecoration: "none",
                      fontFamily: "var(--font-mono)",
                    }}
                  >
                    <div style={{ minWidth: 0, flex: 1 }}>
                      <div style={{ fontSize: "0.8rem", fontWeight: 700, color: "var(--text-primary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {job.title}
                      </div>
                      <div style={{ fontSize: "0.75rem", color: "var(--accent-secondary)" }}>
                        {job.company}
                      </div>
                    </div>
                    <div style={{ fontWeight: 700, color: "var(--accent-primary)", fontSize: "0.8rem", marginLeft: 8 }}>
                      {Math.round(job.match_score)}%
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <div className="empty-state" style={{ padding: "20px 0" }}>
                <p style={{ fontSize: "0.8rem" }}>No jobs evaluated yet.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
