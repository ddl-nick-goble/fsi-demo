mkdir ~/.streamlit

cat <<EOF > ~/.streamlit/config.toml
[browser]
gatherUsageStats = true

[server]
address = "0.0.0.0"
port = 8888
enableCORS = false
enableXsrfProtection = false
EOF

streamlit run dashboard.py
