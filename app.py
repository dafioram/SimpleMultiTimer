from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import time
import os

app = Flask(__name__)

# Ensure the instance folder exists for the database
db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'timers.db')
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

@app.route('/toggle/<int:id>')
def toggle_timer(id):
    timer = Timer.query.get(id)
    if timer:
        now = int(time.time())
        if timer.start_time: 
            # STOP: Bank the difference, clear start time
            elapsed = now - timer.start_time
            timer.banked_time += elapsed
            timer.start_time = None
        else:
            # START: Set start time
            timer.start_time = now
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
    app.run(host='0.0.0.0', port=5000)