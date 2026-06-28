import React from 'react';
import { Grid, Activity, Sparkles, Bell, Sliders, Eye, AlertOctagon, HelpCircle } from 'lucide-react';

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: any) => void;
  chaosEnabled: boolean;
  onOpenChaosMonkey: () => void;
  approvalCount: number;
}

export default function Sidebar({
  activeTab,
  setActiveTab,
  chaosEnabled,
  onOpenChaosMonkey,
  approvalCount
}: SidebarProps) {
  
  const menuItems = [
    { id: 'dashboard', label: 'Dashboard', icon: Grid },
    { id: 'workflows', label: 'Live Agent Graph', icon: Activity },
    { id: 'leads', label: 'Qualified Leads', icon: Sparkles },
    { 
      id: 'approvals', 
      label: 'Approvals Queue', 
      icon: Bell,
      badge: approvalCount > 0 ? approvalCount : undefined 
    },
    { id: 'config', label: 'Domain Configs', icon: Sliders },
    { id: 'observability', label: 'Observability & Governance', icon: Eye }
  ];

  return (
    <aside className="w-12 h-screen border-r border-strong bg-surface flex flex-col justify-between items-center py-4 shrink-0 relative z-30">
      
      {/* Brand logo (non-navigation, just points to Dashboard) */}
      <div className="flex flex-col gap-5 items-center w-full">
        <button
          onClick={() => setActiveTab('dashboard')}
          className="h-8 w-8 rounded bg-accent-dim border border-accent/20 flex items-center justify-center text-accent"
          title="NexusAI Dashboard"
        >
          ⚡
        </button>

        {/* Sidebar Navigation */}
        <nav className="flex flex-col gap-2 w-full items-center">
          {menuItems.map((item) => {
            const isActive = activeTab === item.id;
            const Icon = item.icon;
            
            return (
              <div key={item.id} className="relative group w-full flex justify-center">
                <button
                  onClick={() => setActiveTab(item.id)}
                  className={`h-9 w-9 rounded flex items-center justify-center relative transition ${
                    isActive 
                      ? 'text-accent bg-accent-dim border-l-2 border-accent' 
                      : 'text-secondary hover:text-primary hover:bg-elevated'
                  }`}
                  title={item.label}
                >
                  <Icon className="h-4.5 w-4.5" />
                  
                  {item.badge !== undefined && (
                    <span className="absolute -top-1 -right-1 bg-warning text-base text-[8px] font-mono px-1 rounded-full scale-90">
                      {item.badge}
                    </span>
                  )}
                </button>

                {/* Tooltip */}
                <div className="absolute left-12 top-1.5 hidden group-hover:block z-50 px-2 py-1 bg-overlay border border-strong rounded text-[10px] font-mono text-primary whitespace-nowrap shadow-xl">
                  {item.label}
                </div>
              </div>
            );
          })}
        </nav>
      </div>

      {/* Bottom Pinned Controls */}
      <div className="flex flex-col gap-3 items-center w-full">
        
        {/* Chaos Monkey trigger */}
        <div className="relative group flex justify-center w-full">
          <button
            onClick={onOpenChaosMonkey}
            className={`h-9 w-9 rounded flex items-center justify-center transition relative ${
              chaosEnabled 
                ? 'bg-danger-dim border border-danger/30 text-danger shadow-[0_0_10px_rgba(248,113,113,0.2)] animate-pulse' 
                : 'text-secondary hover:text-primary hover:bg-elevated'
            }`}
            title="Chaos Monkey Config"
          >
            <AlertOctagon className="h-4.5 w-4.5" />
          </button>
          <div className="absolute left-12 top-1.5 hidden group-hover:block z-50 px-2 py-1 bg-overlay border border-strong rounded text-[10px] font-mono text-primary whitespace-nowrap shadow-xl">
            Chaos Monkey config
          </div>
        </div>

        {/* System Online badge */}
        <div className="relative group flex justify-center w-full">
          <div className="h-6 w-6 rounded-full flex items-center justify-center cursor-pointer">
            <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse" />
          </div>
          <div className="absolute left-12 top-0.5 hidden group-hover:block z-50 px-2 py-1 bg-overlay border border-strong rounded text-[10px] font-mono text-success whitespace-nowrap shadow-xl">
            SYSTEM ONLINE
          </div>
        </div>

      </div>
    </aside>
  );
}
