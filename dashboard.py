import streamlit as st
import altair as alt
from st_pages import add_page_title, get_nav_from_toml

st.set_page_config(layout="wide")
with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

@alt.theme.register('domino', enable=True)
def domino_theme():
    return {
        "config": {
            "background": "#FFFFFF",
            "axis": {
                "domainColor": "#D6D6D6",
                "gridColor": "#D6D6D6",
                "labelColor": "#2E2E38",
                "titleColor": "#2E2E38",
                "labelFont": "Inter",
                "titleFont": "Inter"
            },
            "legend": {
                "labelColor": "#2E2E38",
                "titleColor": "#2E2E38",
                "labelFont": "Inter",
                "titleFont": "Inter"
            },
            "title": {
                "color": "#2E2E38",
                "font": "Inter"
            }
        }
    }


# Load navigation from .streamlit/pages.toml
nav = get_nav_from_toml()

# Create and render the navigation sidebar
pg = st.navigation(nav)
add_page_title(pg)

pg.run()
