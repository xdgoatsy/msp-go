import * as React from 'react';
import { cn } from '../../libs/utils/cn';
import { animationCombos } from '../../libs/animations';

interface TabsContextValue {
  activeTab: string;
  setActiveTab: (value: string) => void;
  keepMounted: boolean;
  baseId: string;
}

const TabsContext = React.createContext<TabsContextValue | undefined>(undefined);

const useTabsContext = () => {
  const context = React.useContext(TabsContext);
  if (!context) {
    throw new Error('Tabs components must be used within a Tabs provider');
  }
  return context;
};

export interface TabsProps extends React.HTMLAttributes<HTMLDivElement> {
  defaultValue: string;
  value?: string;
  onValueChange?: (value: string) => void;
  keepMounted?: boolean;
}

const Tabs = React.forwardRef<HTMLDivElement, TabsProps>(
  (
    {
      className,
      defaultValue,
      value,
      onValueChange,
      keepMounted = true,
      children,
      ...props
    },
    ref
  ) => {
    const [internalValue, setInternalValue] = React.useState(defaultValue);
    const activeTab = value ?? internalValue;
    const baseId = React.useId();

    const setActiveTab = React.useCallback(
      (newValue: string) => {
        if (newValue === activeTab) return;

        React.startTransition(() => {
          if (value === undefined) {
            setInternalValue(newValue);
          }
          onValueChange?.(newValue);
        });
      },
      [activeTab, value, onValueChange]
    );

    const contextValue = React.useMemo(
      () => ({
        activeTab,
        setActiveTab,
        keepMounted,
        baseId,
      }),
      [activeTab, setActiveTab, keepMounted, baseId]
    );

    return (
      <TabsContext.Provider value={contextValue}>
        <div ref={ref} className={cn('w-full', className)} {...props}>
          {children}
        </div>
      </TabsContext.Provider>
    );
  }
);
Tabs.displayName = 'Tabs';

const TabsList = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      role="tablist"
      className={cn(
        'inline-flex h-10 items-center justify-center rounded-md bg-surface-100 p-1 text-surface-500',
        'dark:bg-surface-800 dark:text-surface-400',
        className
      )}
      {...props}
    />
  )
);
TabsList.displayName = 'TabsList';

const sanitizeTabId = (value: string): string => value.replace(/[^a-zA-Z0-9_-]/g, '-');

const buildTabId = (baseId: string, value: string): string => `${baseId}-tab-${sanitizeTabId(value)}`;

const buildPanelId = (baseId: string, value: string): string => `${baseId}-panel-${sanitizeTabId(value)}`;

export interface TabsTriggerProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  value: string;
}

const TabsTrigger = React.forwardRef<HTMLButtonElement, TabsTriggerProps>(
  ({ className, value, ...props }, ref) => {
    const { activeTab, setActiveTab, baseId } = useTabsContext();
    const isActive = activeTab === value;
    const tabId = buildTabId(baseId, value);
    const panelId = buildPanelId(baseId, value);

    return (
      <button
        ref={ref}
        type="button"
        role="tab"
        id={tabId}
        aria-controls={panelId}
        aria-selected={isActive}
        data-state={isActive ? 'active' : 'inactive'}
        onClick={() => setActiveTab(value)}
        className={cn(
          'inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium ring-offset-white',
          animationCombos.buttonHover,
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2',
          'disabled:pointer-events-none disabled:opacity-50',
          isActive
            ? 'bg-white text-surface-950 shadow-sm dark:bg-surface-900 dark:text-surface-50'
            : 'text-surface-500 hover:text-surface-900 dark:text-surface-400 dark:hover:text-surface-50',
          className
        )}
        {...props}
      />
    );
  }
);
TabsTrigger.displayName = 'TabsTrigger';

export interface TabsContentProps extends React.HTMLAttributes<HTMLDivElement> {
  value: string;
  forceMount?: boolean;
}

const TabsContent = React.forwardRef<HTMLDivElement, TabsContentProps>(
  ({ className, value, forceMount = false, ...props }, ref) => {
    const { activeTab, keepMounted, baseId } = useTabsContext();
    const isActive = activeTab === value;
    const [hasBeenActive, setHasBeenActive] = React.useState(isActive);

    React.useEffect(() => {
      if (isActive) {
        setHasBeenActive(true);
      }
    }, [isActive]);

    const shouldRender = forceMount || isActive || (keepMounted && hasBeenActive);
    if (!shouldRender) {
      return null;
    }

    const tabId = buildTabId(baseId, value);
    const panelId = buildPanelId(baseId, value);

    return (
      <div
        ref={ref}
        role="tabpanel"
        id={panelId}
        aria-labelledby={tabId}
        data-state={isActive ? 'active' : 'inactive'}
        hidden={!isActive}
        className={cn(
          'mt-2 ring-offset-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2',
          'dark:ring-offset-surface-900',
          isActive ? 'animate-fade-in' : 'hidden',
          className
        )}
        {...props}
      />
    );
  }
);
TabsContent.displayName = 'TabsContent';

export { Tabs, TabsList, TabsTrigger, TabsContent };
