/**
 * 管理端知识点管理类型定义
 *
 * 定义知识节点和关系的 CRUD 接口数据结构
 */

// ========== 知识节点类型 ==========

/** 节点类型枚举值 */
export type AdminNodeType =
  | 'concept'
  | 'theorem'
  | 'method'
  | 'problem'
  | 'misconception'
  | 'resource';

/** 关系类型枚举值 */
export type AdminRelationType =
  | 'has_prerequisite'
  | 'is_a_special_case_of'
  | 'used_in'
  | 'prone_to_error'
  | 'related_to';

/** 管理端知识节点完整信息 */
export interface KnowledgeNodeAdmin {
  id: string;
  name: string;
  name_en: string | null;
  node_type: string;
  description: string;
  chapter: string | null;
  section: string | null;
  difficulty: number;
  latex_formula: string | null;
  tags: string[];
  created_at: string;
  updated_at: string;
}

/** 知识节点分页列表响应 */
export interface KnowledgeNodeListResponse {
  items: KnowledgeNodeAdmin[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

/** 创建知识节点请求数据 */
export interface KnowledgeNodeCreateData {
  name: string;
  name_en?: string;
  node_type: AdminNodeType;
  description?: string;
  chapter?: string;
  section?: string;
  difficulty?: number;
  latex_formula?: string;
  tags?: string[];
}

/** 更新知识节点请求数据 */
export interface KnowledgeNodeUpdateData {
  name?: string;
  name_en?: string;
  node_type?: AdminNodeType;
  description?: string;
  chapter?: string;
  section?: string;
  difficulty?: number;
  latex_formula?: string;
  tags?: string[];
}

/** 知识节点操作响应 */
export interface KnowledgeNodeResponse {
  success: boolean;
  message: string;
  node: KnowledgeNodeAdmin | null;
}

/** 删除响应 */
export interface KnowledgeDeleteResponse {
  success: boolean;
  message: string;
}

// ========== 知识关系类型 ==========

/** 管理端知识关系信息 */
export interface KnowledgeRelationAdmin {
  id: string;
  source_id: string;
  target_id: string;
  source_name: string | null;
  target_name: string | null;
  relation_type: string;
  weight: number;
  description: string | null;
  created_at: string;
}

/** 知识关系列表响应 */
export interface KnowledgeRelationListResponse {
  items: KnowledgeRelationAdmin[];
  total: number;
}

/** 创建知识关系请求数据 */
export interface KnowledgeRelationCreateData {
  source_id: string;
  target_id: string;
  relation_type: AdminRelationType;
  weight?: number;
  description?: string;
}

/** 更新知识关系请求数据 */
export interface KnowledgeRelationUpdateData {
  relation_type?: AdminRelationType;
  weight?: number;
  description?: string;
}

/** 知识关系操作响应 */
export interface KnowledgeRelationResponse {
  success: boolean;
  message: string;
  relation: KnowledgeRelationAdmin | null;
}

// ========== 公共类型 ==========

/** 简要节点信息（下拉选择和图谱视图用） */
export interface SimpleNode {
  id: string;
  name: string;
  chapter: string | null;
  node_type?: string | null;
}

/** 知识点统计数据 */
export interface KnowledgeStats {
  total_nodes: number;
  total_relations: number;
  chapters_count: number;
  type_distribution: Record<string, number>;
}

/** 章节列表响应 */
export interface ChapterListResponse {
  chapters: string[];
}

// ========== 节点类型和关系类型标签映射 ==========

/** 节点类型中文标签 */
export const NODE_TYPE_LABELS: Record<string, string> = {
  concept: '概念',
  theorem: '定理',
  method: '方法',
  problem: '习题',
  misconception: '迷思',
  resource: '资源',
};

/** 关系类型中文标签 */
export const RELATION_TYPE_LABELS: Record<string, string> = {
  has_prerequisite: '先修关系',
  is_a_special_case_of: '特例关系',
  used_in: '应用于',
  prone_to_error: '易错连接',
  related_to: '一般关联',
};
