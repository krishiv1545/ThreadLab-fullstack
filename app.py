from flask import Flask, render_template, request, redirect, url_for, session, flash
from models import db, User
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from datetime import datetime, UTC
import os
from flask_session import Session
import redis


load_dotenv()

app = Flask(__name__)
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_REDIS'] = redis.Redis(host='localhost', port=6379)
Session(app)

app.secret_key = os.getenv('SECRET_KEY') 
groq_api_key = os.getenv('GROQ_API_KEY')
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
    role = None
    if 'user_id' in session:
        role = session['role']
    return render_template('index.html', role=role)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)
        role = request.form['role']

        try:
            new_user = User(email=email, username=username, role=role,
                            password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            flash('Signup successful! Please log in.', 'success')
            # Redirect to home page with login modal parameter
            return redirect(url_for('home', show_login='true'))
        except Exception as e:
            flash('Username or email already exists.', 'error')
            print(e)
            # Redirect to home page with signup modal parameter
            return redirect(url_for('home', show_signup='true'))
    # If GET request, redirect to home with signup modal parameter
    return redirect(url_for('home', show_signup='true'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role

            if user.role == 'seller':
                matrix = []
                for i in range(15):
                    row = []
                    for j in range(15):
                        row.append("#ffffff00")
                    matrix.append(row)
                
                session['matrix'] = matrix

                return redirect(url_for('seller_dashboard'))
            else:
                return redirect(url_for('home'))

        flash('Invalid username or password.', 'error')
        # Redirect to home page with login modal parameter
        return redirect(url_for('home', show_login='true'))
    # If GET request, redirect to home with login modal parameter
    return redirect(url_for('home', show_login='true'))


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('role', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('home'))


@app.route('/seller_dashboard')
def seller_dashboard():
    if 'user_id' not in session:
        flash('Please log in.', 'error')
        return redirect(url_for('home', show_login='true'))
    if session['role'] != 'seller':
        flash('You are not a seller.', 'error')
        return redirect(url_for('home'))
    role = session['role']
    return render_template('seller_dashboard.html', role=role)

@app.route('/generate', methods=['GET', 'POST'])
def generate():
    if 'user_id' not in session:
        flash('Please log in.', 'error')
        return redirect(url_for('login'))
    if session['role'] != 'seller':
        flash('You are not a seller.', 'error')
        return redirect(url_for('home'))
    
    return render_template('generate.html', role=session['role'], matrix=session['matrix'])


@app.route('/clear-matrix', methods=['GET', 'POST'])
def clear_matrix():
    matrix = []
    for i in range(15):
        row = []
        for j in range(15):
            row.append("#ffffff00")
        matrix.append(row)
    
    session['matrix'] = matrix

    return redirect(url_for('generate', matrix=session['matrix']))



@app.route('/generate-with-groq', methods=['GET', 'POST'])
def generate_with_groq():
    if 'user_id' not in session:
        flash('Please log in.', 'error')
        return redirect(url_for('login'))
    if session['role'] != 'seller':
        flash('You are not a seller.', 'error')
        return redirect(url_for('home'))

    matrix = session['matrix']
    matrix[5][5] = "#ff0000"
    session['matrix'] = matrix
    
    return redirect(url_for('generate', role=session['role'], matrix=session['matrix']))


if __name__ == '__main__':
    app.run(debug=True)
