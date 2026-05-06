package xidian

import (
	"context"
	"net/url"

	xidianapp "mathstudy/backend-go/internal/application/xidian"
)

func (c *Client) fetchScoresEhall(ctx context.Context, session *session, username string) (map[string]any, error) {
	if err := c.ensureEhallLogin(ctx, session); err != nil {
		return nil, err
	}
	location, err := c.useEhallApp(ctx, session, ehallAppIDScore)
	if err != nil {
		return nil, err
	}
	_, _, _, _ = session.getJSON(ctx, location, nil, ehallHeaders())
	querySetting := map[string]any{"name": "SFYX", "value": "1", "linkOpt": "and", "builder": "m_value_equal"}
	payload, status, headers, err := session.getJSON(ctx, c.config.EhallBase+"/jwapp/sys/cjcx/modules/cjcx/xscjcx.do", url.Values{
		"*json":        {"1"},
		"querySetting": {jsonString(querySetting)},
		"*order":       {"+XNXQDM,KCH,KXH"},
		"pageSize":     {"1000"},
		"pageNumber":   {"1"},
	}, ehallHeaders())
	if err != nil {
		return nil, err
	}
	if err := ensureNotRedirected(status, headers); err != nil {
		return nil, err
	}
	return buildScores(rowsFrom(payload, "datas", "xscjcx"), false), nil
}

func (c *Client) fetchScoresYjspt(ctx context.Context, session *session, username string) (map[string]any, error) {
	payload, status, headers, err := session.getJSON(ctx, c.config.YjsptBase+"/gsapp/sys/wdcjapp/modules/wdcj/xscjcx.do", url.Values{
		"querySetting": {"[]"},
		"pageSize":     {"1000"},
		"pageNumber":   {"1"},
	}, nil)
	if err != nil {
		return nil, err
	}
	if err := ensureNotRedirected(status, headers); err != nil {
		return nil, err
	}
	ext := mapValue(payload, "datas", "xscjcx", "extParams")
	if intFromAny(ext["code"], 0) != 1 {
		message := fmtSprint(ext["msg"])
		if message == "" {
			message = "成绩查询失败"
		}
		return nil, xidianapp.ServiceError{Code: "DATA_FETCH_FAILED", Message: message, Status: 400}
	}
	return buildScores(rowsFrom(payload, "datas", "xscjcx"), true), nil
}

func buildScores(rows []any, postgraduate bool) map[string]any {
	scores := make([]map[string]any, 0, len(rows))
	semesterCode := any(nil)
	for index, raw := range rows {
		row := rowMap(raw)
		if index == 0 {
			if postgraduate {
				semesterCode = row["XNXQDM_DISPLAY"]
			} else {
				semesterCode = row["XNXQDM"]
			}
		}
		if postgraduate {
			scores = append(scores, map[string]any{
				"name":            row["KCMC"],
				"score":           row["DYBFZCJ"],
				"semester_code":   row["XNXQDM_DISPLAY"],
				"credit":          row["XF"],
				"class_status":    row["KCLBMC"],
				"class_type":      row["KCLBMC"],
				"score_status":    row["KSXZDM_DISPLAY"],
				"score_type_code": intFromAny(row["CJFZDM"], 0),
				"level":           row["CJXSZ"],
				"is_passed":       row["SFJG"],
				"class_id":        row["KCDM"],
			})
			continue
		}
		status := row["XGXKLBDM_DISPLAY"]
		if status == nil || fmtSprint(status) == "" {
			status = row["KCXZDM_DISPLAY"]
		}
		scores = append(scores, map[string]any{
			"name":            row["XSKCM"],
			"score":           row["ZCJ"],
			"semester_code":   row["XNXQDM"],
			"credit":          row["XF"],
			"class_status":    status,
			"class_type":      row["KCLBDM_DISPLAY"],
			"score_status":    row["CXCKDM_DISPLAY"],
			"score_type_code": intFromAny(row["DJCJLXDM"], 0),
			"level":           row["DJCJMC"],
			"is_passed":       row["SFJG"],
			"class_id":        row["JXBID"],
		})
	}
	return map[string]any{"semester_code": semesterCode, "scores": scores}
}

func (c *Client) fetchExamsEhall(ctx context.Context, session *session, username string) (map[string]any, error) {
	if err := c.ensureEhallLogin(ctx, session); err != nil {
		return nil, err
	}
	location, err := c.useEhallApp(ctx, session, ehallAppIDExam)
	if err != nil {
		return nil, err
	}
	_, _, _, _ = session.getJSON(ctx, location, nil, ehallHeaders())
	semesterCode, err := c.currentSemesterEhall(ctx, session)
	if err != nil {
		return nil, err
	}
	arrangedPayload, status, headers, err := session.getJSON(ctx, c.config.EhallBase+"/jwapp/sys/studentWdksapApp/modules/wdksap/wdksap.do?XNXQDM="+url.QueryEscape(semesterCode)+"&*order=-KSRQ,-KSSJMS", url.Values{}, ehallHeaders())
	if err != nil {
		return nil, err
	}
	if err := ensureNotRedirected(status, headers); err != nil {
		return nil, err
	}
	if code, _ := arrangedPayload["code"].(string); code != "" && code != "0" {
		return nil, xidianapp.ServiceError{Code: "DATA_FETCH_FAILED", Message: "考试信息获取失败", Status: 400}
	}
	toBePayload, status, headers, err := session.getJSON(ctx, c.config.EhallBase+"/jwapp/sys/studentWdksapApp/modules/wdksap/cxyxkwapkwdkc.do?XNXQDM="+url.QueryEscape(semesterCode), url.Values{}, ehallHeaders())
	if err != nil {
		return nil, err
	}
	if err := ensureNotRedirected(status, headers); err != nil {
		return nil, err
	}
	return map[string]any{
		"semester_code":  semesterCode,
		"arranged":       buildArrangedExams(rowsFrom(arrangedPayload, "datas", "wdksap"), false),
		"to_be_arranged": buildToBeArranged(rowsFrom(toBePayload, "datas", "cxyxkwapkwdkc")),
	}, nil
}

func (c *Client) fetchExamsYjspt(ctx context.Context, session *session, username string) (map[string]any, error) {
	semesterCode, err := c.currentSemesterYjspt(ctx, session)
	if err != nil {
		return nil, err
	}
	querySetting := []map[string]any{
		{"name": "XNXQDM", "caption": "学年学期代码", "builder": "equal", "linkOpt": "AND", "value": semesterCode},
		{"name": "SFFBKSAP", "caption": "是否发布考试安排", "builder": "equal", "linkOpt": "AND", "value": "1"},
		{"name": "XH", "caption": "学号", "builder": "equal", "linkOpt": "AND", "value": username},
		{"name": "KSAPWID", "caption": "考试安排WID", "builder": "notEqual", "linkOpt": "AND", "value": nil},
	}
	payload, status, headers, err := session.getJSON(ctx, c.config.YjsptBase+"/gsapp/sys/wdksapp/modules/ksxxck/wdksxxcx.do?querySetting="+url.QueryEscape(jsonString(querySetting))+"&pageSize=1000&pageNumber=1", url.Values{}, nil)
	if err != nil {
		return nil, err
	}
	if err := ensureNotRedirected(status, headers); err != nil {
		return nil, err
	}
	return map[string]any{
		"semester_code":  semesterCode,
		"arranged":       buildArrangedExams(rowsFrom(payload, "datas", "wdksxxcx"), true),
		"to_be_arranged": []map[string]any{},
	}, nil
}

func (c *Client) currentSemesterYjspt(ctx context.Context, session *session) (string, error) {
	payload, status, headers, err := session.getJSON(ctx, c.config.YjsptBase+"/gsapp/sys/yjsemaphome/modules/pubWork/getUserInfo.do", url.Values{}, nil)
	if err != nil {
		return "", err
	}
	if err := ensureNotRedirected(status, headers); err != nil {
		return "", err
	}
	if code, _ := payload["code"].(string); code != "" && code != "0" {
		message := fmtSprint(payload["msg"])
		if message == "" {
			message = "获取学期失败"
		}
		return "", xidianapp.ServiceError{Code: "DATA_FETCH_FAILED", Message: message, Status: 400}
	}
	return fmtSprint(mapValue(payload, "data")["xnxqdm"]), nil
}

func buildArrangedExams(rows []any, postgraduate bool) []map[string]any {
	result := make([]map[string]any, 0, len(rows))
	for _, raw := range rows {
		row := rowMap(raw)
		if postgraduate {
			result = append(result, map[string]any{"subject": row["KCMC"], "type": row["KSLXDM_DISPLAY"], "time": row["KSSJMS"], "place": row["JASMC"], "seat": nil})
		} else {
			result = append(result, map[string]any{"subject": row["KCM"], "type": row["KSMC"], "time": row["KSSJMS"], "place": row["JASMC"], "seat": row["ZWH"]})
		}
	}
	return result
}

func buildToBeArranged(rows []any) []map[string]any {
	result := make([]map[string]any, 0, len(rows))
	for _, raw := range rows {
		row := rowMap(raw)
		result = append(result, map[string]any{"subject": row["KCM"], "id": row["KCH"]})
	}
	return result
}
