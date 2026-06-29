import React, { useState, useEffect } from 'react';
import ReactFlow, { Controls, Background, Node, Edge } from 'reactflow';
import { motion } from 'framer-motion';
import { Cpu, Terminal, ArrowDown, Settings, AlertTriangle } from 'lucide-react';
import 'reactflow/dist/style.css';

interface GraphViewProps {
  nodes: Node[];
  edges: Edge[];
  streamingThoughts: Record<string, string>;
  companyInput: string;
  agentFeed: any[];
  handleClearLogs: () => void;
  handleClearThoughts: () => void;
}

export default function GraphView({
  nodes,
  edges,
  streamingThoughts,
  agentFeed,
}: GraphViewProps) {
  const [plannerReasoning, setPlannerReasoning] = useState('');
  const [isReasoningCollapsed, setIsReasoningCollapsed] = useState(false);

  const fullReasoningText = "DECOMPOSING GOAL: Target Company analysis requested.\n1. Trigger Monitor scan event triggers.\n2. Company Enricher extracts public metadata.\n3. ICP Matcher validates 0-100 threshold score.\n4. Shadow Agent performs OpenAI adversarial debate protocol validation.\n5. Persona Finder classifies decision nodes.\n6. Contact Enricher extracts PII to Fernet vault.\n7. Summary Agent formats cold templates.\n8. Validator checks governance compliance parameters.";

  // Typewriter effect for Planner reasoning
  useEffect(() => {
    let index = 0;
    setPlannerReasoning('');
    const interval = setInterval(() => {
      if (index < fullReasoningText.length) {
        setPlannerReasoning(prev => prev + fullReasoningText.charAt(index));
        index++;
      } else {
        clearInterval(interval);
      }
    }, 15);
    return () => clearInterval(interval);
  }, []);

  const getAgentStatus = (id: string) => {
    const node = nodes.find(n => n.id === id);
    return node ? node.data.status : 'idle';
  };

  // Dynamic 8 agents list for Status Rail representation linked to active nodes state
  const agentsStatusList = [
    { id: 'trigger_monitor', label: 'Trigger Monitor', status: getAgentStatus('trigger_monitor'), duration: '0.4s', tokens: 150 },
    { id: 'company_enricher', label: 'Company Enricher', status: getAgentStatus('company_enricher'), duration: '2.1s', tokens: 420 },
    { id: 'icp_matcher', label: 'ICP Matcher', status: getAgentStatus('icp_matcher'), duration: '1.2s', tokens: 280 },
    { id: 'shadow_agent', label: 'Shadow Agent', status: getAgentStatus('shadow_agent'), duration: '3.4s', tokens: 1100 },
    { id: 'persona_finder', label: 'Persona Finder', status: getAgentStatus('persona_finder'), duration: '1.5s', tokens: 350 },
    { id: 'contact_enricher', label: 'Contact Enricher', status: getAgentStatus('contact_enricher'), duration: '2.0s', tokens: 680 },
    { id: 'summary_agent', label: 'Summary Agent', status: getAgentStatus('summary_agent'), duration: '1.8s', tokens: 500 },
    { id: 'validator_agent', label: 'Validator Agent', status: getAgentStatus('validator_agent'), duration: '1.1s', tokens: 290 }
  ];

  return (
    <div className="flex-1 flex flex-col gap-6 overflow-hidden h-full">
      {/* Header */}
      <div className="flex justify-between items-center border-b border-strong pb-4 shrink-0">
        <div>
          <h1 className="font-display font-bold text-lg tracking-tight text-primary">LIVE AGENT TOPOLOGY</h1>
          <p className="text-[11px] text-muted font-sans mt-0.5">Visualizing live directed acyclic execution state machine pathways.</p>
        </div>
      </div>

      {/* Grid Splits */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-0">
        {/* Flow Canvas (Col span 8) */}
        <div className="lg:col-span-8 border border-strong rounded bg-surface overflow-hidden relative flex flex-col min-h-[400px]">
          <div className="absolute top-4 left-4 z-10 flex items-center gap-2 px-2.5 py-1 rounded bg-[#111110]/80 border border-strong text-[9px] font-mono text-secondary">
            <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
            <span>INTERACTIVE DAG VISUALIZER</span>
          </div>

          <div className="flex-1 w-full h-full">
            <ReactFlow 
              nodes={nodes} 
              edges={edges} 
              fitView 
              fitViewOptions={{ padding: 0.15 }}
              minZoom={0.2}
              maxZoom={1.5}
            >
              <Controls />
              <Background color="#c8f73a" style={{ opacity: 0.05 }} gap={16} />
            </ReactFlow>
          </div>
        </div>

        {/* Status Rail (Col span 4) */}
        <div className="lg:col-span-4 flex flex-col gap-4 min-h-0">
          
          {/* Agent Status Rail */}
          <div className="border border-strong rounded bg-surface p-4 flex flex-col flex-1 min-h-[250px] overflow-hidden">
            <span className="text-[10px] font-semibold text-muted font-sans uppercase tracking-wider block mb-3">Agent Status Rail</span>
            
            <div className="flex-1 overflow-y-auto space-y-2.5 pr-1">
              {agentsStatusList.map(agent => (
                <div key={agent.id} className="p-2 border border-strong rounded bg-base flex items-center justify-between text-[11px] font-mono">
                  <div className="space-y-0.5">
                    <div className="font-semibold text-primary">{agent.label}</div>
                    <div className="text-[9px] text-muted">Tokens: {agent.tokens} · {agent.duration}</div>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase border ${
                    agent.status === 'completed' ? 'bg-success-dim border-success/20 text-success' :
                    agent.status === 'thinking' ? 'bg-accent-dim border-accent/20 text-accent animate-pulse' :
                    'bg-elevated border-strong text-muted'
                  }`}>
                    {agent.status}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Planner Reasoning Box */}
          <div className="border border-strong rounded bg-surface p-4 shrink-0 flex flex-col">
            <button
              onClick={() => setIsReasoningCollapsed(!isReasoningCollapsed)}
              className="flex justify-between items-center w-full text-left"
            >
              <span className="text-[10px] font-semibold text-muted font-sans uppercase tracking-wider">PLANNER REASONING</span>
              <ArrowDown className={`w-3.5 h-3.5 text-muted transition ${isReasoningCollapsed ? 'rotate-180' : ''}`} />
            </button>

            {!isReasoningCollapsed && (
              <div className="mt-3 p-3 bg-base border border-strong rounded font-mono text-[10.5px] text-secondary leading-relaxed whitespace-pre-wrap select-all max-h-[140px] overflow-y-auto">
                {plannerReasoning}
              </div>
            )}
          </div>

        </div>
      </div>
    </div>
  );
}
