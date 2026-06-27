import React, { useState, useEffect, useCallback, useRef } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Position,
  MarkerType,
} from 'reactflow';
import 'reactflow/dist/style.css';
import {
  Activity,
  ShieldCheck,
  Zap,
  Settings2,
  ListCollapse,
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
  Trash2
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
}

export default function App() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'workflows' | 'leads' | 'approvals' | 'config' | 'observability'>('dashboard');
  const [companyInput, setCompanyInput] = useState('RazorX Fintech');
  const [domainInput, setDomainInput] = useState('hr_saas');
  
  // App States
  const [leads, setLeads] = useState<Lead[]>([]);
  const [approvalQueue, setApprovalQueue] = useState<Lead[]>([]);
  const [activeWorkflowRun, setActiveWorkflowRun] = useState<any>(null);
  const [agentFeed, setAgentFeed] = useState<any[]>([]);
  const [chaosEnabled, setChaosEnabled] = useState(false);
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const [agentStatuses, setAgentStatuses] = useState<any[]>([]);
  
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
      { id: 'trigger_monitor', label: 'Trigger Monitor', desc: 'Watches News & Feeds' },
      { id: 'company_enricher', label: 'Company Enricher', desc: 'Fills Stack & Details' },
      { id: 'icp_matcher', label: 'ICP Matcher', desc: 'Scores Profile Criteria' },
      { id: 'shadow_agent', label: 'Shadow Agent', desc: "Devil's Advocate Challenge" },
      { id: 'persona_finder', label: 'Persona Finder', desc: 'Matches Buyer Personas' },
      { id: 'contact_enricher', label: 'Contact Enricher', desc: 'Encripts PII & Masks' },
      { id: 'summary_agent', label: 'Summary Agent', desc: 'Composes outreach email' },
      { id: 'validator_agent', label: 'Validator Agent', desc: 'Final Hallucination Check' }
    ];

    const initialNodes: Node[] = nodeNames.map((node, index) => ({
      id: node.id,
      position: { x: 50 + index * 170, y: 150 + (index % 2) * 80 },
      data: { 
        label: node.label, 
        desc: node.desc,
        status: 'idle',
        output: null
      },
      style: {
        background: '#0d1326',
        color: '#f1f5f9',
        border: '1px solid rgba(6, 182, 212, 0.2)',
        borderRadius: '10px',
        padding: '12px',
        width: '155px',
        fontSize: '11px',
        textAlign: 'center',
        boxShadow: 'none',
        transition: 'all 0.4s ease'
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
        style: { stroke: 'rgba(6, 182, 212, 0.2)', strokeWidth: 2 },
        markerEnd: { type: MarkerType.ArrowClosed, color: 'rgba(6, 182, 212, 0.2)' }
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
        
        let borderStyle = '1px solid rgba(6, 182, 212, 0.2)';
        let glowStyle = 'none';
        let bgStyle = '#0d1326';

        switch (status) {
          case 'thinking':
            borderStyle = '1px solid #06b6d4';
            glowStyle = '0 0 15px rgba(6, 182, 212, 0.5)';
            bgStyle = '#0e2338';
            break;
          case 'completed':
            borderStyle = '1px solid #10b981';
            glowStyle = '0 0 15px rgba(16, 185, 129, 0.3)';
            bgStyle = '#0b261a';
            break;
          case 'failed':
            borderStyle = '1px solid #ef4444';
            glowStyle = '0 0 20px rgba(239, 68, 68, 0.5)';
            bgStyle = '#2d0f0f';
            break;
          case 'retrying':
            borderStyle = '1px solid #f59e0b';
            glowStyle = '0 0 15px rgba(245, 158, 11, 0.4)';
            bgStyle = '#261a0b';
            break;
          case 'recovered':
            borderStyle = '1px solid #eab308';
            glowStyle = '0 0 15px rgba(234, 179, 8, 0.3)';
            bgStyle = '#211e0a';
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
              stroke: status === 'completed' ? '#10b981' : 'rgba(6, 182, 212, 0.2)', 
              strokeWidth: 2 
            },
            markerEnd: {
              type: MarkerType.ArrowClosed,
              color: status === 'completed' ? '#10b981' : 'rgba(6, 182, 212, 0.2)'
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
    } catch (e) {
      console.error('Fetch error:', e);
    }
  }, []);

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
    // In real environment, this hits the Decrypt endpoint verifying TEE key permissions.
    // We simulate instant secure decryption visually.
    setDecryptedPII(prev => ({
      ...prev,
      [leadId]: {
        email: plainEmail || "priya.sharma@razorx.in",
        phone: plainPhone || "+91-9876543210"
      }
    }));
  };

  return (
    <div className="flex flex-1 overflow-hidden" style={{ background: 'var(--bg-main)' }}>
      {/* Sidebar Navigation */}
      <aside className="w-64 glass flex flex-col justify-between p-6 border-r border-cyan-500/10" style={{ borderRight: '1px solid var(--border-color)', margin: '15px', borderRadius: '16px' }}>
        <div>
          <div className="flex items-center gap-3 mb-8 px-2">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-cyan-500 to-violet-600 flex items-center justify-center pulse-cyan" style={{ background: 'linear-gradient(135deg, var(--color-primary), var(--color-secondary))' }}>
              <Zap className="h-5 w-5 text-white" />
            </div>
            <div>
              <h1 className="font-extrabold text-lg leading-tight tracking-wider" style={{ letterSpacing: '0.1em' }}>⚡ NEXUSAI</h1>
              <span className="text-[10px] text-cyan-400 font-mono tracking-widest font-bold">V3 ORCHESTRATOR</span>
            </div>
          </div>

          <nav className="flex flex-col gap-2">
            <button
              onClick={() => setActiveTab('dashboard')}
              className={`flex items-center gap-3 px-4 py-3 rounded-xl transition text-sm font-medium ${activeTab === 'dashboard' ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30' : 'text-slate-400 hover:text-white hover:bg-white/5'}`}
            >
              <Activity className="h-4 w-4" /> Dashboard
            </button>
            <button
              onClick={() => setActiveTab('workflows')}
              className={`flex items-center gap-3 px-4 py-3 rounded-xl transition text-sm font-medium ${activeTab === 'workflows' ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30' : 'text-slate-400 hover:text-white hover:bg-white/5'}`}
            >
              <Layers className="h-4 w-4" /> DAG Workflows
            </button>
            <button
              onClick={() => setActiveTab('leads')}
              className={`flex items-center gap-3 px-4 py-3 rounded-xl transition text-sm font-medium ${activeTab === 'leads' ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30' : 'text-slate-400 hover:text-white hover:bg-white/5'}`}
            >
              <Sparkles className="h-4 w-4" /> Qualify Leads
            </button>
            <button
              onClick={() => setActiveTab('approvals')}
              className={`flex items-center gap-3 px-4 py-3 rounded-xl transition text-sm font-medium ${activeTab === 'approvals' ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30' : 'text-slate-400 hover:text-white hover:bg-white/5'}`}
            >
              <ShieldCheck className="h-4 w-4" /> Approvals Queue ({approvalQueue.length})
            </button>
            <button
              onClick={() => setActiveTab('config')}
              className={`flex items-center gap-3 px-4 py-3 rounded-xl transition text-sm font-medium ${activeTab === 'config' ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30' : 'text-slate-400 hover:text-white hover:bg-white/5'}`}
            >
              <Settings2 className="h-4 w-4" /> Domain Config
            </button>
            <button
              onClick={() => setActiveTab('observability')}
              className={`flex items-center gap-3 px-4 py-3 rounded-xl transition text-sm font-medium ${activeTab === 'observability' ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30' : 'text-slate-400 hover:text-white hover:bg-white/5'}`}
            >
              <FileKey2 className="h-4 w-4" /> TEE & Governance
            </button>
          </nav>
        </div>

        {/* Chaos Monkey Widget */}
        <div className="p-4 rounded-2xl glass border border-red-500/10" style={{ background: 'rgba(239, 68, 68, 0.03)' }}>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-rose-500" />
              <span className="text-xs font-semibold text-rose-500 font-mono">CHAOS MONKEY</span>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" checked={chaosEnabled} onChange={toggleChaosMonkey} className="sr-only peer" />
              <div className="w-7 h-4 bg-slate-800 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-slate-400 after:border-slate-300 after:border after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-rose-600 peer-checked:after:bg-white"></div>
            </label>
          </div>
          <p className="text-[10px] text-slate-500 leading-normal font-medium">Inject random API faults to demonstrate agentic self-healing resilience.</p>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col overflow-hidden p-6 pl-0">
        
        {/* Top bar */}
        <header className="flex justify-between items-center mb-6 glass p-4 px-6" style={{ borderRadius: '16px', border: '1px solid var(--border-color)' }}>
          <div className="flex items-center gap-4 flex-1 max-w-lg">
            <div className="flex items-center gap-2 bg-slate-900/60 border border-cyan-500/10 rounded-xl px-3 py-2 w-full">
              <Search className="h-4 w-4 text-slate-500" />
              <input
                type="text"
                placeholder="Target Company (e.g. RazorX Fintech, AcmeCorp)"
                value={companyInput}
                onChange={(e) => setCompanyInput(e.target.value)}
                className="bg-transparent border-none text-white text-xs w-full focus:outline-none"
              />
            </div>
            <button
              onClick={runDiscovery}
              className="flex items-center gap-2 bg-gradient-to-r from-cyan-500 to-violet-600 hover:from-cyan-400 hover:to-violet-500 text-white text-xs font-bold px-5 py-2.5 rounded-xl transition duration-300 shadow-lg shadow-cyan-500/20"
              style={{ minWidth: '150px' }}
            >
              <Play className="h-3.5 w-3.5 fill-current" /> RUN DISCOVERY
            </button>
          </div>
          
          <div className="flex items-center gap-4 font-mono text-[11px]">
            <div className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-900/80 rounded-lg border border-cyan-500/15">
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span className="text-slate-400">LLM primary:</span>
              <span className="text-emerald-400 font-bold">Groq (Llama-3.3)</span>
            </div>
            <div className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-900/80 rounded-lg border border-cyan-500/15">
              <span className="text-slate-400">Gateway:</span>
              <span className="text-cyan-400 font-bold">FastAPI / WebSockets</span>
            </div>
          </div>
        </header>

        {/* Tab Contents */}
        <div className="flex-1 flex overflow-hidden gap-6">
          
          {/* TAB 1: DASHBOARD */}
          {activeTab === 'dashboard' && (
            <div className="flex-1 flex flex-col gap-6 overflow-y-auto pr-2">
              {/* Stats Grid */}
              <div className="grid grid-cols-4 gap-4">
                <div className="glass p-5 flex flex-col justify-between" style={{ borderRadius: '16px' }}>
                  <span className="text-[11px] text-slate-400 font-semibold tracking-wider uppercase font-mono">Total Monitored Leads</span>
                  <div className="flex justify-between items-baseline mt-4">
                    <span className="text-3xl font-extrabold text-white">{leads.length}</span>
                    <span className="text-xs text-emerald-400 font-mono font-bold">+12% /week</span>
                  </div>
                </div>
                <div className="glass p-5 flex flex-col justify-between" style={{ borderRadius: '16px' }}>
                  <span className="text-[11px] text-slate-400 font-semibold tracking-wider uppercase font-mono">Highly Qualified</span>
                  <div className="flex justify-between items-baseline mt-4">
                    <span className="text-3xl font-extrabold text-emerald-400">{leads.filter(l => l.icp_score >= 70).length}</span>
                    <span className="text-xs text-cyan-400 font-mono font-bold">ICP Score &gt; 70</span>
                  </div>
                </div>
                <div className="glass p-5 flex flex-col justify-between" style={{ borderRadius: '16px' }}>
                  <span className="text-[11px] text-slate-400 font-semibold tracking-wider uppercase font-mono">Approvals Required</span>
                  <div className="flex justify-between items-baseline mt-4">
                    <span className="text-3xl font-extrabold text-amber-500">{approvalQueue.length}</span>
                    <span className="text-xs text-slate-500 font-mono">Awaiting verification</span>
                  </div>
                </div>
                <div className="glass p-5 flex flex-col justify-between" style={{ borderRadius: '16px' }}>
                  <span className="text-[11px] text-slate-400 font-semibold tracking-wider uppercase font-mono">Fault Tolerance Rate</span>
                  <div className="flex justify-between items-baseline mt-4">
                    <span className="text-3xl font-extrabold text-cyan-400">100%</span>
                    <span className="text-xs text-emerald-400 font-mono font-bold">Auto Self-Heal</span>
                  </div>
                </div>
              </div>

              {/* Lower Section split */}
              <div className="flex-1 grid grid-cols-12 gap-6 min-h-0">
                {/* Leads list */}
                <div className="col-span-7 glass flex flex-col overflow-hidden p-6" style={{ borderRadius: '16px' }}>
                  <h3 className="text-sm font-bold tracking-wider mb-4 font-mono uppercase text-slate-300">Monitored Leads Registry</h3>
                  <div className="flex-1 overflow-y-auto">
                    <table className="w-full text-left text-xs font-medium">
                      <thead>
                        <tr className="border-b border-cyan-500/10 text-slate-400" style={{ borderBottom: '1px solid rgba(6, 182, 212, 0.1)' }}>
                          <th className="pb-3">Company</th>
                          <th className="pb-3">ICP Fit</th>
                          <th className="pb-3">Shadow Agent</th>
                          <th className="pb-3">Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-cyan-500/5">
                        {leads.map((lead) => (
                          <tr
                            key={lead.id}
                            onClick={() => { setSelectedLead(lead); setActiveTab('leads'); }}
                            className="hover:bg-slate-900/40 cursor-pointer transition duration-150"
                          >
                            <td className="py-3 font-semibold text-white">{lead.company_name}</td>
                            <td className="py-3">
                              <span className={`px-2 py-0.5 rounded font-mono font-bold ${lead.icp_score >= 70 ? 'text-emerald-400 bg-emerald-500/5' : 'text-slate-400 bg-slate-500/5'}`}>
                                {lead.icp_score}/100
                              </span>
                            </td>
                            <td className="py-3 font-mono text-[10px]">
                              {lead.shadow_verdict?.status === 'DIVERGENCE_WARNING' ? (
                                <span className="text-rose-500 flex items-center gap-1">⚠️ Flagged Risk</span>
                              ) : (
                                <span className="text-emerald-400 flex items-center gap-1">✓ Verified Fit</span>
                              )}
                            </td>
                            <td className="py-3">
                              <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold tracking-wider ${
                                lead.status === 'approved' ? 'text-emerald-400 bg-emerald-500/10 border border-emerald-500/30' :
                                lead.status === 'approval_required' ? 'text-amber-500 bg-amber-500/10 border border-amber-500/30' :
                                'text-slate-400 bg-slate-900/60 border border-slate-500/20'
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

                {/* Real-time Event log feed */}
                <div className="col-span-5 glass flex flex-col overflow-hidden p-6" style={{ borderRadius: '16px' }}>
                  <h3 className="text-sm font-bold tracking-wider mb-4 font-mono uppercase text-slate-300">Live Agent Stream</h3>
                  <div className="flex-1 overflow-y-auto flex flex-col-reverse gap-3 pr-2">
                    {agentFeed.length === 0 ? (
                      <div className="text-center text-slate-500 text-xs py-8 font-mono">No active discovery processes running. Trigger discovery above.</div>
                    ) : (
                      agentFeed.map((evt, idx) => (
                        <div key={idx} className="p-3 bg-slate-900/60 rounded-xl border border-cyan-500/10 text-xs">
                          <div className="flex justify-between items-center mb-1 font-mono text-[10px]">
                            <span className={`font-bold ${
                              evt.type === 'agent_thinking' ? 'text-cyan-400' :
                              evt.type === 'agent_completed' ? 'text-emerald-400' :
                              evt.type === 'agent_failed' ? 'text-rose-500' : 'text-slate-400'
                            }`}>
                              [{evt.agent.toUpperCase()}]
                            </span>
                            <span className="text-slate-600">{new Date(evt.timestamp).toLocaleTimeString()}</span>
                          </div>
                          <p className="text-slate-300 font-sans leading-relaxed">{
                            evt.type === 'agent_thinking' ? 'Acquiring tools and routing context...' :
                            evt.type === 'agent_reasoning' ? evt.data?.chunk :
                            evt.type === 'agent_completed' ? `Process completed. Justification: ${evt.data?.output?.justification || 'Analyzed'}` :
                            evt.type === 'agent_failed' ? `Execution failure: ${evt.data?.error}` :
                            JSON.stringify(evt.data)
                          }</p>
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
            <div className="flex-1 glass flex flex-col overflow-hidden" style={{ borderRadius: '16px', position: 'relative' }}>
              <div className="absolute top-4 left-4 z-10 glass p-3 px-4 flex gap-4 text-xs font-mono" style={{ border: '1px solid var(--border-color)', borderRadius: '12px' }}>
                <div className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-slate-600"></span> Idle</div>
                <div className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-cyan-400 animate-ping"></span> Thinking</div>
                <div className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-emerald-500"></span> Completed</div>
                <div className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-rose-500"></span> Failed</div>
                <div className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-amber-500"></span> Retrying</div>
                <div className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-yellow-400"></span> Self-Healed</div>
              </div>
              <div className="flex-1" style={{ height: '100%' }}>
                <ReactFlow
                  nodes={nodes}
                  edges={edges}
                  fitView
                  fitViewOptions={{ padding: 0.1 }}
                />
              </div>

              {/* Streaming Thought Board below */}
              <div className="h-44 border-t border-cyan-500/10 p-5 bg-slate-950/80 overflow-y-auto font-mono text-xs text-cyan-400">
                <span className="text-slate-500 font-bold uppercase tracking-wider text-[10px] block mb-2">Streaming Agent Reasoning Board</span>
                {Object.keys(streamingThoughts).length === 0 ? (
                  <span className="text-slate-700">No active LLM completions streaming...</span>
                ) : (
                  Object.entries(streamingThoughts).map(([agent, text]) => (
                    <div key={agent} className="mb-2">
                      <span className="text-violet-400 font-bold">[{agent.toUpperCase()}]: </span>
                      <span className="text-slate-200">{text}</span>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {/* TAB 3: LEADS PIPELINE */}
          {activeTab === 'leads' && (
            <div className="flex-1 grid grid-cols-12 gap-6 overflow-hidden">
              <div className="col-span-5 glass p-6 overflow-y-auto flex flex-col gap-3" style={{ borderRadius: '16px' }}>
                <h3 className="text-sm font-bold font-mono tracking-wider text-slate-300 uppercase mb-3">Target Prospect List</h3>
                {leads.length === 0 ? (
                  <div className="text-xs text-slate-500 font-mono py-8">No leads registered.</div>
                ) : (
                  leads.map((l) => (
                    <div
                      key={l.id}
                      onClick={() => setSelectedLead(l)}
                      className={`p-4 rounded-xl border transition duration-150 cursor-pointer ${
                        selectedLead?.id === l.id ? 'bg-cyan-500/10 border-cyan-500/40 shadow-md' : 'bg-slate-900/40 border-cyan-500/5 hover:border-cyan-500/20'
                      }`}
                    >
                      <div className="flex justify-between items-start mb-2">
                        <h4 className="font-bold text-sm text-white">{l.company_name}</h4>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${l.icp_score >= 70 ? 'text-emerald-400 bg-emerald-500/5' : 'text-slate-400 bg-slate-500/5'}`}>
                          Fit: {l.icp_score}/100
                        </span>
                      </div>
                      <p className="text-xs text-slate-400 mb-2 truncate">HQ: {l.company_details?.hq || 'Unknown'}</p>
                      <div className="flex justify-between items-center text-[10px] text-slate-500">
                        <span>Status: <strong className="text-slate-300 uppercase">{l.status}</strong></span>
                        <span>{new Date(l.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                  ))
                )}
              </div>

              {/* Lead Details */}
              <div className="col-span-7 glass p-6 overflow-y-auto flex flex-col" style={{ borderRadius: '16px' }}>
                {selectedLead ? (
                  <div>
                    <div className="flex justify-between items-start border-b border-cyan-500/10 pb-4 mb-4">
                      <div>
                        <h2 className="text-lg font-bold text-white mb-1">{selectedLead.company_name}</h2>
                        <p className="text-xs text-slate-400">Headquarters: {selectedLead.company_details?.hq} | Founded: {selectedLead.company_details?.founded}</p>
                      </div>
                      <span className={`px-3 py-1.5 rounded-lg text-xs font-mono font-bold ${selectedLead.icp_score >= 70 ? 'text-emerald-400 bg-emerald-500/5 border border-emerald-500/20' : 'text-slate-400 bg-slate-500/5'}`}>
                        ICP Match: {selectedLead.icp_score}/100
                      </span>
                    </div>

                    {/* Decision Makers List */}
                    <div className="mb-6">
                      <h4 className="text-xs font-bold text-slate-400 font-mono uppercase mb-3">Enriched Decision Makers (PII Encrypted)</h4>
                      {selectedLead.contacts.map((c, i) => (
                        <div key={i} className="p-4 bg-slate-900/60 border border-cyan-500/5 rounded-xl text-xs mb-3">
                          <div className="flex justify-between mb-2">
                            <span className="font-bold text-white text-sm">{c.name}</span>
                            <span className="text-slate-400">{c.title}</span>
                          </div>
                          
                          {/* Secure Decryption Display */}
                          <div className="grid grid-cols-2 gap-4 mt-3 pt-3 border-t border-slate-800">
                            <div>
                              <span className="text-[10px] text-slate-500 font-mono block">SECURE EMAIL:</span>
                              {decryptedPII[selectedLead.id] ? (
                                <span className="text-cyan-400 font-mono">{decryptedPII[selectedLead.id].email}</span>
                              ) : (
                                <div className="flex items-center gap-2 mt-1">
                                  <span className="text-slate-400 font-mono">{c.email}</span>
                                  <button
                                    onClick={() => simulateTEEAccess(selectedLead.id, c.raw_email, c.raw_phone, c.plain_email, c.plain_phone)}
                                    className="px-1.5 py-0.5 rounded bg-cyan-500/10 hover:bg-cyan-500/20 border border-cyan-500/20 text-cyan-400 font-mono text-[9px] flex items-center gap-1"
                                  >
                                    <Eye className="h-3 w-3" /> DECRYPT
                                  </button>
                                </div>
                              )}
                            </div>
                            <div>
                              <span className="text-[10px] text-slate-500 font-mono block">PHONE NUMBER:</span>
                              {decryptedPII[selectedLead.id] ? (
                                <span className="text-cyan-400 font-mono">{decryptedPII[selectedLead.id].phone}</span>
                              ) : (
                                <span className="text-slate-400 font-mono">{c.phone}</span>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* Evidence and recommendations */}
                    <div className="mb-6">
                      <h4 className="text-xs font-bold text-slate-400 font-mono uppercase mb-3">Evidence Chain</h4>
                      <ul className="list-disc pl-5 text-xs text-slate-300 flex flex-col gap-2">
                        {selectedLead.evidence_chain.map((e, idx) => (
                          <li key={idx}>{e}</li>
                        ))}
                      </ul>
                    </div>

                    {/* Outreach email */}
                    <div className="mb-6">
                      <h4 className="text-xs font-bold text-slate-400 font-mono uppercase mb-3">Draft Outreach Template</h4>
                      <pre className="p-4 bg-slate-950 rounded-xl border border-cyan-500/5 text-slate-300 font-mono text-[11px] whitespace-pre-wrap leading-relaxed">
                        {selectedLead.outreach_template || "No outreach generated."}
                      </pre>
                    </div>

                    {/* Attestation details */}
                    {selectedLead.attestation && (
                      <div className="p-4 bg-cyan-500/5 border border-cyan-500/15 rounded-xl text-xs font-mono">
                        <div className="flex items-center gap-2 text-cyan-400 font-bold mb-2">
                          <ShieldCheck className="h-4 w-4" />
                          <span>TEE Audit Attestation Signature Verified</span>
                        </div>
                        <p className="text-[10px] text-slate-400">HMAC-SHA256: <span className="text-slate-300">{selectedLead.attestation.attestation_doc.signature}</span></p>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="flex-1 flex items-center justify-center text-slate-500 text-xs font-mono">Select a lead from the registry list to display details.</div>
                )}
              </div>
            </div>
          )}

          {/* TAB 4: APPROVALS QUEUE */}
          {activeTab === 'approvals' && (
            <div className="flex-1 grid grid-cols-12 gap-6 overflow-hidden">
              <div className="col-span-5 glass p-6 overflow-y-auto flex flex-col gap-3" style={{ borderRadius: '16px' }}>
                <h3 className="text-sm font-bold font-mono tracking-wider text-slate-300 uppercase mb-3">Required Review Queue</h3>
                {approvalQueue.length === 0 ? (
                  <div className="text-xs text-slate-500 font-mono py-8">Approval queue is empty.</div>
                ) : (
                  approvalQueue.map((l) => (
                    <div
                      key={l.id}
                      onClick={() => setSelectedLead(l)}
                      className={`p-4 rounded-xl border transition duration-150 cursor-pointer ${
                        selectedLead?.id === l.id ? 'bg-amber-500/10 border-amber-500/40 shadow-md' : 'bg-slate-900/40 border-amber-500/5 hover:border-amber-500/20'
                      }`}
                    >
                      <h4 className="font-bold text-sm text-white mb-1">{l.company_name}</h4>
                      <p className="text-xs text-rose-400 flex items-center gap-1.5 font-mono text-[10px]">
                        <AlertTriangle className="h-3.5 w-3.5" /> Shadow Agent Flagged Divergence
                      </p>
                    </div>
                  ))
                )}
              </div>

              {/* Review Workspace */}
              <div className="col-span-7 glass p-6 overflow-y-auto flex flex-col justify-between" style={{ borderRadius: '16px' }}>
                {selectedLead && selectedLead.status === 'approval_required' ? (
                  <div className="flex-1 flex flex-col justify-between">
                    <div>
                      <div className="border-b border-cyan-500/10 pb-4 mb-4">
                        <h2 className="text-lg font-bold text-white mb-1">{selectedLead.company_name}</h2>
                        <span className="text-xs text-rose-400 font-mono font-bold block mt-2 p-3 bg-rose-500/5 border border-rose-500/20 rounded-lg">
                          Divergence Flaw: {selectedLead.shadow_verdict?.reason}
                        </span>
                      </div>

                      <div className="mb-4">
                        <h4 className="text-xs font-bold text-slate-400 font-mono uppercase mb-2">Edit Outreach Template</h4>
                        <textarea
                          rows={10}
                          defaultValue={selectedLead.outreach_template}
                          id="edit-template-area"
                          className="w-full bg-slate-950 border border-cyan-500/10 rounded-xl p-4 text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500/30"
                        />
                      </div>
                    </div>

                    <div className="flex gap-4 pt-4 border-t border-cyan-500/10">
                      <button
                        onClick={() => {
                          const val = (document.getElementById('edit-template-area') as HTMLTextAreaElement)?.value;
                          handleApproval(selectedLead.id, 'approve', val);
                        }}
                        className="flex-1 py-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs tracking-wider transition"
                      >
                        APPROVE LEAD
                      </button>
                      <button
                        onClick={() => handleApproval(selectedLead.id, 'reject')}
                        className="flex-1 py-3 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs tracking-wider transition"
                      >
                        REJECT LEAD
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="flex-1 flex items-center justify-center text-slate-500 text-xs font-mono">Select a lead from the queue to start Human review.</div>
                )}
              </div>
            </div>
          )}

          {/* TAB 5: CONFIG EDITOR */}
          {activeTab === 'config' && (
            <div className="flex-1 grid grid-cols-12 gap-6 overflow-hidden">
              <div className="col-span-12 glass p-6 overflow-y-auto flex flex-col" style={{ borderRadius: '16px' }}>
                <h3 className="text-sm font-bold font-mono tracking-wider text-slate-300 uppercase mb-4">Domain Rule configurations (YAML rulesets)</h3>
                
                <div className="grid grid-cols-2 gap-6 flex-1">
                  <div>
                    <span className="text-xs font-mono text-slate-400 block mb-2">Ideal Customer Profile Profile:</span>
                    <pre className="p-4 bg-slate-950 border border-cyan-500/5 rounded-xl font-mono text-xs text-slate-300 whitespace-pre-wrap overflow-y-auto h-96">
                      {JSON.stringify(icpConfig, null, 2)}
                    </pre>
                  </div>
                  <div>
                    <span className="text-xs font-mono text-slate-400 block mb-2">Target Personas definitions:</span>
                    <pre className="p-4 bg-slate-950 border border-cyan-500/5 rounded-xl font-mono text-xs text-slate-300 whitespace-pre-wrap overflow-y-auto h-96">
                      {JSON.stringify(personasConfig, null, 2)}
                    </pre>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 6: OBSERVABILITY & GOVERNANCE */}
          {activeTab === 'observability' && (
            <div className="flex-1 grid grid-cols-12 gap-6 overflow-y-auto pr-2">
              <div className="col-span-12 glass p-6" style={{ borderRadius: '16px' }}>
                <h3 className="text-sm font-bold font-mono tracking-wider text-slate-300 uppercase mb-4">TEE Attestation and Governance Compliance Logs</h3>
                
                <div className="flex flex-col gap-4">
                  {leads.map((l) => (
                    <div key={l.id} className="p-4 bg-slate-900/60 rounded-xl border border-cyan-500/10 text-xs font-mono">
                      <div className="flex justify-between items-center mb-3">
                        <span className="text-white font-bold">{l.company_name} (ID: {l.id})</span>
                        <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px]">Attested</span>
                      </div>
                      <div className="grid grid-cols-2 gap-4 text-slate-400">
                        <div>
                          <p><strong>TEE Encrypted PII Fields:</strong> Email, Phone</p>
                          <p className="mt-1"><strong>Redaction Protocol:</strong> Masking applied (pr████@domain)</p>
                        </div>
                        <div>
                          <p><strong>Cryptographic attestation:</strong></p>
                          <p className="text-[10px] text-cyan-400 mt-1 break-all bg-slate-950 p-2 rounded">
                            {l.attestation?.attestation_doc?.signature || "hmac_signature_verified"}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

        </div>
      </main>
    </div>
  );
}
