import { useState, useEffect } from 'react';
import { getStats } from '../api';

const GRADIENT_COLORS = [
  'var(--gradient-primary)',
  'var(--gradient-accent)',
  'var(--gradient-success)',
  'var(--gradient-warm)',
  'linear-gradient(135deg, #a855f7, #ec4899)',
  'linear-gradient(135deg, #06b6d4, #22d3ee)',
];

function BarChart({ data, gradient, maxItems = 8 }) {
  const entries = Object.entries(data).slice(0, maxItems);
  const max = Math.max(...entries.map(([, v]) => v), 1);

  return (
    <div className="chart-bar-group">
      {entries.map(([label, value]) => (
        <div className="chart-bar-row" key={label}>
          <span className="chart-bar-label" title={label}>{label}</span>
          <div className="chart-bar-track">
            <div
              className="chart-bar-fill"
              style={{
                width: `${(value / max) * 100}%`,
                background: gradient,
              }}
            >
              <span className="chart-bar-value">{value.toLocaleString()}</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getStats()
      .then(setStats)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading-spinner"><div className="spinner" /></div>;
  if (!stats) return <div className="empty-state">Failed to load stats</div>;

  const statCards = [
    { label: 'Total Contacts', value: stats.total_contacts?.toLocaleString(), sub: 'From Apollo CSV' },
    { label: 'Companies', value: stats.total_companies?.toLocaleString(), sub: 'Unique match keys' },
    { label: 'Classified', value: stats.opportunity?.classified_count?.toLocaleString(), sub: `${stats.opportunity?.unclassified_count || 0} unclassified` },
    { label: 'High Priority', value: stats.opportunity?.priority_stats?.high_priority_count?.toLocaleString() || '0', sub: `Score >= 70 (avg: ${stats.opportunity?.priority_stats?.avg || '-'})` },
    { label: 'Valid Emails', value: stats.email_valid?.true?.toLocaleString(), sub: `${stats.email_valid?.false} invalid` },
    { label: 'Founders', value: stats.is_founder?.true?.toLocaleString(), sub: `${((stats.is_founder?.true / stats.total_contacts) * 100).toFixed(1)}% of contacts` },
  ];

  return (
    <div>
      {/* Stat Cards */}
      <div className="stats-grid">
        {statCards.map((s, i) => (
          <div className="stat-card animate-in" key={s.label}>
            <div className="stat-label">{s.label}</div>
            <div className="stat-value">{s.value}</div>
            <div className="stat-sub">{s.sub}</div>
          </div>
        ))}
      </div>

      {/* Charts Row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-lg)', marginBottom: 'var(--space-xl)' }}>
        {/* Opportunity Breakdown */}
        <div className="card animate-in">
          <div className="card-header">
            <span className="card-title">Opportunity Types</span>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              {stats.opportunity?.classified_count?.toLocaleString()} classified
            </span>
          </div>
          <BarChart
            data={stats.opportunity?.type_breakdown || {}}
            gradient="var(--gradient-accent)"
          />
        </div>

        {/* Role Breakdown */}
        <div className="card animate-in">
          <div className="card-header">
            <span className="card-title">Role Distribution</span>
          </div>
          <BarChart
            data={stats.role_breakdown || {}}
            gradient="var(--gradient-primary)"
          />
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-lg)', marginBottom: 'var(--space-xl)' }}>
        {/* Country Breakdown */}
        <div className="card animate-in">
          <div className="card-header">
            <span className="card-title">Top Countries</span>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              75 countries total
            </span>
          </div>
          <BarChart
            data={stats.top_countries || {}}
            gradient="var(--gradient-success)"
            maxItems={10}
          />
        </div>

        {/* Stage Pipeline */}
        <div className="card animate-in">
          <div className="card-header">
            <span className="card-title">Pipeline Stages</span>
          </div>
          <BarChart
            data={stats.stage_breakdown || {}}
            gradient="var(--gradient-warm)"
          />
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-lg)' }}>
        {/* Size Buckets */}
        <div className="card animate-in">
          <div className="card-header">
            <span className="card-title">Company Size</span>
          </div>
          <BarChart
            data={stats.size_buckets || {}}
            gradient="linear-gradient(135deg, #a855f7, #ec4899)"
          />
        </div>

        {/* Top Industries */}
        <div className="card animate-in">
          <div className="card-header">
            <span className="card-title">Top Industries</span>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              122 industries
            </span>
          </div>
          <BarChart
            data={stats.top_industries || {}}
            gradient="linear-gradient(135deg, #06b6d4, #22d3ee)"
          />
        </div>
      </div>
    </div>
  );
}
