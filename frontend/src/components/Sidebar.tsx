import React from 'react';
import { motion } from 'framer-motion';
import { 
  Zap, 
  Activity, 
  CheckCircle2, 
  AlertTriangle, 
  Settings2, 
  FileKey2,
  ChevronLeft,
  ChevronRight,
  ShieldAlert
} from 'lucide-react';

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: any) => void;
  chaosEnabled: boolean;
  toggleChaosMonkey: () => void;
  approvalCount: number;
  collapsed: boolean;
  setCollapsed: (collapsed: boolean) => void;
}

export default function Sidebar({
  activeTab,
  setActiveTab,
  chaosEnabled,
  toggleChaosMonkey,
  approvalCount,
  collapsed,
  setCollapsed
}: SidebarProps) {
  const menuItems = [
    { id: 'dashboard', label: 'Dashboard', icon: Activity },
    { id: 'workflows', label: 'Live Agent Graph', icon: Zap },
    { id: 'leads', label: 'Qualified Leads', icon: CheckCircle2 },
    { 
      id: 'approvals', 
      label: 'Approvals Queue', 
      icon: AlertTriangle,
      badge: approvalCount > 0 ? approvalCount : undefined 
    },
    { id: 'config', label: 'Domain Configs', icon: Settings2 },
    { id: 'observability', label: 'Observability & Governance', icon: FileKey2 }
  ];

  return (
    <motion.aside
      initial={false}
      animate={{ width: collapsed ? 80 : 280 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      className="h-screen sticky top-0 border-r border-slate-900 bg-slate-950/70 backdrop-blur-xl flex flex-col justify-between p-4 relative z-20 shrink-0"
    >
      {/* Dynamic top gradient glow */}
      <div className="absolute top-0 left-0 w-full h-36 bg-gradient-to-b from-cyan-500/5 to-transparent pointer-events-none" />

      <div>
        {/* Header/Logo section */}
        <div className={`flex items-center ${collapsed ? 'justify-center' : 'justify-between'} mb-8 px-2 py-3 border-b border-slate-900`}>
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-cyan-400 via-cyan-600 to-violet-600 flex items-center justify-center shadow-[0_0_20px_rgba(6,182,212,0.15)]">
              <Zap className="h-5 w-5 text-white" />
            </div>
            {!collapsed && (
              <motion.div
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.1 }}
              >
                <h1 className="font-extrabold text-sm tracking-wider text-slate-100 flex items-center gap-0.5">
                  NEXUS<span className="text-cyan-400">AI</span>
                </h1>
                <span className="text-[9px] text-violet-400 font-mono tracking-widest font-bold block uppercase">
                  COGNITIVE ORCHESTRATOR
                </span>
              </motion.div>
            )}
          </div>

          {!collapsed && (
            <button 
              onClick={() => setCollapsed(true)} 
              className="p-1.5 rounded-lg border border-slate-800 hover:bg-slate-900/60 text-slate-400 hover:text-slate-200 transition"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* Collapsed toggle button */}
        {collapsed && (
          <div className="flex justify-center mb-6">
            <button 
              onClick={() => setCollapsed(false)} 
              className="p-2 rounded-xl border border-slate-800 hover:bg-slate-900/60 text-slate-400 hover:text-slate-200 transition"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        )}

        {/* Navigation Section */}
        <nav className="flex flex-col gap-1">
          {menuItems.map((item) => {
            const isActive = activeTab === item.id;
            const Icon = item.icon;
            
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`flex items-center ${collapsed ? 'justify-center py-3' : 'px-4 py-3'} rounded-xl text-xs font-semibold tracking-wide transition-all relative ${
                  isActive ? 'text-cyan-300' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/30'
                }`}
              >
                {isActive && (
                  <motion.div
                    layoutId="sidebar-active-tab"
                    className="absolute inset-0 bg-cyan-500/10 border border-cyan-500/20 rounded-xl"
                    transition={{ type: "spring", bounce: 0.15, duration: 0.4 }}
                  />
                )}
                
                <Icon className={`h-4.5 w-4.5 relative z-10 shrink-0 ${isActive ? 'text-cyan-400' : 'text-slate-400'}`} />
                
                {!collapsed && (
                  <motion.span 
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="ml-3 relative z-10 block"
                  >
                    {item.label}
                  </motion.span>
                )}

                {item.badge !== undefined && !collapsed && (
                  <span className="ml-auto relative z-10 bg-amber-500/25 border border-amber-500/35 text-amber-300 text-[9px] font-extrabold px-1.5 py-0.5 rounded-full">
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Bottom Controls (Chaos Monkey and Status) */}
      <div className="flex flex-col gap-4 border-t border-slate-900 pt-4">
        {/* Chaos Monkey widget */}
        {!collapsed ? (
          <div className="p-3.5 rounded-2xl bg-slate-950 border border-slate-900 relative overflow-hidden">
            <div className="absolute top-0 right-0 w-16 h-16 bg-amber-500/5 rounded-full blur-xl" />
            <div className="flex items-center justify-between gap-3 mb-2">
              <div className="flex items-center gap-2">
                <ShieldAlert className={`h-4 w-4 ${chaosEnabled ? 'text-amber-400' : 'text-slate-500'}`} />
                <span className="text-[11px] font-bold text-slate-300 font-mono tracking-wide">CHAOS MONKEY</span>
              </div>
              <button
                onClick={toggleChaosMonkey}
                className={`relative w-8 h-4.5 rounded-full transition-colors duration-200 focus:outline-none ${
                  chaosEnabled ? 'bg-amber-500' : 'bg-slate-800'
                }`}
              >
                <div
                  className={`absolute top-0.5 left-0.5 w-3.5 h-3.5 rounded-full bg-white transition-transform duration-200 transform ${
                    chaosEnabled ? 'translate-x-3.5' : 'translate-x-0'
                  }`}
                />
              </button>
            </div>
            <p className="text-[9px] text-slate-500 leading-normal">
              Inject active system faults (timeouts, timeouts) to test agent self-healing.
            </p>
          </div>
        ) : (
          <button
            onClick={toggleChaosMonkey}
            className={`mx-auto h-9 w-9 rounded-xl border flex items-center justify-center transition ${
              chaosEnabled 
                ? 'bg-amber-500/10 border-amber-500/30 text-amber-400 shadow-[0_0_10px_rgba(245,158,11,0.1)]' 
                : 'border-slate-850 bg-slate-900/40 text-slate-500 hover:text-slate-300'
            }`}
            title="Toggle Chaos Monkey Fault Injection"
          >
            <ShieldAlert className="h-4.5 w-4.5" />
          </button>
        )}

        {/* Live system state badge */}
        {!collapsed && (
          <div className="flex items-center gap-2.5 px-3 py-2 border border-emerald-500/10 rounded-xl bg-emerald-500/5 text-emerald-400 text-[10px] font-semibold font-mono">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            SYSTEM ONLINE
          </div>
        )}
      </div>
    </motion.aside>
  );
}
