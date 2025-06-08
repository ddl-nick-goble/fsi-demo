# app/ir_cone_dashboard.py

import streamlit as st
import pandas as pd
import altair as alt
from domino.data_sources import DataSourceClient
from datetime import date

# ─── Data access ────────────────────────────────────────────────────────────
ds = DataSourceClient().get_datasource("market_data")

@st.cache_data(ttl=120)
def get_available_dates() -> list[date]:
    df = ds.query("""
        SELECT DISTINCT curve_date
          FROM rate_cones
         ORDER BY curve_date
    """).to_pandas()
    df["curve_date"] = pd.to_datetime(df["curve_date"])
    return df["curve_date"].dt.date.tolist()

@st.cache_data(ttl=120)
def get_available_days(as_of_date: date) -> list[int]:
    df = ds.query(f"""
        SELECT DISTINCT days_forward
          FROM rate_cones
         WHERE curve_date = '{as_of_date}'
         ORDER BY days_forward
    """).to_pandas()
    return df["days_forward"].astype(int).tolist()

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
def load_cone_curves(as_of_date: date, days_forward: int) -> pd.DataFrame:
    sql = f"""
    SELECT tenor_num, cone_type, rate
      FROM rate_cones
     WHERE curve_date    = '{as_of_date}'
       AND days_forward = {days_forward}
     ORDER BY tenor_num, cone_type;
    """
    return ds.query(sql).to_pandas()

# ─── App ───────────────────────────────────────────────────────────────────
def main():
    dates = get_available_dates()
    if not dates:
        st.error("No cone dates found in rate_cones.")
        return

    col1, col2 = st.columns(2)
    
    with col1:
        as_of = st.selectbox(
            "As-of Date",
            options=dates,
            index=len(dates) - 1,
            format_func=lambda d: d.strftime("%Y-%m-%d")
        )
    
    with col2:
        days_opts = get_available_days(as_of)
        days_forward = st.selectbox(
            "Days Forward",
            options=days_opts,
            index=0
        )


    # ─── Load data ────────────────────────────────────────────────────────────
    base_df = load_base_curve(as_of)
    cone_df = load_cone_curves(as_of, days_forward)

    if base_df.empty or cone_df.empty:
        st.warning("No data for that date/horizon combination.")
        return

    base_df["tenor_num"] = base_df["tenor_num"].round(2)
    cone_df["tenor_num"] = cone_df["tenor_num"].round(2)

    # pivot cone curves
    cone_pivot = cone_df.pivot(
        index="tenor_num",
        columns="cone_type",
        values="rate"
    )
    scale_mode = st.session_state.get("scale_mode", "linear")

    # ─── Build layers ─────────────────────────────────────────────────────────
    layers = []
    for low, high, opacity in [("1%", "99%", 0.2), ("10%", "90%", 0.4)]:
        if low in cone_pivot.columns and high in cone_pivot.columns:
            band = (
                cone_pivot[[low, high]]
                .reset_index()
                .melt(
                    id_vars="tenor_num",
                    var_name="percentile",
                    value_name="rate"
                )
            )
            layers.append(
                alt.Chart(band)
                .mark_line(opacity=opacity, strokeWidth=2, interpolate="monotone")
                .encode(
                    x=alt.X(
                        f"tenor_num:{'O' if scale_mode=='even spacing' else 'Q'}",
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

    # base curve on top
    layers.append(
        alt.Chart(base_df)
        .mark_line(strokeWidth=3, interpolate="monotone")
        .encode(
            x=alt.X(
                f"tenor_num:{'O' if scale_mode=='even spacing' else 'Q'}",
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

    cone_pivot = cone_df.pivot(
        index="tenor_num",
        columns="cone_type",
        values="rate"
    ).reset_index()

    # ─── shaded 1%–99% band ───────────────────────────────────────────────────
    layers.append(alt.Chart(cone_pivot).mark_area(
        color="lightblue",
        opacity=0.05
    ).encode(
        x=alt.X(
            f"tenor_num:{'O' if scale_mode=='even spacing' else 'Q'}",
            title="Tenor (years)",
            axis=alt.Axis(labelExpr="format(datum.value, '.2f')", grid=True)
        ),
        y=alt.Y("1%:Q", title="Yield (%)", scale=alt.Scale(zero=False)),
        y2="99%:Q"
    ))
    
    layers.append(alt.Chart(cone_pivot).mark_area(
        color="lightblue",
        opacity=0.1
    ).encode(
        x=alt.X(
            f"tenor_num:{'O' if scale_mode=='even spacing' else 'Q'}",
            title="Tenor (years)",
            axis=alt.Axis(labelExpr="format(datum.value, '.2f')", grid=True)
        ),
        y=alt.Y("10%:Q", title="Yield (%)", scale=alt.Scale(zero=False)),
        y2="90%:Q"
    ))
    
    # ─── Compose & render ─────────────────────────────────────────────────────
    chart = (
        alt.layer(*layers)
        .properties(
            width=700,
            height=400,
            title=f"{days_forward}-Day IR Cones on {as_of}"
        )
        .configure_title(fontSize=18, fontWeight="bold")
        .configure_axis(labelFontSize=12, titleFontSize=14)
        .interactive()
    )
    st.altair_chart(chart, use_container_width=True)
    st.markdown(
        """
        <div style="display:flex; justify-content:center; gap:2em; margin-top: -1em;">
          <div style="display:flex; align-items:center;">
            <svg width="20" height="6"><rect width="20" height="6" style="fill:lightblue"/></svg>
            &nbsp;Base Curve
          </div>
          <div style="display:flex; align-items:center;">
            <svg width="20" height="6"><rect width="20" height="6" style="fill:lightblue;opacity:0.15"/></svg>
            &nbsp;1%–99% Band
          </div>
          <div style="display:flex; align-items:center;">
            <svg width="20" height="6"><rect width="20" height="6" style="fill:lightblue;opacity:0.3"/></svg>
            &nbsp;10%–90% Band
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # 3) X-axis spacing toggle
    st.radio(
        "X-axis spacing:",
        options=["linear", "even spacing"],
        index=0,
        key="scale_mode",
        horizontal=True
    )


if __name__ == "__main__":
    main()