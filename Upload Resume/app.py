import os
import sqlite3
import json
from flask import Flask, render_template, request, redirect, url_for, session, flash
from process_pdf import process_pdf  # Import the updated process_pdf function

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Secret key for session management
UPLOAD_FOLDER = 'uploads/'
RESPONSE_FOLDER = 'candidates_response/'  # New folder for storing the JSON response
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

DATABASE = 'database.db'

def get_db():
    """Connect to the SQLite database."""
    conn = sqlite3.connect(DATABASE)
    return conn

def check_user(email, password=None):
    """Check if the user exists. If password is provided, also check if the password matches."""
    conn = get_db()
    cursor = conn.cursor()
    if password:
        cursor.execute("SELECT * FROM users WHERE email = ? AND password = ?", (email, password))
    else:
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()
    return user

def add_user(email, password):
    """Add a new user to the database."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (email, password, submitted) VALUES (?, ?, 0)", (email, password))
    conn.commit()
    conn.close()

def update_submission_status(email):
    """Mark the user as having submitted an application."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET submitted = 1 WHERE email = ?", (email,))
    conn.commit()
    conn.close()

# Check if the database exists; if not, create it
if not os.path.exists(DATABASE):
    print("Database does not exist. Creating database...")
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        submitted INTEGER DEFAULT 0
    )
    ''')
    conn.commit()
    conn.close()

@app.route("/", methods=["GET", "POST"])
def login():
    """Login page for users."""
    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']
        
        # Check user credentials
        user = check_user(email, password)
        if user:
            session['user'] = user[1]  # Store the email in the session
            if user[3] == 1:  # If the user has already submitted
                return render_template("submitted.html", email=email)  # Pass email to submitted page
            else:
                return redirect(url_for("upload_resume"))  # Redirect to resume upload page
        else:
            flash("Invalid credentials. Please try again.", "error")
            return redirect(url_for('login'))  # Show login page again with error message

    return render_template("login.html")  # Render the login page

@app.route("/create_account", methods=["GET", "POST"])
def create_account():
    """Create account page for new users."""
    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']

        # Check if the user already exists
        existing_user = check_user(email)
        if existing_user:
            if existing_user[3] == 1:  # If the user has already submitted
                return render_template("submitted.html", email=email)  # Pass email to submitted page

        # Add the user to the database
        add_user(email, password)
        session['user'] = email  # Automatically log in the new user

        # Redirect to the PDF upload page after account creation
        return redirect(url_for('upload_resume'))

    return render_template("create_account.html")

@app.route("/upload_resume", methods=["GET", "POST"])
def upload_resume():
    """Page for uploading the resume, displaying the email at the top."""
    if 'user' not in session:
        return redirect(url_for('login'))  # Redirect to login if not logged in
    
    email = session['user']

    if request.method == "POST":
        file = request.files['resume']
        if file.filename == '':
            return "Please select a file."
        
        if file and file.filename.endswith('.pdf'):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)

            # Process the PDF and get answers
            result = process_pdf(file_path)
            
            # Save result as JSON in the 'candidates_response' folder
            if not os.path.exists(RESPONSE_FOLDER):
                os.makedirs(RESPONSE_FOLDER)

            json_filename = f"{email}.json"
            json_path = os.path.join(RESPONSE_FOLDER, json_filename)

            with open(json_path, "w") as json_file:
                json.dump(result, json_file, indent=4)
            
            # Mark the user as having submitted
            update_submission_status(email)
            
            # Redirect to show_answers page
            return redirect(url_for('show_answers'))
    
    return render_template("upload_resume.html", email=email)

@app.route("/show_answers", methods=["GET", "POST"])
def show_answers():
    """Display the answers extracted from the resume."""
    email = session.get('user')
    json_path = os.path.join(RESPONSE_FOLDER, f"{email}.json")
    
    # Load the JSON data from the file
    with open(json_path, "r") as json_file:
        data = json.load(json_file)
    
    if request.method == "POST":
        # Handle form submission logic here
        return "Form submitted successfully!"
    
    return render_template("show_answers.html", data=data)

@app.route('/submit', methods=['POST'])
def submit():
    """Handle the final form submission and save it as a JSON."""
    email = request.form.get('email')
    personal_info = {
        'name': request.form.get('name'),
        'phone': request.form.get('phone')
    }
    
    # Parse education, work experience, projects, and skills data
    education = [{'degree': d, 'institution': i, 'start_date': s, 'end_date': e} 
                 for d, i, s, e in zip(request.form.getlist('degree'), 
                                       request.form.getlist('institution'), 
                                       request.form.getlist('education_start_date'), 
                                       request.form.getlist('education_end_date'))]
    
    work_experience = [{'role': r, 'company': c, 'start_date': s, 'end_date': e, 'responsibilities': res} 
                       for r, c, s, e, res in zip(request.form.getlist('role'), 
                                                  request.form.getlist('company'), 
                                                  request.form.getlist('work_start_date'), 
                                                  request.form.getlist('work_end_date'), 
                                                  request.form.getlist('responsibilities'))]
    
    projects = [{'name': p, 'link': l} 
                for p, l in zip(request.form.getlist('project_name'), 
                                request.form.getlist('github_link'))]
    
    skills = request.form.get('skills')

    # Save the form data as JSON
    response_data = {
        'personal_info': personal_info,
        'education': education,
        'work_experience': work_experience,
        'projects': projects,
        'skills': skills
    }

    json_filename = f"{email}.json"
    json_path = os.path.join(RESPONSE_FOLDER, json_filename)

    with open(json_path, 'w') as json_file:
        json.dump(response_data, json_file, indent=4)

    return render_template('submitted.html', email=email)

if __name__ == "__main__":
    # Create necessary folders if they don't exist
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    if not os.path.exists(RESPONSE_FOLDER):
        os.makedirs(RESPONSE_FOLDER)
    
    app.run(debug=True)
