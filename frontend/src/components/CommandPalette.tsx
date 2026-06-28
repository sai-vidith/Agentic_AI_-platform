import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Search, Terminal, Sliders, Play, Settings, AlertTriangle, Eye, Grid } from 'lucide-react';

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onSwitchTab: (tab: any) => void;
  onToggleChaosMonkey: () => void;
  onTriggerDiscovery: () => void;
  onTriggerSimulator: () => void;
}

export default function CommandPalette({
  isOpen,
  onClose,
  onSwitchTab,
  onToggleChaosMonkey,
  onTriggerDiscovery,
  onTriggerSimulator
}: CommandPaletteProps) {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);

  const items = [
    { icon: <Grid className="w-4.5 h-4.5 text-accent" />, label: 'Navigate: Dashboard', action: () => onSwitchTab('dashboard') },
    { icon: <Terminal className="w-4.5 h-4.5 text-accent" />, label: 'Navigate: Live Agent Graph', action: () => onSwitchTab('workflows') },
    { icon: <Sliders className="w-4.5 h-4.5 text-accent" />, label: 'Navigate: Qualified Leads', action: () => onSwitchTab('leads') },
    { icon: <Eye className="w-4.5 h-4.5 text-accent" />, label: 'Navigate: Observability', action: () => onSwitchTab('observability') },
    { icon: <Settings className="w-4.5 h-4.5 text-accent" />, label: 'Navigate: Domain Config', action: () => onSwitchTab('config') },
    { icon: <Play className="w-4.5 h-4.5 text-accent" />, label: 'Open: Webhook Signal Simulator', action: () => onTriggerSimulator() },
    { icon: <AlertTriangle className="w-4.5 h-4.5 text-danger" />, label: 'Action: Toggle Chaos Monkey (Fault Injection)', action: () => onToggleChaosMonkey() },
    { icon: <Play className="w-4.5 h-4.5 text-accent" />, label: 'Action: Trigger Lead Discovery Scan', action: () => onTriggerDiscovery() },
  ];

  const filteredItems = items.filter(item =>
    item.label.toLowerCase().includes(query.toLowerCase())
  );

  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex(prev => (prev + 1) % filteredItems.length);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex(prev => (prev - 1 + filteredItems.length) % filteredItems.length);
      } else if (e.key === 'Enter') {
        e.preventDefault();
        if (filteredItems[selectedIndex]) {
          filteredItems[selectedIndex].action();
          onClose();
        }
      } else if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, selectedIndex, filteredItems, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-base/80 backdrop-blur-sm">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.15 }}
        className="w-full max-w-lg overflow-hidden border rounded-lg bg-elevated border-strong shadow-2xl"
      >
        <div className="flex items-center px-4 border-b border-strong">
          <Search className="w-4 h-4 text-muted shrink-0 mr-3" />
          <input
            type="text"
            placeholder="Search or run a command..."
            value={query}
            onChange={e => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            className="w-full h-12 bg-transparent outline-none text-primary placeholder:text-muted font-mono text-sm"
            autoFocus
          />
        </div>

        <div className="max-h-[300px] overflow-y-auto p-2">
          {filteredItems.length === 0 ? (
            <div className="py-4 text-center text-xs text-muted font-mono">No actions found.</div>
          ) : (
            filteredItems.map((item, idx) => (
              <div
                key={item.label}
                onClick={() => {
                  item.action();
                  onClose();
                }}
                className={`flex items-center gap-3 px-3 py-2.5 rounded cursor-pointer transition text-xs font-mono ${
                  idx === selectedIndex ? 'bg-accent/10 border-l-2 border-accent text-accent' : 'text-secondary hover:bg-overlay'
                }`}
              >
                {item.icon}
                <span>{item.label}</span>
              </div>
            ))
          )}
        </div>
      </motion.div>
    </div>
  );
}
