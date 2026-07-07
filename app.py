from flask import Flask, render_template, request, make_response, session
from emotion_model import detect_emotion
from datetime import datetime
from dotenv import load_dotenv
import os
import re
from flask_sqlalchemy import SQLAlchemy
import uuid  # For generating unique guest IDs

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')  # Required for sessions

# PostgreSQL connection string (apna username, password, db name daalna)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://...')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# ---------- Models ----------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(200), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    moods = db.relationship('Mood', backref='user', lazy=True)

class Mood(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500), nullable=False)
    mood = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# ---------- Helper Functions ----------
def clean_mood(mood):
    return re.sub(r'[^\w\s]', '', mood).strip()

def get_or_create_user():
    """Check if session has user_id, else create new guest user."""
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            return user
    # Create new guest user
    new_user = User(session_id=str(uuid.uuid4()))  # Unique per session
    db.session.add(new_user)
    db.session.commit()
    session['user_id'] = new_user.id
    return new_user

def get_motivation_and_color(mood):
    # (Your existing logic unchanged)
    if "Very Happy" in mood:
        return ("#a8ff78", "#e8ffd1", "Keep shining! 😎")
    elif "Happy" in mood:
        return ("#d4fc79", "#f0ffc8", "Smile more today! 😊")
    elif "Neutral" in mood:
        return ("#fefcea", "#fffdf0", "Stay steady. ✌")
    elif "Sad" in mood:
        return ("#fbc2eb", "#ffe6f7", "Better days are coming. 🌈")
    else:
        return ("#f5576c", "#ffd1d9", "It's okay to feel low. ❤")

# ---------- Routes ----------
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        text = request.form.get("journal", "").strip()
        if not text:
            error = "Please enter your journal entry."
            return render_template("index.html", error=error)
        mood = detect_emotion(text)
        color, bg_color, message = get_motivation_and_color(mood)
        
        # Get the current user (create if new)
        user = get_or_create_user()
        
        # Save mood to PostgreSQL (instead of CSV)
        new_mood = Mood(text=text, mood=mood, user_id=user.id)
        db.session.add(new_mood)
        db.session.commit()
        print(f"[SAVED] {mood} -> {text} (User: {user.id})")
        
        return render_template("result.html", mood=mood, text=text, color=color, bg_color=bg_color, message=message)
    return render_template("index.html")

@app.route("/history")
def history():
    # Only show moods of the current user
    if 'user_id' not in session:
        # No user yet, return empty history
        return render_template("history.html", dates=[], moods=[])
    
    user = User.query.get(session['user_id'])
    if not user:
        return render_template("history.html", dates=[], moods=[])
    
    # Fetch all moods for this user, ordered by timestamp
    user_moods = Mood.query.filter_by(user_id=user.id).order_by(Mood.timestamp.desc()).all()
    dates = [m.timestamp.strftime("%Y-%m-%d %H:%M:%S") for m in user_moods]
    moods = [m.mood for m in user_moods]
    
    response = make_response(render_template("history.html", dates=dates, moods=moods))
    response.headers["Cache-Control"] = "no-store"
    return response

if __name__ == "__main__":
     with app.app_context():
        db.create_all()
     app.run(debug=True)