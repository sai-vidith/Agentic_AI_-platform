import React, { useState } from 'react';
import { Play, Sparkles, Send, Globe, Radio } from 'lucide-react';

interface SimulatorViewProps {
  onFireSignal: (payload: { source: string; event_type: string; company: string; data: any }) => void;
  showNotification: (message: string, type: 'success' | 'warning' | 'info') => void;
}

export default function SimulatorView({ onFireSignal, showNotification }: SimulatorViewProps) {
  const [company, setCompany] = useState('');
  const [eventType, setEventType] = useState('funding');
  const [amount, setAmount] = useState('15M');
  const [logs, setLogs] = useState<string[]>([]);

  const presets = [
    { company: 'RazorX Fintech', type: 'funding', data: { amount: '15M', round: 'Series A', location: 'Bangalore' }, label: 'RazorX Fintech — Series A $15M Funding' },
    { company: 'FinCorp Solutions', type: 'hiring', data: { title: 'VP People Operations', dept: 'HR', salary: '120k' }, label: 'FinCorp — VP People hire detected' },
    { company: 'TechStart Inc', type: 'leadership_change', data: { prev: 'Outsource HR', current: 'In-house strategy', headcount_surge: '40%' }, label: 'TechStart — Headcount surge +40%' },
    { company: 'AcmeCorp Systems', type: 'funding', data: { amount: '1M', round: 'Seed', employees: 8 }, label: 'AcmeCorp — Low ICP match (pruning demo)' }
  ];

  const handleFirePreset = (preset: typeof presets[0]) => {
    const payload = {
      source: 'crunchbase',
      event_type: preset.type,
      company: preset.company,
      data: preset.data
    };
    sendPayload(payload);
  };

  const handleCustomFire = (e: React.FormEvent) => {
    e.preventDefault();
    if (!company) {
      showNotification('Company name is required', 'warning');
      return;
    }
    const payload = {
      source: 'custom',
      event_type: eventType,
      company: company,
      data: { amount: `${amount}` }
    };
    sendPayload(payload);
  };

  const sendPayload = async (payload: any) => {
    const time = new Date().toLocaleTimeString();
    setLogs(prev => [...prev, `[${time}] Sending Webhook payload to /v2/webhooks/${payload.source}...`]);
    
    try {
      const response = await fetch(`http://localhost:8000/v2/webhooks/${payload.source}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (response.ok) {
        setLogs(prev => [...prev, `[${time}] Success: Signal accepted by gateway (202 Accepted)`]);
        showNotification(`Autonomous trigger — ${payload.company} discovery started via webhook`, 'success');
        onFireSignal(payload);
      } else {
        setLogs(prev => [...prev, `[${time}] Error: Gateway returned status code ${response.status}`]);
      }
    } catch (e) {
      setLogs(prev => [...prev, `[${time}] Connection Failed: Backend server is not running`]);
    }
  };

  return (
    <div className="flex-1 flex flex-col gap-6 overflow-y-auto">
      <div className="flex justify-between items-center border-b border-strong pb-4">
        <div>
          <h1 className="font-display font-bold text-lg tracking-tight text-primary">MARKET SIGNAL SIMULATOR</h1>
          <p className="text-[11px] text-muted font-sans mt-0.5">Send simulated webhook events to test real-time agentic execution workflows.</p>
        </div>
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-accent-dim border border-accent/20 text-accent font-mono text-[10px]">
          <Radio className="w-3 h-3 animate-pulse" />
          <span>LISTENING TO PORT 8000</span>
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-6 items-start">
        {/* Left settings */}
        <div className="space-y-6">
          <div className="border border-strong rounded bg-surface p-4 space-y-4">
            <h2 className="font-display font-semibold text-xs tracking-wider uppercase text-secondary">PRESET EVENTS</h2>
            <div className="flex flex-col gap-2">
              {presets.map((preset, i) => (
                <button
                  key={i}
                  onClick={() => handleFirePreset(preset)}
                  className="w-full text-left px-3 py-2 bg-base border border-strong rounded text-[11px] font-mono text-secondary hover:text-accent hover:border-accent transition flex justify-between items-center"
                >
                  <span>{preset.label}</span>
                  <Play className="w-3 h-3 text-accent shrink-0" />
                </button>
              ))}
            </div>
          </div>

          <form onSubmit={handleCustomFire} className="border border-strong rounded bg-surface p-4 space-y-4">
            <h2 className="font-display font-semibold text-xs tracking-wider uppercase text-secondary">CUSTOM WEBHOOK PAYLOAD</h2>
            
            <div className="space-y-3 font-mono text-[11px]">
              <div className="space-y-1">
                <label className="text-muted">Target Company Name:</label>
                <input
                  type="text"
                  placeholder="e.g. Stripe, Airbnb"
                  value={company}
                  onChange={(e) => setCompany(e.target.value)}
                  className="w-full px-3 py-2 bg-base border border-strong rounded text-primary placeholder:text-muted outline-none focus:border-accent"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-muted">Event Type:</label>
                  <select
                    value={eventType}
                    onChange={(e) => setEventType(e.target.value)}
                    className="w-full px-3 py-2 bg-base border border-strong rounded text-primary outline-none focus:border-accent"
                  >
                    <option value="funding">Funding</option>
                    <option value="hiring">Hiring</option>
                    <option value="leadership_change">Leadership Change</option>
                  </select>
                </div>
                <div className="space-y-1">
                  <label className="text-muted">Metrics (Size/Amount):</label>
                  <input
                    type="text"
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                    className="w-full px-3 py-2 bg-base border border-strong rounded text-primary outline-none focus:border-accent"
                  />
                </div>
              </div>
            </div>

            <button
              type="submit"
              className="w-full py-2.5 bg-accent text-base rounded text-xs font-display font-semibold uppercase tracking-wider hover:bg-accent/90 transition flex justify-center items-center gap-1.5 shadow-[0_0_15px_rgba(200,247,58,0.15)]"
            >
              <Send className="w-3.5 h-3.5" /> Fire Webhook Signal
            </button>
          </form>
        </div>

        {/* Right logs */}
        <div className="border border-strong rounded bg-surface p-4 flex flex-col h-[400px]">
          <h2 className="font-display font-semibold text-xs tracking-wider uppercase text-secondary mb-3">SIMULATION FEED LOGS</h2>
          <div className="flex-1 overflow-y-auto bg-base border border-strong p-3.5 rounded font-mono text-[11px] text-muted space-y-2 leading-relaxed select-all">
            {logs.length === 0 ? (
              <div className="text-center py-20">Ready to simulate. Fire a webhook signal above...</div>
            ) : (
              logs.map((log, i) => (
                <div key={i} className={log.includes('Success') ? 'text-success' : log.includes('Error') || log.includes('Failed') ? 'text-danger' : 'text-secondary'}>
                  &gt; {log}
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
