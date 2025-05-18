import streamlit as st

from st_pages import add_page_title, get_nav_from_toml

st.set_page_config(layout="wide")

# Load navigation from .streamlit/pages.toml
nav = get_nav_from_toml()

# Create and render the navigation sidebar
# st.set_page_config(layout="wide")
pg = st.navigation(nav)
add_page_title(pg)
# pg.set_page_config(layout="wide")

pg.run()
