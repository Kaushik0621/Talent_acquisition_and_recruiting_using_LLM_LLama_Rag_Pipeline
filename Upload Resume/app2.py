from flask import Flask, render_template
import sqlite3

app = Flask(__name__)

def read_database(db_path):
    # Connect to the SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Query to list all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    # Assuming you want to query the first table found
    if tables:
        table_name = tables[0][0]
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        
        # Fetch column names
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [column[1] for column in cursor.fetchall()]
    else:
        rows = []
        columns = []

    conn.close()

    return columns, rows

@app.route('/')
def show_database():
    db_path = 'database_old.db'  # Path to your SQLite database
    columns, rows = read_database(db_path)
    
    return render_template('show_database.html', columns=columns, rows=rows)

if __name__ == "__main__":
    app.run(debug=True)
