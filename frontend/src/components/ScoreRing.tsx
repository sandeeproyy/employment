"use client";

interface ScoreRingProps {
  score: number;
  size?: number;
  strokeWidth?: number;
}

export default function ScoreRing({
  score,
  size = 56,
  strokeWidth = 4,
}: ScoreRingProps) {
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (score / 100) * circumference;

  const scoreClass =
    score >= 75 ? "score-high" : score >= 50 ? "score-mid" : "score-low";

  const color =
    score >= 75
      ? "var(--accent-success)"
      : score >= 50
      ? "var(--accent-warning)"
      : "var(--accent-danger)";

  return (
    <div className={`score-ring ${scoreClass}`} style={{ width: size, height: size }}>
      <svg width={size} height={size}>
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--border-subtle)"
          strokeWidth={strokeWidth}
        />
        {/* Score circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{
            transition: "stroke-dashoffset 1s cubic-bezier(0.4, 0, 0.2, 1)",
            filter: `drop-shadow(0 0 6px ${color})`,
          }}
        />
      </svg>
      <span className="score-value" style={{ color }}>
        {Math.round(score)}
      </span>
    </div>
  );
}
