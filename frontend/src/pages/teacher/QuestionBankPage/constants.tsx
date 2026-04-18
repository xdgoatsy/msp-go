import React from 'react';
import { Badge } from '../../../components/ui/Badge';

export const difficultyOptions = [
  { value: '', label: '全部难度' },
  { value: 'easy', label: '简单' },
  { value: 'medium', label: '中等' },
  { value: 'hard', label: '困难' },
];

export const typeOptions = [
  { value: '', label: '全部题型' },
  { value: 'short_answer', label: '简答题' },
  { value: 'multiple_choice', label: '选择题' },
  { value: 'proof', label: '证明题' },
];

export const statusOptions = [
  { value: '', label: '全部状态' },
  { value: 'draft', label: '草稿' },
  { value: 'published', label: '已发布' },
  { value: 'archived', label: '已归档' },
];

export const getDifficultyBadge = (difficulty: number) => {
  if (difficulty < 0.33) {
    return React.createElement(Badge, { variant: 'success' }, '简单');
  } else if (difficulty < 0.67) {
    return React.createElement(Badge, { variant: 'warning' }, '中等');
  } else {
    return React.createElement(Badge, { variant: 'destructive' }, '困难');
  }
};

export const getTypeBadge = (type: string) => {
  switch (type) {
    case 'short_answer':
      return React.createElement(Badge, { variant: 'default' }, '简答');
    case 'multiple_choice':
      return React.createElement(Badge, { variant: 'secondary' }, '选择');
    case 'proof':
      return React.createElement(Badge, { variant: 'outline' }, '证明');
    default:
      return React.createElement(Badge, { variant: 'outline' }, type);
  }
};

export const getStatusBadge = (status: string) => {
  switch (status) {
    case 'published':
      return React.createElement(Badge, { variant: 'success' }, '已发布');
    case 'draft':
      return React.createElement(Badge, { variant: 'warning' }, '草稿');
    case 'archived':
      return React.createElement(Badge, { variant: 'secondary' }, '已归档');
    default:
      return React.createElement(Badge, { variant: 'outline' }, status);
  }
};
