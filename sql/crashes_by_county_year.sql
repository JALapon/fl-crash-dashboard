-- crashes_by_county_year.sql
--
-- Powers the dashboard's choropleth map + year filter.
-- One row per (county, year) with totals split by severity.
--
-- Expected row count: up to 67 FL counties x 8 years = ~530 rows
-- (in practice less, since not every county has fatal/serious
-- crashes every year).

SELECT
    county,
    year,
    COUNT(*)                                         AS total,
    COUNT(*) FILTER (WHERE severity = 'Fatal')       AS fatal,
    COUNT(*) FILTER (WHERE severity = 'Serious injury') AS serious_injury
FROM crashes
GROUP BY county, year
ORDER BY year, total DESC;
