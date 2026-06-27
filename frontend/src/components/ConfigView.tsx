import React from 'react';
import { Settings2, Cpu, Eye, FileJson } from 'lucide-react';

interface ConfigViewProps {
  icpConfig: any;
  personasConfig: any;
  domainInput: string;
  setDomainInput: (val: string) => void;
}

export default function ConfigView({
  icpConfig,
  personasConfig,
  domainInput,
  setDomainInput
}: ConfigViewProps) {
  return (
    <div className="flex-1 flex flex-col gap-6 overflow-y-auto pr-1">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            Domain Configuration Engine <Settings2 className="h-5 w-5 text-cyan-400" />
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Swapping domain parameters changes scoring criteria and buyer personas instantly.
          </p>
        </div>
      </div>

      {/* Target Config Selection card */}
      <div className="p-5 glass-panel border border-slate-900 rounded-2xl bg-slate-950/40 flex flex-col md:flex-row gap-4 items-center justify-between relative overflow-hidden">
        <div className="absolute top-0 right-0 w-32 h-32 bg-cyan-500/5 rounded-full blur-3xl" />
        <div className="flex items-center gap-4">
          <div className="h-11 w-11 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center shrink-0">
            <Cpu className="h-5.5 w-5.5 text-cyan-400" />
          </div>
          <div>
            <span className="text-[10px] font-bold text-slate-500 font-mono uppercase tracking-wider block">Active Configuration</span>
            <span className="text-sm font-extrabold text-slate-200 mt-0.5 block">
              {domainInput === 'hr_saas' ? 'HR SaaS Prospect Rules' : 'Cybersecurity Framework Rules'}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto">
          <select
            value={domainInput}
            onChange={(e) => setDomainInput(e.target.value)}
            className="bg-slate-950 border border-slate-850 hover:border-slate-700 text-slate-350 text-xs font-bold rounded-xl px-4 py-3 cursor-pointer transition outline-none"
          >
            <option value="hr_saas">HR SaaS Products</option>
            <option value="cybersecurity">Cybersecurity Tools</option>
          </select>
        </div>
      </div>

      {/* Split JSON Config Code blocks */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* ICP parameters block */}
        <div className="glass-panel border border-slate-900 p-5 rounded-2xl bg-slate-950/40 flex flex-col h-[400px]">
          <h3 className="text-xs font-bold text-slate-350 font-mono uppercase tracking-wider mb-4 flex items-center gap-2 border-b border-slate-900 pb-3 shrink-0">
            <FileJson className="h-4.5 w-4.5 text-cyan-400" /> Target ICP Parameters
          </h3>
          <div className="flex-1 bg-slate-950/80 border border-slate-900 rounded-xl p-4 font-mono text-[10px] text-slate-400 overflow-y-auto leading-relaxed shadow-inner">
            {icpConfig ? (
              <pre>{JSON.stringify(icpConfig, null, 2)}</pre>
            ) : (
              <span className="text-slate-650 italic">Loading configuration database...</span>
            )}
          </div>
        </div>

        {/* Persona targets block */}
        <div className="glass-panel border border-slate-900 p-5 rounded-2xl bg-slate-950/40 flex flex-col h-[400px]">
          <h3 className="text-xs font-bold text-slate-350 font-mono uppercase tracking-wider mb-4 flex items-center gap-2 border-b border-slate-900 pb-3 shrink-0">
            <FileJson className="h-4.5 w-4.5 text-violet-400" /> Buyer Personas & Guidelines
          </h3>
          <div className="flex-1 bg-slate-950/80 border border-slate-900 rounded-xl p-4 font-mono text-[10px] text-slate-400 overflow-y-auto leading-relaxed shadow-inner">
            {personasConfig ? (
              <pre>{JSON.stringify(personasConfig, null, 2)}</pre>
            ) : (
              <span className="text-slate-650 italic">Loading configuration database...</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
