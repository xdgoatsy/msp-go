/**
 * DOCX 文件解析适配器
 *
 * 使用 mammoth 在浏览器端将 DOCX 转换为纯文本
 * mammoth 通过动态导入按需加载，减少首屏 bundle 体积
 */

export interface DocxParseResult {
  /** 提取的纯文本内容 */
  text: string;
  /** 解析警告 */
  warnings: string[];
}

/**
 * 解析 DOCX 文件为纯文本
 *
 * @param file - DOCX 文件对象
 * @returns 纯文本内容和警告信息
 */
export async function parseDocxFile(file: File): Promise<DocxParseResult> {
  const warnings: string[] = [];

  try {
    const mammoth = await import('mammoth');
    const arrayBuffer = await file.arrayBuffer();
    const result = await mammoth.extractRawText({ arrayBuffer });

    // 收集 mammoth 的警告信息
    if (result.messages && result.messages.length > 0) {
      for (const msg of result.messages) {
        if (msg.type === 'warning') {
          warnings.push(msg.message);
        }
      }
    }

    // 检查是否有内容
    if (!result.value || result.value.trim().length === 0) {
      warnings.push('DOCX 文件内容为空，请检查文件是否正确');
    }

    // 提示图片和公式的局限性
    if (result.value && result.value.includes('\ufffc')) {
      warnings.push('检测到 DOCX 中包含嵌入对象（图片/公式），这些内容已被忽略，请导入后手动补充');
    }

    return {
      text: result.value || '',
      warnings,
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : '未知错误';
    throw new Error(`DOCX 文件解析失败: ${message}。请尝试将文件另存为 .txt 格式后重试`);
  }
}
