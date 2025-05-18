mkdir -p .streamlit

cat <<EOF > .streamlit/config.toml
[browser]
gatherUsageStats = true

[server]
address = "0.0.0.0"
port = 8501
enableCORS = false
enableXsrfProtection = false

[theme]
primaryColor = "#543FDD"              # purple5000
backgroundColor = "#FFFFFF"           # neutralLight50
secondaryBackgroundColor = "#FAFAFA"  # neutralLight100
textColor = "#2E2E38"                 # neutralDark700
font = "Inter"                        # explicit Inter
EOF

# Pages definition for st.navigation
cat <<EOF > .streamlit/pages.toml
[[pages]]
path = "dashboard.py"
name = "Home"
icon = ":house:"

[[pages]]
path = "interest_rate_page.py"
name = "Interest Rate Exposures"
icon = "💹"

EOF

streamlit run dashboard.py
