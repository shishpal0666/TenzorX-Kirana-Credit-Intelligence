'use client';

const FLAG_CONFIG = {
  inventory_footfall_mismatch   : { label: 'Inventory/Footfall Mismatch', severity: 'medium', icon: '⚠️' },
  exif_staged_shoot             : { label: 'EXIF: Staged Shoot Detected', severity: 'high',   icon: '🚨' },
  image_inconsistency           : { label: 'Image Inconsistency (CLIP)',   severity: 'high',   icon: '🚨' },
  possible_borrowed_inventory   : { label: 'Possible Borrowed Inventory',  severity: 'high',   icon: '🚨' },
  overstock_anomaly             : { label: 'Overstock Anomaly',            severity: 'medium', icon: '⚠️' },
  staging_suspected             : { label: 'Staging Suspected',            severity: 'high',   icon: '🚨' },
  product_mix_city_mismatch     : { label: 'Product Mix/City Mismatch',    severity: 'medium', icon: '⚠️' },
  limited_view_coverage         : { label: 'Limited View Coverage',        severity: 'low',    icon: 'ℹ️' },
};

const SEVERITY_STYLES = {
  high:   'bg-red-500/15 border-red-500/30 text-red-400',
  medium: 'bg-yellow-500/15 border-yellow-500/30 text-yellow-400',
  low:    'bg-blue-500/15 border-blue-500/30 text-blue-400',
};

export default function RiskBadge({ flag }) {
  const config = FLAG_CONFIG[flag] || {
    label: flag.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
    severity: 'medium',
    icon: '⚠️',
  };

  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border ${SEVERITY_STYLES[config.severity]}`}>
      <span>{config.icon}</span>
      {config.label}
    </span>
  );
}

export function RiskFlagList({ flags, fraudRiskLevel }) {
  if (!flags || flags.length === 0) {
    return (
      <div className="flex items-center gap-2 text-green-400 text-sm">
        <span className="w-2 h-2 rounded-full bg-green-400 flex-shrink-0" />
        No fraud signals detected
      </div>
    );
  }

  const levelColors = { low: 'text-green-400', medium: 'text-yellow-400', high: 'text-red-400' };

  return (
    <div className="space-y-2">
      <div className={`text-xs font-medium uppercase tracking-wider ${levelColors[fraudRiskLevel] || 'text-yellow-400'}`}>
        {fraudRiskLevel?.toUpperCase()} FRAUD RISK — {flags.length} signal{flags.length > 1 ? 's' : ''} detected
      </div>
      <div className="flex flex-wrap gap-2">
        {flags.map(flag => <RiskBadge key={flag} flag={flag} />)}
      </div>
    </div>
  );
}
