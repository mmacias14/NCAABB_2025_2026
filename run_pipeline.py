import subprocess
import sys
import datetime
import shutil

# ANSI color codes
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"

# Create a timestamped log file
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = f"pipeline_log_{timestamp}.txt"

# Track step outcomes
step_results = {}

def log_message(message):
    print(message)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(message + "\n")

# Function to run a Python script in format 'python script_name' and log output
def run_python_script(script_name):
    log_message(f"\n Running script {script_name}...")
    result = subprocess.run([sys.executable, script_name], capture_output=True, text=True)
    log_message(result.stdout)
    if result.stderr:
        log_message(f" Errors/Warnings in {script_name}:\n{result.stderr}")
        step_results[script_name] = f"{YELLOW}Warnings/Errors{RESET}"
    else:
        step_results[script_name] = f"{GREEN}Success{RESET}"

def run_notebook(notebook_name):
    log_message(f"\n Executing notebook {notebook_name}...")
    result = subprocess.run([
        sys.executable, "-m", "nbconvert",
        "--to", "notebook", "--execute",
        "--inplace", notebook_name
    ], capture_output=True, text=True)
    log_message(result.stdout)
    if result.stderr:
        log_message(f" Errors/Warnings in {notebook_name}:\n{result.stderr}")
        step_results[notebook_name] = f"{YELLOW}Warnings/Errors{RESET}"
    else:
        step_results[notebook_name] = f"{GREEN}Success{RESET}"

if __name__ == "__main__":
    # Step 1: Run web scraping
    run_python_script("web_scraping.py")

    # Step 2: Run injury report scraping
    run_python_script("injury_report_scraping.py")

    # Step 3: Run model training notebook
    run_notebook("model_training_Spread+MoneyLine_model_NN.ipynb")

    # Step 4: Copy NCAA_Basketball_Spread_Predictions_2025_2026.rds file to ncaabb_2025_2026 folder using shutil
    shutil.copy("NCAA_Basketball_Spread_Predictions_2025_2026.rds", "ncaabb_2025_2026/NCAA_Basketball_Spread_Predictions_2025_2026.rds")

    # Step 5: Run app
    subprocess.run(["python", "ncaabb_2025_2026/deploy_shiny.py"])

    # Final summary
    log_message("\n Workflow Summary:")
    for step, outcome in step_results.items():
        log_message(f" - {step}: {outcome}")

    log_message("\n Workflow completed (errors were logged if any occurred).")
    print(f" Logs saved to {log_file}")