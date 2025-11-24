import subprocess

# Add your ShinyApps.io account
# Replace with your actual account name, token, and secret from shinyapps.io
# account_name = "mmacias"
# token = "43D70152C005CBF3EECCCB3EFB986C69"
# secret = "QSarSmVp0UWmDhmhxTIF0pcYewkQjL4SOCRXlvJK"

# subprocess.run([
#     "rsconnect", "add",
#     "--account", account_name,
#     "--name", account_name,
#     "--token", token,
#     "--secret", secret
# ])

# 3. Deploy the Shiny app
# Assumes your app.py defines `app = App(...)` and is in the current folder
subprocess.run([
    "rsconnect", "deploy", "shiny",
    "--entrypoint", "app:app",
    "ncaabb_2025_2026/."
])
