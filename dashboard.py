import streamlit as st
import altair as alt
from st_pages import add_page_title, get_nav_from_toml

st.set_page_config(layout="wide")
with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def domino_theme():
    return {
      "config": {
        "background":   "#FAFAFA",      # bgLight1
        "axis": {
          "domainColor":  "#D6D6D6",    # borderMedium
          "gridColor":    "#D6D6D6",    # borderMedium
          "labelColor":   "#2E2E38",    # textPrimary
          "titleColor":   "#2E2E38"
        },
        "legend": {
          "labelColor":"#2E2E38",
          "titleColor":"#2E2E38"
        },
        "title": {
          "color":"#2E2E38"
        },
        # "range": {
        #   "category": [
        #     "#543FDE",  # primary
        #     "#30C578",  # success
        #     "#E90C31",  # danger
        #     "#E7D336"   # warning
        #   ]
        # }
      }
    }

alt.themes.register("domino", domino_theme)
alt.themes.enable("domino")

# Load navigation from .streamlit/pages.toml
nav = get_nav_from_toml()

# Create and render the navigation sidebar
pg = st.navigation(nav)
add_page_title(pg)

pg.run()
