#!/usr/bin/env bash
set -euo pipefail

# to use, run PORT=8501 bash app.sh
# run this if needed pkill -f streamlit

# Default to prod port 8888, but allow override via ENV or CLI arg
PORT="${PORT:-${1:-8888}}"

mkdir -p .streamlit

cat > .streamlit/config.toml <<EOF
[browser]
gatherUsageStats = true

[server]
address = "0.0.0.0"
port = $PORT
enableCORS = false
enableXsrfProtection = false

[theme]
primaryColor = "#543FDD"              # purple5000
backgroundColor = "#FFFFFF"           # neutralLight50
secondaryBackgroundColor = "#FAFAFA"  # neutralLight100
textColor = "#2E2E38"                 # neutralDark700
EOF

cat > .streamlit/pages.toml <<EOF
[[pages]]
path = "home_page.py"
name = "Home"

[[pages]]
path = "rate_curves_page.py"
name = "Rate Curves"

[[pages]]
path = "rate_curve_surface.py"
name = "Rate Curve Surface"

[[pages]]
path = "rate_simulations_page.py"
name = "Rate Simulations"

[[pages]]
path = "treasury_inventory.py"
name = "Treasury Inventory"

[[pages]]
path = "treasury_risk.py"
name = "Treasury Risk"

[[pages]]
path = "interest_rate_page.py"
name = "Overnight Rates"

EOF

streamlit run apps/dashboard.py
