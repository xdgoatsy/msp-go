import { useState, useCallback, useRef } from 'react';
import {
  parseDocument,
  validateDocumentFile,
  type ParsedDocument,
} from '@/libs/utils/documentParser';

export interface FileUploadItem {
  /** 原始文件 */
  file: File;
  /** 解析后的文档（解析完成后填充） */
  parsed: ParsedDocument | null;
  /** 解析状态 */
  status: 'parsing' | 'done' | 'error';
  /** 错误信息 */
  error?: string;
}

export const useFileUpload = () => {
  const [files, setFiles] = useState<FileUploadItem[]>([]);
  const [isParsing, setIsParsing] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // 处理文件选择
  const handleFileSelect = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const fileList = e.target.files;
    if (!fileList || fileList.length === 0) return;

    const newItems: FileUploadItem[] = [];

    for (let i = 0; i < fileList.length; i++) {
      const file = fileList[i];
      const validation = validateDocumentFile(file);

      if (validation.valid) {
        newItems.push({ file, parsed: null, status: 'parsing' });
      } else {
        newItems.push({ file, parsed: null, status: 'error', error: validation.error });
      }
    }

    setFiles((prev) => [...prev, ...newItems]);

    // 重置 input 以允许重复选择同一文件
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }

    // 异步解析有效文件
    const validItems = newItems.filter((item) => item.status === 'parsing');
    if (validItems.length === 0) return;

    setIsParsing(true);

    await Promise.all(
      validItems.map(async (item) => {
        try {
          const parsed = await parseDocument(item.file);
          setFiles((prev) =>
            prev.map((f) =>
              f.file === item.file ? { ...f, parsed, status: 'done' as const } : f
            )
          );
        } catch (err) {
          const errorMsg = err instanceof Error ? err.message : '解析失败';
          setFiles((prev) =>
            prev.map((f) =>
              f.file === item.file
                ? { ...f, status: 'error' as const, error: errorMsg }
                : f
            )
          );
        }
      })
    );

    setIsParsing(false);
  }, []);

  // 移除文件
  const handleRemoveFile = useCallback((index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  }, []);

  // 清空所有文件
  const clearFiles = useCallback(() => {
    setFiles([]);
  }, []);

  // 获取所有已成功解析的文档
  const getParsedDocuments = useCallback((): ParsedDocument[] => {
    return files
      .filter((f): f is FileUploadItem & { parsed: ParsedDocument } =>
        f.status === 'done' && f.parsed !== null
      )
      .map((f) => f.parsed);
  }, [files]);

  // 是否有文件正在解析中
  const hasParsingFiles = files.some((f) => f.status === 'parsing');

  // 是否有已解析的文件
  const hasParsedFiles = files.some((f) => f.status === 'done');

  return {
    files,
    isParsing: isParsing || hasParsingFiles,
    hasParsedFiles,
    fileInputRef,
    handleFileSelect,
    handleRemoveFile,
    clearFiles,
    getParsedDocuments,
  };
};
