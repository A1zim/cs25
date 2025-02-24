from flask import Flask, request, render_template, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from random import randint
from collections import defaultdict
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'users.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
CORS(app)
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

def init_db():
    with app.app_context():
        db.drop_all()
        db.create_all()
        print(f"Database created at: {app.config['SQLALCHEMY_DATABASE_URI']}")

user_stats = defaultdict(lambda: {
    "correct": 0,
    "attempt": 0,
    "question": "",
    "incorrect": 0,
    "question_count": 0
})

ops = "+-"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/")
def entrance():
    return render_template("home.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('math'))
        else:
            flash('Invalid username or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
        else:
            hashed_password = generate_password_hash(password)
            new_user = User(username=username, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! Please login.')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/math')
@login_required
def math():
    return render_template('math.html')

@app.route("/get_question")
@login_required
def generate_question():
    try:
        stats = user_stats[current_user.username]
        first = randint(0, 100)
        second = randint(0, 100)
        first, second = max(first, second), min(first, second)
        op = ops[randint(0, 1)]
        stats["question"] = f'{first}{op}{second}'
        stats["question_count"] += 1
        return jsonify({"question": stats["question"]})
    except:
        return "ERROR IN THE SERVER"

@app.route('/check_result')
@login_required
def check_result():
    try:
        stats = user_stats[current_user.username]
        answer = int(request.args.get("answer"))
        stats["attempt"] += 1
        correct = (answer == eval(stats["question"]))
        if correct:
            stats["correct"] += 1
            first = randint(0, 100)
            second = randint(0, 100)
            first, second = max(first, second), min(first, second)
            op = ops[randint(0, 1)]
            stats["question"] = f'{first}{op}{second}'
            stats["question_count"] += 1
        else:
            stats["incorrect"] += 1
        return jsonify({"stats": stats, "correct": correct})
    except:
        return "error in the server"

@app.route('/rating')
@login_required
def rating():
    ratings = []
    for username, stats in user_stats.items():
        if stats["question_count"] > 0:
            rating_score = (stats["correct"] * 100) - (stats["incorrect"] * 10)
            accuracy = (stats["correct"] / (stats["incorrect"]+stats["attempt"])) * 100 if stats["attempt"] > 0 else 0
            ratings.append({
                "username": username,
                "correct_answers": stats["correct"],
                "total_questions": stats["question_count"],
                "accuracy": round(accuracy, 2),
                "rating_score": rating_score
            })
    ratings.sort(key=lambda x: x['rating_score'], reverse=True)
    return render_template('rating.html', ratings=ratings)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('entrance'))

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=8080)