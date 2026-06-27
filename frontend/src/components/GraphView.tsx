import React from 'react';
import ReactFlow, { Controls, Background, Node, Edge } from 'reactflow';
import { motion, AnimatePresence } from 'framer-motion';
import { Cpu, Terminal, ArrowRight } from 'lucide-react';
import 'reactflow/dist/style.css';

interface GraphViewProps {
  nodes: Node[];
  edges: Edge[];
  streamingThoughts: Record<string, string>;
  companyInput: string;
  agentFeed: any[];
  handleClearLogs: () => void;
  handleClearThoughts: () => void;
}

export default function GraphView({
  nodes,
  edges,
  streamingThoughts,
  companyInput,
  agentFeed,
  handleClearLogs,
  handleClearThoughts
}: GraphViewProps) {
  // Find which node is currently active (thinking)
  const activeNode = nodes.find(n => n.data.status === 'thinking');
  const hasThoughts = Object.keys(streamingThoughts).length > 0;

  return (
    <div className="flex-1 flex flex-col gap-4 overflow-hidden" style={{ height: '100%' }}>
      {/* Tab Header */}
      <div>
        <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
          Agent Topology Graph <Cpu className="h-5 w-5 text-cyan-400" />
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Visualizing topological execution path, agent statuses, and dynamic path pruning.
        </p>
      </div>

      {/* Main split canvas */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-0">
        {/* Left: React Flow diagram */}
        <div className="lg:col-span-8 glass-panel border border-slate-900 rounded-2xl overflow-hidden bg-slate-950/40 relative flex flex-col min-h-[350px]">
          <div className="absolute top-4 left-4 z-10 flex items-center gap-2.5 px-3 py-1.5 rounded-lg border border-slate-800 bg-slate-950/90 text-[10px] font-bold font-mono text-slate-300">
            <span className="relative flex h-1.5 w-1.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-cyan-500"></span>
            </span>
            GRAPH INTERACTIVE · DRAG CANVAS
          </div>

          <div className="flex-1" style={{ height: '100%' }}>
            <ReactFlow nodes={nodes} edges={edges} fitView fitViewOptions={{ padding: 0.1 }}>
              <Controls />
              <Background color="#22d3ee" style={{ opacity: 0.03 }} gap={16} />
            </ReactFlow>
          </div>
        </div>

        {/* Right: Dynamic Thoughts Sidebar */}
        <div className="lg:col-span-4 flex flex-col gap-6 min-h-0">
          
          {/* Top: Streaming Thoughts */}
          <div className="glass-panel border border-slate-900 p-5 rounded-2xl flex flex-col bg-slate-950/40 overflow-hidden flex-1">
            <div className="flex items-center justify-between border-b border-slate-900 pb-3 mb-4 shrink-0">
              <h3 className="text-xs font-bold text-slate-350 font-mono uppercase tracking-wider flex items-center gap-2">
                <Terminal className="h-4.5 w-4.5 text-cyan-400" /> Cognitive Process logs
              </h3>
              <button
                onClick={handleClearThoughts}
                className="px-2 py-1 bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-800 hover:border-slate-700 rounded text-[9px] font-mono font-bold transition flex items-center gap-1"
              >
                Clear Logs
              </button>
            </div>

            <div className="flex-1 overflow-y-auto pr-1 flex flex-col gap-4">
              <AnimatePresence mode="wait">
                {hasThoughts ? (
                  Object.entries(streamingThoughts).map(([nodeId, thought]) => {
                    const node = nodes.find(n => n.id === nodeId);
                    const isCurrentlyActive = activeNode?.id === nodeId;
                    
                    return (
                      <motion.div
                        key={nodeId}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="flex flex-col gap-3 mb-4"
                      >
                        <div className="flex items-center gap-2">
                          <span className={`px-2 py-0.5 rounded text-[9px] font-mono font-bold uppercase ${
                            isCurrentlyActive 
                              ? 'bg-cyan-500/10 border-cyan-500/20 text-cyan-300 animate-pulse' 
                              : 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                          } border`}>
                            {isCurrentlyActive ? 'Active' : 'Completed'}
                          </span>
                          <h4 className="text-sm font-bold text-slate-100">{node?.data.label || nodeId}</h4>
                        </div>
                        
                        {node?.data.desc && (
                          <p className="text-xs text-slate-450 italic leading-relaxed">
                            "{node.data.desc}"
                          </p>
                        )}

                        <div className="border border-slate-900 rounded-xl p-3.5 bg-slate-950/80 mt-2 font-mono text-[10px] text-cyan-400 leading-relaxed shadow-inner">
                          {thought}
                        </div>
                      </motion.div>
                    );
                  })
                ) : (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="flex-1 flex flex-col items-center justify-center text-slate-550 p-6 text-center border border-dashed border-slate-900 rounded-xl min-h-[140px]"
                  >
                    <Cpu className="h-6 w-6 text-slate-750 mb-3" />
                    <p className="text-xs font-bold text-slate-400">Pipeline Idle</p>
                    <p className="text-[10px] text-slate-500 mt-1 leading-normal">
                      Trigger a discovery. The active agent's cognitive thoughts will stream here in real-time.
                    </p>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
