-- dim_date  (ZI_CalendarDate, the calendar table ref_calendar is generated in Python,
-- like the SAP standard view I_CalendarDate is built on table SCAL_TT_DATE)
CREATE VIEW ZI_CalendarDate AS
SELECT
    calendar_date,
    year_num,
    quarter_num,
    month_num,
    month_key,                 -- 'YYYY-MM', used for monthly trends
    weekday_num,               -- 0 = Monday
    is_weekend,
    season_half,               -- SS (Feb-Jul) or AW (Aug-Jan) selling season
    is_festive                 -- 1 between 10 Nov and 31 Dec (Black Friday / Christmas)
FROM ref_calendar;
