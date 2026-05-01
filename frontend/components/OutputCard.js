'use client';

import ConfidenceGauge from './ConfidenceGauge';
import { RiskFlagList } from './RiskBadge';
import { MapPin, TrendingUp, IndianRupee, ShieldCheck, BarChart3, Store } from 'lucide-react';

function fmt(n) {
  if (!n && n !== 0) return '—';
  return '₹' + Number(n).toLocaleString('en-IN');
}

function REC_CONFIG(rec) {
  const map = {
    approve_with_standard_terms: { label: 'APPROVE',           cls: 'rec-approve', icon: '✓' },
    needs_verification:          { label: 'VERIFY',            cls: 'rec-verify',  icon: '⚠' },
    reject_pending_review:       { label: 'REJECT / REVIEW',   cls: 'rec-reject',  icon: '✗' },
  };
  return map[rec] || { label: rec, cls: 'rec-verify', icon: '?' };
}

export default function OutputCard({ data }) {
  if (!data) return null;

  const rec = REC_CONFIG(data.recommendation);
  const [dailyLo, dailyHi] = data.daily_sales_range || [0, 0];
  const [revLo, revHi]     = data.monthly_revenue_range || [0, 0];
  const [incLo, incHi]     = data.monthly_income_range || [0, 0];

  return (
    <div className="space-y-4 fade-up">

      {/* ── Header ───────────────────────────────────────────────────────── */}
      <div className="glass p-5 glow-brand">
        <div className="flex items-start justify-between flex-wrap gap-4">
          {/* Location badge */}
          <div className="flex items-center gap-2">
            <MapPin size={16} className="text-brand-400" />
            <div>
              <p className="text-sm font-semibold text-white">
                {data.location?.city || 'Unknown'}, {data.location?.state || 'IN'}
              </p>
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                Tier {data.location?.city_tier} · {data.location?.geo_match_quality} match
                {data.demo_mode && <span className="ml-2 text-brand-400">· 🎭 Demo Mode</span>}
              </p>
            </div>
          </div>

          {/* Recommendation badge */}
          <span className={`px-4 py-1.5 rounded-full text-sm font-bold tracking-wider ${rec.cls}`}>
            {rec.icon} {rec.label}
          </span>
        </div>
      </div>

      {/* ── Confidence + Daily Sales ───────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 delay-100 fade-up">

        {/* Confidence gauge */}
        <div className="glass p-5 flex items-center justify-center gap-6">
          <ConfidenceGauge value={data.confidence_score || 0} />
          <div className="space-y-1 text-sm">
            <p className="font-semibold text-white">Underwriting Score</p>
            <p style={{ color: 'var(--text-muted)' }} className="text-xs">
              p10–p90 interval<br />coverage: 81.2%
            </p>
            <p className="text-xs text-brand-400 font-mono">
              {data.model_version || 'xgb_quantile_v1'}
            </p>
          </div>
        </div>

        {/* Daily sales */}
        <div className="glass p-5 flex flex-col justify-center gap-1.5">
          <div className="flex items-center gap-2 mb-1">
            <TrendingUp size={15} className="text-brand-400" />
            <span className="text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
              Daily Sales Range
            </span>
          </div>
          <div className="currency text-2xl font-bold text-white">
            {fmt(dailyLo)}
            <span className="text-brand-400 mx-2">—</span>
            {fmt(dailyHi)}
          </div>
          <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
            median: <span className="currency text-white">{fmt(data.daily_sales_median)}</span>/day
          </p>
        </div>
      </div>

      {/* ── Revenue & Income ───────────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 delay-200 fade-up">
        <div className="metric-card">
          <div className="flex items-center gap-2 mb-2">
            <IndianRupee size={13} className="text-brand-400" />
            <span className="text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
              Monthly Revenue
            </span>
          </div>
          <p className="currency text-lg font-bold text-white">
            {fmt(revLo)} &ndash; {fmt(revHi)}
          </p>
          <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>26 working days/month</p>
        </div>

        <div className="metric-card">
          <div className="flex items-center gap-2 mb-2">
            <BarChart3 size={13} className="text-brand-400" />
            <span className="text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
              Monthly Net Income
            </span>
          </div>
          <p className="currency text-lg font-bold text-white">
            {fmt(incLo)} &ndash; {fmt(incHi)}
          </p>
          <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>after estimated margins</p>
        </div>
      </div>

      {/* ── Risk Flags ─────────────────────────────────────────────────── */}
      <div className="glass p-5 delay-300 fade-up">
        <div className="flex items-center gap-2 mb-3">
          <ShieldCheck size={15} className="text-brand-400" />
          <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
            Fraud Defense Report
          </span>
        </div>
        <RiskFlagList flags={data.risk_flags} fraudRiskLevel={data.fraud_risk_level} />
      </div>

      {/* ── Vision Summary ─────────────────────────────────────────────── */}
      {data.vision_summary && (
        <div className="glass p-5 delay-400 fade-up">
          <div className="flex items-center gap-2 mb-3">
            <Store size={15} className="text-brand-400" />
            <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
              Vision Feature Extraction
            </span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              { label: 'Shelf Density', value: `${Math.round((data.vision_summary.shelf_density_index || 0) * 100)}%` },
              { label: 'SKU Diversity', value: `${Math.round((data.vision_summary.sku_diversity_score || 0) * 100)}%` },
              { label: 'Store Size',    value: (data.vision_summary.store_size || '—').charAt(0).toUpperCase() + (data.vision_summary.store_size || '').slice(1) },
              { label: 'Refill Signal', value: (data.vision_summary.refill_signal || '—').replace('_', ' ') },
            ].map(({ label, value }) => (
              <div key={label} className="text-center">
                <p className="text-xs" style={{ color: 'var(--text-muted)' }}>{label}</p>
                <p className="text-sm font-semibold text-white mt-0.5">{value}</p>
              </div>
            ))}
          </div>

          {/* Geo metrics */}
          {data.location && (
            <div className="mt-4 pt-4 border-t border-white/5 grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                { label: 'Footfall Score', value: `${Math.round((data.location.footfall_score || 0) * 100)}%` },
                { label: 'Competition',    value: `${data.location.competition_count} nearby` },
                { label: 'Pop. Density',   value: `${Math.round((data.location.population_density || 0) * 100)}%` },
                { label: 'POI Score',      value: `${Math.round((data.location.poi_score || 0) * 100)}%` },
              ].map(({ label, value }) => (
                <div key={label} className="text-center">
                  <p className="text-xs" style={{ color: 'var(--text-muted)' }}>{label}</p>
                  <p className="text-sm font-semibold text-brand-300 mt-0.5">{value}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Raw JSON toggle ────────────────────────────────────────────── */}
      <details className="glass glass-sm p-4 delay-500 fade-up group">
        <summary className="cursor-pointer text-xs font-mono text-brand-400 hover:text-brand-300 select-none list-none flex items-center gap-2">
          <span className="group-open:rotate-90 transition-transform inline-block">▶</span>
          View raw JSON output
        </summary>
        <pre className="mt-3 text-xs font-mono overflow-auto max-h-72 scrollbar-thin" style={{ color: 'var(--text-muted)' }}>
          {JSON.stringify(data, null, 2)}
        </pre>
      </details>
    </div>
  );
}
