package teacher

import (
	"context"
	"errors"
	"testing"
	"time"
)

func TestGetDashboardStatsComputesActiveRate(t *testing.T) {
	now := time.Date(2026, time.April, 27, 15, 0, 0, 0, time.UTC)
	repo := &fakeTeacherRepo{
		classIDs:            []string{"class-1"},
		students:            []string{"student-1", "student-2"},
		activeSessionsSince: 1,
	}
	service := newTeacherTestService(repo, now)

	stats, err := service.GetDashboardStats(context.Background(), "teacher-1")
	if err != nil {
		t.Fatalf("GetDashboardStats() error = %v", err)
	}
	if stats.TotalStudents != 2 || stats.ActiveToday != 50 || stats.AvgCompletionRate != 0 || stats.PendingGrading != 0 {
		t.Fatalf("stats = %#v", stats)
	}
	if !repo.lastSince.Equal(startOfDay(now)) {
		t.Fatalf("since = %v, want start of day", repo.lastSince)
	}
}

func TestListStudentsNormalizesPaginationAndReturnsTotalPages(t *testing.T) {
	displayName := "张三"
	repo := &fakeTeacherRepo{
		studentListItems: []StudentListItem{{
			ID:          "student-1",
			Username:    "zhangsan",
			Email:       "z@example.com",
			DisplayName: &displayName,
			ClassID:     "class-1",
			ClassName:   "高一三班",
		}},
		studentListTotal: 25,
	}
	service := newTeacherTestService(repo, time.Date(2026, time.April, 27, 15, 0, 0, 0, time.UTC))

	response, err := service.ListStudents(context.Background(), "teacher-1", StudentListFilter{ClassID: " class-1 ", Search: " 张 ", Page: -1, PageSize: 500})
	if err != nil {
		t.Fatalf("ListStudents() error = %v", err)
	}
	if response.Total != 25 || response.Page != 1 || response.PageSize != 100 || response.TotalPages != 1 {
		t.Fatalf("response = %#v", response)
	}
	if repo.lastStudentFilter.ClassID != "class-1" || repo.lastStudentFilter.Search != "张" || repo.lastStudentFilter.Page != 1 || repo.lastStudentFilter.PageSize != 100 {
		t.Fatalf("filter = %#v", repo.lastStudentFilter)
	}
}

func TestGetAnalyticsBuildsOverviewMasteryWeeklyAndRanking(t *testing.T) {
	now := time.Date(2026, time.April, 27, 15, 0, 0, 0, time.UTC)
	repo := &fakeTeacherRepo{
		classIDs:                []string{"class-1"},
		students:                []string{"student-1", "student-2"},
		avgScore:                82.25,
		avgScoreOK:              true,
		sumSeconds:              7200,
		distinctAttemptStudents: 1,
		profiles: []StudentProfile{
			{StudentID: "student-1", MasteryVector: map[string]float64{"limit": 0.8, "derivative": 0.4}},
			{StudentID: "student-2", MasteryVector: map[string]float64{"limit": 0.6}},
		},
		knowledgeNames: map[string]string{"limit": "极限", "derivative": "导数"},
		weeklyActivity: map[string]int{"2026-04-27": 1},
		topStudents: []StudentScore{
			{StudentID: "student-2", AvgScore: 95.4},
		},
		displayNames: map[string]string{"student-2": "李四"},
	}
	service := newTeacherTestService(repo, now)

	analytics, err := service.GetAnalytics(context.Background(), "teacher-1", "week")
	if err != nil {
		t.Fatalf("GetAnalytics() error = %v", err)
	}
	if analytics.Overview.TotalStudents != 2 || analytics.Overview.AvgScore != 82.3 || analytics.Overview.AvgCompletionRate != 50 || analytics.Overview.AvgStudyHours != 1 {
		t.Fatalf("overview = %#v", analytics.Overview)
	}
	if len(analytics.KnowledgePoints) != 2 || analytics.KnowledgePoints[0].ConceptID != "limit" || analytics.KnowledgePoints[0].Mastery != 70 {
		t.Fatalf("knowledge points = %#v", analytics.KnowledgePoints)
	}
	if len(analytics.WeeklyActivity) != 7 || analytics.WeeklyActivity[6].Date != "2026-04-27" || analytics.WeeklyActivity[6].ActiveRate != 50 {
		t.Fatalf("weekly = %#v", analytics.WeeklyActivity)
	}
	if len(analytics.TopStudents) != 1 || analytics.TopStudents[0].Name != "李四" || analytics.TopStudents[0].Rank != 1 {
		t.Fatalf("top students = %#v", analytics.TopStudents)
	}
}

func TestGetClassAnalyticsValidatesOwnershipAndBuildsAlerts(t *testing.T) {
	now := time.Date(2026, time.April, 27, 15, 0, 0, 0, time.UTC)
	repo := &fakeTeacherRepo{}
	service := newTeacherTestService(repo, now)
	if _, err := service.GetClassAnalytics(context.Background(), "teacher-1", "class-1"); !errors.Is(err, ErrNotFound) {
		t.Fatalf("GetClassAnalytics(unowned) error = %v, want ErrNotFound", err)
	}

	repo.classOwned = true
	repo.students = []string{"student-1", "student-2"}
	repo.profiles = []StudentProfile{
		{StudentID: "student-1", MasteryVector: map[string]float64{"limit": 0.9}},
		{StudentID: "student-2", MasteryVector: map[string]float64{"limit": 0.3}},
	}
	repo.knowledgeNames = map[string]string{"limit": "极限"}
	repo.avgScore = 75
	repo.avgScoreOK = true
	repo.sumSeconds = 3600
	repo.commonErrors = []CommonErrorAggregate{{Content: "符号错误", Count: 2, Topic: "符号", ErrorType: "symbolic"}}
	repo.lowScoreStudents = map[string]float64{"student-2": 55.4}
	repo.activeStudentSet = map[string]struct{}{"student-1": {}}
	repo.displayNames = map[string]string{"student-1": "张三", "student-2": "李四"}
	repo.topStudents = []StudentScore{{StudentID: "student-1", AvgScore: 91}}
	repo.ids = []string{"alert-low", "error-1"}

	response, err := service.GetClassAnalytics(context.Background(), "teacher-1", "class-1")
	if err != nil {
		t.Fatalf("GetClassAnalytics() error = %v", err)
	}
	if response.Stats.AverageMastery != 0.6 || response.Stats.AverageScore != 75 || response.Stats.WeeklyStudyHours != 0.5 {
		t.Fatalf("stats = %#v", response.Stats)
	}
	if len(response.CommonErrors) != 1 || response.CommonErrors[0].ID != "alert-low" {
		t.Fatalf("common errors = %#v", response.CommonErrors)
	}
	if len(response.Alerts) != 1 || response.Alerts[0].StudentID != "student-2" || response.Alerts[0].Severity != "high" {
		t.Fatalf("alerts = %#v", response.Alerts)
	}
	if len(response.StudentRankings) != 1 || response.StudentRankings[0].Name != "张三" {
		t.Fatalf("rankings = %#v", response.StudentRankings)
	}
}

func TestGetStudentDetailBuildsSummaryAndActivity(t *testing.T) {
	now := time.Date(2026, time.April, 27, 15, 0, 0, 0, time.UTC)
	joinedAt := now.AddDate(0, -1, 0)
	lastActive := now.Add(-time.Hour)
	sessionEnd := now.Add(-30 * time.Minute)
	explanation := "概念混淆"
	displayName := "张三"
	repo := &fakeTeacherRepo{
		enrollment:      StudentEnrollment{ClassID: "class-1", ClassName: "高一三班", JoinedAt: &joinedAt},
		enrollmentFound: true,
		userInfo:        UserInfo{ID: "student-1", Username: "zhangsan", Email: "z@example.com", DisplayName: &displayName},
		userFound:       true,
		profile:         StudentProfile{StudentID: "student-1", TotalExercises: 10, CorrectCount: 7, TotalStudyTimeMinutes: 90, MasteryVector: map[string]float64{"limit": 0.8}},
		profileFound:    true,
		avgStudentScore: 88,
		avgStudentOK:    true,
		students:        []string{"student-2", "student-1"},
		rankScores:      []StudentScore{{StudentID: "student-2", AvgScore: 90}, {StudentID: "student-1", AvgScore: 88}},
		lastSession:     &lastActive,
		sessionDays:     []time.Time{now, now.AddDate(0, 0, -1)},
		knowledgeNames:  map[string]string{"limit": "极限"},
		conceptCounts:   map[string]int{"limit": 3},
		recentAttempts:  []RecentAttempt{{ID: "attempt-1", IsCorrect: true, Score: 88, StartedAt: now.Add(-2 * time.Hour), Title: "极限练习"}},
		recentSessions:  []RecentSession{{ID: "session-1", StartedAt: now.Add(-time.Hour), EndedAt: &sessionEnd}},
		recentMistakes:  []StudentMistake{{ID: "mistake-1", Content: "导数题", ErrorType: "conceptual", Date: "2026-04-27T12:00:00.000000", Explanation: &explanation}},
	}
	service := newTeacherTestService(repo, now)

	response, err := service.GetStudentDetail(context.Background(), "teacher-1", "student-1")
	if err != nil {
		t.Fatalf("GetStudentDetail() error = %v", err)
	}
	if response.Student.Name != "张三" || response.Student.Rank != 2 || response.Student.CorrectRate != 70 || response.Student.TotalStudyHours != 1.5 || response.Student.StreakDays != 2 {
		t.Fatalf("student = %#v", response.Student)
	}
	if len(response.TopicMastery) != 1 || response.TopicMastery[0].Topic != "极限" || response.TopicMastery[0].ExerciseCount != 3 {
		t.Fatalf("topic mastery = %#v", response.TopicMastery)
	}
	if len(response.RecentActivity) != 2 || response.RecentActivity[0].Type != "session" || response.RecentActivity[1].Status != "success" {
		t.Fatalf("recent activity = %#v", response.RecentActivity)
	}
	if len(response.RecentMistakes) != 1 || response.RecentMistakes[0].Explanation == nil {
		t.Fatalf("recent mistakes = %#v", response.RecentMistakes)
	}
}

func TestGetStudentDetailDistinguishesMissingStudentAccount(t *testing.T) {
	repo := &fakeTeacherRepo{
		enrollment:      StudentEnrollment{ClassID: "class-1", ClassName: "高一三班"},
		enrollmentFound: true,
		userFound:       false,
	}
	service := newTeacherTestService(repo, time.Date(2026, time.April, 27, 15, 0, 0, 0, time.UTC))

	_, err := service.GetStudentDetail(context.Background(), "teacher-1", "student-1")
	if !errors.Is(err, ErrStudentNotFound) {
		t.Fatalf("GetStudentDetail() error = %v, want ErrStudentNotFound", err)
	}
}

func newTeacherTestService(repo *fakeTeacherRepo, now time.Time) *Service {
	service, err := NewService(repo)
	if err != nil {
		panic(err)
	}
	service.now = func() time.Time { return now }
	service.idFactory = repo.nextID
	return service
}

type fakeTeacherRepo struct {
	classIDs                []string
	students                []string
	activeSessionsSince     int
	lastSince               time.Time
	avgScore                float64
	avgScoreOK              bool
	sumSeconds              int
	distinctAttemptStudents int
	profiles                []StudentProfile
	knowledgeNames          map[string]string
	weeklyActivity          map[string]int
	topStudents             []StudentScore
	displayNames            map[string]string
	classOwned              bool
	commonErrors            []CommonErrorAggregate
	lowScoreStudents        map[string]float64
	activeStudentSet        map[string]struct{}
	enrollment              StudentEnrollment
	enrollmentFound         bool
	userInfo                UserInfo
	userFound               bool
	profile                 StudentProfile
	profileFound            bool
	avgStudentScore         float64
	avgStudentOK            bool
	rankScores              []StudentScore
	lastSession             *time.Time
	sessionDays             []time.Time
	conceptCounts           map[string]int
	recentAttempts          []RecentAttempt
	recentSessions          []RecentSession
	recentMistakes          []StudentMistake
	studentListItems        []StudentListItem
	studentListTotal        int
	lastStudentFilter       StudentListFilter
	ids                     []string
	idIndex                 int
}

func (r *fakeTeacherRepo) nextID() (string, error) {
	if r.idIndex >= len(r.ids) {
		r.idIndex++
		return "id", nil
	}
	id := r.ids[r.idIndex]
	r.idIndex++
	return id, nil
}

func (r *fakeTeacherRepo) ListTeacherClassIDs(context.Context, string) ([]string, error) {
	return r.classIDs, nil
}

func (r *fakeTeacherRepo) ListStudentsInClasses(context.Context, []string) ([]string, error) {
	return r.students, nil
}

func (r *fakeTeacherRepo) ListTeacherStudents(_ context.Context, _ string, filter StudentListFilter) ([]StudentListItem, int, error) {
	r.lastStudentFilter = filter
	return r.studentListItems, r.studentListTotal, nil
}

func (r *fakeTeacherRepo) CountActiveSessionsSince(_ context.Context, _ []string, since time.Time) (int, error) {
	r.lastSince = since
	return r.activeSessionsSince, nil
}

func (r *fakeTeacherRepo) AverageAttemptScore(context.Context, []string, *time.Time) (float64, bool, error) {
	return r.avgScore, r.avgScoreOK, nil
}

func (r *fakeTeacherRepo) SumAttemptSeconds(context.Context, []string, *time.Time) (int, error) {
	return r.sumSeconds, nil
}

func (r *fakeTeacherRepo) CountDistinctAttemptStudentsSince(context.Context, []string, time.Time) (int, error) {
	return r.distinctAttemptStudents, nil
}

func (r *fakeTeacherRepo) ListProfiles(context.Context, []string) ([]StudentProfile, error) {
	return r.profiles, nil
}

func (r *fakeTeacherRepo) KnowledgeNames(context.Context, []string) (map[string]string, error) {
	return r.knowledgeNames, nil
}

func (r *fakeTeacherRepo) WeeklySessionActivity(context.Context, []string, time.Time) (map[string]int, error) {
	return r.weeklyActivity, nil
}

func (r *fakeTeacherRepo) TopStudentsByAverageScore(context.Context, []string, int) ([]StudentScore, error) {
	return r.topStudents, nil
}

func (r *fakeTeacherRepo) UserDisplayNames(context.Context, []string) (map[string]string, error) {
	return r.displayNames, nil
}

func (r *fakeTeacherRepo) ClassOwnedByTeacher(context.Context, string, string) (bool, error) {
	return r.classOwned, nil
}

func (r *fakeTeacherRepo) CommonErrors(context.Context, []string, int) ([]CommonErrorAggregate, error) {
	return r.commonErrors, nil
}

func (r *fakeTeacherRepo) LowScoreStudents(context.Context, []string, float64) (map[string]float64, error) {
	return r.lowScoreStudents, nil
}

func (r *fakeTeacherRepo) ActiveStudentIDsSince(context.Context, []string, time.Time) (map[string]struct{}, error) {
	return r.activeStudentSet, nil
}

func (r *fakeTeacherRepo) StudentEnrollmentForTeacher(context.Context, string, string) (StudentEnrollment, bool, error) {
	return r.enrollment, r.enrollmentFound, nil
}

func (r *fakeTeacherRepo) GetUser(context.Context, string) (UserInfo, bool, error) {
	return r.userInfo, r.userFound, nil
}

func (r *fakeTeacherRepo) GetProfile(context.Context, string) (StudentProfile, bool, error) {
	return r.profile, r.profileFound, nil
}

func (r *fakeTeacherRepo) AverageStudentScore(context.Context, string) (float64, bool, error) {
	return r.avgStudentScore, r.avgStudentOK, nil
}

func (r *fakeTeacherRepo) RankByAverageScore(context.Context, []string) ([]StudentScore, error) {
	return r.rankScores, nil
}

func (r *fakeTeacherRepo) LastSessionStartedAt(context.Context, string) (*time.Time, error) {
	return r.lastSession, nil
}

func (r *fakeTeacherRepo) ListSessionDays(context.Context, string) ([]time.Time, error) {
	return r.sessionDays, nil
}

func (r *fakeTeacherRepo) AttemptConceptCounts(context.Context, string) (map[string]int, error) {
	return r.conceptCounts, nil
}

func (r *fakeTeacherRepo) RecentAttempts(context.Context, string, int) ([]RecentAttempt, error) {
	return r.recentAttempts, nil
}

func (r *fakeTeacherRepo) RecentSessions(context.Context, string, int) ([]RecentSession, error) {
	return r.recentSessions, nil
}

func (r *fakeTeacherRepo) RecentMistakes(context.Context, string, int) ([]StudentMistake, error) {
	return r.recentMistakes, nil
}
