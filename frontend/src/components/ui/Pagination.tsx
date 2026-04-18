import * as React from 'react';
import { cn } from '../../libs/utils/cn';
import { ChevronLeft, ChevronRight, MoreHorizontal } from 'lucide-react';
import { Button } from './Button';
import { animationCombos } from '../../libs/animations';

export interface PaginationProps extends React.HTMLAttributes<HTMLElement> {
  currentPage: number;
  totalPages: number;
  onPageChange?: (page: number) => void;
  siblingCount?: number;
}

const generatePagination = (currentPage: number, totalPages: number, siblingCount: number = 1) => {
  const totalNumbers = siblingCount * 2 + 3;
  const totalBlocks = totalNumbers + 2;

  if (totalPages <= totalBlocks) {
    return Array.from({ length: totalPages }, (_, i) => i + 1);
  }

  const leftSiblingIndex = Math.max(currentPage - siblingCount, 1);
  const rightSiblingIndex = Math.min(currentPage + siblingCount, totalPages);

  const shouldShowLeftDots = leftSiblingIndex > 2;
  const shouldShowRightDots = rightSiblingIndex < totalPages - 1;

  if (!shouldShowLeftDots && shouldShowRightDots) {
    const leftItemCount = 3 + 2 * siblingCount;
    const leftRange = Array.from({ length: leftItemCount }, (_, i) => i + 1);
    return [...leftRange, 'dots', totalPages];
  }

  if (shouldShowLeftDots && !shouldShowRightDots) {
    const rightItemCount = 3 + 2 * siblingCount;
    const rightRange = Array.from({ length: rightItemCount }, (_, i) => totalPages - rightItemCount + i + 1);
    return [1, 'dots', ...rightRange];
  }

  const middleRange = Array.from(
    { length: rightSiblingIndex - leftSiblingIndex + 1 },
    (_, i) => leftSiblingIndex + i
  );
  return [1, 'dots', ...middleRange, 'dots', totalPages];
};

const Pagination = React.forwardRef<HTMLElement, PaginationProps>(
  ({ className, currentPage, totalPages, onPageChange, siblingCount = 1, ...props }, ref) => {
    const pages = generatePagination(currentPage, totalPages, siblingCount);

    return (
      <nav
        ref={ref}
        role="navigation"
        aria-label="pagination"
        className={cn('mx-auto flex w-full justify-center', animationCombos.pageEnter, className)}
        {...props}
      >
        <ul className="flex flex-row items-center gap-1">
          <li>
            <Button
              variant="outline"
              size="icon"
              className="h-9 w-9"
              onClick={() => onPageChange?.(currentPage - 1)}
              disabled={currentPage <= 1}
              aria-label="上一页"
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
          </li>

          {pages.map((page, index) => (
            <li key={index}>
              {page === 'dots' ? (
                <span className="flex h-9 w-9 items-center justify-center">
                  <MoreHorizontal className="h-4 w-4 text-surface-400" />
                </span>
              ) : (
                <Button
                  variant={currentPage === page ? 'primary' : 'outline'}
                  size="icon"
                  className="h-9 w-9"
                  onClick={() => onPageChange?.(page as number)}
                  aria-label={`第 ${page} 页`}
                  aria-current={currentPage === page ? 'page' : undefined}
                >
                  {page}
                </Button>
              )}
            </li>
          ))}

          <li>
            <Button
              variant="outline"
              size="icon"
              className="h-9 w-9"
              onClick={() => onPageChange?.(currentPage + 1)}
              disabled={currentPage >= totalPages}
              aria-label="下一页"
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </li>
        </ul>
      </nav>
    );
  }
);
Pagination.displayName = 'Pagination';

export { Pagination };
