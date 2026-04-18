export const NODE_TYPE_OPTIONS = [
  { value: '', label: '全部类型' },
  { value: 'concept', label: '概念' },
  { value: 'theorem', label: '定理' },
  { value: 'method', label: '方法' },
  { value: 'problem', label: '习题' },
  { value: 'misconception', label: '迷思' },
  { value: 'resource', label: '资源' },
];

export const RELATION_TYPE_OPTIONS = [
  { value: 'has_prerequisite', label: '先修关系' },
  { value: 'is_a_special_case_of', label: '特例关系' },
  { value: 'used_in', label: '应用于' },
  { value: 'prone_to_error', label: '易错连接' },
  { value: 'related_to', label: '一般关联' },
];

export const INPUT_CLASS =
  'w-full px-3 py-2 rounded-lg border border-surface-300 dark:border-surface-600 bg-white dark:bg-surface-800 text-surface-900 dark:text-surface-100 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500';
