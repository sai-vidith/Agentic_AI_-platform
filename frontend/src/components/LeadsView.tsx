import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ShieldCheck, Mail, Eye, Network, Check, X, ShieldAlert, Cpu } from 'lucide-react';

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
  const [expandedIcpId, setExpandedIcpId] = useState<string | null>(null);
  
  const qualifiedLeads = leads.filter(l => l.status === 'approved' || l.icp_score >= 70);

  const toggleIcpBreakdown = (e: React.MouseEvent, leadId: string) => {
    e.stopPropagation();
    setExpandedIcpId(prev => (prev === leadId ? null : leadId));
  };

  return (
    <div className="flex-1 flex gap-6 overflow-hidden h-full">
      {/* Left Pane: Leads List */}
      <div className="w-1/2 flex flex-col gap-4 min-h-0">
        <div className="border-b border-strong pb-3">
          <h2 className="font-display font-bold text-lg text-primary uppercase tracking-tight">QUALIFIED LEADS VAULT</h2>
          <p className="text-[11px] text-muted font-sans mt-0.5">Explore discovered leads that successfully cleared the target scoring threshold.</p>
        </div>

        <div className="flex-1 overflow-y-auto pr-1 flex flex-col gap-4 min-h-0">
          {qualifiedLeads.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center text-muted border border-dashed border-strong rounded p-8">
              <ShieldCheck className="h-7 w-7 text-disabled mb-3" />
              <p className="text-xs font-mono">No qualified leads logged.</p>
            </div>
          ) : (
            qualifiedLeads.map((lead) => {
              const isSelected = selectedLead?.id === lead.id;
              const isExpanded = expandedIcpId === lead.id;
              
              return (
                <div
                  key={lead.id}
                  onClick={() => setSelectedLead(lead)}
                  className={`p-4 border rounded cursor-pointer transition-all flex flex-col gap-3 ${
                    isSelected ? 'border-accent bg-accent-dim' : 'border-strong bg-surface hover:border-border-strong'
                  }`}
                >
                  {/* Top Row: Name, ICP, Status */}
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="font-display font-bold text-sm text-primary">{lead.company_name}</h3>
                      <div className="text-[10px] text-muted font-mono mt-0.5">
                        {lead.company_details?.industry || 'Fintech'} · {lead.company_details?.hq || 'Remote'} · {lead.company_details?.founded || 'Series A'}
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-2">
                      <button
                        onClick={(e) => toggleIcpBreakdown(e, lead.id)}
                        className="px-2 py-0.5 bg-base border border-strong rounded text-[10px] font-mono text-accent hover:border-accent"
                      >
                        ICP: {lead.icp_score}
                      </button>
                      <span className="w-4 h-4 rounded-full bg-success-dim border border-success/30 flex items-center justify-center text-success text-[8px]">✓</span>
                    </div>
                  </div>

                  {/* Expanded ICP Breakdown */}
                  <AnimatePresence>
                    {isExpanded && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="p-3 bg-base rounded border border-strong space-y-2.5 font-mono text-[9px] text-secondary shrink-0 overflow-hidden"
                      >
                        <div className="font-bold text-[10px] text-accent uppercase">Decision DNA Breakdown</div>
                        
                        <div className="space-y-1">
                          <div className="flex justify-between"><span>Company Size Match:</span><span>90%</span></div>
                          <div className="w-full bg-surface h-1 rounded"><div className="bg-accent h-full w-[90%]" /></div>
                        </div>

                        <div className="space-y-1">
                          <div className="flex justify-between"><span>Growth Trajectory:</span><span>85%</span></div>
                          <div className="w-full bg-surface h-1 rounded"><div className="bg-accent h-full w-[85%]" /></div>
                        </div>

                        <div className="space-y-1">
                          <div className="flex justify-between"><span>Tech Stack Compatibility:</span><span>75%</span></div>
                          <div className="w-full bg-surface h-1 rounded"><div className="bg-accent h-full w-[75%]" /></div>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>

                  <div className="border-t border-strong" />

                  {/* Contact Row */}
                  {lead.contacts && lead.contacts.length > 0 && (
                    <div className="flex justify-between items-center text-[11px] font-mono">
                      <div className="text-secondary truncate max-w-[200px]">
                        <span>{lead.contacts[0].title}: </span>
                        <span className="text-primary">{lead.contacts[0].name}</span>
                      </div>
                      
                      <div className="flex items-center gap-2">
                        <span className="text-muted font-mono text-[10px]">
                          {decryptedPII[lead.contacts[0].raw_email || lead.id] ? decryptedPII[lead.contacts[0].raw_email || lead.id].email : 'pr████@razorx.in'}
                        </span>
                        {!decryptedPII[lead.contacts[0].raw_email || lead.id] && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              simulateVaultAccess(lead.id, lead.contacts[0].raw_email, lead.contacts[0].raw_phone, lead.contacts[0].plain_email, lead.contacts[0].plain_phone);
                            }}
                            className="p-1 bg-elevated border border-strong rounded hover:border-accent text-accent"
                          >
                            🔓
                          </button>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Shadow verdict & attestation row */}
                  <div className="flex justify-between items-center text-[10px] font-mono text-muted pt-1">
                    <span className="flex items-center gap-1">
                      SHADOW: 
                      <span className={lead.shadow_verdict?.status === 'DIVERGENCE_WARNING' ? 'text-warning font-bold' : 'text-success font-bold'}>
                        {lead.shadow_verdict?.status === 'DIVERGENCE_WARNING' ? 'WARNING' : 'PASSED'}
                      </span>
                    </span>
                    <span>ATTESTATION: {lead.id.substring(0, 8)}...</span>
                  </div>

                  {/* Action buttons */}
                  <div className="flex gap-2 border-t border-strong pt-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteLead(lead.id);
                      }}
                      className="flex-1 py-1 bg-danger-dim border border-danger/20 hover:bg-danger text-danger hover:text-base rounded text-[10px] font-mono uppercase transition text-center"
                    >
                      Remove Lead
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Right Pane: Selected Lead details */}
      <div className="w-1/2 flex flex-col min-h-0">
        <AnimatePresence mode="wait">
          {selectedLead ? (
            <motion.div
              key={selectedLead.id}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              className="flex-1 border border-strong rounded bg-surface p-5 overflow-y-auto flex flex-col gap-6"
            >
              {/* Header */}
              <div className="border-b border-strong pb-4">
                <h3 className="font-display font-bold text-base text-primary">{selectedLead.company_name}</h3>
                <p className="text-[11px] text-muted font-sans mt-1.5 leading-relaxed">
                  {selectedLead.company_details?.description || 'No description extracted.'}
                </p>
              </div>

              {/* Secure Vault */}
              <div className="p-4 bg-base border border-strong rounded relative space-y-3">
                <div className="flex justify-between items-center border-b border-strong pb-2">
                  <span className="text-[10px] font-semibold text-muted font-sans uppercase tracking-wider">Secure Cryptographic Vault</span>
                  <span className="text-[9px] text-accent font-mono">TEE LOCK</span>
                </div>

                <div className="space-y-2">
                  {selectedLead.contacts?.map((c: any, i: number) => {
                    const decryptedKey = c.raw_email || selectedLead.id;
                    const decrypted = decryptedPII[decryptedKey];
                    return (
                      <div key={i} className="p-2 border border-strong rounded bg-surface flex items-center justify-between text-xs font-mono">
                        <div className="space-y-1">
                          <div className="font-semibold text-primary">{c.name} ({c.title})</div>
                          <div className="text-[10px] text-secondary">
                            {decrypted ? decrypted.email : 'pr████@razorx.in'}
                          </div>
                        </div>
                        {!decrypted && (
                          <button
                            onClick={() => simulateVaultAccess(selectedLead.id, c.raw_email, c.raw_phone, c.plain_email, c.plain_phone)}
                            className="px-2.5 py-1 bg-elevated border border-strong rounded text-[10px] text-accent hover:border-accent"
                          >
                            Decrypt
                          </button>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Debate Transcript */}
              {selectedLead.debate_transcript && selectedLead.debate_transcript.length > 0 && (
                <div className="space-y-3">
                  <span className="text-[10px] font-semibold text-muted font-sans uppercase tracking-wider block">Adversarial Debate Transcript</span>
                  <div className="p-4 bg-base border border-strong rounded font-mono text-[10.5px] space-y-4">
                    {selectedLead.debate_transcript.map((turn: any, ti: number) => (
                      <div key={ti} className="space-y-1 border-b border-strong/40 pb-2.5 last:border-b-0 last:pb-0">
                        <div className="font-bold text-accent">{turn.role}</div>
                        <div className="text-secondary leading-relaxed">{turn.text}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Cryptographic Attestation */}
              {selectedLead.attestation && (
                <div className="p-4 bg-base border border-strong rounded font-mono text-[10.5px] space-y-2">
                  <div className="flex items-center gap-2 text-accent font-semibold">
                    <ShieldCheck className="w-4 h-4" />
                    <span>TEE Audit Attestation Signature</span>
                  </div>
                  <div className="text-secondary break-all space-y-1 text-[9.5px]">
                    <div><strong>Signature:</strong> {selectedLead.attestation.signature}</div>
                    <div><strong>Payload Hash:</strong> {selectedLead.attestation.attestation_doc?.hash}</div>
                    <div><strong>TEE Signer:</strong> Intel SGX Mock Vault</div>
                  </div>
                </div>
              )}
            </motion.div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-muted border border-dashed border-strong rounded p-8">
              <Cpu className="h-6 w-6 text-disabled mb-2 animate-pulse" />
              <p className="text-xs font-mono">Select a prospect lead on the left to reveal secure vault, debate transcripts, and graph mappings.</p>
            </div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
