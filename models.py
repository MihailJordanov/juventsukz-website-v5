from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(100))
    number = db.Column(db.Integer)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    type = db.Column(db.Integer)
    max_goals = db.Column(db.Integer)
    max_goals_in_one_match = db.Column(db.Integer)
    max_assists = db.Column(db.Integer)
    max_assists_in_one_match  = db.Column(db.Integer)
    played_matches = db.Column(db.Integer)
    win_matches = db.Column(db.Integer)
    draw_matches = db.Column(db.Integer)
    max_passes = db.Column(db.Integer)
    max_passes_in_one_match = db.Column(db.Integer)
    max_hat_tricks = db.Column(db.Integer)
    max_ball_game_score = db.Column(db.Integer)


    # Метод за задаване на парола
    def set_password(self, password):
        self.password = generate_password_hash(password)

    # Метод за проверка на парола
    def check_password(self, password):
        return check_password_hash(self.password, password)

class Match(db.Model):
    __tablename__ = 'matches'
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50))
    team_one = db.Column(db.String(50))
    team_two = db.Column(db.String(50))
    team_one_result = db.Column(db.Integer)
    team_two_result = db.Column(db.Integer)
    date = db.Column(db.Date, default=date.today)
    location = db.Column(db.String(100))

class UserMatch(db.Model):
    __tablename__ = 'user_match'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id', ondelete='CASCADE'))
    goals = db.Column(db.Integer)
    assists = db.Column(db.Integer)
    shots = db.Column(db.Integer)
    shots_on_target = db.Column(db.Integer)
    passes = db.Column(db.Integer)
    fouls = db.Column(db.Integer)
    yellow_cards = db.Column(db.Integer)
    red_cards = db.Column(db.Integer)

class Team(db.Model):
    __tablename__ = 'teams'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    difficulty = db.Column(db.Integer)

class Location(db.Model):
    __tablename__ = 'locations'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

class Achievement(db.Model):
    __tablename__ = 'achievements'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(511), unique=False, nullable=False)
    difficulty = db.Column(db.Integer)

class UserAchievement(db.Model):
    __tablename__ = 'user_achievement'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    achievement_id = db.Column(db.Integer, db.ForeignKey('achievements.id', ondelete='CASCADE'))
    date = db.Column(db.Date, default=date.today)
