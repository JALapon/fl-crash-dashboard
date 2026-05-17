-- crashes_yearly_trend.sql
--
-- Year-over-year trend across 2011-2018 (the 8 full years; 2019 was
-- dropped in clean.py for being a partial year). Powers the
-- dashboard's time-series line chart.
--
-- Expected row count: 8.

SELECT
    year,
    COUNT(*)                                         AS total,
    COUNT(*) FILTER (WHERE severity = 'Fatal')       AS fatal,
    COUNT(*) FILTER (WHERE severity = 'Serious injury') AS serious_injury
FROM crashes
GROUP BY year
ORDER BY year;
