import subprocess

# Deploy the Shiny app
# Assumes your app.py defines `app = App(...)` and is in the current folder
subprocess.run([
    "rsconnect", "deploy", "shiny",
    "--entrypoint", "app:app",
    "ncaabb_2025_2026/."
])
