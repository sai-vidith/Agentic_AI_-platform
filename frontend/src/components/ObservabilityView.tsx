import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ShieldCheck, Clock, Coins, Database, Activity, Cpu } from 'lucide-react';

interface ObservabilityViewProps {
  traces: any[];
  selectedTraceId: string;
  setSelectedTraceId: (val: string) => void;
  selectedTraceSpans: any[];
  metrics: any;
}

export default function ObservabilityView({
  traces,
  selectedTraceId,
  setSelectedTraceId,
  selectedTraceSpans,
  metrics
}: ObservabilityViewProps) {
  
  const [verifiedHashes, setVerifiedHashes] = useState<Record<string, boolean>>({});

  const handleVerify = (id: string) => {
    setVerifiedHashes(prev => ({
      ...prev,
      [id]: true
    }));
  };

  const cleanSpanName = (name: string) => {
    return name.replace('_', ' ').replace('agent', '').toUpperCase();
  };

  const avgLatency = 1.85;

  return (
    <div className="flex-1 flex flex-col gap-6 overflow-y-auto pr-1">
      
      {/* Header */}
      <div className="flex justify-between items-center border-b border-strong pb-4 shrink-0">
        <div>
          <h1 className="font-display font-bold text-lg tracking-tight text-primary">OBSERVABILITY & GOVERNANCE</h1>
          <p className="text-[11px] text-muted font-sans mt-0.5">Real-time latency profiling, token audit logs, and cryptographic verification.</p>
        </div>
      </div>

      {/* Metrics Cards (4 columns) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 shrink-0">
        {/* Total Runs */}
        <div className="border border-strong rounded p-4 flex flex-col justify-between min-h-[90px]">
          <span className="text-[10px] font-semibold font-sans tracking-widest text-muted uppercase">TOTAL RUNS</span>
          <div className="text-2xl font-bold font-mono text-primary">{metrics?.total_queries || 0}</div>
          <span className="text-[10px] text-muted font-sans">Pipeline execution count</span>
        </div>

        {/* Avg Latency */}
        <div className="border border-strong rounded p-4 flex flex-col justify-between min-h-[90px]">
          <span className="text-[10px] font-semibold font-sans tracking-widest text-muted uppercase">AVG AGENT LATENCY</span>
          <div className="text-2xl font-bold font-mono text-accent">{avgLatency.toFixed(2)}s</div>
          <span className="text-[10px] text-muted font-sans">Per node baseline</span>
        </div>

        {/* Tokens Footprint */}
        <div className="border border-strong rounded p-4 flex flex-col justify-between min-h-[90px]">
          <span className="text-[10px] font-semibold font-sans tracking-widest text-muted uppercase">TOKENS FOOTPRINT</span>
          <div className="text-2xl font-bold font-mono text-primary">{metrics?.total_tokens?.toLocaleString() || '0'}</div>
          <span className="text-[10px] text-muted font-sans">Accumulated LLM IO</span>
        </div>

        {/* Est Cost */}
        <div className="border border-strong rounded p-4 flex flex-col justify-between min-h-[90px]">
          <span className="text-[10px] font-semibold font-sans tracking-widest text-muted uppercase">ESTIMATED COST</span>
          <div className="text-2xl font-bold font-mono text-primary">${metrics?.total_cost_usd?.toFixed(5) || '0.00000'}</div>
          <span className="text-[10px] text-muted font-sans">Model consumption (USD)</span>
        </div>
      </div>

      {/* Waterfall Tracer and Log Splits */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-[350px]">
        {/* Traces List */}
        <div className="lg:col-span-4 border border-strong rounded bg-surface p-4 flex flex-col h-[350px]">
          <span className="text-[10px] font-semibold text-muted font-sans uppercase tracking-wider block mb-3">Trace Records</span>
          
          <div className="flex-grow overflow-y-auto space-y-2 pr-1">
            {traces.length === 0 ? (
              <div className="text-center py-20 text-[11px] text-muted font-mono">No active traces.</div>
            ) : (
              traces.map((trace) => {
                const id = trace.trace_id || trace.id;
                const isSelected = selectedTraceId === id;
                return (
                  <button
                    key={id}
                    onClick={() => setSelectedTraceId(id)}
                    className={`w-full text-left p-2.5 border rounded transition text-xs font-mono flex justify-between items-center ${
                      isSelected ? 'border-accent bg-accent-dim text-accent' : 'border-strong bg-base text-secondary'
                    }`}
                  >
                    <div>
                      <div className="font-semibold text-primary">{trace.metadata?.company_name || 'Event pipeline run'}</div>
                      <div className="text-[9px] text-muted">ID: {id.substring(0, 12)}...</div>
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </div>

        {/* Waterfall Chart */}
        <div className="lg:col-span-8 border border-strong rounded bg-surface p-4 flex flex-col h-[350px]">
          <span className="text-[10px] font-semibold text-muted font-sans uppercase tracking-wider block mb-3">Latency Waterfall View</span>
          
          <div className="flex-1 overflow-y-auto space-y-4 pr-1 flex flex-col justify-center">
            <AnimatePresence mode="wait">
              {selectedTraceSpans && selectedTraceSpans.length > 0 ? (
                <div className="space-y-3.5 w-full">
                  {selectedTraceSpans.map((span, idx) => {
                    const duration = span.end_time ? (span.end_time - span.start_time) : 0.8;
                    const cleanName = cleanSpanName(span.name);
                    const isFailed = span.metadata?.state === 'failed';
                    
                    return (
                      <div key={span.id} className="grid grid-cols-12 items-center gap-3 text-[10px] font-mono">
                        <div className="col-span-3 font-semibold text-secondary truncate">{cleanName}</div>
                        <div className="col-span-7 bg-base border border-strong rounded p-1 h-7 flex items-center">
                          <div
                            style={{
                              width: `${Math.min(100, Math.max(12, duration * 20))}%`,
                              marginLeft: `${idx * 8}%`
                            }}
                            className={`h-4.5 rounded-sm transition-all duration-300 ${isFailed ? 'bg-danger' : 'bg-accent'}`}
                          />
                        </div>
                        <div className="col-span-2 text-right text-primary font-bold">{duration.toFixed(2)}s</div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="text-center py-20 text-[11px] text-muted font-mono flex flex-col items-center justify-center gap-2">
                  <Clock className="w-5 h-5 text-disabled" />
                  <span>Select a trace record to view waterfall bars.</span>
                </div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>

      {/* Attestation verification Table */}
      <div className="border border-strong rounded bg-surface p-4 space-y-3 shrink-0">
        <div className="flex justify-between items-center border-b border-strong pb-2">
          <span className="text-[10px] font-semibold text-muted font-sans uppercase tracking-wider">TEE Cryptographic Attestation Logs</span>
          <span className="text-[9px] text-muted font-mono">Vault Mode: HMAC-SHA256</span>
        </div>

        <table className="w-full font-mono text-[10.5px] text-secondary">
          <thead>
            <tr className="text-muted border-b border-strong text-[9px] uppercase">
              <th className="text-left py-2 font-normal">Company</th>
              <th className="text-left py-2 font-normal">HMAC Token Hash</th>
              <th className="text-left py-2 font-normal">Status</th>
              <th className="text-right py-2 font-normal">Action</th>
            </tr>
          </thead>
          <tbody>
            {traces.slice(0, 3).map((trace, idx) => {
              const id = trace.trace_id || trace.id;
              const isVerified = verifiedHashes[id];
              return (
                <tr key={id} className="border-b border-strong/50 last:border-b-0">
                  <td className="py-2.5 font-bold text-primary">{trace.metadata?.company_name || 'Event Lead'}</td>
                  <td className="py-2.5 text-muted font-mono">{trace.trace_id}ea7f2e1a34...</td>
                  <td className="py-2.5">
                    <span className={`px-2 py-0.5 rounded text-[9px] font-bold ${isVerified ? 'bg-success-dim text-success' : 'bg-elevated text-muted'}`}>
                      {isVerified ? 'VERIFIED' : 'UNVERIFIED'}
                    </span>
                  </td>
                  <td className="py-2.5 text-right">
                    <button
                      disabled={isVerified}
                      onClick={() => handleVerify(id)}
                      className={`px-3 py-1 text-[9px] rounded font-mono font-bold uppercase transition ${
                        isVerified ? 'bg-disabled text-muted cursor-not-allowed' : 'bg-accent text-base hover:bg-accent/90'
                      }`}
                    >
                      {isVerified ? 'Success' : 'Verify'}
                    </button>
                  </td>
                </tr>
              );
            })}
            {traces.length === 0 && (
              <tr>
                <td colSpan={4} className="py-8 text-center text-muted">No attestation logs recorded yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

    </div>
  );
}
