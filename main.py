from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

import time
import os
import shutil
import datetime

app = Flask(__name__)

# --- NEW PATH LOGIC ---
# 1. Define the folder and file path
base_dir = os.path.abspath(os.path.dirname(__file__))
data_dir = os.path.join(base_dir, 'data')
db_path = os.path.join(data_dir, 'timers.db')

# 2. Create the 'data' directory if it doesn't exist
os.makedirs(data_dir, exist_ok=True)

# 3. Configure Flask to use this new path
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Model ---
class Timer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    # start_time is NULL if stopped, otherwise it holds the timestamp
    start_time = db.Column(db.Integer, nullable=True) 
    banked_time = db.Column(db.Integer, default=0)
    position = db.Column(db.Integer, default=0)

with app.app_context():
    # Enable WAL mode for better stability
    db.session.execute(text("PRAGMA journal_mode=WAL"))
    db.create_all()

# --- Routes ---
@app.route('/')
def index():
    # 1. Get all timers
    timers = Timer.query.all()
    
    # 2. Python Sort Logic for "Auto-Float"
    # Primary Key: (t.start_time is None). False (0) comes before True (1).
    # Secondary Key: t.position (Your manual order)
    sorted_timers = sorted(timers, key=lambda t: (t.start_time is None, t.position))
    
    return render_template('index.html', timers=sorted_timers, now=time.time())

# Add this to your app.py
@app.route('/sw.js')
def service_worker():
    # We serve the file from 'static', but the browser thinks it's at root
    return send_from_directory('static', 'sw.js', mimetype='application/javascript')

@app.route('/add', methods=['POST'])
def add_timer():
    name = request.form.get('name')
    if name:
        # Add to the bottom of the "manual" list
        max_pos = db.session.query(db.func.max(Timer.position)).scalar()
        new_pos = (max_pos + 1) if max_pos is not None else 0
        
        new_timer = Timer(name=name, position=new_pos)
        db.session.add(new_timer)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/start/<int:id>')
def start_timer(id):
    timer = Timer.query.get(id)
    if timer and not timer.start_time: # Only start if currently stopped
        timer.start_time = int(time.time())
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/stop/<int:id>')
def stop_timer(id):
    timer = Timer.query.get(id)
    if timer and timer.start_time: # Only stop if currently running
        now = int(time.time())
        elapsed = now - timer.start_time
        timer.banked_time += elapsed
        timer.start_time = None
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/move/<int:id>/<direction>')
def move_timer(id, direction):
    current = Timer.query.get(id)
    if not current: return redirect(url_for('index'))
    
    # Simple swap logic for manual ordering
    if direction == 'up':
        neighbor = Timer.query.filter(Timer.position < current.position)\
                              .order_by(Timer.position.desc()).first()
    else: # down
        neighbor = Timer.query.filter(Timer.position > current.position)\
                              .order_by(Timer.position.asc()).first()

    if neighbor:
        current.position, neighbor.position = neighbor.position, current.position
        db.session.commit()
        
    return redirect(url_for('index'))

@app.route('/delete/<int:id>')
def delete_timer(id):
    timer = Timer.query.get(id)
    if timer:
        db.session.delete(timer)
        db.session.commit()
    return redirect(url_for('index'))

if __name__ == '__main__':
    # --- 1. Automatic Backup on Launch ---
    if os.path.exists(db_path):
        # FORCE DATA SYNC: Move data from WAL to DB before copying
        with app.app_context():
            print("⏳ Checkpointing database (merging WAL)...")
            try:
                # TRUNCATE moves data to .db and deletes the .wal file
                db.session.execute(text("PRAGMA wal_checkpoint(TRUNCATE)"))
                print("✅ Database checkpointed successfully.")
            except Exception as e:
                print(f"⚠️ Warning: Checkpoint failed: {e}")

        # NOW it is safe to copy just the .db file
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"timers_backup_{timestamp}.db"
        
        backup_dir = os.path.join(os.path.dirname(db_path), 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        shutil.copy(db_path, os.path.join(backup_dir, backup_name))
        print(f"✅ Database backed up to: backups/{backup_name}")

    # --- 2. Run the App ---
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)