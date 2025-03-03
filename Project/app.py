from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from mysql.connector import Error
import bcrypt
app = Flask(__name__)
app.secret_key = 'your_secret_key'

def connect_to_mysql():
    try:
        connection = mysql.connector.connect(
            host='localhost',  # Change this if you're using a different host
            database='Digitalsys',  # Replace with your MySQL database name
            user='root',  # Replace with your MySQL username
            password='root'  # Replace with your MySQL password
        )
        return connection
    except Error as e:
        print(f"Error: {e}")
        return None

@app.route('/')
def home():
    return render_template('index.html')


@app.route('/login')
def loginhtml():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']

    connection = connect_to_mysql()
    if connection is not None:
        try:
            cursor = connection.cursor(dictionary=True)

            # Check if user exists
            query = "SELECT * FROM users WHERE email = %s"
            cursor.execute(query, (email,))
            user = cursor.fetchone()

            if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
                # Login successful, store user info in session
                session['user_id'] = user['id']
                session['username'] = user['username']
                flash('Login successful!', 'success')
                return redirect(url_for('dashboard'))  # Redirect to a dashboard page
            else:
                flash('Invalid email or password', 'danger')
                return redirect(url_for('login_page'))

        except Error as e:
            return f"Database Error: {e}"
        finally:
            cursor.close()
            connection.close()
    return "Failed to connect to the database."


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please log in first', 'warning')
        return redirect(url_for('login_page'))

    return f"Welcome, {session['username']}! <br><a href='/logout'>Logout</a>"

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login_page'))

@app.route('/register', methods=['GET'])
def show_form():
    return render_template('register.html')
@app.route('/register', methods=['POST'])
def register():

    name = request.form['name']
    email = request.form['email']
    password = request.form['password']

    # Hash the password before storing it in the database
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    # Insert the data into MySQL
    connection = connect_to_mysql()
    if connection is not None:
        try:
            cursor = connection.cursor()

            # SQL query to insert data into users table
            query = "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)"
            values = (name, email, hashed_password)

            cursor.execute(query, values)
            connection.commit()

            return redirect(url_for('login'))

        except Error as e:
            return f"Error: {e}"
        finally:
            cursor.close()
            connection.close()
    return "Failed to connect to the database."


if __name__ == '__main__':
    app.run(debug=True)