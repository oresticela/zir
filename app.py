from flask import Flask, render_template, url_for, request, redirect, flash, session
from pymongo import MongoClient
import secrets
import string
import paypalrestsdk

app = Flask(__name__)
app.secret_key = "oresti"

# MongoDB connection
uri = "mongodb+srv://oresti:oresti@zirapp.u05jwyn.mongodb.net/?retryWrites=true&w=majority&appName=zirapp"
client = MongoClient(uri)
db = client["zirapp"]
users = db["users"]
groups = db["groups"]
notes = db["notes"]
todos = db["todos"]
todosdone = db["To-Dos Done"]
chat = db['chat']

paypalrestsdk.configure({
    "mode": "sandbox",  # sandbox or live
    "client_id": "AdImIegHRa7yuJ78wPccSqc7o5JveUR2fKI5eoQPITbmc0WtzrI3X0A8grgHNTCfIa5id4abBWiaAZsv",
    "client_secret": "EJSsWz_EYK0y4N6yH1u2xouV50Y_y5Dr0fuAV3Xod6vWJgMmYZrhPj0zYQf-MuKGFcW4wYm-osZjjSQz"
})

@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')

@app.route('/home', methods=['GET', 'POST'])
def home():
    # Ensure only logged-in users can access this page
    if 'user_id' not in session:
        flash('You must be logged in to view this page.', 'error')
        return redirect(url_for('login'))

    print(session)


    if request.method == 'POST':
        note = request.form.get('note')
        todo = request.form.get('todo')

        if note:
            user = users.find_one({"email": session['email']})
            notes.insert_one({str(user['group']): str(note)})
        else:
            user = users.find_one({"email": session['email']})
            todos.insert_one({str(user['group']): str(todo)})

        return redirect(url_for('home'))

    user = users.find_one({"email": session['email']})

    cursor = notes.find({str(user['group']): {"$exists": True}})
    cursor_todo = todos.find({str(user['group']): {"$exists": True}})
    cursor_todo_done = todosdone.find({str(user['group']): {"$exists": True}})
    todos_done = [document_todo_done.get(str(user['group'])) for document_todo_done in cursor_todo_done]


    # Extract the notes
    group_notes = [document.get(str(user['group'])) for document in cursor]
    group_todos = [document_todo.get(str(user['group'])) for document_todo in cursor_todo]

    user = users.find_one({"email": user['email']})

    your_group = groups.find_one({"code": user['group']})
    return render_template('home.html', name=session.get('name'), chat=chat, user=user, users=users, group=your_group, notes=group_notes, todos_done=todos_done, todos=group_todos, session=session)

@app.route('/delete', methods=['POST'])
def delete_note():
    if request.method == 'POST':
        note_to_delete = request.form.get('note')

        # Find and delete the document containing the specific note
        notes.delete_one({str(session['group']): note_to_delete})

    return redirect(url_for('home'))

@app.route('/deletetodo', methods=['POST'])
def delete_todo():
    if request.method == 'POST':
        todo_to_delete = request.form.get('todo')

        # Find and delete the document containing the specific note
        todos.delete_one({str(session['group']): todo_to_delete})

    return redirect(url_for('home'))

@app.route('/delete_group', methods=['POST', 'GET'])
def delete_group():
    user = users.find_one({"email": session['email']})

    if user['group'] != 0:

        delete_group = groups.find_one({"code": user['group']})
        users.update_many(
            {"group": delete_group['code']},
            {"$set": {"group": "0"}}
        )
        groups.delete_one({"code": delete_group['code']})
        flash("Group Successfully Deleted")

        return redirect(url_for('home'))

@app.route('/tododone', methods=['POST'])
def todo_done():
    if request.method == 'POST':
        todo_done = request.form.get('todo')

        cursor_todo_done = todos.find({str(session['group']): {"$exists": True}})

        todos_done = [document_todo_done.get(str(session['group'])) for document_todo_done in cursor_todo_done]


        # Find and delete the document containing the specific note
        todosdone.insert_one({str(session['group']): todo_done})
        todos.delete_one({str(session['group']): todo_done})

    return redirect(url_for('home'))

@app.route('/tododonedelete', methods=['POST'])
def todo_done_delete():
    if request.method == 'POST':
            todo_done = request.form.get('todo_done')

            # Find and delete the document containing the specific note
            todosdone.delete_one({str(session['group']): todo_done})

    return redirect(url_for('home'))

@app.route('/join_group', methods=['POST'])
def join_group():
    if request.method == 'POST':
        group_code = request.form.get('group_code')

        if groups.find_one({"code": str(group_code)}):
            group_found = groups.find_one({"code": str(group_code)})

            after_user_group = {"$set": {"group": group_found['code']}}

            users.update_one(
                {"email": session['email']},
                after_user_group
            )

            flash("Successfully joined the group", 'success')
            return redirect(url_for('home'))
        else:
            flash("That code does not match with any group!", "error")
            return redirect(url_for('home'))


@app.route('/send_message', methods=['POST'])
def send_message():
    message = request.form.get('message')
    sender = session['name']

    user = users.find_one({"email": session['email']})

    chat.insert_one({"sender": sender, "message": message, "group": user['group']})

    return redirect(url_for('home'))


@app.route('/create_group', methods=['POST'])
def create_group():
    if request.method == 'POST':
        group_name = request.form.get('group_name')
        group_description = request.form.get('group_description')

        def generate_custom_random_code(length=8, exclude_confusing=True):
            characters = string.ascii_letters + string.digits
            if exclude_confusing:
                characters = characters.replace('O', '').replace('0', '').replace('l', '').replace('1', '')
            code = ''.join(secrets.choice(characters) for _ in range(length))
            return code

        # Example usage
        custom_random_code = generate_custom_random_code(12)
        user = users.find_one({"email": session['email']})

        if user['account'] == "leader":
            groups.insert_one({"name": group_name, "description": group_description, "code":custom_random_code})
            users.update_one(
                    {"email": session['email']},
                    {"$set": {"group": custom_random_code}}
                )

        return redirect(url_for('home'))



@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        if users.find_one({"email": email}):
            flash('Email already exists. Please use another email.', 'error')
            return redirect(url_for('signup'))

        new_user = {
            "name": name,
            "email": email,
            "password": password,
            "account": "leader",
            "group": "0"
        }

        users.insert_one(new_user)
        flash('Sign-up successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():

    if 'user_id' not in session:

        if request.method == 'POST':
            email = request.form.get('email')
            password = request.form.get('password')

            user = users.find_one({"email": email})
            if user and users.find_one({"email": email, "password":password}):
                # User authenticated, set session variables
                session['user_id'] = str(user['_id'])
                session['name'] = user['name']
                session['email'] = user['email']
                session['group'] = user['group']
                session['account'] = user['account']
                flash('Login successful!', 'success')
                return redirect(url_for('home'))
            else:
                flash('Invalid email or password.', 'error')
                return redirect(url_for('login'))

        return render_template('login.html')
    else:
        return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True)
