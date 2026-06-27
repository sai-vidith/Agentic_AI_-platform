import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  CheckCircle2, 
  Trash2, 
  Mail, 
  Eye, 
  ShieldCheck, 
  Network,
  ChevronRight,
  Sparkles,
  ExternalLink
} from 'lucide-react';

interface LeadsViewProps {
  leads: any[];
  selectedLead: any | null;
  setSelectedLead: (lead: any | null) => void;
  decryptedPII: Record<string, { email: string; phone: string }>;
  simulateVaultAccess: (leadId: string, rawEmail: string, rawPhone: string, plainEmail: string, plainPhone: string) => void;
  handleDeleteLead: (leadId: string) => void;
}

export default function LeadsView({
  leads,
  selectedLead,
  setSelectedLead,
  decryptedPII,
  simulateVaultAccess,
  handleDeleteLead
}: LeadsViewProps) {
  
  // Filter for qualified leads
  const qualifiedLeads = leads.filter(l => l.status === 'approved' || l.icp_score >= 70);

  return (
    <div className="flex-1 flex gap-6 overflow-hidden" style={{ height: '100%' }}>
      {/* Left Pane: Leads List */}
      <div className="w-1/2 flex flex-col gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            Qualified Leads Vault <CheckCircle2 className="h-5 w-5 text-emerald-400" />
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Browse leads matching target ICP guidelines and access decrypted secure communication vault values.
          </p>
        </div>

        <div className="flex-1 overflow-y-auto pr-1 flex flex-col gap-3 min-h-0">
          {qualifiedLeads.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center text-slate-550 border border-dashed border-slate-900 rounded-2xl p-8">
              <CheckCircle2 className="h-7 w-7 text-slate-700 mb-3" />
              <p className="text-xs font-bold text-slate-400">No leads qualified yet</p>
              <p className="text-[10px] text-slate-500 mt-1 leading-normal text-center max-w-[280px]">
                Once discoveries finish scoring above the 70 target or get manual approval, they populate here.
              </p>
            </div>
          ) : (
            qualifiedLeads.map((lead) => {
              const isSelected = selectedLead?.id === lead.id;
              return (
                <button
                  key={lead.id}
                  onClick={() => setSelectedLead(lead)}
                  className={`w-full text-left p-4.5 border rounded-2xl transition-all relative flex flex-col gap-2.5 ${
                    isSelected 
                      ? 'border-cyan-500/30 bg-cyan-500/5 shadow-[0_0_15px_rgba(6,182,212,0.05)]' 
                      : 'border-slate-900 bg-slate-950/40 hover:border-slate-800'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-extrabold text-sm text-slate-200">{lead.company_name}</span>
                    <div className="flex items-center gap-2.5">
                      <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold font-mono ${
                        lead.icp_score >= 70 ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/15' : 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/15'
                      }`}>
                        ICP {lead.icp_score}/100
                      </span>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteLead(lead.id);
                        }}
                        className="p-1 rounded-lg border border-transparent hover:border-slate-850 hover:bg-slate-900/60 text-slate-500 hover:text-slate-350 transition"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                  
                  {lead.company_details?.description && (
                    <p className="text-[10.5px] text-slate-450 line-clamp-2 leading-relaxed">
                      {lead.company_details.description}
                    </p>
                  )}

                  <div className="flex items-center justify-between text-[9px] font-mono text-slate-500 border-t border-slate-900/60 pt-2 mt-1">
                    <span>SECTOR: {lead.company_details?.industry || 'N/A'}</span>
                    <span className="flex items-center gap-1 text-slate-400 font-bold group-hover:text-cyan-400">
                      EXPLORE <ChevronRight className="h-3 w-3" />
                    </span>
                  </div>
                </button>
              );
            })
          )}
        </div>
      </div>

      {/* Right Pane: Selected Lead detail */}
      <div className="w-1/2 flex flex-col min-h-0">
        <AnimatePresence mode="wait">
          {selectedLead ? (
            <motion.div
              key={selectedLead.id}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              className="flex-1 glass-panel border border-slate-900 rounded-2xl p-5 bg-slate-950/40 overflow-y-auto flex flex-col gap-6"
            >
              {/* Card Header */}
              <div className="border-b border-slate-900 pb-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-black text-slate-100">{selectedLead.company_name}</h3>
                  <a 
                    href={selectedLead.company_details?.website || '#'} 
                    target="_blank" 
                    rel="noreferrer"
                    className="p-1.5 rounded-lg border border-slate-850 bg-slate-900/40 hover:bg-slate-900 hover:border-slate-700 text-slate-400 hover:text-slate-200 text-[10px] flex items-center gap-1 transition"
                  >
                    WEBSITE <ExternalLink className="h-3 w-3" />
                  </a>
                </div>
                <p className="text-[11px] text-slate-400 mt-1.5 leading-relaxed">
                  {selectedLead.company_details?.description || 'No description extracted.'}
                </p>
              </div>

              {/* Decrypted Vault Box */}
              <div className="p-4 rounded-xl border border-slate-900 bg-slate-950/80 relative">
                <div className="absolute top-4 right-4 text-[9px] font-mono text-cyan-400 font-extrabold flex items-center gap-1">
                  <ShieldCheck className="h-3.5 w-3.5" /> SECURE VAULT
                </div>
                <h4 className="text-[10px] font-bold text-slate-400 font-mono uppercase tracking-wider mb-3">
                  Enriched Decision Makers
                </h4>

                <div className="flex flex-col gap-3">
                  {selectedLead.contacts && selectedLead.contacts.length > 0 ? (
                    selectedLead.contacts.map((c: any, ci: number) => {
                      const decrypted = decryptedPII[selectedLead.id];
                      return (
                        <div key={ci} className="p-3 border border-slate-900/60 bg-slate-950 rounded-lg flex items-center justify-between text-xs">
                          <div className="flex flex-col gap-1.5">
                            <span className="font-extrabold text-slate-200">{c.name} ({c.title})</span>
                            <div className="flex flex-col gap-1 text-[10.5px]">
                              {decrypted ? (
                                <>
                                  <span className="text-cyan-400 font-mono flex items-center gap-1.5">
                                    <Mail className="h-3 w-3" /> {decrypted.email}
                                  </span>
                                  <span className="text-cyan-400 font-mono">
                                    📞 {decrypted.phone}
                                  </span>
                                </>
                              ) : (
                                <>
                                  <span className="text-slate-500 font-mono flex items-center gap-1.5">
                                    <Mail className="h-3 w-3" /> {c.email}
                                  </span>
                                  <span className="text-slate-500 font-mono">
                                    📞 {c.phone}
                                  </span>
                                </>
                              )}
                            </div>
                          </div>

                          {!decrypted && (
                            <button
                              onClick={() => simulateVaultAccess(selectedLead.id, c.raw_email, c.raw_phone, c.plain_email, c.plain_phone)}
                              className="px-2.5 py-1 rounded bg-cyan-500/10 hover:bg-cyan-500/20 border border-cyan-500/20 text-cyan-300 text-[10px] font-bold tracking-wider flex items-center gap-1 transition"
                            >
                              <Eye className="h-3 w-3" /> DECRYPT
                            </button>
                          )}
                        </div>
                      );
                    })
                  ) : (
                    <span className="text-[11px] text-slate-550 italic">No direct target decision makers found.</span>
                  )}
                </div>
              </div>

              {/* Hybrid Graph-Vector Entities details */}
              <div className="flex flex-col gap-3">
                <h4 className="text-[10px] font-bold text-slate-400 font-mono uppercase tracking-wider flex items-center gap-1.5">
                  <Network className="h-4 w-4 text-violet-400" /> Knowledge Graph Connections
                </h4>
                
                <div className="p-4 border border-slate-900 bg-slate-950/80 rounded-xl flex flex-col gap-2.5">
                  <div className="flex flex-wrap gap-2">
                    <span className="px-2 py-1 rounded-lg bg-slate-900 border border-slate-850 text-[10.5px] text-slate-350">
                      🏢 <strong>Company:</strong> {selectedLead.company_name}
                    </span>
                    <span className="px-2 py-1 rounded-lg bg-slate-900 border border-slate-850 text-[10.5px] text-slate-350">
                      🏷️ <strong>Domain:</strong> {selectedLead.company_details?.industry || 'Fintech'}
                    </span>
                    <span className="px-2 py-1 rounded-lg bg-slate-900 border border-slate-850 text-[10.5px] text-slate-350">
                      ⚡ <strong>Tech Stack:</strong> {selectedLead.company_details?.tech_stack?.join(', ') || 'React, Python'}
                    </span>
                    <span className="px-2 py-1 rounded-lg bg-slate-900 border border-slate-850 text-[10.5px] text-slate-350">
                      🚀 <strong>Funding Stage:</strong> {selectedLead.company_details?.funding_stage || 'Series A'}
                    </span>
                  </div>

                  <p className="text-[10.5px] text-slate-500 leading-normal italic mt-1 border-t border-slate-900/60 pt-2">
                    Note: Downstream agents query this entity-relationship map for multi-hop graph context.
                  </p>
                </div>
              </div>

              {/* Secure HMAC attest details */}
              {selectedLead.attestation && (
                <div className="p-4 bg-cyan-500/5 border border-cyan-500/10 rounded-xl font-mono text-[10.5px] flex flex-col gap-2.5">
                  <div className="flex items-center gap-2 text-cyan-400 font-black text-[11px]">
                    <ShieldCheck className="h-4.5 w-4.5" />
                    <span>Cryptographic Audit Attestation Verified</span>
                  </div>
                  <div className="text-slate-400 flex flex-col gap-1 text-[9.5px]">
                    <p className="truncate"><strong>HASH:</strong> {selectedLead.attestation.attestation_doc?.hash}</p>
                    <p><strong>ATTESTED BY:</strong> {selectedLead.attestation.attestation_doc?.attested_by}</p>
                    <p><strong>TIMESTAMP:</strong> {selectedLead.attestation.attestation_doc?.timestamp}</p>
                  </div>
                </div>
              )}
            </motion.div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-slate-550 border border-dashed border-slate-900 rounded-2xl p-8">
              <Sparkles className="h-6 w-6 text-slate-700 mb-2 animate-pulse" />
              <p className="text-xs font-bold">Select a lead to explore</p>
              <p className="text-[10px] text-slate-600 mt-0.5">Click any qualified prospect on the left to reveal deep-tech details.</p>
            </div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
