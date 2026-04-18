import * as React from 'react';
import { cn } from '../../libs/utils/cn';
import { ChevronDown } from 'lucide-react';
import { animationCombos } from '../../libs/animations';

export interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

export interface SelectProps extends Omit<React.SelectHTMLAttributes<HTMLSelectElement>, 'onChange'> {
  options: SelectOption[];
  placeholder?: string;
  onChange?: (value: string) => void;
}

const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, options, placeholder, onChange, value, ...props }, ref) => {
    const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
      onChange?.(e.target.value);
    };

    return (
      <div className="relative">
        <select
          ref={ref}
          value={value}
          onChange={handleChange}
          className={cn(
            'flex h-10 w-full appearance-none rounded-md border border-surface-200 bg-white px-3 py-2 pr-10 text-sm ring-offset-white',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2',
            'disabled:cursor-not-allowed disabled:opacity-50',
            'dark:border-surface-700 dark:bg-surface-800 dark:text-surface-100 dark:ring-offset-surface-900',
            animationCombos.inputFocus,
            className
          )}
          {...props}
        >
          {placeholder && (
            <option value="" disabled>
              {placeholder}
            </option>
          )}
          {options.map((option) => (
            <option key={option.value} value={option.value} disabled={option.disabled}>
              {option.label}
            </option>
          ))}
        </select>
        <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-surface-500 dark:text-surface-400" />
      </div>
    );
  }
);
Select.displayName = 'Select';

export { Select };
