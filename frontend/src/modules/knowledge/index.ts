/**
 * Knowledge 模块 - 知识图谱
 */

// Components
export {
  KnowledgeGraph,
  KnowledgeGraphModal,
  KnowledgeGraphLegend,
} from './components/KnowledgeGraph';

export type {
  KnowledgeNode,
  KnowledgeEdge,
  KnowledgeGraphProps,
  KnowledgeGraphModalProps,
} from './components/KnowledgeGraph';

// Services
export { default as knowledgeService } from './services/knowledgeService';

// Store
export { default as knowledgeReducer } from './store/knowledgeSlice';
