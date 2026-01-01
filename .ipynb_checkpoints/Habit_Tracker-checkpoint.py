from dash import Dash, html, dcc, Input, Output, ALL, ctx
import calendar
import sqlite3
import os

app = Dash(__name__)
server = app.server
# -----------------------
# Habits and options
# -----------------------
HABITS = [
    "Gym Workout 💪", 
    "Read 5 pages 📚", 
    "Meditate 10 mins 🧘",
    "Apply Skin Care (Morning) 🧴", 
    "Drink 2.5+ L Water 💧", 
    "Walk 10k steps 🚶‍♂️",
    "Personal Growth 1 hour",
    "Eat Healthy Food 🥗",
    "Apply Skin Care (Night) 🧴",
    "Sleep Early 7 Hours 😴",
]

YEARS = list(range(2026, 2031))
MONTHS = [{"label": calendar.month_name[i], "value": i} for i in range(1, 13)]

DB_FILE = "habit_tracker.db"

# -----------------------
# Initialize DB
# -----------------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Table: habit_data (habit TEXT, year INT, month INT, day INT, completed INT)
    c.execute('''
        CREATE TABLE IF NOT EXISTS habit_data (
            habit TEXT,
            year INTEGER,
            month INTEGER,
            day INTEGER,
            completed INTEGER,
            PRIMARY KEY (habit, year, month, day)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# -----------------------
# Save progress to DB
# -----------------------
def save_habit(habit, year, month, day, completed):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        INSERT INTO habit_data (habit, year, month, day, completed)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(habit, year, month, day) DO UPDATE SET completed=excluded.completed
    ''', (habit, year, month, day, completed))
    conn.commit()
    conn.close()

# -----------------------
# Load progress from DB
# -----------------------
def load_habit_data(year, month):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT habit, day, completed FROM habit_data WHERE year=? AND month=?', (year, month))
    rows = c.fetchall()
    conn.close()
    # Convert to dictionary for quick lookup
    habit_dict = {(habit, day): completed for habit, day, completed in rows}
    return habit_dict

# -----------------------
# App Layout
# -----------------------
app.layout = html.Div([
    html.H2("📅 Monthly Habit Tracker", style={"textAlign": "center", "marginBottom": "20px"}),

    html.Div(style={
        "display": "flex", 
        "flexWrap": "wrap", 
        "gap": "10px", 
        "justifyContent": "center",
        "marginBottom": "20px"
    }, children=[
        dcc.Dropdown(
            id="year-dropdown", 
            options=[{"label": y, "value": y} for y in YEARS], 
            value=2026, 
            clearable=False,
            style={"minWidth": "150px", "borderRadius": "8px"}
        ),
        dcc.Dropdown(
            id="month-dropdown", 
            options=MONTHS, 
            value=1, 
            clearable=False,
            style={"minWidth": "150px", "borderRadius": "8px"}
        ),
    ]),

    html.Div(
        id="habit-grid-container",
        style={
            "overflowX": "auto",
            "border": "1px solid #ccc",
            "borderRadius": "8px",
            "padding": "10px",
            "margin": "auto",
            "maxWidth": "100%",
        },
        children=[
            html.Div(id="habit-grid")
        ]
    ),

    html.Br(),
    html.Div(id="completion-output", style={"fontSize": "18px", "fontWeight": "bold", "textAlign": "center"}),

    html.Br(),
    html.Div(id="per-habit-progress", style={"maxWidth": "900px", "margin": "auto"})
])

# -----------------------
# Build table dynamically
# -----------------------
@app.callback(
    Output("habit-grid", "children"),
    Input("year-dropdown", "value"),
    Input("month-dropdown", "value"),
)
def update_grid(year, month):
    days_in_month = calendar.monthrange(year, month)[1]
    habit_data = load_habit_data(year, month)

    # Table header
    header = [html.Th("Habit", style={
        "position": "sticky", "left": 0, "backgroundColor": "#f9f9f9", 
        "zIndex": 1, "minWidth": "200px", "whiteSpace": "nowrap", "padding": "8px",
        "textAlign": "left", "borderBottom": "2px solid #ccc"
    })]
    header += [html.Th(str(day), style={"minWidth": "40px", "padding": "8px"}) for day in range(1, days_in_month + 1)]
    table_rows = [html.Tr(header)]

    # Table body
    for idx, habit in enumerate(HABITS):
        row_color = "#f7f7f7" if idx % 2 == 0 else "white"
        row = [html.Td(habit, style={
            "position": "sticky", "left": 0, "backgroundColor": row_color,
            "fontWeight": "bold", "whiteSpace": "nowrap", "padding": "8px", "borderBottom": "1px solid #ddd"
        })]
        for day in range(1, days_in_month + 1):
            checked = [1] if habit_data.get((habit, day), 0) == 1 else []
            row.append(html.Td(
                dcc.Checklist(
                    options=[{"label": "", "value": 1}],
                    value=checked,
                    id={"type": "habit-checkbox", "habit": habit, "day": day},
                    inputStyle={"margin": "auto"}
                ),
                style={
                    "textAlign": "center", 
                    "backgroundColor": row_color, 
                    "padding": "5px", 
                    "borderBottom": "1px solid #ddd"
                }
            ))
        table_rows.append(html.Tr(row))

    table_style = {
        "borderCollapse": "collapse",
        "border": "1px solid #ccc",
        "minWidth": "700px",
        "width": "100%",
    }

    return html.Table(table_rows, style=table_style)

# -----------------------
# Save checkbox changes and update progress
# -----------------------
@app.callback(
    Output("completion-output", "children"),
    Output("per-habit-progress", "children"),
    Input({"type": "habit-checkbox", "habit": ALL, "day": ALL}, "value"),
    Input("year-dropdown", "value"),
    Input("month-dropdown", "value"),
)
def update_completion(values, year, month):
    days_in_month = calendar.monthrange(year, month)[1]

    # Save to DB
    start = 0
    for habit in HABITS:
        end = start + days_in_month
        habit_values = values[start:end]
        for day_index, v in enumerate(habit_values, start=1):
            save_habit(habit, year, month, day_index, 1 if v else 0)
        start = end

    # Overall completion
    total_boxes = len(HABITS) * days_in_month
    completed = sum([1 for v in values if v])
    overall_percent = completed / total_boxes * 100 if total_boxes > 0 else 0
    overall_text = f"Monthly Completion: {completed}/{total_boxes} habits ({overall_percent:.0f}%) ✅"

    # Per-habit progress bars
    per_habit_children = []
    start = 0
    for habit in HABITS:
        end = start + days_in_month
        habit_values = values[start:end]
        habit_completed = sum([1 for v in habit_values if v])
        habit_percent = habit_completed / days_in_month * 100 if days_in_month > 0 else 0

        per_habit_children.append(
            html.Div([
                html.Div(f"{habit}: {habit_completed}/{days_in_month} ({habit_percent:.0f}%)", 
                         style={"marginBottom": "3px", "fontWeight": "bold"}),
                html.Div(style={
                    "backgroundColor": "#eee", 
                    "borderRadius": "8px", 
                    "height": "12px", 
                    "width": "100%",
                    "marginBottom": "8px",
                    "overflow": "hidden"
                }, children=[
                    html.Div(style={
                        "width": f"{habit_percent}%",
                        "backgroundColor": "#4CAF50",
                        "height": "100%",
                        "borderRadius": "8px"
                    })
                ])
            ])
        )

        start = end

    return overall_text, per_habit_children

# -----------------------
if __name__ == "__main__":
    app.run(host = "0.0.0.0",port = 80, debug=True)
