import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Node, Edge, Position, MarkerType } from 'reactflow';
import { motion, AnimatePresence } from 'framer-motion';
import { Terminal, Grid, Activity, Sparkles, Bell, Sliders, Eye, AlertOctagon, HelpCircle, ShieldAlert } from 'lucide-react';

// Import Modular Components
import Sidebar from './components/Sidebar';
import DashboardView from './components/DashboardView';
import GraphView from './components/GraphView';
import LeadsView from './components/LeadsView';
import ApprovalsView from './components/ApprovalsView';
import ConfigView from './components/ConfigView';
import ObservabilityView from './components/ObservabilityView';
import LandingPage from './components/LandingPage';

// Interactive Redesign Components
import CommandPalette from './components/CommandPalette';
import ChaosMonkeyPopover from './components/ChaosMonkeyPopover';
import ArchModeOverlay from './components/ArchModeOverlay';
import SimulatorView from './components/SimulatorView';

// API Gateways
const API_BASE = 'http://localhost:8000/v2';
const WS_BASE = 'ws://localhost:8000/v2/ws/events';

interface Lead {
  id: string;
  company_name: string;
  company_details: any;
  contacts: any[];
  icp_score: number;
  evidence_chain: string[];
  shadow_verdict: any;
  outreach_template: string;
  status: string;
  created_at: string;
  attestation?: any;
  plan_reasoning?: string;
  token_usage?: any;
  debate_transcript?: any[];
  buying_committee?: any[];
}

export default function App() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'workflows' | 'leads' | 'approvals' | 'config' | 'observability' | 'simulator'>('dashboard');
  const [inDashboard, setInDashboard] = useState(false);
  const [companyInput, setCompanyInput] = useState('');
  const [domainInput, setDomainInput] = useState('hr_saas');

  // Overlay States
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);
  const [isChaosMonkeyOpen, setIsChaosMonkeyOpen] = useState(false);
  const [isArchModeOpen, setIsArchModeOpen] = useState(false);
  const [isTerminalExpanded, setIsTerminalExpanded] = useState(false);

  // Active tracking for Arch Mode highlighting
  const [activeAgent, setActiveAgent] = useState<string | null>(null);
  const [activeAgentState, setActiveAgentState] = useState<string | null>(null);

  // Floating Notifications State
  const [notifications, setNotifications] = useState<{ id: string; message: string; type: 'success' | 'warning' | 'info' }[]>([]);
  const showNotification = useCallback((message: string, type: 'success' | 'warning' | 'info') => {
    const id = Math.random().toString();
    setNotifications((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setNotifications((prev) => prev.filter((n) => n.id !== id));
    }, 4000);
  }, []);

  // Core App states
  const [leads, setLeads] = useState<Lead[]>([]);
  const [approvalQueue, setApprovalQueue] = useState<Lead[]>([]);
  const [agentFeed, setAgentFeed] = useState<any[]>([]);
  const [chaosEnabled, setChaosEnabled] = useState(false);
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);

  // Observability & Traces
  const [traces, setTraces] = useState<any[]>([]);
  const [selectedTraceId, setSelectedTraceId] = useState<string>('');
  const [selectedTraceSpans, setSelectedTraceSpans] = useState<any[]>([]);
  const [metrics, setMetrics] = useState<any>(null);

  // Config matrices
  const [icpConfig, setIcpConfig] = useState<any>({});
  const [personasConfig, setPersonasConfig] = useState<any>({});

  // Real-time streaming thoughts state
  const [streamingThoughts, setStreamingThoughts] = useState<Record<string, string>>({});

  // React Flow state bindings
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);

  // WS Ref
  const wsRef = useRef<WebSocket | null>(null);

  // Initialize pipeline DAG Nodes
  const initializeDAG = useCallback((runCompany: string) => {
    const nodeNames = [
      { id: 'trigger_monitor', label: 'Trigger Monitor', desc: 'News & Feeds Scanner' },
      { id: 'company_enricher', label: 'Company Enricher', desc: 'Metadata & Tech Stack' },
      { id: 'icp_matcher', label: 'ICP Matcher', desc: 'Scores Compatibility' },
      { id: 'shadow_agent', label: 'Shadow Agent', desc: "Devil's Advocate Check" },
      { id: 'persona_finder', label: 'Persona Finder', desc: 'Matches Buyer Personas' },
      { id: 'contact_enricher', label: 'Contact Enricher', desc: 'PII Vault Encrypter' },
      { id: 'summary_agent', label: 'Summary Agent', desc: 'Outreach Messaging' },
      { id: 'validator_agent', label: 'Validator Agent', desc: 'Quality Guardrail Check' }
    ];

    const initialNodes: Node[] = nodeNames.map((node, index) => ({
      id: node.id,
      position: { x: 40 + index * 160, y: 130 + (index % 2) * 90 },
      data: {
        label: node.label,
        desc: node.desc,
        status: 'idle',
        output: null
      },
      style: {
        background: 'rgba(17, 17, 16, 0.95)',
        color: '#f5f5f0',
        border: '0.5px solid var(--bg-border)',
        borderRadius: '4px',
        padding: '12px',
        width: '145px',
        fontSize: '11px',
        textAlign: 'center',
        boxShadow: 'none',
        transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)'
      },
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
    }));

    const initialEdges: Edge[] = [];
    for (let i = 0; i < nodeNames.length - 1; i++) {
      initialEdges.push({
        id: `e-${nodeNames[i].id}-${nodeNames[i + 1].id}`,
        source: nodeNames[i].id,
        target: nodeNames[i + 1].id,
        animated: false,
        style: { stroke: 'var(--bg-border)', strokeWidth: 1.5 },
        markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--bg-border-strong)' }
      });
    }

    setNodes(initialNodes);
    setEdges(initialEdges);
  }, []);

  // Update Node status in Graph UI
  const updateNodeStatus = useCallback((nodeId: string, status: string, dataPayload?: any) => {
    setNodes((prevNodes) =>
      prevNodes.map((node) => {
        if (node.id !== nodeId) return node;

        let borderStyle = '0.5px solid var(--bg-border)';
        let glowStyle = 'none';
        let bgStyle = 'rgba(17, 17, 16, 0.95)';

        switch (status) {
          case 'thinking':
            borderStyle = '0.5px solid var(--accent)';
            glowStyle = '0 0 20px rgba(200, 247, 58, 0.15)';
            bgStyle = 'rgba(200, 247, 58, 0.05)';
            break;
          case 'completed':
            borderStyle = '0.5px solid var(--success)';
            bgStyle = 'rgba(74, 222, 128, 0.05)';
            break;
          case 'failed':
            borderStyle = '0.5px solid var(--danger)';
            bgStyle = 'rgba(248, 113, 113, 0.05)';
            break;
          case 'retrying':
            borderStyle = '0.5px solid var(--warning)';
            bgStyle = 'rgba(245, 158, 11, 0.05)';
            break;
          case 'recovered':
            borderStyle = '0.5px solid var(--accent)';
            bgStyle = 'rgba(200, 247, 58, 0.04)';
            break;
        }

        return {
          ...node,
          data: {
            ...node.data,
            status,
            output: dataPayload || node.data.output
          },
          style: {
            ...node.style,
            border: borderStyle,
            boxShadow: glowStyle,
            background: bgStyle
          }
        };
      })
    );

    // Animate edge when previous step finishes
    setEdges((prevEdges) =>
      prevEdges.map((edge) => {
        if (edge.source === nodeId) {
          return {
            ...edge,
            animated: status === 'thinking' || status === 'completed',
            style: {
              ...edge.style,
              stroke: status === 'completed' ? 'var(--success)' : 'var(--accent)',
              strokeWidth: 1.5
            },
            markerEnd: {
              type: MarkerType.ArrowClosed,
              color: status === 'completed' ? 'var(--success)' : 'var(--accent)'
            }
          };
        }
        return edge;
      })
    );
  }, []);

  // Fetch initial app data
  const fetchData = async () => {
    try {
      const [leadsRes, approvalsRes, metricsRes, tracesRes] = await Promise.all([
        fetch(`${API_BASE}/workflows/leads`),
        fetch(`${API_BASE}/approvals/queue`),
        fetch(`${API_BASE}/observability/metrics`),
        fetch(`${API_BASE}/observability/traces`)
      ]);

      if (leadsRes.ok) setLeads(await leadsRes.json());
      if (approvalsRes.ok) setApprovalQueue(await approvalsRes.json());
      if (metricsRes.ok) setMetrics(await metricsRes.json());
      if (tracesRes.ok) {
        const trs = await tracesRes.json();
        setTraces(Array.isArray(trs) ? trs : (trs.traces || []));
        const traceList = Array.isArray(trs) ? trs : (trs.traces || []);
        if (traceList.length > 0 && !selectedTraceId) {
          setSelectedTraceId(traceList[0].trace_id || traceList[0].id);
        }
      }
    } catch (e) {
      console.error('Data sync failed:', e);
    }
  };

  // Fetch config details
  const fetchConfigs = useCallback(async () => {
    try {
      const [icpRes, personasRes] = await Promise.all([
        fetch(`${API_BASE}/config/icp?domain=${domainInput}`),
        fetch(`${API_BASE}/config/personas?domain=${domainInput}`)
      ]);
      if (icpRes.ok) setIcpConfig(await icpRes.json());
      if (personasRes.ok) setPersonasConfig(await personasRes.json());
    } catch (e) {
      console.error(e);
    }
  }, [domainInput]);

  // Fetch spans for trace
  const fetchTraceSpans = useCallback(async () => {
    if (!selectedTraceId) return;
    try {
      const res = await fetch(`${API_BASE}/observability/traces/${selectedTraceId}`);
      if (res.ok) {
        const data = await res.json();
        setSelectedTraceSpans(data.spans || []);
      }
    } catch (e) {
      console.error(e);
    }
  }, [selectedTraceId]);

  // Hook runs
  useEffect(() => {
    initializeDAG('');
    fetchData();
  }, [initializeDAG]);

  useEffect(() => {
    fetchConfigs();
  }, [fetchConfigs]);

  useEffect(() => {
    fetchTraceSpans();
  }, [fetchTraceSpans]);

  // Keybind listeners for command palette and arch mode
  useEffect(() => {
    const handleGlobalKeys = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsCommandPaletteOpen(prev => !prev);
      }
    };
    window.addEventListener('keydown', handleGlobalKeys);
    return () => window.removeEventListener('keydown', handleGlobalKeys);
  }, []);

  // WebSockets setup
  useEffect(() => {
    const ws = new WebSocket(WS_BASE);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      const evt = JSON.parse(event.data);
      console.log('[WebSocket] received event:', evt);

      // Track active agents for Layer pulsing
      if (evt.agent && evt.type === 'agent_thinking') {
        setActiveAgent(evt.agent);
        setActiveAgentState('thinking');
      } else if (evt.agent && evt.type === 'agent_completed') {
        setActiveAgent(evt.agent);
        setActiveAgentState('completed');
      }

      // Update thought stream log
      setAgentFeed((prev) => [
        {
          time: new Date().toLocaleTimeString(),
          type: evt.type === 'agent_failed' ? 'error' : evt.type === 'agent_completed' ? 'success' : 'info',
          message: `[${evt.agent || 'SYSTEM'}] ${evt.type === 'agent_thinking' ? 'Executing core logic...' : evt.data?.chunk || evt.message || 'Updated status'}`
        },
        ...prev
      ]);

      // Update React Flow nodes states
      if (evt.agent && evt.type) {
        let status = 'idle';
        if (evt.type === 'agent_thinking') status = 'thinking';
        else if (evt.type === 'agent_completed') status = 'completed';
        else if (evt.type === 'agent_failed') status = 'failed';
        else if (evt.type === 'agent_retrying') status = 'retrying';
        else if (evt.type === 'agent_recovered') status = 'recovered';

        updateNodeStatus(evt.agent, status, evt.data?.output);
      }

      // Update live thought texts
      if (evt.agent && evt.type === 'agent_reasoning' && evt.data?.chunk) {
        setStreamingThoughts((prev) => ({
          ...prev,
          [evt.agent]: (prev[evt.agent] || '') + evt.data.chunk
        }));
      }

      // If workflow finishes entirely
      if (evt.type === 'workflow_started') {
        setIsTerminalExpanded(true); // Auto-expand terminal
        showNotification(`🚀 Initiating pipeline for discovered target: ${evt.target}`, 'info');
      }

      if (evt.type === 'shadow_divergence') {
        showNotification(`⚠️ Risk Critic flagged a Divergence Warning for ${evt.target}!`, 'warning');
      }

      if (evt.type === 'workflow_completed') {
        showNotification(`🎉 Qualified new company lead: ${evt.target}!`, 'success');
        fetchData();
      }

      if (evt.type === 'lead_contacts_updated') {
        showNotification(`👥 Discovered ${evt.data?.new_contacts_count} new decision makers for ${evt.target}!`, 'success');
        fetchData();
      }

      if (evt.type === 'lead_scanned_no_change') {
        showNotification(`🔍 ${evt.target} was scanned silently. No new decision makers found.`, 'info');
        fetchData();
      }
    };

    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, [updateNodeStatus, showNotification]);

  // Execute workflow
  const handleTriggerDiscovery = async () => {
    setStreamingThoughts({});
    const isAutoDiscover = !companyInput.trim() || companyInput.toLowerCase() === 'discover' || companyInput.toLowerCase() === 'auto';
    initializeDAG(isAutoDiscover ? 'Autonomous Search' : companyInput);
    setActiveTab('workflows');
    setIsTerminalExpanded(true);

    try {
      const endpoint = isAutoDiscover ? `${API_BASE}/workflows/discover` : `${API_BASE}/workflows/run`;
      const body = isAutoDiscover 
        ? JSON.stringify({ domain: domainInput, limit: 3 })
        : JSON.stringify({ company_name: companyInput, domain: domainInput });

      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: body
      });
      if (res.ok) {
        fetchData();
      }
    } catch (e) {
      console.error(e);
    }
  };

  // Manage Approvals
  const handleApproval = async (leadId: string, action: 'approve' | 'reject', template?: string) => {
    try {
      const res = await fetch(`${API_BASE}/approvals/${leadId}/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, outreach_template: template })
      });
      if (res.ok) {
        fetchData();
        if (selectedLead && selectedLead.id === leadId) {
          setSelectedLead(prev => prev ? { ...prev, status: action === 'approve' ? 'approved' : 'rejected', outreach_template: template || prev.outreach_template } : null);
        }
      }
    } catch (e) {
      console.error(e);
    }
  };

  // Delete lead
  const handleDeleteLead = async (leadId: string) => {
    try {
      const res = await fetch(`${API_BASE}/workflows/leads/${leadId}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        fetchData();
        if (selectedLead?.id === leadId) {
          setSelectedLead(null);
        }
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleClearLogs = () => {
    setAgentFeed([]);
  };

  // Toggle Chaos Monkey
  const handleToggleChaosMonkey = async (enabled: boolean, rate: number, target: string) => {
    try {
      const res = await fetch(`${API_BASE}/chaos/toggle`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled })
      });
      if (res.ok) {
        const data = await res.json();
        setChaosEnabled(data.enabled);
        showNotification(data.enabled ? `Chaos Monkey enabled on ${target} (${rate}% failure)` : 'Chaos Monkey disabled', 'warning');
      }
    } catch (e) {
      console.error(e);
    }
  };

  // Decryption Simulator
  const [decryptedPII, setDecryptedPII] = useState<Record<string, { email: string; phone: string }>>({});
  const simulateVaultAccess = async (leadId: string, rawEmail: string, rawPhone: string, plainEmail: string, plainPhone: string) => {
    let email = plainEmail;
    let phone = plainPhone;
    
    try {
      if (rawEmail) {
        const res = await fetch(`${API_BASE}/workflows/decrypt`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ cipher_text: rawEmail })
        });
        if (res.ok) {
          const data = await res.json();
          email = data.decrypted;
        }
      }
      if (rawPhone) {
        const res = await fetch(`${API_BASE}/workflows/decrypt`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ cipher_text: rawPhone })
        });
        if (res.ok) {
          const data = await res.json();
          phone = data.decrypted;
        }
      }
    } catch (e) {
      console.error("Decryption failed, falling back:", e);
    }
    
    const key = rawEmail || rawPhone || leadId;
    setDecryptedPII(prev => ({
      ...prev,
      [key]: {
        email: email || plainEmail || "priya.sharma@razorx.in",
        phone: phone || plainPhone || "+91-9876543210"
      }
    }));
  };

  if (!inDashboard) {
    return <LandingPage onEnterDashboard={() => setInDashboard(true)} />;
  }

  return (
    <div className="flex flex-col h-screen w-screen bg-base text-primary font-sans relative overflow-hidden">
      
      {/* Top Command Bar */}
      <header className="h-12 border-b border-strong bg-surface px-4 flex items-center justify-between shrink-0 z-20">
        <div className="flex items-center gap-2 font-display font-bold text-xs tracking-wider uppercase text-primary">
          <span>⚡ NEXUSAI</span>
          <span className="text-muted">COGNITIVE ORCHESTRATOR</span>
        </div>

        {/* Center Search / Command Trigger */}
        <button
          onClick={() => setIsCommandPaletteOpen(true)}
          className="flex items-center justify-between px-3 py-1.5 w-64 rounded bg-base border border-strong text-muted text-[11px] font-mono hover:border-accent hover:text-secondary transition"
        >
          <span>Search or run a command...</span>
          <span>⌘K</span>
        </button>

        {/* Right Status / Actions */}
        <div className="flex items-center gap-4 text-[10px] font-mono">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-success" />
            <span className="text-secondary">GROQ PRIMARY</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-warning" />
            <span className="text-secondary">CEREBRAS</span>
          </div>
          
          <button
            onClick={() => setIsArchModeOpen(true)}
            className="px-2.5 py-1 border border-strong hover:border-accent hover:text-accent font-display font-semibold uppercase tracking-wider rounded-sm transition text-secondary"
          >
            ARCH MODE
          </button>
        </div>
      </header>

      {/* Main content body container */}
      <div className="flex-1 flex overflow-hidden relative">
        
        {/* Left icon rail */}
        <Sidebar
          activeTab={activeTab}
          setActiveTab={(tab) => {
            if (tab === 'simulator') {
              setActiveTab('simulator');
            } else {
              setActiveTab(tab);
            }
          }}
          chaosEnabled={chaosEnabled}
          onOpenChaosMonkey={() => setIsChaosMonkeyOpen(true)}
          approvalCount={approvalQueue.length}
        />

        {/* Content pane */}
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden relative">
          
          {/* Chaos banner if active */}
          {chaosEnabled && (
            <div className="bg-danger/10 border-b border-danger/20 text-danger text-[10px] font-mono px-4 py-1.5 text-center shrink-0 uppercase tracking-widest animate-pulse">
              ⚡ CHAOS MODE ACTIVE — Fault injection enabled
            </div>
          )}

          <div className="flex-1 p-6 overflow-hidden flex flex-col">
            {activeTab === 'dashboard' && (
              <DashboardView
                companyInput={companyInput}
                setCompanyInput={setCompanyInput}
                domainInput={domainInput}
                setDomainInput={setDomainInput}
                handleTriggerDiscovery={handleTriggerDiscovery}
                handleClearLogs={handleClearLogs}
                metrics={metrics}
                leads={leads}
                approvalQueue={approvalQueue}
                agentFeed={agentFeed}
              />
            )}

            {activeTab === 'workflows' && (
              <GraphView
                nodes={nodes}
                edges={edges}
                streamingThoughts={streamingThoughts}
                companyInput={companyInput}
                agentFeed={agentFeed}
                handleClearLogs={handleClearLogs}
                handleClearThoughts={() => setStreamingThoughts({})}
              />
            )}

            {activeTab === 'leads' && (
              <LeadsView
                leads={leads}
                selectedLead={selectedLead}
                setSelectedLead={setSelectedLead}
                decryptedPII={decryptedPII}
                simulateVaultAccess={simulateVaultAccess}
                handleDeleteLead={handleDeleteLead}
              />
            )}

            {activeTab === 'approvals' && (
              <ApprovalsView
                approvalQueue={approvalQueue}
                handleApproval={handleApproval}
              />
            )}

            {activeTab === 'config' && (
              <ConfigView
                icpConfig={icpConfig}
                personasConfig={personasConfig}
                domainInput={domainInput}
                setDomainInput={setDomainInput}
              />
            )}

            {activeTab === 'observability' && (
              <ObservabilityView
                traces={traces}
                selectedTraceId={selectedTraceId}
                setSelectedTraceId={setSelectedTraceId}
                selectedTraceSpans={selectedTraceSpans}
                metrics={metrics}
              />
            )}

            {activeTab === 'simulator' && (
              <SimulatorView
                onFireSignal={() => {
                  fetchData();
                  setActiveTab('workflows');
                }}
                showNotification={showNotification}
              />
            )}
          </div>

          {/* Collapsible terminal thought logs drawer */}
          <div
            className={`border-t border-strong bg-surface transition-all duration-300 flex flex-col shrink-0 overflow-hidden relative z-10`}
            style={{ height: isTerminalExpanded ? '220px' : '32px' }}
          >
            {/* Header tab */}
            <div className="h-8 border-b border-strong bg-[#0e0e0d] px-4 flex items-center justify-between font-mono text-[10px] select-none">
              <div className="flex items-center gap-3">
                <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
                <span className="font-bold text-primary">LIVE THOUGHT STREAM</span>
                <span className="text-muted">|</span>
                <span className="text-muted">WS STATUS: ONLINE</span>
              </div>
              <div className="flex items-center gap-3">
                <button onClick={handleClearLogs} className="text-muted hover:text-primary transition uppercase text-[9px]">Clear</button>
                <button
                  onClick={() => setIsTerminalExpanded(!isTerminalExpanded)}
                  className="text-accent font-bold hover:underline transition uppercase text-[9px]"
                >
                  {isTerminalExpanded ? 'Collapse ↓' : 'Expand ↑'}
                </button>
              </div>
            </div>

            {/* Stream content */}
            <div className="flex-1 p-3.5 bg-base overflow-y-auto terminal-scroll font-mono text-[11px] leading-relaxed">
              {agentFeed.length === 0 ? (
                <div className="text-muted">Ready. Awaiting pipeline triggers...</div>
              ) : (
                <div className="flex flex-col gap-1.5">
                  {agentFeed.map((item, idx) => (
                    <div key={idx} className="flex gap-2">
                      <span className="text-muted">[{item.time}]</span>
                      <span className={item.type === 'error' ? 'text-danger' : item.type === 'success' ? 'text-success' : 'text-secondary'}>
                        {item.message}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

        </div>
      </div>

      {/* Floating Notifications */}
      <div className="fixed bottom-10 right-6 z-50 flex flex-col gap-2.5 max-w-sm pointer-events-none">
        {notifications.map((n) => (
          <div
            key={n.id}
            className={`p-3 rounded border pointer-events-auto backdrop-blur-md shadow-2xl flex items-center gap-2 transition-all font-mono text-[10.5px] ${
              n.type === 'success' 
                ? 'bg-success-dim border-success/30 text-success' 
                : n.type === 'warning' 
                ? 'bg-danger-dim border-danger/30 text-danger' 
                : 'bg-accent-dim border-accent/30 text-accent'
            }`}
          >
            <span>{n.message}</span>
          </div>
        ))}
      </div>

      {/* Popovers / Modals */}
      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
        onSwitchTab={(tab) => {
          setActiveTab(tab);
        }}
        onToggleChaosMonkey={() => handleToggleChaosMonkey(!chaosEnabled, 30, 'ALL AGENTS')}
        onTriggerDiscovery={handleTriggerDiscovery}
        onTriggerSimulator={() => {
          setActiveTab('simulator');
        }}
      />

      <ChaosMonkeyPopover
        isOpen={isChaosMonkeyOpen}
        onClose={() => setIsChaosMonkeyOpen(false)}
        isEnabled={chaosEnabled}
        onToggle={handleToggleChaosMonkey}
      />

      <ArchModeOverlay
        isActive={isArchModeOpen}
        onClose={() => setIsArchModeOpen(false)}
        activeAgent={activeAgent}
        agentState={activeAgentState}
      />

    </div>
  );
}
