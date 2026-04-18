/**
 * 流式 Markdown 增量渲染组件
 *
 * 将内容拆分为"已稳定段落"和"正在输入的尾部"，
 * 已稳定段落使用 useMemo 缓存渲染结果（含 KaTeX），只有尾部需要重新解析。
 */

import React, { useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import {
  MARKDOWN_COMPONENTS,
  REMARK_PLUGINS,
  REHYPE_PLUGINS,
  normalizeAssistantMarkdown,
} from './markdownRenderConfig';

interface StreamingMarkdownContentProps {
  content: string;
  isStreaming: boolean;
}

/**
 * 找到最后一个完整段落的分割点
 * 完整段落 = 以双换行符结尾的文本块
 */
function findStableSplitPoint(content: string): number {
  const lastDoubleNewline = content.lastIndexOf('\n\n');
  if (lastDoubleNewline === -1) return 0;
  return lastDoubleNewline + 2;
}

export const StreamingMarkdownContent = React.memo<StreamingMarkdownContentProps>(
  ({ content, isStreaming }) => {
    const normalizedContent = normalizeAssistantMarkdown(content);

    // 非流式状态：直接渲染全部内容
    if (!isStreaming) {
      return (
        <ReactMarkdown
          remarkPlugins={REMARK_PLUGINS}
          rehypePlugins={REHYPE_PLUGINS}
          components={MARKDOWN_COMPONENTS}
        >
          {normalizedContent}
        </ReactMarkdown>
      );
    }

    // 流式状态：拆分为稳定部分 + 尾部
    const splitPoint = findStableSplitPoint(normalizedContent);
    const stableContent = normalizedContent.slice(0, splitPoint);
    const tailContent = normalizedContent.slice(splitPoint);

    return (
      <StreamingSplit stableContent={stableContent} tailContent={tailContent} />
    );
  }
);

StreamingMarkdownContent.displayName = 'StreamingMarkdownContent';

/**
 * 内部拆分渲染组件
 * 将 useMemo 放在独立组件中，避免 hooks 在条件分支中调用
 */
const StreamingSplit: React.FC<{ stableContent: string; tailContent: string }> = ({
  stableContent,
  tailContent,
}) => {
  // 稳定部分使用 useMemo 缓存，只有 stableContent 变化时才重新解析
  const stableRendered = useMemo(() => {
    if (!stableContent) return null;
    return (
      <ReactMarkdown
        remarkPlugins={REMARK_PLUGINS}
        rehypePlugins={REHYPE_PLUGINS}
        components={MARKDOWN_COMPONENTS}
      >
        {stableContent}
      </ReactMarkdown>
    );
  }, [stableContent]);

  return (
    <>
      {stableRendered}
      {tailContent && (
        <ReactMarkdown
          remarkPlugins={REMARK_PLUGINS}
          rehypePlugins={REHYPE_PLUGINS}
          components={MARKDOWN_COMPONENTS}
        >
          {tailContent}
        </ReactMarkdown>
      )}
    </>
  );
};

StreamingSplit.displayName = 'StreamingSplit';
