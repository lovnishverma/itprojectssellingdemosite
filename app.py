from flask import Flask, render_template, redirect, request, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import pytz
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ab#1867$@817'  # Replace with a strong random key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'  # Database filename

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

# User model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return "<User {}>".format(self.username)

# Project model for the database table
class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_name = db.Column(db.String(100), nullable=False)
    project_details = db.Column(db.Text, nullable=False)

# ProjectRequest model for the database table
class ProjectRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    user = db.relationship('User', backref='project_requests')
    project = db.relationship('Project', backref='project_requests')
    message_to_admin = db.Column(db.Text)  # New field for user message to admin

# Load user function required by Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create the database tables
db.create_all()

# Form to create a new project
class NewProjectForm(FlaskForm):
    project_name = StringField('Project Name', validators=[DataRequired()])
    project_details = TextAreaField('Project Details', validators=[DataRequired()])
    message_to_admin = TextAreaField('Message to Admin')  # Add the new message field
    submit = SubmitField('Create Project')

# ...

@app.route('/admin/project_requests')
@login_required
def admin_project_requests():
    # Make sure only the admin can access this view
    if current_user.username != "admin":
        flash("You do not have permission to access this page.", 'error')
        return redirect(url_for('dashboard'))

    # Get all project requests from the database
    project_requests = ProjectRequest.query.all()

    return render_template('admin_project_requests.html', project_requests=project_requests)

# ...

if __name__ == '__main__':
    app.run(debug=True)
