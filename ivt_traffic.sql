#data cleaning and preparation 
-- Remove incomplete rows or impossible values
DELETE FROM ad_traffic_data
WHERE unique_idfas = 0 OR total_requests = 0;

-- Optional: Replace NULL values with 0 for numeric columns
UPDATE ad_traffic_data
SET 
  impressions = COALESCE(impressions, 0),
  impressions_per_idfa = COALESCE(impressions_per_idfa, 0),
  idfa_ip_ratio = COALESCE(idfa_ip_ratio, 0),
  idfa_ua_ratio = COALESCE(idfa_ua_ratio, 0);

#average and variation by app 
SELECT
    app_name,
    AVG(requests_per_idfa) AS avg_requests_per_idfa,
    STDDEV(requests_per_idfa) AS std_requests_per_idfa,
    AVG(impressions_per_idfa) AS avg_impressions_per_idfa,
    AVG(idfa_ip_ratio) AS avg_idfa_ip_ratio,
    AVG(idfa_ua_ratio) AS avg_idfa_ua_ratio,
    SUM(CASE WHEN ivt > 0 THEN 1 ELSE 0 END) AS ivt_flag_count,
    COUNT(*) AS total_records
FROM ad_traffic_data
GROUP BY app_name
ORDER BY avg_idfa_ua_ratio DESC;

SELECT
    app_name,
    date_or_hour,
    requests_per_idfa,
    impressions_per_idfa,
    idfa_ip_ratio,
    idfa_ua_ratio,
    ivt,
    CASE 
      WHEN idfa_ua_ratio > 10 THEN 'HIGH_UA_RATIO'
      WHEN requests_per_idfa > 5 THEN 'EXCESS_REQUESTS'
      WHEN impressions_per_idfa < 0.1 THEN 'LOW_IMPRESSIONS'
      ELSE 'NORMAL'
    END AS anomaly_type
FROM ad_traffic_data
WHERE idfa_ua_ratio > 10 
   OR requests_per_idfa > 5
   OR impressions_per_idfa < 0.1;

#time series analysis 
SELECT
    app_name,
    DATE(date_or_hour) AS report_date,
    SUM(ivt) AS total_ivt_events,
    COUNT(*) AS records,
    ROUND(SUM(ivt) / COUNT(*), 4) AS ivt_rate
FROM ad_traffic_data
GROUP BY app_name, DATE(date_or_hour)
ORDER BY report_date;

SELECT
    a.app_name,
    a.date_or_hour,
    a.requests_per_idfa,
    a.impressions_per_idfa,
    a.idfa_ua_ratio,
    a.idfa_ip_ratio
FROM ad_traffic_data a
JOIN (
    SELECT app_name, MIN(date_or_hour) AS first_ivt_time
    FROM ad_traffic_data
    WHERE ivt > 0
    GROUP BY app_name
) ivt_start
  ON a.app_name = ivt_start.app_name
WHERE a.date_or_hour BETWEEN (ivt_start.first_ivt_time - INTERVAL 1 DAY)
                          AND ivt_start.first_ivt_time
ORDER BY a.app_name, a.date_or_hour;

#correlation and relationship checks 
-- Approximate relationship between IVT and other ratios
SELECT
    app_name,
    ROUND(COVAR_POP(ivt, idfa_ua_ratio) / (STDDEV_POP(ivt) * STDDEV_POP(idfa_ua_ratio)), 4) AS corr_ivt_ua,
    ROUND(COVAR_POP(ivt, requests_per_idfa) / (STDDEV_POP(ivt) * STDDEV_POP(requests_per_idfa)), 4) AS corr_ivt_req,
    ROUND(COVAR_POP(ivt, idfa_ip_ratio) / (STDDEV_POP(ivt) * STDDEV_POP(idfa_ip_ratio)), 4) AS corr_ivt_ip
FROM ad_traffic_data
GROUP BY app_name;

#classification by ivt behaviour 
SELECT
    app_name,
    CASE
        WHEN SUM(ivt) = 0 THEN 'Non-IVT App'
        WHEN MIN(date_or_hour) = (SELECT MIN(date_or_hour) FROM ad_traffic_data WHERE ivt > 0) THEN 'Early IVT'
        ELSE 'Late IVT'
    END AS ivt_category,
    COUNT(*) AS total_records
FROM ad_traffic_data
GROUP BY app_name;

#top 10 suspicious windows overall 
SELECT
    app_name,
    date_or_hour,
    requests_per_idfa,
    impressions_per_idfa,
    idfa_ua_ratio,
    idfa_ip_ratio,
    ivt
FROM ad_traffic_data
WHERE idfa_ua_ratio > 10
   OR requests_per_idfa > 5
   OR impressions_per_idfa < 0.1
ORDER BY idfa_ua_ratio DESC, requests_per_idfa DESC
LIMIT 10;

#summary kpi table 
SELECT
    app_name,
    ROUND(AVG(requests_per_idfa),2) AS avg_req_per_idfa,
    ROUND(AVG(impressions_per_idfa),2) AS avg_impr_per_idfa,
    ROUND(AVG(idfa_ip_ratio),2) AS avg_idfa_ip,
    ROUND(AVG(idfa_ua_ratio),2) AS avg_idfa_ua,
    ROUND(SUM(ivt)/COUNT(*),4) AS ivt_rate
FROM ad_traffic_data
GROUP BY app_name
ORDER BY ivt_rate DESC;

#derived metrics 
CREATE VIEW ivt_metrics_summary AS
SELECT
    app_name,
    DATE(date_or_hour) AS report_date,
    AVG(requests_per_idfa) AS avg_req_idfa,
    AVG(impressions_per_idfa) AS avg_impr_idfa,
    AVG(idfa_ip_ratio) AS avg_ip_ratio,
    AVG(idfa_ua_ratio) AS avg_ua_ratio,
    SUM(ivt) AS total_ivt
FROM ad_traffic_data
GROUP BY app_name, DATE(date_or_hour);

#use in python dashboard 
from sqlalchemy import create_engine
import pandas as pd
engine = create_engine("mysql+pymysql://user:pass@localhost/dbname")
query = "SELECT * FROM ivt_metrics_summary;"
df = pd.read_sql(query, engine)
