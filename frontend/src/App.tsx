import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Node, Edge, Position, MarkerType } from 'reactflow';
import { motion, AnimatePresence } from 'framer-motion';

// Import Modular Components
import Sidebar from './components/Sidebar';
import DashboardView from './components/DashboardView';
import GraphView from './components/GraphView';
import LeadsView from './components/LeadsView';
import ApprovalsView from './components/ApprovalsView';
import ConfigView from './components/ConfigView';
import ObservabilityView from './components/ObservabilityView';

// API Gateways
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
  const [collapsed, setCollapsed] = useState(false);

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
      { id: 'contact_enricher', label: 'Contact Enricher', desc: 'PII & Cryptographic Encrypter' },
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
        id: `e-${nodeNames[i].id}-${nodeNames[i + 1].id}`,
        source: nodeNames[i].id,
        target: nodeNames[i + 1].id,
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
            animated: status === 'thinking' || status === 'completed',
            style: {
              ...edge.style,
              stroke: status === 'completed' ? '#10b981' : '#06b6d4',
              strokeWidth: 2
            },
            markerEnd: {
              type: MarkerType.ArrowClosed,
              color: status === 'completed' ? '#10b981' : '#06b6d4'
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

      if (leadsRes.ok) setLeads(await leadsRes.ok ? await leadsRes.json() : []);
      if (approvalsRes.ok) setApprovalQueue(await approvalsRes.json());
      if (metricsRes.ok) setMetrics(await metricsRes.json());
      if (tracesRes.ok) {
        const trs = await tracesRes.json();
        setTraces(trs);
        if (trs.length > 0 && !selectedTraceId) {
          setSelectedTraceId(trs[0].id);
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
      const res = await fetch(`${API_BASE}/traces/${selectedTraceId}/spans`);
      if (res.ok) setSelectedTraceSpans(await res.json());
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

  // WebSockets setup
  useEffect(() => {
    const ws = new WebSocket(WS_BASE);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      const evt = JSON.parse(event.data);

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
      if (evt.type === 'workflow_completed') {
        fetchData();
      }
    };

    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, [updateNodeStatus]);

  // Execute workflow
  const handleTriggerDiscovery = async () => {
    // Clear old runs (only streaming thoughts, keep agent feed)
    setStreamingThoughts({});
    initializeDAG(companyInput);
    setActiveTab('workflows');

    try {
      const res = await fetch(`${API_BASE}/workflows/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          company_name: companyInput,
          domain: domainInput
        })
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

  const handleClearThoughts = () => {
    setStreamingThoughts({});
  };

  // Toggle Chaos Monkey
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

  // Decryption Simulator
  const [decryptedPII, setDecryptedPII] = useState<Record<string, { email: string; phone: string }>>({});
  const simulateVaultAccess = (leadId: string, rawEmail: string, rawPhone: string, plainEmail: string, plainPhone: string) => {
    setDecryptedPII(prev => ({
      ...prev,
      [leadId]: {
        email: plainEmail || "priya.sharma@razorx.in",
        phone: plainPhone || "+91-9876543210"
      }
    }));
  };

  return (
    <div className="flex flex-1 overflow-hidden cyber-grid h-screen w-screen bg-[#030712] text-slate-100 font-sans">
      {/* Sidebar Navigation */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        chaosEnabled={chaosEnabled}
        toggleChaosMonkey={toggleChaosMonkey}
        approvalCount={approvalQueue.length}
        collapsed={collapsed}
        setCollapsed={setCollapsed}
      />

      {/* Main Panel Content */}
      <main className="flex-1 flex flex-col overflow-hidden p-6 relative z-10">
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -15 }}
            transition={{ duration: 0.25, ease: 'easeInOut' }}
            className="flex-grow flex flex-col overflow-hidden"
          >
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
                handleClearThoughts={handleClearThoughts}
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
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  );
}
