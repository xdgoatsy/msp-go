package xidian

import (
	"context"
	"fmt"
	"net/http"
	"net/url"
	"regexp"
	"strings"

	xidianapp "mathstudy/backend-go/internal/application/xidian"
)

func (c *Client) ensureEhallLogin(ctx context.Context, session *session) error {
	payload, status, headers, err := session.getJSON(ctx, c.config.EhallBase+"/jsonp/getAppUsageMonitor.json?type=uv", nil, ehallHeaders())
	if err != nil {
		return err
	}
	if err := ensureNotRedirected(status, headers); err != nil {
		return err
	}
	if loggedIn, _ := payload["hasLogin"].(bool); !loggedIn {
		return xidianapp.ServiceError{Code: "CAPTCHA_REQUIRED", Message: "会话已过期，请重新验证", Status: 409}
	}
	return nil
}

func (c *Client) useEhallApp(ctx context.Context, session *session, appID string) (string, error) {
	response, err := session.request(ctx, http.MethodGet, c.config.EhallBase+"/appShow", url.Values{"appId": {appID}}, nil, ehallHeaders())
	if err != nil {
		return "", err
	}
	defer response.Body.Close()
	if err := ensureNotRedirected(response.StatusCode, response.Header); err != nil {
		return "", err
	}
	location := response.Header.Get("Location")
	if location == "" {
		return "", xidianapp.ServiceError{Code: "DATA_FETCH_FAILED", Message: "无法打开教务应用", Status: 400}
	}
	return sessionIDPattern.ReplaceAllString(location, "?"), nil
}

func (c *Client) currentSemesterEhall(ctx context.Context, session *session) (string, error) {
	payload, status, headers, err := session.getJSON(ctx, c.config.EhallBase+"/jwapp/sys/wdkb/modules/jshkcb/dqxnxq.do", url.Values{}, ehallHeaders())
	if err != nil {
		return "", err
	}
	if err := ensureNotRedirected(status, headers); err != nil {
		return "", err
	}
	rows := rowsFrom(payload, "datas", "dqxnxq")
	if len(rows) == 0 {
		return "", nil
	}
	value, _ := rowMap(rows[0])["DM"].(string)
	return value, nil
}

func (c *Client) termStartDayEhall(ctx context.Context, session *session, semesterCode string) (string, error) {
	parts := strings.Split(semesterCode, "-")
	yearPart := semesterCode
	termPart := ""
	if len(parts) >= 2 {
		yearPart = strings.Join(parts[:2], "-")
	}
	if len(parts) >= 3 {
		termPart = parts[2]
	}
	payload, status, headers, err := session.getJSON(ctx, c.config.EhallBase+"/jwapp/sys/wdkb/modules/jshkcb/cxjcs.do", url.Values{"XN": {yearPart}, "XQ": {termPart}}, ehallHeaders())
	if err != nil {
		return "", err
	}
	if err := ensureNotRedirected(status, headers); err != nil {
		return "", err
	}
	rows := rowsFrom(payload, "datas", "cxjcs")
	if len(rows) == 0 {
		return "", nil
	}
	value, _ := rowMap(rows[0])["XQKSRQ"].(string)
	return value, nil
}

func (c *Client) fetchClasstableEhall(ctx context.Context, session *session, username string) (map[string]any, error) {
	if err := c.ensureEhallLogin(ctx, session); err != nil {
		return nil, err
	}
	location, err := c.useEhallApp(ctx, session, ehallAppIDClasstable)
	if err != nil {
		return nil, err
	}
	_, _, _, _ = session.getJSON(ctx, location, nil, ehallHeaders())
	semesterCode, err := c.currentSemesterEhall(ctx, session)
	if err != nil {
		return nil, err
	}
	termStartDay, err := c.termStartDayEhall(ctx, session, semesterCode)
	if err != nil {
		return nil, err
	}
	payload, status, headers, err := session.getJSON(ctx, c.config.EhallBase+"/jwapp/sys/wdkb/modules/xskcb/xskcb.do", url.Values{"XNXQDM": {semesterCode}, "XH": {username}}, ehallHeaders())
	if err != nil {
		return nil, err
	}
	if err := ensureNotRedirected(status, headers); err != nil {
		return nil, err
	}
	data := mapValue(payload, "datas", "xskcb")
	ext := mapValue(data, "extParams")
	if intFromAny(ext["code"], 0) != 1 {
		message := "课表查询失败"
		if ext["msg"] != nil {
			message = fmtSprint(ext["msg"])
		}
		if strings.Contains(message, "课程未发布") {
			return emptyClasstable(semesterCode, termStartDay), nil
		}
		return nil, xidianapp.ServiceError{Code: "DATA_FETCH_FAILED", Message: message, Status: 400}
	}
	return buildClasstable(rowsFrom(payload, "datas", "xskcb"), semesterCode, termStartDay, false), nil
}

func (c *Client) fetchClasstableYjspt(ctx context.Context, session *session, username string) (map[string]any, error) {
	semesterPayload, status, headers, err := session.getJSON(ctx, c.config.YjsptBase+"/gsapp/sys/wdkbapp/modules/xskcb/kfdxnxqcx.do", url.Values{}, nil)
	if err != nil {
		return nil, err
	}
	if err := ensureNotRedirected(status, headers); err != nil {
		return nil, err
	}
	semesterCode := ""
	if rows := rowsFrom(semesterPayload, "datas", "kfdxnxqcx"); len(rows) > 0 {
		semesterCode, _ = rowMap(rows[0])["WID"].(string)
	}
	termStartDay := c.now().Format("2006-01-02")
	weekPayload, _, _, _ := session.getJSON(ctx, c.config.YjsptBase+"/gsapp/sys/yjsemaphome/portal/queryRcap.do", url.Values{"day": {c.now().Format("20060102")}}, nil)
	if match := integerPattern.FindString(strings.TrimSpace(stringFieldString(weekPayload, "xnxq"))); match != "" {
		currentWeek := intFromAny(match, 1)
		termStart := c.now().AddDate(0, 0, (1-currentWeek)*7-int(c.now().Weekday()))
		termStartDay = termStart.Format("2006-01-02")
	}
	classPayload, status, headers, err := session.getJSON(ctx, c.config.YjsptBase+"/gsapp/sys/wdkbapp/modules/xskcb/xspkjgcx.do", url.Values{"XNXQDM": {semesterCode}}, nil)
	if err != nil {
		return nil, err
	}
	if err := ensureNotRedirected(status, headers); err != nil {
		return nil, err
	}
	if code, _ := classPayload["code"].(string); code != "" && code != "0" {
		message, _ := classPayload["msg"].(string)
		if strings.Contains(message, "课程未发布") {
			return emptyClasstable(semesterCode, termStartDay), nil
		}
		if message == "" {
			message = "课表查询失败"
		}
		return nil, xidianapp.ServiceError{Code: "DATA_FETCH_FAILED", Message: message, Status: 400}
	}
	result := buildClasstable(rowsFrom(classPayload, "datas", "xspkjgcx"), semesterCode, termStartDay, true)
	notPayload, _, _, _ := session.getJSON(ctx, c.config.YjsptBase+"/gsapp/sys/wdkbapp/modules/xskcb/xswsckbkc.do", url.Values{"XNXQDM": {semesterCode}, "XH": {username}}, nil)
	result["not_arranged"] = buildNotArranged(rowsFrom(notPayload, "datas", "xswsckbkc"), true)
	return result, nil
}

func buildClasstable(rows []any, semesterCode string, termStartDay string, postgraduate bool) map[string]any {
	classDetail := make([]map[string]any, 0)
	timeArrangement := make([]map[string]any, 0)
	index := map[string]int{}
	semesterLength := 1
	for _, raw := range rows {
		row := rowMap(raw)
		name := fmtSprint(stringField(row, "KCM", "KCMC"))
		code := fmtSprint(stringField(row, "KCH", "KCDM"))
		number := stringField(row, "KXH")
		key := name + "|" + code + "|" + fmtSprint(number)
		if _, ok := index[key]; !ok {
			index[key] = len(classDetail)
			classDetail = append(classDetail, map[string]any{"name": name, "code": nullableString(code), "number": number})
		}
		weekValue := stringField(row, "SKZC", "ZCBH")
		weeks := buildWeekList(weekValue)
		if len(weeks) > semesterLength {
			semesterLength = len(weeks)
		}
		startKey, stopKey, dayKey, teacherKey := "KSJC", "JSJC", "SKXQ", "SKJS"
		if postgraduate {
			startKey, stopKey, dayKey, teacherKey = "KSJCDM", "JSJCDM", "XQ", "JSXM"
		}
		timeArrangement = append(timeArrangement, map[string]any{
			"source":    "school",
			"index":     index[key],
			"start":     intFromAny(row[startKey], 0),
			"stop":      intFromAny(row[stopKey], 0),
			"day":       intFromAny(row[dayKey], 0),
			"week_list": weeks,
			"teacher":   row[teacherKey],
			"classroom": row["JASMC"],
		})
	}
	return map[string]any{
		"semester_code":    semesterCode,
		"term_start_day":   termStartDay,
		"semester_length":  semesterLength,
		"class_detail":     classDetail,
		"not_arranged":     []map[string]any{},
		"time_arrangement": timeArrangement,
		"class_changes":    []map[string]any{},
	}
}

func buildNotArranged(rows []any, postgraduate bool) []map[string]any {
	result := make([]map[string]any, 0, len(rows))
	for _, raw := range rows {
		row := rowMap(raw)
		if postgraduate {
			result = append(result, map[string]any{"name": row["KCMC"], "code": row["KCDM"], "number": nil, "teacher": row["SKJS"]})
		} else {
			result = append(result, map[string]any{"name": row["KCM"], "code": row["KCH"], "number": row["KXH"], "teacher": row["SKJS"]})
		}
	}
	return result
}

func emptyClasstable(semesterCode string, termStartDay string) map[string]any {
	return map[string]any{
		"semester_code":    semesterCode,
		"term_start_day":   termStartDay,
		"semester_length":  1,
		"class_detail":     []map[string]any{},
		"not_arranged":     []map[string]any{},
		"time_arrangement": []map[string]any{},
		"class_changes":    []map[string]any{},
	}
}

var fmtPattern = regexp.MustCompile(`\s+`)

func fmtSprint(value any) string {
	if value == nil {
		return ""
	}
	return fmtPattern.ReplaceAllString(strings.TrimSpace(fmt.Sprint(value)), " ")
}

func nullableString(value string) any {
	if value == "" {
		return nil
	}
	return value
}

func stringFieldString(row map[string]any, key string) string {
	if row == nil {
		return ""
	}
	if value, ok := row[key]; ok {
		return fmtSprint(value)
	}
	return ""
}
