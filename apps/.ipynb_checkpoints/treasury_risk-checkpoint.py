import streamlit as st
import pandas as pd
import altair as alt
from domino.data_sources import DataSourceClient
from datetime import date

# ─── Data access ────────────────────────────────────────────────────────────
ds = DataSourceClient().get_datasource("market_data")

@st.cache_data
def get_available_dates() -> list[date]:
    """
    Return a sorted list of all valuation_date values from the summary view.
    """
    df = ds.query("""
        SELECT DISTINCT valuation_date
          FROM tsy_valuation_summary
         ORDER BY valuation_date
    """).to_pandas()
    df["valuation_date"] = pd.to_datetime(df["valuation_date"])
    return df["valuation_date"].dt.date.tolist()

@st.cache_data
def get_security_types() -> list[str]:
    """
    Return all distinct security_type values from the summary view.
    """
    df = ds.query("""
        SELECT DISTINCT security_type
          FROM tsy_valuation_summary
         ORDER BY security_type
    """).to_pandas()
    return df["security_type"].dropna().astype(str).tolist()

@st.cache_data
def load_metrics_data(
    start_date: date, end_date: date
) -> pd.DataFrame:
    """
    Query valuation_date, security_type, and all requested metrics from tsy_valuation_summary
    between start_date and end_date. Returns a DataFrame with columns:
      - valuation_date (datetime)
      - security_type (string)
      - total_dv01
      - total_quantity
      - time_to_maturity_dv01_wavg
      - krd1y_dv01_wavg
      - krd2y_dv01_wavg
      - krd3y_dv01_wavg
      - krd5y_dv01_wavg
      - krd7y_dv01_wavg
      - krd10y_dv01_wavg
      - krd20y_dv01_wavg
      - krd30y_dv01_wavg
      - pca1_dv01_dv01_wavg
      - pca2_dv01_dv01_wavg
      - pca3_dv01_dv01_wavg
    """
    sql = f"""
      SELECT
        valuation_date,
        security_type,
        total_dv01,
        total_quantity,
        time_to_maturity_dv01_wavg,
        krd1y_dv01_wavg,
        krd2y_dv01_wavg,
        krd3y_dv01_wavg,
        krd5y_dv01_wavg,
        krd7y_dv01_wavg,
        krd10y_dv01_wavg,
        krd20y_dv01_wavg,
        krd30y_dv01_wavg,
        pca1_dv01_dv01_wavg,
        pca2_dv01_dv01_wavg,
        pca3_dv01_dv01_wavg
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
    selected_types = st.multiselect(
        "Select security types",
        options=all_types,
        default=all_types  # all selected by default
    )
    if not selected_types:
        st.warning("Please select at least one security type.")
        return

    # 4) Metric fields multi-select
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
    selected_metrics = st.multiselect(
        "Select metrics to plot",
        options=metric_options,
        default=metric_options  # all selected by default
    )
    if not selected_metrics:
        st.warning("Please select at least one metric.")
        return

    # 5) Load the data
    df = load_metrics_data(start_date, end_date)
    if df.empty:
        st.warning(f"No data between {start_date} and {end_date}.")
        return

    # 6) Filter by chosen security types
    df = df[df["security_type"].isin(selected_types)]
    if df.empty:
        st.warning("No data for the selected security types in this date range.")
        return

    # 7) Melt into long form: each row → (date, type, metric, value)
    long_df = df.melt(
        id_vars=["valuation_date", "security_type"],
        value_vars=selected_metrics,
        var_name="metric",
        value_name="value"
    ).dropna(subset=["value"])

    if long_df.empty:
        st.warning("After filtering, no data remains to plot.")
        return

    # 8) Build the Altair chart
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
                axis=alt.Axis(labelExpr="format(datum.value, '.2f')", grid=True), scale=alt.Scale(nice=True)
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

    # 9) Show raw pivoted data if desired
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
