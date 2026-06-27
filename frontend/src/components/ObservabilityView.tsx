import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FileKey2, Coins, Clock, Database, ChevronRight, Activity } from 'lucide-react';

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
  
  // Helper to format span names
  const cleanSpanName = (name: string) => {
    return name.replace('_', ' ').replace('agent', '').toUpperCase();
  };

  return (
    <div className="flex-1 flex flex-col gap-6 overflow-y-auto pr-1">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
          Observability & Cost Dashboard <FileKey2 className="h-5 w-5 text-cyan-400" />
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Monitor token cost aggregates, API query latencies, and execution traces in real-time.
        </p>
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Token Cost Card */}
        <div className="p-5 border border-slate-900 bg-slate-950/40 rounded-2xl flex items-center gap-4 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-24 h-24 bg-violet-500/5 rounded-full blur-2xl" />
          <div className="h-11 w-11 rounded-xl bg-violet-500/10 border border-violet-500/20 flex items-center justify-center shrink-0">
            <Coins className="h-5.5 w-5.5 text-violet-400" />
          </div>
          <div>
            <span className="text-[10px] font-bold text-slate-500 font-mono uppercase tracking-wider block">Estimated Cost</span>
            <span className="text-2xl font-black text-slate-100 mt-0.5 block font-mono">
              ${metrics?.total_cost_usd?.toFixed(5) || '0.00000'}
            </span>
            <span className="text-[9.5px] text-slate-450 block mt-0.5">
              Accumulated model cost (USD)
            </span>
          </div>
        </div>

        {/* Total Tokens Card */}
        <div className="p-5 border border-slate-900 bg-slate-950/40 rounded-2xl flex items-center gap-4 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-24 h-24 bg-cyan-500/5 rounded-full blur-2xl" />
          <div className="h-11 w-11 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center shrink-0">
            <Database className="h-5.5 w-5.5 text-cyan-400" />
          </div>
          <div>
            <span className="text-[10px] font-bold text-slate-500 font-mono uppercase tracking-wider block">Token Footprint</span>
            <span className="text-2xl font-black text-slate-100 mt-0.5 block font-mono">
              {metrics?.total_tokens?.toLocaleString() || '0'}
            </span>
            <span className="text-[9.5px] text-slate-450 block mt-0.5">
              In: {metrics?.total_prompt_tokens?.toLocaleString() || '0'} · Out: {metrics?.total_completion_tokens?.toLocaleString() || '0'}
            </span>
          </div>
        </div>

        {/* API queries card */}
        <div className="p-5 border border-slate-900 bg-slate-950/40 rounded-2xl flex items-center gap-4 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-24 h-24 bg-emerald-500/5 rounded-full blur-2xl" />
          <div className="h-11 w-11 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center shrink-0">
            <Clock className="h-5.5 w-5.5 text-emerald-400" />
          </div>
          <div>
            <span className="text-[10px] font-bold text-slate-500 font-mono uppercase tracking-wider block">Total API Calls</span>
            <span className="text-2xl font-black text-slate-100 mt-0.5 block font-mono">
              {metrics?.total_queries || '0'}
            </span>
            <span className="text-[9.5px] text-slate-450 block mt-0.5">
              Across Groq, Cerebras, & Gemini pools
            </span>
          </div>
        </div>
      </div>

      {/* Spans Tracer Waterfall Chart */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-[350px]">
        {/* Left Side: Traces list */}
        <div className="lg:col-span-4 glass-panel border border-slate-900 p-5 rounded-2xl flex flex-col h-[400px]">
          <h3 className="text-xs font-bold text-slate-350 font-mono uppercase tracking-wider mb-4 flex items-center gap-2 border-b border-slate-900 pb-3 shrink-0">
            <Activity className="h-4.5 w-4.5 text-cyan-400" /> Trace Records
          </h3>
          <div className="flex-1 overflow-y-auto pr-1 flex flex-col gap-2 min-h-0">
            {traces.length === 0 ? (
              <div className="flex-1 flex items-center justify-center text-slate-650 italic text-xs">
                No active execution traces found.
              </div>
            ) : (
              traces.map((trace) => {
                const isSelected = selectedTraceId === trace.id;
                return (
                  <button
                    key={trace.id}
                    onClick={() => setSelectedTraceId(trace.id)}
                    className={`w-full text-left p-3 border rounded-xl transition flex items-center justify-between text-xs ${
                      isSelected 
                        ? 'border-cyan-500/25 bg-cyan-500/5 text-cyan-300' 
                        : 'border-slate-900 bg-slate-950/20 hover:border-slate-800 text-slate-400'
                    }`}
                  >
                    <div className="flex flex-col gap-1.5 min-w-0">
                      <span className="font-extrabold truncate text-slate-300">
                        {trace.metadata?.company_name || 'Workflow Run'}
                      </span>
                      <span className="text-[10px] font-mono text-slate-550">
                        ID: {trace.id.substring(0, 8)}...
                      </span>
                    </div>
                    <ChevronRight className="h-4 w-4 shrink-0" />
                  </button>
                );
              })
            )}
          </div>
        </div>

        {/* Right Side: Waterfall Spans Rendering */}
        <div className="lg:col-span-8 glass-panel border border-slate-900 p-5 rounded-2xl bg-slate-950/40 flex flex-col h-[400px]">
          <h3 className="text-xs font-bold text-slate-350 font-mono uppercase tracking-wider mb-4 flex items-center gap-2 border-b border-slate-900 pb-3 shrink-0">
            <Clock className="h-4.5 w-4.5 text-violet-400" /> Latency Waterfall View
          </h3>
          
          <div className="flex-1 overflow-y-auto pr-1 flex flex-col gap-4 min-h-0 justify-center">
            <AnimatePresence mode="wait">
              {selectedTraceSpans && selectedTraceSpans.length > 0 ? (
                <motion.div
                  key={selectedTraceId}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="flex flex-col gap-3.5 w-full"
                >
                  {selectedTraceSpans.map((span, index) => {
                    const duration = span.end_time ? (span.end_time - span.start_time) : 0.8;
                    const cleanName = cleanSpanName(span.name);
                    
                    // Style depending on span state
                    let barColor = 'bg-gradient-to-r from-cyan-500/80 to-cyan-400/80 shadow-[0_0_10px_rgba(6,182,212,0.15)]';
                    let labelColor = 'text-cyan-400';
                    if (span.metadata?.state === 'failed') {
                      barColor = 'bg-gradient-to-r from-rose-500/80 to-rose-400/80';
                      labelColor = 'text-rose-450';
                    } else if (span.metadata?.state === 'recovered' || span.metadata?.state === 'retrying') {
                      barColor = 'bg-gradient-to-r from-amber-500/80 to-amber-400/80';
                      labelColor = 'text-amber-400';
                    }

                    return (
                      <div key={span.id} className="grid grid-cols-12 items-center gap-4 text-xs font-mono">
                        {/* Name Column */}
                        <div className="col-span-3 truncate text-slate-350 text-[10px] font-bold">
                          {cleanName}
                        </div>
                        
                        {/* Visual Waterfall Bar Column */}
                        <div className="col-span-7 bg-slate-950/80 border border-slate-900 rounded-lg p-1.5 h-8 flex items-center">
                          <div 
                            style={{ 
                              width: `${Math.min(100, Math.max(12, duration * 20))}%`,
                              marginLeft: `${index * 8}%` 
                            }}
                            className={`h-4.5 rounded-md ${barColor} transition-all duration-500`}
                          />
                        </div>

                        {/* Duration Column */}
                        <div className={`col-span-2 text-right text-[10px] font-bold ${labelColor}`}>
                          {duration.toFixed(2)}s
                        </div>
                      </div>
                    );
                  })}
                </motion.div>
              ) : (
                <div className="flex-grow flex flex-col items-center justify-center text-slate-550 p-6 text-center border border-dashed border-slate-900 rounded-xl">
                  <Clock className="h-6 w-6 text-slate-700 mb-3" />
                  <p className="text-xs font-bold">No active trace selected</p>
                  <p className="text-[10px] text-slate-650 mt-1 leading-normal max-w-[280px]">
                    Select a trace record from the list on the left to map its relative latency waterfall bars.
                  </p>
                </div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </div>
  );
}
