"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { api, KanbanBoard, Application, Job } from "@/lib/api";

const STATUS_COLORS: Record<string, string> = {
  pending: "var(--accent-warning)",
  applied: "var(--accent-primary)",
  interview: "var(--accent-secondary)",
  assessment: "var(--accent-purple)",
  offer: "var(--accent-success)",
  rejected: "var(--accent-danger)",
};

export default function ApplicationsPage() {
  const [board, setBoard] = useState<KanbanBoard | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedApp, setSelectedApp] = useState<Application | null>(null);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [loadingJob, setLoadingJob] = useState(false);
  const [savingNotes, setSavingNotes] = useState(false);
  const [notesText, setNotesText] = useState("");
  const [copied, setCopied] = useState(false);
  const [latexCode, setLatexCode] = useState("");
  const [copiedLatex, setCopiedLatex] = useState(false);
  const [loadingLatex, setLoadingLatex] = useState(false);
  const [showLatexViewer, setShowLatexViewer] = useState(false);

  const loadBoard = () => {
    api
      .getKanban()
      .then(setBoard)
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  const inspectApplication = async (app: Application) => {
    setSelectedApp(app);
    setNotesText(app.notes || "");
    setCopied(false);
    setLatexCode("");
    setCopiedLatex(false);
    setShowLatexViewer(false);
    setLoadingJob(true);
    setSelectedJob(null);
    try {
      const job = await api.getJob(app.job_id);
      setSelectedJob(job);
    } catch (e) {
      console.error("Failed to fetch job details for application:", e);
    } finally {
      setLoadingJob(false);
    }
  };

  const handleDrawerStatusChange = async (appId: number, newStatus: string) => {
    try {
      await api.updateApplicationStatus(appId, newStatus);
      if (selectedApp && selectedApp.id === appId) {
        setSelectedApp({ ...selectedApp, status: newStatus });
      }
      loadBoard();
    } catch (e) {
      console.error(e);
    }
  };

  const handleSaveNotes = async () => {
    if (!selectedApp) return;
    setSavingNotes(true);
    try {
      await api.updateApplicationNotes(selectedApp.id, notesText);
      setSelectedApp({ ...selectedApp, notes: notesText });
      loadBoard();
      alert("Notes saved successfully.");
    } catch (e) {
      console.error(e);
    } finally {
      setSavingNotes(false);
    }
  };

  const handleCopyCoverLetter = () => {
    if (!selectedApp?.cover_letter_text) return;
    navigator.clipboard.writeText(selectedApp.cover_letter_text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  
  const handleFetchLatex = async () => {
    if (!selectedApp) return;
    if (showLatexViewer) {
      setShowLatexViewer(false);
      return;
    }
    setLoadingLatex(true);
    try {
      const res = await api.getApplicationLatex(selectedApp.id);
      setLatexCode(res.latex);
      setShowLatexViewer(true);
    } catch (e) {
      console.error(e);
      alert("Failed to fetch LaTeX source: " + (e as Error).message);
    } finally {
      setLoadingLatex(false);
    }
  };

  const handleCopyLatex = () => {
    if (!latexCode) return;
    navigator.clipboard.writeText(latexCode);
    setCopiedLatex(true);
    setTimeout(() => setCopiedLatex(false), 2000);
  };

  useEffect(() => {
    loadBoard();
  }, []);

  const handleStatusChange = async (appId: number, newStatus: string) => {
    try {
      await api.updateApplicationStatus(appId, newStatus);
      loadBoard();
    } catch (e) {
      console.error(e);
    }
  };

  const analytics = board?.analytics;

  return (
    <AppShell>
      <div className="page-header">
        <h1>~/applications</h1>
        <p>Track progress of active application pipeline records</p>
      </div>

      {/* Analytics Panels */}
      {analytics && (
        <div className="stats-grid" style={{ marginBottom: "var(--space-lg)" }}>
          <div className="stat-card">
            <div className="stat-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                <polyline points="22,6 12,13 2,6" />
              </svg>
            </div>
            <div className="stat-card-details">
              <div className="stat-value">{analytics.total_applied}</div>
              <div className="stat-label">applied</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
                <path d="M19 10v1a7 7 0 0 1-14 0v-1" />
                <line x1="12" y1="19" x2="12" y2="23" />
                <line x1="8" y1="23" x2="16" y2="23" />
              </svg>
            </div>
            <div className="stat-card-details">
              <div className="stat-value">{analytics.total_interviews}</div>
              <div className="stat-label">interviews</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="20" x2="18" y2="10" />
                <line x1="12" y1="20" x2="12" y2="4" />
                <line x1="6" y1="20" x2="6" y2="14" />
              </svg>
            </div>
            <div className="stat-card-details">
              <div className="stat-value">{analytics.response_rate}%</div>
              <div className="stat-label">response_rate</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6" />
                <path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18" />
                <path d="M4 22h16" />
                <path d="M10 14.66V17c0 .55-.45 1-1 1H4v2h16v-2h-5c-.55 0-1-.45-1-1v-2.34" />
                <path d="M12 2a6 6 0 0 0-6 6v3.58a6 6 0 0 0 4.14 5.71 1.8 1.8 0 0 0 3.72 0A6 6 0 0 0 18 11.58V8a6 6 0 0 0-6-6z" />
              </svg>
            </div>
            <div className="stat-card-details">
              <div className="stat-value">{analytics.total_offers}</div>
              <div className="stat-label">offers</div>
            </div>
          </div>
        </div>
      )}

      {/* Kanban Board columns */}
      {loading ? (
        <div className="empty-state">
          <div className="loading-spinner" />
          <p style={{ marginTop: 16 }}>Loading tracking index...</p>
        </div>
      ) : !board?.columns ? (
        <div className="empty-state">
          <div className="empty-icon">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ display: "inline-block" }}>
              <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
              <line x1="16" y1="2" x2="16" y2="6" />
              <line x1="8" y1="2" x2="8" y2="6" />
              <line x1="3" y1="10" x2="21" y2="10" />
            </svg>
          </div>
          <h3>Board Empty</h3>
          <p>Go to ~/jobs and approve entries to build active cards.</p>
        </div>
      ) : (
        <div className="kanban-board">
          {board.columns.map((column) => (
            <div key={column.status} className="kanban-column">
              <div className="kanban-column-header">
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <span
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: "50%",
                      background: STATUS_COLORS[column.status] || "var(--text-tertiary)",
                    }}
                  />
                  <span className="kanban-column-title" style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem" }}>
                    {column.label}
                  </span>
                </div>
                <span className="kanban-column-count">{column.count}</span>
              </div>
              <div className="kanban-cards">
                {column.applications.map((app) => (
                  <div
                    key={app.id}
                    className="kanban-card"
                    onClick={() => inspectApplication(app)}
                    style={{
                      cursor: "pointer",
                      border: selectedApp?.id === app.id ? "1px solid var(--accent-primary)" : "1px solid var(--border-subtle)"
                    }}
                  >
                    <div className="card-job-title">{app.job_title || `Job #${app.job_id}`}</div>
                    <div className="card-company">{app.job_company || "Unknown"}</div>
                    
                    <div className="card-footer">
                      <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", fontWeight: 700, color: "var(--accent-primary)" }}>
                        {app.job_match_score ? `${Math.round(app.job_match_score)}%` : "N/A"}
                      </div>
                      
                      <select
                        className="input"
                        value={app.status}
                        onChange={(e) => handleStatusChange(app.id, e.target.value)}
                        onClick={(e) => e.stopPropagation()}
                        style={{
                          width: "auto",
                          padding: "2px 6px",
                          fontSize: "0.7rem",
                          background: "var(--bg-secondary)",
                          border: "1px solid var(--border-subtle)",
                        }}
                      >
                        <option value="pending">pending</option>
                        <option value="applied">applied</option>
                        <option value="interview">interview</option>
                        <option value="assessment">assessment</option>
                        <option value="offer">offer</option>
                        <option value="rejected">rejected</option>
                      </select>
                    </div>

                    {app.notes && (
                      <div
                        style={{
                          marginTop: 6,
                          paddingTop: 4,
                          borderTop: "1px dashed var(--border-subtle)",
                          fontSize: "0.75rem",
                          color: "var(--text-secondary)",
                          fontFamily: "var(--font-mono)",
                        }}
                      >
                        NOTE: {app.notes}
                      </div>
                    )}
                  </div>
                ))}
                {column.applications.length === 0 && (
                  <div
                    style={{
                      padding: 16,
                      textAlign: "center",
                      color: "var(--text-tertiary)",
                      fontFamily: "var(--font-mono)",
                      fontSize: "0.75rem",
                    }}
                  >
                    [empty]
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
      {/* Side drawer details inspector */}
      {selectedApp && (
        <div className="inspector-drawer">
          <div className="inspector-header">
            <div>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", color: "var(--text-tertiary)" }}>
                APPLICATION_RECORD = #{selectedApp.id}
              </div>
              <h2 style={{ fontFamily: "var(--font-mono)", fontSize: "1.1rem", fontWeight: 700, marginTop: 2, color: "var(--text-primary)" }}>
                {selectedApp.job_title || (selectedJob ? selectedJob.title : "Loading...")}
              </h2>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.82rem", color: "var(--accent-secondary)", marginTop: 4 }}>
                {selectedApp.job_company || (selectedJob ? selectedJob.company : "Loading...")}
              </div>
            </div>
            <button
              className="btn btn-sm btn-ghost"
              onClick={() => { setSelectedApp(null); setSelectedJob(null); }}
              style={{ padding: 6, fontSize: "0.85rem" }}
            >
              [X]
            </button>
          </div>

          <div className="inspector-body">
            {/* Status Dropdown */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.85rem", fontWeight: 700 }}>STATUS</span>
              <select
                className="input"
                value={selectedApp.status}
                onChange={(e) => handleDrawerStatusChange(selectedApp.id, e.target.value)}
                style={{ width: "auto", padding: "4px 10px" }}
              >
                <option value="pending">pending</option>
                <option value="applied">applied</option>
                <option value="interview">interview</option>
                <option value="assessment">assessment</option>
                <option value="offer">offer</option>
                <option value="rejected">rejected</option>
              </select>
            </div>

            {/* Generated Materials Section */}
            <div style={{ marginBottom: 24 }}>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", color: "var(--text-tertiary)", marginBottom: 8 }}>
                GENERATED_MATERIALS
              </div>
              <div style={{ display: "flex", gap: 10, marginBottom: 12 }}>
                <a
                  href={`http://localhost:8000/api/applications/${selectedApp.id}/resume`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-sm btn-primary"
                  style={{ flex: 1, display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 6 }}
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                    <polyline points="14 2 14 8 20 8" />
                    <line x1="16" y1="13" x2="8" y2="13" />
                    <line x1="16" y1="17" x2="8" y2="17" />
                    <polyline points="10 9 9 9 8 9" />
                  </svg>
                  View HTML Resume
                </a>
                <button
                  onClick={handleFetchLatex}
                  disabled={loadingLatex}
                  className="btn btn-sm btn-secondary"
                  style={{ flex: 1, display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 6 }}
                >
                  {loadingLatex ? (
                    <div className="loading-spinner" style={{ width: 10, height: 10 }} />
                  ) : (
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M16 18l6-6-6-6M8 6l-6 6 6 6" />
                    </svg>
                  )}
                  {showLatexViewer ? "Hide LaTeX" : "View LaTeX"}
                </button>
              </div>

              {showLatexViewer && latexCode && (
                <div style={{ marginBottom: 16 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                    <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                      TAILORED_LATEX_SOURCE
                    </span>
                    <button
                      className="btn btn-ghost"
                      onClick={handleCopyLatex}
                      style={{ fontSize: "0.7rem", padding: "2px 6px" }}
                    >
                      {copiedLatex ? "[Copied!]" : "[Copy LaTeX]"}
                    </button>
                  </div>
                  <textarea
                    readOnly
                    className="input"
                    value={latexCode}
                    style={{
                      width: "100%",
                      height: "200px",
                      background: "var(--bg-secondary)",
                      border: "1px solid var(--border-subtle)",
                      padding: 10,
                      fontSize: "0.78rem",
                      fontFamily: "var(--font-mono)",
                      color: "var(--text-secondary)",
                      lineHeight: 1.4,
                      resize: "vertical",
                    }}
                  />
                </div>
              )}

              {selectedApp.cover_letter_text ? (
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                    <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                      TAILORED_COVER_LETTER
                    </span>
                    <button
                      className="btn btn-ghost"
                      onClick={handleCopyCoverLetter}
                      style={{ fontSize: "0.7rem", padding: "2px 6px" }}
                    >
                      {copied ? "[Copied!]" : "[Copy Letter]"}
                    </button>
                  </div>
                  <div
                    style={{
                      background: "var(--bg-secondary)",
                      border: "1px solid var(--border-subtle)",
                      padding: 10,
                      fontSize: "0.78rem",
                      fontFamily: "var(--font-mono)",
                      maxHeight: 180,
                      overflowY: "auto",
                      whiteSpace: "pre-wrap",
                      color: "var(--text-secondary)",
                      lineHeight: 1.5,
                    }}
                  >
                    {selectedApp.cover_letter_text}
                  </div>
                </div>
              ) : (
                <div style={{ fontSize: "0.78rem", color: "var(--text-tertiary)", fontStyle: "italic" }}>
                  No cover letter generated
                </div>
              )}
            </div>

            {/* Notes Section */}
            <div style={{ marginBottom: 24 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", color: "var(--text-tertiary)" }}>
                  USER_NOTES
                </span>
                <button
                  className="btn btn-success"
                  onClick={handleSaveNotes}
                  disabled={savingNotes}
                  style={{ fontSize: "0.7rem", padding: "2px 8px" }}
                >
                  {savingNotes ? "Saving..." : "Save"}
                </button>
              </div>
              <textarea
                className="input"
                rows={3}
                placeholder="Add your notes about interviews, contacts, next steps..."
                value={notesText}
                onChange={(e) => setNotesText(e.target.value)}
                style={{ resize: "vertical", fontSize: "0.8rem", width: "100%" }}
              />
            </div>

            {/* Match Breakdown & Analysis Section */}
            <div>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", color: "var(--text-tertiary)", marginBottom: 8 }}>
                MATCH_QUALIFICATION_ANALYSIS
              </div>

              {loadingJob ? (
                <div style={{ padding: 16, textAlign: "center", color: "var(--text-tertiary)", fontSize: "0.8rem" }}>
                  <div className="loading-spinner" style={{ width: 14, height: 14, display: "inline-block", marginRight: 8 }} />
                  Loading relevance details...
                </div>
              ) : selectedJob ? (
                <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.85rem", fontWeight: 700 }}>RELEVANCE SCORE</span>
                    <span style={{ fontFamily: "var(--font-mono)", fontSize: "1.2rem", fontWeight: 700, color: "var(--accent-primary)" }}>
                      {Math.round(selectedJob.match_score)}%
                    </span>
                  </div>

                  {selectedJob.match_breakdown && (
                    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                      {[
                        { label: "Skills", val: selectedJob.match_breakdown.skills, max: 40, color: "var(--accent-primary)" },
                        { label: "Projects", val: selectedJob.match_breakdown.projects, max: 25, color: "var(--accent-secondary)" },
                        { label: "Education", val: selectedJob.match_breakdown.education, max: 15, color: "var(--accent-purple)" },
                        { label: "Location", val: selectedJob.match_breakdown.location, max: 10, color: "var(--accent-success)" },
                      ].map((item) => (
                        <div key={item.label} style={{ fontSize: "0.75rem", fontFamily: "var(--font-mono)" }}>
                          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                            <span>{item.label}</span>
                            <span>{item.val}/{item.max}</span>
                          </div>
                          <div style={{ height: 4, background: "var(--bg-tertiary)", position: "relative" }}>
                            <div
                              style={{
                                height: "100%",
                                background: item.color,
                                width: `${(item.val / item.max) * 100}%`,
                              }}
                            />
                          </div>
                        </div>
                      ))}

                      {selectedJob.match_breakdown.reason && (
                        <div
                          style={{
                            marginTop: 4,
                            padding: 10,
                            background: "var(--bg-secondary)",
                            border: "1px solid var(--border-subtle)",
                            fontSize: "0.78rem",
                            fontFamily: "var(--font-mono)",
                            color: "var(--text-secondary)",
                            lineHeight: 1.5,
                          }}
                        >
                          {selectedJob.match_breakdown.reason}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Skills lists */}
                  <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                    {selectedJob.match_breakdown?.matched_skills?.length ? (
                      <div>
                        <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", color: "var(--text-tertiary)", marginBottom: 4 }}>
                          MATCHED_SKILLS
                        </div>
                        <div className="skills-grid">
                          {selectedJob.match_breakdown.matched_skills.map((s, i) => (
                            <span key={i} className="skill-tag matched" style={{ fontSize: "0.7rem" }}>{s}</span>
                          ))}
                        </div>
                      </div>
                    ) : null}

                    {selectedJob.match_breakdown?.missing_skills?.length ? (
                      <div>
                        <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", color: "var(--text-tertiary)", marginBottom: 4 }}>
                          MISSING_SKILLS
                        </div>
                        <div className="skills-grid">
                          {selectedJob.match_breakdown.missing_skills.map((s, i) => (
                            <span key={i} className="skill-tag missing" style={{ fontSize: "0.7rem" }}>{s}</span>
                          ))}
                        </div>
                      </div>
                    ) : null}
                  </div>

                  {/* Job details description */}
                  <div style={{ display: "flex", flexDirection: "column", height: 180 }}>
                    <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", color: "var(--text-tertiary)", marginBottom: 4 }}>
                      JOB_DESCRIPTION
                    </div>
                    <div
                      style={{
                        flex: 1,
                        background: "var(--bg-secondary)",
                        border: "1px solid var(--border-subtle)",
                        padding: 10,
                        fontSize: "0.78rem",
                        fontFamily: "var(--font-mono)",
                        overflowY: "auto",
                        whiteSpace: "pre-wrap",
                        color: "var(--text-secondary)",
                        lineHeight: 1.5,
                      }}
                    >
                      {selectedJob.description}
                    </div>
                  </div>
                </div>
              ) : (
                <div style={{ fontSize: "0.78rem", color: "var(--text-tertiary)", fontStyle: "italic" }}>
                  No match analysis details found
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
}
