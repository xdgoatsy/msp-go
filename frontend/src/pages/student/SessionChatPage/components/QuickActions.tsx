import React from 'react';
import { Button } from '../../../../components/ui/Button';
import type { QuickAction } from '../constants.tsx';

interface QuickActionsProps {
  actions: QuickAction[];
  onActionClick: (prompt: string) => void;
}

export const QuickActions = React.memo<QuickActionsProps>(({ actions, onActionClick }) => {
  return (
    <div className="px-6 py-4">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {actions.map((action) => (
          <Button
            key={action.prompt}
            variant="outline"
            size="sm"
            onClick={() => onActionClick(action.prompt)}
            className="flex items-center gap-2 justify-start"
          >
            {action.icon}
            <span className="text-xs">{action.label}</span>
          </Button>
        ))}
      </div>
    </div>
  );
});

QuickActions.displayName = 'QuickActions';
