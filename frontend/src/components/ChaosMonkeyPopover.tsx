import React, { useState } from 'react';
import { AlertOctagon, Sliders, Shield } from 'lucide-react';

interface ChaosMonkeyPopoverProps {
  isOpen: boolean;
  onClose: () => void;
  isEnabled: boolean;
  onToggle: (enabled: boolean, rate: number, target: string) => void;
}

export default function ChaosMonkeyPopover({
  isOpen,
  onClose,
  isEnabled,
  onToggle
}: ChaosMonkeyPopoverProps) {
  const [rate, setRate] = useState(30);
  const [target, setTarget] = useState('ALL AGENTS');

  if (!isOpen) return null;

  return (
    <div className="absolute left-14 bottom-14 z-50 w-64 p-4 border rounded-lg bg-overlay border-strong shadow-2xl space-y-4">
      <div className="flex items-center gap-2 text-danger font-display font-semibold text-xs tracking-wider uppercase">
        <AlertOctagon className="w-4 h-4" />
        <span>Chaos Monkey Config</span>
      </div>

      <div className="text-[11px] text-muted leading-relaxed font-sans">
        Inject transient network and API rate limit failures to validate self-healing.
      </div>

      <div className="space-y-3 font-mono text-[11px]">
        <div className="space-y-1">
          <div className="flex justify-between text-secondary">
            <span>Failure Rate:</span>
            <span className="text-accent">{rate}%</span>
          </div>
          <input
            type="range"
            min="10"
            max="90"
            value={rate}
            onChange={(e) => setRate(Number(e.target.value))}
            className="w-full h-1 bg-border rounded-lg appearance-none cursor-pointer accent-accent"
          />
        </div>

        <div className="space-y-1">
          <div className="text-secondary">Target Agent:</div>
          <select
            value={target}
            onChange={(e) => setTarget(e.target.value)}
            className="w-full px-2 py-1 bg-elevated border border-strong rounded text-primary text-[10px] outline-none"
          >
            <option value="ALL AGENTS">ALL AGENTS</option>
            <option value="company_enricher">Company Enricher</option>
            <option value="icp_matcher">ICP Matcher</option>
            <option value="shadow_agent">Shadow Agent</option>
            <option value="contact_enricher">Contact Enricher</option>
          </select>
        </div>
      </div>

      <div className="flex gap-2">
        <button
          onClick={() => {
            onToggle(!isEnabled, rate, target);
            onClose();
          }}
          className={`flex-1 py-1.5 rounded text-[10px] font-mono font-bold transition uppercase tracking-wider ${
            isEnabled 
              ? 'bg-danger text-base hover:bg-danger/90' 
              : 'bg-accent text-base hover:bg-accent/90'
          }`}
        >
          {isEnabled ? 'Disable' : 'Inject Faults'}
        </button>
        <button
          onClick={onClose}
          className="px-2.5 py-1.5 border border-strong rounded text-[10px] text-secondary hover:bg-elevated uppercase font-mono"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
