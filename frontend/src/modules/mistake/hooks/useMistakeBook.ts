import { useState, useMemo, useCallback, useEffect } from 'react';
import { xidianService } from '@/modules/xidian/services/xidianService';
import type { XidianBindingStatus } from '@/modules/xidian/services/xidianService';
import { useAppDispatch, useAppSelector } from '@/store';
import { fetchPortrait, generatePortrait, clearPortrait } from '@/modules/student/store/studentPortraitSlice';
import {
  fetchMistakes,
  deleteMistake,
  markAsMastered,
  selectMistakes,
  selectPagination,
  selectLoadingState,
  selectError,
} from '@/modules/mistake/store/mistakeSlice';

// ========== 类型定义 ==========

export interface ScoreRecord {
  name: string;
  score: number | string | null;
  semester_code: string;
  credit: number | null;
  class_status: string | null;
  class_type: string | null;
  is_passed: string | null;
  level: string | null;
}

export interface SemesterStats {
  semester: string;
  weightedAvg: number;
  totalCredits: number;
  count: number;
}

// ========== 工具函数 ==========

export function parseScore(score: number | string | null): number {
  if (typeof score === 'number') return score;
  return parseFloat(String(score));
}

function calcWeightedAvg(scores: ScoreRecord[]): number {
  let totalWeight = 0;
  let totalScore = 0;
  for (const s of scores) {
    const num = parseScore(s.score);
    const credit = s.credit ?? 0;
    if (!isNaN(num) && credit > 0) {
      totalScore += num * credit;
      totalWeight += credit;
    }
  }
  return totalWeight > 0 ? Math.round((totalScore / totalWeight) * 100) / 100 : 0;
}

function getSemesters(scores: ScoreRecord[]): string[] {
  const set = new Set(scores.map(s => s.semester_code));
  return Array.from(set).sort();
}

function getSemesterStats(scores: ScoreRecord[]): SemesterStats[] {
  const map = new Map<string, ScoreRecord[]>();
  for (const s of scores) {
    const arr = map.get(s.semester_code) || [];
    arr.push(s);
    map.set(s.semester_code, arr);
  }
  return Array.from(map.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([semester, items]) => ({
      semester,
      weightedAvg: calcWeightedAvg(items),
      totalCredits: items.reduce((sum, s) => sum + (s.credit ?? 0), 0),
      count: items.length,
    }));
}

export function getDifficultyBadge(difficulty: number) {
  if (difficulty >= 0.7) return { variant: 'destructive' as const, label: '困难' };
  if (difficulty >= 0.4) return { variant: 'warning' as const, label: '中等' };
  return { variant: 'success' as const, label: '简单' };
}

export function getErrorTypeLabel(errorType: string | null) {
  const labels: Record<string, string> = {
    'conceptual': '概念性错误',
    'procedural': '过程性错误',
    'logical': '逻辑错误',
    'symbolic': '符号错误',
    'calculation': '计算错误',
  };
  return errorType ? labels[errorType] || '未知错误' : '未分类';
}

// ========== 主 Hook ==========

export function useMistakeBook() {
  const [scores, setScores] = useState<ScoreRecord[]>([]);
  const [selectedSemester, setSelectedSemester] = useState('all');
  const [syncing, setSyncing] = useState(false);
  const [bindingStatus, setBindingStatus] = useState<XidianBindingStatus | null>(null);
  const [lastSyncAt, setLastSyncAt] = useState<string | null>(null);
  const [scoresLoading, setScoresLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('scores');

  const dispatch = useAppDispatch();
  const { portrait, loadingState: portraitLoading, generating, clearing } = useAppSelector(state => state.studentPortrait);

  const mistakes = useAppSelector(selectMistakes);
  const pagination = useAppSelector(selectPagination);
  const mistakesLoading = useAppSelector(selectLoadingState);
  const mistakesError = useAppSelector(selectError);

  // 加载错题列表
  useEffect(() => {
    if (activeTab === 'mistakes') {
      dispatch(fetchMistakes({ page: 1, pageSize: 20 }));
    }
  }, [activeTab, dispatch]);

  // 页面加载：获取绑定状态 + 成绩快照
  useEffect(() => {
    xidianService.getBindingStatus().then(setBindingStatus).catch(() => {});
    xidianService.getSnapshot('score')
      .then((res) => {
        const data = res.data as { scores?: ScoreRecord[] };
        if (data.scores && Array.isArray(data.scores) && data.scores.length > 0) {
          setScores(data.scores);
          setLastSyncAt(res.cached_at);
        }
      })
      .catch(() => {})
      .finally(() => setScoresLoading(false));
  }, []);

  // Tab 切换
  const handleTabChange = useCallback((value: string) => {
    setActiveTab(value);
    if (value === 'portrait') {
      dispatch(fetchPortrait());
    }
  }, [dispatch]);

  // 同步成绩
  const handleSync = useCallback(async () => {
    setSyncing(true);
    try {
      const res = await xidianService.syncScores();
      const data = res.data as { scores?: ScoreRecord[] };
      if (data.scores && Array.isArray(data.scores)) {
        setScores(data.scores);
        setLastSyncAt(res.fetched_at);
      }
    } catch {
      // 同步失败，保持当前数据不变
    } finally {
      setSyncing(false);
    }
  }, []);

  // 错题操作
  const handleDeleteMistake = useCallback(async (attemptId: string) => {
    if (window.confirm('确定要删除这条错题记录吗？删除后无法恢复。')) {
      await dispatch(deleteMistake(attemptId));
    }
  }, [dispatch]);

  const handleMarkAsMastered = useCallback(async (attemptId: string) => {
    await dispatch(markAsMastered(attemptId));
  }, [dispatch]);

  const handleFetchMistakes = useCallback((page: number) => {
    dispatch(fetchMistakes({ page, pageSize: 20 }));
  }, [dispatch]);

  // 画像操作
  const handleGeneratePortrait = useCallback(() => {
    dispatch(generatePortrait());
  }, [dispatch]);

  const handleClearPortrait = useCallback(() => {
    if (window.confirm('确定要清除画像吗？清除后需要重新生成。')) {
      dispatch(clearPortrait());
    }
  }, [dispatch]);

  // 计算统计数据
  const filteredScores = useMemo(() => {
    if (selectedSemester === 'all') return scores;
    return scores.filter(s => s.semester_code === selectedSemester);
  }, [scores, selectedSemester]);

  const semesters = useMemo(() => getSemesters(scores), [scores]);
  const semesterStats = useMemo(() => getSemesterStats(scores), [scores]);

  const overallStats = useMemo(() => {
    const numericScores = scores.filter(s => !isNaN(parseScore(s.score)));
    const passed = numericScores.filter(s => s.is_passed === '1').length;
    const totalCredits = scores.reduce((sum, s) => sum + (s.credit ?? 0), 0);
    return {
      weightedAvg: calcWeightedAvg(scores),
      totalCredits,
      passRate: numericScores.length > 0 ? Math.round((passed / numericScores.length) * 100) : 0,
      totalCourses: scores.length,
    };
  }, [scores]);

  const maxSemesterAvg = useMemo(
    () => Math.max(...semesterStats.map(s => s.weightedAvg), 100),
    [semesterStats]
  );

  const weakSubjects = useMemo(() => {
    return [...scores]
      .filter(s => !isNaN(parseScore(s.score)))
      .sort((a, b) => parseScore(a.score) - parseScore(b.score))
      .slice(0, 5);
  }, [scores]);

  const semesterOptions = useMemo(() => [
    { value: 'all', label: '全部学期' },
    ...semesters.map(s => ({ value: s, label: s })),
  ], [semesters]);

  const courseDistribution = useMemo(() => {
    const typeMap = new Map<string, number>();
    scores.forEach(s => {
      const t = s.class_status || '其他';
      typeMap.set(t, (typeMap.get(t) || 0) + 1);
    });
    return Array.from(typeMap.entries());
  }, [scores]);

  return {
    // 状态
    scores, scoresLoading, syncing, activeTab, selectedSemester, bindingStatus, lastSyncAt,
    // 错题
    mistakes, pagination, mistakesLoading, mistakesError,
    // 画像
    portrait, portraitLoading, generating, clearing,
    // 计算值
    filteredScores, semesters, semesterStats, overallStats, maxSemesterAvg,
    weakSubjects, semesterOptions, courseDistribution,
    // 操作
    setSelectedSemester, handleTabChange, handleSync,
    handleDeleteMistake, handleMarkAsMastered, handleFetchMistakes,
    handleGeneratePortrait, handleClearPortrait,
  };
}
