/**
 * 渠道 API 配置组件
 *
 * 包含：API 地址输入
 */

import React from 'react';
import { Link2 } from 'lucide-react';
import { Input } from '@/components/ui/Input';

interface ChannelApiConfigProps {
  baseUrl: string;
  onBaseUrlChange: (value: string) => void;
}

export const ChannelApiConfig: React.FC<ChannelApiConfigProps> = ({
  baseUrl,
  onBaseUrlChange,
}) => {
  return (
    <div className="bg-surface-50 dark:bg-surface-900 rounded-xl p-4 space-y-4">
      <div className="flex items-center gap-3">
        <div className="p-2 bg-primary-100 dark:bg-primary-900/30 rounded-lg">
          <Link2 className="w-4 h-4 text-primary-600 dark:text-primary-400" />
        </div>
        <div>
          <h3 className="font-medium text-surface-900 dark:text-surface-100">API 配置</h3>
          <p className="text-xs text-surface-500 dark:text-surface-400">API 地址和相关配置</p>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-surface-900 dark:text-surface-100 mb-2">
          API 地址
        </label>
        <Input
          value={baseUrl}
          onChange={(e) => onBaseUrlChange(e.target.value)}
          placeholder="此项可选，用于通过自定义API地址来进行 API 调用，末尾不要带/v1和/"
          className="w-full"
        />
        <p className="text-xs text-surface-500 dark:text-surface-400 mt-1">
          对于官方渠道，已经内置地址，除非是第三方代理站点或者Azure的特殊接入地址，否则不需要填写
        </p>
      </div>
    </div>
  );
};
