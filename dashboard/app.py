import os
import glob
from pathlib import Path
from datetime import datetime

import pandas as pd
import streamlit as st
import plotly.express as px

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"

st.set_page_config(page_title="Sales Performance Dashboard", layout="wide")

# ---------- Helpers ----------

def find_latest_file(directory: Path, pattern: str) -> Path | None:
    files = sorted(directory.glob(pattern))
    return files[-1] if files else None


def load_data() -> pd.DataFrame:
    # Prefer processed sales line if available, else fallback to sample
    processed_line = find_latest_file(DATA_DIR, "processed_sales_line_*.csv")
    sample_file = DATA_DIR / "sales_sample.csv"

    if processed_line and processed_line.exists():
        df = pd.read_csv(processed_line)
    elif sample_file.exists():
        df = pd.read_csv(sample_file)
    else:
        st.error("No data files found in data/ folder.")
        return pd.DataFrame()

    # Standardize column names
    df.columns = [c.strip().lower() for c in df.columns]

    # Ensure date column
    date_col = None
    for candidate in ["order_date", "date", "orderdate"]:
        if candidate in df.columns:
            date_col = candidate
            break
    if date_col:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    else:
        st.warning("No date column found; charts may be limited.")

    # Compute revenue & profit if possible
    if {"quantity", "unit_price", "discount_rate"}.issubset(df.columns):
        df["revenue"] = df["quantity"] * df["unit_price"] * (1 - df["discount_rate"].fillna(0))
    elif {"quantity", "unit_price"}.issubset(df.columns):
        df["revenue"] = df["quantity"] * df["unit_price"]

    if {"quantity", "unit_price", "unit_cost", "discount_rate"}.issubset(df.columns):
        df["profit"] = df["quantity"] * (df["unit_price"] - df["unit_cost"]) * (1 - df["discount_rate"].fillna(0))
    elif {"quantity", "unit_price", "unit_cost"}.issubset(df.columns):
        df["profit"] = df["quantity"] * (df["unit_price"] - df["unit_cost"])

    return df


def load_latest_anomalies() -> pd.DataFrame | None:
    anomalies_file = find_latest_file(REPORTS_DIR, "anomalies_*.csv")
    if anomalies_file and anomalies_file.exists():
        try:
            return pd.read_csv(anomalies_file)
        except Exception as e:
            st.warning(f"Failed to load anomalies: {e}")
    return None


def load_latest_kpis() -> dict | pd.DataFrame | None:
    kpis_json = find_latest_file(REPORTS_DIR, "kpis_*.json")
    if kpis_json and kpis_json.exists():
        try:
            import json
            with open(kpis_json, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data
        except Exception as e:
            st.warning(f"Failed to load KPIs JSON: {e}")
    kpis_csv = find_latest_file(REPORTS_DIR, "kpis_*.csv")
    if kpis_csv and kpis_csv.exists():
        try:
            return pd.read_csv(kpis_csv)
        except Exception as e:
            st.warning(f"Failed to load KPIs CSV: {e}")
    return None


def load_latest_insights() -> str | None:
    insights_md = find_latest_file(REPORTS_DIR, "insights_*.md")
    if insights_md and insights_md.exists():
        try:
            return insights_md.read_text(encoding="utf-8")
        except Exception as e:
            st.warning(f"Failed to load insights: {e}")
    return None


# ---------- Sidebar Filters ----------

df = load_data()

st.sidebar.header("Filters")

if not df.empty:
    # Date range filter
    date_col = next((c for c in ["order_date", "date", "orderdate"] if c in df.columns), None)
    if date_col:
        min_date = df[date_col].min()
        max_date = df[date_col].max()
        date_default = (
            min_date.date() if pd.notna(min_date) else datetime(2000, 1, 1),
            max_date.date() if pd.notna(max_date) else datetime.now().date(),
        )
        date_input = st.sidebar.date_input("Date range", value=date_default, key="date_range")
        if isinstance(date_input, tuple) and len(date_input) == 2:
            start, end = date_input
        else:
            start = end = date_input
        if start and end:
            df = df[(df[date_col] >= pd.to_datetime(start)) & (df[date_col] <= pd.to_datetime(end))]

    # Category filter
    if "category" in df.columns:
        categories = sorted(df["category"].dropna().unique().tolist())
        selected_categories = st.sidebar.multiselect("Category", categories, default=categories)
        if selected_categories:
            df = df[df["category"].isin(selected_categories)]

    # Region filter
    if "region" in df.columns:
        regions = sorted(df["region"].dropna().unique().tolist())
        selected_regions = st.sidebar.multiselect("Region", regions, default=regions)
        if selected_regions:
            df = df[df["region"].isin(selected_regions)]


# ---------- KPIs ----------

st.title("📊 Sales Performance Dashboard")

if df.empty:
    st.info("No data available to display. Please ensure files exist in data/ or reports/.")
else:
    total_orders = len(df)
    total_quantity = df["quantity"].sum() if "quantity" in df.columns else None
    total_revenue = df["revenue"].sum() if "revenue" in df.columns else None
    total_profit = df["profit"].sum() if "profit" in df.columns else None

    cols = st.columns(4)
    cols[0].metric("Total Orders", f"{total_orders:,.0f}")
    cols[1].metric("Total Quantity", f"{(total_quantity or 0):,.0f}")
    cols[2].metric("Total Revenue", f"₹{(total_revenue or 0):,.2f}")
    cols[3].metric("Total Profit", f"₹{(total_profit or 0):,.2f}")

    # ---------- Charts ----------
    st.subheader("Trends & Breakdown")
    with st.container():
        chart_cols = st.columns(2)
        date_col = next((c for c in ["order_date", "date", "orderdate"] if c in df.columns), None)
        value_col = "revenue" if "revenue" in df.columns else ("quantity" if "quantity" in df.columns else None)

        if date_col and value_col:
            by_date = df[[date_col, value_col]].dropna().copy()
            by_date["month"] = by_date[date_col].dt.to_period("M").astype(str)
            agg = by_date.groupby("month", as_index=False)[value_col].sum()
            fig_trend = px.line(agg, x="month", y=value_col, title=f"{value_col.capitalize()} by Month")
            chart_cols[0].plotly_chart(fig_trend, use_container_width=True)
        else:
            chart_cols[0].write("Date/value columns not found for trend chart.")

        if "category" in df.columns and value_col:
            agg_cat = df.groupby("category", as_index=False)[value_col].sum().sort_values(value_col, ascending=False)
            fig_cat = px.bar(agg_cat, x="category", y=value_col, title=f"{value_col.capitalize()} by Category")
            chart_cols[1].plotly_chart(fig_cat, use_container_width=True)
        else:
            chart_cols[1].write("Category/value columns not found for breakdown chart.")

    # Region/channel
    if "region" in df.columns and value_col:
        st.plotly_chart(px.bar(df.groupby("region", as_index=False)[value_col].sum(), x="region", y=value_col, title=f"{value_col.capitalize()} by Region"), use_container_width=True)
    if "channel" in df.columns and value_col:
        st.plotly_chart(px.pie(df, names="channel", values=value_col, title=f"{value_col.capitalize()} by Channel"), use_container_width=True)

    # Top products
    if "product_id" in df.columns and value_col:
        top_products = df.groupby("product_id", as_index=False)[value_col].sum().sort_values(value_col, ascending=False).head(10)
        st.plotly_chart(px.bar(top_products, x="product_id", y=value_col, title=f"Top 10 Products by {value_col.capitalize()}"), use_container_width=True)

    # Raw data preview
    with st.expander("Preview Data"):
        st.dataframe(df.head(200))

# ---------- Reports: KPIs, Insights, Anomalies ----------

st.header("Reports")

kpis = load_latest_kpis()
if kpis is not None:
    st.subheader("Latest KPIs")
    if isinstance(kpis, dict):
        cols = st.columns(min(4, len(kpis)))
        for i, (k, v) in enumerate(kpis.items()):
            cols[i % len(cols)].metric(k.replace("_", " ").title(), f"{v}")
    elif isinstance(kpis, pd.DataFrame):
        st.dataframe(kpis)

insights = load_latest_insights()
if insights:
    st.subheader("Insights")
    st.markdown(insights)

anomalies_df = load_latest_anomalies()
if anomalies_df is not None:
    st.subheader("Anomalies")
    st.dataframe(anomalies_df)

st.caption("Data sources: data/, reports/")
