import { describe, it, expect } from 'vitest';
import {
  isMathCourse,
  calculateCurrentWeek,
  getClassesForWeek,
  calculateMathHours,
  formatPeriod,
  getPeriodTimeRange,
  WEEKDAYS,
} from '@/libs/utils/classtableUtils';
import type { ClasstableData } from '@/modules/classroom/types/classtable';

// ============================================
// isMathCourse 测试
// ============================================
describe('isMathCourse', () => {
  it('匹配"高等数学"', () => {
    expect(isMathCourse('高等数学')).toBe(true);
  });

  it('匹配"微积分"', () => {
    expect(isMathCourse('微积分')).toBe(true);
  });

  it('匹配"数学分析"', () => {
    expect(isMathCourse('数学分析')).toBe(true);
  });

  it('匹配"高数"', () => {
    expect(isMathCourse('高数')).toBe(true);
  });

  it('匹配包含关键词的课程名', () => {
    expect(isMathCourse('高等数学（上）')).toBe(true);
  });

  it('对"英语"返回 false', () => {
    expect(isMathCourse('英语')).toBe(false);
  });

  it('对"物理"返回 false', () => {
    expect(isMathCourse('物理')).toBe(false);
  });

  it('对空字符串返回 false', () => {
    expect(isMathCourse('')).toBe(false);
  });
});

// ============================================
// calculateCurrentWeek 测试
// ============================================
describe('calculateCurrentWeek', () => {
  it('今天作为开学日返回第 1 周', () => {
    const today = new Date().toISOString().split('T')[0];
    expect(calculateCurrentWeek(today)).toBe(1);
  });

  it('7 天前开学返回第 2 周', () => {
    const d = new Date();
    d.setDate(d.getDate() - 7);
    const dateStr = d.toISOString().split('T')[0];
    expect(calculateCurrentWeek(dateStr)).toBe(2);
  });

  it('14 天前开学返回第 3 周', () => {
    const d = new Date();
    d.setDate(d.getDate() - 14);
    const dateStr = d.toISOString().split('T')[0];
    expect(calculateCurrentWeek(dateStr)).toBe(3);
  });

  it('未来日期至少返回 1', () => {
    const d = new Date();
    d.setDate(d.getDate() + 30);
    const dateStr = d.toISOString().split('T')[0];
    expect(calculateCurrentWeek(dateStr)).toBeGreaterThanOrEqual(1);
  });

  it('很久以前的日期返回大于 1 的周次', () => {
    expect(calculateCurrentWeek('2020-01-01')).toBeGreaterThan(1);
  });
});

// ============================================
// formatPeriod 测试
// ============================================
describe('formatPeriod', () => {
  it('第 1 节返回"第1节"', () => {
    expect(formatPeriod(1)).toBe('第1节');
  });

  it('第 4 节返回"第4节"', () => {
    expect(formatPeriod(4)).toBe('第4节');
  });

  it('第 8 节返回"第8节"', () => {
    expect(formatPeriod(8)).toBe('第8节');
  });

  it('第 12 节返回"第12节"', () => {
    expect(formatPeriod(12)).toBe('第12节');
  });
});

// ============================================
// getPeriodTimeRange 测试
// ============================================
describe('getPeriodTimeRange', () => {
  it('第 1 节返回 08:00-08:45', () => {
    expect(getPeriodTimeRange(1)).toBe('08:00-08:45');
  });

  it('第 5 节返回 14:00-14:45', () => {
    expect(getPeriodTimeRange(5)).toBe('14:00-14:45');
  });

  it('第 9 节返回 19:00-19:45', () => {
    expect(getPeriodTimeRange(9)).toBe('19:00-19:45');
  });

  it('第 12 节返回 21:45-22:30', () => {
    expect(getPeriodTimeRange(12)).toBe('21:45-22:30');
  });

  it('无效节次返回空字符串', () => {
    expect(getPeriodTimeRange(0)).toBe('');
    expect(getPeriodTimeRange(13)).toBe('');
  });
});

// ============================================
// WEEKDAYS 测试
// ============================================
describe('WEEKDAYS', () => {
  it('包含 7 个元素', () => {
    expect(WEEKDAYS).toHaveLength(7);
  });

  it('第一个元素是"周一"', () => {
    expect(WEEKDAYS[0]).toBe('周一');
  });

  it('最后一个元素是"周日"', () => {
    expect(WEEKDAYS[6]).toBe('周日');
  });
});

// ============================================
// getClassesForWeek 测试
// ============================================

/** 构造最小测试数据 */
function makeData(overrides?: Partial<ClasstableData>): ClasstableData {
  return {
    semester_code: '2024-2025-1',
    term_start_day: '2024-09-01',
    semester_length: 20,
    time_arrangement: [],
    class_detail: [],
    not_arranged: [],
    class_changes: [],
    ...overrides,
  };
}

describe('getClassesForWeek', () => {
  it('空数据返回 7x12 全 null 网格', () => {
    const grid = getClassesForWeek(makeData(), 1);
    expect(grid).toHaveLength(7);
    grid.forEach(row => {
      expect(row).toHaveLength(12);
      row.forEach(cell => expect(cell).toBeNull());
    });
  });

  it('正确放置第 1 周的课程', () => {
    const data = makeData({
      time_arrangement: [
        {
          source: 'test',
          index: 1,
          day: 1,       // 周一
          start: 1,
          stop: 2,
          teacher: '张老师',
          classroom: 'A101',
          week_list: [1, 0, 0], // 第 1 周有课
        },
      ],
      class_detail: [
        { name: '', code: '', number: '' },
        { name: '高等数学', code: 'MATH001', number: '001' },
      ],
    });

    const grid = getClassesForWeek(data, 1);
    // 周一(index 0)，第 1、2 节应有课
    expect(grid[0][0]).not.toBeNull();
    expect(grid[0][1]).not.toBeNull();
    expect(grid[0][0]?.name).toBe('高等数学');
    expect(grid[0][0]?.isMath).toBe(true);
    // 第 3 节应为 null
    expect(grid[0][2]).toBeNull();
  });

  it('week_list 中不包含该周时跳过课程', () => {
    const data = makeData({
      time_arrangement: [
        {
          source: 'test',
          index: 1,
          day: 2,
          start: 3,
          stop: 4,
          teacher: '李老师',
          classroom: 'B202',
          week_list: [0, 1, 0], // 第 2 周有课，第 1 周没有
        },
      ],
      class_detail: [
        { name: '', code: '', number: '' },
        { name: '英语', code: 'ENG001', number: '002' },
      ],
    });

    const grid = getClassesForWeek(data, 1);
    // 第 1 周查询，周二第 3、4 节应为 null
    expect(grid[1][2]).toBeNull();
    expect(grid[1][3]).toBeNull();
  });

  it('week_list 为布尔数组时可正确渲染课程', () => {
    const data = makeData({
      time_arrangement: [
        {
          source: 'test',
          index: 1,
          day: 4,
          start: 2,
          stop: 3,
          teacher: '赵老师',
          classroom: 'D404',
          week_list: [true, false, false],
        },
      ],
      class_detail: [
        { name: '', code: '', number: '' },
        { name: '高等数学', code: 'MATH001', number: '001' },
      ],
    });

    const grid = getClassesForWeek(data, 1);
    expect(grid[3][1]?.name).toBe('高等数学');
    expect(grid[3][2]?.name).toBe('高等数学');
  });

  it('非高数课程 isMath 为 false', () => {
    const data = makeData({
      time_arrangement: [
        {
          source: 'test',
          index: 2,
          day: 3,
          start: 1,
          stop: 1,
          teacher: '王老师',
          classroom: 'C303',
          week_list: [1],
        },
      ],
      class_detail: [
        { name: '', code: '', number: '' },
        { name: '', code: '', number: '' },
        { name: '物理', code: 'PHY001', number: '003' },
      ],
    });

    const grid = getClassesForWeek(data, 1);
    expect(grid[2][0]?.isMath).toBe(false);
  });
});

// ============================================
// calculateMathHours 测试
// ============================================
describe('calculateMathHours', () => {
  it('无高数课时返回全零统计', () => {
    const data = makeData({
      time_arrangement: [
        {
          source: 'test',
          index: 1,
          day: 1,
          start: 1,
          stop: 2,
          teacher: '张老师',
          classroom: 'A101',
          week_list: [1, 1],
        },
      ],
      class_detail: [
        { name: '', code: '', number: '' },
        { name: '英语', code: 'ENG001', number: '002' },
      ],
    });

    const stats = calculateMathHours(data, 1);
    expect(stats.weeklyHours).toBe(0);
    expect(stats.totalHours).toBe(0);
    expect(stats.remainingHours).toBe(0);
  });

  it('计算每周课时', () => {
    const data = makeData({
      time_arrangement: [
        {
          source: 'test',
          index: 1,
          day: 1,
          start: 1,
          stop: 2, // 2 节课
          teacher: '张老师',
          classroom: 'A101',
          week_list: [1, 1, 1],
        },
      ],
      class_detail: [
        { name: '', code: '', number: '' },
        { name: '高等数学', code: 'MATH001', number: '001' },
      ],
    });

    const stats = calculateMathHours(data, 1);
    expect(stats.weeklyHours).toBe(2);
  });

  it('计算总课时', () => {
    const data = makeData({
      time_arrangement: [
        {
          source: 'test',
          index: 1,
          day: 1,
          start: 1,
          stop: 2, // 每次 2 节
          teacher: '张老师',
          classroom: 'A101',
          week_list: [1, 1, 1], // 3 周
        },
      ],
      class_detail: [
        { name: '', code: '', number: '' },
        { name: '高等数学', code: 'MATH001', number: '001' },
      ],
    });

    const stats = calculateMathHours(data, 1);
    expect(stats.totalHours).toBe(6); // 2 节 × 3 周
  });

  it('计算剩余课时（从当前周开始）', () => {
    const data = makeData({
      time_arrangement: [
        {
          source: 'test',
          index: 1,
          day: 1,
          start: 1,
          stop: 2,
          teacher: '张老师',
          classroom: 'A101',
          week_list: [1, 1, 1], // 3 周
        },
      ],
      class_detail: [
        { name: '', code: '', number: '' },
        { name: '高等数学', code: 'MATH001', number: '001' },
      ],
    });

    // 当前第 2 周，剩余应为第 2、3 周 = 4 节
    const stats = calculateMathHours(data, 2);
    expect(stats.remainingHours).toBe(4);
  });

  it('totalWeeks 和 remainingWeeks 正确', () => {
    const data = makeData({
      time_arrangement: [
        {
          source: 'test',
          index: 1,
          day: 1,
          start: 1,
          stop: 1,
          teacher: '张老师',
          classroom: 'A101',
          week_list: [1, 1, 1, 0],
        },
      ],
      class_detail: [
        { name: '', code: '', number: '' },
        { name: '高数', code: 'MATH002', number: '003' },
      ],
    });

    const stats = calculateMathHours(data, 2);
    expect(stats.totalWeeks).toBe(3);
    expect(stats.remainingWeeks).toBe(2); // 第 2、3 周
  });

  it('week_list 为布尔数组时统计正确', () => {
    const data = makeData({
      time_arrangement: [
        {
          source: 'test',
          index: 1,
          day: 1,
          start: 1,
          stop: 2, // 每次 2 节
          teacher: '张老师',
          classroom: 'A101',
          week_list: [true, true, false],
        },
      ],
      class_detail: [
        { name: '', code: '', number: '' },
        { name: '高数', code: 'MATH002', number: '003' },
      ],
    });

    const stats = calculateMathHours(data, 2);
    expect(stats.weeklyHours).toBe(2);
    expect(stats.totalHours).toBe(4);
    expect(stats.remainingHours).toBe(2);
  });

  it('week_list 混合 number 和 boolean 时统计一致', () => {
    const data = makeData({
      time_arrangement: [
        {
          source: 'test',
          index: 1,
          day: 2,
          start: 3,
          stop: 3, // 每次 1 节
          teacher: '李老师',
          classroom: 'B202',
          week_list: [1, true, 0, false],
        },
      ],
      class_detail: [
        { name: '', code: '', number: '' },
        { name: '高等数学', code: 'MATH001', number: '001' },
      ],
    });

    const stats = calculateMathHours(data, 2);
    expect(stats.totalWeeks).toBe(2);
    expect(stats.remainingWeeks).toBe(1);
    expect(stats.totalHours).toBe(2);
    expect(stats.remainingHours).toBe(1);
    expect(stats.weeklyHours).toBe(1);
  });
});
