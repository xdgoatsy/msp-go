import React from 'react';

interface ChannelAdvancedSettingsProps {
  description: string;
  onDescriptionChange: (value: string) => void;
}

export const ChannelAdvancedSettings: React.FC<ChannelAdvancedSettingsProps> = ({
  description,
  onDescriptionChange,
}) => (
  <div className="rounded-lg border border-surface-200 bg-surface-50/50 p-5 dark:border-surface-700 dark:bg-surface-900/40">
    <label className="mb-2 block text-sm font-medium text-surface-900 dark:text-surface-100">
      渠道备注
    </label>
    <textarea
      value={description}
      onChange={(event) => onDescriptionChange(event.target.value)}
      placeholder="可选，记录用途、环境或维护说明"
      rows={4}
      maxLength={500}
      className="w-full resize-y rounded-md border border-surface-200 bg-white px-3 py-3 text-sm leading-6 text-surface-900 outline-none transition-shadow placeholder:text-surface-400 focus:border-primary-400 focus:ring-2 focus:ring-primary-500/20 dark:border-surface-700 dark:bg-surface-800 dark:text-surface-100 dark:placeholder:text-surface-500"
    />
    <div className="mt-2 text-right text-xs text-surface-400">{description.length}/500</div>
  </div>
);
