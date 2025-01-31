import re
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
from models import db, User, Leaderboard
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from datetime import datetime, UTC
import os


load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///project_db.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db.init_app(app)

with app.app_context():
    db.create_all()


@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('signup.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)
        resume = request.files['resume']

        if resume and resume.filename:
            resume_path = os.path.join(
                app.config['UPLOAD_FOLDER'], resume.filename)
            resume.save(resume_path)

            try:
                new_user = User(email=email, username=username,
                                password=hashed_password, resume_path=resume_path)
                db.session.add(new_user)
                db.session.commit()
                flash('Signup successful! Please log in.', 'success')
                return redirect(url_for('home'))
            except Exception as e:
                flash('Username or email already exists.', 'error')
                print(e)
        else:
            flash('Please upload your resume.', 'error')
    return render_template('signup.html')


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please log in.', 'error')
        return redirect(url_for('home'))
    return render_template('dashboard.html')
