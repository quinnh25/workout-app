from flask_cors import CORS  # <--- LINE 1
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
import json
import os

app = Flask(__name__)
CORS(app)  # <--- LINE 2 (Right under app = Flask)

# Sets up the SQLite database in your ironlog folder
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'ironlog.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    workouts_json = db.Column(db.Text, default="[]")

with app.app_context():
    db.create_all()

# --- SERVE THE FRONTEND ---
@app.route('/')
def home():
    return render_template('index.html')

# --- API ENDPOINTS ---
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'User already exists'}), 400

    hashed_pw = generate_password_hash(data['password'])
    new_user = User(username=data['username'], password_hash=hashed_pw)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'User created!'})

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(username=data['username']).first()

    if user and check_password_hash(user.password_hash, data['password']):
        return jsonify({'message': 'Logged in', 'user_id': user.id, 'workouts': json.loads(user.workouts_json)})
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/sync_workouts', methods=['POST'])
def sync_workouts():
    data = request.json
    user = User.query.get(data['user_id'])

    if not user:
        return jsonify({'error': 'User not found'}), 404

    user.workouts_json = json.dumps(data['workouts'])
    db.session.commit()
    return jsonify({'message': 'Workouts saved!'})