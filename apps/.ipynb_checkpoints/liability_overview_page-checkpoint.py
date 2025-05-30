import streamlit as st
import pandas as pd
from domino.data_sources import DataSourceClient
from datetime import date

# ─── Title & Intro ──────────────────────────────────────────────────────────
st.title("Liability Overview")
st.markdown(
    "This page shows the current bond-based liability inventory for ALM."
)

# ─── Data Access ────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def get_inventory_dates() -> list[date]:
    """Fetch distinct inventory dates to populate the date selector."""
    ds = DataSourceClient().get_datasource("market_data")
    df = ds.query(
        """
        SELECT DISTINCT inventory_date
          FROM bond_inventory
         ORDER BY inventory_date
        """
    ).to_pandas()
    df["inventory_date"] = pd.to_datetime(df["inventory_date"])  # ensure datetime
    return df["inventory_date"].dt.date.tolist()

@st.cache_data(show_spinner=False)
def load_inventory_for_date(inv_date: date) -> pd.DataFrame:
    """Load the full bond inventory snapshot for the selected date."""
    ds = DataSourceClient().get_datasource("market_data")
    sql = f"""
    SELECT
      cusip,
      quantity,
      security_type,
      security_term,
      issue_date,
      maturity_date,
      int_rate AS coupon,
      int_payment_frequency,
      series,
      price_per100,
      auction_date
    FROM bond_inventory
    WHERE inventory_date = '{inv_date}'
    ORDER BY maturity_date
    """
    return ds.query(sql).to_pandas()

# ─── Sidebar Controls ────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Controls")
    dates = get_inventory_dates()
    if not dates:
        st.error("No inventory data available.")
        st.stop()
    selected_date = st.date_input(
        "Inventory Date",
        value=dates[-1],
        min_value=dates[0],
        max_value=dates[-1],
    )
    st.write(f"Showing inventory for **{selected_date}**")

# ─── Load & Display ──────────────────────────────────────────────────────────
df = load_inventory_for_date(selected_date)
if df.empty:
    st.warning("No records found for this date.")
else:
    # Compute summary metrics
    total_qty = df["quantity"].sum()
    avg_coupon = (df["coupon"] * df["quantity"]).sum() / total_qty

    # Display KPIs
    k1, k2 = st.columns(2)
    k1.metric(label="Total Quantity", value=f"{total_qty:,.0f}")
    k2.metric(label="Weighted Avg Coupon", value=f"{avg_coupon:.3f}%")

    # Show data table
    st.subheader("Bond Inventory Table")
    st.dataframe(
        df.assign(
            issue_date=lambda x: pd.to_datetime(x["issue_date"]).dt.date,
            maturity_date=lambda x: pd.to_datetime(x["maturity_date"]).dt.date,
            auction_date=lambda x: pd.to_datetime(x["auction_date"]).dt.date,
        ),
        use_container_width=True,
    )

    # Optionally allow filtering by security type
    sec_types = df["security_type"].unique().tolist()
    filter_type = st.multiselect(
        "Filter by Security Type", options=sec_types, default=sec_types
    )
    if set(filter_type) != set(sec_types):
        df_filt = df[df["security_type"].isin(filter_type)]
        st.subheader("Filtered Inventory")
        st.dataframe(df_filt, use_container_width=True)
