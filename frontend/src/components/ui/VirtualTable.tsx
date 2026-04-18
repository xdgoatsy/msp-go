/**
 * 虚拟化表格组件
 *
 * 使用 @tanstack/react-virtual 实现大数据量表格的虚拟滚动
 */

import React, { useRef } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';

export interface VirtualTableColumn<T> {
  key: string;
  header: string;
  width?: string;
  align?: 'left' | 'center' | 'right';
  render: (item: T, index: number) => React.ReactNode;
}

export interface VirtualTableProps<T> {
  data: T[];
  columns: VirtualTableColumn<T>[];
  rowHeight?: number;
  overscan?: number;
  getRowKey: (item: T) => string;
  onRowClick?: (item: T) => void;
  emptyMessage?: string;
  className?: string;
}

/**
 * 虚拟化表格组件
 *
 * @description 使用虚拟滚动技术，只渲染可见区域的行，
 * 大幅提升大数据量（1000+ 行）的渲染性能
 *
 * @example
 * ```tsx
 * <VirtualTable
 *   data={users}
 *   columns={[
 *     { key: 'name', header: '姓名', render: (user) => user.name },
 *     { key: 'email', header: '邮箱', render: (user) => user.email },
 *   ]}
 *   rowHeight={56}
 *   getRowKey={(user) => user.id}
 * />
 * ```
 */
export function VirtualTable<T>({
  data,
  columns,
  rowHeight = 56,
  overscan = 5,
  getRowKey,
  onRowClick,
  emptyMessage = '暂无数据',
  className = '',
}: VirtualTableProps<T>) {
  const parentRef = useRef<HTMLDivElement>(null);

  // eslint-disable-next-line react-hooks/incompatible-library
  const virtualizer = useVirtualizer({
    count: data.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => rowHeight,
    overscan,
  });

  const virtualItems = virtualizer.getVirtualItems();

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center py-12 text-surface-500 dark:text-surface-400">
        {emptyMessage}
      </div>
    );
  }

  return (
    <div className={className}>
      {/* 表头 */}
      <div className="border-b border-surface-200 dark:border-surface-700">
        <div className="flex">
          {columns.map((column) => (
            <div
              key={column.key}
              className={`py-3 px-4 font-medium text-surface-500 dark:text-surface-400 text-sm ${
                column.align === 'center' ? 'text-center' :
                column.align === 'right' ? 'text-right' : 'text-left'
              }`}
              style={{ width: column.width || 'auto', flex: column.width ? 'none' : 1 }}
            >
              {column.header}
            </div>
          ))}
        </div>
      </div>

      {/* 虚拟化表体 */}
      <div
        ref={parentRef}
        className="overflow-auto scroll-optimized"
        style={{ height: `${Math.min(data.length * rowHeight, 500)}px` }}
      >
        <div
          style={{
            height: `${virtualizer.getTotalSize()}px`,
            width: '100%',
            position: 'relative',
          }}
        >
          {virtualItems.map((virtualRow) => {
            const item = data[virtualRow.index];
            return (
              <div
                key={getRowKey(item)}
                className={`absolute top-0 left-0 w-full flex items-center hover:bg-surface-50 dark:hover:bg-surface-800/50 transition-colors ${
                  onRowClick ? 'cursor-pointer' : ''
                }`}
                style={{
                  height: `${rowHeight}px`,
                  transform: `translateY(${virtualRow.start}px)`,
                }}
                onClick={() => onRowClick?.(item)}
              >
                {columns.map((column) => (
                  <div
                    key={column.key}
                    className={`py-2 px-4 ${
                      column.align === 'center' ? 'text-center' :
                      column.align === 'right' ? 'text-right' : 'text-left'
                    }`}
                    style={{ width: column.width || 'auto', flex: column.width ? 'none' : 1 }}
                  >
                    {column.render(item, virtualRow.index)}
                  </div>
                ))}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export default VirtualTable;
