import type {
  ClasstableData,
  ClassCell,
  MathHoursStats,
  TimeArrangement,
  WeekFlag,
} from '@/modules/classroom/types/classtable';

const MATH_KEYWORDS = ['高等数学', '微积分', '数学分析', '高数'];

function isWeekActive(flag: WeekFlag | undefined): boolean {
  return flag === true || flag === 1;
}

/**
 * 判断是否为高数课程
 */
export function isMathCourse(name: string): boolean {
  const lowerName = name.toLowerCase();
  return MATH_KEYWORDS.some(kw => lowerName.includes(kw.toLowerCase()));
}

/**
 * 计算当前周次
 */
export function calculateCurrentWeek(termStartDay: string): number {
  const termStart = new Date(termStartDay);
  const now = new Date();
  const diffMs = now.getTime() - termStart.getTime();
  const diffDays = Math.floor(diffMs / (24 * 60 * 60 * 1000));
  const week = Math.floor(diffDays / 7) + 1;
  return Math.max(1, week);
}

/**
 * 获取指定周的课表矩阵
 * 返回 7(天) x 12(节) 的二维数组
 */
export function getClassesForWeek(
  data: ClasstableData,
  week: number
): (ClassCell | null)[][] {
  const grid: (ClassCell | null)[][] = Array.from({ length: 7 }, () =>
    Array.from({ length: 12 }, () => null)
  );

  data.time_arrangement.forEach((arr: TimeArrangement) => {
    if (!isWeekActive(arr.week_list[week - 1])) return;

    const classDetail = data.class_detail[arr.index];
    if (!classDetail) return;

    const dayIndex = arr.day - 1;
    if (dayIndex < 0 || dayIndex > 6) return;

    const cell: ClassCell = {
      name: classDetail.name,
      teacher: arr.teacher,
      classroom: arr.classroom,
      isMath: isMathCourse(classDetail.name),
      startPeriod: arr.start,
      endPeriod: arr.stop,
    };

    for (let period = arr.start; period <= arr.stop && period <= 12; period++) {
      grid[dayIndex][period - 1] = cell;
    }
  });

  return grid;
}

/**
 * 计算高数课时统计
 */
export function calculateMathHours(
  data: ClasstableData,
  currentWeek: number
): MathHoursStats {
  let weeklyHours = 0;
  let totalWeeksWithMath = 0;
  let remainingWeeksWithMath = 0;

  const mathArrangements = data.time_arrangement.filter((arr) => {
    const classDetail = data.class_detail[arr.index];
    return classDetail && isMathCourse(classDetail.name);
  });

  const weekSet = new Set<number>();
  const remainingWeekSet = new Set<number>();

  mathArrangements.forEach((arr) => {
    const hoursPerClass = arr.stop - arr.start + 1;

    arr.week_list.forEach((hasClass, weekIndex) => {
      if (isWeekActive(hasClass)) {
        weekSet.add(weekIndex + 1);
        if (weekIndex + 1 >= currentWeek) {
          remainingWeekSet.add(weekIndex + 1);
        }
      }
    });

    if (isWeekActive(arr.week_list[currentWeek - 1])) {
      weeklyHours += hoursPerClass;
    }
  });

  totalWeeksWithMath = weekSet.size;
  remainingWeeksWithMath = remainingWeekSet.size;

  const totalHours = mathArrangements.reduce((sum, arr) => {
    const hoursPerClass = arr.stop - arr.start + 1;
    const classWeeks = arr.week_list.filter(isWeekActive).length;
    return sum + hoursPerClass * classWeeks;
  }, 0);

  const remainingHours = mathArrangements.reduce((sum, arr) => {
    const hoursPerClass = arr.stop - arr.start + 1;
    const remainingClassWeeks = arr.week_list
      .slice(currentWeek - 1)
      .filter(isWeekActive).length;
    return sum + hoursPerClass * remainingClassWeeks;
  }, 0);

  return {
    totalWeeks: totalWeeksWithMath,
    remainingWeeks: remainingWeeksWithMath,
    totalHours,
    remainingHours,
    weeklyHours,
  };
}

/**
 * 格式化节次显示
 */
export function formatPeriod(period: number): string {
  if (period <= 4) return `第${period}节`;
  if (period <= 8) return `第${period}节`;
  return `第${period}节`;
}

/**
 * 获取节次时间段
 */
export function getPeriodTimeRange(period: number): string {
  const times: Record<number, string> = {
    1: '08:00-08:45',
    2: '08:55-09:40',
    3: '10:00-10:45',
    4: '10:55-11:40',
    5: '14:00-14:45',
    6: '14:55-15:40',
    7: '16:00-16:45',
    8: '16:55-17:40',
    9: '19:00-19:45',
    10: '19:55-20:40',
    11: '20:50-21:35',
    12: '21:45-22:30',
  };
  return times[period] || '';
}

/**
 * 星期几显示
 */
export const WEEKDAYS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
