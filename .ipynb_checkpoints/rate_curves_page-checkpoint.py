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
        SELECT DISTINCT curve_date
          FROM rate_curves
         ORDER BY curve_date
    """).to_pandas()
    df["curve_date"] = pd.to_datetime(df["curve_date"])
    return df["curve_date"].dt.date.tolist()

@st.cache_data
def load_curve_for_date(selected_date: date) -> pd.DataFrame:
    sql = f"""
    SELECT tenor_num, rate
      FROM rate_curves
     WHERE curve_date = '{selected_date}'
     ORDER BY tenor_num;
    """
    df = ds.query(sql).to_pandas()
    return df

dset = []

# ─── App ────────────────────────────────────────────────────────────────────
def main():
    # 1) Calendar picker (single date)
    dates = get_available_dates()
    pick = st.date_input(
        "Select curve date",
        value=dates[-1],
        min_value=dates[0],
        max_value=dates[-1],
    )
    dset.append(pick)
    print(dset)
    # 2) Load & plot
    curve = load_curve_for_date(pick)
    if curve.empty:
        st.warning("No data for that date.")
        return

    chart = (
        alt.Chart(curve)
        .mark_line(point=True)
        .encode(
            x=alt.X("tenor_num:Q", title="Tenor (yrs)"),
            y=alt.Y(
                "rate:Q",
                title="Rate (%)",
                axis=alt.Axis(labelExpr="format(datum.value, '.2f') + '%'")
            ),
        )
        .properties(width=700, height=400)
        .interactive()
    )
    st.altair_chart(chart, use_container_width=True)

    # ─── New: show the picked date in a div under the chart ────────────────
    st.markdown(
        f"<div style='margin-top:10px; font-size:14px; color:#555;'>"
        f"Selected curve date: <strong>{pick}</strong>"
        f"</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
