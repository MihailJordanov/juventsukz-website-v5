from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import re
from sqlalchemy import func, extract
import os
from models import db, User, Match, UserMatch, UserAchievement, Team, Location, Achievement
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("SQLALCHEMY_DATABASE_URI")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Инициализиране на базата данни
db.init_app(app)


@app.route('/getUsers')
def get_users():
    users = User.query.all()
    user_data = []

    for user in users:
        win_rate, total_matches = calculate_user_win_rate(user.id)
        user_data.append({
            'id': user.id,
            'type': user.type,
            'title': user.title,
            'last_name': user.last_name,
            'win_rate': win_rate,
            'total_matches': total_matches
        })

    return jsonify(user_data)

@app.route('/getMatches', methods=['GET'])
def get_matches():
    matches = Match.query.all()
    matches_list = []
    for match in matches:
        match_data = {
            'team_one': match.team_one,
            'team_two': match.team_two,
            'team_one_result': match.team_one_result,
            'team_two_result': match.team_two_result,
            'date': match.date.isoformat(),
            'type': match.type  # Добавяме вида на мача
        }
        matches_list.append(match_data)
    return jsonify(matches_list)



@app.route('/matchHistory', methods=['GET', 'POST'])
def matchHistory():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('matchHistory.html')


@app.route('/saveStats', methods=['POST'])
def save_stats():
    data = request.json
    user_id = data.get('user_id')
    stats = data.get('stats')

    if not user_id or not stats:
        return jsonify({'error': 'Missing data'}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Вземете най-голямото ID на мач от таблицата Matches
    max_match_id = db.session.query(func.max(Match.id)).scalar()
    if not max_match_id:
        return jsonify({'error': 'No matches found'}), 404

    try:
        user_match = UserMatch(
            user_id=user_id,
            match_id=max_match_id,  # Използвайте най-голямото ID на мача
            goals=stats['goals'],
            assists=stats['assists'],
            shots=stats['shots'],
            shots_on_target=stats['shots_on_target'],
            passes=stats['passes'],
            fouls=stats['fouls'],
            yellow_cards=stats['yellow_cards'],
            red_cards=stats['red_cards']
        )

        db.session.add(user_match)
        db.session.commit()

        return jsonify({'message': 'Stats saved successfully!'}), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error: {e}")  # Ще добавим лог за грешката
        return jsonify({'error': str(e)}), 500


@app.route('/getStats')
def get_stats():
    # Текущият потребител от сесията
    current_user_id = session.get('user_id')

    # Извличане на статистиките за всеки потребител с помощта на агрегационни функции
    user_stats = db.session.query(
        User.id,
        User.first_name,
        User.last_name,
        func.sum(UserMatch.goals).label('total_goals'),
        func.sum(UserMatch.assists).label('total_assists'),
        func.sum(UserMatch.shots).label('total_shots'),
        func.sum(UserMatch.shots_on_target).label('total_shots_on_target'),
        func.sum(UserMatch.passes).label('total_passes'),
        func.sum(UserMatch.fouls).label('total_fouls'),
        func.sum(UserMatch.yellow_cards).label('total_yellow_cards'),
        func.sum(UserMatch.red_cards).label('total_red_cards')
    ).join(UserMatch, User.id == UserMatch.user_id) \
    .group_by(User.id, User.first_name, User.last_name) \
    .all()

    # Маркиране на текущия потребител
    stats = []
    for user in user_stats:
        stats.append({
            'user_id': user.id,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'total_goals': user.total_goals or 0,
            'total_assists': user.total_assists or 0,
            'total_shots': user.total_shots or 0,
            'total_shots_on_target': user.total_shots_on_target or 0,
            'total_passes': user.total_passes or 0,
            'total_fouls': user.total_fouls or 0,
            'total_yellow_cards': user.total_yellow_cards or 0,
            'total_red_cards': user.total_red_cards or 0,
            'is_current_user': user.id == current_user_id
        })

    # Сортиране: текущият потребител първи
    sorted_stats = sorted(stats, key=lambda x: not x['is_current_user'])

    return jsonify(sorted_stats)


@app.route('/stats', methods=['GET', 'POST'])
def stats():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('stats.html')


@app.route('/addMatches', methods=['GET', 'POST'])
def add_matches():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    current_user = get_current_user()
    if current_user is None:
        return redirect(url_for('login'))
    
    if current_user.type <= 0:
        return redirect(url_for('home'))

    if request.method == 'POST':
        try:
            # Извличане на основна информация за мача от формата
            match_type = request.form.get('type')
            team_one = request.form.get('team_one')
            team_two = request.form.get('team_two')
            team_one_result = int(request.form.get('team_one_result'))
            team_two_result = int(request.form.get('team_two_result'))
            date = request.form.get('date')
            location = request.form.get('location')

            # Създаване на нов запис за мача
            new_match = Match(type=match_type, team_one=team_one, team_two=team_two,
                              team_one_result=team_one_result, team_two_result=team_two_result,
                              date=date, location=location)

            db.session.add(new_match)
            db.session.flush()  # Изпълняваме flush, за да получим ID на новия мач
            
            # Обработка на статистиката на играчите
            for user in User.query.all():
                # Проверка дали чекбоксът "Играл" е маркиран
                played = request.form.get(f'played_{user.id}')  # Чекбоксът ще върне "on", ако е маркиран
                if played:  # Обработваме само ако чекбоксът е маркиран
                    goals = int(request.form.get(f'goals_{user.id}', 0))
                    assists = int(request.form.get(f'assists_{user.id}', 0))
                    shots = int(request.form.get(f'shots_{user.id}', 0))
                    shots_on_target = int(request.form.get(f'shots_on_target_{user.id}', 0))
                    passes = int(request.form.get(f'passes_{user.id}', 0))
                    fouls = int(request.form.get(f'fouls_{user.id}', 0))
                    yellow_cards = int(request.form.get(f'yellow_cards_{user.id}', 0))
                    red_cards = int(request.form.get(f'red_cards_{user.id}', 0))

                    # Създаване и запазване на статистика за съответния играч
                    users_match = UserMatch(user_id=user.id, match_id=new_match.id,
                                            goals=goals, assists=assists, shots=shots,
                                            shots_on_target=shots_on_target, passes=passes,
                                            fouls=fouls, yellow_cards=yellow_cards,
                                            red_cards=red_cards)
                    db.session.add(users_match)

                    # Актуализиране на max_goals на играча
                    user.max_goals += goals  
                    user.max_assists += assists
                    user.played_matches += 1
                    user.max_passes += passes
                    user.max_hat_tricks += (goals // 3)
                    if(team_one_result > team_two_result):
                        user.win_matches += 1
                    elif(team_one_result == team_two_result):
                        user.draw_matches +=1
                    if(user.max_goals_in_one_match < goals and match_type != "Training"):
                        user.max_goals_in_one_match = goals
                    if(user.max_assists_in_one_match < assists and match_type != "Training"):
                        user.max_assists_in_one_match  = goals
                    if(user.max_passes_in_one_match < passes and match_type != "Training"):
                        user.max_passes_in_one_match   = goals

                    
                    db.session.add(user)  # Добавяме обновения играч в сесията

            # Потвърждение на транзакцията
            db.session.commit()
            return redirect(url_for('home'))

        except Exception as e:
            # Връщане обратно на транзакцията при грешка
            db.session.rollback()
            flash('Please fill in the fields')
            return redirect(url_for('add_matches'))

    # При GET заявка връщаме шаблона
    return render_template('addmatch.html')


def get_current_user():
    user_id = session.get('user_id')  # Get the user_id from session
    if user_id:
        return User.query.get(user_id)  # Fetch the user from the database
    return None

@app.route('/', methods=['GET'])
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    current_user = get_current_user()
    if current_user is None:
        return redirect(url_for('login')) 
    
    return render_template('home.html', user_type=current_user.type)


@app.route('/login', methods=['GET', 'POST'])
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
            flash('Грешен имейл или парола.', 'danger')
    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if len(first_name) < 3 or not re.match("^[A-Z][a-z]+$", first_name):
            flash('First name must be at least 3 characters long, contain only letters, and start with a capital letter.')
            return redirect(url_for('signup'))

        if len(last_name) < 3 or not re.match("^[A-Z][a-z]+$", last_name):
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
                        max_passes = 0, max_passes_in_one_match = 0, max_hat_tricks = 0)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('signup.html')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Успешно излязохте от профила.', 'info')
    return redirect(url_for('login'))


@app.route('/add_team_location', methods=['GET', 'POST'])
def add_team_location():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    current_user = get_current_user()
    if current_user is None:
        return redirect(url_for('login'))
    
    if current_user.type <= 0:
        return redirect(url_for('home'))


    if request.method == 'POST':
        # Проверка дали е подадена форма за отбор
        if 'team_name' in request.form and 'difficulty' in request.form:
            team_name = request.form['team_name']
            difficulty = int(request.form['difficulty'])

            # Проверка дали отборът вече съществува
            existing_team = Team.query.filter_by(name=team_name).first()
            if existing_team:
                return redirect(url_for('add_team_location', team_exists=True))

            new_team = Team(name=team_name, difficulty=difficulty)
            db.session.add(new_team)
            db.session.commit()

            return redirect(url_for('add_team_location', team_success=True))

        # Проверка дали е подадена форма за локация
        elif 'location_name' in request.form:
            location_name = request.form['location_name']

            # Проверка дали локацията вече съществува
            existing_location = Location.query.filter_by(name=location_name).first()
            if existing_location:
                return redirect(url_for('add_team_location', location_exists=True))

            new_location = Location(name=location_name)
            db.session.add(new_location)
            db.session.commit()

            return redirect(url_for('add_team_location', location_success=True))

    return render_template('controlldb.html')


@app.route('/winRate')
def win_rate():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Извличаме всички мачове от базата данни
    matches = Match.query.all()
    
    # Изчисляваме общия win rate
    total_wins = sum(1 for match in matches if match.team_one_result > match.team_two_result)
    total_matches = len(matches)
    overall_win_rate = round((total_wins / total_matches * 100), 2) if total_matches > 0 else 0
    
    # Изчисляваме win rate по локация
    location_stats = {}
    for match in matches:
        location = match.location
        if location:  # Проверяваме дали location не е None или празен
            if location not in location_stats:
                location_stats[location] = {'wins': 0, 'losses': 0, 'draws': 0, 'total': 0}
            location_stats[location]['total'] += 1
            
            if match.team_one_result > match.team_two_result:
                location_stats[location]['wins'] += 1
            elif match.team_one_result < match.team_two_result:
                location_stats[location]['losses'] += 1
            else:
                location_stats[location]['draws'] += 1

    location_win_rates = {
        location: {
            'win_rate': round((stats['wins'] / stats['total'] * 100), 2) if stats['total'] > 0 else 0,
            'total_matches': stats['total'],
            'wins': stats['wins'],
            'losses': stats['losses'],
            'draws': stats['draws'],
        }
        for location, stats in location_stats.items()
    }

    # Изчисляваме win rate по away_team
    away_team_stats = {}
    for match in matches:
        away_team = match.team_two
        if away_team:  # Проверяваме дали away_team не е None или празен
            if away_team not in away_team_stats:
                away_team_stats[away_team] = {'wins': 0, 'losses': 0, 'draws': 0, 'total': 0}
            away_team_stats[away_team]['total'] += 1
            
            if match.team_one_result > match.team_two_result:
                away_team_stats[away_team]['wins'] += 1
            elif match.team_one_result < match.team_two_result:
                away_team_stats[away_team]['losses'] += 1
            else:
                away_team_stats[away_team]['draws'] += 1

    away_team_win_rates = {
        away_team: {
            'win_rate': round((stats['wins'] / stats['total'] * 100), 2) if stats['total'] > 0 else 0,
            'total_matches': stats['total'],
            'wins': stats['wins'],
            'losses': stats['losses'],
            'draws': stats['draws'],
        }
        for away_team, stats in away_team_stats.items()
    }

    return render_template('winRate.html', overall_win_rate=overall_win_rate, 
                           location_win_rates=location_win_rates, 
                           away_team_win_rates=away_team_win_rates)



@app.route('/getYears')
def get_years():
    years = db.session.query(func.extract('year', Match.date)).distinct().order_by(func.extract('year', Match.date)).all()
    # Преобразуваме резултата в обикновен списък от години
    year_list = [int(year[0]) for year in years]
    return jsonify(year_list)


@app.route('/getPlayTimeData')
def get_play_time_data():
    year = request.args.get('year', type=int)

    # Извличаме броя на мачовете по месеци за избраната година
    matches_by_month = db.session.query(
        extract('month', Match.date).label('month'),
        func.count(Match.id).label('count')
    ).filter(extract('year', Match.date) == year) \
     .group_by('month').order_by('month').all()

    # Преобразуваме данните в JSON формат
    data = [{'month': m[0], 'count': m[1]} for m in matches_by_month]

    return jsonify(data)



@app.route('/playtime')
def playtime():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('playtime.html')



@app.route('/getTeams')
def get_teams():
    teams = Team.query.all()  # Предполагаме, че имате модел Team
    return jsonify([team.name for team in teams])  # Върнете списък с имената на отборите


@app.route('/getLocations')
def get_locations():
    locations = Location.query.all()  # Предполагаме, че имате модел Location
    return jsonify([location.name for location in locations]) 


@app.route('/op_users')
def op_users():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    current_user = get_current_user()
    if current_user is None:
        return redirect(url_for('login'))
    
    if current_user.type <= 1:
        return redirect(url_for('home'))

    users = User.query.all()
    return render_template('op_users.html', users=users)


@app.route('/update_user_types', methods=['POST'])
def update_user_types():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    current_user = get_current_user()
    if current_user is None or current_user.type <= 1:
        return redirect(url_for('home'))

    users = User.query.all()

    for user in users:
        user_type_key = f"user_type_{user.id}"
        user_number_key = f"user_number_{user.id}"
        user_title_key = f"user_title_{user.id}"

        if user_type_key in request.form:
            user.type = int(request.form[user_type_key])
        if user_number_key in request.form:
            user.number = int(request.form[user_number_key])
        if user_title_key in request.form:
            user.title = request.form[user_title_key]
    
    db.session.commit()
    return redirect(url_for('op_users'))


def get_achievement_by_id(id):
    return Achievement.query.get(id)


@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    current_user = get_current_user()
    if current_user is None:
        return redirect(url_for('login'))
    
    if current_user.type <= 0:
        return redirect(url_for('home'))
    current_user_id = session.get('user_id')
    user = User.query.get(current_user_id)
    

    if user.number == 7:
        profile_image = 'images/teniska.jfif'
        outline_image = 'images/bar1.jpg'  
    elif user.number == 8:
        profile_image = 'images/teniska.jfif'
        outline_image = 'images/bg35.png' 
    elif user.number == 9:
        profile_image = 'images/teniska.jfif'
        outline_image = 'images/bar1.jpg' 
    elif user.number == 10:
        profile_image = 'images/teniska.jfif'
        outline_image = 'images/man3.jpg' 
    elif user.number == 11:
        profile_image = 'images/teniska.jfif'
        outline_image = 'images/bayernStadium.jpg' 
    elif user.number == 17:
        profile_image = 'images/teniska.jfif'
        outline_image = 'images/bayernStadium.jpg'
    elif user.number == 19:
        profile_image = 'images/teniska.jfif'
        outline_image = 'images/bayernStadium.jpg'
    elif user.number == 47:
        profile_image = 'images/teniska.jfif'
        outline_image = 'images/bayernStadium.jpg'   
    else:
        profile_image = 'images/teniska.jfif'
        outline_image = 'images/bg35.png'
    

    achievements = []
    if current_user.max_goals >= 7:
        achievements.append(get_achievement_by_id(2))  
    if current_user.max_goals >= 77:
        achievements.append(get_achievement_by_id(3)) 
    if current_user.max_goals >= 777:
        achievements.append(get_achievement_by_id(4)) 
    if current_user.max_goals_in_one_match >= 7:
        achievements.append(get_achievement_by_id(5)) 



    win_rate, total_matches = calculate_user_win_rate(current_user_id)

    return render_template('profile.html', user=user, achievements=achievements, win_rate=win_rate, total_matches=total_matches, profile_image=profile_image, outline_image=outline_image)


def get_user_by_id(user_id):
    return User.query.get(user_id)


def calculate_user_win_rate(user_id):
    # Вземете записите от UserMatch за потребителя
    user_matches = UserMatch.query.filter_by(user_id=user_id).all()

    wins = 0
    losses = 0
    draws = 0

    # Изчислете резултатите за всеки мач
    for user_match in user_matches:
        match = Match.query.get(user_match.match_id)
        if match:
            if match.team_one_result > match.team_two_result:
                wins += 1
            elif match.team_one_result < match.team_two_result:
                losses += 1
            else:
                draws += 1

    total_matches = wins + losses + draws
    win_rate = (wins / total_matches * 100) if total_matches > 0 else 0

    win_rate = round(win_rate, 2)

    return win_rate, total_matches


@app.route('/album', methods=['GET'])
def album():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    current_user = get_current_user()
    if current_user is None:
        return redirect(url_for('login')) 
    
    return render_template('album.html', user_type=current_user.type)


@app.route('/add_achievements', methods=['GET', 'POST'])
def add_achievements():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    current_user = get_current_user()
    if current_user is None:
        return redirect(url_for('login'))
    
    if current_user.type <= 1:
        return redirect(url_for('home'))

    if request.method == 'POST':
        name = request.form['name']
        difficulty = int(request.form['difficulty'])
        description = request.form['description']
        
        new_achievement = Achievement(name=name, difficulty=difficulty, description=description)
        db.session.add(new_achievement)
        db.session.commit()
        return redirect(url_for('add_achievements'))
    
    achievements = Achievement.query.all()
    return render_template('add_achievements.html', achievements=achievements)


@app.route('/achievements')
def achievements():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    current_user = get_current_user()
    if current_user is None:
        return redirect(url_for('login'))
    

    achievements = Achievement.query.all()
    return render_template('achievements.html', achievements=achievements)


if __name__ == '__main__':
    app.run(debug=True)
