from app import app, db, User
from werkzeug.security import generate_password_hash

with app.app_context():
    # Create test student
    student = User(
        username='student1',
        password=generate_password_hash('password123'),
        role='student',
        name='Test Student'
    )
    db.session.add(student)
    
    # Create test warden
    warden = User(
        username='warden1',
        password=generate_password_hash('password123'),
        role='warden',
        name='Test Warden'
    )
    db.session.add(warden)
    
    db.session.commit()
    print("Test users created successfully!")