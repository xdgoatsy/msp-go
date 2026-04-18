/**
 * 知识图谱相关类型定义
 */

/**
 * 知识节点类型
 */
export type KnowledgeNodeType = 'concept' | 'theorem' | 'method';

/**
 * 知识关系类型
 */
export type KnowledgeRelationType = 'prerequisite' | 'used_in' | 'related';

/**
 * 知识节点
 */
export interface KnowledgeNode {
  id: string;
  label: string;
  type: KnowledgeNodeType;
  mastery: number; // 0-1
  chapter?: string;
  description?: string;
}

/**
 * 知识关系边
 */
export interface KnowledgeEdge {
  source: string;
  target: string;
  relation: KnowledgeRelationType;
}

/**
 * 知识图谱统计信息
 */
export interface KnowledgeGraphStatistics {
  total_nodes: number;
  mastered_nodes: number;
  overall_mastery: number;
}

/**
 * 知识图谱数据
 */
export interface KnowledgeGraphData {
  nodes: KnowledgeNode[];
  edges: KnowledgeEdge[];
  statistics: KnowledgeGraphStatistics;
}

/**
 * 知识图谱筛选条件
 */
export interface KnowledgeGraphFilters {
  chapter?: string;
  type?: KnowledgeNodeType;
  search?: string;
}

/**
 * 知识图谱 API 响应
 */
export interface KnowledgeGraphResponse {
  nodes: KnowledgeNode[];
  edges: KnowledgeEdge[];
  statistics: KnowledgeGraphStatistics;
}
