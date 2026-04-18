import React from 'react';
import { AlertCircle } from 'lucide-react';
import { cn } from '../../libs/utils/cn';

export interface FormErrorProps {
  /** Error message to display */
  message?: string;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Form field error message component
 *
 * Displays validation error messages with consistent styling
 */
export const FormError: React.FC<FormErrorProps> = ({ message, className }) => {
  if (!message) return null;

  return (
    <p
      className={cn(
        'flex items-center gap-1.5 text-sm text-red-500 dark:text-red-400 mt-1.5',
        className
      )}
      role="alert"
    >
      <AlertCircle className="w-3.5 h-3.5 shrink-0" />
      <span>{message}</span>
    </p>
  );
};

export interface FormFieldProps {
  /** Field label */
  label: string;
  /** Field name for accessibility */
  name: string;
  /** Whether the field is required */
  required?: boolean;
  /** Error message */
  error?: string;
  /** Helper text */
  helperText?: string;
  /** Label icon */
  icon?: React.ReactNode;
  /** Children (input element) */
  children: React.ReactNode;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Form field wrapper component
 *
 * Provides consistent layout for form fields with label, input, and error message
 */
export const FormField: React.FC<FormFieldProps> = ({
  label,
  name,
  required = false,
  error,
  helperText,
  icon,
  children,
  className,
}) => {
  return (
    <div className={cn('space-y-2', className)}>
      <label
        htmlFor={name}
        className="text-sm font-medium text-surface-700 dark:text-surface-300 flex items-center gap-2"
      >
        {icon}
        {label}
        {required && <span className="text-red-500">*</span>}
      </label>
      {children}
      {error ? (
        <FormError message={error} />
      ) : helperText ? (
        <p className="text-xs text-surface-500 dark:text-surface-400 mt-1">
          {helperText}
        </p>
      ) : null}
    </div>
  );
};

