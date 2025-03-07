from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False)

    def __repr__(self):
        return f'<User {self.username}>'

    def set_password(self, password):
        """Set password."""
        self.password = generate_password_hash(password)

    def check_password(self, value):
        """Check password."""
        return check_password_hash(self.password, value)


class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticket_number = db.Column(db.String(20), unique=True, nullable=False)
    raised_by = db.Column(db.String(80), nullable=False)
    attended_by = db.Column(db.String(80))
    status = db.Column(db.String(20), default='Open')
    start_time = db.Column(db.DateTime)
    close_time = db.Column(db.DateTime)
    downtime = db.Column(db.Float)  # In minutes
    # Production details
    line = db.Column(db.String(50))
    project = db.Column(db.String(50))
    station = db.Column(db.String(50))
    qpl = db.Column(db.Integer)
    section = db.Column(db.String(50))
    # Engineer details
    respond_time = db.Column(db.Float)
    issue_description = db.Column(db.Text)
    category = db.Column(db.String(50))
    root_cause = db.Column(db.Text)
    corrective_action = db.Column(db.Text)
    spares_required = db.Column(db.Text)

    def __repr__(self):
        return f'<Ticket {self.ticket_number}>'
