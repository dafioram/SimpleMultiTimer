from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv

import time
import os
import subprocess

# --- IMPORT DATABASE COMPONENTS ---
from database import db, Timer, init_db, move_to_top, backup_database

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

app.wsgi_app = ProxyFix(
    app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
)

# --- CONFIGURATION ---
base_dir = os.path.abspath(os.path.dirname(__file__))
data_dir = os.path.join(base_dir, 'data')
db_path = os.path.join(data_dir, 'timers.db')

os.makedirs(data_dir, exist_ok=True)

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database with our app context
init_db(app)

# --- NON-DB HELPERS ---
def parse_duration(time_str):
    time_str = time_str.strip()
    if not time_str: return 0
    parts = time_str.split(':')
    seconds = 0
    try:
        if len(parts) == 1:
            seconds = int(parts[0]) * 60
        elif len(parts) == 2:
            hours, minutes = int(parts[0]), int(parts[1])
            seconds = (hours * 3600) + (minutes * 60)
        elif len(parts) == 3:
            hours, minutes, secs = int(parts[0]), int(parts[1]), int(parts[2])
            seconds = (hours * 3600) + (minutes * 60) + secs
    except ValueError:
        pass 
    return seconds

def is_time_synced():
    """
    Cross-platform check for system clock synchronization.
    Supports Linux (timedatectl) and Windows (w32tm).
    """
    try:
        if os.name == 'nt':
            output = subprocess.check_output(['w32tm', '/query', '/status'], text=True)
            return "Local CMOS Clock" not in output
        else:
            result = subprocess.check_output(
                ['timedatectl', 'show', '-p', 'NTPSynchronized', '--value'],
                text=True
            ).strip()
            return result == 'yes'
    except Exception:
        return False


# --- ROUTES ---
@app.route('/')
def index():
    timers = Timer.query.all()
    
    # 1st Priority: Active status (Running timers bubble to top)
    # 2nd Priority: Position score (0 is newest/most recently used)
    sorted_timers = sorted(timers, key=lambda t: (t.start_time is None, t.position))
    
    synced = is_time_synced()
    return render_template('index.html', timers=sorted_timers, now=time.time(), synced=synced)

@app.route('/sw.js')
def service_worker():
    return send_from_directory('static', 'sw.js', mimetype='application/javascript')

@app.route('/add', methods=['POST'])
def add_timer():
    name = request.form.get('name')
    if name:
        existing_timers = Timer.query.all()
        for t in existing_timers:
            t.position += 1
            
        new_timer = Timer(name=name, position=0)
        db.session.add(new_timer)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/start/<int:id>')
def start_timer(id):
    timer = db.session.get(Timer, id)
    if timer:
        move_to_top(timer)
        if not timer.start_time:
            timer.start_time = int(time.time())
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/stop/<int:id>')
def stop_timer(id):
    timer = db.session.get(Timer, id)
    if timer and timer.start_time:
        now = int(time.time())
        elapsed = now - timer.start_time
        timer.banked_time += elapsed
        timer.start_time = None
        
        move_to_top(timer)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/edit_time/<int:id>', methods=['POST'])
def edit_time(id):
    timer = db.session.get(Timer, id)
    new_time_str = request.form.get('new_time')
    
    if timer and not timer.start_time and new_time_str:
        timer.banked_time = parse_duration(new_time_str)
        db.session.commit()
        
    return redirect(url_for('index'))

@app.route('/delete/<int:id>')
def delete_timer(id):
    timer = db.session.get(Timer, id)
    if timer:
        db.session.delete(timer)
        db.session.commit()
    return redirect(url_for('index'))

# --- API ROUTES ---
@app.route('/api/backup', methods=['POST'])
def api_backup():
    expected_key = os.environ.get("API_BACKUP_KEY")
    provided_key = request.headers.get('X-API-Key')
    
    if expected_key and provided_key != expected_key:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
    # We pass app and db_path explicitly to the helper
    success, result = backup_database(app, db_path)
    if success:
        return jsonify({"status": "success", "message": f"Database backed up to {result}"}), 200
    else:
        return jsonify({"status": "error", "message": result}), 500


if __name__ == '__main__':
    print("⏳ Running startup database backup...")
    success, msg = backup_database(app, db_path)
    if success:
        print(f"✅ Startup backup successful: backups/{msg}")
    else:
        print(f"⚠️ Warning: Startup backup failed: {msg}")

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)