# IVT-traffic-analysis-
Comprehensive IVT Traffic Analysis Project using Python, SQL, and Excel Dashboard to detect patterns and anomalies in ad traffic data.

Overview

This project analyzes advertising traffic data to detect and explain patterns of Invalid Traffic (IVT) across multiple mobile applications.
Using Python, SQL, and Excel Dashboards, the analysis explores metrics like requests per device, impressions ratios, and user-agent diversity to understand why certain apps were flagged as IVT earlier, later, or not at all.

#🎯Objectives
Identify traffic behavior differences between IVT and Non-IVT apps.
Detect anomalies in ratios such as:
1. requests_per_idfa
2. impressions_per_idfa
3. idfa_ip_ratio
4. idfa_ua_ratio
Highlight patterns leading to suspicious (non-human) traffic.
Provide actionable insights for ad fraud detection and prevention.

#📂Project Structure
IVT_Traffic_Analysis/
│
├── data/
│   ├── ivt_traffic_data.csv        # Cleaned dataset (exported from Google Sheets)
│
├── analysis/
│   ├── ivt_analysis.ipynb          # Python notebook with full data analysis
│   ├── ivt_queries.sql             # SQL queries for data extraction & analytics
│
├── dashboard/
│   ├── IVT_Traffic_Dashboard.xlsx  # Excel dashboard with charts & KPIs
│
├── report/
│   ├── IVT_Traffic_Analysis_Report.pdf  # Formal report with findings and visuals
│
├── README.md
└── requirements.txt

#🧠Tools & Technologies
1. Python (Pandas, Matplotlib, Seaborn) → Data cleaning & visualization
2. SQL (MySQL / PostgreSQL) → Query-based exploration
3. Excel → Interactive dashboard creation
4. Jupyter Notebook → Exploratory data analysis
5. Git & GitHub → Version control and project documentation

#📈Key Insights
Apps flagged IVT early showed high idfa_ua_ratio spikes, indicating multiple fake devices using the same User-Agent.
Late IVT apps had gradual growth in requests_per_idfa, signaling delayed detection of automated traffic.
Non-IVT apps maintained stable ratios and balanced impressions per device — indicating organic traffic.

#📜Report Summary
The formal report (PDF) includes:
1. Data overview & methodology
2. Detailed trend analysis per app
3. Visualization of anomalies
4. IVT detection insights & recommendations

#✅Conclusion
The IVT Traffic Analysis Project effectively identifies traffic integrity issues through data-driven analytics.
By integrating Python, SQL, and Excel, it provides both quantitative insight and visual clarity into how traffic behaviors evolve before IVT flagging.
The findings show that abnormal device-to-agent ratios and unbalanced request volumes are strong precursors to invalid traffic detection.
This project demonstrates a scalable analytical framework for ad fraud monitoring, offering actionable intelligence to improve ad quality assurance and prevent non-human traffic.
