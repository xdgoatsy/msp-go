/**
 * 管理端知识点管理 API 服务
 *
 * 提供知识节点和关系的 CRUD 操作
 * 使用请求去重机制避免重复调用
 */

import { apiClient } from '@/libs/http/apiClient';
import { logger } from '@/libs/utils/logger';
import { requestDeduplication } from '@/libs/utils/requestDeduplication';
import type {
  ChapterListResponse,
  KnowledgeDeleteResponse,
  KnowledgeNodeAdmin,
  KnowledgeNodeCreateData,
  KnowledgeNodeListResponse,
  KnowledgeNodeResponse,
  KnowledgeNodeUpdateData,
  KnowledgeRelationCreateData,
  KnowledgeRelationListResponse,
  KnowledgeRelationResponse,
  KnowledgeRelationUpdateData,
  KnowledgeStats,
  SimpleNode,
} from '@/modules/admin/types/knowledgeAdmin';

const knowledgeAdminLogger = logger.createContextLogger('KnowledgeAdmin');
const BASE_PATH = '/admin/knowledge';

export const knowledgeAdminService = {
  // ========== 统计和元数据 ==========

  /** 获取知识点统计数据（带去重） */
  async getStats(): Promise<KnowledgeStats> {
    return requestDeduplication.dedupe(
      `${BASE_PATH}/stats`,
      async () => {
        const response = await apiClient.get<KnowledgeStats>(`${BASE_PATH}/stats`);
        return response.data;
      }
    );
  },

  /** 获取章节列表（带去重） */
  async getChapters(): Promise<string[]> {
    return requestDeduplication.dedupe(
      `${BASE_PATH}/chapters`,
      async () => {
        const response = await apiClient.get<ChapterListResponse>(`${BASE_PATH}/chapters`);
        return response.data.chapters;
      }
    );
  },

  /** 获取所有节点简要信息（下拉选择用，带去重） */
  async getAllNodesSimple(): Promise<SimpleNode[]> {
    return requestDeduplication.dedupe(
      `${BASE_PATH}/nodes/all`,
      async () => {
        const response = await apiClient.get<SimpleNode[]>(`${BASE_PATH}/nodes/all`);
        return response.data;
      }
    );
  },

  // ========== 知识节点 CRUD ==========

  /** 分页查询知识节点列表（带去重） */
  async listNodes(params: {
    page?: number;
    page_size?: number;
    chapter?: string;
    type?: string;
    search?: string;
  } = {}): Promise<KnowledgeNodeListResponse> {
    return requestDeduplication.dedupe(
      `${BASE_PATH}/nodes`,
      async () => {
        const response = await apiClient.get<KnowledgeNodeListResponse>(
          `${BASE_PATH}/nodes`,
          { params },
        );
        knowledgeAdminLogger.info('知识节点列表获取成功', {
          total: response.data.total,
        });
        return response.data;
      },
      params
    );
  },

  /** 获取单个知识节点（带去重） */
  async getNode(nodeId: string): Promise<KnowledgeNodeAdmin> {
    return requestDeduplication.dedupe(
      `${BASE_PATH}/nodes/${nodeId}`,
      async () => {
        const response = await apiClient.get<KnowledgeNodeAdmin>(
          `${BASE_PATH}/nodes/${nodeId}`,
        );
        return response.data;
      }
    );
  },

  /** 创建知识节点 */
  async createNode(data: KnowledgeNodeCreateData): Promise<KnowledgeNodeResponse> {
    const response = await apiClient.post<KnowledgeNodeResponse>(
      `${BASE_PATH}/nodes`,
      data,
    );
    knowledgeAdminLogger.info('知识节点创建成功', { name: data.name });
    // 清除相关缓存
    requestDeduplication.clearByUrl(`${BASE_PATH}/stats`);
    requestDeduplication.clearByUrl(`${BASE_PATH}/nodes`);
    requestDeduplication.clearByUrl(`${BASE_PATH}/chapters`);
    return response.data;
  },

  /** 更新知识节点 */
  async updateNode(
    nodeId: string,
    data: KnowledgeNodeUpdateData,
  ): Promise<KnowledgeNodeResponse> {
    const response = await apiClient.put<KnowledgeNodeResponse>(
      `${BASE_PATH}/nodes/${nodeId}`,
      data,
    );
    knowledgeAdminLogger.info('知识节点更新成功', { nodeId });
    // 清除相关缓存
    requestDeduplication.clearByUrl(`${BASE_PATH}/stats`);
    requestDeduplication.clearByUrl(`${BASE_PATH}/nodes`);
    requestDeduplication.clearByUrl(`${BASE_PATH}/chapters`);
    return response.data;
  },

  /** 删除知识节点 */
  async deleteNode(nodeId: string): Promise<KnowledgeDeleteResponse> {
    const response = await apiClient.delete<KnowledgeDeleteResponse>(
      `${BASE_PATH}/nodes/${nodeId}`,
    );
    knowledgeAdminLogger.info('知识节点删除成功', { nodeId });
    // 清除相关缓存
    requestDeduplication.clearByUrl(`${BASE_PATH}/stats`);
    requestDeduplication.clearByUrl(`${BASE_PATH}/nodes`);
    requestDeduplication.clearByUrl(`${BASE_PATH}/relations`);
    return response.data;
  },

  // ========== 知识关系 CRUD ==========

  /** 查询知识关系列表（带去重） */
  async listRelations(nodeId?: string): Promise<KnowledgeRelationListResponse> {
    const params = nodeId ? { node_id: nodeId } : {};
    return requestDeduplication.dedupe(
      `${BASE_PATH}/relations`,
      async () => {
        const response = await apiClient.get<KnowledgeRelationListResponse>(
          `${BASE_PATH}/relations`,
          { params },
        );
        return response.data;
      },
      params
    );
  },

  /** 创建知识关系 */
  async createRelation(
    data: KnowledgeRelationCreateData,
  ): Promise<KnowledgeRelationResponse> {
    const response = await apiClient.post<KnowledgeRelationResponse>(
      `${BASE_PATH}/relations`,
      data,
    );
    knowledgeAdminLogger.info('知识关系创建成功');
    // 清除相关缓存
    requestDeduplication.clearByUrl(`${BASE_PATH}/stats`);
    requestDeduplication.clearByUrl(`${BASE_PATH}/relations`);
    return response.data;
  },

  /** 更新知识关系 */
  async updateRelation(
    relationId: string,
    data: KnowledgeRelationUpdateData,
  ): Promise<KnowledgeRelationResponse> {
    const response = await apiClient.put<KnowledgeRelationResponse>(
      `${BASE_PATH}/relations/${relationId}`,
      data,
    );
    knowledgeAdminLogger.info('知识关系更新成功', { relationId });
    // 清除相关缓存
    requestDeduplication.clearByUrl(`${BASE_PATH}/stats`);
    requestDeduplication.clearByUrl(`${BASE_PATH}/relations`);
    return response.data;
  },

  /** 删除知识关系 */
  async deleteRelation(relationId: string): Promise<KnowledgeDeleteResponse> {
    const response = await apiClient.delete<KnowledgeDeleteResponse>(
      `${BASE_PATH}/relations/${relationId}`,
    );
    knowledgeAdminLogger.info('知识关系删除成功', { relationId });
    // 清除相关缓存
    requestDeduplication.clearByUrl(`${BASE_PATH}/stats`);
    requestDeduplication.clearByUrl(`${BASE_PATH}/relations`);
    return response.data;
  },
};

export default knowledgeAdminService;
