import subprocess

# Deploy the Shiny app
# Assumes your app.py defines `app = App(...)` and is in the current folder
subprocess.run([
    "/home/ec2-user/.local/bin/rsconnect", "deploy", "shiny",
    "--entrypoint", "app:app",
    "/home/ec2-user/NCAABB_2025_2026/ncaabb_2025_2026/."
])
