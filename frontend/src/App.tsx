import React, { useState, useEffect, useCallback, useRef } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Position,
  MarkerType,
  Controls,
  Background,
} from 'reactflow';
import 'reactflow/dist/style.css';
import {
  Activity,
  ShieldCheck,
  Zap,
  Settings2,
  RefreshCw,
  Search,
  CheckCircle2,
  XCircle,
  Eye,
  AlertTriangle,
  Play,
  Layers,
  Sparkles,
  Check,
  FileKey2,
  Trash2,
  Network,
  Clock,
  Coins,
  Cpu,
  Mail,
  ChevronRight,
  TrendingUp,
} from 'lucide-react';

const API_BASE = 'http://127.0.0.1:8000/v2';
const WS_BASE = 'ws://127.0.0.1:8000/v2/ws/events';

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
}

export default function App() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'workflows' | 'leads' | 'approvals' | 'config' | 'observability'>('dashboard');
  const [companyInput, setCompanyInput] = useState('RazorX Fintech');
  const [domainInput, setDomainInput] = useState('hr_saas');
  
  // App States
  const [leads, setLeads] = useState<Lead[]>([]);
  const [approvalQueue, setApprovalQueue] = useState<Lead[]>([]);
  const [agentFeed, setAgentFeed] = useState<any[]>([]);
  const [chaosEnabled, setChaosEnabled] = useState(false);
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const [agentStatuses, setAgentStatuses] = useState<any[]>([]);
  
  // Observability States
  const [traces, setTraces] = useState<any[]>([]);
  const [selectedTraceId, setSelectedTraceId] = useState<string>('');
  const [selectedTraceSpans, setSelectedTraceSpans] = useState<any[]>([]);
  const [metrics, setMetrics] = useState<any>(null);
  
  // Config States
  const [icpConfig, setIcpConfig] = useState<any>({});
  const [personasConfig, setPersonasConfig] = useState<any>({});
  
  // Real-time Agent Thoughts Stream State
  const [streamingThoughts, setStreamingThoughts] = useState<Record<string, string>>({});
  
  // React Flow States
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  
  // WS Reference
  const wsRef = useRef<WebSocket | null>(null);

  // Initialize pipeline DAG Nodes
  const initializeDAG = useCallback((runCompany: string) => {
    const nodeNames = [
      { id: 'trigger_monitor', label: 'Trigger Monitor', desc: 'News & Feeds Scanner' },
      { id: 'company_enricher', label: 'Company Enricher', desc: 'Metadata & Tech Stack' },
      { id: 'icp_matcher', label: 'ICP Matcher', desc: 'Scores Compatibility' },
      { id: 'shadow_agent', label: 'Shadow Agent', desc: "Devil's Advocate Check" },
      { id: 'persona_finder', label: 'Persona Finder', desc: 'Matches Buyer Personas' },
      { id: 'contact_enricher', label: 'Contact Enricher', desc: 'PII/TEE Encrypter' },
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
        background: 'rgba(10, 15, 30, 0.95)',
        color: '#f8fafc',
        border: '1px solid rgba(6, 182, 212, 0.15)',
        borderRadius: '12px',
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
        id: `e-${nodeNames[i].id}-${nodeNames[i+1].id}`,
        source: nodeNames[i].id,
        target: nodeNames[i+1].id,
        animated: false,
        style: { stroke: 'rgba(6, 182, 212, 0.12)', strokeWidth: 2 },
        markerEnd: { type: MarkerType.ArrowClosed, color: 'rgba(6, 182, 212, 0.12)' }
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
        
        let borderStyle = '1px solid rgba(6, 182, 212, 0.15)';
        let glowStyle = 'none';
        let bgStyle = 'rgba(10, 15, 30, 0.95)';

        switch (status) {
          case 'thinking':
            borderStyle = '1px solid #06b6d4';
            glowStyle = '0 0 20px rgba(6, 182, 212, 0.4)';
            bgStyle = 'rgba(6, 182, 212, 0.08)';
            break;
          case 'completed':
            borderStyle = '1px solid #10b981';
            glowStyle = '0 0 15px rgba(16, 185, 129, 0.25)';
            bgStyle = 'rgba(16, 185, 129, 0.06)';
            break;
          case 'failed':
            borderStyle = '1px solid #f43f5e';
            glowStyle = '0 0 20px rgba(244, 63, 94, 0.4)';
            bgStyle = 'rgba(244, 63, 94, 0.08)';
            break;
          case 'retrying':
            borderStyle = '1px solid #f59e0b';
            glowStyle = '0 0 15px rgba(245, 158, 11, 0.3)';
            bgStyle = 'rgba(245, 158, 11, 0.06)';
            break;
          case 'recovered':
            borderStyle = '1px solid #eab308';
            glowStyle = '0 0 15px rgba(234, 179, 8, 0.2)';
            bgStyle = 'rgba(234, 179, 8, 0.05)';
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
            animated: status === 'completed',
            style: { 
              stroke: status === 'completed' ? '#10b981' : 'rgba(6, 182, 212, 0.12)', 
              strokeWidth: 2.5 
            },
            markerEnd: {
              type: MarkerType.ArrowClosed,
              color: status === 'completed' ? '#10b981' : 'rgba(6, 182, 212, 0.12)'
            }
          };
        }
        return edge;
      })
    );
  }, []);

  // Fetch initial APIs
  const fetchData = useCallback(async () => {
    try {
      const leadsRes = await fetch(`${API_BASE}/workflows/leads`);
      if (leadsRes.ok) {
        const data = await leadsRes.json();
        setLeads(data);
        if (data.length > 0 && !selectedLead) {
          setSelectedLead(data[0]);
        }
      }
      
      const approvalsRes = await fetch(`${API_BASE}/approvals/queue`);
      if (approvalsRes.ok) {
        const data = await approvalsRes.json();
        setApprovalQueue(data);
      }

      const configRes = await fetch(`${API_BASE}/config/hr_saas`);
      if (configRes.ok) {
        const data = await configRes.json();
        setIcpConfig(data.icp);
        setPersonasConfig(data.personas);
      }

      const agentsRes = await fetch(`${API_BASE}/agents`);
      if (agentsRes.ok) {
        const data = await agentsRes.json();
        setAgentStatuses(data);
      }

      const chaosRes = await fetch(`${API_BASE}/chaos/status`);
      if (chaosRes.ok) {
        const data = await chaosRes.json();
        setChaosEnabled(data.enabled);
      }

      // Observability fetch
      const tracesRes = await fetch(`${API_BASE}/observability/traces`);
      if (tracesRes.ok) {
        const data = await tracesRes.json();
        setTraces(data.traces || []);
        if (data.traces && data.traces.length > 0) {
          setSelectedTraceId(data.traces[0].trace_id);
        }
      }

      const metricsRes = await fetch(`${API_BASE}/observability/metrics`);
      if (metricsRes.ok) {
        const data = await metricsRes.json();
        setMetrics(data);
      }
    } catch (e) {
      console.error('Fetch error:', e);
    }
  }, [selectedLead]);

  // Fetch single trace waterfall
  const fetchTraceDetail = useCallback(async (traceId: string) => {
    if (!traceId) return;
    try {
      const res = await fetch(`${API_BASE}/observability/traces/${traceId}`);
      if (res.ok) {
        const data = await res.json();
        setSelectedTraceSpans(data.spans || []);
      }
    } catch (e) {
      console.error(e);
    }
  }, []);

  useEffect(() => {
    if (selectedTraceId) {
      fetchTraceDetail(selectedTraceId);
    }
  }, [selectedTraceId, fetchTraceDetail]);

  useEffect(() => {
    fetchData();
    initializeDAG('RazorX Fintech');
    
    // Connect WebSocket
    const connectWS = () => {
      const ws = new WebSocket(WS_BASE);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('WS connected to backend gateway');
      };

      ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        console.log('WS Event received:', msg);

        // Update real-time logs feed
        setAgentFeed((prev) => [msg, ...prev]);

        const agentName = msg.agent;
        const wsType = msg.type;
        const company = msg.target;

        // Clean streaming thoughts when workflow triggers
        if (wsType === 'workflow_started') {
          setStreamingThoughts({});
          initializeDAG(company || 'RazorX Fintech');
        }

        // Handle streaming thoughts chunks
        if (wsType === 'agent_reasoning' && msg.data?.chunk) {
          setStreamingThoughts((prev) => ({
            ...prev,
            [agentName]: (prev[agentName] || '') + msg.data.chunk
          }));
        }

        // Map status updates to UI nodes
        if (wsType === 'agent_thinking') {
          updateNodeStatus(agentName, 'thinking');
        } else if (wsType === 'agent_completed') {
          updateNodeStatus(agentName, 'completed', msg.data.output);
        } else if (wsType === 'agent_failed') {
          updateNodeStatus(agentName, 'failed');
        } else if (wsType === 'agent_retrying') {
          updateNodeStatus(agentName, 'retrying');
        } else if (wsType === 'agent_recovered') {
          updateNodeStatus(agentName, 'recovered', msg.data);
        }

        if (wsType === 'workflow_completed') {
          fetchData();
        }
      };

      ws.onclose = () => {
        console.log('WS disconnected. Reconnecting in 3s...');
        setTimeout(connectWS, 3000);
      };
    };

    connectWS();

    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, [fetchData, initializeDAG, updateNodeStatus]);

  // Actions
  const runDiscovery = async () => {
    setAgentFeed([]);
    setStreamingThoughts({});
    initializeDAG(companyInput);
    
    try {
      const res = await fetch(`${API_BASE}/workflows/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          domain: domainInput,
          company_name: companyInput
        })
      });
      if (res.ok) {
        setActiveTab('workflows');
      }
    } catch (e) {
      console.error(e);
    }
  };

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

  const toggleChaosMonkey = async () => {
    try {
      const res = await fetch(`${API_BASE}/chaos/toggle`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: !chaosEnabled })
      });
      if (res.ok) {
        const data = await res.json();
        setChaosEnabled(data.enabled);
      }
    } catch (e) {
      console.error(e);
    }
  };

  // Mock Decryption for TEE viewing
  const [decryptedPII, setDecryptedPII] = useState<Record<string, { email: string; phone: string }>>({});
  const simulateTEEAccess = (leadId: string, rawEmail: string, rawPhone: string, plainEmail: string, plainPhone: string) => {
    setDecryptedPII(prev => ({
      ...prev,
      [leadId]: {
        email: plainEmail || "priya.sharma@razorx.in",
        phone: plainPhone || "+91-9876543210"
      }
    }));
  };

  return (
    <div className="flex flex-1 overflow-hidden cyber-grid" style={{ background: 'var(--bg-main)', height: '100vh' }}>
      {/* Sidebar Navigation */}
      <aside className="w-72 glass-panel flex flex-col justify-between p-6 m-4 mr-0 border border-cyan-500/10 rounded-2xl">
        <div>
          {/* Logo / Header */}
          <div className="flex items-center gap-3.5 mb-9 px-1">
            <div className="h-11 w-11 rounded-xl bg-gradient-to-br from-cyan-400 via-cyan-600 to-violet-600 flex items-center justify-center glow-active">
              <Zap className="h-5.5 w-5.5 text-white" />
            </div>
            <div>
              <h1 className="font-black text-base tracking-wider text-slate-100 flex items-center gap-1">
                NEXUS<span className="text-cyan-400">AI</span>
              </h1>
              <span className="text-[10px] text-violet-400 font-mono tracking-widest font-bold block uppercase">
                DAG ORCHESTRATOR v3
              </span>
            </div>
          </div>

          <div className="text-[10px] text-slate-500 font-mono uppercase font-bold tracking-widest px-2 mb-3">
            Core Modules
          </div>
          <nav className="flex flex-col gap-1.5">
            <button
              onClick={() => setActiveTab('dashboard')}
              className={`flex items-center gap-3.5 px-4 py-3.5 rounded-xl transition duration-200 text-sm font-semibold border ${
                activeTab === 'dashboard'
                  ? 'bg-cyan-500/10 text-cyan-300 border-cyan-500/25 shadow-[0_0_15px_rgba(6,182,212,0.1)]'
                  : 'text-slate-400 border-transparent hover:text-slate-100 hover:bg-slate-900/50 hover:border-slate-800'
              }`}
            >
              <Activity className="h-4.5 w-4.5" /> Dashboard
            </button>
            <button
              onClick={() => setActiveTab('workflows')}
              className={`flex items-center gap-3.5 px-4 py-3.5 rounded-xl transition duration-200 text-sm font-semibold border ${
                activeTab === 'workflows'
                  ? 'bg-cyan-500/10 text-cyan-300 border-cyan-500/25 shadow-[0_0_15px_rgba(6,182,212,0.1)]'
                  : 'text-slate-400 border-transparent hover:text-slate-100 hover:bg-slate-900/50 hover:border-slate-800'
              }`}
            >
              <Layers className="h-4.5 w-4.5" /> Live Agent Graph
            </button>
            <button
              onClick={() => setActiveTab('leads')}
              className={`flex items-center gap-3.5 px-4 py-3.5 rounded-xl transition duration-200 text-sm font-semibold border ${
                activeTab === 'leads'
                  ? 'bg-cyan-500/10 text-cyan-300 border-cyan-500/25 shadow-[0_0_15px_rgba(6,182,212,0.1)]'
                  : 'text-slate-400 border-transparent hover:text-slate-100 hover:bg-slate-900/50 hover:border-slate-800'
              }`}
            >
              <Sparkles className="h-4.5 w-4.5" /> Qualified Leads
            </button>
            <button
              onClick={() => setActiveTab('approvals')}
              className={`flex items-center gap-3.5 px-4 py-3.5 rounded-xl transition duration-200 text-sm font-semibold border ${
                activeTab === 'approvals'
                  ? 'bg-cyan-500/10 text-cyan-300 border-cyan-500/25 shadow-[0_0_15px_rgba(6,182,212,0.1)]'
                  : 'text-slate-400 border-transparent hover:text-slate-100 hover:bg-slate-900/50 hover:border-slate-800'
              }`}
            >
              <ShieldCheck className="h-4.5 w-4.5" /> Approvals Queue
              {approvalQueue.length > 0 && (
                <span className="ml-auto bg-amber-500/20 text-amber-400 border border-amber-500/30 px-2 py-0.5 rounded-md text-[10px] font-bold font-mono">
                  {approvalQueue.length}
                </span>
              )}
            </button>
            <button
              onClick={() => setActiveTab('config')}
              className={`flex items-center gap-3.5 px-4 py-3.5 rounded-xl transition duration-200 text-sm font-semibold border ${
                activeTab === 'config'
                  ? 'bg-cyan-500/10 text-cyan-300 border-cyan-500/25 shadow-[0_0_15px_rgba(6,182,212,0.1)]'
                  : 'text-slate-400 border-transparent hover:text-slate-100 hover:bg-slate-900/50 hover:border-slate-800'
              }`}
            >
              <Settings2 className="h-4.5 w-4.5" /> Domain Configs
            </button>
            <button
              onClick={() => setActiveTab('observability')}
              className={`flex items-center gap-3.5 px-4 py-3.5 rounded-xl transition duration-200 text-sm font-semibold border ${
                activeTab === 'observability'
                  ? 'bg-cyan-500/10 text-cyan-300 border-cyan-500/25 shadow-[0_0_15px_rgba(6,182,212,0.1)]'
                  : 'text-slate-400 border-transparent hover:text-slate-100 hover:bg-slate-900/50 hover:border-slate-800'
              }`}
            >
              <FileKey2 className="h-4.5 w-4.5" /> Observability & TEE
            </button>
          </nav>
        </div>

        {/* Chaos Monkey Widget */}
        <div className="p-4.5 rounded-2xl glass-panel border border-red-500/15" style={{ background: 'rgba(244, 63, 94, 0.03)' }}>
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4.5 w-4.5 text-rose-500" />
              <span className="text-xs font-bold text-rose-500 font-mono tracking-wider uppercase">CHAOS MONKEY</span>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" checked={chaosEnabled} onChange={toggleChaosMonkey} className="sr-only peer" />
              <div className="w-8 h-4.5 bg-slate-800 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-slate-400 after:border-slate-300 after:border after:rounded-full after:h-3.5 after:w-3.5 after:transition-all peer-checked:bg-rose-600 peer-checked:after:bg-white"></div>
            </label>
          </div>
          <p className="text-[11px] text-slate-500 leading-relaxed font-medium">
            Simulate transient network faults dynamically. Watch agents self-heal automatically using fallback registries.
          </p>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col overflow-hidden p-4">
        
        {/* Top Header Control Panel */}
        <header className="flex justify-between items-center mb-4 glass-panel p-4 px-6 border border-cyan-500/10">
          <div className="flex items-center gap-3 flex-1 max-w-xl">
            <div className="flex items-center gap-2 bg-slate-950/70 border border-cyan-500/10 rounded-xl px-4 py-3 w-full focus-within:border-cyan-500/30 transition-all">
              <Search className="h-4.5 w-4.5 text-slate-500" />
              <input
                type="text"
                placeholder="Target Company Prospect (e.g. RazorX Fintech, AcmeCorp)"
                value={companyInput}
                onChange={(e) => setCompanyInput(e.target.value)}
                className="bg-transparent border-none text-white text-xs w-full focus:outline-none placeholder-slate-600"
              />
            </div>
            <button
              onClick={runDiscovery}
              className="flex items-center justify-center gap-2.5 bg-gradient-to-r from-cyan-500 to-violet-600 hover:from-cyan-400 hover:to-violet-500 text-white text-xs font-bold px-6 py-3.5 rounded-xl transition duration-300 shadow-[0_4px_20px_rgba(6,182,212,0.2)] whitespace-nowrap"
            >
              <Play className="h-4 w-4 fill-current text-cyan-200" /> TRIGGER DISCOVERY
            </button>
          </div>
          
          <div className="flex items-center gap-3 font-mono text-[11px]">
            <div className="flex items-center gap-2 px-3 py-2 bg-slate-950/80 rounded-xl border border-cyan-500/10">
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span className="text-slate-400">Router status:</span>
              <span className="text-emerald-400 font-extrabold">Groq / Cerebras</span>
            </div>
            <div className="flex items-center gap-2 px-3 py-2 bg-slate-950/80 rounded-xl border border-cyan-500/10">
              <span className="text-slate-400">Fallback:</span>
              <span className="text-cyan-400 font-bold">DuckDuckGo / Firecrawl v2</span>
            </div>
          </div>
        </header>

        {/* Tab Contents */}
        <div className="flex-1 flex overflow-hidden gap-4">
          
          {/* TAB 1: DASHBOARD */}
          {activeTab === 'dashboard' && (
            <div className="flex-1 flex flex-col gap-4 overflow-y-auto pr-1">
              
              {/* Stats Cards */}
              <div className="grid grid-cols-4 gap-4">
                <div className="glass-panel p-5 border border-cyan-500/10 flex flex-col justify-between">
                  <div className="flex items-center justify-between text-slate-400">
                    <span className="text-[11px] font-bold tracking-wider uppercase font-mono">Monitored Prospects</span>
                    <TrendingUp className="h-4 w-4 text-cyan-400" />
                  </div>
                  <div className="flex justify-between items-baseline mt-4">
                    <span className="text-4xl font-black text-slate-100">{leads.length}</span>
                    <span className="text-xs text-emerald-400 font-mono font-bold bg-emerald-500/5 px-2 py-0.5 rounded">+12%</span>
                  </div>
                </div>
                <div className="glass-panel p-5 border border-cyan-500/10 flex flex-col justify-between">
                  <div className="flex items-center justify-between text-slate-400">
                    <span className="text-[11px] font-bold tracking-wider uppercase font-mono">ICP Qualified</span>
                    <Check className="h-4.5 w-4.5 text-emerald-400" />
                  </div>
                  <div className="flex justify-between items-baseline mt-4">
                    <span className="text-4xl font-black text-emerald-400">{leads.filter(l => l.icp_score >= 70).length}</span>
                    <span className="text-xs text-cyan-400 font-mono font-semibold bg-cyan-500/5 px-2 py-0.5 rounded">Score &ge; 70</span>
                  </div>
                </div>
                <div className="glass-panel p-5 border border-cyan-500/10 flex flex-col justify-between">
                  <div className="flex items-center justify-between text-slate-400">
                    <span className="text-[11px] font-bold tracking-wider uppercase font-mono">Divergence Alerts</span>
                    <AlertTriangle className="h-4.5 w-4.5 text-amber-500" />
                  </div>
                  <div className="flex justify-between items-baseline mt-4">
                    <span className="text-4xl font-black text-amber-500">{approvalQueue.length}</span>
                    <span className="text-xs text-amber-400 bg-amber-500/5 px-2 py-0.5 rounded font-mono">Needs Approval</span>
                  </div>
                </div>
                <div className="glass-panel p-5 border border-cyan-500/10 flex flex-col justify-between">
                  <div className="flex items-center justify-between text-slate-400">
                    <span className="text-[11px] font-bold tracking-wider uppercase font-mono">API Self-Heal</span>
                    <Cpu className="h-4.5 w-4.5 text-cyan-400" />
                  </div>
                  <div className="flex justify-between items-baseline mt-4">
                    <span className="text-4xl font-black text-cyan-400">100%</span>
                    <span className="text-xs text-emerald-400 bg-emerald-500/5 px-2 py-0.5 rounded font-mono">Fault Tolerance</span>
                  </div>
                </div>
              </div>

              {/* Lower Section Grid */}
              <div className="flex-1 grid grid-cols-12 gap-4 min-h-0">
                {/* Leads Registry */}
                <div className="col-span-7 glass-panel border border-cyan-500/10 p-6 flex flex-col overflow-hidden">
                  <div className="flex justify-between items-center mb-4">
                    <h3 className="text-sm font-extrabold tracking-wider font-mono uppercase text-slate-300 flex items-center gap-2">
                      <Sparkles className="h-4 w-4 text-cyan-400" /> Prospects Database
                    </h3>
                    <span className="text-[10px] text-slate-500 font-mono">Updated: Real-time</span>
                  </div>
                  
                  <div className="flex-1 overflow-y-auto">
                    <table className="w-full text-left text-xs">
                      <thead>
                        <tr className="border-b border-cyan-500/10 text-slate-400 font-mono uppercase text-[10px]">
                          <th className="pb-3 font-semibold">Company Name</th>
                          <th className="pb-3 font-semibold text-center">ICP Fit</th>
                          <th className="pb-3 font-semibold">Shadow Verdict</th>
                          <th className="pb-3 font-semibold">Attestation</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-cyan-500/5">
                        {leads.map((lead) => (
                          <tr
                            key={lead.id}
                            onClick={() => { setSelectedLead(lead); setActiveTab('leads'); }}
                            className="hover:bg-slate-900/35 cursor-pointer transition duration-150 group"
                          >
                            <td className="py-3.5 font-bold text-slate-100 group-hover:text-cyan-400 transition-colors">
                              {lead.company_name}
                            </td>
                            <td className="py-3.5 text-center">
                              <span className={`px-2.5 py-1 rounded font-mono font-bold text-[10px] ${
                                lead.icp_score >= 70 ? 'text-emerald-400 bg-emerald-500/5 border border-emerald-500/15' : 'text-slate-400 bg-slate-500/5'
                              }`}>
                                {lead.icp_score}%
                              </span>
                            </td>
                            <td className="py-3.5 font-mono text-[10px]">
                              {lead.shadow_verdict?.status === 'DIVERGENCE_WARNING' ? (
                                <span className="text-rose-400 bg-rose-500/5 border border-rose-500/15 px-2 py-0.5 rounded flex items-center gap-1 w-max">
                                  ⚠️ Risk Warning
                                </span>
                              ) : (
                                <span className="text-emerald-400 bg-emerald-500/5 border border-emerald-500/15 px-2 py-0.5 rounded flex items-center gap-1 w-max">
                                  ✓ Verified Fit
                                </span>
                              )}
                            </td>
                            <td className="py-3.5">
                              <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-mono font-bold tracking-wider ${
                                lead.status === 'approved' ? 'text-emerald-400 bg-emerald-500/10 border border-emerald-500/20' :
                                lead.status === 'approval_required' ? 'text-amber-500 bg-amber-500/10 border border-amber-500/20' :
                                'text-slate-400 bg-slate-900/60 border border-slate-800'
                              }`}>
                                {lead.status}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Console Event Logs */}
                <div className="col-span-5 glass-panel border border-cyan-500/10 p-6 flex flex-col overflow-hidden">
                  <div className="flex justify-between items-center mb-4">
                    <h3 className="text-sm font-extrabold tracking-wider font-mono uppercase text-slate-300 flex items-center gap-2">
                      <ChevronRight className="h-4.5 w-4.5 text-cyan-400 animate-pulse" /> Live Thought Stream
                    </h3>
                    <div className="flex items-center gap-1.5 font-mono text-[9px] text-cyan-500">
                      <span className="h-1.5 w-1.5 bg-cyan-400 rounded-full animate-ping"></span> Websocket listening
                    </div>
                  </div>
                  
                  <div className="flex-1 overflow-y-auto flex flex-col gap-3 font-mono text-xs pr-1">
                    {agentFeed.length === 0 ? (
                      <div className="text-center text-slate-600 py-16">
                        No active workflow events. Trigger a run to stream agent logs.
                      </div>
                    ) : (
                      agentFeed.map((evt, idx) => (
                        <div key={idx} className="p-3 bg-slate-950/70 rounded-xl border border-cyan-500/5 text-[11px]">
                          <div className="flex justify-between items-center mb-1 text-[10px]">
                            <span className={`font-bold ${
                              evt.type === 'agent_thinking' ? 'text-cyan-400' :
                              evt.type === 'agent_completed' ? 'text-emerald-400' :
                              evt.type === 'agent_failed' ? 'text-rose-500' : 'text-slate-400'
                            }`}>
                              [{evt.agent.toUpperCase()}]
                            </span>
                            <span className="text-slate-600">{new Date(evt.timestamp).toLocaleTimeString()}</span>
                          </div>
                          <p className="text-slate-400 font-sans leading-relaxed">
                            {evt.type === 'agent_thinking' ? 'Acquiring inputs and executing toolchain...' :
                             evt.type === 'agent_reasoning' ? evt.data?.chunk :
                             evt.type === 'agent_completed' ? `Completed. Score fit: ${evt.data?.output?.score || 'Processed'}` :
                             evt.type === 'agent_failed' ? `Error: ${evt.data?.error}` :
                             JSON.stringify(evt.data)}
                          </p>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: DAG WORKFLOWS */}
          {activeTab === 'workflows' && (
            <div className="flex-1 glass-panel border border-cyan-500/10 flex flex-col overflow-hidden" style={{ position: 'relative' }}>
              
              {/* DAG Nodes Color Code Indicator */}
              <div className="absolute top-4 left-4 z-10 glass-panel p-3 px-4 flex gap-4 text-[10px] font-mono border border-cyan-500/15" style={{ background: 'rgba(5, 8, 20, 0.9)' }}>
                <div className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-slate-700"></span> Idle</div>
                <div className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-cyan-400 animate-pulse"></span> Thinking</div>
                <div className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-emerald-500"></span> Completed</div>
                <div className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-rose-500"></span> Failed</div>
                <div className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-amber-500"></span> Retrying</div>
                <div className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-yellow-400"></span> Self-Healed</div>
              </div>

              <div className="flex-1" style={{ height: '100%' }}>
                <ReactFlow nodes={nodes} edges={edges} fitView fitViewOptions={{ padding: 0.1 }}>
                  <Controls />
                  <Background color="#22d3ee" style={{ opacity: 0.03 }} gap={16} />
                </ReactFlow>
              </div>

              {/* Streaming Thought Board below */}
              <div className="h-56 border-t border-cyan-500/10 p-5 bg-slate-950/90 overflow-y-auto font-mono text-xs text-cyan-400">
                <span className="text-slate-500 font-bold uppercase tracking-wider text-[10px] block mb-3 border-b border-slate-900 pb-2">
                  Streaming Agent Reasoner Console
                </span>
                {Object.keys(streamingThoughts).length === 0 ? (
                  <span className="text-slate-700 italic">Awaiting active agent execution...</span>
                ) : (
                  Object.entries(streamingThoughts).map(([agent, text]) => (
                    <div key={agent} className="mb-3.5 bg-slate-900/40 p-3 rounded-lg border border-slate-900">
                      <span className="text-violet-400 font-bold uppercase text-[10px] block mb-1">[{agent}]</span>
                      <span className="text-slate-300 font-sans leading-relaxed block">{text}</span>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {/* TAB 3: LEADS PIPELINE */}
          {activeTab === 'leads' && (
            <div className="flex-1 grid grid-cols-12 gap-4 overflow-hidden">
              {/* Leads side-list */}
              <div className="col-span-4 glass-panel border border-cyan-500/10 p-5 overflow-y-auto flex flex-col gap-2">
                <h3 className="text-xs font-bold font-mono tracking-wider text-slate-400 uppercase mb-3 px-1">Monitored Leads Registry</h3>
                {leads.length === 0 ? (
                  <div className="text-xs text-slate-600 font-mono p-4">No records stored.</div>
                ) : (
                  leads.map((l) => (
                    <div
                      key={l.id}
                      onClick={() => setSelectedLead(l)}
                      className={`p-4.5 rounded-xl border transition duration-150 cursor-pointer ${
                        selectedLead?.id === l.id
                          ? 'bg-cyan-500/10 border-cyan-500/35 shadow-[0_0_15px_rgba(6,182,212,0.08)]'
                          : 'bg-slate-950/40 border-slate-900 hover:border-slate-800'
                      }`}
                    >
                      <div className="flex justify-between items-start mb-2">
                        <h4 className="font-extrabold text-sm text-slate-200">{l.company_name}</h4>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                          l.icp_score >= 70 ? 'text-emerald-400 bg-emerald-500/5' : 'text-slate-400 bg-slate-500/5'
                        }`}>
                          {l.icp_score}%
                        </span>
                      </div>
                      <div className="flex justify-between items-center text-[10px] text-slate-500">
                        <span>Status: <strong className="text-slate-300 uppercase">{l.status}</strong></span>
                        <span>{new Date(l.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                  ))
                )}
              </div>

              {/* Lead Details Workspace */}
              <div className="col-span-8 glass-panel border border-cyan-500/10 p-6 overflow-y-auto flex flex-col gap-6">
                {selectedLead ? (
                  <div>
                    {/* Header */}
                    <div className="flex justify-between items-start border-b border-cyan-500/10 pb-4">
                      <div>
                        <h2 className="text-xl font-black text-slate-100 mb-1.5">{selectedLead.company_name}</h2>
                        <div className="text-xs text-slate-400 flex items-center gap-3">
                          <span>HQ: <strong className="text-slate-200">{selectedLead.company_details?.hq || 'Bangalore, India'}</strong></span>
                          <span>|</span>
                          <span>Employees: <strong className="text-slate-200">{selectedLead.company_details?.employees || '87'}</strong></span>
                        </div>
                      </div>
                      <div className="flex flex-col items-end">
                        <span className="px-3 py-1.5 rounded-lg text-xs font-mono font-black text-emerald-400 bg-emerald-500/5 border border-emerald-500/20">
                          ICP MATCH: {selectedLead.icp_score}%
                        </span>
                        <span className="text-[10px] text-slate-500 font-mono mt-1">ID: {selectedLead.id}</span>
                      </div>
                    </div>

                    {/* Section grid */}
                    <div className="grid grid-cols-2 gap-4 mt-6">
                      {/* Left: Decision makers */}
                      <div className="flex flex-col gap-4">
                        <h4 className="text-xs font-bold text-slate-400 font-mono uppercase tracking-wider flex items-center gap-1.5">
                          <Mail className="h-4 w-4 text-cyan-400" /> secure Contacts
                        </h4>
                        
                        {selectedLead.contacts.length === 0 ? (
                          <div className="text-xs text-slate-600 font-mono">No contacts enriched.</div>
                        ) : (
                          selectedLead.contacts.map((c, i) => (
                            <div key={i} className="p-4 bg-slate-950/70 border border-slate-900 rounded-xl text-xs flex flex-col gap-3">
                              <div className="flex justify-between border-b border-slate-900 pb-2">
                                <span className="font-extrabold text-slate-200">{c.name}</span>
                                <span className="text-cyan-400 font-mono text-[10px]">{c.title}</span>
                              </div>
                              
                              <div className="flex flex-col gap-2 font-mono text-[10px] text-slate-400">
                                <div className="flex justify-between items-center">
                                  <span>Email:</span>
                                  {decryptedPII[selectedLead.id] ? (
                                    <span className="text-emerald-400 font-bold">{decryptedPII[selectedLead.id].email}</span>
                                  ) : (
                                    <div className="flex items-center gap-2">
                                      <span className="text-slate-500">{c.email}</span>
                                      <button
                                        onClick={() => simulateTEEAccess(selectedLead.id, c.raw_email, c.raw_phone, c.plain_email, c.plain_phone)}
                                        className="px-2 py-0.5 rounded bg-cyan-500/10 hover:bg-cyan-500/20 border border-cyan-500/20 text-cyan-300 text-[9px] flex items-center gap-1 transition"
                                      >
                                        <Eye className="h-3 w-3" /> DECRYPT
                                      </button>
                                    </div>
                                  )}
                                </div>
                                <div className="flex justify-between items-center">
                                  <span>Phone:</span>
                                  {decryptedPII[selectedLead.id] ? (
                                    <span className="text-emerald-400 font-bold">{decryptedPII[selectedLead.id].phone}</span>
                                  ) : (
                                    <span className="text-slate-500">{c.phone}</span>
                                  )}
                                </div>
                              </div>
                            </div>
                          ))
                        )}
                      </div>

                      {/* Right: GraphRAG Knowledge Graph visualizer */}
                      <div className="flex flex-col gap-4">
                        <h4 className="text-xs font-bold text-slate-400 font-mono uppercase tracking-wider flex items-center gap-1.5">
                          <Network className="h-4 w-4 text-violet-400" /> GraphRAG Network Entities
                        </h4>
                        
                        <div className="p-4 bg-slate-950/70 border border-slate-900 rounded-xl text-xs flex flex-col gap-3 min-h-[140px] justify-center">
                          <div className="flex items-center gap-2 text-[10px] text-slate-500 font-mono uppercase">
                            <span className="h-1.5 w-1.5 bg-violet-500 rounded-full"></span> Connected relationships
                          </div>
                          
                          <div className="flex flex-wrap gap-2">
                            <span className="px-2.5 py-1 rounded-md bg-cyan-500/5 border border-cyan-500/15 text-cyan-400 font-mono text-[10px]">
                              Company: {selectedLead.company_name}
                            </span>
                            {selectedLead.company_details?.tech_stack?.map((t: string) => (
                              <span key={t} className="px-2.5 py-1 rounded-md bg-violet-500/5 border border-violet-500/15 text-violet-400 font-mono text-[10px]">
                                technology: {t}
                              </span>
                            ))}
                            {selectedLead.contacts.map((c: any) => (
                              <span key={c.name} className="px-2.5 py-1 rounded-md bg-emerald-500/5 border border-emerald-500/15 text-emerald-400 font-mono text-[10px]">
                                person: {c.name}
                              </span>
                            ))}
                            {selectedLead.company_details?.industry && (
                              <span className="px-2.5 py-1 rounded-md bg-amber-500/5 border border-amber-500/15 text-amber-400 font-mono text-[10px]">
                                industry: {selectedLead.company_details.industry}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Evidence Chain */}
                    <div className="mt-6 border-t border-slate-900 pt-6">
                      <h4 className="text-xs font-bold text-slate-400 font-mono uppercase tracking-wider mb-3">Evidence Chain</h4>
                      <div className="flex flex-col gap-2.5">
                        {selectedLead.evidence_chain.map((e, idx) => (
                          <div key={idx} className="flex gap-2 text-xs text-slate-300">
                            <span className="text-cyan-400 font-mono">[{idx + 1}]</span>
                            <span>{e}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Outreach email */}
                    <div className="mt-6 border-t border-slate-900 pt-6">
                      <h4 className="text-xs font-bold text-slate-400 font-mono uppercase tracking-wider mb-3">Outreach Template</h4>
                      <pre className="p-4.5 bg-slate-950 rounded-xl border border-slate-900 text-slate-200 font-mono text-[11px] whitespace-pre-wrap leading-relaxed">
                        {selectedLead.outreach_template || "No outreach generated."}
                      </pre>
                    </div>

                    {/* Cryptographic Attestation */}
                    {selectedLead.attestation && (
                      <div className="mt-6 p-4.5 bg-cyan-500/5 border border-cyan-500/15 rounded-xl text-xs font-mono">
                        <div className="flex items-center gap-2.5 text-cyan-400 font-extrabold mb-2 text-[11px]">
                          <ShieldCheck className="h-4.5 w-4.5" />
                          <span>TEE Cryptographic Audit Attestation Verified</span>
                        </div>
                        <div className="text-[10px] text-slate-400 flex flex-col gap-1">
                          <p><strong>Hash:</strong> {selectedLead.attestation.attestation_doc.hash}</p>
                          <p><strong>Signature:</strong> <span className="text-slate-300 break-all">{selectedLead.attestation.attestation_doc.signature}</span></p>
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="flex-1 flex items-center justify-center text-slate-500 text-xs font-mono">
                    Select a prospect from the side list to display lead workspace.
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 4: APPROVALS QUEUE */}
          {activeTab === 'approvals' && (
            <div className="flex-1 grid grid-cols-12 gap-4 overflow-hidden">
              {/* Approvals side-list */}
              <div className="col-span-4 glass-panel border border-cyan-500/10 p-5 overflow-y-auto flex flex-col gap-2">
                <h3 className="text-xs font-bold font-mono tracking-wider text-slate-400 uppercase mb-3 px-1">Required Review Queue</h3>
                {approvalQueue.length === 0 ? (
                  <div className="text-xs text-slate-600 font-mono p-4">No reviews required.</div>
                ) : (
                  approvalQueue.map((l) => (
                    <div
                      key={l.id}
                      onClick={() => setSelectedLead(l)}
                      className={`p-4.5 rounded-xl border transition duration-150 cursor-pointer ${
                        selectedLead?.id === l.id ? 'bg-amber-500/10 border-amber-500/35' : 'bg-slate-950/40 border-slate-900 hover:border-slate-800'
                      }`}
                    >
                      <h4 className="font-extrabold text-sm text-slate-200 mb-2">{l.company_name}</h4>
                      <span className="px-2.5 py-1 rounded text-[10px] font-mono font-bold text-rose-400 bg-rose-500/5 border border-rose-500/15 flex items-center gap-1 w-max">
                        <AlertTriangle className="h-3.5 w-3.5" /> Divergence Warning
                      </span>
                    </div>
                  ))
                )}
              </div>

              {/* Review Panel */}
              <div className="col-span-8 glass-panel border border-cyan-500/10 p-6 overflow-y-auto flex flex-col justify-between">
                {selectedLead && selectedLead.status === 'approval_required' ? (
                  <div className="flex-1 flex flex-col justify-between">
                    <div>
                      <div className="border-b border-slate-900 pb-4 mb-4">
                        <h2 className="text-lg font-black text-slate-100">{selectedLead.company_name}</h2>
                        <div className="mt-3 p-4 bg-rose-500/5 border border-rose-500/15 rounded-xl text-xs text-rose-400 leading-relaxed font-mono">
                          <span className="font-bold text-rose-300 block mb-1">SHADOW AGENT WARNING:</span>
                          {selectedLead.shadow_verdict?.reason}
                        </div>
                      </div>

                      <div className="mb-4">
                        <h4 className="text-xs font-bold text-slate-400 font-mono uppercase mb-2">Outreach Message Draft</h4>
                        <textarea
                          rows={11}
                          defaultValue={selectedLead.outreach_template}
                          id="edit-template-area"
                          className="w-full bg-slate-950 border border-slate-900 rounded-xl p-4.5 text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500/30 leading-relaxed"
                        />
                      </div>
                    </div>

                    <div className="flex gap-4 pt-4 border-t border-slate-900">
                      <button
                        onClick={() => {
                          const val = (document.getElementById('edit-template-area') as HTMLTextAreaElement)?.value;
                          handleApproval(selectedLead.id, 'approve', val);
                        }}
                        className="flex-1 py-3.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs tracking-wider transition duration-150"
                      >
                        APPROVE PROSPECT
                      </button>
                      <button
                        onClick={() => handleApproval(selectedLead.id, 'reject')}
                        className="flex-1 py-3.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs tracking-wider transition duration-150"
                      >
                        REJECT PROSPECT
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="flex-1 flex items-center justify-center text-slate-500 text-xs font-mono">
                    Select a prospect from the divergence queue to initialize human-in-the-loop review.
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 5: CONFIG EDITOR */}
          {activeTab === 'config' && (
            <div className="flex-1 glass-panel border border-cyan-500/10 p-6 overflow-y-auto flex flex-col">
              <h3 className="text-sm font-extrabold font-mono tracking-wider text-slate-300 uppercase mb-4 flex items-center gap-2">
                <Settings2 className="h-4.5 w-4.5 text-cyan-400" /> Configuration Matrix
              </h3>
              
              <div className="grid grid-cols-2 gap-4 flex-1 min-h-[300px]">
                <div className="flex flex-col gap-2">
                  <span className="text-xs font-mono text-slate-500">Ideal Customer Profile (ICP) Configurations:</span>
                  <pre className="p-4 bg-slate-950 border border-slate-900 rounded-xl font-mono text-xs text-slate-300 whitespace-pre-wrap overflow-y-auto h-[420px]">
                    {JSON.stringify(icpConfig, null, 2)}
                  </pre>
                </div>
                <div className="flex flex-col gap-2">
                  <span className="text-xs font-mono text-slate-500">Target Persona Parameters:</span>
                  <pre className="p-4 bg-slate-950 border border-slate-900 rounded-xl font-mono text-xs text-slate-300 whitespace-pre-wrap overflow-y-auto h-[420px]">
                    {JSON.stringify(personasConfig, null, 2)}
                  </pre>
                </div>
              </div>
            </div>
          )}

          {/* TAB 6: OBSERVABILITY & TEE GOVERNANCE */}
          {activeTab === 'observability' && (
            <div className="flex-1 flex flex-col gap-4 overflow-y-auto pr-1">
              
              {/* Token cost cards */}
              {metrics && (
                <div className="grid grid-cols-3 gap-4">
                  <div className="glass-panel p-5 border border-cyan-500/10 flex flex-col justify-between">
                    <div className="flex items-center justify-between text-slate-400">
                      <span className="text-[11px] font-bold tracking-wider uppercase font-mono">LLM Tokens Consumed</span>
                      <Coins className="h-4 w-4 text-cyan-400" />
                    </div>
                    <div className="flex justify-between items-baseline mt-4">
                      <span className="text-3xl font-black text-slate-100">{metrics.total_tokens}</span>
                      <span className="text-xs text-slate-500 font-mono">Prompt + Completion</span>
                    </div>
                  </div>
                  <div className="glass-panel p-5 border border-cyan-500/10 flex flex-col justify-between">
                    <div className="flex items-center justify-between text-slate-400">
                      <span className="text-[11px] font-bold tracking-wider uppercase font-mono">LLM API Queries</span>
                      <Activity className="h-4 w-4 text-violet-400" />
                    </div>
                    <div className="flex justify-between items-baseline mt-4">
                      <span className="text-3xl font-black text-violet-400">{metrics.total_calls}</span>
                      <span className="text-xs text-rose-400 font-mono font-bold bg-rose-500/5 px-2 rounded">
                        Failed: {metrics.failed_calls}
                      </span>
                    </div>
                  </div>
                  <div className="glass-panel p-5 border border-cyan-500/10 flex flex-col justify-between">
                    <div className="flex items-center justify-between text-slate-400">
                      <span className="text-[11px] font-bold tracking-wider uppercase font-mono">Estimated cost (USD)</span>
                      <Coins className="h-4 w-4 text-amber-500" />
                    </div>
                    <div className="flex justify-between items-baseline mt-4">
                      <span className="text-3xl font-black text-emerald-400">${metrics.total_cost_usd}</span>
                      <span className="text-xs text-emerald-400 font-mono bg-emerald-500/5 px-2 rounded">
                        Free Tier active
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* Spans Tracer & TEE */}
              <div className="grid grid-cols-12 gap-4">
                {/* Traces List */}
                <div className="col-span-4 glass-panel border border-cyan-500/10 p-5 flex flex-col h-[400px]">
                  <h4 className="text-xs font-bold font-mono tracking-wider text-slate-400 uppercase mb-3 flex items-center gap-1.5">
                    <Clock className="h-4 w-4 text-cyan-400" /> Execution Traces
                  </h4>
                  <div className="flex-1 overflow-y-auto flex flex-col gap-2">
                    {traces.length === 0 ? (
                      <div className="text-xs text-slate-600 font-mono p-2">No active traces recorded.</div>
                    ) : (
                      traces.map((t) => (
                        <div
                          key={t.trace_id}
                          onClick={() => setSelectedTraceId(t.trace_id)}
                          className={`p-3 rounded-lg border text-xs font-mono transition duration-150 cursor-pointer ${
                            selectedTraceId === t.trace_id ? 'bg-cyan-500/10 border-cyan-500/30' : 'bg-slate-950/30 border-slate-900 hover:border-slate-800'
                          }`}
                        >
                          <div className="flex justify-between font-bold text-slate-300 mb-1">
                            <span>trace_{t.trace_id.slice(0, 8)}</span>
                            <span className={t.status === 'failed' ? 'text-rose-500' : 'text-emerald-400'}>
                              {t.status}
                            </span>
                          </div>
                          <div className="text-[10px] text-slate-500 flex justify-between">
                            <span>Spans: {t.span_count}</span>
                            <span>{t.total_duration_ms}ms</span>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                {/* Waterfall view */}
                <div className="col-span-8 glass-panel border border-cyan-500/10 p-5 flex flex-col h-[400px] overflow-hidden">
                  <h4 className="text-xs font-bold font-mono tracking-wider text-slate-400 uppercase mb-4 flex items-center gap-1.5">
                    <Activity className="h-4 w-4 text-violet-400" /> trace Waterfall Timing Chart
                  </h4>
                  <div className="flex-1 overflow-y-auto flex flex-col gap-3 pr-1">
                    {selectedTraceSpans.length === 0 ? (
                      <div className="text-xs text-slate-600 font-mono py-12 text-center">Select an execution trace on the left.</div>
                    ) : (
                      selectedTraceSpans.map((span) => (
                        <div key={span.span_id} className="p-3.5 bg-slate-950/70 border border-slate-900 rounded-xl text-xs">
                          <div className="flex justify-between items-center mb-2 font-mono">
                            <span className="font-extrabold text-slate-200">{span.agent_name.toUpperCase() || span.operation}</span>
                            <span className="text-slate-500 text-[10px]">{span.duration_ms}ms</span>
                          </div>
                          
                          {/* Relative horizontal timing bar */}
                          <div className="w-full h-1.5 bg-slate-900 rounded-full overflow-hidden relative">
                            <div 
                              className={`h-full rounded-full ${
                                span.status === 'failed' ? 'bg-rose-500 shadow-[0_0_10px_#f43f5e]' :
                                span.status === 'recovered' ? 'bg-amber-400 shadow-[0_0_10px_#fbbf24]' :
                                'bg-cyan-500 shadow-[0_0_10px_#06b6d4]'
                              }`}
                              style={{ 
                                width: `${Math.max(5, Math.min(100, (span.duration_ms / 1500) * 100))}%`,
                                marginLeft: `${Math.min(90, (span.offset_ms / 3000) * 100)}%`
                              }}
                            />
                          </div>
                          <div className="flex justify-between text-[9px] text-slate-600 font-mono mt-1">
                            <span>Status: <strong className={span.status === 'failed' ? 'text-rose-500' : 'text-slate-400'}>{span.status}</strong></span>
                            <span>Offset: {span.offset_ms}ms</span>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

        </div>
      </main>
    </div>
  );
}
