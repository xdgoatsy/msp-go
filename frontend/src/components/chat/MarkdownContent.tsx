/**
 * Markdown 内容渲染组件
 *
 * 用于渲染 AI 消息中的 Markdown 内容，支持：
 * - GitHub Flavored Markdown (表格、任务列表等)
 * - 数学公式 (KaTeX 渲染)
 * - 代码高亮
 *
 * 性能优化：
 * - React.memo 避免不必要的重渲染
 */

import React from 'react';
import ReactMarkdown from 'react-markdown';
import {
  MARKDOWN_COMPONENTS,
  REMARK_PLUGINS,
  REHYPE_PLUGINS,
  normalizeAssistantMarkdown,
} from './markdownRenderConfig';

interface MarkdownContentProps {
  content: string;
  /**
   * 若内容被 LLM 用单个 ```...```（或 ~~~...~~~）整段包裹（常见于 ```markdown），
   * 则先“解包”外层 fence，再按 Markdown 渲染。
   *
   * - 默认关闭，避免影响聊天场景中“只想展示原始代码块”的消息。
   */
  unwrapOuterFence?: boolean;
}

function unwrapOuterFencedBlock(content: string): string {
  if (!content) return content;

  // 统一行结束符，便于正则匹配；内部内容以 \n 返回即可被 react-markdown 正常解析。
  const normalizedEol = content.replace(/\r\n/g, '\n');
  const trimmed = normalizedEol.trim();

  // 只在“整段内容是一个单独 fence”的情况下解包。
  const backtick = trimmed.match(/^```[^\n]*\n([\s\S]*?)\n\s*```$/);
  if (backtick) return backtick[1];

  const tilde = trimmed.match(/^~~~[^\n]*\n([\s\S]*?)\n\s*~~~$/);
  if (tilde) return tilde[1];

  return content;
}

export const MarkdownContent = React.memo<MarkdownContentProps>(({ content, unwrapOuterFence = false }) => {
  const preprocessed = unwrapOuterFence ? unwrapOuterFencedBlock(content) : content;
  const normalized = normalizeAssistantMarkdown(preprocessed);
  return (
    <ReactMarkdown
      remarkPlugins={REMARK_PLUGINS}
      rehypePlugins={REHYPE_PLUGINS}
      components={MARKDOWN_COMPONENTS}
    >
      {normalized}
    </ReactMarkdown>
  );
});

MarkdownContent.displayName = 'MarkdownContent';
