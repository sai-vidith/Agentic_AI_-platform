import React, { useState, useEffect } from 'react';
import { Settings, FileText, CheckCircle, Eye, Folder, Plus, Save } from 'lucide-react';

interface ConfigViewProps {
  icpConfig: any;
  personasConfig: any;
  domainInput: string;
  setDomainInput: (val: string) => void;
  domainsList: string[];
  fetchDomains: () => void;
}

const API_BASE = 'http://localhost:8000/v2';

export default function ConfigView({
  icpConfig,
  personasConfig,
  domainInput,
  setDomainInput,
  domainsList = ['hr_saas', 'cybersecurity'],
  fetchDomains
}: ConfigViewProps) {
  const [activeFile, setActiveFile] = useState('icp_profiles/icp.yaml');
  const [yamlContent, setYamlContent] = useState('');
  const [newDomainName, setNewDomainName] = useState('');
  const [previewOpen, setPreviewOpen] = useState(false);

  // Fetch config file content based on selection
  const fetchFileContent = async (file: string, domain: string) => {
    try {
      if (file.includes('mock.json')) {
        const res = await fetch(`${API_BASE}/config/${domain}/mock-data`);
        if (res.ok) {
          const data = await res.json();
          setYamlContent(JSON.stringify(data, null, 2));
        }
      } else {
        const res = await fetch(`${API_BASE}/config/${domain}`);
        if (res.ok) {
          const data = await res.json();
          if (file.includes('icp')) {
            setYamlContent(data.icp ? JSON.stringify(data.icp, null, 2) : '{}');
          } else if (file.includes('personas')) {
            setYamlContent(data.personas ? JSON.stringify(data.personas, null, 2) : '{}');
          } else if (file.includes('triggers')) {
            setYamlContent(data.triggers ? JSON.stringify(data.triggers, null, 2) : '{}');
          } else {
            setYamlContent(data.guardrails ? JSON.stringify(data.guardrails, null, 2) : '{}');
          }
        }
      }
    } catch (e) {
      console.error("Error fetching file content:", e);
    }
  };

  useEffect(() => {
    fetchFileContent(activeFile, domainInput);
  }, [activeFile, domainInput]);

  const handleCreateDomain = async () => {
    const cleanName = newDomainName.trim().toLowerCase().replace(/\s+/g, '_');
    if (!cleanName) {
      alert("Please enter a valid domain name");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/config/domains/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ domain: cleanName })
      });
      if (res.ok) {
        alert(`Domain '${cleanName}' created successfully! Default configuration templates and mock companies are generated.`);
        setNewDomainName('');
        fetchDomains();
        setDomainInput(cleanName);
        setActiveFile('icp_profiles/icp.yaml');
      } else {
        const err = await res.json();
        alert(`Error: ${err.detail || 'Could not create domain'}`);
      }
    } catch (e) {
      console.error(e);
      alert("Failed to connect to backend api");
    }
  };

  const handleSave = async () => {
    try {
      let parsed;
      try {
        parsed = JSON.parse(yamlContent);
      } catch (je) {
        alert("Error: Invalid JSON syntax. Please check formatting in the editor (configurations must be valid JSON objects, mock datasets must be valid JSON arrays).");
        return;
      }

      if (activeFile.includes('mock.json')) {
        if (!Array.isArray(parsed)) {
          alert("Error: Mock dataset must be a JSON Array [] containing company profiles");
          return;
        }

        const res = await fetch(`${API_BASE}/config/${domainInput}/mock-data`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(parsed)
        });
        if (res.ok) {
          alert("Mock JSON dataset saved successfully!");
        } else {
          alert("Failed to save mock dataset");
        }
      } else {
        let configType = 'icp';
        if (activeFile.includes('personas')) configType = 'personas';
        else if (activeFile.includes('triggers')) configType = 'triggers';
        else if (activeFile.includes('safety')) configType = 'safety';

        const res = await fetch(`${API_BASE}/config/${domainInput}/${configType}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(parsed)
        });
        if (res.ok) {
          alert(`Config for ${configType} updated successfully!`);
        } else {
          alert("Failed to save config file");
        }
      }
    } catch (e) {
      console.error(e);
      alert("Api request failed");
    }
  };

  const files = [
    { id: 'icp_profiles/icp.yaml', name: `icp_profiles/${domainInput}_icp.yaml` },
    { id: 'personas/personas.yaml', name: `personas/${domainInput}_personas.yaml` },
    { id: 'triggers/triggers.yaml', name: `triggers/${domainInput}_triggers.yaml` },
    { id: 'mock_data/mock.json', name: `mock_data/${domainInput}_mock.json` }
  ];

  return (
    <div className="flex-1 flex flex-col gap-6 overflow-hidden h-full">
      {/* Header */}
      <div className="flex justify-between items-center border-b border-strong pb-4 shrink-0">
        <div>
          <h1 className="font-display font-bold text-lg tracking-tight text-primary">DOMAIN CONFIGURATION ENGINE</h1>
          <p className="text-[11px] text-muted font-sans mt-0.5">Edit rules, target filters, buyer persona criteria, and mock companies/contacts JSON datasets.</p>
        </div>
      </div>

      {/* Main split editor */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-0">
        {/* Left Workspace Panel (3 cols) */}
        <div className="lg:col-span-3 border border-strong rounded bg-surface p-4 flex flex-col gap-4 min-h-0 overflow-y-auto">
          {/* Active Domain Selector */}
          <div className="space-y-1.5">
            <span className="text-[10px] font-semibold text-muted font-sans uppercase tracking-wider block">ACTIVE DOMAIN</span>
            <select
              value={domainInput}
              onChange={(e) => setDomainInput(e.target.value)}
              className="w-full bg-base border border-strong rounded-sm px-2.5 py-2 text-secondary outline-none focus:border-accent text-xs cursor-pointer font-sans"
            >
              {domainsList.map(d => (
                <option key={d} value={d}>
                  {d.replace('_', ' ').toUpperCase()}
                </option>
              ))}
            </select>
          </div>

          {/* Create Domain Option */}
          <div className="border-t border-strong pt-3 space-y-2">
            <span className="text-[10px] font-semibold text-muted font-sans uppercase tracking-wider block">REGISTER CUSTOM DOMAIN</span>
            <div className="flex gap-2">
              <input
                type="text"
                value={newDomainName}
                onChange={(e) => setNewDomainName(e.target.value)}
                placeholder="e.g. martech"
                className="flex-1 bg-base border border-strong rounded-sm px-2.5 py-1 text-primary placeholder:text-muted outline-none focus:border-accent text-[11px]"
              />
              <button
                onClick={handleCreateDomain}
                className="p-1.5 bg-accent hover:bg-[#d4f950] text-slate-950 rounded-sm font-semibold transition"
                title="Create Domain Templates"
              >
                <Plus className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Config Files Tree */}
          <div className="border-t border-strong pt-3 flex-1 flex flex-col gap-1.5 min-h-0">
            <span className="text-[10px] font-semibold text-muted font-sans uppercase tracking-wider block">WORKSPACE FILES</span>
            
            <div className="space-y-1 overflow-y-auto flex-1 font-mono text-[11px] text-secondary">
              {files.map(f => {
                const isActive = activeFile === f.id;
                return (
                  <button
                    key={f.id}
                    onClick={() => setActiveFile(f.id)}
                    className={`w-full flex items-center gap-2 px-2 py-1.5 rounded text-left transition ${
                      isActive ? 'bg-accent-dim text-accent font-bold' : 'hover:bg-base text-muted hover:text-secondary'
                    }`}
                  >
                    <Folder className="w-3.5 h-3.5 shrink-0" />
                    <span className="truncate">{f.name}</span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right JSON/Text Editor (9 cols) */}
        <div className="lg:col-span-9 border border-strong rounded bg-surface flex flex-col overflow-hidden relative min-h-0">
          {/* File Header */}
          <div className="flex justify-between items-center px-4 py-2 border-b border-strong bg-base shrink-0">
            <span className="font-mono text-[11px] text-muted">{activeFile.replace('icp.yaml', `${domainInput}_icp.yaml`).replace('personas.yaml', `${domainInput}_personas.yaml`).replace('triggers.yaml', `${domainInput}_triggers.yaml`).replace('mock.json', `${domainInput}_mock.json`)}</span>
            <span className="text-[9px] text-accent font-mono">
              {activeFile.includes('mock.json') ? 'JSON DATASET DETECTED' : 'CONFIG OBJECT DETECTED'}
            </span>
          </div>

          {/* Text Area */}
          <div className="flex-1 p-4 bg-[#0a0a08] min-h-0">
            <textarea
              value={yamlContent}
              onChange={(e) => setYamlContent(e.target.value)}
              className="w-full h-full bg-transparent font-mono text-[11px] text-secondary leading-relaxed outline-none resize-none"
            />
          </div>

          {/* Bottom Controls Bar */}
          <div className="flex items-center justify-between px-4 py-3 border-t border-strong bg-surface shrink-0 text-[10px] font-mono text-muted">
            <div>
              <span>Domain: <strong className="text-primary">{domainInput.toUpperCase()}</strong></span>
            </div>
            
            <div className="flex gap-2">
              {!activeFile.includes('mock.json') && (
                <button
                  onClick={() => setPreviewOpen(!previewOpen)}
                  className="px-3 py-1.5 border border-strong bg-base hover:bg-elevated text-secondary hover:text-primary rounded-sm transition uppercase"
                >
                  Preview ICP Rules
                </button>
              )}
              <button
                onClick={handleSave}
                className="px-3 py-1.5 bg-accent hover:bg-[#d4f950] text-slate-950 rounded-sm font-display font-semibold transition uppercase flex items-center gap-1.5"
              >
                <Save className="w-3 h-3" /> Save Changes
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Preview ICP Criteria Overlay */}
      {previewOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-base/80 backdrop-blur-sm">
          <div className="w-full max-w-md border border-strong rounded bg-surface p-5 space-y-4">
            <div className="flex justify-between items-center border-b border-strong pb-3">
              <span className="font-display font-bold text-xs tracking-wider uppercase text-accent">ICP RULES PREVIEW</span>
              <button onClick={() => setPreviewOpen(false)} className="text-muted hover:text-primary">×</button>
            </div>

            <div className="space-y-3 font-mono text-[11px] text-secondary">
              <div className="p-3 bg-base border border-strong rounded space-y-1.5">
                <div><strong>Qualification Limit:</strong> ≥ 70</div>
                <div><strong>Domain Context:</strong> {domainInput.toUpperCase()}</div>
              </div>
            </div>

            <button
              onClick={() => setPreviewOpen(false)}
              className="w-full py-2 bg-accent text-slate-950 font-display font-semibold uppercase text-xs rounded-sm"
            >
              Close Preview
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
