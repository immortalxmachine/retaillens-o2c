-- dim_date  (ZI_CalendarDate, the calendar table ref_calendar is generated in Python,
-- like the SAP standard view I_CalendarDate is built on a generated calendar table)
CREATE VIEW ZI_CalendarDate AS
SELECT
    date_key,                  -- 'YYYY-MM-DD' text, joins to DATE_KEY(timestamp) in facts
    calendar_date,
    year_num,
    quarter_num,
    month_num,
    month_key,                 -- 'YYYY-MM', used for monthly trends
    weekday_num,               -- 0 = Monday
    is_weekend,
    is_festive,                -- 1 from 10 Nov to 31 Dec (Black Friday / Christmas)
    in_analysis_window         -- 1 for complete months used by the KPIs
FROM ref_calendar;
