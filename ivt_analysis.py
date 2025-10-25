"""
ivt_analysis.py
Run: python ivt_analysis.py --sheet_url "<google_sheet_url>" --output_dir ./output

Requirements:
pip install pandas numpy matplotlib openpyxl xlsxwriter jinja2
Optional (to produce PDF): pip install pdfkit  and install wkhtmltopdf, OR use headless chrome via playwright.

Notes:
- If your sheet is public, the script will read CSV export.
- If private, set up a service account and download JSON credentials, then use gspread/pandas with OAuth.
"""

import os
import sys
import argparse
from urllib.parse import urlparse, parse_qs
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
import io
from jinja2 import Template

# ---------- Helpers ----------
def sheet_csv_export_url(sheet_url, gid=None):
    """
    For a public sheet, return CSV export URL for the first sheet or a specified gid.
    """
    # Example: https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit#gid=0
    parsed = urlparse(sheet_url)
    parts = parsed.path.split('/')
    try:
        sheet_id = parts[3]
    except Exception:
        raise ValueError("Couldn't parse sheet id from URL.")
    gid_arg = gid if gid is not None else 0
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid_arg}"

def load_csv_url(url):
    # pandas can read remote URL if publicly accessible.
    return pd.read_csv(url)

# ---------- Analysis functions ----------
def preprocess(df):
    # lower-case column names and strip spaces
    df = df.rename(columns=lambda c: c.strip())
    # try parse date
    date_cols = [c for c in df.columns if 'date' in c.lower() or 'hour' in c.lower() or 'time' in c.lower()]
    if date_cols:
        df['Date'] = pd.to_datetime(df[date_cols[0]], errors='coerce')
    else:
        # try first column
        df['Date'] = pd.to_datetime(df.iloc[:,0], errors='coerce')
    # numeric conversion for common columns
    numcols = ['unique_idfas','unique_ips','unique_uas','total_requests',
               'requests_per_idfa','impressions','impressions_per_idfa',
               'idfa_ip_ratio','idfa_ua_ratio','IVT']
    for c in numcols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce')
    return df

def detect_spikes(series, window=24, z_thresh=3.0):
    rol_mean = series.rolling(window=window, min_periods=1).mean()
    rol_std = series.rolling(window=window, min_periods=1).std().replace(0,np.nan)
    z = (series - rol_mean) / rol_std
    return (z.abs() > z_thresh).fillna(False), z

def make_timeplot(df, xcol, ycol, outpath, title=None, highlight_idx=None):
    plt.figure(figsize=(10,3))
    plt.plot(df[xcol], df[ycol], marker='.', linewidth=0.8)
    if highlight_idx is not None and len(highlight_idx):
        plt.scatter(df.loc[highlight_idx, xcol], df.loc[highlight_idx, ycol], color='red', s=20)
    plt.title(title or ycol)
    plt.xlabel('Date')
    plt.tight_layout()
    plt.gca().xaxis.set_major_formatter(DateFormatter("%Y-%m-%d %H:%M"))
    plt.xticks(rotation=30)
    plt.savefig(outpath, dpi=150)
    plt.close()

# ---------- Main ----------
def run_analysis(df, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    charts_dir = os.path.join(output_dir, 'charts')
    os.makedirs(charts_dir, exist_ok=True)

    df = preprocess(df)
    # Basic summary
    summary = df.describe(include='all').transpose()

    # If the sheet contains an 'app' column, group by app. If not, treat entire dataset as single app.
    app_col = None
    for candidate in ['app','app_name','application','bundle_id']:
        if candidate in df.columns:
            app_col = candidate; break

    apps = df[app_col].unique() if app_col else ['__ALL__']
    # store per-app results
    report_entries = []

    for app in apps:
        df_app = df[df[app_col] == app].copy() if app_col else df.copy()
        df_app = df_app.sort_values('Date').reset_index(drop=True)

        # compute spikes for key metrics
        spikes = {}
        zscores = {}
        for metric in ['idfa_ua_ratio','requests_per_idfa','impressions_per_idfa','idfa_ip_ratio']:
            if metric in df_app.columns:
                flag, z = detect_spikes(df_app[metric].fillna(0))
                spikes[metric] = flag
                zscores[metric] = z

        # Define suspicious windows: where at least two metrics spike or where impressions_per_idfa is near zero with many requests
        combined_spike = np.zeros(len(df_app), dtype=bool)
        for metric, flag in spikes.items():
            combined_spike = combined_spike | flag.values
        # additional rule: many requests but zero impressions
        rule_zero_impr = (df_app.get('impressions',0).fillna(0) == 0) & (df_app.get('total_requests',0).fillna(0) > 1000)
        suspicious = pd.Series(combined_spike) | rule_zero_impr.fillna(False)

        # correlation of IVT vs metrics (if IVT exists)
        corr = {}
        if 'IVT' in df_app.columns:
            for metric in ['idfa_ua_ratio','requests_per_idfa','impressions_per_idfa','idfa_ip_ratio']:
                if metric in df_app.columns:
                    corr[metric] = df_app[metric].corr(df_app['IVT'])

        # Save charts
        for metric in ['idfa_ua_ratio','requests_per_idfa','impressions_per_idfa']:
            if metric in df_app.columns:
                out = os.path.join(charts_dir, f"{str(app)}_{metric}.png".replace('/','_'))
                hidx = df_app.index[suspicious.values]
                make_timeplot(df_app, 'Date', metric, out, title=f"{app} - {metric}", highlight_idx=hidx)

        # Summaries for Excel sheet
        entry = {
            'app': app,
            'n_rows': len(df_app),
            'suspicious_count': int(suspicious.sum()),
            'suspicious_ratio': float(suspicious.mean()),
            'corr': corr,
            'top_suspicious_windows': df_app.loc[suspicious].head(20).to_dict('records')
        }
        report_entries.append(entry)

    # Build Excel workbook
    writer = pd.ExcelWriter(os.path.join(output_dir, "analysis.xlsx"), engine='xlsxwriter')
    # summary tabs
    pd.DataFrame(report_entries).to_excel(writer, sheet_name='summary', index=False)
    # write raw data
    df.to_excel(writer, sheet_name='raw_data', index=False)
    # add charts as images into a dashboard sheet
    workbook  = writer.book
    dashboard = workbook.add_worksheet('dashboard')
    # insert chart images
    y = 1
    for fname in sorted(os.listdir(charts_dir)):
        path = os.path.join(charts_dir, fname)
        if y > 40:
            break
        dashboard.insert_image(y, 1, path, {'x_scale':0.8,'y_scale':0.8})
        y += 15
    writer.close()

    # produce a simple HTML report
    html_templ = Template("""
    <html><head><meta charset="utf-8"><title>IVT Analysis Report</title></head><body>
    <h1>IVT Analysis Report</h1>
    <p>Generated: {{when}}</p>
    <h2>Per-app summary</h2>
    {% for e in entries %}
      <h3>{{e.app}}</h3>
      <ul>
        <li>Rows: {{e.n_rows}}</li>
        <li>Suspicious windows: {{e.suspicious_count}} ({{"{:.1%}".format(e.suspicious_ratio)}})</li>
        <li>Correlations: {{e.corr}}</li>
      </ul>
    {% endfor %}
    </body></html>
    """)
    html = html_templ.render(when=pd.Timestamp.now(), entries=report_entries)
    with open(os.path.join(output_dir,'analysis_report.html'),'w', encoding='utf8') as f:
        f.write(html)

    print("Analysis finished. Outputs in:", output_dir)
    return

# ---------- CLI ----------
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--sheet_url', required=True, help='Google Sheet edit URL')
    parser.add_argument('--gid', required=False, help='gid of the sheet tab (0 default)', default=0)
    parser.add_argument('--output_dir', required=False, default='./output', help='Output directory')
    args = parser.parse_args()

    csv_url = sheet_csv_export_url(args.sheet_url, gid=args.gid)
    print("Attempting to load sheet as CSV from:", csv_url)
    try:
        df = load_csv_url(csv_url)
    except Exception as e:
        print("Failed to load public CSV. If your sheet is private, please follow instructions in the README.")
        raise

    run_analysis(df, args.output_dir)
