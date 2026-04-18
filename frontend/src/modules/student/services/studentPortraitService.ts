/**
 * 学生画像 API 服务
 *
 * 提供学生画像的获取、生成和清除功能
 */

import { apiClient } from '@/libs/http/apiClient';
import { logger } from '@/libs/utils/logger';
import type {
  StudentPortrait,
  GeneratePortraitResponse,
  ClearPortraitResponse,
} from '@/modules/student/types/studentPortrait';

const portraitLogger = logger.createContextLogger('StudentPortrait');

const BASE_PATH = '/portrait';

export const studentPortraitService = {
  /**
   * 获取学生画像
   */
  async getPortrait(): Promise<StudentPortrait> {
    try {
      const response = await apiClient.get<StudentPortrait>(BASE_PATH);
      portraitLogger.debug('获取学生画像成功', {
        has_content: response.data.has_content,
      });
      return response.data;
    } catch (error) {
      portraitLogger.error('获取学生画像失败', error);
      throw error;
    }
  },

  /**
   * 生成/重新生成学生画像
   */
  async generatePortrait(): Promise<GeneratePortraitResponse> {
    try {
      const response = await apiClient.post<GeneratePortraitResponse>(
        `${BASE_PATH}/generate`
      );
      portraitLogger.info('生成学生画像成功', {
        version: response.data.portrait_version,
      });
      return response.data;
    } catch (error) {
      portraitLogger.error('生成学生画像失败', error);
      throw error;
    }
  },

  /**
   * 清除学生画像
   */
  async clearPortrait(): Promise<ClearPortraitResponse> {
    try {
      const response =
        await apiClient.delete<ClearPortraitResponse>(BASE_PATH);
      portraitLogger.info('清除学生画像成功');
      return response.data;
    } catch (error) {
      portraitLogger.error('清除学生画像失败', error);
      throw error;
    }
  },
};

export default studentPortraitService;
