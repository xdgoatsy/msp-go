import React from 'react';
import { Link } from 'react-router-dom';
import { cn } from '../../libs/utils/cn';
import { animationCombos } from '../../libs/animations';

interface FooterProps {
  variant?: 'default' | 'dark';
}

const footerLinks = [
  { label: '使用指南', href: '/guide' },
  { label: '常见问题', href: '/faq' },
  { label: '团队介绍', href: '/about' },
  { label: '联系我们', href: '/contact' },
  { label: '隐私政策', href: '/privacy-policy' },
];

export const Footer: React.FC<FooterProps> = ({ variant = 'default' }) => {
  const isDark = variant === 'dark';

  return (
    <footer className={cn(
      "border-t py-5",
      animationCombos.buttonHover,
      isDark
        ? "bg-surface-950 border-surface-800 text-surface-400"
        : "bg-white border-surface-200 text-surface-600 dark:bg-surface-900 dark:border-surface-700 dark:text-surface-400"
    )}>
      <div className="container mx-auto px-6">
        <div className="flex flex-col md:flex-row justify-between items-center gap-4">
          {/* Left: Logo & Copyright */}
          <div className="flex items-center gap-4">
            <div className="flex items-center space-x-2">
              <div className="h-6 w-6 bg-linear-to-br from-primary-500 to-secondary-600 rounded flex items-center justify-center text-white shadow-sm">
                <span className="font-bold text-sm">M</span>
              </div>
              <span className={cn("font-bold text-lg", isDark ? "text-surface-100" : "text-surface-900 dark:text-surface-100")}>
                高数智学
              </span>
            </div>
            <span className={cn("hidden md:inline text-xs", isDark ? "text-surface-500" : "text-surface-400")}>
              © 2026 Xidian MathStudyPlatform
            </span>
          </div>

          {/* Right: Links */}
          <nav className="flex flex-wrap items-center justify-center gap-x-1 gap-y-1 text-xs">
            {footerLinks.map((link, index) => (
              <React.Fragment key={link.href}>
                {index > 0 && (
                  <span className={cn("mx-1.5", isDark ? "text-surface-600" : "text-surface-300 dark:text-surface-600")}>
                    ·
                  </span>
                )}
                <Link
                  to={link.href}
                  className={cn(
                    animationCombos.buttonHover,
                    "hover:underline decoration-primary-600/30 underline-offset-2",
                    isDark ? "hover:text-primary-400" : "hover:text-primary-600 dark:hover:text-primary-400"
                  )}
                >
                  {link.label}
                </Link>
              </React.Fragment>
            ))}
          </nav>

          {/* Mobile Copyright */}
          <span className={cn("md:hidden text-xs", isDark ? "text-surface-500" : "text-surface-400")}>
            © 2024 Xidian MathStudyPlatform. All rights reserved.
          </span>
        </div>
      </div>
    </footer>
  );
};
