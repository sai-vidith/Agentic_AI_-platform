import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ShieldCheck, Mail, Eye, Network, Check, X, ShieldAlert, Cpu, Linkedin, Globe, ExternalLink, Activity } from 'lucide-react';

interface LeadsViewProps {
  leads: any[];
  selectedLead: any | null;
  setSelectedLead: (lead: any | null) => void;
  decryptedPII: Record<string, { email: string; phone: string }>;
  simulateVaultAccess: (leadId: string, rawEmail: string, rawPhone: string, plainEmail: string, plainPhone: string) => void;
  handleDeleteLead: (leadId: string) => void;
  handleApproval?: (leadId: string, action: 'approve' | 'reject', outreachTemplate?: string) => Promise<any>;
}

export default function LeadsView({
  leads,
  selectedLead,
  setSelectedLead,
  decryptedPII,
  simulateVaultAccess,
  handleDeleteLead,
  handleApproval
}: LeadsViewProps) {
  const [expandedIcpId, setExpandedIcpId] = useState<string | null>(null);
  const [domainFilter, setDomainFilter] = useState<'all' | 'hr_saas' | 'cybersecurity'>('all');
  const [leadTab, setLeadTab] = useState<'approved' | 'pending' | 'disqualified' | 'all_scans'>('all_scans');
  
  // Calculate counts for tab headers
  const approvedCount = leads.filter(l => l.status === 'approved').length;
  const pendingCount = leads.filter(l => l.status === 'approval_required').length;
  const disqualifiedCount = leads.filter(l => l.status === 'disqualified').length;
  const totalScansCount = leads.length;

  const filteredByTab = leads.filter(l => {
    if (leadTab === 'approved') return l.status === 'approved';
    if (leadTab === 'pending') return l.status === 'approval_required';
    if (leadTab === 'disqualified') return l.status === 'disqualified';
    return true; // show all scans
  });

  const qualifiedLeads = filteredByTab.filter(l => {
    if (domainFilter === 'all') return true;
    return l.domain === domainFilter;
  });

  const totalAllCount = filteredByTab.length;
  const hrSaasCount = filteredByTab.filter(l => l.domain === 'hr_saas').length;
  const cyberCount = filteredByTab.filter(l => l.domain === 'cybersecurity').length;

  const toggleIcpBreakdown = (e: React.MouseEvent, leadId: string) => {
    e.stopPropagation();
    setExpandedIcpId(prev => (prev === leadId ? null : leadId));
  };

  return (
    <div className="flex-1 flex gap-6 overflow-hidden h-full">
      {/* Left Pane: Leads List */}
      <div className="w-1/2 flex flex-col gap-4 min-h-0">
        <div className="border-b border-strong pb-3">
          <h2 className="font-display font-bold text-lg text-primary uppercase tracking-tight">PROSPECT INTELLIGENCE & AUDIT VAULT</h2>
          <p className="text-[11px] text-muted font-sans mt-0.5">Explore discovered leads, approve new candidates, audit disqualified records, and trace background silent scans.</p>
          
          {/* Status Tabs Segment Control */}
          <div className="flex gap-2 mt-4 border-b border-strong/40 pb-2">
            <button
              onClick={() => setLeadTab('approved')}
              className={`px-2 py-1 text-[10px] font-mono font-bold uppercase transition rounded-sm ${
                leadTab === 'approved' ? 'bg-success-dim text-success border border-success/30' : 'bg-transparent text-muted hover:text-secondary'
              }`}
            >
              Approved ({approvedCount})
            </button>
            <button
              onClick={() => setLeadTab('pending')}
              className={`px-2 py-1 text-[10px] font-mono font-bold uppercase transition rounded-sm ${
                leadTab === 'pending' ? 'bg-warning-dim text-warning border border-warning/30' : 'bg-transparent text-muted hover:text-secondary'
              }`}
            >
              Pending ({pendingCount})
            </button>
            <button
              onClick={() => setLeadTab('disqualified')}
              className={`px-2 py-1 text-[10px] font-mono font-bold uppercase transition rounded-sm ${
                leadTab === 'disqualified' ? 'bg-danger-dim text-danger border border-danger/30' : 'bg-transparent text-muted hover:text-secondary'
              }`}
            >
              Disqualified ({disqualifiedCount})
            </button>
            <button
              onClick={() => setLeadTab('all_scans')}
              className={`px-2 py-1 text-[10px] font-mono font-bold uppercase transition rounded-sm ${
                leadTab === 'all_scans' ? 'bg-accent-dim text-accent border border-accent/30' : 'bg-transparent text-muted hover:text-secondary'
              }`}
            >
              All Scans ({totalScansCount})
            </button>
          </div>
          
          {/* Domain Filter Buttons */}
          <div className="flex gap-2 mt-3">
            <button
              onClick={() => setDomainFilter('all')}
              className={`px-3 py-1 rounded text-[9px] font-mono font-bold uppercase transition ${
                domainFilter === 'all' ? 'bg-accent text-base' : 'bg-surface border border-strong text-secondary hover:border-accent'
              }`}
            >
              All Domains ({totalAllCount})
            </button>
            <button
              onClick={() => setDomainFilter('hr_saas')}
              className={`px-3 py-1 rounded text-[9px] font-mono font-bold uppercase transition ${
                domainFilter === 'hr_saas' ? 'bg-accent text-base' : 'bg-surface border border-strong text-secondary hover:border-accent'
              }`}
            >
              HR SaaS ({hrSaasCount})
            </button>
            <button
              onClick={() => setDomainFilter('cybersecurity')}
              className={`px-3 py-1 rounded text-[9px] font-mono font-bold uppercase transition ${
                domainFilter === 'cybersecurity' ? 'bg-accent text-base' : 'bg-surface border border-strong text-secondary hover:border-accent'
              }`}
            >
              Cybersecurity ({cyberCount})
            </button>
          </div>
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
                      <div className="flex items-center gap-2">
                        <h3 className="font-display font-bold text-sm text-primary">{lead.company_name}</h3>
                        {lead.status === 'approved' && (
                          <span className="px-1.5 py-0.5 bg-success-dim border border-success/40 text-success text-[8px] font-mono uppercase rounded flex items-center gap-1 font-bold">
                            <Check className="w-2 h-2" /> Approved
                          </span>
                        )}
                        {lead.status === 'approval_required' && (
                          <span className="px-1.5 py-0.5 bg-warning-dim border border-warning/40 text-warning text-[8px] font-mono uppercase rounded flex items-center gap-1 font-bold">
                            <Eye className="w-2 h-2" /> Pending Review
                          </span>
                        )}
                        {lead.status === 'disqualified' && (
                          <span className="px-1.5 py-0.5 bg-danger-dim border border-danger/40 text-danger text-[8px] font-mono uppercase rounded flex items-center gap-1 font-bold">
                            <X className="w-2 h-2" /> Disqualified
                          </span>
                        )}
                        {lead.status === 'new' && (
                          <span className="px-1.5 py-0.5 bg-accent-dim border border-accent/40 text-accent text-[8px] font-mono uppercase rounded flex items-center gap-1 font-bold">
                            <Network className="w-2 h-2" /> Discovered
                          </span>
                        )}
                      </div>
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
                <div className="flex items-center justify-between">
                  <h3 className="font-display font-bold text-base text-primary">{selectedLead.company_name}</h3>
                </div>
                <div className="flex items-center gap-2 mt-1.5 mb-2.5">
                  {selectedLead.company_details?.website && (
                    <a href={selectedLead.company_details.website} target="_blank" rel="noopener noreferrer" className="px-2 py-0.5 border border-strong rounded bg-elevated hover:border-muted text-[10px] text-muted flex items-center gap-1 transition-colors">
                      <Globe className="w-3 h-3 text-accent" />
                      <span>Website</span>
                    </a>
                  )}
                  {selectedLead.company_details?.linkedin && (
                    <a href={selectedLead.company_details.linkedin} target="_blank" rel="noopener noreferrer" className="px-2 py-0.5 border border-strong rounded bg-elevated hover:border-muted text-[10px] text-muted flex items-center gap-1 transition-colors">
                      <Linkedin className="w-3 h-3 text-accent" />
                      <span>LinkedIn</span>
                    </a>
                  )}
                </div>
                <p className="text-[11px] text-muted font-sans leading-relaxed">
                  {selectedLead.company_details?.description || 'No description extracted.'}
                </p>
              </div>

              {/* Pending Human Approval Panel */}
              {selectedLead.status === 'approval_required' && handleApproval && (
                <div className="p-4 border border-warning/30 bg-warning-dim rounded flex flex-col gap-2 shrink-0">
                  <div className="text-xs text-warning font-semibold uppercase font-mono flex items-center gap-1.5">
                    <ShieldAlert className="w-4 h-4" /> Pending Human-in-the-Loop Approval
                  </div>
                  <p className="text-[11px] text-muted font-sans leading-relaxed">
                    This lead successfully cleared the target ICP criteria and requires manual validation before outreach campaign dispatch.
                  </p>
                  <div className="flex gap-2.5 mt-2">
                    <button
                      onClick={async () => {
                        await handleApproval(selectedLead.id, 'approve', selectedLead.outreach_template);
                        setSelectedLead({ ...selectedLead, status: 'approved' });
                      }}
                      className="flex-1 py-1.5 bg-success hover:bg-success/80 text-slate-950 font-display font-bold rounded text-[11px] uppercase transition text-center shadow-lg"
                    >
                      Approve & Dispatch
                    </button>
                    <button
                      onClick={async () => {
                        await handleApproval(selectedLead.id, 'reject');
                        setSelectedLead({ ...selectedLead, status: 'rejected' });
                      }}
                      className="px-4 py-1.5 bg-elevated border border-strong hover:bg-danger text-secondary hover:text-white font-display font-bold rounded text-[11px] uppercase transition text-center"
                    >
                      Reject
                    </button>
                  </div>
                </div>
              )}

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
                          <div className="font-semibold text-primary">
                            <span>{c.name} ({c.title})</span>
                          </div>
                          <div className="text-[10px] text-secondary">
                            {decrypted ? decrypted.email : 'pr████@razorx.in'}
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {c.linkedin && (
                            <a href={c.linkedin} target="_blank" rel="noopener noreferrer" className="p-1 border border-strong rounded bg-elevated hover:border-muted text-muted hover:text-primary transition-colors" title="View LinkedIn Profile">
                              <Linkedin className="w-3.5 h-3.5 text-accent" />
                            </a>
                          )}
                          {!decrypted && (
                            <button
                              onClick={() => simulateVaultAccess(selectedLead.id, c.raw_email, c.raw_phone, c.plain_email, c.plain_phone)}
                              className="px-2.5 py-1 bg-elevated border border-strong rounded text-[10px] text-accent hover:border-accent"
                            >
                              Decrypt
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Pipeline Activity Logs */}
              {selectedLead.pipeline_log && selectedLead.pipeline_log.length > 0 && (
                <div className="space-y-3">
                  <span className="text-[10px] font-semibold text-muted font-sans uppercase tracking-wider block">Agent Pipeline Logs & Activity Trace</span>
                  <div className="p-4 bg-base border border-strong rounded font-mono text-[10px] text-secondary space-y-2 max-h-[200px] overflow-y-auto leading-relaxed">
                    {selectedLead.pipeline_log.map((log: string, lIdx: number) => (
                      <div key={lIdx} className="border-b border-strong/20 pb-1.5 last:border-0 last:pb-0 flex gap-2">
                        <span className="text-accent shrink-0">⚡</span>
                        <span>{log}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

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

              {/* Research Sources & Trust Verification */}
              {selectedLead.sources && selectedLead.sources.length > 0 && (
                <div className="space-y-2.5">
                  <span className="text-[10px] font-semibold text-muted font-sans uppercase tracking-wider block">Research Citations ({selectedLead.sources.length})</span>
                  
                  {/* Perplexity-style horizontal citation links */}
                  <div className="flex flex-wrap gap-1.5">
                    {selectedLead.sources.map((s: any, idx: number) => {
                      const isCorrect = s.status !== 'Wrong';
                      let domainName = 'link';
                      try {
                        domainName = new URL(s.url).hostname.replace('www.', '');
                      } catch (e) {}
                      
                      return (
                        <a
                          key={idx}
                          href={s.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          title={`${s.title} - ${isCorrect ? 'Verified' : 'Stale/Unverified'}\nAudit: ${s.reason || 'Verified'}`}
                          className={`px-2.5 py-1 border rounded text-[10px] font-mono flex items-center gap-1.5 transition-all hover:scale-[1.02] cursor-pointer ${
                            isCorrect 
                              ? 'border-success/30 bg-success-dim hover:border-success/60 text-success' 
                              : 'border-danger/30 bg-danger-dim hover:border-danger/60 text-danger'
                          }`}
                        >
                          <span className="w-3.5 h-3.5 rounded-full bg-surface border border-strong flex items-center justify-center text-[9px] font-sans font-bold text-muted">
                            {idx + 1}
                          </span>
                          <span className="truncate max-w-[110px]">{domainName}</span>
                          <ExternalLink className="w-2.5 h-2.5 opacity-60" />
                        </a>
                      );
                    })}
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

              {/* Outreach Campaign Section */}
              {selectedLead.outreach_template && (
                <div className="space-y-3 pt-2 border-t border-strong">
                  <div className="flex justify-between items-center">
                    <span className="text-[10px] font-semibold text-muted font-sans uppercase tracking-wider">Outreach Message Draft</span>
                    {selectedLead.status === 'approved' && (
                      <span className="px-1.5 py-0.2 bg-success/20 border border-success/40 text-success text-[8px] font-mono uppercase rounded">Campaign Dispatched</span>
                    )}
                  </div>
                  <div className="p-3 bg-base border border-strong rounded font-mono text-[10.5px] leading-relaxed text-secondary select-all whitespace-pre-wrap">
                    {selectedLead.outreach_template}
                  </div>
                  
                  {/* Send Mail Trigger Button */}
                  <button
                    onClick={() => {
                      const firstContact = selectedLead.contacts?.[0];
                      if (firstContact) {
                        const email = decryptedPII[firstContact.raw_email || selectedLead.id]?.email || firstContact.plain_email || firstContact.email || '';
                        const lines = selectedLead.outreach_template.split('\n');
                        const subjectLine = lines.find((line: string) => line.toLowerCase().startsWith('subject:')) || '';
                        const subject = subjectLine ? subjectLine.replace(/subject:/i, '').trim() : `Outreach to ${selectedLead.company_name}`;
                        const bodyLines = lines.filter((line: string) => !line.toLowerCase().startsWith('subject:'));
                        const body = bodyLines.join('\n').trim();
                        
                        const mailtoUrl = `mailto:${encodeURIComponent(email)}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
                        window.open(mailtoUrl, '_self');
                      }
                    }}
                    className="w-full py-2 bg-accent hover:bg-[#d4f950] text-slate-950 hover:scale-[1.01] transition font-sans font-bold uppercase text-[11px] rounded flex justify-center items-center gap-1.5"
                  >
                    <Mail className="w-4 h-4" /> Send Outreach via Mail Client
                  </button>
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
