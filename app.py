from flask import Flask, render_template, redirect, request, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import pytz
from flask_wtf import FlaskForm
from wtforms import TextAreaField, SubmitField
from wtforms.validators import DataRequired

app = Flask(__name__)
app.config['SECRET_KEY'] = 'joa#1867$@817it'  # Replace with a strong random key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'  # Database filename

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

# User model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(255), nullable=False)
    password = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return "<User {}>".format(self.username)

# Load user function required by Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_image = db.Column(db.String(200), nullable=False)
    project_name = db.Column(db.String(100), nullable=False)
    project_details = db.Column(db.Text, nullable=False)
    
    # Change the backref name to 'project_requests' in the relationship definition
    requests = db.relationship('ProjectRequest', backref=db.backref('project', lazy=True))


# ProjectRequest model for the database table
class ProjectRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    custom_message = db.Column(db.Text, nullable=True)

    # Change the backref name to 'user' in the relationship definition
    user = db.relationship('User', backref=db.backref('project_requests', lazy=True))



class ProjectRequestForm(FlaskForm):
    custom_message = TextAreaField('Custom Message', validators=[DataRequired()])
    submit = SubmitField('Request this Project')

# Create the database tables
with app.app_context():
    db.create_all()

@app.route('/')
@login_required
def dashboard():
    # Helper function to read and update visitor count
    def get_visitor_count():
        with open("visitor_count.txt", "r") as f:
            count = int(f.read())
        count += 1
        with open("visitor_count.txt", "w") as f:
            f.write(str(count))
        return count
    
    # Get the current UTC time
    utc_now = datetime.utcnow()

    # Define the timezone for India (IST)
    tz = pytz.timezone('Asia/Kolkata')

    # Get the UTC offset for the India time zone
    india_offset = timedelta(seconds=tz.utcoffset(utc_now).total_seconds())

    # Add the UTC offset to the current UTC time to get India time
    india_time = utc_now + india_offset

    # Extract date and time components in 12-hour format
    date = india_time.strftime("%Y-%m-%d")
    time = india_time.strftime("%I:%M %p")

    # Extract only the year from the date
    year = india_time.strftime("%Y")

    # Get the current hour in the India time zone
    india_hour = india_time.hour

    # Determine the time of day based on the current hour
    if 5 <= india_hour < 12:
        time_of_day = 'Morning'
    elif 12 <= india_hour < 17:
        time_of_day = 'Afternoon'
    elif 17 <= india_hour < 21:
        time_of_day = 'Evening'
    else:
        time_of_day = 'Night'
    
    # Get the visitor count
    visitor_count = get_visitor_count()
    username = current_user.username  # Get the username of the current user
    
    # Fetch all projects from the database
    projects = Project.query.all()

    return render_template("main.html", projects=projects, username=username, time_of_day=time_of_day, date=date, time=time, year=year, visitor_count=visitor_count)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Logged in successfully.', 'success')
            return redirect(url_for('dashboard'))

        flash('Invalid username or password.', 'error')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        phone = request.form['phone']
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user:
            flash('Username already exists. Please choose a different username.', 'error')
        else:
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                flash('Email already exists. Please choose a different email.', 'error')
            else:
                hashed_password = generate_password_hash(password)
                new_user = User(username=username, phone=phone, email=email, password=hashed_password)
                db.session.add(new_user)
                db.session.commit()
                flash('Registration successful. You can now log in.', 'success')
                return redirect(url_for('login'))

    return render_template('register.html')
@app.route('/request_project/<int:project_id>', methods=['GET', 'POST'])
@login_required
def request_project(project_id):
    project = Project.query.get(project_id)

    if project is None:
        flash("Project not found.", 'error')
        return redirect(url_for('dashboard'))

    form = ProjectRequestForm()

    if form.validate_on_submit():
        custom_message = form.custom_message.data

        # Store the project request in the database
        new_request = ProjectRequest(user_id=current_user.id, project_id=project.id, custom_message=custom_message)
        db.session.add(new_request)
        db.session.commit()

        flash("Project request sent successfully.", 'success')
        return redirect(url_for('dashboard'))

    return render_template('request_project.html', form=form)
  
@app.route('/users')
@login_required
def list_users():
    if current_user.username == "admin":
        users = User.query.all()
        return render_template('user_list.html', users=users)
    else:
        flash("You do not have permission to access Admin page.", 'error')
        return redirect(url_for('dashboard'))

@app.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.username == "admin":
        if current_user.id == user_id:
            flash("You cannot delete your own account.", 'error')
        else:
            user = User.query.get(user_id)
            if user:
                db.session.delete(user)
                db.session.commit()
                flash("User '{}' has been deleted.".format(user.username), 'success')
            else:
                flash("User not found.", 'error')
    else:
        flash("You do not have permission to perform this action.", 'error')
    return redirect(url_for('list_users'))

# Admin Panel - Main Page
@app.route('/admin')
@login_required
def admin_panel():
    if current_user.is_authenticated and current_user.username == "admin":
        return render_template('admin_panel.html')
    
    flash("You do not have permission to access the Admin panel.", 'error')
    return redirect(url_for('dashboard'))

@app.route('/admin/project_requests')
@login_required
def project_requests():
    if current_user.is_authenticated and current_user.username == "admin":
        # Fetch all project requests from the database
        project_requests = ProjectRequest.query.all()

        return render_template('project_requests.html', project_requests=project_requests)

    flash("You do not have permission to access the Admin panel.", 'error')
    return redirect(url_for('dashboard'))


# Admin Panel - Add New Project
@app.route('/admin/add_project', methods=['GET', 'POST'])
@login_required
def add_project():
    if current_user.is_authenticated and current_user.username == "admin":
        if request.method == 'POST':
            project_image = request.form['projectImage']
            project_name = request.form['projectName']
            project_details = request.form['projectDetails']

            # Store the project data in the database
            new_project = Project(
                project_image=project_image,
                project_name=project_name,
                project_details=project_details,
            )
            db.session.add(new_project)
            db.session.commit()
            flash("Project added successfully.", 'success')
            return redirect(url_for('admin_panel'))

        return render_template('add_project.html')

    flash("You do not have permission to access the Admin panel.", 'error')
    return redirect(url_for('dashboard'))

# Admin Panel - List Projects
@app.route('/admin/list_projects')
@login_required
def list_projects():
    if current_user.is_authenticated and current_user.username == "admin":
        projects = Project.query.all()
        return render_template('list_projects.html', projects=projects)

    flash("You do not have permission to access the Admin panel.", 'error')
    return redirect(url_for('dashboard'))

# Admin Panel - Modify Project
@app.route('/admin/modify_project/<int:project_id>', methods=['GET', 'POST'])
@login_required
def modify_project(project_id):
    if current_user.is_authenticated and current_user.username == "admin":
        project = Project.query.get(project_id)

        if project is None:
            flash("Project not found.", 'error')
            return redirect(url_for('admin_panel'))

        if request.method == 'POST':
            project.project_image = request.form['projectImage']
            project.project_name = request.form['projectName']
            project.project_details = request.form['projectDetails']

            db.session.commit()
            flash("Project updated successfully.", 'success')
            return redirect(url_for('admin_panel'))

        return render_template('modify_project.html', project=project)

    flash("You do not have permission to access the Admin panel.", 'error')
    return redirect(url_for('dashboard'))

# Admin Panel - Delete Project
@app.route('/admin/delete_project/<int:project_id>', methods=['POST'])
@login_required
def delete_project(project_id):
    if current_user.is_authenticated and current_user.username == "admin":
        project = Project.query.get(project_id)

        if project is None:
            flash("Project not found.", 'error')
        else:
            db.session.delete(project)
            db.session.commit()
            flash("Project deleted successfully.", 'success')

    return redirect(url_for('admin_panel'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)