import os
import shutil
import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text, func

# Initialize SQLAlchemy with no app tied to it yet
db = SQLAlchemy()

# --- MODEL ---
class Timer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    start_time = db.Column(db.Integer, nullable=True) 
    position = db.Column(db.Integer, default=0)

    # Relationship to sessions
    sessions = db.relationship('SessionHistory', backref='timer', cascade="all, delete-orphan", lazy=True)

    @property
    def total_banked_time(self):
        """Calculates the sum of all sessions and manual edits for this timer."""
        total = db.session.query(func.sum(SessionHistory.duration)).filter_by(timer_id=self.id).scalar()
        return total if total else 0

class SessionHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timer_id = db.Column(db.Integer, db.ForeignKey('timer.id'), nullable=False)
    entry_type = db.Column(db.String(50), default='session') # 'session' or 'manual_edit'
    start_time = db.Column(db.Integer, nullable=False)
    end_time = db.Column(db.Integer, nullable=False)
    duration = db.Column(db.Integer, nullable=False) # Store in seconds

# --- DATABASE SETUP ---
def init_db(app):
    """Binds the database to the Flask app and creates tables."""
    db.init_app(app)
    with app.app_context():
        # Enable WAL mode for better SQLite stability
        db.session.execute(text("PRAGMA journal_mode=WAL"))
        db.create_all()

# --- DATABASE HELPERS ---
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

def backup_database(app, db_path):
    """
    Forces a WAL checkpoint and copies the database to the backups folder.
    Returns (True, filename) on success, or (False, error_message) on failure.
    """
    if not os.path.exists(db_path):
        return False, "Database file does not exist yet."
        
    try:
        with app.app_context():
            db.session.execute(text("PRAGMA wal_checkpoint(TRUNCATE)"))
            
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"timers_backup_{timestamp}.db"
        backup_dir = os.path.join(os.path.dirname(db_path), 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        dest_path = os.path.join(backup_dir, backup_name)
        shutil.copy(db_path, dest_path)
        return True, backup_name
    except Exception as e:
        return False, str(e)