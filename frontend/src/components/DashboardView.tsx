import React from 'react';
import { motion } from 'framer-motion';
import { Search, Play, ShieldAlert, Zap, Layers, RefreshCw } from 'lucide-react';

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
  metrics,
  leads,
  approvalQueue
}: DashboardViewProps) {
  const totalMonitored = leads.length + approvalQueue.length;
  const qualifiedLeads = leads.filter(l => l.icp_score >= 70).length;
  const riskAlerts = approvalQueue.length;
  const selfHealRate = 100;

  return (
    <div className="flex-1 flex flex-col gap-6 overflow-y-auto pr-1">
      {/* Bento Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-10 gap-6 shrink-0">
        
        {/* Trigger Discovery Card (Takes 60% of top row: 6 out of 10 cols) */}
        <div className="lg:col-span-6 border border-strong rounded bg-surface p-5 flex flex-col justify-between space-y-4">
          <div className="space-y-1">
            <span className="text-[10px] font-semibold text-muted font-sans uppercase tracking-wider block">DISCOVERY ORCHESTRATOR</span>
            <span className="font-display font-bold text-base text-primary block">Launch Event Pipeline</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5 font-mono text-[10px]">
              <span className="text-muted uppercase">Target Company:</span>
              <div className="relative">
                <Search className="absolute left-3.5 top-3 h-4 w-4 text-muted" />
                <input
                  type="text"
                  value={companyInput}
                  onChange={(e) => setCompanyInput(e.target.value)}
                  placeholder="e.g. Stripe"
                  className="w-full bg-base border border-strong rounded-sm pl-10 pr-3 py-2 text-primary placeholder:text-muted outline-none focus:border-accent text-xs font-sans"
                />
              </div>
            </div>

            <div className="space-y-1.5 font-mono text-[10px]">
              <span className="text-muted uppercase">Business Domain:</span>
              <select
                value={domainInput}
                onChange={(e) => setDomainInput(e.target.value)}
                className="w-full bg-base border border-strong rounded-sm px-3 py-2.5 text-secondary outline-none focus:border-accent text-xs cursor-pointer font-sans"
              >
                <option value="hr_saas">HR SaaS Products</option>
                <option value="cybersecurity">Cybersecurity Tools</option>
              </select>
            </div>
          </div>

          <button
            onClick={handleTriggerDiscovery}
            className="w-full py-2.5 bg-accent hover:bg-[#d4f950] text-base font-display font-semibold uppercase tracking-wider text-[12px] rounded-sm transition duration-200 flex justify-center items-center gap-2 border border-transparent hover:border-accent/50"
          >
            <Play className="w-3.5 h-3.5 fill-base text-base" /> Trigger Discovery
          </button>
        </div>

        {/* Metric Cards (Take remaining 40% of top row: 4 out of 10 cols) */}
        <div className="lg:col-span-4 grid grid-cols-2 gap-6">
          {/* Monitored Metric */}
          <div className="border border-strong rounded p-5 flex flex-col justify-between min-h-[120px]">
            <span className="text-[10px] font-semibold font-sans tracking-widest text-muted uppercase">MONITORED</span>
            <div className="text-3xl font-bold font-mono text-primary my-1">{totalMonitored}</div>
            <span className="text-[10px] text-muted font-sans">Active in pipeline</span>
          </div>

          {/* Qualified Metric */}
          <div className="border border-strong rounded p-5 flex flex-col justify-between min-h-[120px]">
            <span className="text-[10px] font-semibold font-sans tracking-widest text-muted uppercase">QUALIFIED</span>
            <div className="text-3xl font-bold font-mono text-accent my-1">{qualifiedLeads}</div>
            <span className="text-[10px] text-muted font-sans">ICP Score ≥ 70</span>
          </div>
        </div>
      </div>

      {/* Second Row Bento grid */}
      <div className="grid grid-cols-1 lg:grid-cols-10 gap-6 shrink-0">
        
        {/* LLM Pool Status (Left 60%) */}
        <div className="lg:col-span-6 border border-strong rounded bg-surface p-5 space-y-4">
          <span className="text-[10px] font-semibold text-muted font-sans uppercase tracking-wider block">LLM ROUTER POOL</span>
          
          <div className="grid grid-cols-3 gap-3">
            {/* Groq Card */}
            <div className="p-3 bg-base border border-strong rounded space-y-2">
              <div className="flex justify-between items-center">
                <span className="font-display font-medium text-[11px] text-primary">GROQ</span>
                <span className="h-1.5 w-1.5 rounded-full bg-success" />
              </div>
              <div className="font-mono text-[9px] text-muted">Llama-3-70b-Tool</div>
              <div className="text-[9px] text-accent font-mono font-bold">PRIMARY · 18ms</div>
            </div>

            {/* Cerebras Card */}
            <div className="p-3 bg-base border border-strong rounded space-y-2">
              <div className="flex justify-between items-center">
                <span className="font-display font-medium text-[11px] text-primary">CEREBRAS</span>
                <span className="h-1.5 w-1.5 rounded-full bg-warning" />
              </div>
              <div className="font-mono text-[9px] text-muted">Llama-3.1-8b</div>
              <div className="text-[9px] text-warning font-mono font-bold">FALLBACK · 12ms</div>
            </div>

            {/* Gemini Card */}
            <div className="p-3 bg-base border border-strong rounded space-y-2">
              <div className="flex justify-between items-center">
                <span className="font-display font-medium text-[11px] text-secondary">GEMINI</span>
                <span className="h-1.5 w-1.5 rounded-full bg-disabled" />
              </div>
              <div className="font-mono text-[9px] text-muted">Gemini-1.5-Pro</div>
              <div className="text-[9px] text-muted font-mono font-bold">STANDBY · Idle</div>
            </div>
          </div>
        </div>

        {/* Alerts / Self-heal (Right 40%) */}
        <div className="lg:col-span-4 grid grid-cols-2 gap-6">
          {/* Risk Alerts */}
          <div className="border border-strong rounded p-5 flex flex-col justify-between min-h-[120px]">
            <span className="text-[10px] font-semibold font-sans tracking-widest text-muted uppercase flex items-center gap-1.5">
              <ShieldAlert className="w-3.5 h-3.5 text-danger" /> RISK ALERTS
            </span>
            <div className="text-3xl font-bold font-mono text-danger my-1">{riskAlerts}</div>
            <span className="text-[10px] text-muted font-sans">Queue size</span>
          </div>

          {/* Self-heal */}
          <div className="border border-strong rounded p-5 flex flex-col justify-between min-h-[120px]">
            <span className="text-[10px] font-semibold font-sans tracking-widest text-muted uppercase flex items-center gap-1.5">
              <RefreshCw className="w-3.5 h-3.5 text-success" /> SELF-HEAL
            </span>
            <div className="text-3xl font-bold font-mono text-success my-1">{selfHealRate}%</div>
            <span className="text-[10px] text-muted font-sans">Baselines maintained</span>
          </div>
        </div>
      </div>

      {/* Recent Evaluated Pipeline leads */}
      <div className="border border-strong rounded bg-surface p-4 flex flex-col flex-1 min-h-[200px]">
        <div className="flex justify-between items-center border-b border-strong pb-3 mb-4">
          <span className="text-[10px] font-sans font-bold text-muted tracking-wider uppercase">Active Pipeline Discoveries</span>
          <span className="text-[9px] text-muted font-mono">Persistence: SQLite Locked</span>
        </div>

        <div className="flex-1 overflow-y-auto pr-1 flex flex-col gap-3.5">
          {leads.length === 0 && approvalQueue.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center text-muted border border-dashed border-strong rounded p-6">
              <span className="text-xs font-mono">No prospects logged. Run event pipeline trigger above...</span>
            </div>
          ) : (
            Array.from(new Map([...approvalQueue, ...leads].map(item => [item.id, item])).values())
              .slice(0, 5)
              .map((lead, idx) => (
              <div key={lead.id || idx} className="p-3 border border-strong rounded bg-base hover:bg-elevated transition flex items-center justify-between">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-display font-bold text-xs text-primary">{lead.company_name}</span>
                    <span className={`px-2 py-0.5 rounded text-[8px] font-mono font-bold uppercase border ${
                      lead.status === 'approved' ? 'bg-success-dim text-success border-success/20' :
                      lead.status === 'rejected' ? 'bg-danger-dim text-danger border-danger/20' :
                      lead.status === 'pending_approval' ? 'bg-warning-dim text-warning border-warning/20 animate-pulse' :
                      'bg-accent-dim text-accent border-accent/20'
                    }`}>
                      {lead.status === 'pending_approval' ? 'Review Required' : lead.status}
                    </span>
                  </div>
                  <div className="text-[10px] font-mono text-muted">Verification ID: {lead.id.substring(0, 16)}</div>
                </div>

                <div className="flex flex-col items-end">
                  <span className="text-[9px] font-sans font-bold text-muted uppercase tracking-wider">ICP score</span>
                  <span className="font-mono font-black text-sm text-primary">{lead.icp_score}/100</span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
