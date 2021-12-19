import json
import random
from flask.templating import render_template_string
from werkzeug.urls import URL
from app import app, db, bcrypt
from itsdangerous import URLSafeTimedSerializer
from flask import render_template, redirect, url_for, request, flash, session, jsonify
from MySQLdb._exceptions import IntegrityError

ts = URLSafeTimedSerializer(app.config['SECRET_KEY'])


@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')


@app.route('/dashboard')
def dashboard():
    cursor = db.connection.cursor()
    cursor.execute("SELECT * FROM datav WHERE uid = %s", (session['user_id'],))
    stuff = cursor.fetchall()
    return render_template('dashboard.html', stuff=stuff, session=session)


@app.route('/login', methods=["GET", "POST"])
def login():
    msg = None
    # if session['logged_in'] == True or session != None:
    #     return redirect(url_for('dashboard'))
    # else:
    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']
        cursor = db.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        if user:
            if bcrypt.check_password_hash(user[4], password):
                session['user_id'] = user[0]
                session['username'] = user[3]
                session['logged_in'] = True
                session['fname'] = user[1]
                session['ukey'] = random.randint(1000000, 9999999)
                # session['ukey'] = ts.dumps(
                #     session['user_id'], salt='u-key', max_age=604800)
                return redirect(url_for('dashboard'))
            else:
                msg = 'Incorrect password'
        else:
            msg = 'User not found'
    if msg != None:
        return render_template('login.html', msg=msg)

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = None
    # if session['logged_in'] == True or session != None:
    #     return redirect(url_for('dashboard'))
    # else:
    if request.method == "POST":
        cursor = db.connection.cursor()
        fname = request.form['fname']
        lname = request.form['lname']
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        rpass = request.form['rpass']

        if password == rpass:
            try:
                hashed_password = bcrypt.generate_password_hash(password)
                cursor.execute("""INSERT INTO users (fname, lname, username, usersPassword, email) VALUES (%s, %s, %s, %s, %s)""", (
                    fname, lname, username, hashed_password, email))
                db.connection.commit()
                session['username'] = username
                session['logged_in'] = True
                session['user_id'] = cursor.lastrowid
                session['fname'] = fname
                session['ukey'] = random.randint(1000000, 9999999)
                return redirect(url_for('dashboard'))
            except IntegrityError:
                db.connection.rollback()
                msg = "Email already exists"
        else:
            msg = "Passwords do not match"
        if msg != None:
            return render_template('register.html', msg=msg)
            return redirect(url_for('login'))
    return render_template('register.html')
# https://prod.liveshare.vsengsaas.visualstudio.com/join?C7167ABD0C477D3DE8345D354827C1FDDFD2


@app.route('/add-data', methods=['GET', 'POST'])
def add_data():
    if request.method == "POST":
        data_received = request.get_json()
        print(data_received)
        fr = data_received['for']
        data = data_received['data']
        cursor = db.connection.cursor()
        cursor.execute("""INSERT INTO datav (fr, datav, uid) VALUES (%s, %s, %s)""",
                       (fr, data, session['user_id']))
        db.connection.commit()
        return jsonify({"success": True, "id": cursor.lastrowid})


@app.route('/get-data', methods=['GET', 'POST'])
def get_data():
    if request.method == "POST":
        data_received = request.get_json()
        print(data_received)
        id = data_received['id']
        cursor = db.connection.cursor()
        cursor.execute("""SELECT * FROM datav WHERE id = %s""", (id,))
        data = cursor.fetchone()
        if data[3] != session['user_id']:
            return jsonify({"success": True, "msg": "You are not authorized to view this data"})
        return jsonify({"success": True, "data": data})

@app.route('/delete-data', methods=['GET', 'POST'])
def delete_data():
    if request.method == 'POST':
        data_received = request.get_json()
        print(data_received)
        id = data_received['id']
        cursor = db.connection.cursor()
        cursor.execute("""SELECT * FROM datav WHERE id = %s""", (id,))
        stuff = cursor.fetchone()
        print(stuff)
        if stuff != None:
            if stuff[3] == session['user_id']:
                cursor.execute("""DELETE FROM datav WHERE id = %s""", (id,))
                db.connection.commit()
                return jsonify({"success": True, "id": id})
            else:
                return jsonify({"success":True, "data": "You are not authorized to delete this data"})
        else:
            return jsonify({"success":True, "msg": "No data with that id was found."})
        
@app.route('/alter-data', methods=['GET', 'POST'])
def alter_data():
    if request.method == 'POST':
        data_received = request.get_json()
        print(data_received)
        id = data_received['id']
        fr = data_received['for']
        data = data_received['data']
        cursor = db.connection.cursor()
        cursor.execute("""SELECT * FROM datav WHERE id = %s""", (id,))
        stuff = cursor.fetchone()
        if stuff != None:
            if stuff[3] == session['user_id']:
                cursor.execute("""UPDATE datav SET fr = %s, datav = %s WHERE id = %s""", (fr, data, id))
                db.connection.commit()
                return jsonify({"success": True, "id": id})
            else:
                return jsonify({"success":True, "unauthorized": True, "data": "You are not authorized to alter this data"})
        else:
            return jsonify({"success":True, "msg": "No data with that id was found."})
        
@app.route('/delete-user', methods=['GET', 'POST'])
def delete_account():
    if request.method == "POST":
        data_received = request.get_json()
        cursor = db.connection.cursor()
        cursor.execute("""SELECT * FROM users WHERE id = %s""", (session['user_id'],))
        user = cursor.fetchone()
        cursor.execute("""SELECT * FROM datav WHERE uid = %s""", (session['user_id'],))
        data = cursor.fetchall()
        if user != None:
            if data != None:
                cursor.execute("""DELETE FROM datav WHERE uid = %s""", (session['user_id'],))
                cursor.execute("""DELETE FROM users WHERE id = %s""", (session['user_id'],))
                db.connection.commit()
                return jsonify({"success": True, "msg": "User deleted and all data associated with them deleted."})
            else:
                cursor.execute("""DELETE FROM users WHERE id = %s""", (session['user_id'],))
                db.connection.commit()
                return jsonify({"success": True, "msg": "User deleted."})
        else:
            return jsonify({"success": False, "msg": "User not found."})
                