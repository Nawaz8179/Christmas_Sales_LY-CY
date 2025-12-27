import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# -----------------------------
# CONFIG
# -----------------------------
st.set_page_config(
    page_title="Christmas Sales LY-CY",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.title("Christmas Sales LY-CY (2024 vs 2025)")
st.caption("20–25 Dec | Like-to-Like Stores")

# -----------------------------
# LOAD DATA
# -----------------------------
@st.cache_data
def load_data(path):
    df = pd.read_excel(path)
    return df

FILE_PATH = "YOY COMPARISION OF STORES & HO.xlsx"
df_raw = load_data(FILE_PATH)

# -----------------------------
# SANITY CHECKS (FAIL FAST)
# -----------------------------
required_cols = [
    "Site", "Date",
    "Net Sale Qty - 2024", "Net Sale Amount - 2024",
    "Net Sale Qty - 2025", "Net Sale Amount - 2025"
]

missing = [c for c in required_cols if c not in df_raw.columns]
if missing:
    st.error(f"Missing required columns: {missing}")
    st.stop()

# -----------------------------
# NORMALIZE DATA
# -----------------------------
df = df_raw.rename(columns={
    "Site": "Store",
    "Net Sale Qty - 2024": "Qty_LY",
    "Net Sale Amount - 2024": "Sales_LY",
    "Net Sale Qty - 2025": "Qty_CY",
    "Net Sale Amount - 2025": "Sales_CY"
})

df["Date"] = pd.to_datetime(df["Date"])

df["Daily_YOY"] = df["Sales_CY"] - df["Sales_LY"]
df["Qty_YOY"] = df["Qty_CY"] - df["Qty_LY"]

# -----------------------------
# AGGREGATIONS
# -----------------------------
store_agg = df.groupby("Store").agg(
    Sales_LY_Total=("Sales_LY", "sum"),
    Sales_CY_Total=("Sales_CY", "sum"),
    Qty_LY_Total=("Qty_LY", "sum"),
    Qty_CY_Total=("Qty_CY", "sum"),
    Max_Daily_YOY=("Daily_YOY", "max"),
    Min_Daily_YOY=("Daily_YOY", "min"),
    Avg_Daily_YOY=("Daily_YOY", "mean"),
    Std_Daily_YOY=("Daily_YOY", "std")
).reset_index()

store_agg["YOY_Delta"] = store_agg["Sales_CY_Total"] - store_agg["Sales_LY_Total"]
store_agg["YOY_Pct"] = np.where(
    store_agg["Sales_LY_Total"] != 0,
    store_agg["YOY_Delta"] / store_agg["Sales_LY_Total"],
    0
)

store_agg["Qty_YOY_Pct"] = np.where(
    store_agg["Qty_LY_Total"] != 0,
    (store_agg["Qty_CY_Total"] - store_agg["Qty_LY_Total"]) / store_agg["Qty_LY_Total"],
    0
)

store_agg["YOY_Spike_Index"] = np.where(
    store_agg["Avg_Daily_YOY"] > 0,
    store_agg["Max_Daily_YOY"] / store_agg["Avg_Daily_YOY"],
    np.nan
)

store_agg["YOY_Volatility"] = np.where(
    store_agg["Avg_Daily_YOY"] != 0,
    store_agg["Std_Daily_YOY"] / abs(store_agg["Avg_Daily_YOY"]),
    np.nan
)

# -----------------------------
# EXECUTION VERDICT (AUTO)
# -----------------------------
def verdict(row):
    if row["YOY_Pct"] < 0:
        return "DECLINED"
    if row["YOY_Spike_Index"] > 1.8:
        return "IMPROVED – FORCED"
    if row["YOY_Pct"] > 0 and row["Qty_YOY_Pct"] >= 0:
        return "IMPROVED – CONTROLLED"
    if row["YOY_Pct"] > 0 and row["Qty_YOY_Pct"] < 0:
        return "PRICE-DRIVEN RISK"
    return "UNCLASSIFIED"

store_agg["Execution_Verdict"] = store_agg.apply(verdict, axis=1)

# -----------------------------
# KPI METRICS
# -----------------------------
total_ly = store_agg["Sales_LY_Total"].sum()
total_cy = store_agg["Sales_CY_Total"].sum()
net_yoy = total_cy - total_ly
pct_improved = (store_agg["YOY_Pct"] > 0).mean() * 100

# -----------------------------
# TABS
# -----------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "CEO Verdict",
    "Daily YOY Consistency",
    "LY vs CY Shape",
    "Value vs Volume",
    "Action Table"
])

# -----------------------------
# TAB 1 — CEO VERDICT
# -----------------------------
with tab1:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Sales 2024", f"₹{total_ly:,.0f}")
    c2.metric("Sales 2025", f"₹{total_cy:,.0f}")
    c3.metric("Net YOY Change", f"₹{net_yoy:,.0f}")
    c4.metric("% Stores Improved", f"{pct_improved:.1f}%")

    fig = px.bar(
        store_agg.sort_values("YOY_Delta"),
        x="YOY_Delta",
        y="Store",
        orientation="h",
        color=store_agg["YOY_Delta"] > 0,
        color_discrete_map={True: "green", False: "red"},
        title="Store-wise YOY Impact"
    )

    spike_stores = store_agg[store_agg["YOY_Spike_Index"] > 1.8]
    fig.add_scatter(
        x=spike_stores["YOY_Delta"],
        y=spike_stores["Store"],
        mode="markers",
        marker=dict(color="black", size=10),
        name="Spike-Driven"
    )

    st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# TAB 2 — DAILY YOY CONSISTENCY
# -----------------------------
with tab2:
    heat = df.pivot_table(
        index="Store",
        columns=df["Date"].dt.strftime("%d-%b"),
        values="Daily_YOY",
        aggfunc="sum"
    )

    fig = px.imshow(
        heat,
        color_continuous_scale="RdYlGn",
        title="Daily YOY Difference (CY − LY)"
    )
    st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# TAB 3 — LY vs CY SHAPE
# -----------------------------
with tab3:
    store_sel = st.selectbox("Select Store", df["Store"].unique())

    d = df[df["Store"] == store_sel].sort_values("Date")

    fig = px.line(
        d,
        x="Date",
        y=["Sales_LY", "Sales_CY"],
        labels={"value": "Sales", "variable": "Year"},
        title=f"LY vs CY Daily Shape — {store_sel}"
    )
    fig.update_traces(line=dict(width=3))
    st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# TAB 4 — VALUE vs VOLUME
# -----------------------------
with tab4:
    fig = px.scatter(
        store_agg,
        x="Qty_YOY_Pct",
        y="YOY_Pct",
        text="Store",
        title="Value vs Volume Truth Map"
    )
    fig.add_hline(y=0)
    fig.add_vline(x=0)
    st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# TAB 5 — ACTION TABLE
# -----------------------------
with tab5:
    final_table = store_agg[[
        "Store",
        "Sales_LY_Total",
        "Sales_CY_Total",
        "YOY_Delta",
        "YOY_Pct",
        "YOY_Spike_Index",
        "Qty_YOY_Pct",
        "Execution_Verdict"
    ]]

    final_table = final_table.rename(columns={
        "Sales_LY_Total": "Sales LY",
        "Sales_CY_Total": "Sales CY",
        "YOY_Delta": "YOY Δ",
        "YOY_Pct": "YOY %",
        "YOY_Spike_Index": "YOY Spike Index",
        "Qty_YOY_Pct": "Qty YOY %",
        "Execution_Verdict": "Execution Verdict"
    })

    st.dataframe(final_table, use_container_width=True)
