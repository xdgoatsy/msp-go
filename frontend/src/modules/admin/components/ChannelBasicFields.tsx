/**
 * 渠道基础字段组件
 *
 * 包含：提供商类型选择、名称、密钥、描述
 */

import React from 'react';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { PROVIDER_PRESETS } from '../constants/providerPresets';

interface ChannelBasicFieldsProps {
  providerType: string;
  name: string;
  apiKey: string;
  description: string;
  isEditMode: boolean;
  onProviderTypeChange: (value: string) => void;
  onNameChange: (value: string) => void;
  onApiKeyChange: (value: string) => void;
  onDescriptionChange: (value: string) => void;
}

export const ChannelBasicFields: React.FC<ChannelBasicFieldsProps> = ({
  providerType,
  name,
  apiKey,
  description,
  isEditMode,
  onProviderTypeChange,
  onNameChange,
  onApiKeyChange,
  onDescriptionChange,
}) => {
  return (
    <>
      {/* 提供商类型 */}
      <div>
        <Select
          value={providerType}
          onChange={onProviderTypeChange}
          disabled={isEditMode}
          className="w-full"
          options={PROVIDER_PRESETS.map((p) => ({
            value: p.code,
            label: p.name,
          }))}
        />
      </div>

      {/* 名称 */}
      <div>
        <label className="block text-sm font-medium text-surface-900 dark:text-surface-100 mb-2">
          名称 <span className="text-red-500">*</span>
        </label>
        <Input
          value={name}
          onChange={(e) => onNameChange(e.target.value)}
          placeholder="请为渠道命名"
          className="w-full"
        />
      </div>

      {/* 密钥 */}
      <div>
        <label className="block text-sm font-medium text-surface-900 dark:text-surface-100 mb-2">
          密钥 <span className="text-red-500">*</span>
        </label>
        <Input
          type="password"
          value={apiKey}
          onChange={(e) => onApiKeyChange(e.target.value)}
          placeholder={isEditMode ? '留空则不修改' : '请输入渠道对应的鉴权密钥'}
          className="w-full"
        />
      </div>

      {/* 描述 */}
      <div>
        <label className="block text-sm font-medium text-surface-900 dark:text-surface-100 mb-2">
          描述
        </label>
        <Input
          value={description}
          onChange={(e) => onDescriptionChange(e.target.value)}
          placeholder="可选，渠道描述信息"
          className="w-full"
        />
      </div>
    </>
  );
};
