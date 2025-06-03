from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'student' or 'warden'
    name = db.Column(db.String(100), nullable=False)

class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='New')  # New, In Progress, Resolved
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    student = db.relationship('User')

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow)
    status = db.Column(db.String(10), default='Present')  # Present, Absent
    location = db.Column(db.String(100))
    student = db.relationship('User')

class GatePass(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    out_time = db.Column(db.DateTime, nullable=False)
    in_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='Pending')  # Pending, Approved, Rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    student = db.relationship('User')

# Create tables
with app.app_context():
    db.create_all()

# Login Manager
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def home():
    return render_template('base.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            if user.role == 'student':
                return redirect(url_for('student_dashboard'))
            else:
                return redirect(url_for('warden_dashboard'))
        else:
            flash('Invalid username or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        name = request.form['name']
        role = request.form['role']
        
        # Check if username already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists')
            return redirect(url_for('register'))
        
        # Create new user
        new_user = User(
            username=username,
            password=generate_password_hash(password, method='sha256'),
            name=name,
            role=role
        )
        
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please login.')
        return redirect(url_for('login'))
    
    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

# Student Routes
@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if current_user.role != 'student':
        return redirect(url_for('warden_dashboard'))
    
    # Get counts for dashboard
    complaints = Complaint.query.filter_by(student_id=current_user.id).count()
    attendance = Attendance.query.filter_by(student_id=current_user.id).count()
    gatepasses = GatePass.query.filter_by(student_id=current_user.id).count()
    
    return render_template('student/dashboard.html', 
                         complaints=complaints, 
                         attendance=attendance, 
                         gatepasses=gatepasses)

@app.route('/student/complaint', methods=['GET', 'POST'])
@login_required
def student_complaint():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        
        new_complaint = Complaint(
            student_id=current_user.id,
            title=title,
            description=description
        )
        db.session.add(new_complaint)
        db.session.commit()
        flash('Complaint submitted successfully!')
        return redirect(url_for('student_complaint'))
    
    complaints = Complaint.query.filter_by(student_id=current_user.id).order_by(Complaint.created_at.desc()).all()
    return render_template('student/complaint.html', complaints=complaints)

@app.route('/student/attendance', methods=['GET', 'POST'])
@login_required
def student_attendance():
    if request.method == 'POST':
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')
        
        location = f"Lat: {latitude}, Lon: {longitude}" if latitude and longitude else "Location unavailable"

        new_attendance = Attendance(
            student_id=current_user.id,
            location=location
        )
        db.session.add(new_attendance)
        db.session.commit()
        flash('Attendance marked successfully!')
        return redirect(url_for('student_attendance'))
    
    attendance = Attendance.query.filter_by(student_id=current_user.id).order_by(Attendance.date.desc()).all()
    return render_template('student/attendance.html', attendance=attendance)


@app.route('/student/gatepass', methods=['GET', 'POST'])
@login_required
def student_gatepass():
    if request.method == 'POST':
        reason = request.form['reason']
        out_time = datetime.strptime(request.form['out_time'], '%Y-%m-%dT%H:%M')
        in_time = datetime.strptime(request.form['in_time'], '%Y-%m-%dT%H:%M')
        
        new_gatepass = GatePass(
            student_id=current_user.id,
            reason=reason,
            out_time=out_time,
            in_time=in_time
        )
        db.session.add(new_gatepass)
        db.session.commit()
        flash('Gate pass requested successfully!')
        return redirect(url_for('student_gatepass'))
    
    gatepasses = GatePass.query.filter_by(student_id=current_user.id).order_by(GatePass.created_at.desc()).all()
    return render_template('student/gatepass.html', gatepasses=gatepasses)

@app.route('/student/records')
@login_required
def student_records():
    complaints = Complaint.query.filter_by(student_id=current_user.id).order_by(Complaint.created_at.desc()).all()
    attendance = Attendance.query.filter_by(student_id=current_user.id).order_by(Attendance.date.desc()).all()
    gatepasses = GatePass.query.filter_by(student_id=current_user.id).order_by(GatePass.created_at.desc()).all()
    
    return render_template('student/records.html', 
                         complaints=complaints, 
                         attendance=attendance, 
                         gatepasses=gatepasses)

# Warden Routes
@app.route('/warden/dashboard')
@login_required
def warden_dashboard():
    if current_user.role != 'warden':
        return redirect(url_for('student_dashboard'))
    
    # Get counts for dashboard
    pending_gatepasses = GatePass.query.filter_by(status='Pending').count()
    new_complaints = Complaint.query.filter_by(status='New').count()
    
    return render_template('warden/dashboard.html', 
                         pending_gatepasses=pending_gatepasses, 
                         new_complaints=new_complaints)

@app.route('/warden/gatepass', methods=['GET', 'POST'])
@login_required
def warden_gatepass():
    if current_user.role != 'warden':
        return redirect(url_for('student_dashboard'))
    
    if request.method == 'POST':
        gatepass_id = request.form['gatepass_id']
        action = request.form['action']
        
        gatepass = GatePass.query.get(gatepass_id)
        if action == 'approve':
            gatepass.status = 'Approved'
        else:
            gatepass.status = 'Rejected'
        
        db.session.commit()
        flash(f'Gate pass {action}d successfully!')
        return redirect(url_for('warden_gatepass'))
    
    gatepasses = GatePass.query.filter_by(status='Pending').order_by(GatePass.created_at.desc()).all()
    return render_template('warden/gatepass.html', gatepasses=gatepasses)

from collections import defaultdict

@app.route('/warden/attendance')
@login_required
def warden_attendance():
    if current_user.role != 'warden':
        return redirect(url_for('student_dashboard'))

    attendance_data = db.session.query(Attendance, User).join(User).order_by(Attendance.date.desc()).all()

    # Count attendance per student
    attendance_counts = defaultdict(int)
    student_names = {}

    for record, user in attendance_data:
        attendance_counts[user.id] += 1
        student_names[user.id] = user.name

    chart_labels = [student_names[uid] for uid in attendance_counts.keys()]
    chart_values = [count for count in attendance_counts.values()]

    return render_template('warden/attendance.html', 
                           attendance=attendance_data,
                           chart_labels=chart_labels,
                           chart_values=chart_values)


@app.route('/warden/complaints', methods=['GET', 'POST'])
@login_required
def warden_complaints():
    if current_user.role != 'warden':
        return redirect(url_for('student_dashboard'))
    
    if request.method == 'POST':
        complaint_id = request.form['complaint_id']
        status = request.form['status']
        
        complaint = Complaint.query.get(complaint_id)
        complaint.status = status
        db.session.commit()
        flash('Complaint status updated successfully!')
        return redirect(url_for('warden_complaints'))
    
    complaints = db.session.query(Complaint, User).join(User).order_by(Complaint.created_at.desc()).all()
    return render_template('warden/complaints.html', complaints=complaints)

if __name__ == '__main__':
    app.run(debug=True)