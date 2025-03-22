from app import app, db, User
from werkzeug.security import generate_password_hash
import os

def init_db():
    """Initialize the database."""
    print("Initializing database...")
    try:
        # Make sure the upload folder exists
        if not os.path.exists('static/uploads'):
            os.makedirs('static/uploads')
            print("Created uploads directory")

        with app.app_context():
            # Drop all tables
            db.drop_all()
            print("Dropped all tables.")
            
            # Create all tables
            db.create_all()
            print("Created all tables.")
            
            # Create admin user if not exists
            admin = User.query.filter_by(username='admin').first()
            if not admin:
                admin = User(
                    username='admin',
                    email='admin@example.com',
                    password=generate_password_hash('admin', method='sha256'),
                    is_instructor=True
                )
                db.session.add(admin)
                db.session.commit()
                print("Created admin user.")
            
            print("Database initialization complete.")
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        raise

if __name__ == '__main__':
    init_db()
