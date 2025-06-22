from flask import Flask, render_template, request, redirect, url_for, flash
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import config

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Replace with a strong secret key

# MySQL config
app.config['MYSQL_HOST'] = config.MYSQL_HOST
app.config['MYSQL_USER'] = config.MYSQL_USER
app.config['MYSQL_PASSWORD'] = config.MYSQL_PASSWORD
app.config['MYSQL_DB'] = config.MYSQL_DB

mysql = MySQL(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# User model
class User(UserMixin):
    def __init__(self, id, name, email):
        self.id = id
        self.name = name
        self.email = email

@login_manager.user_loader
def load_user(user_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users WHERE id = %s", [user_id])
    user = cur.fetchone()
    if user:
        return User(user[0], user[1], user[2])
    return None

@app.route('/')
def home():
    return render_template("home.html")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s", [email])
        user = cur.fetchone()

        if user:
            flash('Email already exists!', 'danger')
            return redirect(url_for('register'))

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        cur.execute("INSERT INTO users (name, email, password) VALUES (%s, %s, %s)", (name, email, hashed_password))
        mysql.connection.commit()
        cur.close()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s", [email])
        user = cur.fetchone()

        if user and bcrypt.check_password_hash(user[3], password):
            user_obj = User(user[0], user[1], user[2])
            login_user(user_obj)
            return redirect(url_for('dashboard'))

        flash('Invalid login credentials!', 'danger')
        return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM subjects WHERE user_id = %s", [current_user.id])
    subjects = cur.fetchall()

    notes_by_subject = {}
    for subj in subjects:
        cur.execute("SELECT * FROM notes WHERE subject_id = %s", [subj[0]])
        notes = cur.fetchall()
        notes_by_subject[subj[0]] = notes

    cur.close()
    return render_template('dashboard.html', user=current_user, subjects=subjects, notes_by_subject=notes_by_subject)

@app.route('/add_subject', methods=['POST'])
@login_required
def add_subject():
    name = request.form['subject_name']
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO subjects (user_id, name) VALUES (%s, %s)", (current_user.id, name))
    mysql.connection.commit()
    cur.close()
    flash('Subject added!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/add_note', methods=['POST'])
@login_required
def add_note():
    subject_id = request.form['subject_id']
    title = request.form['title']
    content = request.form['content']
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO notes (subject_id, title, content) VALUES (%s, %s, %s)", (subject_id, title, content))
    mysql.connection.commit()
    cur.close()
    flash('Note added!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/delete_subject/<int:subject_id>', methods=['POST'])
@login_required
def delete_subject(subject_id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM notes WHERE subject_id = %s", [subject_id])
    cur.execute("DELETE FROM subjects WHERE id = %s AND user_id = %s", (subject_id, current_user.id))
    mysql.connection.commit()
    cur.close()
    flash('Subject and its notes deleted!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/delete_note/<int:note_id>',methods=['POST'])
@login_required
def delete_note(note_id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM notes WHERE id = %s AND subject_id IN (SELECT id FROM subjects WHERE user_id = %s)", 
                [note_id, current_user.id])
    mysql.connection.commit()
    cur.close()
    flash('Note deleted!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/edit_subject/<int:subject_id>', methods=['GET', 'POST'])
@login_required
def edit_subject(subject_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM subjects WHERE id = %s AND user_id = %s", [subject_id, current_user.id])
    subject = cur.fetchone()

    if request.method == 'POST':
        new_name = request.form['subject_name']
        cur.execute("UPDATE subjects SET name = %s WHERE id = %s", [new_name, subject_id])
        mysql.connection.commit()
        cur.close()
        flash('Subject updated!', 'success')
        return redirect(url_for('dashboard'))

    cur.close()
    return render_template('edit_subject.html', subject=subject)

@app.route('/edit_note/<int:note_id>', methods=['GET', 'POST'])
@login_required
def edit_note(note_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM notes WHERE id = %s AND subject_id IN (SELECT id FROM subjects WHERE user_id = %s)", 
                [note_id, current_user.id])
    note = cur.fetchone()

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        cur.execute("UPDATE notes SET title = %s, content = %s WHERE id = %s", [title, content, note_id])
        mysql.connection.commit()
        cur.close()
        flash('Note updated!', 'success')
        return redirect(url_for('dashboard'))

    cur.close()
    return render_template('edit_note.html', note=note)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
