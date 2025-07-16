from flask import Flask, render_template_string, request, redirect, url_for, session
import random
from jinja2 import Environment, FileSystemLoader, select_autoescape, TemplateNotFound

# from api_utils import recommend_players_by_tier # Import if you are using the API features

app = Flask(__name__)
app.secret_key = 'your_super_secret_key_change_this_in_production_please'

# --- Game Data & Setup ---
DECADES = ['1950s', '1960s', '1970s', '1980s', '1990s', '2000s', '2010s', '2020s']
BENCH_DECADES = ['1960s', '1970s', '1980s', '1990s', '2000s', '2010s', '2020s']
POSITIONS = [1, 2, 3, 4, 5]
ABILITIES = ['95+', '90~94', '85~89', '80~84', '75~79']

# --- HTML Templates (No changes to logic) ---
BASE_TEMPLATE_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Fantasy Team Draft</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #282c34; color: #abb2bf; margin: 20px; line-height: 1.6; display: flex; justify-content: center; align-items: center; min-height: 90vh; }
        .container { max-width: 800px; width: 100%; margin: auto; background-color: #3a404b; padding: 25px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3); }
        h1, h2, h3 { color: #61afef; text-align: center; margin-bottom: 25px; }
        p { font-size: 1.1em; margin-bottom: 15px; text-align: center; }
        .player-info { background-color: #4a505b; padding: 15px; border-radius: 6px; margin-bottom: 20px; text-align: center; }
        .player-info strong { color: #e5c07b; }
        .form-container { display: flex; justify-content: center; align-items: center; gap: 15px; flex-wrap: wrap; }
        .form-group { text-align: center; margin-top: 25px; }
        .form-group button, .form-group input[type="submit"] { padding: 12px 25px; margin: 0 5px; background-color: #98c379; color: white; border: none; border-radius: 5px; font-size: 1em; cursor: pointer; transition: background-color 0.3s ease; }
        .form-group button:hover, .form-group input[type="submit"]:hover { background-color: #82b362; }
        .form-group button.no-btn, form button.no-btn { background-color: #e06c75; }
        .form-group button.no-btn:hover, form button.no-btn:hover { background-color: #c05860; }
        input[type="text"] { padding: 10px; border-radius: 5px; border: 1px solid #5c6370; background-color: #282c34; color: #abb2bf; width: calc(100% - 22px); box-sizing: border-box; margin-bottom: 15px; font-size: 1em; }
        ul { list-style-type: none; padding: 0; }
        li { background-color: #4a505b; margin-bottom: 8px; padding: 10px 15px; border-radius: 5px; display: flex; justify-content: space-between; align-items: center; }
        .team-display { margin-top: 30px; border-top: 1px solid #5c6370; padding-top: 20px; }
        .team-display h3 { color: #e5c07b; }
        .team-display ul li { background-color: #3a404b; border: 1px solid #5c6370; }
        .team-display ul li span:first-child { font-weight: bold; color: #98c379; }
        .restart-button { background-color: #be5046 !important; margin-top: 15px !important; }
        .restart-button:hover { background-color: #a04036 !important; }
    </style>
</head>
<body><div class="container">{% block content %}{% endblock %}</div></body>
</html>
"""

START_PAGE_TEMPLATE = """
{% extends 'base.html' %}
{% block content %}
    <h1>Welcome to the Fantasy Team Draft!</h1>
    <p>You will draft starters and bench players for two teams (Team A and Team B), taking turns.</p>
    <div class="form-group">
        <form action="/start_draft" method="post"><button type="submit">Start Draft</button></form>
    </div>
{% endblock %}
"""

DRAFT_PLAYER_TEMPLATE = """
{% extends 'base.html' %}
{% block content %}
    <h2>Drafting {{ player_type }} #{{ current_round_player_number }} for {{ team_name }}...</h2>
    <div class="player-info">
        <p>Player drawn:</p>
        <p><strong>Decade:</strong> {{ player.decade }} | <strong>Position:</strong> {{ player.position }} | {% if player.ability %}<strong>Ability:</strong> {{ player.ability }}{% endif %}</p>
    </div>
    <form action="/draft" method="post" class="form-group">
        <input type="text" name="player_name" placeholder="Enter player name" required>
        <button type="submit" name="action" value="save_player">Confirm Name (Accept Player)</button>
    </form>
    <form action="/reroll" method="post" class="form-group" style="margin-top: 10px;">
        <button type="submit" class="no-btn">Reroll (Reject Player)</button>
    </form>
    <div class="form-group">
        <form action="/" method="get"><button type="submit" class="restart-button">Back to Home</button></form>
    </div>
{% endblock %}
"""

INTERIM_SCREEN_TEMPLATE = """
{% extends 'base.html' %}
{% block content %}
    <h2>Starters Draft Complete!</h2>
    <div class="team-display">
        <h3>Team A Starters</h3>
        <ul>{% for p in team_a_starters %}<li><span>Position {{ p.position }}:</span> <span>{{ p.player }} ({{ p.decade }}, {{ p.ability }})</span></li>{% endfor %}</ul>
    </div>
    <div class="team-display">
        <h3>Team B Starters</h3>
        <ul>{% for p in team_b_starters %}<li><span>Position {{ p.position }}:</span> <span>{{ p.player }} ({{ p.decade }}, {{ p.ability }})</span></li>{% endfor %}</ul>
    </div>
    <div class="form-group">
        <form action="/start_bench_draft" method="post"><button type="submit">Continue to Bench Draft</button></form>
    </div>
{% endblock %}
"""

FINAL_DISPLAY_TEMPLATE = """
{% extends 'base.html' %}
{% block content %}
    <h1>Draft Complete!</h1>
    <div class="team-display">
        <h2>Team A Final Roster</h2>
        <h3>— Starters —</h3>
        <ul>{% for p in team_a_starters %}<li><span>Position {{ p.position }}:</span> <span>{{ p.player }} ({{ p.decade }}, {{ p.ability }})</span></li>{% endfor %}</ul>
        <h3>— Bench —</h3>
        <ul>{% for p in team_a_bench %}<li><span>Position {{ p.position }}:</span> <span>{{ p.player }} ({{ p.decade }})</span></li>{% endfor %}</ul>
    </div>
    <div class="team-display">
        <h2>Team B Final Roster</h2>
        <h3>— Starters —</h3>
        <ul>{% for p in team_b_starters %}<li><span>Position {{ p.position }}:</span> <span>{{ p.player }} ({{ p.decade }}, {{ p.ability }})</span></li>{% endfor %}</ul>
        <h3>— Bench —</h3>
        <ul>{% for p in team_b_bench %}<li><span>Position {{ p.position }}:</span> <span>{{ p.player }} ({{ p.decade }})</span></li>{% endfor %}</ul>
    </div>
    <div class="form-group">
        <form action="/" method="get"><button type="submit" class="restart-button">Restart Draft</button></form>
    </div>
{% endblock %}
"""


# --- Helper Functions ---
def initialize_game_state():
    session.clear()
    session['team_A_starters'], session['team_B_starters'] = [], []
    session['team_A_bench'], session['team_B_bench'] = [], []
    session['pos_pool_A'], session['abil_pool_A'] = POSITIONS[:], ABILITIES[:]
    session['pos_pool_B'], session['abil_pool_B'] = POSITIONS[:], ABILITIES[:]
    session['shuffled_bench_pos_A'], session['shuffled_bench_pos_B'] = [], []
    session['current_draft_team'], session['current_draft_type'] = 'A', 'starter'
    session['current_player_count'], session['current_round_player_number'] = 0, 1
    session['proposed_player_details'] = None
    session.modified = True

def propose_player(player_type, team):
    decades_pool = DECADES if player_type == 'starter' else BENCH_DECADES
    if player_type == 'starter':
        pos_pool = session.setdefault(f'pos_pool_{team}', [])
        abil_pool = session.setdefault(f'abil_pool_{team}', [])
        if not pos_pool or not abil_pool: return None
        pos, abil = random.choice(pos_pool), random.choice(abil_pool)
        pos_pool.remove(pos)
        abil_pool.remove(abil)
        proposed_data = {'decade': random.choice(decades_pool), 'position': pos, 'ability': abil, 'type': 'starter'}
    else: # Bench
        bench_pos_pool = session.setdefault(f'shuffled_bench_pos_{team}', [])
        if not bench_pos_pool:
            shuffled = POSITIONS[:]
            random.shuffle(shuffled)
            session[f'shuffled_bench_pos_{team}'] = shuffled
        if not session[f'shuffled_bench_pos_{team}']: return None
        pos = session[f'shuffled_bench_pos_{team}'].pop(0)
        proposed_data = {'decade': random.choice(decades_pool), 'position': pos, 'ability': None, 'type': 'bench'}
    session.modified = True
    return proposed_data

def return_proposed_player_to_pool(team, player_data):
    if player_data.get('type') == 'starter':
        pos_pool = session.setdefault(f'pos_pool_{team}', [])
        if player_data['position'] not in pos_pool:
            pos_pool.append(player_data['position'])
        abil_pool = session.setdefault(f'abil_pool_{team}', [])
        if player_data.get('ability') and player_data['ability'] not in abil_pool:
            abil_pool.append(player_data['ability'])
        session.modified = True

# --- THIS IS THE CORRECTED FUNCTION ---
def finalize_player_selection(team, player_data):
    """Adds a confirmed player to the correct team roster."""
    player_type = player_data['type'] # 'starter' or 'bench'

    # CORRECTED LOGIC: Explicitly define the key to avoid typos.
    if player_type == 'starter':
        roster_key = f'team_{team}_starters'
    else: # type must be 'bench'
        roster_key = f'team_{team}_bench' # The old code incorrectly added an 's' here.

    roster = session.setdefault(roster_key, [])
    if len(roster) < 5:
        roster.append(player_data)
        # Sort the list by position immediately after adding
        roster.sort(key=lambda p: p['position'])
    else:
        print(f"Warning: Roster for {roster_key} is full. Player rejected.")
        return_proposed_player_to_pool(team, player_data)
    
    session.modified = True


def next_draft_turn():
    session['current_player_count'] += 1
    if session['current_draft_team'] == 'A':
        session['current_draft_team'] = 'B'
    else:
        session['current_draft_team'] = 'A'
        session['current_round_player_number'] += 1
    session.modified = True
    if session['current_draft_type'] == 'starter' and session['current_player_count'] >= 10:
        return 'interim_screen'
    elif session['current_draft_type'] == 'bench' and session['current_player_count'] >= 10:
        return 'final_display'
    return 'continue_draft'

# --- Flask Routes ---
class StringLoader(FileSystemLoader):
    def __init__(self): super().__init__(searchpath=['.'])
    def get_source(self, environment, template):
        if template == 'base.html': return BASE_TEMPLATE_CONTENT, template, lambda: False
        raise TemplateNotFound(template)

app.jinja_env.loader = StringLoader()
app.jinja_env.autoescape = select_autoescape(['html', 'xml'])

@app.route('/')
def index():
    initialize_game_state()
    return render_template_string(START_PAGE_TEMPLATE)

@app.route('/start_draft', methods=['POST'])
def start_draft():
    proposed_player = propose_player('starter', 'A')
    if not proposed_player: return "Error: Could not generate first player.", 500
    session['proposed_player_details'] = proposed_player
    return redirect(url_for('draft_player'))

@app.route('/draft', methods=['GET', 'POST'])
def draft_player():
    if request.method == 'POST':
        player_name = request.form.get('player_name')
        if not player_name: return redirect(url_for('draft_player'))

        team = session['current_draft_team']
        player_data = session['proposed_player_details']
        player_data['player'] = player_name
        
        finalize_player_selection(team, player_data)
        session['proposed_player_details'] = None
        
        next_state = next_draft_turn()
        
        if next_state == 'interim_screen':
            return render_template_string(INTERIM_SCREEN_TEMPLATE,
                team_a_starters=session.get('team_A_starters', []),
                team_b_starters=session.get('team_B_starters', []))
        
        elif next_state == 'final_display':
            return render_template_string(FINAL_DISPLAY_TEMPLATE,
                team_a_starters=session.get('team_A_starters', []),
                team_a_bench=session.get('team_A_bench', []),
                team_b_starters=session.get('team_B_starters', []),
                team_b_bench=session.get('team_B_bench', []))
        
        else: # Continue draft
            next_player = propose_player(session['current_draft_type'], session['current_draft_team'])
            if not next_player: return "Error: Pool exhausted.", 500
            session['proposed_player_details'] = next_player
            return redirect(url_for('draft_player'))

    else: # GET request
        if 'proposed_player_details' not in session or not session['proposed_player_details']:
            return redirect(url_for('index'))
        
        return render_template_string(DRAFT_PLAYER_TEMPLATE,
            team_name="Team A" if session['current_draft_team'] == 'A' else "Team B",
            player_type="Starter" if session['current_draft_type'] == 'starter' else "Subs",
            current_round_player_number=session['current_round_player_number'],
            player=session['proposed_player_details'])

@app.route('/reroll', methods=['POST'])
def reroll_player():
    if 'proposed_player_details' not in session or not session['proposed_player_details']:
        return redirect(url_for('index'))

    team, player_type = session['current_draft_team'], session['current_draft_type']
    rejected_player = session['proposed_player_details']
    return_proposed_player_to_pool(team, rejected_player)
    
    new_player = propose_player(player_type, team)
    if new_player is None:
        return "Error: Could not re-roll, pool may be exhausted. Please restart.", 500

    session['proposed_player_details'] = new_player
    session.modified = True
    return redirect(url_for('draft_player'))

@app.route('/start_bench_draft', methods=['POST'])
def start_bench_draft():
    session['current_draft_type'] = 'bench'
    session['current_draft_team'] = 'A'
    session['current_player_count'] = 0
    session['current_round_player_number'] = 1
    
    for team_char in ['A', 'B']:
        shuffled_pos = POSITIONS[:]
        random.shuffle(shuffled_pos)
        session[f'shuffled_bench_pos_{team_char}'] = shuffled_pos

    proposed_player = propose_player('bench', 'A')
    if not proposed_player: return "Error: Could not start bench draft.", 500
    session['proposed_player_details'] = proposed_player
    session.modified = True
    return redirect(url_for('draft_player'))

# --- Run Application ---
if __name__ == '__main__':
    app.run(debug=True)