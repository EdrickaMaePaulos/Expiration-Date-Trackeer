from datetime import datetime
from uuid import uuid4

from flask import Flask, render_template, request, redirect, url_for, flash, session, current_app
from flask_mysqldb import MySQL
import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps

load_dotenv()

app = Flask(__name__)

app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST', 'localhost')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER', 'root')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD', '')
app.config['MYSQL_DB'] = 'smartstock'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)

app.secret_key = os.getenv('SECRET_KEY', 'your_secret_key')

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please sign in to access this page.", "danger")
            return redirect(url_for('signin'))
        return f(*args, **kwargs)

    return decorated_function


@app.route('/')
def welcome():
    if 'user_id' in session:
        return redirect(url_for('home'))
    return render_template('index.html')




# Sign Up route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # Fetch form data
        fullname = request.form.get('fullname', '').strip()  # Ensure no leading/trailing spaces
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        # Validate all required fields are filled
        if not (fullname and username and email and password and confirm_password):
            flash('All fields are required.', 'danger')
            return redirect(url_for('signup'))

        # Validate password confirmation
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('signup'))

        # Hash the password for secure storage
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        try:
            # Check if the email already exists in the database
            cur = mysql.connection.cursor()
            cur.execute("SELECT user_id FROM users WHERE email=%s", (email,))
            user = cur.fetchone()

            if user:
                flash('Email is already registered. Please try signing in.', 'danger')
                return redirect(url_for('signup'))

            # Insert new user into the database
            cur.execute("""
                INSERT INTO users (fullname, username, email, password)
                VALUES (%s, %s, %s, %s)
            """, (fullname, username, email, hashed_password))
            mysql.connection.commit()

            flash('Account created successfully! Please sign in.', 'success')
            return redirect(url_for('signin'))

        except Exception as e:
            # Log the error and notify the user
            flash(f'An error occurred while creating your account: {str(e)}', 'danger')
            return redirect(url_for('signup'))

        finally:
            # Close the database cursor
            cur.close()

    # GET request renders the signup form
    return render_template('signup.html')


# Sign In route
@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        if not (email and password):
            flash("Email and password are required.", "danger")
            return redirect(url_for('signin'))

        cur = mysql.connection.cursor()
        try:
            # Fetch user data by email
            cur.execute("SELECT user_id, fullname, username, password FROM users WHERE email = %s", (email,))
            user = cur.fetchone()

            if user and check_password_hash(user['password'], password):
                # User authenticated successfully
                session['user_id'] = user['user_id']  # Save user_id in the session
                session['username'] = user['username']  # Optional: Save username
                session['fullname'] = user['fullname']  # Optional: Save fullname

                flash(f"Welcome, {user['fullname']}!", "success")
                return redirect(url_for('home'))
            else:
                flash("Invalid email or password.", "danger")
        except Exception as e:
            flash(f"An error occurred during sign-in: {str(e)}", "danger")
        finally:
            cur.close()

    return render_template('signin.html')


# Logout route
@app.route('/signout')
def signout():
    session.pop('user_id', None)  # Remove user session
    session.pop('username', None)  # Remove username
    session.pop('fullname', None)  # Remove fullname
    flash('You have been successfully logged out.', 'success')
    return redirect(url_for('welcome'))


@app.route('/home', methods=['GET', 'POST'])
@login_required
def home():
    user_id = session['user_id']
    username = session['username']
    today_date = datetime.today().strftime('%B %d, %Y')
    request.args.get('storageID')

    cur = mysql.connection.cursor()
    try:
        query_notifications = """
            SELECT i.name, s.name AS storage, 
                   DATEDIFF(i.expiration_date, CURDATE()) AS days_remaining
            FROM items i 
            LEFT JOIN Storage s ON i.storageID = s.storageID
            WHERE i.expiration_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 7 DAY)
              AND i.user_id = %s
            ORDER BY i.expiration_date ASC
        """
        cur = mysql.connection.cursor()
        cur.execute(query_notifications, (user_id,))
        notifications = cur.fetchall()


        cur.execute("SELECT * FROM Storage WHERE user_id = %s", (user_id,))
        storages = cur.fetchall()

            # Get count of items by category for this user
        cur.execute("""
                SELECT c.name, COUNT(i.id) as item_count 
                FROM Category c 
                LEFT JOIN items i ON c.categoryID = i.categoryID AND i.user_id = %s
                WHERE c.user_id = %s
                GROUP BY c.name
            """, (user_id, user_id))
        category_stats = cur.fetchall()

        # Get count of expiring items
        cur.execute("""
            SELECT COUNT(*) as expiring_soon 
            FROM items 
            WHERE user_id = %s AND 
                  expiration_date IS NOT NULL AND 
                  expiration_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 7 DAY)
        """, (user_id,))
        expiring_soon = cur.fetchone()['expiring_soon']

        # Get count of expired items
        cur.execute("""
            SELECT COUNT(*) as expired 
            FROM items 
            WHERE user_id = %s AND 
                  expiration_date IS NOT NULL AND 
                  expiration_date < CURDATE()
        """, (user_id,))
        expired = cur.fetchone()['expired']

        query_storages = """
                SELECT storageID, name 
                FROM Storage 
                WHERE user_id = %s 
                ORDER BY name
            """
        cur.execute(query_storages, (user_id,))
        storages = cur.fetchall()
        storage_id = request.args.get('storageID')
        items_in_storage = []
        if storage_id:
            query_items_in_storage = """
                    SELECT i.*, s.name AS storage, c.name AS category,
                           DATEDIFF(i.expiration_date, CURDATE()) AS days_remaining
                    FROM items i
                    LEFT JOIN Storage s ON i.storageID = s.storageID
                    LEFT JOIN Category c ON i.categoryID = c.categoryID
                    WHERE i.storageID = %s
                    AND i.user_id = %s
                    ORDER BY i.expiration_date ASC
                """
            cur.execute(query_items_in_storage, (storage_id,user_id))
            items_in_storage = cur.fetchall()

    except Exception as e:
        flash(f"An error occurred while fetching data: {str(e)}", "danger")
        storages = []
        category_stats =[
                        ]
        expiring_soon = 0
        expired = 0
        items_in_storage = []
    finally:
        cur.close()

    return render_template('home.html',
                           username=username,
                           today_date=today_date,
                           notifications = notifications,
                           storages=storages,
                           category_stats=category_stats,
                           expiring_soon=expiring_soon,
                           expired=expired,
                           items_in_storage=items_in_storage)


# ITEM LIST
@app.route('/list', methods=['GET', 'POST'])
@login_required
def item_list():
    user_id = session['user_id']
    username = session['username']

    search_query = request.args.get('search', '').strip()
    storage_id = request.args.get('storageID')

    # Create cursor
    cur = mysql.connection.cursor()

    # Get all storages for this user
    query_storages = """
        SELECT storageID, name 
        FROM Storage 
        WHERE user_id = %s 
        ORDER BY name
    """
    cur.execute(query_storages, (user_id,))
    storages = cur.fetchall()

    # Base query for all items
    query = """
        SELECT i.*, s.name AS storage, c.name AS category,
        DATEDIFF(i.expiration_date, CURDATE()) AS days_remaining
        FROM items i
        LEFT JOIN Storage s ON i.storageID = s.storageID
        LEFT JOIN Category c ON i.categoryID = c.categoryID
        WHERE i.user_id = %s
    """
    params = [user_id]

    # Apply search filter if provided
    if search_query:
        query += " AND (LOWER(i.name) LIKE LOWER(%s) OR LOWER(c.name) LIKE LOWER(%s))"
        params.extend([f"%{search_query}%", f"%{search_query}%"])

    query += " ORDER BY i.expiration_date ASC"
    cur.execute(query, params)
    items = cur.fetchall()

    # Filtered storage items (if any storage is selected)
    selected_storage = None
    items_in_storage = []

    if storage_id:
        cur.execute("SELECT storageID, name FROM Storage WHERE storageID = %s AND user_id = %s",
                    (storage_id, user_id))
        selected_storage = cur.fetchone()

        query_items_in_storage = """
            SELECT i.*, s.name AS storage, c.name AS category,
            DATEDIFF(i.expiration_date, CURDATE()) AS days_remaining
            FROM items i
            LEFT JOIN Storage s ON i.storageID = s.storageID
            LEFT JOIN Category c ON i.categoryID = c.categoryID
            WHERE i.storageID = %s AND i.user_id = %s
            ORDER BY i.expiration_date ASC
        """
        cur.execute(query_items_in_storage, (storage_id, user_id))
        items_in_storage = cur.fetchall()

    # Close cursor
    cur.close()

    return render_template('list.html',
                           username=username,
                           storages=storages,
                           selected_storage=selected_storage,
                           items_in_storage=items_in_storage,
                           items=items)



# Make sure these routes accept both GET and POST methods
@app.route('/addItem', methods=['GET', 'POST'])
@login_required
def add_item():
    user_id = session['user_id']

    if request.method == 'POST':
        name = request.form.get('name')
        storageID = request.form.get('storageID')
        categoryID = request.form.get('categoryID')
        manufactured_date = request.form.get('manufactured_date')
        expiration_date = request.form.get('expiration_date')
        notes = request.form.get('notes')


        # Verify storage and category belong to the user
        cur = mysql.connection.cursor()

        # Check if the selected storage belongs to the user
        cur.execute("SELECT storageID FROM Storage WHERE storageID = %s AND user_id = %s",
                    (storageID, user_id))
        storage = cur.fetchone()

        # Check if the selected category belongs to the user
        cur.execute("SELECT categoryID FROM Category WHERE categoryID = %s AND user_id = %s",
                    (categoryID, user_id))
        category = cur.fetchone()

        if not storage or not category:
            flash('Invalid storage or category selected', 'danger')
            return redirect(url_for('add_item'))

        # Insert item with user_id
        cur.execute("""INSERT INTO items (name, storageID, categoryID, manufactured_date, expiration_date, notes, user_id)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (name, storageID, categoryID, manufactured_date, expiration_date, notes, user_id))
        mysql.connection.commit()
        cur.close()

        flash('Item added successfully!', 'success')
        return redirect(url_for('item_list'))

    # Get user's storages and categories for the dropdown menus
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM Storage WHERE user_id = %s", (user_id,))
    storages = cur.fetchall()

    cur.execute("SELECT * FROM Category WHERE user_id = %s", (user_id,))
    categories = cur.fetchall()
    cur.close()

    return render_template('add_item.html',
                           username=session['username'],
                           storages=storages,
                           categories=categories)


@app.route('/addStorage', methods=['GET', 'POST'])
@login_required
def add_storage():
    user_id = session['user_id']

    if request.method == 'POST':
        storage_name = request.form.get('storage')
        file = request.files.get('file')
        photo_path = None

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid4().hex}_{filename}"
            upload_path = os.path.join(current_app.root_path, 'static/uploads', unique_filename)
            os.makedirs(os.path.dirname(upload_path), exist_ok=True)
            file.save(upload_path)
            photo_path = f'static/uploads/{unique_filename}'  # ✅ Correct path

        print("PHOTO PATH SAVED TO DB:", photo_path)  # Debug log

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO Storage (name, user_id, photo) VALUES (%s, %s, %s)",
                    (storage_name, user_id, photo_path))
        mysql.connection.commit()
        cur.close()

        flash('Storage added successfully!', 'success')
        return redirect(url_for('home'))

    return render_template('add_storage.html',
                           username=session['username'])



@app.route('/addCategory', methods=['GET', 'POST'])
@login_required
def add_category():
    user_id = session['user_id']

    if request.method == 'POST':
        category_name = request.form.get('category')

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO Category (name, user_id) VALUES (%s, %s)",
                    [category_name, user_id])
        mysql.connection.commit()
        cur.close()

        flash('Category added successfully!', 'success')
        return redirect(url_for('home'))

    return render_template('add_category.html',
                           username=session['username']
                           )


# Edit Item
@app.route('/edit/<int:item_id>', methods=['GET', 'POST'])
@login_required
def edit_item(item_id):
    user_id = session['user_id']

    # Verify the item belongs to the user
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM items WHERE id = %s AND user_id = %s",
                (item_id, user_id))
    item = cur.fetchone()

    if not item:
        flash("Item not found or you don't have permission to edit it", "danger")
        return redirect(url_for('item_list'))

    if request.method == 'POST':
        name = request.form.get('name')
        storage_id = request.form.get('storageID')
        category_id = request.form.get('categoryID')
        manufactured_date = request.form.get('manufactured_date')
        expiration_date = request.form.get('expiration_date')
        notes = request.form.get('notes')

        if not name or not storage_id or not category_id:
            flash("All fields are required.", "danger")
            return redirect(f'/edit/{item_id}')

        # Verify storage and category belong to the user
        cur.execute("SELECT storageID FROM Storage WHERE storageID = %s AND user_id = %s",
                    (storage_id, user_id))
        storage = cur.fetchone()

        cur.execute("SELECT categoryID FROM Category WHERE categoryID = %s AND user_id = %s",
                    (category_id, user_id))
        category = cur.fetchone()

        if not storage or not category:
            flash('Invalid storage or category selected', 'danger')
            return redirect(f'/edit/{item_id}')

        try:
            cur.execute("""
                UPDATE items 
                SET name = %s, storageID = %s, categoryID = %s, 
                    manufactured_date = %s, expiration_date = %s, notes = %s
                WHERE id = %s AND user_id = %s
            """, (name, storage_id, category_id, manufactured_date, expiration_date, notes, item_id, user_id))
            mysql.connection.commit()

            flash("Item updated successfully!", "success")
            return redirect(url_for('item_list'))
        except Exception as e:
            flash(f"An error occurred: {str(e)}", "danger")
            return redirect(f'/edit/{item_id}')

    # Get user's storages and categories for the form
    cur.execute("SELECT * FROM Storage WHERE user_id = %s", (user_id,))
    storages = cur.fetchall()

    cur.execute("SELECT * FROM Category WHERE user_id = %s", (user_id,))
    categories = cur.fetchall()
    cur.close()

    return render_template('edit_item.html',
                           username=session['username'],
                           item=item,
                           storages=storages,
                           categories=categories)


# Delete Item
@app.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_item(id):
    user_id = session['user_id']

    cur = mysql.connection.cursor()
    # First verify the item belongs to the user
    cur.execute("SELECT id FROM items WHERE id = %s AND user_id = %s",
                (id, user_id))
    item = cur.fetchone()

    if not item:
        flash("Item not found or you don't have permission to delete it", "danger")
        return redirect(url_for('item_list'))

    cur.execute("DELETE FROM items WHERE id = %s AND user_id = %s",
                [id, user_id])
    mysql.connection.commit()
    cur.close()

    flash('Item deleted successfully', 'success')
    return redirect(url_for('item_list'))


@app.route('/editStorage/<int:storage_id>', methods=['GET', 'POST'])
@login_required
def edit_storage(storage_id):
    user_id = session['user_id']

    # Verify the storage belongs to the user
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM Storage WHERE storageID = %s AND user_id = %s",
                (storage_id, user_id))
    storage = cur.fetchone()

    if not storage:
        flash("Storage not found or you don't have permission to edit it", "danger")
        return redirect(url_for('home'))  # Assuming there's a storage_list route

    if request.method == 'POST':
        name = request.form.get('name')


        try:
            # Update storage details
            cur.execute("""
                UPDATE Storage 
                SET name = %s
                WHERE storageID = %s AND user_id = %s
            """, (name, storage_id, user_id))
            mysql.connection.commit()

            flash("Storage updated successfully!", "success")
            return redirect(url_for('home'))  # Redirect to the storage list page after successful update
        except Exception as e:
            flash(f"An error occurred: {str(e)}", "danger")
            return redirect(f'/editStorage/{storage_id}')

    # Get the user's storage data for the form
    cur.execute("SELECT * FROM Storage WHERE user_id = %s", (user_id,))
    storages = cur.fetchall()
    cur.close()

    return render_template('edit_storage.html',
                           username=session['username'],
                           storage=storage,
                           storages=storages)



@app.route('/deleteStorage/<int:storageID>', methods=['GET', 'POST'])
def delete_storage(storageID):
    user_id = session['user_id']

    cur = mysql.connection.cursor()
    # First verify the item belongs to the user
    cur.execute("SELECT storage.storageID FROM storage WHERE storageID = %s AND user_id = %s",
                (storageID, user_id))
    item = cur.fetchone()

    if not item:
        flash("Item not found or you don't have permission to delete it", "danger")
        return redirect(url_for('item_list'))

    cur.execute("DELETE FROM storage WHERE storageID = %s AND user_id = %s",
                [storageID, user_id])
    mysql.connection.commit()
    cur.close()

    flash('Storage deleted successfully', 'success')
    return redirect(url_for('home'))
@app.route('/about', methods=['GET', 'POST'])
@login_required
def about():
    user_id = session['user_id']
    username = session['username']
    today_date = datetime.today().strftime('%B %d, %Y')

    return render_template('about.html',
                    user_id=user_id,
                    username=username,
                    today_date=today_date)

@app.route('/education', methods=['GET', 'POST'])
@login_required
def education():
    user_id = session['user_id']
    username = session['username']
    today_date = datetime.today().strftime('%B %d, %Y')

    return render_template('education.html',
                           user_id=user_id,
                           username=username,
                           today_date=today_date)

if __name__ == '__main__':
    app.run(debug=True)