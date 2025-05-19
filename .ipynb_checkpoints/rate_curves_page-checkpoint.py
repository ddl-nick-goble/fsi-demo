import streamlit as st
import pandas as pd
import altair as alt
from domino.data_sources import DataSourceClient
from datetime import date, datetime

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
    return ds.query(sql).to_pandas()

# ─── Callbacks to modify session_state ────────────────────────────────────────
def on_date_change():
    """When the user picks a new date, append it if not already present."""
    new = st.session_state.selected_date
    if new not in st.session_state.selected_dates:
        st.session_state.selected_dates.append(new)

def remove_pills():
    """When the user clicks a pill, remove that date from our history."""
    # st.pills writes its selection into session_state['pills_selected']
    for s in st.session_state.pills_selected:
        # parse back into a date
        d = datetime.strptime(s, "%Y/%m/%d").date()
        if d in st.session_state.selected_dates:
            st.session_state.selected_dates.remove(d)
    # clear the pill selection so pills go away immediately
    st.session_state.pills_selected = []

# ─── App ────────────────────────────────────────────────────────────────────
def main():
    dates = get_available_dates()
    latest = dates[-1]

    # Initialize session state on first run:
    if "selected_dates" not in st.session_state:
        st.session_state.selected_dates = [latest]
    if "selected_date" not in st.session_state:
        st.session_state.selected_date = latest

    # 1) Calendar picker with callback
    st.date_input(
        "Select curve date",
        key="selected_date",
        min_value=dates[0],
        max_value=latest,
        on_change=on_date_change
    )

    # 2) Show each picked date as a removable pill
    pill_opts = [d.strftime("%Y/%m/%d") for d in st.session_state.selected_dates]
    st.pills(
        label="Dates selected so far (click any to remove):",
        options=pill_opts,
        selection_mode="multi",      # allow selecting multiple pills at once
        default=[],                  # start with none “active”
        key="pills_selected",        # writes list of clicked pills here
        on_change=remove_pills       # callback to drop them from state
    )

    # 3) Load & combine all curves in history
    all_dfs = []
    for dt in st.session_state.selected_dates:
        df = load_curve_for_date(dt)
        if not df.empty:
            df["curve_date"] = dt
            all_dfs.append(df)

    if not all_dfs:
        st.warning("Pick a date above to see its curve—and it will stay in the plot history!")
        return

    history_df = pd.concat(all_dfs, ignore_index=True)
    history_df["curve_date_str"] = history_df["curve_date"].apply(
        lambda d: d.strftime("%Y/%m/%d")
    )

    # 4) Plot all curves, colored by date
    chart = (
        alt.Chart(history_df)
        .mark_line(point=True)
        .encode(
            x=alt.X("tenor_num:Q", title="Tenor (yrs)"),
            y=alt.Y(
                "rate:Q",
                title="Rate (%)",
                scale=alt.Scale(zero=False),
                axis=alt.Axis(labelExpr="format(datum.value, '.2f') + '%'")
            ),
            color=alt.Color("curve_date_str:N", title="Curve Date"),
            tooltip=[
                alt.Tooltip("curve_date_str:N", title="Date"),
                alt.Tooltip("tenor_num:Q", title="Tenor (yrs)"),
                alt.Tooltip("rate:Q", title="Rate", format=".2f")
            ],
        )
        .properties(width=700, height=400)
        .interactive()
    )

    st.altair_chart(chart, use_container_width=True)


if __name__ == "__main__":
    main()
