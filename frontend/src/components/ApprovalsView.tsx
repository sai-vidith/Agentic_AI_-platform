import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertTriangle, Check, X, ShieldAlert, Terminal } from 'lucide-react';

interface ApprovalsViewProps {
  approvalQueue: any[];
  handleApproval: (leadId: string, action: 'approve' | 'reject', template?: string) => void;
}

export default function ApprovalsView({
  approvalQueue,
  handleApproval
}: ApprovalsViewProps) {
  const [selectedApproval, setSelectedApproval] = useState<any | null>(null);
  const [editedTemplate, setEditedTemplate] = useState<string>('');

  const selectLeadForReview = (lead: any) => {
    setSelectedApproval(lead);
    setEditedTemplate(lead.outreach_template || '');
  };

  return (
    <div className="flex-1 flex gap-6 overflow-hidden h-full">
      {/* Left Pane: Pending list */}
      <div className="w-1/2 flex flex-col gap-4 min-h-0">
        <div className="border-b border-strong pb-3">
          <h2 className="font-display font-bold text-lg text-primary uppercase tracking-tight">Approvals Queue</h2>
          <p className="text-[11px] text-muted font-sans mt-0.5">Review validation conflicts and override warnings flagged by the shadow adversary.</p>
        </div>

        <div className="flex-1 overflow-y-auto pr-1 flex flex-col gap-3 min-h-0">
          {approvalQueue.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center text-muted border border-dashed border-strong rounded p-8">
              <Check className="h-7 w-7 text-success mb-3 animate-pulse" />
              <p className="text-xs font-mono">Approvals queue clear.</p>
            </div>
          ) : (
            approvalQueue.map((lead) => {
              const isSelected = selectedApproval?.id === lead.id;
              return (
                <button
                  key={lead.id}
                  onClick={() => selectLeadForReview(lead)}
                  className={`w-full text-left p-4 border rounded transition-all flex flex-col gap-2.5 ${
                    isSelected ? 'border-accent bg-accent-dim' : 'border-strong bg-surface hover:border-border-strong'
                  }`}
                >
                  <div className="flex items-center justify-between w-full">
                    <span className="font-display font-bold text-sm text-primary">{lead.company_name}</span>
                    <span className="px-2 py-0.5 rounded bg-warning-dim border border-warning/20 text-warning text-[9px] font-mono font-bold uppercase">
                      SHADOW CONFLICT
                    </span>
                  </div>

                  <p className="text-[11px] text-secondary font-sans line-clamp-2 leading-relaxed">
                    ⚠️ {lead.shadow_verdict?.reason || 'Shadow Agent warning of fit divergence.'}
                  </p>

                  <div className="flex items-center justify-between text-[10px] font-mono text-muted border-t border-strong pt-2 mt-1 w-full">
                    <span>RISK FACTOR: {lead.shadow_verdict?.confidence || '75'}%</span>
                    <span className="text-accent font-bold uppercase tracking-wider">Review Conflict →</span>
                  </div>
                </button>
              );
            })
          )}
        </div>
      </div>

      {/* Right Pane: Review details and diff-view */}
      <div className="w-1/2 flex flex-col min-h-0">
        <AnimatePresence mode="wait">
          {selectedApproval ? (
            <motion.div
              key={selectedApproval.id}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              className="flex-1 border border-strong rounded bg-surface p-5 overflow-y-auto flex flex-col gap-5"
            >
              {/* Header */}
              <div className="border-b border-strong pb-3">
                <h3 className="font-display font-bold text-base text-primary flex items-center gap-2">
                  <ShieldAlert className="w-4 h-4 text-warning" />
                  <span>Reviewing {selectedApproval.company_name}</span>
                </h3>
              </div>

              {/* Side-by-Side Diff Panel */}
              <div className="grid grid-cols-2 gap-4">
                {/* Left: Shadow Objection */}
                <div className="p-3 bg-danger-dim border border-danger/10 rounded font-mono text-[10px] text-danger space-y-2">
                  <div className="font-bold uppercase tracking-wider">Adversary Objection</div>
                  <div className="leading-relaxed">
                    "{selectedApproval.shadow_verdict?.reason || 'Objection raised regarding client headcount target size.'}"
                  </div>
                </div>

                {/* Right: ICP Matcher Defense */}
                <div className="p-3 bg-success-dim border border-success/10 rounded font-mono text-[10px] text-success space-y-2">
                  <div className="font-bold uppercase tracking-wider">ICP Advocate Defense</div>
                  <div className="leading-relaxed">
                    "ICP Matcher scored fit at {selectedApproval.icp_score}/100. Target stack shows growth indicators."
                  </div>
                </div>
              </div>

              {/* Outreach Template Draft Editor */}
              <div className="flex flex-col gap-2 font-mono text-[10px]">
                <label className="text-muted uppercase">Outreach Message Draft</label>
                <textarea
                  value={editedTemplate}
                  onChange={(e) => setEditedTemplate(e.target.value)}
                  className="w-full min-h-[120px] bg-base border border-strong text-primary text-[11px] p-3 rounded outline-none focus:border-accent resize-none leading-relaxed"
                />
              </div>

              {/* Action Buttons */}
              <div className="flex flex-col gap-2 pt-2">
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() => {
                      handleApproval(selectedApproval.id, 'approve', editedTemplate);
                      setSelectedApproval(null);
                    }}
                    className="py-2.5 bg-accent hover:bg-[#d4f950] text-base font-display font-semibold uppercase tracking-wider text-[12px] rounded-sm transition text-center text-slate-950 flex justify-center items-center gap-1.5"
                  >
                    <Check className="w-4 h-4" /> Approve Lead
                  </button>

                  <button
                    onClick={() => {
                      handleApproval(selectedApproval.id, 'reject');
                      setSelectedApproval(null);
                    }}
                    className="py-2.5 border border-danger/30 bg-danger-dim hover:bg-danger hover:text-base text-danger text-xs font-mono uppercase rounded-sm transition flex justify-center items-center gap-1.5"
                  >
                    <X className="w-4 h-4" /> Reject Lead
                  </button>
                </div>

                <button
                  onClick={() => selectLeadForReview(selectedApproval)}
                  className="w-full py-2 border border-strong bg-base hover:bg-elevated text-secondary hover:text-primary text-[11px] font-mono uppercase rounded-sm transition"
                >
                  Ask Shadow to Re-Evaluate
                </button>
              </div>
            </motion.div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-muted border border-dashed border-strong rounded p-8">
              <Terminal className="h-6 w-6 text-disabled mb-2 animate-pulse" />
              <p className="text-xs font-mono">Select a conflict lead on the left to resolve and run override actions.</p>
            </div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
