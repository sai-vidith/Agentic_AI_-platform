import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  AlertTriangle, 
  Check, 
  X, 
  Terminal, 
  Sparkles,
  ShieldAlert
} from 'lucide-react';

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
    <div className="flex-1 flex gap-6 overflow-hidden" style={{ height: '100%' }}>
      {/* Left Pane: Pending list */}
      <div className="w-1/2 flex flex-col gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            Human-in-the-Loop Approvals <AlertTriangle className="h-5 w-5 text-amber-400" />
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Review leads marked with high risk ratings by the adversarial Shadow Agent and override flags.
          </p>
        </div>

        <div className="flex-1 overflow-y-auto pr-1 flex flex-col gap-3 min-h-0">
          {approvalQueue.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center text-slate-550 border border-dashed border-slate-900 rounded-2xl p-8">
              <Check className="h-7 w-7 text-emerald-400 mb-3" />
              <p className="text-xs font-bold text-slate-400">Approvals queue clean</p>
              <p className="text-[10px] text-slate-500 mt-1 leading-normal text-center">
                No active threats or validation conflicts flagged by the shadow agent. All systems verified.
              </p>
            </div>
          ) : (
            approvalQueue.map((lead) => {
              const isSelected = selectedApproval?.id === lead.id;
              return (
                <button
                  key={lead.id}
                  onClick={() => selectLeadForReview(lead)}
                  className={`w-full text-left p-4.5 border rounded-2xl transition-all flex flex-col gap-2 ${
                    isSelected 
                      ? 'border-amber-500/35 bg-amber-500/5 shadow-[0_0_15px_rgba(245,158,11,0.05)]' 
                      : 'border-slate-900 bg-slate-950/40 hover:border-slate-800'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-extrabold text-sm text-slate-200">{lead.company_name}</span>
                    <span className="px-1.5 py-0.5 rounded bg-amber-500/10 border border-amber-500/25 text-amber-300 text-[9px] font-bold font-mono">
                      RISK CONFIG
                    </span>
                  </div>

                  <p className="text-[10.5px] text-slate-450 line-clamp-2 leading-relaxed">
                    ⚠️ {lead.shadow_verdict?.reasoning || 'Shadow Agent warning of fit divergence.'}
                  </p>

                  <div className="flex items-center justify-between text-[9px] font-mono text-slate-500 border-t border-slate-900/60 pt-2 mt-1">
                    <span>RISK CONFIDENCE: {lead.shadow_verdict?.risk_score || '75'}%</span>
                    <span className="text-amber-400 font-bold">REVIEW DETAILS →</span>
                  </div>
                </button>
              );
            })
          )}
        </div>
      </div>

      {/* Right Pane: Review details and edit outreach */}
      <div className="w-1/2 flex flex-col min-h-0">
        <AnimatePresence mode="wait">
          {selectedApproval ? (
            <motion.div
              key={selectedApproval.id}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              className="flex-1 glass-panel border border-slate-900 rounded-2xl p-5 bg-slate-950/40 overflow-y-auto flex flex-col gap-5"
            >
              {/* Header */}
              <div className="border-b border-slate-900 pb-3">
                <h3 className="text-base font-extrabold text-slate-100 flex items-center gap-2">
                  <ShieldAlert className="h-4.5 w-4.5 text-amber-400" /> Reviewing {selectedApproval.company_name}
                </h3>
                <p className="text-[10.5px] text-slate-400 mt-1">
                  Read the risk indicators below and decide whether to approve or reject this lead.
                </p>
              </div>

              {/* Shadow agent reasoning */}
              <div className="p-4 rounded-xl border border-amber-500/15 bg-amber-500/5 text-xs text-amber-350 leading-relaxed font-mono flex flex-col gap-2">
                <div className="font-extrabold flex items-center gap-1.5 text-[10.5px]">
                  <span>SHADOW VERDICT RATIONALE</span>
                </div>
                <p>"{selectedApproval.shadow_verdict?.reasoning || 'Lead deviates from target buyer persona guidelines.'}"</p>
                <div className="text-[9.5px] text-slate-500 mt-1.5 border-t border-amber-500/10 pt-1.5">
                  ICP Score: {selectedApproval.icp_score}/100 · Risk Factor: {selectedApproval.shadow_verdict?.risk_score || '75'}%
                </div>
              </div>

              {/* Outreach Template Editor */}
              <div className="flex flex-col gap-2">
                <label className="text-[10px] font-bold text-slate-400 font-mono uppercase tracking-wider">
                  Outreach Draft Message
                </label>
                <textarea
                  value={editedTemplate}
                  onChange={(e) => setEditedTemplate(e.target.value)}
                  className="w-full min-h-[140px] bg-slate-950/80 border border-slate-900 focus:border-cyan-500/50 text-slate-300 font-mono text-[11px] leading-relaxed p-3.5 rounded-xl outline-none resize-none"
                />
              </div>

              {/* Action Buttons */}
              <div className="grid grid-cols-2 gap-3 mt-2">
                <button
                  onClick={() => {
                    handleApproval(selectedApproval.id, 'reject');
                    setSelectedApproval(null);
                  }}
                  className="py-3 border border-rose-500/20 bg-rose-500/5 hover:bg-rose-500/10 text-rose-400 text-xs font-bold uppercase tracking-wider rounded-xl transition flex items-center justify-center gap-2"
                >
                  <X className="h-4 w-4" /> Reject Lead
                </button>
                <button
                  onClick={() => {
                    handleApproval(selectedApproval.id, 'approve', editedTemplate);
                    setSelectedApproval(null);
                  }}
                  className="py-3 bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-400 hover:to-emerald-500 text-slate-950 text-xs font-bold uppercase tracking-wider rounded-xl transition shadow-[0_0_15px_rgba(16,185,129,0.1)] flex items-center justify-center gap-2"
                >
                  <Check className="h-4 w-4" /> Approve Lead
                </button>
              </div>
            </motion.div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-slate-555 border border-dashed border-slate-900 rounded-2xl p-8">
              <Terminal className="h-6 w-6 text-slate-700 mb-2 animate-pulse" />
              <p className="text-xs font-bold">Select a risk lead to audit</p>
              <p className="text-[10px] text-slate-650 mt-0.5">Click any lead flagged by the shadow agent on the left to resolve.</p>
            </div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
