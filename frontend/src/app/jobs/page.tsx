"use client";

import { useEffect, useState, useCallback } from "react";
import AppShell from "@/components/AppShell";
import ScoreRing from "@/components/ScoreRing";
import { api, Job, JobListResponse } from "@/lib/api";

export default function JobsPage() {
  const [data, setData] = useState<JobListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [loadingSelected, setLoadingSelected] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [exporting, setExporting] = useState(false);

  const handleExportPDF = async () => {
    setExporting(true);
    try {
      const { API_BASE } = await import("@/lib/api");
      const token = localStorage.getItem("api_token") || "";
      const headers: Record<string, string> = {};
      if (token) headers["X-API-Token"] = token;

      const response = await fetch(`${API_BASE}/api/jobs/export-pdf`, {
        headers,
      });

      if (!response.ok) {
        throw new Error("Failed to generate PDF");
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "matching_jobs.pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e: any) {
      alert("Error exporting PDF: " + e.message);
    } finally {
      setExporting(false);
    }
  };

  const [filters, setFilters] = useState({
    page: 1,
    page_size: 20,
    min_score: "",
    status: "",
    source: "",
    job_type: "",
    search: "",
    sort_by: "match_score",
    sort_order: "desc",
    strict_preferences: false,
  });

  const loadJobs = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string | number | boolean> = {
        page: filters.page,
        page_size: filters.page_size,
        sort_by: filters.sort_by,
        sort_order: filters.sort_order,
      };
      if (filters.min_score) params.min_score = Number(filters.min_score);
      if (filters.status) params.status = filters.status;
      if (filters.source) params.source = filters.source;
      if (filters.job_type) params.job_type = filters.job_type;
      if (filters.search) params.search = filters.search;
      if (filters.strict_preferences) params.strict_preferences = filters.strict_preferences;

      const result = await api.getJobs(params);
      setData(result);
    } catch {
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    loadJobs();
  }, [loadJobs]);

  const inspectJob = async (jobId: number) => {
    setLoadingSelected(true);
    try {
      const job = await api.getJob(jobId);
      setSelectedJob(job);
      // Refresh list to capture status updates (e.g. reviewed status)
      loadJobs();
    } catch (e) {
      console.error("Failed to fetch job inspect info:", e);
    } finally {
      setLoadingSelected(false);
    }
  };

  const handleAction = async (jobId: number, action: "approve" | "reject") => {
    try {
      if (action === "approve") {
        await api.approveJob(jobId);
      } else {
        await api.rejectJob(jobId);
      }
      // Reload lists and currently inspected job details
      loadJobs();
      inspectJob(jobId);
    } catch (e) {
      console.error(e);
    }
  };

  const runScan = async () => {
    setScanning(true);
    try {
      await api.triggerDiscovery();
      alert("Job scan triggered in the background. Check logs or reload in a moment.");
      loadJobs();
    } catch (e) {
      console.error(e);
    } finally {
      setScanning(false);
    }
  };

  const totalPages = data ? Math.ceil(data.total / data.page_size) : 0;

  return (
    <AppShell>
      <div className="page-header">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <h1>~/jobs</h1>
            <p>
              {data?.total ?? 0} jobs discovered
              {data?.total ? ` • page ${data.page} of ${totalPages}` : ""}
            </p>
          </div>
          <div style={{ display: "flex", gap: 10 }}>
            <button className="btn btn-success" onClick={handleExportPDF} disabled={exporting}>
              {exporting ? (
                <>
                  <div className="loading-spinner" style={{ width: 12, height: 12, borderWidth: "1.5px", marginRight: 6 }} />
                  Exporting...
                </>
              ) : (
                <>
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: 6 }}>
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                    <polyline points="14 2 14 8 20 8" />
                    <line x1="16" y1="13" x2="8" y2="13" />
                    <line x1="16" y1="17" x2="8" y2="17" />
                    <polyline points="10 9 9 9 8 9" />
                  </svg>
                  export-pdf
                </>
              )}
            </button>
            <button className="btn btn-primary" onClick={runScan} disabled={scanning}>
              {scanning ? (
                <>
                  <div className="loading-spinner" style={{ width: 12, height: 12, borderWidth: "1.5px", marginRight: 6 }} />
                  Scanning...
                </>
              ) : (
                <>
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: 6 }}>
                    <circle cx="11" cy="11" r="8" />
                    <line x1="21" y1="21" x2="16.65" y2="16.65" />
                  </svg>
                  run-scan
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Filters Form */}
      <div
        className="card"
        style={{
          marginBottom: "var(--space-lg)",
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
          gap: "var(--space-md)",
          background: "var(--bg-secondary)",
        }}
      >
        <div style={{ gridColumn: "span 2", minWidth: 200 }}>
          <label style={{ fontSize: "0.7rem", color: "var(--text-tertiary)", textTransform: "uppercase", display: "block", marginBottom: 6, fontFamily: "var(--font-mono)", fontWeight: 700 }}>Search Description</label>
          <input
            className="input"
            placeholder="Search keywords..."
            value={filters.search}
            onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value, page: 1 }))}
          />
        </div>
        <div>
          <label style={{ fontSize: "0.7rem", color: "var(--text-tertiary)", textTransform: "uppercase", display: "block", marginBottom: 6, fontFamily: "var(--font-mono)", fontWeight: 700 }}>Min Score</label>
          <select
            className="input"
            value={filters.min_score}
            onChange={(e) => setFilters((f) => ({ ...f, min_score: e.target.value, page: 1 }))}
          >
            <option value="">Any Score</option>
            <option value="90">90% Match</option>
            <option value="80">80% Match</option>
            <option value="70">70% Match</option>
            <option value="50">50% Match</option>
          </select>
        </div>
        <div>
          <label style={{ fontSize: "0.7rem", color: "var(--text-tertiary)", textTransform: "uppercase", display: "block", marginBottom: 6, fontFamily: "var(--font-mono)", fontWeight: 700 }}>Status</label>
          <select
            className="input"
            value={filters.status}
            onChange={(e) => setFilters((f) => ({ ...f, status: e.target.value, page: 1 }))}
          >
            <option value="">All Statuses</option>
            <option value="new">new</option>
            <option value="scored">scored</option>
            <option value="reviewed">reviewed</option>
            <option value="approved">approved</option>
            <option value="rejected">rejected</option>
          </select>
        </div>
        <div>
          <label style={{ fontSize: "0.7rem", color: "var(--text-tertiary)", textTransform: "uppercase", display: "block", marginBottom: 6, fontFamily: "var(--font-mono)", fontWeight: 700 }}>Source</label>
          <select
            className="input"
            value={filters.source}
            onChange={(e) => setFilters((f) => ({ ...f, source: e.target.value, page: 1 }))}
          >
            <option value="">All Sources</option>
            <option value="greenhouse">greenhouse</option>
            <option value="lever">lever</option>
            <option value="linkedin">linkedin</option>
            <option value="rss">rss feed</option>
          </select>
        </div>
        <div>
          <label style={{ fontSize: "0.7rem", color: "var(--text-tertiary)", textTransform: "uppercase", display: "block", marginBottom: 6, fontFamily: "var(--font-mono)", fontWeight: 700 }}>Job Type</label>
          <select
            className="input"
            value={filters.job_type}
            onChange={(e) => setFilters((f) => ({ ...f, job_type: e.target.value, page: 1 }))}
          >
            <option value="">All Types</option>
            <option value="internship">internship</option>
            <option value="full-time">full-time</option>
            <option value="research">research</option>
            <option value="contract">contract</option>
            <option value="part-time">part-time</option>
          </select>
        </div>
        <div style={{ display: "flex", flexDirection: "column", justifyContent: "flex-end", paddingBottom: 4 }}>
          <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer", fontFamily: "var(--font-mono)", fontSize: "0.75rem", color: "var(--text-secondary)", userSelect: "none" }}>
            <input
              type="checkbox"
              checked={filters.strict_preferences}
              onChange={(e) => setFilters((f) => ({ ...f, strict_preferences: e.target.checked, page: 1 }))}
              style={{ accentColor: "var(--accent-primary)", width: 14, height: 14, cursor: "pointer" }}
            />
            STRICT_MATCH
          </label>
        </div>
      </div>

      {/* Main Job Table list */}
      {loading ? (
        <div className="empty-state">
          <div className="loading-spinner" />
          <p style={{ marginTop: 16 }}>Loading discovery index...</p>
        </div>
      ) : !data?.jobs.length ? (
        <div className="empty-state">
          <div className="empty-icon">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ display: "inline-block" }}>
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
          </div>
          <h3>Index Empty</h3>
          <p>Try running a scanner or adjust active filter queries.</p>
        </div>
      ) : (
        <>
          <div className="console-table-container">
            <table className="console-table">
              <thead>
                <tr>
                  <th style={{ width: 60 }}>ID</th>
                  <th>Job Title</th>
                  <th>Company</th>
                  <th style={{ width: 100 }}>Score</th>
                  <th style={{ width: 110 }}>Source</th>
                  <th style={{ width: 110 }}>Posted</th>
                  <th style={{ width: 100 }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {data.jobs.map((job) => (
                  <tr
                    key={job.id}
                    onClick={() => inspectJob(job.id)}
                    style={{
                      cursor: "pointer",
                      background: selectedJob?.id === job.id ? "var(--bg-secondary)" : "transparent",
                    }}
                  >
                    <td>#{job.id}</td>
                    <td style={{ fontWeight: 600 }}>{job.title}</td>
                    <td style={{ color: "var(--accent-secondary)" }}>{job.company}</td>
                    <td style={{ fontWeight: 700, color: "var(--accent-primary)" }}>{Math.round(job.match_score)}%</td>
                    <td>{job.source}</td>
                    <td style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>{job.posted_at || "recently"}</td>
                    <td>
                      <span
                        className={`tag ${
                          job.status === "approved"
                            ? "tag-success"
                            : job.status === "rejected"
                            ? "tag-danger"
                            : "tag-warning"
                        }`}
                      >
                        {job.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div style={{ display: "flex", justifyContent: "center", gap: 8, marginTop: 16 }}>
              <button
                className="btn btn-ghost btn-sm"
                disabled={data.page <= 1}
                onClick={() => setFilters((f) => ({ ...f, page: f.page - 1 }))}
              >
                [← Prev]
              </button>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.85rem", padding: "4px 8px" }}>
                {data.page} / {totalPages}
              </span>
              <button
                className="btn btn-ghost btn-sm"
                disabled={data.page >= totalPages}
                onClick={() => setFilters((f) => ({ ...f, page: f.page + 1 }))}
              >
                [Next →]
              </button>
            </div>
          )}
        </>
      )}

      {/* Side drawer details inspector */}
      {selectedJob && (
        <div className="inspector-drawer">
          <div className="inspector-header">
            <div>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", color: "var(--text-tertiary)" }}>
                INSPECT_JOB_ID = #{selectedJob.id}
              </div>
              <h2 style={{ fontFamily: "var(--font-mono)", fontSize: "1.1rem", fontWeight: 700, marginTop: 2 }}>
                {selectedJob.title}
              </h2>
              <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.82rem", color: "var(--accent-secondary)", marginTop: 4 }}>
                {selectedJob.company} • {selectedJob.location || "N/A"} • Posted: {selectedJob.posted_at || "recently"}
              </div>
            </div>
            <button
              className="btn btn-sm btn-ghost"
              onClick={() => setSelectedJob(null)}
              style={{ padding: 6, fontSize: "0.85rem" }}
            >
              [X]
            </button>
          </div>

          <div className="inspector-body">
            {/* Score details */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.85rem", fontWeight: 700 }}>RELEVANCE MATCH</span>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: "1.2rem", fontWeight: 700, color: "var(--accent-primary)" }}>
                {Math.round(selectedJob.match_score)}%
              </span>
            </div>

            {selectedJob.match_breakdown && (
              <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 20 }}>
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
                      marginTop: 8,
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
            <div style={{ display: "flex", flexDirection: "column", gap: 12, marginBottom: 20 }}>
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
            <div style={{ display: "flex", flexDirection: "column", height: 200 }}>
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

          <div className="inspector-footer">
            {selectedJob.status !== "approved" && selectedJob.status !== "rejected" && (
              <>
                <button
                  className="btn btn-success btn-sm"
                  onClick={() => handleAction(selectedJob.id, "approve")}
                  style={{ flex: 1 }}
                >
                  Approve
                </button>
                <button
                  className="btn btn-danger btn-sm"
                  onClick={() => handleAction(selectedJob.id, "reject")}
                  style={{ flex: 1 }}
                >
                  Reject
                </button>
              </>
            )}
            {selectedJob.apply_url && (
              <a
                href={selectedJob.apply_url}
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-sm btn-primary"
                style={{ textAlign: "center", display: "inline-flex", alignItems: "center" }}
              >
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: 6 }}>
                  <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                  <polyline points="15 3 21 3 21 9" />
                  <line x1="10" y1="14" x2="21" y2="3" />
                </svg>
                Open URL
              </a>
            )}
          </div>
        </div>
      )}
    </AppShell>
  );
}
