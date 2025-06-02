import streamlit as st
import pandas as pd
import altair as alt
from domino.data_sources import DataSourceClient
from datetime import date

# ─── Data access ────────────────────────────────────────────────────────────
ds = DataSourceClient().get_datasource("market_data")

@st.cache_data
def get_available_dates() -> list[date]:
    df = ds.query("""
        SELECT DISTINCT valuation_date
          FROM tsy_valuation_summary
         ORDER BY valuation_date
    """).to_pandas()
    df["valuation_date"] = pd.to_datetime(df["valuation_date"])
    return df["valuation_date"].dt.date.tolist()

@st.cache_data
def get_security_types() -> list[str]:
    # We only ever need “Bill”, “Note”, “Bond”, “All Tsy” for filtering.
    return ["Bill", "Note", "Bond", "All Tsy"]

@st.cache_data
def load_metrics_data(
    start_date: date, end_date: date
) -> pd.DataFrame:
    """
    Pull every relevant price_closedform … and price_closedform_pca* … column
    that actually exists in tsy_valuation_summary.  Notice that PCA2 and PCA3 now
    also have the “down” shocks in the DB.
    """
    sql = f"""
      SELECT
        valuation_date,
        security_type,
        total_dv01,
        total_quantity,

        -- base price levels (qty‐weighted)
        price_closedform_qty_wavg,
        price_closedform_u25bps_qty_wavg,
        price_closedform_d25bps_qty_wavg,
        price_closedform_u100bps_qty_wavg,
        price_closedform_d100bps_qty_wavg,
        price_closedform_u200bps_qty_wavg,
        price_closedform_d200bps_qty_wavg,

        -- PCA1 shocks (up & down)
        price_closedform_pca1_u25bps_qty_wavg,
        price_closedform_pca1_d25bps_qty_wavg,
        price_closedform_pca1_u100bps_qty_wavg,
        price_closedform_pca1_d100bps_qty_wavg,
        price_closedform_pca1_u200bps_qty_wavg,
        price_closedform_pca1_d200bps_qty_wavg,

        -- PCA2 shocks (up & down)
        price_closedform_pca2_u25bps_qty_wavg,
        price_closedform_pca2_d25bps_qty_wavg,
        price_closedform_pca2_u100bps_qty_wavg,
        price_closedform_pca2_d100bps_qty_wavg,
        price_closedform_pca2_u200bps_qty_wavg,
        price_closedform_pca2_d200bps_qty_wavg,

        -- PCA3 shocks (up & down)
        price_closedform_pca3_u25bps_qty_wavg,
        price_closedform_pca3_d25bps_qty_wavg,
        price_closedform_pca3_u100bps_qty_wavg,
        price_closedform_pca3_d100bps_qty_wavg,
        price_closedform_pca3_u200bps_qty_wavg,
        price_closedform_pca3_d200bps_qty_wavg

      FROM tsy_valuation_summary
     WHERE valuation_date BETWEEN '{start_date}' AND '{end_date}'
     ORDER BY valuation_date, security_type;
    """
    df = ds.query(sql).to_pandas()
    if not df.empty:
        df["valuation_date"] = pd.to_datetime(df["valuation_date"])
    return df


# ─── Streamlit App ───────────────────────────────────────────────────────────
def main():
    # 1) Fetch available dates
    dates = get_available_dates()
    if not dates:
        st.error("No valuation dates found in tsy_valuation_summary.")
        return

    earliest = dates[0]
    latest = dates[-1]

    # 2) Date pickers
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "Start date",
            value=earliest,
            min_value=earliest,
            max_value=latest
        )
    with col2:
        end_date = st.date_input(
            "End date",
            value=latest,
            min_value=earliest,
            max_value=latest
        )
    if start_date > end_date:
        st.error("Start date must be on or before end date.")
        return

    # 3) Security types multi-select
    all_types = get_security_types()
    default_types = [t for t in ["Bond", "All Tsy"] if t in all_types]
    selected_types = st.multiselect(
        "Select security types",
        options=all_types,
        default=default_types
    )
    if not selected_types:
        st.warning("Please select at least one security type.")
        return

    # 4) Metric fields multi-select (for the Altair chart)
    metric_options = [
        "total_dv01",
        "total_quantity",
        "time_to_maturity_dv01_wavg",
        "krd1y_dv01_wavg",
        "krd2y_dv01_wavg",
        "krd3y_dv01_wavg",
        "krd5y_dv01_wavg",
        "krd7y_dv01_wavg",
        "krd10y_dv01_wavg",
        "krd20y_dv01_wavg",
        "krd30y_dv01_wavg",
        "pca1_dv01_dv01_wavg",
        "pca2_dv01_dv01_wavg",
        "pca3_dv01_dv01_wavg",
    ]
    default_metrics = ["total_dv01"]
    selected_metrics = st.multiselect(
        "Select metrics to plot",
        options=metric_options,
        default=default_metrics
    )
    if not selected_metrics:
        st.warning("Please select at least one metric.")
        return

    # 5) Load all the needed columns
    df = load_metrics_data(start_date, end_date)
    if df.empty:
        st.warning(f"No data between {start_date} and {end_date}.")
        return

    # 6) Filter by the user‐selected security types
    df = df[df["security_type"].isin(selected_types)]
    if df.empty:
        st.warning("No data for the selected security types in this date range.")
        return

    # ─── Liability Shock Summary for end_date ──────────────────────────────
    df_latest = df[df["valuation_date"].dt.date == end_date]
    if not df_latest.empty:
        rows = []

        # We only build rows for “Bond” and “All Tsy” – each will have 4 sub‐rows
        generic_labels = [
            "−200bps loss ($ mm)",
            "−100bps loss ($ mm)",
            "−25bps loss ($ mm)",
            "+25bps gain ($ mm)",
            "+100bps gain ($ mm)",
            "+200bps gain ($ mm)",
        ]

        for sec in ["Bond", "All Tsy"]:
            tmp = df_latest[df_latest["security_type"] == sec]
            if tmp.empty:
                continue

            r = tmp.iloc[0]
            qty = r["total_quantity"]
            base_price = r["price_closedform_qty_wavg"]

            # helper to compute P&L in $ mm; if column is absent or NaN, return NaN
            def pnl_mm(col_shock: str) -> float:
                if col_shock not in r or pd.isna(r[col_shock]):
                    return float("nan")
                return (base_price - r[col_shock]) * qty / 1e6

            total_cols = [
                "price_closedform_d200bps_qty_wavg",
                "price_closedform_d100bps_qty_wavg",
                "price_closedform_d25bps_qty_wavg",
                "price_closedform_u25bps_qty_wavg",
                "price_closedform_u100bps_qty_wavg",
                "price_closedform_u200bps_qty_wavg",
            ]
            pca1_cols = [
                "price_closedform_pca1_d200bps_qty_wavg",
                "price_closedform_pca1_d100bps_qty_wavg",
                "price_closedform_pca1_d25bps_qty_wavg",
                "price_closedform_pca1_u25bps_qty_wavg",
                "price_closedform_pca1_u100bps_qty_wavg",
                "price_closedform_pca1_u200bps_qty_wavg",
            ]
            pca2_cols = [
                "price_closedform_pca2_d200bps_qty_wavg",
                "price_closedform_pca2_d100bps_qty_wavg",
                "price_closedform_pca2_d25bps_qty_wavg",
                "price_closedform_pca2_u25bps_qty_wavg",
                "price_closedform_pca2_u100bps_qty_wavg",
                "price_closedform_pca2_u200bps_qty_wavg",
            ]
            pca3_cols = [
                "price_closedform_pca3_d200bps_qty_wavg",
                "price_closedform_pca3_d100bps_qty_wavg",
                "price_closedform_pca3_d25bps_qty_wavg",
                "price_closedform_pca3_u25bps_qty_wavg",
                "price_closedform_pca3_u100bps_qty_wavg",
                "price_closedform_pca3_u200bps_qty_wavg",
            ]

            # Now each mode only needs its list of shock‐columns (no DV01 field)
            mode_defs = [
                ("complete", total_cols),
                ("level",    pca1_cols),
                ("slope",    pca2_cols),
                ("curvature",pca3_cols),
            ]

            for mode_name, col_list in mode_defs:
                row = {"Type": f"{sec} ({mode_name})"}
                for label, shock_col in zip(generic_labels, col_list):
                    row[label] = pnl_mm(shock_col)
                rows.append(row)

        # 4) Build the DataFrame & format columns
        if rows:
            summary_df = pd.DataFrame(rows).set_index("Type")

            styled = (
                summary_df.style
                .format("${:,.2f}", subset=generic_labels)
            )

            st.subheader(f"Liability Shock Summary (as of {end_date})")
            st.dataframe(styled)

    # ─── Rest of the app (Altair chart etc.) ──────────────────────────────────
    long_df = df.melt(
        id_vars=["valuation_date", "security_type"],
        value_vars=selected_metrics,
        var_name="metric",
        value_name="value"
    ).dropna(subset=["value"])

    if long_df.empty:
        st.warning("After filtering, no data remains to plot.")
        return

    chart = (
        alt.Chart(long_df)
        .mark_line(point=True)
        .encode(
            x=alt.X(
                "valuation_date:T",
                title="Date",
                axis=alt.Axis(
                    format="%Y-%m-%d",
                    labelAngle=-45,
                    tickCount="day"
                )
            ),
            y=alt.Y(
                "value:Q",
                title="Metric Value",
                axis=alt.Axis(format=",.2f", grid=True),
                scale=alt.Scale(zero=False)
            ),
            color=alt.Color(
                "security_type:N",
                title="Security Type"
            ),
            strokeDash=alt.StrokeDash(
                "metric:N",
                title="Metric",
                legend=alt.Legend(columns=2)
            ),
            tooltip=[
                alt.Tooltip("valuation_date:T", title="Date", format="%Y-%m-%d"),
                alt.Tooltip("security_type:N", title="Type"),
                alt.Tooltip("metric:N", title="Metric"),
                alt.Tooltip("value:Q", title="Value", format=".2f"),
            ]
        )
        .properties(
            width=700,
            height=400,
            title=f"Treasury Risk Metrics ({', '.join(selected_types)})"
        )
        .interactive()
    )

    st.altair_chart(chart, use_container_width=True)

    if st.checkbox("Show raw data"):
        pivoted = (
            long_df
            .pivot_table(
                index="valuation_date",
                columns=["security_type", "metric"],
                values="value"
            )
            .fillna(0)
        )
        st.dataframe(pivoted)

if __name__ == "__main__":
    main()
