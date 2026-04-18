import * as React from 'react';
import katex from 'katex';
import 'katex/dist/katex.min.css';
import { cn } from '../utils/cn';

interface MathTextProps {
  children: string;
  className?: string;
}

/**
 * MathText 组件 - 渲染混合文本和 LaTeX 公式的内容
 *
 * 支持两种格式：
 * - 行内公式：$...$
 * - 块级公式：$$...$$
 *
 * @example
 * <MathText>求极限 $\lim_{x \to 0} \frac{\sin x}{x}$</MathText>
 */
export const MathText: React.FC<MathTextProps> = ({ children, className }) => {
  const containerRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (!containerRef.current || !children) return;

    // 正则表达式匹配 $...$ 或 $$...$$
    // 先处理 $$...$$ (块级公式)，再处理 $...$ (行内公式)
    const blockMathRegex = /\$\$([\s\S]*?)\$\$/g;
    const inlineMathRegex = /\$([^$]+?)\$/g;

    let html = children;

    // 转义 HTML 特殊字符（除了我们的占位符）
    html = html
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    // 处理块级公式 $$...$$
    html = html.replace(blockMathRegex, (_, expr) => {
      try {
        return `<div class="math-block my-2">${katex.renderToString(expr.trim(), {
          displayMode: true,
          throwOnError: false,
          output: 'htmlAndMathml',
        })}</div>`;
      } catch {
        return `<div class="math-block math-error">${expr}</div>`;
      }
    });

    // 处理行内公式 $...$
    html = html.replace(inlineMathRegex, (_, expr) => {
      try {
        return katex.renderToString(expr.trim(), {
          displayMode: false,
          throwOnError: false,
          output: 'htmlAndMathml',
        });
      } catch {
        return `<span class="math-error">${expr}</span>`;
      }
    });

    containerRef.current.innerHTML = html;
  }, [children]);

  return (
    <div
      ref={containerRef}
      className={cn('math-text', className)}
    />
  );
};

export default MathText;
