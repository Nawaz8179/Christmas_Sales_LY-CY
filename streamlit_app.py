import streamlit as st
import pandas as pd
import plotly.express as px

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(
    page_title="Sales Performance YOY",
    layout="wide"
)

st.title("Sales Performance Dashboard")
st.caption("Christmas | December Full Month | January MTD — YOY Review")

# =====================================================
# LOAD FILES
# =====================================================
@st.cache_data
def load_sheets(path):
    return pd.read_excel(path, sheet_name=None)

CHRISTMAS_FILE = "YOY COMPARISION OF STORES & HO.xlsx"
DEC_FILE = "DEC 2024-2025.xlsx"
JAN_FILE = "JAN 2025-2026 MTD.xlsx"

christmas_sheets = load_sheets(CHRISTMAS_FILE)
dec_sheets = load_sheets(DEC_FILE)
jan_sheets = load_sheets(JAN_FILE)

# =====================================================
# PERIOD TOGGLE (GLOBAL)
# =====================================================
period = st.radio(
    "Select Period",
    [
        "Christmas (20–25 Dec)",
        "December Full Month",
        "January MTD (1–27)"
    ],
    horizontal=True
)

if period == "Christmas (20–25 Dec)":
    data_source = christmas_sheets
elif period == "December Full Month":
    data_source = dec_sheets
else:
    data_source = jan_sheets

# =====================================================
# SIDEBAR – VIEW MODE
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
# HELPER: SAFE SALES COLUMN DETECTION
# =====================================================
def detect_sales_columns(df):
    sale_cols = [c for c in df.columns if "Net Sale Amount" in c]

    if not sale_cols:
        return None, None

    sale_cols_sorted = sorted(
        sale_cols,
        key=lambda x: int("".join(filter(str.isdigit, x)))
    )

    ly_col = sale_cols_sorted[0] if len(sale_cols_sorted) >= 1 else None
    cy_col = sale_cols_sorted[1] if len(sale_cols_sorted) >= 2 else None

    return ly_col, cy_col

# =====================================================
# 1️⃣ LFL – YOY
# =====================================================
if view_mode == "YOY – Like-to-Like Stores (LFL)":

    df_raw = data_source["YOY – Like-to-Like Stores (LFL)"].copy()
    ly_col, cy_col = detect_sales_columns(df_raw)

    if ly_col is None or cy_col is None:
        st.error("LFL sheet must contain both LY and CY sales columns.")
        st.stop()

    df = df_raw.rename(columns={
        "Site": "Store",
        ly_col: "Sales_LY",
        cy_col: "Sales_CY"
    })

    store_agg = df.groupby("Store").agg(
        Sales_LY=("Sales_LY", "sum"),
        Sales_CY=("Sales_CY", "sum")
    ).reset_index()

    store_agg["YOY_Δ"] = store_agg["Sales_CY"] - store_agg["Sales_LY"]
    store_agg["YOY_%"] = store_agg["YOY_Δ"] / store_agg["Sales_LY"]

    total_ly = store_agg["Sales_LY"].sum()
    total_cy = store_agg["Sales_CY"].sum()
    net_yoy = total_cy - total_ly
    yoy_pct = (net_yoy / total_ly) if total_ly else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Sales LY", f"₹{total_ly:,.0f}")
    c2.metric("Sales CY", f"₹{total_cy:,.0f}")
    c3.metric("Net YOY", f"₹{net_yoy:,.0f}")
    c4.metric("YOY %", f"{yoy_pct*100:.1f}%")

    fig = px.bar(
        store_agg.sort_values("YOY_Δ"),
        x="YOY_Δ",
        y="Store",
        orientation="h",
        title=f"LFL Store Impact — {period}",
        color=store_agg["YOY_Δ"] > 0,
        color_discrete_map={True: "green", False: "red"}
    )
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(store_agg, use_container_width=True)

# =====================================================
# 2️⃣ YOY OF HO
# =====================================================
elif view_mode == "YOY of HO":

    df = data_source["YOY OF HO"].copy()
    ly_col, cy_col = detect_sales_columns(df)

    if ly_col is None or cy_col is None:
        st.error("HO sheet must contain both LY and CY sales columns.")
        st.stop()

    total_ly = df[ly_col].sum()
    total_cy = df[cy_col].sum()
    net_yoy = total_cy - total_ly
    yoy_pct = (net_yoy / total_ly) if total_ly else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("HO LY", f"₹{total_ly:,.0f}")
    c2.metric("HO CY", f"₹{total_cy:,.0f}")
    c3.metric("Net YOY", f"₹{net_yoy:,.0f}")
    c4.metric("YOY %", f"{yoy_pct*100:.1f}%")

# =====================================================
# 3️⃣ CLOSED STORES
# =====================================================
elif view_mode == "Closed Stores":

    df = data_source["Closed Stores"].copy()
    ly_col, _ = detect_sales_columns(df)

    if ly_col is None:
        st.error("Closed Stores sheet must contain an LY sales column.")
        st.stop()

    lost_sales = df[ly_col].sum()
    st.metric(f"Revenue Lost — {period}", f"₹{lost_sales:,.0f}")

    fig = px.bar(
        df.groupby("Site")[ly_col].sum().reset_index(),
        x=ly_col,
        y="Site",
        orientation="h",
        title=f"Closed Store Impact — {period}"
    )
    st.plotly_chart(fig, use_container_width=True)

# =====================================================
# 4️⃣ NEW STORES
# =====================================================
elif view_mode == "New Stores":

    df = data_source["New Stores"].copy()
    _, cy_col = detect_sales_columns(df)

    if cy_col is None:
        st.error("New Stores sheet must contain a CY sales column.")
        st.stop()

    total_sales = df[cy_col].sum()
    avg_sales = df.groupby("Site")[cy_col].sum().mean()

    c1, c2 = st.columns(2)
    c1.metric(f"New Store Sales — {period}", f"₹{total_sales:,.0f}")
    c2.metric("Avg per Store", f"₹{avg_sales:,.0f}")

    fig = px.bar(
        df.groupby("Site")[cy_col].sum().reset_index(),
        x=cy_col,
        y="Site",
        orientation="h",
        title=f"New Store Contribution — {period}"
    )
    st.plotly_chart(fig, use_container_width=True)
