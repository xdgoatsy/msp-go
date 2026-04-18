import React, { useEffect, useRef, useState, useCallback } from 'react';
import { createPortal } from 'react-dom';
import type { Graph } from '@antv/g6';
import { ZoomIn, ZoomOut, Maximize2, Expand, X } from 'lucide-react';
import { cn } from '@/libs/utils/cn';
import { animationCombos } from '@/libs/animations';
import {
  createGraphInstance,
  updateGraphData,
  graphZoomIn,
  graphZoomOut,
  graphFitView,
} from '@/libs/graph';
import type { KnowledgeNode, KnowledgeEdge } from '@/modules/knowledge/types/knowledge';

// Re-export 供外部使用
export type { KnowledgeNode, KnowledgeEdge } from '@/modules/knowledge/types/knowledge';

export interface KnowledgeGraphProps {
  nodes: KnowledgeNode[];
  edges: KnowledgeEdge[];
  onNodeClick?: (node: KnowledgeNode) => void;
  onNodeHover?: (node: KnowledgeNode | null) => void;
  className?: string;
  height?: number;
  showToolbar?: boolean;
}

/**
 * 图谱工具栏组件
 */
interface GraphToolbarProps {
  onZoomIn: () => void;
  onZoomOut: () => void;
  onFitView: () => void;
  onFullscreen?: () => void;
  className?: string;
  position?: 'top-right' | 'bottom';
}

const GraphToolbar: React.FC<GraphToolbarProps> = ({
  onZoomIn,
  onZoomOut,
  onFitView,
  onFullscreen,
  className,
  position = 'top-right',
}) => {
  const isBottom = position === 'bottom';

  return (
    <div
      className={cn(
        'flex items-center gap-1 bg-white/90 dark:bg-surface-800/90 backdrop-blur-sm rounded-lg shadow-lg border border-surface-200 dark:border-surface-700 p-1',
        isBottom ? 'justify-center' : '',
        className
      )}
    >
      <button
        type="button"
        onClick={onZoomIn}
        className={cn(
          'p-2 rounded-md text-surface-600 dark:text-surface-400 hover:bg-surface-100 dark:hover:bg-surface-700 hover:text-primary-600 dark:hover:text-primary-400',
          animationCombos.buttonHover
        )}
        title="放大"
      >
        <ZoomIn className="w-4 h-4" />
      </button>
      <button
        type="button"
        onClick={onZoomOut}
        className={cn(
          'p-2 rounded-md text-surface-600 dark:text-surface-400 hover:bg-surface-100 dark:hover:bg-surface-700 hover:text-primary-600 dark:hover:text-primary-400',
          animationCombos.buttonHover
        )}
        title="缩小"
      >
        <ZoomOut className="w-4 h-4" />
      </button>
      <button
        type="button"
        onClick={onFitView}
        className={cn(
          'p-2 rounded-md text-surface-600 dark:text-surface-400 hover:bg-surface-100 dark:hover:bg-surface-700 hover:text-primary-600 dark:hover:text-primary-400',
          animationCombos.buttonHover
        )}
        title="适应视图"
      >
        <Maximize2 className="w-4 h-4" />
      </button>
      {onFullscreen && (
        <button
          type="button"
          onClick={onFullscreen}
          className={cn(
            'p-2 rounded-md text-surface-600 dark:text-surface-400 hover:bg-surface-100 dark:hover:bg-surface-700 hover:text-primary-600 dark:hover:text-primary-400',
            animationCombos.buttonHover
          )}
          title="全屏"
        >
          <Expand className="w-4 h-4" />
        </button>
      )}
    </div>
  );
};

/**
 * 知识图谱可视化组件
 *
 * 基于 AntV G6 实现的交互式知识图谱
 */
export const KnowledgeGraph: React.FC<KnowledgeGraphProps> = ({
  nodes,
  edges,
  onNodeClick,
  onNodeHover,
  className,
  height = 400,
  showToolbar = true,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<Graph | null>(null);
  const [isReady, setIsReady] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // 使用 ref 存储最新的回调和数据，避免 useEffect 依赖问题
  const nodesRef = useRef(nodes);
  const onNodeClickRef = useRef(onNodeClick);
  const onNodeHoverRef = useRef(onNodeHover);
  const heightRef = useRef(height);

  // 使用 useEffect 同步更新 ref（符合 React Compiler 规则）
  useEffect(() => {
    nodesRef.current = nodes;
  }, [nodes]);

  useEffect(() => {
    onNodeClickRef.current = onNodeClick;
  }, [onNodeClick]);

  useEffect(() => {
    onNodeHoverRef.current = onNodeHover;
  }, [onNodeHover]);

  useEffect(() => {
    heightRef.current = height;
  }, [height]);

  // 初始化图谱
  useEffect(() => {
    if (!containerRef.current) return;

    // 用于跟踪组件是否仍然挂载，避免在卸载后操作已销毁的实例
    let isMounted = true;

    // 延迟初始化以避开 React StrictMode 的首次挂载-卸载周期
    const initTimer = setTimeout(() => {
      if (!isMounted || !containerRef.current || graphRef.current) return;

      const graph = createGraphInstance({
        container: containerRef.current,
        width: containerRef.current.offsetWidth,
        height: heightRef.current,
        nodes: nodesRef.current,
        edges,
        padding: [40, 40, 40, 40],
        nodeSize: 40,
        fontSize: 12,
        labelOffsetY: 8,
        lineWidth: 1.5,
        arrowSize: 6,
        nodesep: 60,
        ranksep: 80,
        onNodeClick: (nodeId, currentNodes) => {
          const nodeData = currentNodes.find((n) => n.id === nodeId);
          if (nodeData && onNodeClickRef.current) {
            onNodeClickRef.current(nodeData);
          }
        },
        onNodeHover: (nodeId, currentNodes) => {
          if (onNodeHoverRef.current) {
            if (nodeId) {
              const nodeData = currentNodes.find((n) => n.id === nodeId);
              if (nodeData) {
                onNodeHoverRef.current(nodeData);
              }
            } else {
              onNodeHoverRef.current(null);
            }
          }
        },
      });

      graphRef.current = graph;

      graph
        .render()
        .then(() => {
          // 检查组件是否仍然挂载（React StrictMode 会导致组件卸载重建）
          if (isMounted && graphRef.current) {
            setIsReady(true);
          }
        })
        .catch(() => {
          // 忽略因组件卸载导致的渲染错误
        });
    }, 0);

    // 窗口大小变化时调整图谱大小
    const handleResize = () => {
      if (containerRef.current && graphRef.current) {
        graphRef.current.setSize(containerRef.current.offsetWidth, heightRef.current);
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      isMounted = false;
      clearTimeout(initTimer);
      window.removeEventListener('resize', handleResize);
      if (graphRef.current) {
        graphRef.current.destroy();
        graphRef.current = null;
      }
    };
    // edges 在初始化时使用，不需要作为依赖
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 数据更新时重新布局
  useEffect(() => {
    const graph = graphRef.current;
    if (graph && isReady) {
      updateGraphData(graph, nodes, edges);
    }
  }, [nodes, edges, isReady]);

  // 缩放控制函数
  const handleZoomIn = useCallback(() => {
    graphZoomIn(graphRef.current);
  }, []);

  const handleZoomOut = useCallback(() => {
    graphZoomOut(graphRef.current);
  }, []);

  const handleFitView = useCallback(() => {
    graphFitView(graphRef.current);
  }, []);

  const handleOpenModal = useCallback(() => {
    setIsModalOpen(true);
  }, []);

  const handleCloseModal = useCallback(() => {
    setIsModalOpen(false);
  }, []);

  return (
    <>
      <div className={cn('relative', className)} style={{ height }}>
        <div
          ref={containerRef}
          className="w-full h-full rounded-xl bg-white dark:bg-surface-900 border border-surface-200 dark:border-surface-700 overflow-hidden"
        />
        {showToolbar && isReady && (
          <GraphToolbar
            onZoomIn={handleZoomIn}
            onZoomOut={handleZoomOut}
            onFitView={handleFitView}
            onFullscreen={handleOpenModal}
            className="absolute top-3 right-3"
          />
        )}
      </div>
      <KnowledgeGraphModal
        isOpen={isModalOpen}
        onClose={handleCloseModal}
        nodes={nodes}
        edges={edges}
        onNodeClick={onNodeClick}
      />
    </>
  );
};

/**
 * 知识图谱全屏弹窗组件
 */
export interface KnowledgeGraphModalProps {
  isOpen: boolean;
  onClose: () => void;
  nodes: KnowledgeNode[];
  edges: KnowledgeEdge[];
  onNodeClick?: (node: KnowledgeNode) => void;
}

export const KnowledgeGraphModal: React.FC<KnowledgeGraphModalProps> = ({
  isOpen,
  onClose,
  nodes,
  edges,
  onNodeClick,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<Graph | null>(null);
  const [isReady, setIsReady] = useState(false);
  const nodesRef = useRef(nodes);

  // 同步更新 nodes ref
  useEffect(() => {
    nodesRef.current = nodes;
  }, [nodes]);

  // 初始化 Modal 内的图谱
  useEffect(() => {
    if (!isOpen || !containerRef.current) return;

    let isMounted = true;

    const initTimer = setTimeout(() => {
      if (!isMounted || !containerRef.current || graphRef.current) return;

      const graph = createGraphInstance({
        container: containerRef.current,
        width: containerRef.current.offsetWidth,
        height: containerRef.current.offsetHeight,
        nodes: nodesRef.current,
        edges,
        padding: [60, 60, 60, 60],
        nodeSize: 50,
        fontSize: 14,
        labelOffsetY: 10,
        lineWidth: 2,
        arrowSize: 8,
        nodesep: 80,
        ranksep: 100,
        onNodeClick: (nodeId, currentNodes) => {
          const nodeData = currentNodes.find((n) => n.id === nodeId);
          if (nodeData && onNodeClick) {
            onNodeClick(nodeData);
          }
        },
      });

      graphRef.current = graph;

      graph
        .render()
        .then(() => {
          if (isMounted && graphRef.current) {
            setIsReady(true);
          }
        })
        .catch(() => {
          // 忽略因组件卸载导致的渲染错误
        });
    }, 100);

    return () => {
      isMounted = false;
      clearTimeout(initTimer);
      if (graphRef.current) {
        graphRef.current.destroy();
        graphRef.current = null;
      }
      setIsReady(false);
    };
    // edges 和 onNodeClick 在初始化时使用，不需要作为依赖
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen]);

  // 缩放控制函数
  const handleZoomIn = useCallback(() => {
    graphZoomIn(graphRef.current);
  }, []);

  const handleZoomOut = useCallback(() => {
    graphZoomOut(graphRef.current);
  }, []);

  const handleFitView = useCallback(() => {
    graphFitView(graphRef.current);
  }, []);

  // 阻止滚动
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-fade-in"
      onClick={onClose}
    >
      <div
        className="relative w-[95vw] h-[90vh] bg-white dark:bg-surface-900 rounded-2xl shadow-2xl overflow-hidden animate-scale-in"
        onClick={(e) => e.stopPropagation()}
      >
        {/* 标题栏 */}
        <div className="absolute top-0 left-0 right-0 z-10 flex items-center justify-between px-6 py-4 bg-linear-to-b from-white/95 to-white/80 dark:from-surface-900/95 dark:to-surface-900/80 backdrop-blur-sm border-b border-surface-200 dark:border-surface-700">
          <h2 className="text-xl font-bold text-surface-900 dark:text-surface-100">
            知识图谱全景
          </h2>
          <button
            type="button"
            onClick={onClose}
            className={cn(
              'p-2 rounded-lg text-surface-600 dark:text-surface-400 hover:bg-surface-100 dark:hover:bg-surface-800 hover:text-surface-900 dark:hover:text-surface-100',
              animationCombos.buttonHover
            )}
            title="关闭"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* 图谱容器 */}
        <div ref={containerRef} className="w-full h-full pt-16 pb-20" />

        {/* 工具栏 */}
        {isReady && (
          <GraphToolbar
            onZoomIn={handleZoomIn}
            onZoomOut={handleZoomOut}
            onFitView={handleFitView}
            className="absolute bottom-6 left-1/2 -translate-x-1/2"
            position="bottom"
          />
        )}
      </div>
    </div>,
    document.body
  );
};

/**
 * 知识图谱图例组件
 */
export const KnowledgeGraphLegend: React.FC = () => {
  return (
    <div className="space-y-4">
      {/* 节点类型 */}
      <div>
        <h4 className="text-sm font-medium text-surface-700 dark:text-surface-300 mb-2">
          节点类型
        </h4>
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded-full bg-primary-500" />
            <span className="text-sm text-surface-600 dark:text-surface-400">概念 (Concept)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rotate-45 bg-primary-500" />
            <span className="text-sm text-surface-600 dark:text-surface-400">定理 (Theorem)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-primary-500" />
            <span className="text-sm text-surface-600 dark:text-surface-400">方法 (Method)</span>
          </div>
        </div>
      </div>

      {/* 掌握度 */}
      <div>
        <h4 className="text-sm font-medium text-surface-700 dark:text-surface-300 mb-2">
          掌握度
        </h4>
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded-full bg-emerald-500" />
            <span className="text-sm text-surface-600 dark:text-surface-400">优秀 (≥80%)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded-full bg-primary-500" />
            <span className="text-sm text-surface-600 dark:text-surface-400">良好 (60-80%)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded-full bg-amber-500" />
            <span className="text-sm text-surface-600 dark:text-surface-400">一般 (40-60%)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded-full bg-red-500" />
            <span className="text-sm text-surface-600 dark:text-surface-400">较差 (&lt;40%)</span>
          </div>
        </div>
      </div>

      {/* 关系类型 */}
      <div>
        <h4 className="text-sm font-medium text-surface-700 dark:text-surface-300 mb-2">
          关系类型
        </h4>
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <div className="w-8 h-0.5 border-t-2 border-dashed border-surface-400" />
            <span className="text-sm text-surface-600 dark:text-surface-400">先修</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-8 h-0.5 bg-primary-500" />
            <span className="text-sm text-surface-600 dark:text-surface-400">应用</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-8 h-0.5 border-t-2 border-dotted border-purple-400" />
            <span className="text-sm text-surface-600 dark:text-surface-400">相关</span>
          </div>
        </div>
      </div>
    </div>
  );
};
