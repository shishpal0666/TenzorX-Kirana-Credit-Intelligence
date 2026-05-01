'use client';

import { useState, useCallback, useRef } from 'react';
import { Upload, X, Image as ImageIcon, AlertCircle } from 'lucide-react';

export default function UploadZone({ onFilesChange }) {
  const [files, setFiles] = useState([]);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState('');
  const inputRef = useRef(null);

  const MAX_FILES = 5;
  const ACCEPTED  = ['image/jpeg', 'image/png', 'image/webp', 'image/jpg'];

  const processFiles = useCallback((newFiles) => {
    setError('');
    const valid = Array.from(newFiles).filter(f => ACCEPTED.includes(f.type));
    if (valid.length === 0) {
      setError('Only JPG, PNG, or WebP images are accepted.');
      return;
    }

    setFiles(prev => {
      const combined = [...prev, ...valid].slice(0, MAX_FILES);
      onFilesChange(combined);
      return combined;
    });
  }, [onFilesChange]);

  const onDrop = useCallback((e) => {
    e.preventDefault();
    setDragging(false);
    processFiles(e.dataTransfer.files);
  }, [processFiles]);

  const removeFile = (idx) => {
    setFiles(prev => {
      const next = prev.filter((_, i) => i !== idx);
      onFilesChange(next);
      return next;
    });
  };

  const LABELS = ['Interior Shelves', 'Counter Area', 'Exterior / Street View', 'Side View', 'Extra View'];

  return (
    <div className="space-y-4">
      {/* Drop Zone */}
      <div
        className={`drop-zone p-8 text-center cursor-pointer ${dragging ? 'drag-over' : ''}`}
        onDragOver={e => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          accept="image/jpeg,image/jpg,image/png,image/webp"
          className="hidden"
          onChange={e => processFiles(e.target.files)}
        />
        <div className="flex flex-col items-center gap-3">
          <div className="w-14 h-14 rounded-2xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center">
            <Upload size={24} className="text-brand-400" />
          </div>
          <div>
            <p className="text-white font-semibold">Drop store images here</p>
            <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
              or click to browse · JPG / PNG / WebP · max {MAX_FILES} images
            </p>
          </div>
          <div className="flex gap-2 mt-1">
            {['Interior', 'Counter', 'Exterior'].map(t => (
              <span key={t} className="text-xs px-2 py-0.5 rounded-full bg-brand-500/10 text-brand-300 border border-brand-500/20">
                {t}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 text-red-400 text-sm bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
          <AlertCircle size={14} />
          {error}
        </div>
      )}

      {/* Previews */}
      {files.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {files.map((file, idx) => (
            <div key={idx} className="relative group glass-sm overflow-hidden">
              <img
                src={URL.createObjectURL(file)}
                alt={LABELS[idx] || `Image ${idx + 1}`}
                className="w-full h-32 object-cover rounded-xl"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent rounded-xl" />
              <div className="absolute bottom-2 left-2 right-8">
                <p className="text-xs text-white font-medium truncate">{LABELS[idx] || `Image ${idx + 1}`}</p>
              </div>
              <button
                onClick={(e) => { e.stopPropagation(); removeFile(idx); }}
                className="absolute top-2 right-2 w-6 h-6 rounded-full bg-black/60 hover:bg-red-500/80 flex items-center justify-center transition-colors opacity-0 group-hover:opacity-100"
              >
                <X size={12} className="text-white" />
              </button>
            </div>
          ))}

          {/* Placeholder slots */}
          {Array.from({ length: Math.max(0, 3 - files.length) }).map((_, idx) => (
            <div
              key={`slot-${idx}`}
              onClick={() => inputRef.current?.click()}
              className="h-32 rounded-xl border border-dashed border-white/10 flex flex-col items-center justify-center gap-2 cursor-pointer hover:border-brand-500/30 transition-colors"
            >
              <ImageIcon size={20} className="text-white/20" />
              <span className="text-xs text-white/20">{LABELS[files.length + idx]}</span>
            </div>
          ))}
        </div>
      )}

      {/* Status */}
      <div className="flex justify-between text-xs" style={{ color: 'var(--text-muted)' }}>
        <span>{files.length} / {MAX_FILES} images selected</span>
        {files.length >= 3 && (
          <span className="text-green-400">✓ Ready to analyze</span>
        )}
        {files.length > 0 && files.length < 3 && (
          <span className="text-yellow-400">Add {3 - files.length} more for best accuracy</span>
        )}
      </div>
    </div>
  );
}
