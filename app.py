from flask import Flask, render_template, request, redirect, url_for, session, flash
from models import db, User
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from datetime import datetime, UTC
import os
from flask_session import Session
import redis
import openai
import json
from groq import Groq
import regex as re
import ast
import requests
import io
from PIL import Image
import base64
import numpy as np



load_dotenv()

app = Flask(__name__)
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_REDIS'] = redis.Redis(host='localhost', port=6379)
Session(app)

app.secret_key = os.getenv('SECRET_KEY') 
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///project_db.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db.init_app(app)

with app.app_context():
    db.create_all()

client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
    timeout=120.0
)


def generate_image_from_prompt(prompt):
    api_key = os.environ.get("STABILITY_API_KEY")
    url = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    payload = {
        "text_prompts": [{"text": f"{prompt}, pixel art style, 8-bit, simple colors, square format"}],
        "cfg_scale": 7,
        "height": 1024,
        "width": 1024,
        "samples": 1,
        "steps": 30,
    }
    
    response = requests.post(url, headers=headers, json=payload)
    print(f"Response status: {response.status_code}")
    print(f"Response body: {response.text}")
    if response.status_code == 200:
        # Get image data from response
        image_data = base64.b64decode(response.json()["artifacts"][0]["base64"])
        return Image.open(io.BytesIO(image_data))
    else:
        raise Exception(f"Image generation failed: {response.text}")
        


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
                for i in range(30):
                    row = []
                    for j in range(30):
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
    for i in range(30):
        row = []
        for j in range(30):
            row.append("#ffffff00")
        matrix.append(row)
    
    session['matrix'] = matrix

    return redirect(url_for('generate', matrix=session['matrix']))



@app.route('/generate-with-groq', methods=['GET', 'POST'])
@app.route('/generate-with-groq', methods=['GET', 'POST'])
def generate_with_groq():
    if 'user_id' not in session:
        flash('Please log in.', 'error')
        return redirect(url_for('login'))
    if session['role'] != 'seller':
        flash('You are not a seller.', 'error')
        return redirect(url_for('home'))
    
    prompt = "A beautiful car"
    if request.method == 'POST':
        prompt = request.form['prompt']

    image = None
    try:
        print("tried")
        image = generate_image_from_prompt(prompt)
        img_path = os.path.join(app.config['UPLOAD_FOLDER'], f"original_{session['user_id']}.png")
        image.save(img_path)
    
    except Exception as e:
        flash(f'Error generating pixel art: {str(e)}', 'error')
        if 'matrix' not in session:
            session['matrix'] = [["#FFFFFF00"] * 30 for _ in range(30)]
        return redirect(url_for('generate'))

    if image:
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG")
        base64_image = base64.b64encode(buffered.getvalue()).decode('utf-8')

        print("Hello")
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a pixel art generator. When given any prompt, respond ONLY with a JSON object containing a 30x30 matrix of hexadecimal color codes. The JSON should use the key 'pixelArt' (exactly as written) for the matrix."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"This image was generated based on the prompt: '{prompt}'. Please suggest color adjustments to make it better as pixel art."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            model="meta-llama/llama-4-scout-17b-16e-instruct",  # Use a model that supports vision
            response_format={"type": "json_object"}
        )

        output = chat_completion.choices[0].message.content
        data = json.loads(output)
        data = data["pixelArt"]
        print(data)
        print(type(data))

        session['matrix'] = data

    return redirect(url_for('generate'))



if __name__ == '__main__':
    app.run(debug=True)
