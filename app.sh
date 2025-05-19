mkdir -p .streamlit

cat <<EOF > .streamlit/config.toml
[browser]
gatherUsageStats = true

[server]
address = "0.0.0.0"
port = 8888
enableCORS = false
enableXsrfProtection = false

[theme]
primaryColor = "#543FDD"              # purple5000
backgroundColor = "#FFFFFF"           # neutralLight50
secondaryBackgroundColor = "#FAFAFA"  # neutralLight100
textColor = "#2E2E38"                 # neutralDark700
EOF

# Pages definition for st.navigation
cat <<EOF > .streamlit/pages.toml
[[pages]]
path = "equity_exposures.py"
name = "Home"

[[pages]]
path = "interest_rate_page.py"
name = "Overnight Reference Rates"

[[pages]]
path = "rate_curves_page.py"
name = "Rate Curves"

EOF

streamlit run dashboard.py
