import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { MainLayout } from '@/components/layout/MainLayout';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card, CardContent } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Modal } from '@/components/ui/Modal';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs';
import {
  Archive,
  Bell,
  CheckCircle2,
  HelpCircle,
  Import,
  Loader2,
  MessageSquare,
  Paperclip,
  Plus,
  Search,
  Send,
  Trash2,
} from 'lucide-react';
import { cn } from '@/libs/utils/cn';
import { formatRelativeTime } from '@/libs/utils/dateFormat';
import {
  conversationService,
  type ConversationItem,
  type ConversationDetail,
  type Contact,
} from '@/modules/message-center/services/conversationService';
import {
  noticeService,
  type StudentNoticeItem,
} from '@/modules/message-center/services/noticeService';
import {
  qaThreadService,
  type StudentThreadItem,
  type ThreadDetail,
} from '@/modules/message-center/services/qaThreadService';
import {
  fetchMistakes,
  type MistakeRecord,
} from '@/modules/mistake/services/mistakeService';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function matchKeywords(haystack: string, search: string): boolean {
  if (!search.trim()) return true;
  const keywords = search.trim().toLowerCase().split(/\s+/);
  const lower = haystack.toLowerCase();
  return keywords.every((kw) => lower.includes(kw));
}

const statusVariant = {
  '待回复': 'warning',
  '已回复': 'default',
  '已解决': 'success',
} as const;
const noticeStatuses = ['全部', '待确认', '已确认'];

const renderTabCount = (count: number) => {
  if (count <= 0) return null;
  return (
    <span className="ml-2 inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-red-500 px-1.5 text-xs font-semibold leading-none text-white">
      {count > 99 ? '99+' : count}
    </span>
  );
};

function mapConversationItem(c: ConversationItem) {
  return {
    id: c.id,
    teacherId: c.teacher_id ?? '',
    teacherName: c.teacher_name ?? '',
    scope: c.scope ?? '',
    lastMessage: c.last_message,
    lastTime: formatRelativeTime(c.last_time),
    unread: c.unread,
    archived: c.archived,
    messages: [] as Array<{ id: string; from: string; text: string; time: string; readByRecipient?: boolean }>,
  };
}

function mapNotice(n: StudentNoticeItem) {
  return {
    id: n.id,
    className: n.class_name,
    title: n.title,
    body: n.body,
    publishedAt: formatRelativeTime(n.published_at),
    confirmed: n.confirmed,
    attachments: n.attachments,
  };
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
export const MessageCenterPage: React.FC = () => {
  // ---- state ---------------------------------------------------------
  const [searchTerm, setSearchTerm] = useState('');
  const [activeTab, setActiveTab] = useState('private');
  const [initialLoad, setInitialLoad] = useState(true);
  const [loading, setLoading] = useState(false);

  // conversations
  const [convItems, setConvItems] = useState<ReturnType<typeof mapConversationItem>[]>([]);
  const [activeConv, setActiveConv] = useState<ConversationDetail | null>(null);
  const [activeConvId, setActiveConvId] = useState('');
  const [messageDraft, setMessageDraft] = useState('');
  const [sendingMsg, setSendingMsg] = useState(false);

  // new conversation modal
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [newConvOpen, setNewConvOpen] = useState(false);
  const [selectedTeacherId, setSelectedTeacherId] = useState('');
  const [contactSearch, setContactSearch] = useState('');
  const [globalSearchResults, setGlobalSearchResults] = useState<Contact[]>([]);
  const [newConvDraft, setNewConvDraft] = useState('');
  const [creatingConv, setCreatingConv] = useState(false);

  // notices
  const [notices, setNotices] = useState<ReturnType<typeof mapNotice>[]>([]);
  const [activeNoticeId, setActiveNoticeId] = useState('');
  const [noticeStatus, setNoticeStatus] = useState('全部');
  const [confirming, setConfirming] = useState('');

  // questions
  const [questions, setQuestions] = useState<StudentThreadItem[]>([]);
  const [activeThread, setActiveThread] = useState<ThreadDetail | null>(null);
  const [activeQuestionId, setActiveQuestionId] = useState('');
  const [questionDraft, setQuestionDraft] = useState('');
  const [selectedQTeacherId, setSelectedQTeacherId] = useState('');
  const [submittingQ, setSubmittingQ] = useState(false);
  const [followUpDraft, setFollowUpDraft] = useState('');
  const [sendingFollowUp, setSendingFollowUp] = useState(false);
  const [deletingThread, setDeletingThread] = useState(false);

  // import modal
  const [importOpen, setImportOpen] = useState(false);
  const [importTeacherId, setImportTeacherId] = useState('');
  const [importing, setImporting] = useState(false);
  const [mistakes, setMistakes] = useState<MistakeRecord[]>([]);
  const [loadingMistakes, setLoadingMistakes] = useState(false);
  const [selectedMistakeId, setSelectedMistakeId] = useState('');
  const [importQuestionText, setImportQuestionText] = useState('');

  // ---- load contacts --------------------------------------------------
  const loadContacts = useCallback(async () => {
    try {
      const { contacts: list } = await conversationService.contacts();
      setContacts(list);
      if (list.length > 0) {
        setSelectedTeacherId(list[0].id);
        setSelectedQTeacherId(list[0].id);
        setImportTeacherId(list[0].id);
      }
    } catch { /* contacts load fails silently */ }
  }, []);

  // ---- load conversations ---------------------------------------------
  const loadConversations = useCallback(async () => {
    try {
      const res = await conversationService.list({ page: 1, page_size: 50 });
      setConvItems(res.items.map(mapConversationItem));
    } catch { /* handled by loading state */ }
  }, []);

  const loadConversationDetail = useCallback(async (id: string) => {
    try {
      const detail = await conversationService.get(id);
      setActiveConv(detail);
    } catch { /* silent */ }
  }, []);

  // ---- load notices ---------------------------------------------------
  const loadNotices = useCallback(async () => {
    try {
      const res = await noticeService.list({ status: noticeStatus, page: 1, page_size: 50 });
      setNotices((res.items as StudentNoticeItem[]).map(mapNotice));
      if (res.items.length > 0 && !activeNoticeId) {
        setActiveNoticeId(res.items[0].id);
      }
    } catch { /* silent */ }
  }, [noticeStatus, activeNoticeId]);

  // ---- load questions -------------------------------------------------
  const loadQuestions = useCallback(async () => {
    try {
      const res = await qaThreadService.list({ page: 1, page_size: 50 });
      setQuestions(res.items as StudentThreadItem[]);
      if (res.items.length > 0 && !activeQuestionId) {
        setActiveQuestionId(res.items[0].id);
      }
    } catch { /* silent */ }
  }, [activeQuestionId]);

  const loadThreadDetail = useCallback(async (id: string) => {
    try {
      const detail = await qaThreadService.get(id);
      setActiveThread(detail);
    } catch { /* silent */ }
  }, []);

  // ---- initial load — only shows full-page spinner on first mount
  useEffect(() => {
    let active = true;
    const init = async () => {
      if (initialLoad) setLoading(true);
      await Promise.allSettled([
        loadContacts(),
        loadConversations(),
        loadNotices(),
        loadQuestions(),
      ]);
      if (active) {
        setLoading(false);
        setInitialLoad(false);
      }
    };
    init();
    return () => { active = false; };
  }, [loadContacts, loadConversations, loadNotices, loadQuestions]);

  // ---- derived --------------------------------------------------------
  const activeNotice = useMemo(
    () => notices.find((n) => n.id === activeNoticeId) ?? notices[0],
    [notices, activeNoticeId],
  );

  const filteredConversations = useMemo(
    () => convItems.filter((c) =>
      !c.archived &&
      matchKeywords(`${c.teacherName} ${c.scope} ${c.lastMessage}`, searchTerm),
    ),
    [convItems, searchTerm],
  );

  const filteredNotices = useMemo(
    () => notices.filter((n) => {
      const matchesSearch = matchKeywords(`${n.className} ${n.title} ${n.body}`, searchTerm);
      const matchesStatus = noticeStatus === '全部' ||
        (noticeStatus === '待确认' && !n.confirmed) ||
        (noticeStatus === '已确认' && n.confirmed);
      return matchesSearch && matchesStatus;
    }),
    [notices, noticeStatus, searchTerm],
  );

  const filteredQuestions = useMemo(
    () => questions.filter((q) =>
      matchKeywords(`${q.title} ${q.teacher_name} ${q.source} ${q.context}`, searchTerm),
    ),
    [questions, searchTerm],
  );

  const availableContacts = useMemo(
    () => contacts.filter((c) => !convItems.some((conv) => conv.teacherId === c.id)),
    [contacts, convItems],
  );

  const filteredAvailableContacts = useMemo(
    () => {
      if (!contactSearch.trim()) return availableContacts;
      const kw = contactSearch.trim().toLowerCase();
      return availableContacts.filter((c) =>
        c.id.toLowerCase().includes(kw) ||
        c.teacher_name.toLowerCase().includes(kw) ||
        c.scope.toLowerCase().includes(kw),
      );
    },
    [availableContacts, contactSearch],
  );

  // Global search — debounced, queries all users
  useEffect(() => {
    const q = contactSearch.trim();
    if (!q) { setGlobalSearchResults([]); return; }
    const timer = setTimeout(async () => {
      try {
        const { contacts: list } = await conversationService.searchUsers(q);
        setGlobalSearchResults(list.filter((c) => !availableContacts.some((a) => a.id === c.id)));
      } catch { setGlobalSearchResults([]); }
    }, 300);
    return () => clearTimeout(timer);
  }, [contactSearch, availableContacts]);

  const allSearchResults = useMemo(() => {
    const local = filteredAvailableContacts;
    const extra = globalSearchResults.filter((g) => !local.some((l) => l.id === g.id));
    return [...local, ...extra];
  }, [filteredAvailableContacts, globalSearchResults]);

  const privateUnreadCount = convItems.filter((c) => !c.archived).reduce((t, c) => t + c.unread, 0);
  const noticePendingCount = notices.filter((n) => !n.confirmed).length;
  const questionAnsweredCount = questions.filter((q) => q.status !== '待回复').length;

  // ---- actions: conversations -----------------------------------------
  const openConversation = useCallback(async (id: string) => {
    setActiveConvId(id);
    setActiveConv(null);
    // mark as read locally
    setConvItems((prev) => prev.map((c) => (c.id === id ? { ...c, unread: 0 } : c)));
    await loadConversationDetail(id);
  }, [loadConversationDetail]);

  const sendPrivateMessage = useCallback(async (event?: React.FormEvent<HTMLFormElement>) => {
    event?.preventDefault();
    if (!activeConvId || !messageDraft.trim() || sendingMsg) return;
    setSendingMsg(true);
    try {
      await conversationService.sendMessage(activeConvId, messageDraft.trim());
      setMessageDraft('');
      await loadConversationDetail(activeConvId);
      await loadConversations(); // refresh sidebar
    } catch { /* silent */ }
    finally { setSendingMsg(false); }
  }, [activeConvId, messageDraft, sendingMsg, loadConversationDetail, loadConversations]);

  const createConversation = useCallback(async () => {
    if (!selectedTeacherId || creatingConv) return;
    setCreatingConv(true);
    try {
      const teacher = contacts.find((c) => c.id === selectedTeacherId);
      const detail = await conversationService.create({
        target_id: selectedTeacherId,
        subject: teacher?.scope ?? '',
        initial_message: newConvDraft.trim(),
      });
      setNewConvDraft('');
      setNewConvOpen(false);
      await loadConversations();
      setActiveConvId(detail.id);
      setActiveConv(detail);
    } catch { /* silent */ }
    finally { setCreatingConv(false); }
  }, [selectedTeacherId, newConvDraft, creatingConv, loadConversations]);

  const archiveConversation = useCallback(async (id: string) => {
    try {
      await conversationService.archive(id);
      await loadConversations();
      const next = convItems.find((c) => c.id !== id && !c.archived);
      if (next) setActiveConvId(next.id);
      else setActiveConv(null);
    } catch { /* silent */ }
  }, [loadConversations, convItems]);

  const deleteConversation = useCallback(async (id: string) => {
    try {
      await conversationService.delete(id);
      await loadConversations();
      const next = convItems.find((c) => c.id !== id && !c.archived);
      if (next) setActiveConvId(next.id);
      else setActiveConv(null);
    } catch { /* silent */ }
  }, [loadConversations, convItems]);

  // ---- actions: notices -----------------------------------------------
  const confirmNotice = useCallback(async (id: string) => {
    if (confirming === id) return;
    setConfirming(id);
    try {
      await noticeService.confirm(id);
      setNotices((prev) => prev.map((n) => (n.id === id ? { ...n, confirmed: true } : n)));
    } catch { /* silent */ }
    finally { setConfirming(''); }
  }, [confirming]);

  // ---- actions: questions ---------------------------------------------
  const createQuestion = useCallback(async () => {
    if (!questionDraft.trim() || submittingQ) return;
    setSubmittingQ(true);
    try {
      await qaThreadService.create({ teacher_id: selectedQTeacherId, content: questionDraft.trim() });
      setQuestionDraft('');
      await loadQuestions();
    } catch { /* silent */ }
    finally { setSubmittingQ(false); }
  }, [questionDraft, selectedQTeacherId, submittingQ, loadQuestions]);

  const loadMistakesForImport = useCallback(async () => {
    setLoadingMistakes(true);
    try {
      const res = await fetchMistakes({ page: 1, pageSize: 50 });
      setMistakes(res.items);
    } catch { /* silent */ }
    finally { setLoadingMistakes(false); }
  }, []);

  const importQuestion = useCallback(async () => {
    if (importing) return;
    const selected = mistakes.find((m) => m.id === selectedMistakeId);
    if (!selected) return;
    setImporting(true);
    try {
      const fullContext = [
        `【原题】${selected.exercise.title}`,
        `【题目内容】${selected.exercise.content}`,
        `【我的答案】${selected.attempt.studentAnswer}`,
        `【正确答案】${selected.attempt.correctAnswer}`,
        selected.diagnosis.explanation ? `【错因分析】${selected.diagnosis.explanation}` : '',
        selected.diagnosis.suggestion ? `【建议】${selected.diagnosis.suggestion}` : '',
      ].filter(Boolean).join('\n\n');
      const question = importQuestionText.trim();
      const content = question
        ? `${question}\n\n---\n\n${fullContext}`
        : fullContext;
      await qaThreadService.importQuestion({
        teacher_id: importTeacherId,
        source: '错题本',
        content,
      });
      setSelectedMistakeId('');
      setImportQuestionText('');
      setImportOpen(false);
      await loadQuestions();
    } catch { /* silent */ }
    finally { setImporting(false); }
  }, [importing, mistakes, selectedMistakeId, importTeacherId, importQuestionText, loadQuestions]);

  const createFollowUp = useCallback(async () => {
    if (!followUpDraft.trim() || !activeQuestionId || sendingFollowUp) return;
    setSendingFollowUp(true);
    try {
      await qaThreadService.sendMessage(activeQuestionId, followUpDraft.trim());
      setFollowUpDraft('');
      await loadThreadDetail(activeQuestionId);
      await loadQuestions();
    } catch { /* silent */ }
    finally { setSendingFollowUp(false); }
  }, [followUpDraft, activeQuestionId, sendingFollowUp, loadThreadDetail, loadQuestions]);

  const deleteThread = useCallback(async () => {
    if (!activeQuestionId || deletingThread) return;
    if (!window.confirm('确定要删除这条提问吗？')) return;
    setDeletingThread(true);
    try {
      await qaThreadService.delete(activeQuestionId);
      setActiveQuestionId('');
      setActiveThread(null);
      await loadQuestions();
    } catch (err) {
      console.error('删除提问失败', err);
    } finally {
      setDeletingThread(false);
    }
  }, [activeQuestionId, deletingThread, loadQuestions]);

  const selectQuestion = useCallback(async (id: string) => {
    setActiveQuestionId(id);
    setActiveThread(null);
    await loadThreadDetail(id);
  }, [loadThreadDetail]);

  // ---- render ---------------------------------------------------------
  if (initialLoad && loading) {
    return (
      <MainLayout>
        <div className="container mx-auto flex max-w-7xl items-center justify-center px-4 py-24">
          <Loader2 className="h-8 w-8 animate-spin text-primary-500" />
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <div className="container mx-auto max-w-7xl px-4 py-8">
        <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h1 className="text-2xl font-bold text-surface-900 dark:text-surface-100">消息中心</h1>
            <p className="mt-1 text-sm text-surface-500 dark:text-surface-400">
              管理和老师的私信、班级通知与答疑线程
            </p>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row">
            <div className="relative w-full sm:w-72">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-surface-400" />
              <Input
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder={activeTab === 'private' ? '搜索老师、班级…' : activeTab === 'notices' ? '搜索通知标题、内容…' : '搜索问题、知识点…'}
                className="pl-10"
              />
            </div>
          </div>
        </div>

        <Tabs defaultValue="private" keepMounted={false} onValueChange={(v) => { setActiveTab(v); setSearchTerm(''); }}>
          <TabsList className="mb-4">
            <TabsTrigger value="private">
              <MessageSquare className="mr-2 h-4 w-4" />
              私信{renderTabCount(privateUnreadCount)}
            </TabsTrigger>
            <TabsTrigger value="notices">
              <Bell className="mr-2 h-4 w-4" />
              通知{renderTabCount(noticePendingCount)}
            </TabsTrigger>
            <TabsTrigger value="questions">
              <HelpCircle className="mr-2 h-4 w-4" />
              答疑{renderTabCount(questionAnsweredCount)}
            </TabsTrigger>
          </TabsList>

          {/* ============================================================ PRIVATE */}
          <TabsContent value="private" className="mt-0">
            <div className="grid min-h-[620px] grid-cols-1 gap-4 lg:grid-cols-[340px_1fr]">
              <Card>
                <CardContent className="p-0">
                  <div className="border-b border-surface-100 p-4 dark:border-surface-800">
                    <Button
                      className="w-full"
                      onClick={() => {
                        setContactSearch('');
                        setSelectedTeacherId(availableContacts[0]?.id ?? '');
                        setNewConvOpen(true);
                      }}
                    >
                      <Plus className="mr-2 h-4 w-4" />
                      新建对话
                    </Button>
                  </div>
                  {filteredConversations.map((c) => (
                    <button
                      key={c.id}
                      type="button"
                      onClick={() => openConversation(c.id)}
                      className={cn(
                        'w-full border-b border-surface-100 p-4 text-left last:border-b-0 hover:bg-surface-50 dark:border-surface-800 dark:hover:bg-surface-800',
                        activeConvId === c.id && 'bg-primary-50 dark:bg-primary-950/30',
                      )}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="font-medium text-surface-900 dark:text-surface-100">{c.teacherName}</div>
                          <div className="text-xs text-surface-500 dark:text-surface-400">{c.scope}</div>
                        </div>
                        <Badge variant={c.unread > 0 ? 'warning' : 'secondary'}>
                          {c.unread > 0 ? `未读 ${c.unread}` : '已读'}
                        </Badge>
                      </div>
                      <p className="mt-2 line-clamp-2 text-sm text-surface-600 dark:text-surface-300">{c.lastMessage}</p>
                      <div className="mt-2 text-xs text-surface-400">{c.lastTime}</div>
                    </button>
                  ))}
                </CardContent>
              </Card>

              <Card>
                <CardContent className="flex h-full flex-col p-0">
                  {activeConv ? (
                    <>
                      <div className="border-b border-surface-100 p-5 dark:border-surface-800">
                        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                          <div>
                            <div className="text-lg font-semibold text-surface-900 dark:text-surface-100">
                              {activeConv.teacher_name}
                            </div>
                            <div className="text-sm text-surface-500 dark:text-surface-400">{activeConv.scope}</div>
                          </div>
                          <div className="flex flex-wrap gap-2">
                            <Button variant="outline" size="sm" onClick={() => archiveConversation(activeConv.id)}>
                              <Archive className="mr-2 h-4 w-4" />归档
                            </Button>
                            <Button variant="outline" size="sm" onClick={() => deleteConversation(activeConv.id)}>
                              <Trash2 className="mr-2 h-4 w-4" />删除
                            </Button>
                          </div>
                        </div>
                      </div>
                      <div className="flex-1 space-y-4 overflow-y-auto p-5">
                        {activeConv.messages.map((msg) => (
                          <div key={msg.id} className="flex w-full">
                            <div className={cn('max-w-[80%]', msg.from === 'student' ? 'ml-auto text-right' : 'mr-auto')}>
                              <div className={cn(
                                'inline-block rounded-lg px-4 py-3 text-sm',
                                msg.from === 'student'
                                  ? 'bg-primary-600 text-white'
                                  : 'bg-surface-100 text-surface-800 dark:bg-surface-800 dark:text-surface-100',
                              )}>
                                {msg.text}
                              </div>
                              <div className={cn('mt-1 flex gap-2 text-xs text-surface-400', msg.from === 'student' ? 'justify-end' : 'justify-start')}>
                                <span>{formatRelativeTime(msg.time)}</span>
                                {msg.from === 'student' && <span>{msg.read_by_recipient ? '老师已读' : '老师未读'}</span>}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                      <div className="border-t border-surface-100 p-4 dark:border-surface-800">
                        <form className="flex gap-2" onSubmit={sendPrivateMessage}>
                          <Input value={messageDraft} onChange={(e) => setMessageDraft(e.target.value)} placeholder="输入给老师的消息" />
                          <Button type="submit" size="icon" aria-label="发送私信" disabled={sendingMsg}>
                            {sendingMsg ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                          </Button>
                        </form>
                      </div>
                    </>
                  ) : (
                    <div className="flex h-full items-center justify-center p-8 text-sm text-surface-500 dark:text-surface-400">
                      暂无可显示的私信对话
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* ============================================================ NOTICES */}
          <TabsContent value="notices" className="mt-0">
            <div className="mb-4 flex flex-wrap gap-2">
              {noticeStatuses.map((s) => (
                <Button key={s} variant={noticeStatus === s ? 'primary' : 'outline'} size="sm" onClick={() => setNoticeStatus(s)}>{s}</Button>
              ))}
            </div>
            <div className="grid min-h-[620px] grid-cols-1 gap-4 lg:grid-cols-[360px_1fr]">
              <Card>
                <CardContent className="p-0">
                  {filteredNotices.map((n) => (
                    <button
                      key={n.id}
                      type="button"
                      onClick={() => setActiveNoticeId(n.id)}
                      className={cn(
                        'w-full border-b border-surface-100 p-4 text-left last:border-b-0 hover:bg-surface-50 dark:border-surface-800 dark:hover:bg-surface-800',
                        activeNotice?.id === n.id && 'bg-primary-50 dark:bg-primary-950/30',
                      )}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="font-medium text-surface-900 dark:text-surface-100">{n.title}</div>
                          <div className="mt-1 text-xs text-surface-500 dark:text-surface-400">{n.className}</div>
                        </div>
                        <Badge variant={n.confirmed ? 'success' : 'warning'}>{n.confirmed ? '已确认' : '待确认'}</Badge>
                      </div>
                      <div className="mt-2 text-xs text-surface-400">{n.publishedAt}</div>
                    </button>
                  ))}
                </CardContent>
              </Card>

              <Card>
                <CardContent className="p-6">
                  {activeNotice && (
                    <div className="space-y-5">
                      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                        <div>
                          <div className="text-sm text-surface-500 dark:text-surface-400">{activeNotice.className} · {activeNotice.publishedAt}</div>
                          <h2 className="mt-2 text-xl font-semibold text-surface-900 dark:text-surface-100">{activeNotice.title}</h2>
                        </div>
                        <Badge variant={activeNotice.confirmed ? 'success' : 'warning'}>{activeNotice.confirmed ? '已确认收到' : '待确认'}</Badge>
                      </div>
                      <p className="leading-7 text-surface-700 dark:text-surface-300">{activeNotice.body}</p>
                      {activeNotice.attachments.length > 0 && (
                        <div className="space-y-2">
                          {activeNotice.attachments.map((a) => (
                            <div key={a} className="flex items-center gap-2 rounded-md border border-surface-200 p-3 text-sm dark:border-surface-700">
                              <Paperclip className="h-4 w-4 text-surface-400" />{a}
                            </div>
                          ))}
                        </div>
                      )}
                      <Button onClick={() => confirmNotice(activeNotice.id)} disabled={activeNotice.confirmed || confirming === activeNotice.id}>
                        {confirming === activeNotice.id
                          ? <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          : <CheckCircle2 className="mr-2 h-4 w-4" />}
                        {activeNotice.confirmed ? '已确认收到' : '确认收到'}
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* ============================================================ QUESTIONS */}
          <TabsContent value="questions" className="mt-0">
            <div className="grid min-h-[620px] grid-cols-1 gap-4 lg:grid-cols-[360px_1fr]">
              <Card>
                <CardContent className="space-y-4 p-4">
                  <div className="space-y-2">
                    <select
                      value={selectedQTeacherId}
                      onChange={(e) => setSelectedQTeacherId(e.target.value)}
                      className="h-10 w-full rounded-md border border-surface-200 bg-white px-3 text-sm dark:border-surface-700 dark:bg-surface-800 dark:text-surface-100"
                    >
                      {contacts.map((c) => <option key={c.id} value={c.id}>{c.teacher_name} · {c.scope}</option>)}
                    </select>
                    <textarea
                      value={questionDraft}
                      onChange={(e) => setQuestionDraft(e.target.value)}
                      placeholder="新建一个要问老师的问题"
                      className="min-h-24 w-full rounded-md border border-surface-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 dark:border-surface-700 dark:bg-surface-800 dark:text-surface-100"
                    />
                    <Button className="w-full" onClick={createQuestion} disabled={submittingQ}>
                      {submittingQ ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <HelpCircle className="mr-2 h-4 w-4" />}
                      提交问题
                    </Button>
                    <Button className="w-full" variant="outline" onClick={() => { setImportOpen(true); loadMistakesForImport(); }}>
                      <Import className="mr-2 h-4 w-4" />导入问题
                    </Button>
                  </div>
                  <div className="divide-y divide-surface-100 dark:divide-surface-800">
                    {filteredQuestions.map((q) => (
                      <button
                        key={q.id}
                        type="button"
                        onClick={() => selectQuestion(q.id)}
                        className={cn(
                          'w-full py-4 text-left hover:bg-surface-50 dark:hover:bg-surface-800',
                          activeQuestionId === q.id && 'bg-primary-50 dark:bg-primary-950/30',
                        )}
                      >
                        <div className="flex items-start justify-between gap-3 px-3">
                          <div>
                            <div className="font-medium text-surface-900 dark:text-surface-100">{q.title}</div>
                            <div className="mt-1 text-xs text-surface-500 dark:text-surface-400">
                              {q.teacher_name} · {q.source} · {formatRelativeTime(q.last_update)}
                            </div>
                          </div>
                          <Badge variant={statusVariant[q.status as keyof typeof statusVariant] ?? 'secondary'}>{q.status}</Badge>
                        </div>
                      </button>
                    ))}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="p-6">
                  {activeThread ? (
                    <div className="space-y-5">
                      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                        <div>
                          <div className="text-sm text-surface-500 dark:text-surface-400">
                            提问给：{activeThread.teacher_name} · 来源：{activeThread.source}
                          </div>
                          <h2 className="mt-2 text-xl font-semibold text-surface-900 dark:text-surface-100">{activeThread.title}</h2>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge variant={statusVariant[activeThread.status as keyof typeof statusVariant] ?? 'secondary'}>{activeThread.status}</Badge>
                          <Button variant="outline" size="sm" onClick={deleteThread} disabled={deletingThread}>
                            {deletingThread ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
                          </Button>
                        </div>
                      </div>
                      {activeThread.source !== '消息中心' && (
                        <div className="rounded-md bg-surface-50 p-4 text-sm leading-6 text-surface-700 dark:bg-surface-800 dark:text-surface-300">
                          {activeThread.context}
                        </div>
                      )}
                      <div className="space-y-3">
                        {activeThread.messages.map((msg) => (
                          <div key={msg.id} className={cn('rounded-md border p-3', msg.from === 'student' ? 'border-primary-200 bg-primary-50/30 dark:border-primary-800 dark:bg-primary-950/20' : 'border-surface-200 dark:border-surface-700')}>
                            <div className="mb-1 flex items-center gap-2">
                              <span className={cn('text-xs font-medium', msg.from === 'student' ? 'text-primary-600 dark:text-primary-400' : 'text-emerald-600 dark:text-emerald-400')}>
                                {msg.from === 'student' ? '我' : activeThread.teacher_name}
                              </span>
                            </div>
                            <div className="text-sm text-surface-700 dark:text-surface-300">{msg.text}</div>
                            <div className="mt-2 text-xs text-surface-400">{formatRelativeTime(msg.time)}</div>
                          </div>
                        ))}
                      </div>
                      <div className="space-y-2 border-t border-surface-100 pt-4 dark:border-surface-800">
                        <textarea
                          value={followUpDraft}
                          onChange={(e) => setFollowUpDraft(e.target.value)}
                          placeholder="继续追问这个问题"
                          className="min-h-24 w-full rounded-md border border-surface-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 dark:border-surface-700 dark:bg-surface-800 dark:text-surface-100"
                        />
                        <div className="flex justify-end">
                          <Button onClick={createFollowUp} disabled={sendingFollowUp}>
                            {sendingFollowUp ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Send className="mr-2 h-4 w-4" />}
                            追问
                          </Button>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="flex h-full items-center justify-center p-8 text-sm text-surface-500 dark:text-surface-400">
                      暂无提问详情
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>

        {/* Import modal — browse mistakes */}
        <Modal isOpen={importOpen} onClose={() => { setImportOpen(false); setSelectedMistakeId(''); setImportQuestionText(''); }} title="从错题本导入" className="max-w-xl">
          <div className="space-y-4">
            <label className="block text-sm font-medium text-surface-700 dark:text-surface-300">选择老师</label>
            <select value={importTeacherId} onChange={(e) => setImportTeacherId(e.target.value)}
              className="h-10 w-full rounded-md border border-surface-200 bg-white px-3 text-sm dark:border-surface-700 dark:bg-surface-800 dark:text-surface-100">
              {contacts.map((c) => <option key={c.id} value={c.id}>{c.teacher_name} · {c.scope}</option>)}
            </select>

            <label className="block text-sm font-medium text-surface-700 dark:text-surface-300">选择错题</label>
            {loadingMistakes ? (
              <div className="flex justify-center py-8"><Loader2 className="h-6 w-6 animate-spin text-primary-500" /></div>
            ) : mistakes.length === 0 ? (
              <div className="rounded-md border border-surface-200 p-8 text-center text-sm text-surface-500 dark:border-surface-700 dark:text-surface-400">
                暂无错题记录，完成练习后错题会自动收集到这里
              </div>
            ) : (
              <div className="max-h-80 space-y-1 overflow-y-auto rounded-md border border-surface-200 dark:border-surface-700">
                {mistakes.map((m) => (
                  <button
                    key={m.id}
                    type="button"
                    onClick={() => setSelectedMistakeId(m.id)}
                    className={cn(
                      'w-full px-4 py-3 text-left transition-colors hover:bg-surface-50 dark:hover:bg-surface-800',
                      selectedMistakeId === m.id
                        ? 'bg-primary-50 ring-1 ring-inset ring-primary-200 dark:bg-primary-950/30 dark:ring-primary-800'
                        : 'border-b border-surface-100 last:border-b-0 dark:border-surface-800',
                    )}
                  >
                    <div className="text-sm font-medium text-surface-900 dark:text-surface-100">
                      {m.exercise.title}
                    </div>
                    <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-surface-500 dark:text-surface-400">
                      {m.exercise.knowledgePoints.slice(0, 3).map((kp) => (
                        <span key={kp} className="rounded bg-surface-100 px-1.5 py-0.5 dark:bg-surface-800">{kp}</span>
                      ))}
                      {m.diagnosis.errorType && (
                        <span className="text-red-500">{m.diagnosis.errorType}</span>
                      )}
                      <span>错误 {m.errorCount} 次</span>
                    </div>
                  </button>
                ))}
              </div>
            )}

            {selectedMistakeId && (
              <div className="space-y-1">
                <label className="block text-sm font-medium text-surface-700 dark:text-surface-300">
                  你的疑问（可选）
                </label>
                <textarea
                  value={importQuestionText}
                  onChange={(e) => setImportQuestionText(e.target.value)}
                  placeholder="例如：我不明白为什么这里要用洛必达法则，什么时候该用？"
                  className="min-h-20 w-full rounded-md border border-surface-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 dark:border-surface-700 dark:bg-surface-800 dark:text-surface-100"
                />
              </div>
            )}

            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => { setImportOpen(false); setSelectedMistakeId(''); setImportQuestionText(''); }}>取消</Button>
              <Button onClick={importQuestion} disabled={importing || !selectedMistakeId}>
                {importing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}导入选中
              </Button>
            </div>
          </div>
        </Modal>

        {/* New conversation modal */}
        <Modal isOpen={newConvOpen} onClose={() => { setNewConvOpen(false); setContactSearch(''); }} title="新建私信对话" className="max-w-lg">
          <div className="space-y-4">
            <label className="block text-sm font-medium text-surface-700 dark:text-surface-300">选择联系人</label>
            <Input value={contactSearch} onChange={(e) => { setContactSearch(e.target.value); if (!e.target.value.trim()) setSelectedTeacherId(''); }}
              placeholder="搜索老师姓名或 ID…" />
            {allSearchResults.length > 0 ? (
              <div className="max-h-48 space-y-0.5 overflow-y-auto rounded-md border border-surface-200 dark:border-surface-700">
                {allSearchResults.map((c) => (
                  <button key={c.id} type="button"
                    onClick={() => { setSelectedTeacherId(c.id); setContactSearch(''); setGlobalSearchResults([]); }}
                    className={cn('w-full px-4 py-2.5 text-left text-sm hover:bg-surface-50 dark:hover:bg-surface-800',
                      selectedTeacherId === c.id && 'bg-primary-50 ring-1 ring-inset ring-primary-200 dark:bg-primary-950/30 dark:ring-primary-800')}>
                    <div className="font-medium text-surface-900 dark:text-surface-100">{c.teacher_name}</div>
                    <div className="flex items-center justify-between text-xs text-surface-500 dark:text-surface-400">
                      <span>{c.scope || '全校'}</span>
                      <span className="font-mono text-surface-400">{c.id}</span>
                    </div>
                  </button>
                ))}
              </div>
            ) : contactSearch.trim() ? (
              <p className="text-sm text-surface-500 dark:text-surface-400">未找到匹配的教师。</p>
            ) : availableContacts.length === 0 ? (
              <p className="text-sm text-surface-500 dark:text-surface-400">输入教师姓名或 ID 搜索并建立对话。</p>
            ) : null}
            <textarea value={newConvDraft} onChange={(e) => setNewConvDraft(e.target.value)}
              placeholder="可以先写一句要发给老师的消息"
              className="min-h-28 w-full rounded-md border border-surface-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 dark:border-surface-700 dark:bg-surface-800 dark:text-surface-100"
            />
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => { setNewConvOpen(false); setContactSearch(''); }}>取消</Button>
              <Button onClick={createConversation} disabled={!selectedTeacherId || creatingConv}>
                {creatingConv ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}创建对话
              </Button>
            </div>
          </div>
        </Modal>
      </div>
    </MainLayout>
  );
};
