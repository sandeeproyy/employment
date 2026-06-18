"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import AppShell from "@/components/AppShell";
import ScoreRing from "@/components/ScoreRing";
import { api, Job } from "@/lib/api";

export default function JobDetailPage() {
  const params = useParams();
  const jobId = Number(params.id);
  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (jobId) {
      api
        .getJob(jobId)
        .then(setJob)
        .catch(console.error)
        .finally(() => setLoading(false));
    }
  }, [jobId]);

  const handleAction = async (action: "approve" | "reject") => {
    if (!job) return;
    try {
      if (action === "approve") await api.approveJob(job.id);
      else await api.rejectJob(job.id);
      const updated = await api.getJob(job.id);
      setJob(updated);
    } catch (e) {
      console.error(e);
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

  if (!job) {
    return (
      <AppShell>
        <div className="empty-state">
          <div className="empty-icon">❌</div>
          <h3>Job Not Found</h3>
        </div>
      </AppShell>
    );
  }

  const breakdown = job.match_breakdown;

  return (
    <AppShell>
      <div className="page-header">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <h1>{job.title}</h1>
            <p style={{ color: "var(--accent-secondary)", fontSize: "1.1rem", fontWeight: 500 }}>
              {job.company}
            </p>
          </div>
          <ScoreRing score={job.match_score} size={80} strokeWidth={5} />
        </div>
      </div>

      {/* Meta Tags */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: "var(--space-2xl)" }}>
        {job.location && <span className="tag">📍 {job.location}</span>}
        {job.remote_allowed && <span className="tag tag-success">🏠 Remote</span>}
        {job.job_type && <span className="tag tag-primary">{job.job_type}</span>}
        {job.department && <span className="tag tag-cyan">{job.department}</span>}
        <span className="tag">{job.source}</span>
        <span className={`tag ${job.status === "approved" ? "tag-success" : job.status === "rejected" ? "tag-danger" : "tag-warning"}`}>
          {job.status}
        </span>
      </div>

      <div className="grid-2">
        {/* Match Breakdown */}
        {breakdown && (
          <div className="card">
            <h3 className="card-title" style={{ marginBottom: "var(--space-lg)" }}>
              Match Breakdown
            </h3>
            {[
              { label: "Skills", value: breakdown.skills, max: 40, color: "var(--accent-primary)" },
              { label: "Projects", value: breakdown.projects, max: 25, color: "var(--accent-secondary)" },
              { label: "Education", value: breakdown.education, max: 15, color: "var(--accent-purple)" },
              { label: "Location", value: breakdown.location, max: 10, color: "var(--accent-success)" },
              { label: "Career Goals", value: breakdown.career_goals, max: 10, color: "var(--accent-warning)" },
            ].map((item) => (
              <div key={item.label} style={{ marginBottom: 16 }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                  <span style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>
                    {item.label}
                  </span>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.85rem", fontWeight: 600, color: item.color }}>
                    {item.value}/{item.max}
                  </span>
                </div>
                <div
                  style={{
                    height: 6,
                    borderRadius: 3,
                    background: "var(--bg-tertiary)",
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      height: "100%",
                      width: `${(item.value / item.max) * 100}%`,
                      background: item.color,
                      borderRadius: 3,
                      transition: "width 1s ease",
                      boxShadow: `0 0 8px ${item.color}`,
                    }}
                  />
                </div>
              </div>
            ))}

            {breakdown.reason && (
              <div
                style={{
                  marginTop: "var(--space-md)",
                  padding: 12,
                  borderRadius: "var(--radius-md)",
                  background: "var(--bg-glass)",
                  fontSize: "0.85rem",
                  color: "var(--text-secondary)",
                  fontStyle: "italic",
                }}
              >
                {breakdown.reason}
              </div>
            )}
          </div>
        )}

        {/* Skills Analysis */}
        <div className="card">
          <h3 className="card-title" style={{ marginBottom: "var(--space-lg)" }}>
            Skills Analysis
          </h3>

          {breakdown?.matched_skills?.length ? (
            <div style={{ marginBottom: "var(--space-lg)" }}>
              <div style={{ fontSize: "0.8rem", color: "var(--text-tertiary)", marginBottom: 8, textTransform: "uppercase", letterSpacing: 1 }}>
                ✓ Matched Skills
              </div>
              <div className="skills-grid">
                {breakdown.matched_skills.map((s, i) => (
                  <span key={i} className="skill-tag matched">{s}</span>
                ))}
              </div>
            </div>
          ) : null}

          {breakdown?.missing_skills?.length ? (
            <div>
              <div style={{ fontSize: "0.8rem", color: "var(--text-tertiary)", marginBottom: 8, textTransform: "uppercase", letterSpacing: 1 }}>
                ✗ Missing Skills
              </div>
              <div className="skills-grid">
                {breakdown.missing_skills.map((s, i) => (
                  <span key={i} className="skill-tag missing">{s}</span>
                ))}
              </div>
            </div>
          ) : null}

          {job.skills_required?.length > 0 && (
            <div style={{ marginTop: "var(--space-lg)" }}>
              <div style={{ fontSize: "0.8rem", color: "var(--text-tertiary)", marginBottom: 8, textTransform: "uppercase", letterSpacing: 1 }}>
                Required Skills
              </div>
              <div className="skills-grid">
                {job.skills_required.map((s, i) => (
                  <span key={i} className="skill-tag">{s}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Job Description */}
      <div className="card" style={{ marginTop: "var(--space-lg)" }}>
        <h3 className="card-title" style={{ marginBottom: "var(--space-md)" }}>
          Job Description
        </h3>
        <div
          style={{
            fontSize: "0.9rem",
            lineHeight: 1.7,
            color: "var(--text-secondary)",
            whiteSpace: "pre-wrap",
            maxHeight: 400,
            overflow: "auto",
          }}
        >
          {job.description}
        </div>
      </div>

      {/* Actions */}
      <div
        style={{
          marginTop: "var(--space-2xl)",
          display: "flex",
          gap: "var(--space-md)",
          alignItems: "center",
        }}
      >
        {job.status !== "approved" && job.status !== "rejected" && (
          <>
            <button
              className="btn btn-success btn-lg"
              onClick={() => handleAction("approve")}
            >
              ✓ Approve & Prepare Application
            </button>
            <button
              className="btn btn-danger btn-lg"
              onClick={() => handleAction("reject")}
            >
              ✗ Reject
            </button>
          </>
        )}
        {job.apply_url && (
          <a
            href={job.apply_url}
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-primary btn-lg"
          >
            🔗 Open Application Page
          </a>
        )}
        {job.source_url && (
          <a
            href={job.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-ghost"
          >
            View Original Listing
          </a>
        )}
      </div>
    </AppShell>
  );
}
