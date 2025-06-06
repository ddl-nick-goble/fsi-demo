# app/ir_cone_dashboard.py

import streamlit as st
import pandas as pd
import altair as alt
import calendar
from domino.data_sources import DataSourceClient
from datetime import date

# ─── Data access ────────────────────────────────────────────────────────────
ds = DataSourceClient().get_datasource("market_data")

@st.cache_data(ttl=120)
def get_available_dates() -> list[date]:
    df = ds.query("""
        SELECT DISTINCT cone_date
          FROM rate_cones
         ORDER BY cone_date
    """).to_pandas()
    df["cone_date"] = pd.to_datetime(df["cone_date"])
    return df["cone_date"].dt.date.tolist()

@st.cache_data
def load_base_curve(as_of_date: date) -> pd.DataFrame:
    sql = f"""
    SELECT tenor_num, rate
      FROM rate_curves
     WHERE curve_date = '{as_of_date}'
     ORDER BY tenor_num;
    """
    return ds.query(sql).to_pandas()

@st.cache_data
def load_cone_curves(as_of_date: date) -> pd.DataFrame:
    sql = f"""
    SELECT tenor_num, cone_type, rate
      FROM rate_cones
     WHERE cone_date = '{as_of_date}'
     ORDER BY tenor_num, cone_type;
    """
    return ds.query(sql).to_pandas()

# ─── App ───────────────────────────────────────────────────────────────────
def main():
    dates = get_available_dates()
    if not dates:
        st.error("No cone dates found in rate_cones.")
        return
    latest = dates[-1]

    # preserve scale_mode in session_state
    if "scale_mode" not in st.session_state:
        st.session_state.scale_mode = "linear"

    # ─── TOP CONTROLS ──────────────────────────────────────────────────────────
    c1, c2 = st.columns(2)
    with c1:
        as_of = st.date_input(
            "As-of Date",
            value=st.session_state.get("as_of_date", latest),
            min_value=dates[0],
            max_value=latest,
            key="as_of_date"
        )
    with c2:
        scale_mode = st.radio(
            "X-axis spacing:",
            options=["linear", "even spacing"],
            index=0,
            key="scale_mode",
            horizontal=True
        )

    as_of = st.session_state.as_of_date

    base_df = load_base_curve(as_of)
    cone_df = load_cone_curves(as_of)

    if base_df.empty or cone_df.empty:
        st.warning("No data for the selected as-of date.")
        return

    # Pivot cone curves so each cone_type is a column
    cone_pivot = cone_df.pivot(index="tenor_num", columns="cone_type", values="rate")

    # ─── BUILD LAYERS ──────────────────────────────────────────────────────────
    layers = []

    for low, high, opacity in [("1%", "99%", 0.2), ("10%", "90%", 0.4)]:
        if low in cone_pivot.columns and high in cone_pivot.columns:
            df_band = (
                cone_pivot[[low, high]]
                .reset_index()
                .melt(id_vars="tenor_num", var_name="percentile", value_name="rate")
            )
            layers.append(
                alt.Chart(df_band)
                .mark_line(color="steelblue", opacity=opacity, strokeWidth=2, interpolate="monotone")
                .encode(
                    x=alt.X(
                        "tenor_num:" + ("O" if st.session_state.scale_mode=="even spacing" else "Q"),
                        title="Tenor (years)",
                        axis=alt.Axis(labelExpr="format(datum.value, '.2f')", grid=True)
                    ),
                    y=alt.Y(
                        "rate:Q",
                        title="Yield (%)",
                        scale=alt.Scale(zero=False),
                        axis=alt.Axis(labelExpr="format(datum.value, '.2f') + '%'", grid=True)
                    ),
                    detail="percentile:N"
                )
            )

    # Base curve layer
    layers.append(
        alt.Chart(base_df)
        .mark_line(color="crimson", strokeWidth=3, interpolate="monotone")
        .encode(
            x=alt.X(
                "tenor_num:" + ("O" if st.session_state.scale_mode=="even spacing" else "Q"),
                title="Tenor (years)",
                axis=alt.Axis(labelExpr="format(datum.value, '.2f')", grid=True)
            ),
            y=alt.Y(
                "rate:Q",
                title="Yield (%)",
                axis=alt.Axis(labelExpr="format(datum.value, '.2f') + '%'", grid=True)
            )
        )
    )

    # ─── COMPOSE CHART ─────────────────────────────────────────────────────────
    chart = (
        alt.layer(*layers)
        .properties(
            width=700,
            height=400,
            title=f"IR Cones on {as_of}"
        )
        .configure_title(fontSize=18, fontWeight="bold")
        .configure_axis(labelFontSize=12, titleFontSize=14)
        .interactive()
    )

    st.altair_chart(chart, use_container_width=True)


if __name__ == "__main__":
    main()
