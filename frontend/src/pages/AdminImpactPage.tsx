import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { ImpactReport } from "../lib/types";
import { StatCard } from "../components/StatCard";
import { EmptyState } from "../components/EmptyState";
import { PageSpinner } from "../components/Spinner";
import { BarChart } from "./DashboardPage";

export function AdminImpactPage() {
  const [report, setReport] = useState<ImpactReport | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .adminImpact()
      .then(setReport)
      .catch(() => undefined)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <PageSpinner />;

  const stats = report?.stats;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h2>Impact Analytics</h2>
          <p className="muted">Estimated environmental and social impact of rescued food.</p>
        </div>
      </div>

      <div className="stat-grid">
        <StatCard label="Meals redistributed" value={stats?.meals_redistributed ?? 0} accent="green" />
        <StatCard label="Food saved (kg)" value={stats?.food_saved_kg ?? 0} accent="amber" />
        <StatCard label="People served" value={stats?.people_served ?? 0} accent="violet" />
        <StatCard
          label="CO₂ reduced (kg)"
          value={`${stats?.co2_reduced_kg ?? 0}${stats?.co2_is_estimate ? "*" : ""}`}
          accent="blue"
        />
      </div>
      {stats?.co2_is_estimate && (
        <p className="muted small">* CO₂ estimate based on a standard food-waste factor.</p>
      )}

      <div className="detail-grid">
        <div className="card">
          <div className="card-header">
            <h3>Monthly redistribution</h3>
          </div>
          {report && report.monthly_redistribution.length > 0 ? (
            <BarChart data={report.monthly_redistribution} />
          ) : (
            <EmptyState title="No data yet" />
          )}
        </div>
        <div className="card">
          <div className="card-header">
            <h3>Food categories (share %)</h3>
          </div>
          {report && report.food_categories.length > 0 ? (
            <div className="h-bar-list">
              {report.food_categories.map((c) => (
                <div className="h-bar" key={c.label}>
                  <span className="h-bar-label">{c.label.replace(/_/g, " ")}</span>
                  <div className="h-bar-track">
                    <div className="h-bar-fill" style={{ width: `${c.value}%` }} />
                  </div>
                  <span className="h-bar-value">{c.value}%</span>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title="No data yet" />
          )}
        </div>
      </div>

      <div className="detail-grid">
        <div className="card">
          <div className="card-header">
            <h3>Top contributors</h3>
          </div>
          {report && report.top_contributors.length > 0 ? (
            <ol className="contributor-list">
              {report.top_contributors.map((c) => (
                <li key={c.name}>
                  <div>
                    <strong>{c.name}</strong>
                    <div className="muted small">
                      {c.meals} meals · {c.food_kg} kg
                    </div>
                  </div>
                  <span className="contrib-rank">{c.meals} meals</span>
                </li>
              ))}
            </ol>
          ) : (
            <EmptyState title="No contributions yet" />
          )}
        </div>
        <div className="card">
          <div className="card-header">
            <h3>Goals</h3>
          </div>
          {report && report.goals.length > 0 ? (
            <div className="goal-list">
              {report.goals.map((g) => (
                <div className="goal" key={g.key}>
                  <div className="goal-head">
                    <span>{g.label}</span>
                    <span className="muted small">
                      {g.current.toLocaleString()} / {g.target.toLocaleString()}
                    </span>
                  </div>
                  <div className="goal-track">
                    <div className="goal-fill" style={{ width: `${g.percent}%` }} />
                  </div>
                  <div className="goal-pct">{g.percent}%</div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title="No goals yet" />
          )}
        </div>
      </div>
    </div>
  );
}
