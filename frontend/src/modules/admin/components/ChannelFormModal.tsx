/**
 * 渠道表单 Modal
 *
 * 用于创建和编辑 AI 渠道（提供商 + 模型）
 * 参考设计：一体化配置提供商信息和模型列表
 */

import React, { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { getProviderPreset } from '../constants/providerPresets';
import { aiConfigService } from '@/modules/ai-config/services/aiConfigService';
import type {
  LLMProvider,
  CreateProviderWithModelsRequest,
  UpdateProviderRequest,
  ModelCreateSimple,
  FetchModelsResponse,
  ModelsUpdateResponse,
} from '@/modules/ai-config/types/aiConfig';
import { ChannelBasicFields } from './ChannelBasicFields';
import { ChannelApiConfig } from './ChannelApiConfig';
import { ChannelModelSelector } from './ChannelModelSelector';
import { ChannelFormActions } from './ChannelFormActions';

interface ChannelFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: CreateProviderWithModelsRequest) => Promise<void>;
  onUpdate?: (id: string, data: UpdateProviderRequest) => Promise<void>;
  onUpdateModels?: (providerId: string, models: ModelCreateSimple[]) => Promise<ModelsUpdateResponse>;
  onFetchModels?: (providerId: string) => Promise<FetchModelsResponse>;
  editingProvider?: LLMProvider | null;
  existingModels?: string[];
}

export const ChannelFormModal: React.FC<ChannelFormModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  onUpdate,
  onUpdateModels,
  onFetchModels,
  editingProvider,
  existingModels = [],
}) => {
  // 表单状态
  const [providerType, setProviderType] = useState('openai');
  const [name, setName] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [baseUrl, setBaseUrl] = useState('');
  const [description, setDescription] = useState('');
  const [selectedModels, setSelectedModels] = useState<string[]>([]);
  const [customModel, setCustomModel] = useState('');
  const [availableModels, setAvailableModels] = useState<string[]>([]);

  // UI 状态
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isFetchingModels, setIsFetchingModels] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 是否编辑模式
  const isEditMode = !!editingProvider;

  // 初始化表单
  useEffect(() => {
    if (isOpen) {
      if (editingProvider) {
        // 编辑模式：填充现有数据
        setProviderType(editingProvider.code);
        setName(editingProvider.name);
        setApiKey(''); // API Key 不回显
        setBaseUrl(editingProvider.base_url);
        setDescription(editingProvider.description || '');
        setSelectedModels(existingModels);
        setAvailableModels([]);
      } else {
        // 新建模式：重置表单
        resetForm();
      }
      setError(null);
    }
  }, [isOpen, editingProvider, existingModels]);

  // 提供商类型变化时更新默认 Base URL
  useEffect(() => {
    if (!isEditMode) {
      const preset = getProviderPreset(providerType);
      if (preset) {
        setBaseUrl(preset.defaultBaseUrl);
      }
    }
  }, [providerType, isEditMode]);

  // 重置表单
  const resetForm = () => {
    setProviderType('openai');
    setName('');
    setApiKey('');
    const preset = getProviderPreset('openai');
    setBaseUrl(preset?.defaultBaseUrl || '');
    setDescription('');
    setSelectedModels([]);
    setCustomModel('');
    setAvailableModels([]);
  };

  // 获取模型列表（从 API）
  const handleFetchModels = async () => {
    // 新建模式：使用表单中的凭据
    // 编辑模式：使用已保存的提供商 ID
    if (!isEditMode && (!baseUrl.trim() || !apiKey.trim())) {
      setError('请先填写 API 地址和密钥');
      return;
    }

    setIsFetchingModels(true);
    setError(null);
    try {
      let result;
      if (isEditMode && editingProvider && onFetchModels) {
        // 编辑模式：使用已保存的提供商
        result = await onFetchModels(editingProvider.id);
      } else {
        // 新建模式：使用表单中的凭据
        result = await aiConfigService.fetchModelsByCredentials(baseUrl.trim(), apiKey.trim());
      }

      if (result.success && result.models.length > 0) {
        setAvailableModels(result.models);
      } else {
        setError(result.message || '获取模型列表失败');
      }
    } catch {
      setError('获取模型列表失败');
    } finally {
      setIsFetchingModels(false);
    }
  };

  // 清除所有模型
  const handleClearModels = () => {
    setSelectedModels([]);
  };

  // 添加单个模型（自动去重）
  const handleAddModel = (model: string) => {
    if (!selectedModels.includes(model)) {
      setSelectedModels([...selectedModels, model]);
    }
  };

  // 添加所有可用模型（自动去重）
  const handleAddAllModels = () => {
    const newModels = availableModels.filter((m) => !selectedModels.includes(m));
    if (newModels.length > 0) {
      setSelectedModels([...selectedModels, ...newModels]);
    }
  };

  // 添加自定义模型
  const handleAddCustomModel = () => {
    const trimmed = customModel.trim();
    if (trimmed && !selectedModels.includes(trimmed)) {
      setSelectedModels([...selectedModels, trimmed]);
      setCustomModel('');
    }
  };

  // 移除模型
  const handleRemoveModel = (model: string) => {
    setSelectedModels(selectedModels.filter((m) => m !== model));
  };

  // 提交表单
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // 验证
    if (!name.trim()) {
      setError('请输入渠道名称');
      return;
    }
    if (!isEditMode && !apiKey.trim()) {
      setError('请输入 API 密钥');
      return;
    }
    if (!baseUrl.trim()) {
      setError('请输入 API 地址');
      return;
    }
    if (selectedModels.length === 0) {
      setError('请至少选择一个模型');
      return;
    }

    setIsSubmitting(true);
    try {
      if (isEditMode && onUpdate && editingProvider) {
        // 更新模式：先更新提供商信息
        await onUpdate(editingProvider.id, {
          name: name.trim(),
          base_url: baseUrl.trim(),
          api_key: apiKey.trim() || undefined,
          description: description.trim() || undefined,
        });

        // 然后更新模型列表（如果有变化）
        if (onUpdateModels) {
          const models: ModelCreateSimple[] = selectedModels.map((modelId) => ({
            model_id: modelId,
          }));
          await onUpdateModels(editingProvider.id, models);
        }
      } else {
        // 创建模式
        const models: ModelCreateSimple[] = selectedModels.map((modelId) => ({
          model_id: modelId,
        }));

        await onSubmit({
          name: name.trim(),
          code: providerType,
          base_url: baseUrl.trim(),
          api_key: apiKey.trim(),
          description: description.trim() || undefined,
          models,
        });
      }
      onClose();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : '操作失败';
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* 遮罩层 */}
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />

      {/* Modal 内容 */}
      <div className="relative bg-white dark:bg-surface-800 rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden">
        {/* 标题栏 */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-surface-200 dark:border-surface-700">
          <div className="flex items-center gap-3">
            <Badge variant="default" className="text-xs">
              {isEditMode ? '编辑' : '新建'}
            </Badge>
            <h2 className="text-xl font-semibold text-surface-900 dark:text-surface-100">
              {isEditMode ? '编辑渠道' : '创建新的渠道'}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-surface-100 dark:hover:bg-surface-700 transition-colors"
          >
            <X className="w-5 h-5 text-surface-500" />
          </button>
        </div>

        {/* 表单内容 */}
        <form onSubmit={handleSubmit} className="overflow-y-auto max-h-[calc(90vh-140px)]">
          <div className="p-6 space-y-6">
            {/* 错误提示 */}
            {error && (
              <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-600 dark:text-red-400 text-sm">
                {error}
              </div>
            )}

            <ChannelBasicFields
              providerType={providerType}
              name={name}
              apiKey={apiKey}
              description={description}
              isEditMode={isEditMode}
              onProviderTypeChange={setProviderType}
              onNameChange={setName}
              onApiKeyChange={setApiKey}
              onDescriptionChange={setDescription}
            />

            <ChannelApiConfig
              baseUrl={baseUrl}
              onBaseUrlChange={setBaseUrl}
            />

            <ChannelModelSelector
              selectedModels={selectedModels}
              availableModels={availableModels}
              customModel={customModel}
              isFetchingModels={isFetchingModels}
              canFetchModels={isEditMode || (!!baseUrl.trim() && !!apiKey.trim())}
              onFetchModels={handleFetchModels}
              onClearModels={handleClearModels}
              onAddModel={handleAddModel}
              onAddAllModels={handleAddAllModels}
              onRemoveModel={handleRemoveModel}
              onCustomModelChange={setCustomModel}
              onAddCustomModel={handleAddCustomModel}
            />
          </div>

          <ChannelFormActions
            isEditMode={isEditMode}
            isSubmitting={isSubmitting}
            onClose={onClose}
          />
        </form>
      </div>
    </div>
  );
};

export default ChannelFormModal;
