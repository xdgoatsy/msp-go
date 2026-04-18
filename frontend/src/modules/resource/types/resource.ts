/**
 * 资源类型定义
 */

// 资源类型
export type ResourceType = 'video' | 'document';

// 存储类型
export type StorageType = 'local' | 'cloud' | 'external';

// 资源接口
export interface Resource {
  id: string;
  title: string;
  type: ResourceType;
  body: string;
  chapter: string | null;
  topic: string | null;
  tags: string[];
  difficulty: number;
  source: string | null;

  // 附件信息
  url: string | null;
  storage_type: StorageType | null;
  duration: string | null;
  pages: number | null;

  // 统计信息
  views: number;
  likes: number;

  // 收藏状态
  is_favorite: boolean;

  // 创建者信息
  owner_id: string;
  owner_name: string | null;

  // 时间戳
  created_at: string;
  updated_at: string;
}

// 资源筛选参数
export interface ResourceFilter {
  type?: ResourceType;
  chapter?: string;
  topic?: string;
  search?: string;
  favorites_only?: boolean;
  page?: number;
  page_size?: number;
}

// 资源列表响应
export interface ResourceListResponse {
  items: Resource[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

// 资源统计
export interface ResourceStats {
  total: number;
  videos: number;
  documents: number;
  favorites: number;
}

// 创建资源请求
export interface ResourceCreateRequest {
  title: string;
  type: ResourceType;
  body?: string;
  chapter?: string;
  topic?: string;
  tags?: string[];
  difficulty?: number;
  storage_type?: StorageType;
  url?: string;
  duration?: string;
  pages?: number;
  source?: string;
}

// 更新资源请求
export interface ResourceUpdateRequest {
  title?: string;
  type?: ResourceType;
  body?: string;
  chapter?: string;
  topic?: string;
  tags?: string[];
  difficulty?: number;
  storage_type?: StorageType;
  url?: string;
  duration?: string;
  pages?: number;
  source?: string;
}

// 收藏切换响应
export interface FavoriteToggleResponse {
  resource_id: string;
  is_favorite: boolean;
  message: string;
}

// 批量导入项
export interface BatchImportItem {
  id: string;           // 临时 ID
  url: string;
  title: string;        // 自动识别
  type: ResourceType;   // 自动识别
  source: string;       // 自动识别
  selected: boolean;
}
