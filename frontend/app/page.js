'use client';

import { useState, useCallback } from 'react';
import axios from 'axios';
import {
  MapPin, Zap, Building2, Clock, Brain,
  ChevronDown, ChevronUp, Loader2
} from 'lucide-react';
import UploadZone from '../components/UploadZone';
import OutputCard from '../components/OutputCard';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';

export default function Home() {
  const [files, setFiles]         = useState([]);
  const [lat, setLat]             = useState('19.0760');
  const [lon, setLon]             = useState('72.8777');
  const [shopSize, setShopSize]   = useState('');
  const [rent, setRent]           = useState('');
  const [yearsOp, setYearsOp]     = useState('');
  const [result, setResult]       = useState(null);
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);

  const handleSubmit = useCallback(async () => {
    if (files.length === 0) {
      setError('Please upload at least one store image.');
      return;
    }
    setError('');
    setLoading(true);
    setResult(null);

    try {
      const form = new FormData();
      files.forEach(f => form.append('images', f));
      form.append('lat', lat);
      form.append('lon', lon);
      if (shopSize)  form.append('shop_size', shopSize);
      if (rent)      form.append('rent', rent);
      if (yearsOp)   form.append('years_operation', yearsOp);

      const response = await axios.post(`${API}/api/underwrite`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 60000,
      });
      setResult(response.data);
      // Smooth scroll to result
      setTimeout(() => {
        document.getElementById('result-section')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 100);
    } catch (err) {
      const msg = err.response?.data?.error || err.message || 'Unknown error';
      setError(`Request failed: ${msg}`);
    } finally {
      setLoading(false);
    }
  }, [files, lat, lon, shopSize, rent, yearsOp]);

  const useMyLocation = () => {
    if (!navigator.geolocation) {
      setError('Geolocation not supported by this browser.');
      return;
    }
    navigator.geolocation.getCurrentPosition(
      pos => {
        setLat(pos.coords.latitude.toFixed(6));
        setLon(pos.coords.longitude.toFixed(6));
      },
      () => setError('Could not get location. Enter coordinates manually.')
    );
  };

  return (
    <main className="min-h-screen flex flex-col">
      {/* ── NAVBAR ─────────────────────────────────────────────────────── */}
      <nav className="sticky top-0 z-50 border-b border-white/5" style={{ background: 'rgba(5,5,5,0.90)', backdropFilter: 'blur(20px)' }}>
        <div className="max-w-[1400px] mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center text-sm">🏪</div>
            <div>
              <span className="font-bold text-white tracking-tight">TenzorX</span>
              <span className="ml-1.5 text-xs text-brand-400 font-medium">Kirana Credit Intelligence</span>
            </div>
          </div>
          <div className="flex items-center gap-4 text-xs" style={{ color: 'var(--text-muted)' }}>
            <span className="hidden sm:block">Poonawalla Fincorp &middot; TenzorX 2026</span>
            <span className="w-2 h-2 rounded-full bg-brand-400 animate-pulse" title="Backend connected" />
          </div>
        </div>
      </nav>

      {/* ── DASHBOARD LAYOUT ─────────────────────────────────────────── */}
      <div className="flex-1 max-w-[1400px] w-full mx-auto px-6 py-8 grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        
        {/* ── LEFT PANE: INPUTS (5 cols) ─────────────────────────────── */}
        <div className="lg:col-span-5 space-y-6">
          
          {/* Header */}
          <div className="fade-up">
            <h1 className="text-2xl font-bold text-white tracking-tight">New Underwriting Request</h1>
            <p className="text-sm mt-1 mb-4" style={{ color: 'var(--text-muted)' }}>
              Remote cash flow underwriting via multi-modal AI. Upload store images and location data to run the analysis pipeline.
            </p>
            <div className="flex flex-wrap gap-2">
              <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-md glass-sm text-[11px] text-brand-300 border border-brand-500/20">
                <Brain size={12} /> Gemini 2.5 Flash
              </span>
              <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-md glass-sm text-[11px] text-brand-300 border border-brand-500/20">
                📊 NSSO Economic Fusion
              </span>
            </div>
          </div>

          {/* Form Card */}
          <div className="glass p-6 space-y-6 fade-up delay-100">
            
            {/* Images */}
            <div>
              <label className="block text-sm font-semibold text-white mb-3">
                Store Images <span className="text-brand-400">*</span>
                <span className="ml-2 text-xs font-normal" style={{ color: 'var(--text-muted)' }}>
                  Upload 3–5 images (interior, exterior)
                </span>
              </label>
              <UploadZone onFilesChange={setFiles} />
            </div>

            {/* GPS */}
            <div>
              <label className="block text-sm font-semibold text-white mb-3">
                GPS Coordinates <span className="text-brand-400">*</span>
              </label>
              <div className="grid grid-cols-2 gap-3">
                {[
                  { label: 'Latitude',  id: 'lat', val: lat, set: setLat, placeholder: '19.0760' },
                  { label: 'Longitude', id: 'lon', val: lon, set: setLon, placeholder: '72.8777' },
                ].map(({ label, id, val, set, placeholder }) => (
                  <div key={id}>
                    <label className="block text-xs mb-1.5" style={{ color: 'var(--text-muted)' }}>{label}</label>
                    <input
                      type="number"
                      step="any"
                      value={val}
                      onChange={e => set(e.target.value)}
                      placeholder={placeholder}
                      className="w-full px-3 py-2.5 rounded-lg text-sm font-mono text-white border border-white/10 bg-white/5 focus:outline-none focus:border-brand-500/50 focus:ring-1 focus:ring-brand-500/30 transition-all placeholder-white/20"
                    />
                  </div>
                ))}
              </div>
              <button
                onClick={useMyLocation}
                className="mt-2 flex items-center gap-1.5 text-xs text-brand-400 hover:text-brand-300 transition-colors"
              >
                <MapPin size={11} /> Use my current location
              </button>
            </div>

            {/* Advanced / Optional */}
            <div>
              <button
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="flex items-center gap-2 text-xs font-medium text-brand-400 hover:text-brand-300 transition-colors"
              >
                {showAdvanced ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                Optional context (improves accuracy)
              </button>

              {showAdvanced && (
                <div className="mt-4 space-y-3">
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div>
                      <label className="block text-xs mb-1.5" style={{ color: 'var(--text-muted)' }}>Store Size</label>
                      <select
                        value={shopSize}
                        onChange={e => setShopSize(e.target.value)}
                        className="w-full px-3 py-2.5 rounded-lg text-sm text-white border border-white/10 bg-surface-2 focus:outline-none focus:border-brand-500/50 transition-all"
                      >
                        <option value="">Auto</option>
                        <option value="small">Small</option>
                        <option value="medium">Medium</option>
                        <option value="large">Large</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs mb-1.5" style={{ color: 'var(--text-muted)' }}>Monthly Rent (₹)</label>
                      <input
                        type="number"
                        value={rent}
                        onChange={e => setRent(e.target.value)}
                        placeholder="e.g. 15000"
                        className="w-full px-3 py-2.5 rounded-lg text-sm font-mono text-white border border-white/10 bg-white/5 focus:outline-none focus:border-brand-500/50 transition-all placeholder-white/20"
                      />
                    </div>
                    <div>
                      <label className="block text-xs mb-1.5" style={{ color: 'var(--text-muted)' }}>Years Operating</label>
                      <input
                        type="number"
                        value={yearsOp}
                        onChange={e => setYearsOp(e.target.value)}
                        placeholder="e.g. 8"
                        className="w-full px-3 py-2.5 rounded-lg text-sm font-mono text-white border border-white/10 bg-white/5 focus:outline-none focus:border-brand-500/50 transition-all placeholder-white/20"
                      />
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Error */}
            {error && (
              <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3">
                {error}
              </div>
            )}

            {/* Submit */}
            <button
              id="analyze-btn"
              onClick={handleSubmit}
              disabled={loading || files.length === 0}
              className="btn-primary w-full flex items-center justify-center gap-2 text-base py-3.5"
            >
              {loading ? (
                <>
                  <Loader2 size={18} className="animate-spin" />
                  Analyzing with AI engines...
                </>
              ) : (
                <>
                  <Zap size={18} />
                  Run Underwriting Analysis
                </>
              )}
            </button>
          </div>
          
          <footer className="text-center pt-4 pb-8 text-xs" style={{ color: 'var(--text-muted)' }}>
            <p>Problem Statement 4C — TenzorX</p>
          </footer>
        </div>

        {/* ── RIGHT PANE: OUTPUTS (7 cols) ────────────────────────────── */}
        <div className="lg:col-span-7 lg:sticky lg:top-24 fade-up delay-200">
          {loading ? (
            <div className="glass p-12 flex flex-col items-center justify-center min-h-[500px] text-center">
              <div className="relative w-20 h-20 mb-8">
                <div className="absolute inset-0 border-4 border-brand-500/20 rounded-full"></div>
                <div className="absolute inset-0 border-4 border-brand-500 rounded-full border-t-transparent animate-spin"></div>
                <div className="absolute inset-0 flex items-center justify-center">
                  <Brain size={24} className="text-brand-400 animate-pulse" />
                </div>
              </div>
              <h3 className="text-lg font-bold text-white mb-6">Processing Multi-Modal Pipeline</h3>
              
              <div className="w-full max-w-sm space-y-4 text-sm text-left mx-auto" style={{ color: 'var(--text-muted)' }}>
                {[
                  '👁️ Vision Engine — extracting shelf density, SKU diversity',
                  '🗺️ Geo Engine — looking up footfall and competition data',
                  '🛡️ Fraud Defense — running EXIF and cross-signal checks',
                  '📊 Economic Fusion — computing quantile regression ranges',
                ].map((step, i) => (
                  <div key={i} className="flex items-center gap-3 bg-surface-2 p-3 rounded-lg border border-white/5 animate-pulse" style={{ animationDelay: `${i * 0.4}s` }}>
                    <span className="w-2 h-2 rounded-full bg-brand-400 flex-shrink-0" />
                    {step}
                  </div>
                ))}
              </div>
            </div>
          ) : result ? (
            <div id="result-section">
              <OutputCard data={result} />
            </div>
          ) : (
            <div className="glass p-12 flex flex-col items-center justify-center min-h-[500px] text-center border-dashed border-2 border-white/5">
              <div className="w-16 h-16 rounded-2xl bg-surface-2 flex items-center justify-center mb-6 border border-white/5 shadow-2xl">
                <Building2 size={32} className="text-brand-500/50" />
              </div>
              <h3 className="text-lg font-bold text-white mb-2">Awaiting Store Input</h3>
              <p className="text-sm max-w-sm mx-auto" style={{ color: 'var(--text-muted)' }}>
                Upload kirana store images on the left to generate an instant remote cash flow underwriting report.
              </p>
            </div>
          )}
        </div>

      </div>
    </main>
  );
}
