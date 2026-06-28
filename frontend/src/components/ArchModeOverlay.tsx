import React from 'react';
import { motion } from 'framer-motion';
import { Layers, ShieldCheck, Terminal, Cpu, Database, CpuIcon } from 'lucide-react';

interface ArchModeOverlayProps {
  isActive: boolean;
  onClose: () => void;
  activeAgent: string | null;
  agentState: string | null;
}

export default function ArchModeOverlay({
  isActive,
  onClose,
  activeAgent,
  agentState
}: ArchModeOverlayProps) {
  if (!isActive) return null;

  // Determine speaker notes based on the active agent
  let speakerNotes = "The Operator Terminal is monitoring discovery webhook events. Launch a trigger signal to observe live multi-agent orchestration.";
  
  if (activeAgent) {
    switch (activeAgent) {
      case 'trigger_monitor':
        speakerNotes = "Webhook Gateway intercepts signal payload. The Planner agent decomposes the goal and builds a dynamic task DAG instead of running a hardcoded pipeline.";
        break;
      case 'company_enricher':
        speakerNotes = "Company Enricher is active. To handle API limitations, the system automatically checks caching, drops down from DuckDuckGo, and triggers self-healing routines if exceptions arise.";
        break;
      case 'icp_matcher':
        speakerNotes = "ICP Matcher evaluates leads. If the scored compatibility falls below 50, the executor immediately prunes all subsequent steps, saving up to 60% of LLM token costs.";
        break;
      case 'shadow_agent':
        speakerNotes = "Adversarial Shadow Agent is running the OpenAI Debate Protocol. An advocate argues in favor of the prospect, while the adversary critiques, and the Validator judge settles the verdict.";
        break;
      case 'contact_enricher':
        speakerNotes = "Contact Enricher grabs contact details and redacts PII. PII values are encrypted using the Fernet Vault, producing HMAC attestation codes for complete security audit trails.";
        break;
      case 'summary_agent':
        speakerNotes = "Summary Agent creates customized outreach templates. It leverages enriched company and contact details to match the specific persona requirements.";
        break;
      case 'validator_agent':
        speakerNotes = "Validator Agent performs compliance checks. If any divergence exists, it blocks automatic transit and places the lead directly into the human approvals queue.";
        break;
      default:
        speakerNotes = `Active agent: ${activeAgent} is currently in the ${agentState || 'thinking'} state. Real-time DAG updates are streamed via persistent WebSocket feeds.`;
    }
  }

  const layers = [
    { name: 'Layer 1: Presentation', desc: 'Vite + React SPA / React Flow DAG', icon: <Terminal className="w-3.5 h-3.5" />, active: activeAgent === null },
    { name: 'Layer 2: API Gateway', desc: 'FastAPI REST / WebSockets / Webhooks', icon: <Layers className="w-3.5 h-3.5" />, active: activeAgent === 'trigger_monitor' },
    { name: 'Layer 3: Governance & TEE', desc: 'Fernet Cryptographic Vault / Redactor / HMAC', icon: <ShieldCheck className="w-3.5 h-3.5" />, active: activeAgent === 'contact_enricher' },
    { name: 'Layer 4: Orchestration', desc: 'Planner Agent / DAG Executor / Self-Healer', icon: <Cpu className="w-3.5 h-3.5" />, active: activeAgent !== null && activeAgent !== 'shadow_agent' },
    { name: 'Layer 5: Agent Runtime', desc: 'LiteLLM / Specialist Agents / Shadow Debate', icon: <CpuIcon className="w-3.5 h-3.5" />, active: activeAgent === 'shadow_agent' },
    { name: 'Layer 6: Memory & Graph', desc: 'NetworkX Knowledge Graph / SQLite Persistence', icon: <Database className="w-3.5 h-3.5" />, active: activeAgent === 'company_enricher' || activeAgent === 'icp_matcher' }
  ];

  return (
    <div className="fixed inset-0 z-40 flex">
      {/* Dimmed Left Area */}
      <div className="flex-1 bg-base/70 backdrop-blur-[1px]" onClick={onClose} />

      {/* Right Architecture Map panel */}
      <motion.div
        initial={{ x: '100%' }}
        animate={{ x: 0 }}
        exit={{ x: '100%' }}
        transition={{ type: 'spring', stiffness: 300, damping: 30 }}
        className="w-[420px] h-full border-l border-strong bg-surface p-6 flex flex-col justify-between shadow-2xl relative z-50 overflow-y-auto"
      >
        <div className="space-y-6">
          <div className="flex justify-between items-center border-b border-strong pb-3">
            <span className="font-display font-bold text-sm tracking-wider uppercase text-accent">Architecture Demo Mode</span>
            <button
              onClick={onClose}
              className="px-2 py-1 border border-strong rounded text-[10px] text-muted hover:text-primary uppercase font-mono transition"
            >
              Exit [ESC]
            </button>
          </div>

          <div className="space-y-4">
            <span className="text-[10px] font-sans font-bold text-muted tracking-wider uppercase">System Layers</span>
            <div className="space-y-2">
              {layers.map(layer => (
                <div
                  key={layer.name}
                  className={`p-3 border rounded transition-all duration-300 ${
                    layer.active 
                      ? 'border-accent bg-accent-dim text-accent shadow-[0_0_15px_rgba(200,247,58,0.08)]' 
                      : 'border-strong bg-base text-secondary'
                  }`}
                >
                  <div className="flex items-center gap-2 font-display font-semibold text-xs">
                    {layer.icon}
                    <span>{layer.name}</span>
                  </div>
                  <div className={`text-[10px] mt-1 font-mono ${layer.active ? 'text-primary' : 'text-muted'}`}>
                    {layer.desc}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-8 border-t border-strong pt-4 space-y-2">
          <span className="text-[10px] font-sans font-bold text-muted tracking-wider uppercase block">Speaker talking points</span>
          <div className="p-3 bg-base border border-strong rounded font-mono text-[11px] text-secondary leading-relaxed min-h-[90px] transition-all duration-300">
            &gt; {speakerNotes}
          </div>
        </div>
      </motion.div>
    </div>
  );
}
