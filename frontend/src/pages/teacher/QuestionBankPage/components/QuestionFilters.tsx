import React from 'react';
import { Card, CardContent } from '../../../../components/ui/Card';
import { Input } from '../../../../components/ui/Input';
import { Select } from '../../../../components/ui/Select';
import { Button } from '../../../../components/ui/Button';
import { Search, Filter } from 'lucide-react';
import { difficultyOptions, typeOptions, statusOptions } from '../constants';

interface QuestionFiltersProps {
  searchTerm: string;
  onSearchChange: (value: string) => void;
  selectedDifficulty: string;
  onDifficultyChange: (value: string) => void;
  selectedType: string;
  onTypeChange: (value: string) => void;
  selectedStatus: string;
  onStatusChange: (value: string) => void;
  groups: string[];
  selectedGroup: string;
  onGroupChange: (value: string) => void;
  hasActiveFilters: boolean;
  onReset: () => void;
}

export const QuestionFilters: React.FC<QuestionFiltersProps> = ({
  searchTerm, onSearchChange,
  selectedDifficulty, onDifficultyChange,
  selectedType, onTypeChange,
  selectedStatus, onStatusChange,
  groups, selectedGroup, onGroupChange,
  hasActiveFilters, onReset,
}) => {
  const groupOptions = [
    { value: '', label: '全部分组' },
    ...groups.map((g) => ({ value: g, label: g })),
  ];

  return (
  <Card className="mb-6">
    <CardContent className="p-4">
      <div className="flex flex-col md:flex-row gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-surface-400" />
          <Input
            placeholder="搜索分组名或题目内容..."
            value={searchTerm}
            onChange={(e) => onSearchChange(e.target.value)}
            className="pl-10"
          />
        </div>
        <div className="flex gap-2 flex-wrap">
          <Select options={groupOptions} value={selectedGroup} onChange={onGroupChange} className="w-32" />
          <Select options={difficultyOptions} value={selectedDifficulty} onChange={onDifficultyChange} className="w-28" />
          <Select options={typeOptions} value={selectedType} onChange={onTypeChange} className="w-28" />
          <Select options={statusOptions} value={selectedStatus} onChange={onStatusChange} className="w-28" />
          <Button
            variant="outline"
            size="icon"
            onClick={onReset}
            disabled={!hasActiveFilters}
            className={hasActiveFilters ? 'border-primary-500 text-primary-500 hover:bg-primary-50 dark:hover:bg-primary-900/20' : ''}
            title="重置筛选条件"
          >
            <Filter className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </CardContent>
  </Card>
  );
};
