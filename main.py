from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

import time
import os
import shutil
import datetime
import subprocess

app = Flask(__name__)

# --- CONFIGURATION ---
base_dir = os.path.abspath(os.path.dirname(__file__))
data_dir = os.path.join(base_dir, 'data')
db_path = os.path.join(data_dir, 'timers.db')

os.makedirs(data_dir, exist_ok=True)

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- HELPERS ---
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

def move_to_top(timer_to_move):
    """
    Shifts all timers above the target DOWN by 1, 
    then moves the target to Position 0.
    """
    if timer_to_move.position == 0:
        return # Already at top

    # Find all timers strictly above the current one (0 to N-1)
    timers_above = Timer.query.filter(Timer.position < timer_to_move.position).all()
    
    # Push them all down by 1
    for t in timers_above:
        t.position += 1
    
    # Move target to top
    timer_to_move.position = 0

def is_time_synced():
    """
    Cross-platform check for system clock synchronization.
    Supports Linux (timedatectl) and Windows (w32tm).
    """
    try:
        # 1. Windows Check
        if os.name == 'nt':
            # Run 'w32tm /query /status' to check the time source
            output = subprocess.check_output(['w32tm', '/query', '/status'], text=True)
            
            # If the source is "Local CMOS Clock", it is NOT synced to the internet.
            # If it lists a server (e.g. "time.windows.com"), it IS synced.
            return "Local CMOS Clock" not in output

        # 2. Linux / Raspberry Pi Check
        else:
            result = subprocess.check_output(
                ['timedatectl', 'show', '-p', 'NTPSynchronized', '--value'],
                text=True
            ).strip()
            return result == 'yes'

    except Exception:
        # If the command fails completely, fail safe to False
        return False

# --- MODEL ---
class Timer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    start_time = db.Column(db.Integer, nullable=True) 
    banked_time = db.Column(db.Integer, default=0)
    position = db.Column(db.Integer, default=0)

with app.app_context():
    db.session.execute(text("PRAGMA journal_mode=WAL"))
    db.create_all()

# --- ROUTES ---

@app.route('/')
def index():
    # 1. Sort purely by Position (0 is top)
    timers = Timer.query.order_by(Timer.position.asc()).all()
    
    # 2. Check Time Sync Status
    synced = is_time_synced()
    
    return render_template('index.html', timers=timers, now=time.time(), synced=synced)

@app.route('/sw.js')
def service_worker():
    return send_from_directory('static', 'sw.js', mimetype='application/javascript')

@app.route('/add', methods=['POST'])
def add_timer():
    name = request.form.get('name')
    if name:
        # 1. Shift everyone down to make room at the top
        existing_timers = Timer.query.all()
        for t in existing_timers:
            t.position += 1
            
        # 2. Insert new timer at Position 0
        new_timer = Timer(name=name, position=0)
        db.session.add(new_timer)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/start/<int:id>')
def start_timer(id):
    timer = db.session.get(Timer, id)
    if timer:
        # 1. Move to Top (MRU Logic)
        move_to_top(timer)
        
        # 2. Start Logic (if not already running)
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
        # Note: We do NOT change position here. 
        # It stays at the top until something else pushes it down.
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

if __name__ == '__main__':
    if os.path.exists(db_path):
        with app.app_context():
            try:
                db.session.execute(text("PRAGMA wal_checkpoint(TRUNCATE)"))
            except Exception as e:
                print(f"⚠️ Warning: Checkpoint failed: {e}")

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"timers_backup_{timestamp}.db"
        backup_dir = os.path.join(os.path.dirname(db_path), 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        shutil.copy(db_path, os.path.join(backup_dir, backup_name))
        print(f"✅ Database backed up to: backups/{backup_name}")

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)