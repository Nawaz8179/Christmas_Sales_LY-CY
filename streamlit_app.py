import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(
    page_title="Christmas Sales LY-CY",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("Christmas Sales LY-CY (2024 vs 2025)")
st.caption("20–25 Dec | Christmas Performance Review")

# =====================================================
# LOAD ALL SHEETS
# =====================================================
@st.cache_data
def load_all_sheets(path):
    return pd.read_excel(path, sheet_name=None)

FILE_PATH = "YOY COMPARISION OF STORES & HO.xlsx"
sheets = load_all_sheets(FILE_PATH)

# =====================================================
# SIDEBAR – CONTEXT SWITCH (NOT A FILTER)
# =====================================================
st.sidebar.title("View Mode")

view_mode = st.sidebar.radio(
    "Select Analysis",
    [
        "YOY – Like-to-Like Stores (LFL)",
        "YOY of HO",
        "Closed Stores",
        "New Stores"
    ]
)

# =====================================================
# 1️⃣ LFL – CEO EXECUTION DASHBOARD (UNCHANGED CORE LOGIC)
# =====================================================
if view_mode == "YOY – Like-to-Like Stores (LFL)":

    df_raw = sheets["YOY – Like-to-Like Stores (LFL)"]

    # Detect Qty columns dynamically
    qty_2024_col = next((c for c in df_raw.columns if "qty" in c.lower() and "2024" in c), None)
    qty_2025_col = next((c for c in df_raw.columns if "qty" in c.lower() and "2025" in c), None)

    df = df_raw.rename(columns={
        "Site": "Store",
        "Net Sale Amount - 2024": "Sales_LY",
        "Net Sale Amount - 2025": "Sales_CY",
        qty_2024_col: "Qty_LY",
        qty_2025_col: "Qty_CY"
    })

    df["Date"] = pd.to_datetime(df["Date"])
    df["Daily_YOY"] = df["Sales_CY"] - df["Sales_LY"]

    store_agg = df.groupby("Store").agg(
        Sales_LY=("Sales_LY", "sum"),
        Sales_CY=("Sales_CY", "sum"),
        Qty_LY=("Qty_LY", "sum"),
        Qty_CY=("Qty_CY", "sum"),
        Max_Daily_YOY=("Daily_YOY", "max"),
        Avg_Daily_YOY=("Daily_YOY", "mean")
    ).reset_index()

    store_agg["YOY_Δ"] = store_agg["Sales_CY"] - store_agg["Sales_LY"]
    store_agg["YOY_%"] = store_agg["YOY_Δ"] / store_agg["Sales_LY"]
    store_agg["Qty_YOY_%"] = (store_agg["Qty_CY"] - store_agg["Qty_LY"]) / store_agg["Qty_LY"]

    store_agg["Spike_Index"] = np.where(
        store_agg["Avg_Daily_YOY"] > 0,
        store_agg["Max_Daily_YOY"] / store_agg["Avg_Daily_YOY"],
        np.nan
    )

    def verdict(r):
        if r["YOY_%"] < 0:
            return "DECLINED"
        if r["Spike_Index"] > 1.8:
            return "IMPROVED – FORCED"
        if r["Qty_YOY_%"] >= 0:
            return "IMPROVED – CONTROLLED"
        return "PRICE-DRIVEN RISK"

    store_agg["Verdict"] = store_agg.apply(verdict, axis=1)

    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Sales 2024", f"₹{store_agg['Sales_LY'].sum():,.0f}")
    c2.metric("Sales 2025", f"₹{store_agg['Sales_CY'].sum():,.0f}")
    c3.metric("Net YOY Change", f"₹{store_agg['YOY_Δ'].sum():,.0f}")
    c4.metric("% Stores Improved", f"{(store_agg['YOY_%'] > 0).mean()*100:.1f}%")

    fig = px.bar(
        store_agg.sort_values("YOY_Δ"),
        x="YOY_Δ",
        y="Store",
        orientation="h",
        title="Store-wise YOY Impact",
        color=store_agg["YOY_Δ"] > 0,
        color_discrete_map={True: "green", False: "red"}
    )
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(store_agg[[
        "Store", "Sales_LY", "Sales_CY", "YOY_Δ", "YOY_%", "Spike_Index", "Verdict"
    ]], use_container_width=True)

# =====================================================
# 2️⃣ YOY OF HO
# =====================================================
elif view_mode == "YOY of HO":

    df = sheets["YOY OF HO"]
    df["Date"] = pd.to_datetime(df["Date"])
    df["YOY_Δ"] = df["Net Sale Amount - 2025"] - df["Net Sale Amount - 2024"]

    st.metric("Net HO YOY Change", f"₹{df['YOY_Δ'].sum():,.0f}")

    fig = px.line(
        df,
        x="Date",
        y=["Net Sale Amount - 2024", "Net Sale Amount - 2025"],
        title="HO – LY vs CY Daily Sales"
    )
    st.plotly_chart(fig, use_container_width=True)

# =====================================================
# 3️⃣ CLOSED STORES – LOSS ANALYSIS
# =====================================================
elif view_mode == "Closed Stores":

    df = sheets["Closed Stores"]

    lost_sales = df["Net Sale Amount - 2024"].sum()
    st.metric("Revenue Lost Due to Closures", f"₹{lost_sales:,.0f}")

    fig = px.bar(
        df.groupby("Site")["Net Sale Amount - 2024"].sum().reset_index(),
        x="Net Sale Amount - 2024",
        y="Site",
        orientation="h",
        title="Sales Lost by Closed Store"
    )
    st.plotly_chart(fig, use_container_width=True)

# =====================================================
# 4️⃣ NEW STORES – CONTRIBUTION VIEW
# =====================================================
elif view_mode == "New Stores":

    df = sheets["New Stores"]
    df["Date"] = pd.to_datetime(df["Date"])

    total_sales = df["Net Sale Amount - 2025"].sum()
    avg_sales = df.groupby("Site")["Net Sale Amount - 2025"].sum().mean()

    c1, c2 = st.columns(2)
    c1.metric("Total New Store Sales", f"₹{total_sales:,.0f}")
    c2.metric("Avg Sales per New Store", f"₹{avg_sales:,.0f}")

    fig = px.bar(
        df.groupby("Site")["Net Sale Amount - 2025"].sum().reset_index(),
        x="Net Sale Amount - 2025",
        y="Site",
        orientation="h",
        title="New Store Contribution (2025)"
    )
    st.plotly_chart(fig, use_container_width=True)
