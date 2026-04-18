/**
 * TXT 文件解析适配器
 *
 * 支持 UTF-8 和 GBK 编码自动检测
 */

/**
 * 检测文本是否包含乱码（常见于 GBK 编码被当作 UTF-8 读取）
 */
function hasGarbledText(text: string): boolean {
  // 常见乱码特征：大量连续的替换字符或不可打印字符
  const replacementCharCount = (text.match(/\ufffd/g) || []).length;
  if (replacementCharCount > text.length * 0.05) {
    return true;
  }

  // 检测常见的 GBK 乱码模式（中文被错误解码后的特征）
  const garbledPattern = /[\u00c0-\u00ff]{3,}/;
  if (garbledPattern.test(text)) {
    return true;
  }

  return false;
}

export interface TxtParseResult {
  /** 提取的纯文本内容 */
  text: string;
  /** 解析警告 */
  warnings: string[];
  /** 检测到的编码 */
  encoding: string;
}

/**
 * 解析 TXT 文件为纯文本
 *
 * 先尝试 UTF-8，如果检测到乱码则尝试 GBK
 *
 * @param file - TXT 文件对象
 * @returns 纯文本内容、警告和编码信息
 */
export async function parseTxtFile(file: File): Promise<TxtParseResult> {
  const warnings: string[] = [];

  try {
    // 先尝试 UTF-8
    const utf8Text = await file.text();

    if (!hasGarbledText(utf8Text)) {
      if (!utf8Text.trim()) {
        warnings.push('TXT 文件内容为空，请检查文件是否正确');
      }
      return { text: utf8Text, warnings, encoding: 'UTF-8' };
    }

    // UTF-8 有乱码，尝试 GBK
    try {
      const buffer = await file.arrayBuffer();
      const gbkDecoder = new TextDecoder('gbk');
      const gbkText = gbkDecoder.decode(buffer);

      if (!hasGarbledText(gbkText)) {
        warnings.push('文件编码为 GBK，已自动转换为 UTF-8');
        return { text: gbkText, warnings, encoding: 'GBK' };
      }
    } catch {
      // GBK 解码失败，回退到 UTF-8
    }

    // 两种编码都有问题，使用 UTF-8 结果并警告
    warnings.push('文件编码检测不确定，部分字符可能显示异常，请检查内容是否正确');
    return { text: utf8Text, warnings, encoding: 'UTF-8 (fallback)' };
  } catch (error) {
    const message = error instanceof Error ? error.message : '未知错误';
    throw new Error(`TXT 文件读取失败: ${message}`);
  }
}
