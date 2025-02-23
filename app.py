from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from random import randint, choice
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'users.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    total_questions = db.Column(db.Integer, default=0)
    correct_answers = db.Column(db.Integer, default=0)
    incorrect_answers = db.Column(db.Integer, default=0)


def init_db():
    with app.app_context():
        db.create_all()
        print(f"Database created at: {os.path.join(basedir, 'users.db')}")


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
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


@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    user = current_user
    feedback = None

    if request.method == 'GET':
        num1, num2, operation, result = generate_problem()
        user.total_questions += 1
        db.session.commit()

    elif request.method == 'POST':
        if 'check_answer' in request.form:
            num1 = float(request.form['num1'])
            num2 = float(request.form['num2'])
            operation = request.form['operation']
            result = float(request.form['result'])
            user_answer = request.form['answer']
            try:
                user_answer = float(user_answer)
                if abs(user_answer - result) < 0.01:
                    feedback = "Correct!"
                    user.correct_answers += 1
                else:
                    feedback = "Wrong!"
                    user.incorrect_answers += 1
                db.session.commit()
            except ValueError:
                feedback = "Please enter a valid number"
            num1, num2, operation, result = generate_problem()

    return render_template('dashboard.html',
                           username=user.username,
                           num1=num1,
                           num2=num2,
                           operation=operation,
                           result=result,
                           feedback=feedback,
                           total_questions=user.total_questions,
                           correct_answers=user.correct_answers,
                           incorrect_answers=user.incorrect_answers)


@app.route('/new_problem', methods=['GET'])
@login_required
def new_problem():
    user = current_user
    num1, num2, operation, result = generate_problem()
    user.total_questions += 1
    db.session.commit()
    return jsonify({
        'num1': num1,
        'num2': num2,
        'operation': operation,
        'result': result,
        'total_questions': user.total_questions
    })


@app.route('/rating')
@login_required
def rating():
    # Fetch all users and calculate their ratings
    users = User.query.all()
    ratings = []
    for user in users:
        if user.total_questions > 0:  # Only include users with at least one question
            rating_score = (user.correct_answers * 100) - (user.incorrect_answers * 10)
            accuracy = (user.correct_answers / (user.total_questions + user.incorrect_answers)) * 100 if (
                                                                                                                     user.correct_answers + user.incorrect_answers) > 0 else 0
            ratings.append({
                'username': user.username,
                'correct_answers': user.correct_answers,
                'total_questions': user.total_questions,
                'accuracy': round(accuracy, 2),
                'rating_score': rating_score
            })

    # Sort by rating score descending
    ratings.sort(key=lambda x: x['rating_score'], reverse=True)

    return render_template('rating.html', ratings=ratings)


def generate_problem():
    num1 = round(randint(1, 100), 2)
    num2 = round(randint(1, 100), 2)
    operations = ['+', '-']
    operation = choice(operations)
    if operation == '+':
        result = num1 + num2
    elif operation == '-':
        result = num1 - num2
    return num1, num2, operation, round(result, 2)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


if __name__ == '__main__':
    init_db()
    app.run(debug=True, use_reloader=False)