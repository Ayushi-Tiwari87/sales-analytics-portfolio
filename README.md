# FUTURE_DS_01

## Overview

Data analytics workspace for sales performance: notebooks, processed datasets, reports, and an interactive dashboard.

## Project Structure

- data/: Raw and processed datasets
- notebooks/: Exploratory and analytics notebooks
- reports/: Generated KPIs, insights, anomalies, and figures
- dashboard/: App code for interactive visualization

## Dashboard

An interactive Streamlit app is available in dashboard/app.py to explore sales KPIs, trends, and latest reports (insights, anomalies).

### Quick Start (Windows PowerShell)

1. Create a virtual environment (recommended):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install -r dashboard/requirements.txt
```

3. Run the app:

```powershell
streamlit run dashboard/app.py
```

The app will open at http://localhost:8501. It automatically detects the latest files in data/ and reports/.
