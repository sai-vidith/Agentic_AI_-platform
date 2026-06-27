import React from 'react';
import { motion } from 'framer-motion';
import { 
  Search, 
  Play, 
  Activity, 
  CheckCircle2, 
  AlertTriangle, 
  Sparkles,
  Zap,
  RefreshCw
} from 'lucide-react';

interface DashboardViewProps {
  companyInput: string;
  setCompanyInput: (val: string) => void;
  domainInput: string;
  setDomainInput: (val: string) => void;
  handleTriggerDiscovery: () => void;
  handleClearLogs: () => void;
  metrics: any;
  leads: any[];
  approvalQueue: any[];
  agentFeed: any[];
}

export default function DashboardView({
  companyInput,
  setCompanyInput,
  domainInput,
  setDomainInput,
  handleTriggerDiscovery,
  handleClearLogs,
  metrics,
  leads,
  approvalQueue,
  agentFeed
}: DashboardViewProps) {
  
  // Calculate pipeline stats
  const totalMonitored = leads.length + approvalQueue.length;
  const qualifiedLeads = leads.filter(l => l.icp_score >= 70).length;
  const riskAlerts = approvalQueue.length;
  const selfHealRate = 100; // Calculated baseline

  const stats = [
    { label: 'MONITORED', value: totalMonitored, desc: 'Prospects in pipeline', color: 'border-cyan-500/20 text-cyan-400 bg-cyan-950/10' },
    { label: 'ICP QUALIFIED', value: qualifiedLeads, desc: 'Score ≥ 70/100 target', color: 'border-emerald-500/20 text-emerald-400 bg-emerald-950/10' },
    { label: 'RISK ALERTS', value: riskAlerts, desc: 'Needs manual review', color: 'border-amber-500/20 text-amber-400 bg-amber-950/10' },
    { label: 'SELF-HEAL RATE', value: `${selfHealRate}%`, desc: 'Transient fault tolerance', color: 'border-violet-500/20 text-violet-400 bg-violet-950/10' }
  ];

  return (
    <div className="flex-1 flex flex-col gap-6 overflow-y-auto pr-1">
      {/* Header bar */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            Market Discovery Panel <Sparkles className="h-5 w-5 text-cyan-400 animate-pulse" />
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Initiate B2B agentic pipelines for target domains and monitor real-time decision-maker collection.
          </p>
        </div>
      </div>

      {/* Target input card */}
      <motion.div 
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        className="p-5 glass-panel border border-slate-900 rounded-2xl flex flex-col md:flex-row gap-4 items-end bg-slate-950/40 relative overflow-hidden"
      >
        <div className="flex-1 flex flex-col gap-2">
          <label className="text-[10px] font-bold text-slate-400 font-mono uppercase tracking-wider">Target Company Name</label>
          <div className="relative">
            <Search className="absolute left-3.5 top-3.5 h-4.5 w-4.5 text-slate-500" />
            <input
              type="text"
              value={companyInput}
              onChange={(e) => setCompanyInput(e.target.value)}
              placeholder="e.g. Stripe (or leave blank to auto-discover companies)"
              className="w-full bg-slate-950/80 border border-slate-850 hover:border-slate-700 focus:border-cyan-500/50 text-slate-100 text-sm rounded-xl pl-11 pr-4 py-3 transition duration-200 outline-none placeholder:text-slate-650"
            />
          </div>
        </div>

        <div className="w-full md:w-56 flex flex-col gap-2">
          <label className="text-[10px] font-bold text-slate-400 font-mono uppercase tracking-wider">Business Domain</label>
          <select
            value={domainInput}
            onChange={(e) => setDomainInput(e.target.value)}
            className="w-full bg-slate-950/80 border border-slate-850 hover:border-slate-700 focus:border-cyan-500/50 text-slate-350 text-sm rounded-xl px-4 py-3 transition duration-200 outline-none cursor-pointer"
          >
            <option value="hr_saas">HR SaaS Products</option>
            <option value="cybersecurity">Cybersecurity Tools</option>
          </select>
        </div>

        <button
          onClick={handleTriggerDiscovery}
          className="px-6 py-3.5 bg-gradient-to-r from-cyan-500 to-cyan-600 hover:from-cyan-400 hover:to-cyan-500 text-slate-950 font-bold text-xs uppercase tracking-wider rounded-xl transition duration-200 shadow-[0_0_20px_rgba(6,182,212,0.15)] flex items-center gap-2"
        >
          <Play className="h-4 w-4 fill-slate-950 text-slate-950" /> Trigger Discovery
        </button>
      </motion.div>

      {/* Model routing status */}
      <div className="flex items-center gap-6 px-4 py-3 border border-slate-900 rounded-xl bg-slate-950/30 text-xs font-mono text-slate-450 justify-between">
        <div className="flex items-center gap-4">
          <span className="text-[10px] font-bold text-slate-550">LLM POOL:</span>
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-emerald-500" />
            <span className="text-slate-300">Groq (primary)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-amber-500" />
            <span className="text-slate-400">Cerebras (fallback)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-slate-650" />
            <span className="text-slate-500">Gemini (tertiary)</span>
          </div>
        </div>
        <div className="text-[10px] text-slate-500">
          SENSORY PATHWAYS: DuckDuckGo Keyless Search · Firecrawl v2
        </div>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat, i) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 + 0.1 }}
            className={`p-5 rounded-2xl border ${stat.color} flex flex-col justify-between min-h-[120px] transition hover:translate-y-[-2px]`}
          >
            <span className="text-[9px] font-extrabold font-mono tracking-widest uppercase">{stat.label}</span>
            <div className="my-2.5">
              <span className="text-3xl font-black tracking-tight">{stat.value}</span>
            </div>
            <span className="text-[10px] text-slate-400 font-medium">{stat.desc}</span>
          </motion.div>
        ))}
      </div>

      {/* Bottom split panel: Live Log and Activity list */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 flex-1 min-h-[300px]">
        {/* WebSocket Live Log Console */}
        <div className="lg:col-span-5 glass-panel border border-slate-900 p-5 rounded-2xl flex flex-col bg-slate-950/40 relative h-[400px]">
          <div className="flex items-center justify-between border-b border-slate-900 pb-3 mb-4">
            <h3 className="text-xs font-bold text-slate-300 font-mono uppercase tracking-wider flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-500"></span>
              </span>
              Live Thought Stream
            </h3>
            <div className="flex items-center gap-3">
              <button
                onClick={handleClearLogs}
                className="px-2 py-1 bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-800 hover:border-slate-700 rounded text-[9px] font-mono font-bold transition flex items-center gap-1"
              >
                Clear Logs
              </button>
              <span className="px-2 py-0.5 rounded bg-cyan-500/10 border border-cyan-500/25 text-cyan-300 text-[9px] font-mono">
                WS Connected
              </span>
            </div>
          </div>
          
          <div className="flex-1 bg-slate-950/80 border border-slate-900 rounded-xl p-4 font-mono text-[11px] text-cyan-400 overflow-y-auto leading-relaxed shadow-inner">
            {agentFeed.length === 0 ? (
              <div className="text-slate-500 flex flex-col gap-1">
                <p>00:00 Waiting for workflow trigger...</p>
                <p>00:00 WebSocket listening on ws://localhost:8000/v2/ws/events</p>
              </div>
            ) : (
              <div className="flex flex-col gap-2">
                {agentFeed.map((item, idx) => (
                  <div key={idx} className="flex gap-2">
                    <span className="text-slate-600 shrink-0">[{item.time}]</span>
                    <span className={
                      item.type === 'error' ? 'text-rose-400' :
                      item.type === 'success' ? 'text-emerald-400' :
                      item.type === 'system' ? 'text-violet-400 font-bold' :
                      'text-cyan-300'
                    }>
                      {item.message}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Live System Activity Feed - Fixed height for internal scrolling */}
        <div className="lg:col-span-7 glass-panel border border-slate-900 p-5 rounded-2xl flex flex-col bg-slate-950/40 h-[400px]">
          <div className="flex items-center justify-between border-b border-slate-900 pb-3 mb-4">
            <h3 className="text-xs font-bold text-slate-300 font-mono uppercase tracking-wider">
              Recent Discoveries
            </h3>
            <span className="text-[10px] text-slate-500 font-mono">
              Database Sync: Active
            </span>
          </div>

          <div className="flex-1 overflow-y-auto pr-1 flex flex-col gap-3">
            {leads.length === 0 && approvalQueue.length === 0 ? (
              <div className="flex-1 flex flex-col items-center justify-center text-slate-550 border border-dashed border-slate-900 rounded-xl p-8">
                <RefreshCw className="h-6 w-6 text-slate-650 animate-spin mb-3" />
                <p className="text-xs font-semibold">No prospects evaluated yet.</p>
                <p className="text-[10px] text-slate-600 mt-1 text-center">Type in a target company above and trigger the agentic loop.</p>
              </div>
            ) : (
              Array.from(new Map([...approvalQueue, ...leads].map(item => [item.id, item])).values())
                .slice(0, 5)
                .map((lead, idx) => (
                <div key={lead.id || idx} className="p-3 border border-slate-900 hover:border-slate-800 rounded-xl bg-slate-950/40 flex items-center justify-between transition">
                  <div className="flex flex-col gap-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-slate-200">{lead.company_name}</span>
                      <span className={`px-1.5 py-0.5 rounded text-[9px] font-mono font-bold uppercase ${
                        lead.status === 'approved' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                        lead.status === 'rejected' ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' :
                        lead.status === 'pending_approval' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse' :
                        'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20'
                      }`}>
                        {lead.status === 'pending_approval' ? 'Needs Review' : lead.status}
                      </span>
                    </div>
                    <span className="text-[10px] text-slate-500 font-mono">ID: {lead.id.substring(0, 8)}...</span>
                  </div>

                  <div className="flex items-center gap-4">
                    <div className="flex flex-col items-end">
                      <span className="text-[10px] font-bold text-slate-400 font-mono">ICP SCORE</span>
                      <span className={`text-sm font-black font-mono ${
                        lead.icp_score >= 70 ? 'text-emerald-400' :
                        lead.icp_score >= 50 ? 'text-amber-400' :
                        'text-rose-400'
                      }`}>
                        {lead.icp_score}/100
                      </span>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
