import pytz
from shiny import App, ui, render
import pandas as pd
import plotly.express as px
import pickle
import datetime
from datetime import datetime, date, timedelta
import numpy as np
from sklearn.metrics import (
    mean_squared_error,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score
)
from shinywidgets import output_widget, render_widget  

# Load data file NCAA_Basketball_Spread_Predictions_2025_2026.rds
with open("NCAA_Basketball_Spread_Predictions_2025_2026.rds", "rb") as f:
    df_predictions = pickle.load(f)

# Prepare data
df_master = df_predictions.copy()

# Determine predicted winner
df_master["Predicted.Winner"] = df_master.apply(
    lambda row: row["Favorite"] if row["Predicted.Underdog.Win.Prob"] < 0.5 else row["Underdog"], axis=1)

# Determine predicted winner ranking position based on predicted win probability
df_master["Predicted.Winner.Ranking.Position"] = df_master.apply(
    lambda row: "Favorite" if row["Predicted.Underdog.Win.Prob"] < 0.5 else "Underdog", axis=1)

# Determine actual winner
df_master["Actual.Winner"] = df_master.apply(
    lambda row: row["Home"] if row["Score.Diff"] > 0 else row["Away"], axis=1)

# Find Probability of predicted winner
df_master["Win.Probability"] = df_master.apply(
    lambda row: row["Predicted.Underdog.Win.Prob"] if row["Predicted.Winner"] == row["Underdog"]
    else 1 - row["Predicted.Underdog.Win.Prob"], axis=1)

#Round Probability
df_master['Win.Probability'] = round(df_master['Win.Probability'],3)

#If Probability  is 1, set to 0.999
df_master['Win.Probability'] = df_master['Win.Probability'].apply(lambda x: 0.999 if x == 1 else x)

# Round Score.Diff
df_master['Predicted.Score.Diff'] = (df_master['Predicted.Score.Diff'] * 2).round() / 2

# Convert to datetime and back to string without time
df_master['Date.Game'] = pd.to_datetime(df_master['Date.Game']).dt.strftime('%Y-%m-%d')

# Subset df_master for played games
df_played = df_master.dropna(subset=["Home.Points", "Away.Points"])

# Create metrics dataframe
rmse = np.sqrt(mean_squared_error(df_played['Score.Diff'],df_played['Predicted.Score.Diff']))
mae = (df_played['Score.Diff'] - df_played['Predicted.Score.Diff']).abs().mean()
accuracy = accuracy_score(df_played['Underdog.Win'], df_played['Predicted.Underdog.Win.Prob'] > 0.5)
recall = recall_score(df_played['Underdog.Win'], df_played['Predicted.Underdog.Win.Prob'] > 0.5)
precision = precision_score(df_played['Underdog.Win'], df_played['Predicted.Underdog.Win.Prob'] > 0.5)
f1 = f1_score(df_played['Underdog.Win'], df_played['Predicted.Underdog.Win.Prob'] > 0.5)

df_metrics = {
    "rmse.spread": rmse,
    "mae.spread": mae,
    "accuracy.moneyline": accuracy,
    "recall.moneyline": recall,
    "precision.moneyline": precision,
    "f1.moneyline": f1
}

df_metrics = pd.DataFrame([df_metrics])

# Rename Score.Diff for display in the app
df_master = df_master.rename(columns={"Score.Diff": "Actual.Score.Diff"})

# Exclude records from df_plot where the predicted winner is not consistent with the predicted score difference
# For example, if the predicted winner is the home team but the predicted score difference is negative (indicating the away team is favored), remove that record
df_master = df_master[~(
    ((df_master["Predicted.Winner"] == df_master["Home"]) & (df_master["Predicted.Score.Diff"] < 0)) |
    ((df_master["Predicted.Winner"] == df_master["Away"]) & (df_master["Predicted.Score.Diff"] > 0))
)]

# Set today's date as it currently stands in central time zone
today_central = datetime.now(pytz.timezone('US/Central')).strftime('%Y-%m-%d')

# Filter for upcoming games
df_date = df_master[df_master["Date.Game"] >= today_central]
df_plot = df_master[df_master["Date.Game"] >= today_central].copy()

# --- UI ---
app_ui = ui.page_fluid(

    ui.h1("2025-2026 NCAA Men's Basketball Predictions"),

    ui.layout_columns(  
        ui.card(
            ui.h3("Model Details:"),
            ui.output_text("model_date"),
            ui.p("- Point Differential Model: Neural Network with Home Team Point Differential Response"),
            ui.p("- Game Winner Model: Neural Network with Underdog Win Classifier"),
            ui.p("- Underdogs are defined as teams with lower pre-game power rankings"),
            ui.p("- Only games where at least one team is ranked in the top 200 are evaluated"),
            ui.p("- Games where the two models disagree on the predicted winner have been excluded from the predictions"),
            ui.h3("Model Performance Metrics:"),
            ui.output_text("model_spread"),
            ui.output_text("model_winloss_acc"),
            ui.output_text("model_winloss_prec"),
            ui.output_text("model_winloss_recall"),
            ui.output_text("model_winloss_f1"),
            style="font-size: 12px;"   # 👈 smaller font for this card only
        ),
        ui.card(
            ui.h2("Upcoming Game Predictions"),
            #ui.h4("Filter by Date.Game"),
            ui.input_selectize(
                "date_select",
                "Choose Date(s):",
                choices=list(df_plot["Date.Game"].unique()),
                selected=[df_plot["Date.Game"].unique()[0]],
                multiple=True
            ),
            output_widget("daily_plot"),
            ui.output_data_frame("date_table"),
            ui.p("Note: Games where the Predicted.Score.Diff is negative means the Away team is the predicted winner."),
            ui.h2("Past Game Results"),
            output_widget("all_plot"),
            ui.output_data_frame("past_table")
        ),
        col_widths=(3, 9)
    )
)

# --- Server ---
def server(input, output, session):


    @output
    @render.text
    def model_date(df_played=df_played):
        # Find the last Date.Game in df_played
        last_date_played = df_played['Date.Game'].max()
        return f"- Trained using games played through: {last_date_played}"

    @output
    @render.text
    def model_spread():
        return f"- Point Differential Model Standard Deviation: ± {round(df_metrics['rmse.spread'].item(), 1)} pts"

    @output
    @render.text
    def model_winloss_acc():
        return f"- Game Winner Overall Prediction Accuracy: {round(100 * df_metrics['accuracy.moneyline'].item(), 1)}%"

    @output
    @render.text
    def model_winloss_prec():
        return f"- Game Winner Model Predicted Underdog Win Accuracy (Precision): {round(100 * df_metrics['precision.moneyline'].item(), 1)}%"

    @output
    @render.text
    def model_winloss_recall():
        return f"- Game Winner Model Actual Underdog Win Detection Rate (Recall): {round(100 * df_metrics['recall.moneyline'].item(), 1)}%"

    @output
    @render.text
    def model_winloss_f1():
        return f"- Game Winner Model F1 Score: {round(100 * df_metrics['f1.moneyline'].item(), 1)}%"

    @output
    @render_widget
    def daily_plot():
        today_central = datetime.now(pytz.timezone('US/Central')).strftime('%Y-%m-%d')
        df_plot = df_master[df_master["Date.Game"] >= today_central].copy()

        # Exclude records from df_plot where the predicted winner is not consistent with the predicted score difference
        # For example, if the predicted winner is the home team but the predicted score difference is negative (indicating the away team is favored), remove that record
        df_plot = df_plot[~(
            ((df_plot["Predicted.Winner"] == df_plot["Home"]) & (df_plot["Predicted.Score.Diff"] < 0)) |
            ((df_plot["Predicted.Winner"] == df_plot["Away"]) & (df_plot["Predicted.Score.Diff"] > 0))
        )]
        
        # Create an 'Opponent' column for hover data
        df_plot['Opponent'] = df_plot.apply(lambda row: row['Home'] if row['Predicted.Winner'] == row['Away'] else row['Away'], axis = 1)

        # Adjust Predicted.Score.Diff to be absolute value for plotting
        df_plot["Predicted.Score.Diff"] = df_plot.apply(
            lambda row: -row["Predicted.Score.Diff"] if row["Predicted.Score.Diff"] < 0
            else row["Predicted.Score.Diff"], axis=1)
        
        selected_dates = input.date_select()
        df_filtered = df_plot[df_plot["Date.Game"].isin(selected_dates)]

        # Build daily plot
        fig_date = px.scatter(
            df_filtered,
            x="Predicted.Score.Diff",
            y="Win.Probability",
            color="Predicted.Winner.Ranking.Position",
            opacity=0.7,
            hover_data=["Date.Game","Predicted.Winner","Opponent","Predicted.Score.Diff","Win.Probability"]
        )

        fig_date.update_traces(marker=dict(size=6, opacity=0.7))

        fig_date.add_annotation(
            text="MOST PROBABLE",
            x=rmse.item() + 15,
            y=0.925,
            showarrow=False,
            font=dict(color="red")
        )

        fig_date.add_annotation(
            text="WINNERS",
            x=rmse.item() + 15,
            y=0.9,
            showarrow=False,
            font=dict(color="red")
        )

        prob_thresholds = [0.67, 0.95, 1]
        colors = [
            "rgba(200,0,0,0.3)",    # red (low confidence)
            "rgba(200,200,0,0.3)",  # yellow (medium confidence)
            "rgba(0,200,0,0.3)"     # green (high confidence)
        ]

        # Add circular bands for each probability range
        for i, color in enumerate(colors):
            fig_date.add_shape(
                type="circle",
                xref="x", yref="y",
                x0=-(i+1) * rmse.item(),
                y0= 0.5 - (prob_thresholds[i] - 0.5),       # lower bound of probability band
                x1=(i+1) * rmse.item(),
                y1=prob_thresholds[i],     # upper bound of probability band
                fillcolor=color,
                opacity=0.4,
                line_width=0,
                layer="below"
            )

        fig_date.update_layout(
            title="Predicted Winners with Circular Error Bands",
            xaxis_title="Predicted Point Differential",
            yaxis_title="Predicted Win Probability",
            xaxis_range=[0, 40],
            yaxis_range=[0.5, 1.1]
            )
        fig_date.update_layout(legend=dict(font=dict(size=9)))
        legend_title = "Predicted.Winner. Ranking.Position"
        wrapped_title = "<br>".join(legend_title.split(" "))
        fig_date.update_layout(legend=dict(title=dict(text=wrapped_title)))
        return fig_date




    @output
    @render_widget
    def all_plot():
        # Create a past results plot
        df_past = df_played.copy()

        # Exclude records from df_plot where the predicted winner is not consistent with the predicted score difference
        # For example, if the predicted winner is the home team but the predicted score difference is negative (indicating the away team is favored), remove that record
        df_past = df_past[~(
            ((df_past["Predicted.Winner"] == df_past["Home"]) & (df_past["Predicted.Score.Diff"] < 0)) |
            ((df_past["Predicted.Winner"] == df_past["Away"]) & (df_past["Predicted.Score.Diff"] > 0))
        )]

        df_past["Predicted.Score.Diff"] = df_past.apply(
            lambda row: -row["Predicted.Score.Diff"] if row["Predicted.Score.Diff"] < 0
            else row["Predicted.Score.Diff"], axis=1)

        df_past["Model.Pick"] = df_past.apply(lambda row: "Correct" if row["Actual.Winner"] == row["Predicted.Winner"] else "Incorrect", axis=1)
        
        df_past['Opponent'] = df_past.apply(lambda row: row['Home'] if row['Predicted.Winner'] == row['Away'] else row['Away'], axis = 1)

        df_past = df_past[df_past["Model.Pick"].notna()]
        fig_all = px.scatter(
            df_past, 
            x="Predicted.Score.Diff", 
            y="Win.Probability", 
            color="Model.Pick", 
            opacity=0.5, 
            hover_data=["Date.Game",
                        "Predicted.Winner",
                        "Opponent",
                        "Win.Probability",
                        "Predicted.Score.Diff",
                        "Model.Pick"]
        )

        prob_thresholds = [0.67, 0.95, 1]
        colors = [
            "rgba(200,0,0,0.3)",    # red (low confidence)
            "rgba(200,200,0,0.3)",  # yellow (medium confidence)
            "rgba(0,200,0,0.3)"     # green (high confidence)
        ]

        # Add circular bands for each probability range
        for i, color in enumerate(colors):
            fig_all.add_shape(
                type="circle",
                xref="x", yref="y",
                x0=-(i+1) * rmse.item(),
                y0=-prob_thresholds[i] + 0.5,       # lower bound of probability band
                x1=(i+1) * rmse.item(),
                y1=prob_thresholds[i],
                fillcolor=color,
                opacity=0.4,
                line_width=0,
                layer="below"
            )

        fig_all.update_layout(
            title="Game Winner Prediction Accuracy with Circular Error Bands", 
            xaxis_title="Predicted Point Differential", 
            yaxis_title="Predicted Win Probability",
            xaxis_range=[0, 40],
            yaxis_range=[0.5, 1.1]
        )
        fig_all.update_layout(legend=dict(font=dict(size=9)))
        legend_title = "Model.Pick"
        wrapped_title = "<br>".join(legend_title.split(" "))
        fig_all.update_layout(legend=dict(title=dict(text=wrapped_title)))

        return fig_all




    @output
    @render.data_frame
    def date_table():
        return render.DataGrid(df_date[["Date.Game","Home","Away","Predicted.Winner","Predicted.Winner.Ranking.Position","Predicted.Score.Diff","Win.Probability"]],
                                styles={"searching": True, "ordering": True, "pageLength": 10, "filters": True}
                                )

    @output
    @render.data_frame
    def past_table():
        target_dates = [(datetime.now(pytz.timezone('US/Central')) - timedelta(days=i)).strftime('%Y-%m-%d') for i in [1,2,3]]
        recent = df_master[df_master["Date.Game"].isin(target_dates)]
        return render.DataGrid(recent[["Date.Game","Home","Away","Predicted.Winner","Actual.Winner","Predicted.Score.Diff","Actual.Score.Diff"]],
                                styles={"searching": True, "ordering": True, "pageLength": 10, "filters": True}
                                )

# --- App ---
app = App(app_ui, server)