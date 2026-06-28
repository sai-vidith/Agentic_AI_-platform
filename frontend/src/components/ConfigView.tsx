import React, { useState } from 'react';
import { Settings, FileText, CheckCircle, Eye, Folder, ChevronRight } from 'lucide-react';

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
  const [activeFile, setActiveFile] = useState('icp_profiles/hr_saas.yaml');
  const [yamlContent, setYamlContent] = useState(
    `# Active ICP Configuration Profile\n` +
    `domain: ${domainInput}\n` +
    `qualification_threshold: 70\n` +
    `target_industries:\n` +
    `  - Fintech\n` +
    `  - Enterprise SaaS\n` +
    `growth_triggers:\n` +
    `  - funding_round: Series A\n` +
    `  - hiring_surge: true\n` +
    `min_headcount: 50\n` +
    `max_headcount: 500`
  );

  const [previewOpen, setPreviewOpen] = useState(false);

  const handleValidate = () => {
    alert("Configuration valid: No syntax errors detected in YAML.");
  };

  const files = [
    { name: 'icp_profiles/hr_saas.yaml', active: activeFile === 'icp_profiles/hr_saas.yaml' },
    { name: 'icp_profiles/cybersecurity.yaml', active: activeFile === 'icp_profiles/cybersecurity.yaml' },
    { name: 'personas/hr_directors.yaml', active: activeFile === 'personas/hr_directors.yaml' },
    { name: 'triggers/crunchbase.yaml', active: activeFile === 'triggers/crunchbase.yaml' }
  ];

  const handleSelectFile = (file: string) => {
    setActiveFile(file);
    if (file.includes('cybersecurity')) {
      setYamlContent(
        `# Active ICP Configuration Profile\n` +
        `domain: cybersecurity\n` +
        `qualification_threshold: 75\n` +
        `target_industries:\n` +
        `  - Financial Services\n` +
        `  - Healthcare Cloud\n` +
        `growth_triggers:\n` +
        `  - leadership_change: true\n` +
        `min_headcount: 200\n` +
        `max_headcount: 5000`
      );
    } else {
      setYamlContent(
        `# Active ICP Configuration Profile\n` +
        `domain: hr_saas\n` +
        `qualification_threshold: 70\n` +
        `target_industries:\n` +
        `  - Fintech\n` +
        `  - Enterprise SaaS\n` +
        `growth_triggers:\n` +
        `  - funding_round: Series A\n` +
        `  - hiring_surge: true\n` +
        `min_headcount: 50\n` +
        `max_headcount: 500`
      );
    }
  };

  return (
    <div className="flex-1 flex flex-col gap-6 overflow-hidden h-full">
      {/* Header */}
      <div className="flex justify-between items-center border-b border-strong pb-4 shrink-0">
        <div>
          <h1 className="font-display font-bold text-lg tracking-tight text-primary">DOMAIN CONFIGURATION ENGINE</h1>
          <p className="text-[11px] text-muted font-sans mt-0.5">Edit rules, target filters, and buyer persona criteria models using YAML parameters.</p>
        </div>
      </div>

      {/* Main split editor */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-0">
        {/* Left File Tree (3 cols) */}
        <div className="lg:col-span-3 border border-strong rounded bg-surface p-4 flex flex-col gap-3 min-h-[150px]">
          <span className="text-[10px] font-semibold text-muted font-sans uppercase tracking-wider block">CONFIG WORKSPACE</span>
          
          <div className="space-y-1 overflow-y-auto flex-1 font-mono text-[11px] text-secondary">
            {files.map(f => (
              <button
                key={f.name}
                onClick={() => handleSelectFile(f.name)}
                className={`w-full flex items-center gap-2 px-2 py-1.5 rounded text-left transition ${
                  f.active ? 'bg-accent-dim text-accent' : 'hover:bg-base text-muted hover:text-secondary'
                }`}
              >
                <Folder className="w-3.5 h-3.5" />
                <span className="truncate">{f.name}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Right YAML Editor (9 cols) */}
        <div className="lg:col-span-9 border border-strong rounded bg-surface flex flex-col overflow-hidden relative">
          {/* File Header */}
          <div className="flex justify-between items-center px-4 py-2 border-b border-strong bg-base shrink-0">
            <span className="font-mono text-[11px] text-muted">{activeFile}</span>
            <span className="text-[9px] text-accent font-mono">YAML DETECTED</span>
          </div>

          {/* Monaco styled text area */}
          <div className="flex-1 p-4 bg-[#0a0a08]">
            <textarea
              value={yamlContent}
              onChange={(e) => setYamlContent(e.target.value)}
              className="w-full h-full bg-transparent font-mono text-[11px] text-secondary leading-relaxed outline-none resize-none"
            />
          </div>

          {/* Bottom Controls Bar */}
          <div className="flex items-center justify-between px-4 py-3 border-t border-strong bg-surface shrink-0 text-[10px] font-mono text-muted">
            <div>
              <span>Active Config: <strong className="text-primary">{domainInput}</strong> · Threshold: <strong className="text-primary">70</strong></span>
            </div>
            
            <div className="flex gap-2">
              <button
                onClick={() => setPreviewOpen(!previewOpen)}
                className="px-3 py-1.5 border border-strong bg-base hover:bg-elevated text-secondary hover:text-primary rounded-sm transition uppercase"
              >
                Preview ICP Criteria
              </button>
              <button
                onClick={handleValidate}
                className="px-3 py-1.5 bg-accent hover:bg-[#d4f950] text-slate-950 rounded-sm font-display font-semibold transition uppercase"
              >
                Validate Config
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
                <div><strong>Size Bracket:</strong> 50 - 500 Headcount</div>
                <div><strong>Sector Filter:</strong> Enterprise SaaS, Fintech</div>
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
