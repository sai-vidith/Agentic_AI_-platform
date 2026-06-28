import React from 'react';
import { motion } from 'framer-motion';
import { ArrowRight, Play, Zap, Cpu, ShieldCheck, Network, Layers } from 'lucide-react';

interface LandingPageProps {
  onEnterDashboard: () => void;
}

export default function LandingPage({ onEnterDashboard }: LandingPageProps) {
  const ease = [0.16, 1, 0.3, 1] as const;

  return (
    <div className="min-h-screen bg-base text-primary overflow-y-auto relative cyber-grid">
      {/* Decorative Radial Lightbeams */}
      <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-accent/5 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute top-10 right-1/4 w-[400px] h-[400px] bg-accent/3 rounded-full blur-[100px] pointer-events-none" />

      {/* Navigation Header */}
      <motion.nav
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.6, ease }}
        className="sticky top-0 z-50 w-full px-6 py-4 backdrop-blur-md border-b border-strong bg-base/60"
      >
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3 group cursor-pointer">
            <div className="h-8 w-8 rounded bg-accent-dim border border-accent/20 flex items-center justify-center text-accent">
              ⚡
            </div>
            <span className="text-sm font-bold tracking-wider font-display text-primary uppercase">
              NEXUS<span className="text-accent font-black">AI</span>
            </span>
          </div>

          <button
            onClick={onEnterDashboard}
            className="px-5 py-2.5 text-xs font-display font-semibold uppercase tracking-wider text-slate-950 bg-accent hover:bg-[#d4f950] rounded-sm transition duration-200 flex items-center gap-1.5 border border-transparent"
          >
            Launch Terminal <ArrowRight className="h-3.5 w-3.5 text-slate-950" />
          </button>
        </div>
      </motion.nav>

      {/* Hero Section */}
      <section className="relative max-w-6xl mx-auto px-6 pt-16 pb-24 grid lg:grid-cols-2 gap-12 items-center min-h-[80vh]">
        {/* Left Content */}
        <div className="text-left space-y-6">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease }}
            className="inline-flex items-center gap-2 px-3 py-1 rounded bg-accent-dim border border-accent/20 text-[10px] font-mono text-accent uppercase tracking-wider"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
            <span>Autonomous Discovery Platform</span>
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1, duration: 0.8, ease }}
            className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight leading-[1.1] font-display text-primary uppercase"
          >
            React to Market Events.
            <br />
            <span className="text-accent">
              Sequence Intent.
            </span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2, duration: 0.6, ease }}
            className="text-sm text-secondary max-w-lg leading-relaxed font-sans"
          >
            NexusAI deploys self-healing DAG workflows, dynamic planning models, and multi-agent debates to monitor market triggers, enrich leads, and build complex buying committee maps autonomously.
          </motion.p>

          {/* Social Proof */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 0.6, ease }}
            className="flex items-center gap-4 p-4 rounded bg-surface border border-strong max-w-md font-mono text-[11px]"
          >
            <div className="h-8 w-8 rounded-full bg-accent-dim border border-accent/20 flex items-center justify-center text-[10px] text-accent">
              ⚔️
            </div>
            <div>
              <p className="font-semibold text-primary uppercase text-[10px]">OpenAI Debate Protocol Integrated</p>
              <p className="text-[10px] text-muted leading-normal mt-0.5">Adversarial Shadow critiques & Judge validations.</p>
            </div>
          </motion.div>

          {/* Call to Actions */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4, duration: 0.6, ease }}
            className="flex flex-wrap items-center gap-4"
          >
            <button
              onClick={onEnterDashboard}
              className="px-6 py-3.5 bg-accent hover:bg-[#d4f950] text-slate-950 font-display font-semibold uppercase tracking-wider text-xs rounded-sm transition duration-200 flex items-center gap-2"
            >
              Launch Dashboard Terminal
              <ArrowRight className="w-4 h-4 text-slate-950" />
            </button>
            <button
              onClick={onEnterDashboard}
              className="px-6 py-3.5 bg-surface border border-strong hover:bg-elevated text-secondary hover:text-primary rounded-sm text-xs font-mono transition flex items-center gap-1.5"
            >
              <Play className="w-3.5 h-3.5 text-accent" /> View Spec Architecture
            </button>
          </motion.div>
        </div>

        {/* Right Dashboard Mockup */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95, rotateY: 10, rotateX: 5 }}
          animate={{ opacity: 1, scale: 1, rotateY: -6, rotateX: 6 }}
          transition={{ delay: 0.3, duration: 0.8, ease }}
          className="relative perspective-container hidden lg:block"
        >
          <div className="w-[500px] h-[340px] bg-surface rounded border border-strong shadow-[0_20px_50px_rgba(0,0,0,0.8)] overflow-hidden flex flex-col">
            {/* Window bar */}
            <div className="flex items-center justify-between px-4 py-2 border-b border-strong bg-[#0e0e0d]">
              <div className="flex gap-1.5">
                <span className="w-2 h-2 rounded-full bg-border-strong" />
                <span className="w-2 h-2 rounded-full bg-border-strong" />
                <span className="w-2 h-2 rounded-full bg-border-strong" />
              </div>
              <span className="text-[9px] font-mono text-muted">operator@nexus-terminal:~</span>
            </div>

            {/* Fake Layout */}
            <div className="flex-1 p-4 grid grid-cols-3 gap-3 font-mono text-[10px]">
              {/* Sidebar */}
              <div className="col-span-1 border-r border-strong pr-3 space-y-1.5">
                <div className="h-6 rounded-sm bg-accent-dim border border-accent/20 flex items-center px-2 text-accent">
                  Dashboard
                </div>
                <div className="h-6 rounded-sm bg-base border border-strong flex items-center px-2 text-muted">
                  Agent Graph
                </div>
                <div className="h-6 rounded-sm bg-base border border-strong flex items-center px-2 text-muted">
                  Vault Leads
                </div>
              </div>

              {/* Contents */}
              <div className="col-span-2 space-y-3">
                <div className="flex justify-between items-center text-[10px]">
                  <span className="font-bold text-primary">Workflow Thread: Stripe</span>
                  <span className="text-[8px] px-1.5 py-0.5 rounded bg-success-dim border border-success/20 text-success uppercase">Active</span>
                </div>

                <div className="p-2 border border-strong rounded bg-base space-y-1">
                  <div className="text-[8px] text-muted uppercase">ACTIVE AGENT RUNNING</div>
                  <div className="font-semibold text-accent uppercase">Shadow Agent Debate...</div>
                  <div className="w-full bg-surface h-1 rounded overflow-hidden">
                    <div className="bg-accent w-3/5 h-full rounded animate-pulse" />
                  </div>
                </div>

                <div className="p-2 border border-strong rounded bg-base space-y-1">
                  <div className="text-[8px] text-muted uppercase">Intent Velocity Map</div>
                  <div className="h-10 flex items-end gap-1.5">
                    {[20, 50, 40, 75, 90, 95].map((h, i) => (
                      <div key={i} className="flex-1 bg-accent rounded-t" style={{ height: `${h}%` }} />
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </section>

      {/* Features Specs */}
      <section className="max-w-6xl mx-auto px-6 py-16 border-t border-strong grid md:grid-cols-3 gap-6 shrink-0">
        <div className="p-5 border border-strong rounded bg-surface space-y-3">
          <div className="h-8 w-8 rounded bg-accent-dim border border-accent/20 flex items-center justify-center text-accent font-bold">1</div>
          <h3 className="font-display font-semibold text-sm text-primary uppercase">Event Webhooks</h3>
          <p className="text-[11px] text-muted leading-relaxed font-sans">
            Instantly react to incoming Crunchbase or LinkedIn event webhooks. Trigger qualification pipelines dynamically.
          </p>
        </div>

        <div className="p-5 border border-strong rounded bg-surface space-y-3">
          <div className="h-8 w-8 rounded bg-accent-dim border border-accent/20 flex items-center justify-center text-accent font-bold">2</div>
          <h3 className="font-display font-semibold text-sm text-primary uppercase">Debate Protocol</h3>
          <p className="text-[11px] text-muted leading-relaxed font-sans">
            Multi-turn adversarial debate between Advocate and Shadow agents validated in real-time by TEE-encrypted judges.
          </p>
        </div>

        <div className="p-5 border border-strong rounded bg-surface space-y-3">
          <div className="h-8 w-8 rounded bg-accent-dim border border-accent/20 flex items-center justify-center text-accent font-bold">3</div>
          <h3 className="font-display font-semibold text-sm text-primary uppercase">Influence Graph</h3>
          <p className="text-[11px] text-muted leading-relaxed font-sans">
            Generate complex organizational maps to isolate decision makers, key influencers, and gatekeepers automatically.
          </p>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-strong py-8 text-center text-[10px] font-mono text-muted uppercase">
        <p>© 2026 NexusAI. Powered by OpenAI Research Debate Architectures.</p>
      </footer>
    </div>
  );
}
