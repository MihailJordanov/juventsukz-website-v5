from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash 
import re
from models import db, User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        # Проверка за съществуването на потребителя и паролата
        if user and user.check_password(password):
            session['user_id'] = user.id
            #flash('Успешен вход!', 'success')
            return redirect(url_for('home'))
        else:
            flash('The password or email that you\'ve entered is incorrect.', 'danger')
    return render_template('login.html')


@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if len(first_name) < 3 or not re.match("^[A-ZА-Я][a-zа-я]+$", first_name):
            flash('First name must be at least 3 characters long, contain only letters, and start with a capital letter.')
            return redirect(url_for('signup'))

        if len(last_name) < 3 or not re.match("^[A-ZА-Я][a-zа-я]+$", last_name):
            flash('Last name must be at least 3 characters long, contain only letters, and start with a capital letter.')
            return redirect(url_for('signup'))
        
        # Валидация на паролата: поне 3 символа
        if len(password) < 3:
            flash('Passwords do not match.')
            return redirect(url_for('signup'))

        
        # Проверка дали паролите съвпадат
        if password != confirm_password:
            flash('Passwords do not match.')
            return redirect(url_for('signup'))

        # Проверка дали съществува потребител с този имейл
        existing_user  = User.query.filter_by(email=email).first()
        if existing_user :
            flash('Email alreay exist.')
            return redirect(url_for('signup'))


        new_user = User(first_name=first_name, last_name=last_name,title="",number=0, email=email, password=generate_password_hash(password, method='pbkdf2:sha256'), type = 0, max_goals = 0,
                        max_goals_in_one_match = 0, max_assists = 0, max_assists_in_one_match = 0, played_matches = 0, win_matches = 0, draw_matches = 0,
                        max_passes = 0, max_passes_in_one_match = 0, max_hat_tricks = 0, max_ball_game_score = 0, max_keeper_game_score=0)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('signup.html')


@auth_bp.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))
