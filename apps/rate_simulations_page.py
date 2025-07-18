# app/ir_cone_dashboard.py

import streamlit as st
import pandas as pd
import altair as alt
from domino.data_sources import DataSourceClient
from datetime import date

BASE_COLOR   = "crimson"
MODEL_COLORS = ["#1f77b4", "#ff7f0e"]  # first model → blue, second → orange

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

@st.cache_data(ttl=120)
def get_available_models(as_of_date: date, days_forward: int) -> list[str]:
    df = ds.query(f"""
        SELECT DISTINCT model_type
          FROM rate_cones
         WHERE curve_date    = '{as_of_date}'
           AND days_forward = {days_forward}
         ORDER BY model_type
    """).to_pandas()
    return df["model_type"].tolist()

@st.cache_data
def load_base_curve(as_of_date: date) -> pd.DataFrame:
    sql = f"""
    SELECT tenor_num, rate
      FROM rate_curves
     WHERE curve_date = '{as_of_date}'
     ORDER BY tenor_num;
    """
    return ds.query(sql).to_pandas()

@st.cache_data(ttl=120)
def load_all_cone_curves(as_of_date: date, days_forward: int) -> pd.DataFrame:
    sql = f"""
    SELECT
      tenor_num,
      cone_type,
      rate,
      model_type
    FROM rate_cones
    WHERE curve_date   = '{as_of_date}'
      AND days_forward = {days_forward}
    ORDER BY tenor_num, cone_type, model_type;
    """
    return ds.query(sql).to_pandas()

# ─── App ───────────────────────────────────────────────────────────────────
def main():
    dates = get_available_dates()
    if not dates:
        st.error("No cone dates found in rate_cones.")
        return

    # Top controls: three columns
    col1, col2 = st.columns(2, vertical_alignment="bottom")
    col3, col4 = st.columns(2)
    with col3:
        # bounds for the picker
        min_date, max_date = dates[0], dates[-1]
        # default to the latest available
        picked = st.date_input(
            "As-of Date",
            value=max_date,
            min_value=min_date,
            max_value=max_date
        )
        # if they pick a date with no data, snap down to the closest earlier one
        if picked not in dates:
            # find all available ≤ picked
            earlier = [d for d in dates if d <= picked]
            if earlier:
                as_of = max(earlier)
                st.warning(f"No data for {picked}; using {as_of} instead.")
            else:
                # no earlier dates (shouldn't happen unless picked < min_date)
                as_of = min_date
                st.warning(f"No data before {picked}; using {as_of}.")
        else:
            as_of = picked

    with col1:
        st.markdown(
            """
            <p>This interactive app lets you explore projected yield-curve risk bands for U.S. Treasuries.</p>
            <ol style="font-size:smaller; padding-left:1.2em; margin-top:0.5em;">
              <li><strong>Select an As-of Date</strong> to choose your base yield curve.</li>
              <li><strong>Pick a Forecast Horizon</strong> (Days Forward) for the cone projection.</li>
              <li><strong>Compare up to Two Models</strong> side-by-side to see their 1%–99% and 10%–90% bands.</li>
            </ol>
            """,
            unsafe_allow_html=True
        )
    with col2:
        days_opts = get_available_days(as_of)
        days_forward = st.selectbox(
            "Days Forward",
            options=days_opts,
            index=0
        )
    with col4:
        model_opts = get_available_models(as_of, days_forward)
        selected_models = st.multiselect(
            "Model Types",
            options=model_opts,
            default=model_opts[:2]
        )

    if len(selected_models) > 2:
        st.error("Please select at most 2 models.")
        selected_models = selected_models[:2]

    # ─── Load data ────────────────────────────────────────────────────────────
    base_df = load_base_curve(as_of)
    all_cones = load_all_cone_curves(as_of, days_forward)
    cone_df = all_cones[all_cones["model_type"].isin(selected_models)]

    if base_df.empty or cone_df.empty:
        st.warning("No data for that date/horizon/model combination.")
        return

    base_df["tenor_num"] = base_df["tenor_num"].round(2)
    cone_df["tenor_num"] = cone_df["tenor_num"].round(2)

    # ─── Build layers (base curve + one 1–99% and one 10–90% band per model) ────
    scale_mode = st.session_state.get("scale_mode", "linear")
    layers = []
    
    # For each selected model, draw two bands
    for idx, model in enumerate(selected_models):
        model_color = MODEL_COLORS[idx]
        df_model = cone_df[cone_df["model_type"] == model]
        pivot_model = df_model.pivot_table(
            index="tenor_num",
            columns="cone_type",
            values="rate",
            aggfunc="mean"
        ).reset_index()
    
        # 1%–99% band
        if {"1%", "99%"}.issubset(pivot_model.columns):
            band1 = pivot_model[["tenor_num", "1%", "99%"]].copy()
            band1["model_type"] = model
            layers.append(
                alt.Chart(band1)
                .mark_area(color=model_color, opacity=0.2, interpolate="monotone")
                .encode(
                    x=alt.X(
                        f"tenor_num:{'O' if scale_mode=='even spacing' else 'Q'}"
                    ),
                    y="1%:Q",
                    y2="99%:Q",
                    color=alt.Color("model_type:N", title="Model", legend=None)
                )
            )
            # top & bottom boundary lines
            for pct in ["1%", "99%"]:
                layers.append(
                    alt.Chart(band1)
                    .mark_line(color=model_color, strokeWidth=2, interpolate="monotone")
                    .encode(
                        x=alt.X(f"tenor_num:{'O' if scale_mode=='even spacing' else 'Q'}"),
                        y=alt.Y(f"{pct}:Q"),
                        detail=alt.Detail("model_type:N")
                    )
                )
    
        # 10%–90% band
        if {"10%", "90%"}.issubset(pivot_model.columns):
            band2 = pivot_model[["tenor_num", "10%", "90%"]].copy()
            band2["model_type"] = model
            layers.append(
                alt.Chart(band2)
                .mark_area(color=model_color, opacity=0.1, interpolate="monotone")
                .encode(
                    x=alt.X(
                        f"tenor_num:{'O' if scale_mode=='even spacing' else 'Q'}"
                    ),
                    y="10%:Q",
                    y2="90%:Q",
                    color=alt.Color("model_type:N", title="Model", legend=None)
                )
            )
            for pct in ["10%", "90%"]:
                layers.append(
                    alt.Chart(band2)
                    .mark_line(color=model_color, strokeDash=[4,2], strokeWidth=1, interpolate="monotone")
                    .encode(
                        x=alt.X(f"tenor_num:{'O' if scale_mode=='even spacing' else 'Q'}"),
                        y=alt.Y(f"{pct}:Q"),
                        detail=alt.Detail("model_type:N")
                    )
                )

    # Base curve layer
    layers.append(
        alt.Chart(base_df)
        .mark_line(color=BASE_COLOR, strokeWidth=3, interpolate="monotone")
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
            )
        )
    )
    

    # ─── Compose & render ─────────────────────────────────────────────────────
    chart = (
        alt.layer(*layers)
        .properties(
            width=700,
            height=600,
            title=f"{days_forward}-Day IR Cones on {as_of}"
        )
        .configure_title(fontSize=18, fontWeight="bold")
        .configure_axis(labelFontSize=12, titleFontSize=14)
        .interactive()
    )
    st.altair_chart(chart, use_container_width=True)
    # ─── Dynamic legend ───────────────────────────────────────────────────────
    legend_items = []

    # Base Curve (solid red)
    legend_items.append(
        f'<div style="display:flex; align-items:center; gap:0.5em;">'
        f'<svg width="20" height="2">'
        f'<line x1="0" y1="1" x2="20" y2="1" style="stroke:{BASE_COLOR};stroke-width:3;"/>'
        f'</svg> Base Curve'
        f'</div>'
    )

    # First model bands (solid & dotted blue)
    if selected_models:
        m0 = selected_models[0]
        c0 = MODEL_COLORS[0]
        legend_items.append(
            '<div style="display:flex; flex-direction:column; gap:0.25em;">'
              f'<div style="display:flex; align-items:center; gap:0.5em;">'
                f'<svg width="20" height="2">'
                f'<line x1="0" y1="1" x2="20" y2="1" '
                  f'style="stroke:{c0};stroke-width:2;"/>'
                f'</svg> {m0} 1%–99% Band'
              f'</div>'
              f'<div style="display:flex; align-items:center; gap:0.5em;">'
                f'<svg width="20" height="2">'
                f'<line x1="0" y1="1" x2="20" y2="1" '
                  f'style="stroke:{c0};stroke-width:1;stroke-dasharray:4 2;"/>'
                f'</svg> {m0} 10%–90% Band'
              f'</div>'
            '</div>'
        )

    # Second model bands (solid & dotted orange), if present
    if len(selected_models) > 1:
        m1 = selected_models[1]
        c1 = MODEL_COLORS[1]
        legend_items.append(
            '<div style="display:flex; flex-direction:column; gap:0.25em;">'
              f'<div style="display:flex; align-items:center; gap:0.5em;">'
                f'<svg width="20" height="2">'
                f'<line x1="0" y1="1" x2="20" y2="1" '
                  f'style="stroke:{c1};stroke-width:2;"/>'
                f'</svg> {m1} 1%–99% Band'
              f'</div>'
              f'<div style="display:flex; align-items:center; gap:0.5em;">'
                f'<svg width="20" height="2">'
                f'<line x1="0" y1="1" x2="20" y2="1" '
                  f'style="stroke:{c1};stroke-width:1;stroke-dasharray:4 2;"/>'
                f'</svg> {m1} 10%–90% Band'
              f'</div>'
            '</div>'
        )

    # Render all columns side-by-side
    legend_html = (
        '<div style="display:flex; justify-content:center; gap:2em; margin-top:-1em;">'
        + ''.join(legend_items) +
        '</div>'
    )
    col5, col6 = st.columns(2, vertical_alignment="bottom")
    with col5:
        st.radio(
            "X-axis spacing:",
            options=["linear", "even spacing"],
            index=0,
            key="scale_mode",
            horizontal=True
        )
    with col6:
        st.markdown(legend_html, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
