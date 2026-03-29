from flask_cors import CORS
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import json
import os

app = Flask(__name__)
CORS(app)

# Sets up the SQLite database in your ironlog folder
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'ironlog.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    
    # Store everything as JSON text
    workouts_json = db.Column(db.Text, default="[]")
    templates_json = db.Column(db.Text, default="[]")
    exercises_json = db.Column(db.Text, default="null")
    active_workout_json = db.Column(db.Text, default="null")

# Create tables and auto-upgrade older databases
with app.app_context():
    db.create_all()
    
    # This safely attempts to add the new columns to your existing database.
    # If they already exist, it just silently ignores the error.
    try:
        db.session.execute(db.text('ALTER TABLE user ADD COLUMN templates_json TEXT DEFAULT "[]"'))
        db.session.execute(db.text('ALTER TABLE user ADD COLUMN exercises_json TEXT DEFAULT "null"'))
        db.session.execute(db.text('ALTER TABLE user ADD COLUMN active_workout_json TEXT DEFAULT "null"'))
        db.session.commit()
    except Exception:
        db.session.rollback() # Columns already exist, move on!

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
        # Parse the JSON back into Python dictionaries to send to the frontend
        workouts = json.loads(user.workouts_json) if user.workouts_json else []
        templates = json.loads(user.templates_json) if user.templates_json else []
        exercises = json.loads(user.exercises_json) if user.exercises_json != "null" else None
        active_workout = json.loads(user.active_workout_json) if user.active_workout_json != "null" else None

        return jsonify({
            'message': 'Logged in', 
            'user_id': user.id, 
            'workouts': workouts,
            'templates': templates,
            'exercises': exercises,
            'activeWorkout': active_workout
        })
        
    return jsonify({'error': 'Invalid credentials'}), 401

# Unified endpoint to save ALL user data at once
@app.route('/sync_data', methods=['POST'])
def sync_data():
    data = request.json
    user = User.query.get(data['user_id'])

    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Save everything the frontend sends us
    if 'workouts' in data:
        user.workouts_json = json.dumps(data['workouts'])
    if 'templates' in data:
        user.templates_json = json.dumps(data['templates'])
    if 'exercises' in data:
        user.exercises_json = json.dumps(data['exercises'])
    if 'activeWorkout' in data:
        user.active_workout_json = json.dumps(data['activeWorkout'])

    db.session.commit()
    return jsonify({'message': 'All data safely synced!'})

if __name__ == '__main__':
    app.run(debug=True)