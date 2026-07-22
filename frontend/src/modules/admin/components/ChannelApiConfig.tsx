import React from 'react';
import { KeyRound, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import type { CredentialMode, KeyStrategy } from './channelFormUtils';
import { parseCredentialKeys } from './channelFormUtils';

interface ChannelApiConfigProps {
  apiKey: string;
  baseUrl: string;
  credentialMode: CredentialMode;
  defaultBaseUrl: string;
  isEditMode: boolean;
  keyStrategy: KeyStrategy;
  onApiKeyChange: (value: string) => void;
  onBaseUrlChange: (value: string) => void;
  onCredentialModeChange: (value: CredentialMode) => void;
  onKeyStrategyChange: (value: KeyStrategy) => void;
}

const credentialModeOptions = [
  { value: 'single', label: '单密钥' },
  { value: 'batch', label: '批量添加（每行一个密钥）' },
  { value: 'multi', label: '多密钥模式（多个密钥，一个渠道）' },
];

export const ChannelApiConfig: React.FC<ChannelApiConfigProps> = ({
  apiKey,
  baseUrl,
  credentialMode,
  defaultBaseUrl,
  isEditMode,
  keyStrategy,
  onApiKeyChange,
  onBaseUrlChange,
  onCredentialModeChange,
  onKeyStrategyChange,
}) => {
  const isMultiple = credentialMode !== 'single';
  const keyCount = parseCredentialKeys(apiKey).length;

  const handleDeduplicate = () => {
    onApiKeyChange(parseCredentialKeys(apiKey).join('\n'));
  };

  return (
    <div className="rounded-lg border border-surface-200 bg-surface-50/50 p-5 dark:border-surface-700 dark:bg-surface-900/40">
      <div>
        <label className="mb-2 block text-sm font-medium text-surface-900 dark:text-surface-100">
          API 地址
        </label>
        <Input
          value={baseUrl}
          onChange={(event) => onBaseUrlChange(event.target.value)}
          placeholder={defaultBaseUrl ? `留空使用默认：${defaultBaseUrl}` : 'https://api.example.com'}
          className="h-11"
          inputMode="url"
          autoComplete="url"
        />
        <p className="mt-2 text-xs leading-5 text-surface-500 dark:text-surface-400">
          自定义 API 基础 URL。官方渠道已有内置地址，仅第三方代理或特殊端点需要填写；请勿添加 /v1 或尾部斜杠。
        </p>
      </div>

      <div className="mt-5 border-t border-surface-200 pt-5 dark:border-surface-700">
        <div className="mb-4 flex items-center gap-2 text-xs font-medium text-surface-500 dark:text-surface-400">
          <KeyRound className="h-4 w-4" aria-hidden="true" />
          <span>身份验证</span>
        </div>

        {!isEditMode && (
          <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <label className="text-xs font-medium text-surface-500 dark:text-surface-400">添加模式</label>
            <Select
              value={credentialMode}
              onChange={(value) => onCredentialModeChange(value as CredentialMode)}
              options={credentialModeOptions}
              className="h-10 w-full sm:w-80"
              aria-label="密钥添加模式"
            />
          </div>
        )}

        <div>
          <div className="mb-2 flex items-center justify-between gap-3">
            <label className="block text-sm font-medium text-surface-900 dark:text-surface-100">
              API 密钥 {!isEditMode && <span className="text-red-500">*</span>}
            </label>
            {isMultiple && keyCount > 0 && (
              <span className="text-xs text-surface-500 dark:text-surface-400">已识别 {keyCount} 个密钥</span>
            )}
          </div>
          <textarea
            value={apiKey}
            onChange={(event) => onApiKeyChange(event.target.value)}
            placeholder={
              isEditMode
                ? '输入新密钥以替换现有凭证，留空则保持不变'
                : isMultiple
                  ? '每行输入一个 API 密钥'
                  : '输入此渠道的 API 密钥'
            }
            rows={isMultiple ? 7 : 4}
            className="w-full resize-y rounded-md border border-surface-200 bg-white px-3 py-3 text-sm leading-6 text-surface-900 outline-none transition-shadow placeholder:text-surface-400 focus:border-primary-400 focus:ring-2 focus:ring-primary-500/20 dark:border-surface-700 dark:bg-surface-800 dark:text-surface-100 dark:placeholder:text-surface-500"
            autoComplete="new-password"
            spellCheck={false}
          />
          <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
            <p className="text-xs text-surface-500 dark:text-surface-400">
              {credentialMode === 'batch'
                ? '每个密钥会创建一个独立渠道，并自动为名称添加序号。'
                : credentialMode === 'multi'
                  ? '多个密钥会加密保存到同一渠道，并按策略轮换使用。'
                  : '来自提供商的 API 密钥。'}
            </p>
            {isMultiple && (
              <Button type="button" variant="ghost" size="sm" onClick={handleDeduplicate} disabled={!apiKey.trim()}>
                <Trash2 className="mr-1.5 h-4 w-4" aria-hidden="true" />
                去除重复项
              </Button>
            )}
          </div>
        </div>

        {credentialMode === 'multi' && !isEditMode && (
          <div className="mt-4 flex flex-col gap-2 border-t border-surface-200 pt-4 sm:flex-row sm:items-center sm:justify-between dark:border-surface-700">
            <div>
              <div className="text-sm font-medium text-surface-900 dark:text-surface-100">密钥选择策略</div>
              <div className="mt-0.5 text-xs text-surface-500 dark:text-surface-400">控制每次请求如何选择密钥</div>
            </div>
            <Select
              value={keyStrategy}
              onChange={(value) => onKeyStrategyChange(value as KeyStrategy)}
              className="h-10 w-full sm:w-48"
              aria-label="密钥选择策略"
              options={[
                { value: 'round_robin', label: '轮询' },
                { value: 'random', label: '随机' },
              ]}
            />
          </div>
        )}
      </div>
    </div>
  );
};
