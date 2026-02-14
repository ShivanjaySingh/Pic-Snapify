# pip install flask
from flask import Flask, render_template, redirect, url_for, request, flash, session, json, jsonify, current_app, abort, send_file
# pip install flask-mysqldb
from flask_mysqldb import MySQL
import MySQLdb.cursors
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os
from werkzeug.utils import secure_filename
import uuid
from io import BytesIO
import zipfile
from datetime import date, timedelta
import cleanup_expired_gallery




# pip install instamojo-wrapper
import instamojo_service # This is the module i created for Instamojo payment integration


app =Flask(__name__)

# Secret Key is very important for session management and flash messages
app.secret_key = "tyu653azedr3wyhv!554"

# MySQL configurations
app.config['MYSQL_HOST'] = 'database-1.c9qaeokiumh0.eu-north-1.rds.amazonaws.com'
app.config['MYSQL_USER'] = 'admin'               
app.config['MYSQL_PASSWORD'] = 'AmazonDatabase2003'   
app.config['MYSQL_DB']  = 'PicSnapifyDB'   

# ADD THIS LINE FOR SSL
app.config['MYSQL_CUSTOM_OPTIONS'] = {"ssl": {"ca": "/etc/mysql/certs/global-bundle.pem"}}

mysql = MySQL(app)

# File upload configuration for studio portfolio photos
UPLOAD_FOLDER = os.path.join('static', 'uploads', 'studio', 'portfolio')

# File upload configuration for galleries
UPLOAD_FOLDER = 'static/uploads/galleries'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

# ✅ Ensure directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def home():
    return render_template("website/index.html")

@app.route('/features')
def features():
    return render_template("website/features.html")

@app.route('/how-it-works')
def how_it_works():
    return render_template("website/how-it-works.html")

@app.route('/pricing')
def pricing():
    return render_template("website/pricing.html")

@app.route('/contact')
def contact():
    return render_template('website/contact.html')

@app.route('/privacy-policy')
def privacy_policy():
    return render_template('studio/privacy_policy.html')

@app.route('/terms-and-conditions')
def terms_condition():
    return render_template('studio/terms&condition.html')

# ✅
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Common fields
        role = request.form.get('role')
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')

        # Studio fields (optional)
        studio_name = request.form.get('studio_name')
        city = request.form.get('city')
        address = request.form.get('address')
        website = request.form.get('website')

        # Basic validation
        if not role or not name or not email or not password:
            flash('Please fill all required fields', 'danger')
            return redirect(url_for('register'))

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Check if email already exists
        cursor.execute("SELECT id FROM users WHERE email=%s", (email,))
        existing_user = cursor.fetchone()

        if existing_user:
            flash('Email already registered. Please login.', 'warning')
            cursor.close()
            return redirect(url_for('login'))

        # Hash password
        hashed_password = generate_password_hash(password)

        # Insert user
        cursor.execute("""
            INSERT INTO users (name, email, phone, password, role)
            VALUES (%s, %s, %s, %s, %s)
        """, (name, email, phone, hashed_password, role))

        mysql.connection.commit()
        user_id = cursor.lastrowid

        # If user is a studio owner, create studio entry
        if role == 'studio':
            cursor.execute("""
                INSERT INTO studios (user_id, studio_name, city, address, website)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, studio_name, city, address, website))

            mysql.connection.commit()

        cursor.close()

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('website/registration.html')

# ✅
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
            flash('Please enter email and password', 'danger')
            return redirect(url_for('login'))

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()
        cursor.close()

        if user and check_password_hash(user['password'], password):
            # SESSION CREATION
            session.clear()
            session['loggedin'] = True
            session['user_id'] = user['id']
            session['name'] = user['name']
            session['email'] = user['email']
            session['role'] = user['role']

            flash('Login successful!', 'success')

            # ROLE BASED REDIRECT
            if user['role'] == 'admin':
                return redirect('/admin/dashboard')
            elif user['role'] == 'studio':
                return redirect('/studio/dashboard')
            elif user['role'] == 'client':
                return redirect('/browse')

        flash('Invalid email or password', 'danger')
        return redirect(url_for('login'))

    return render_template('website/login.html')

# ✅
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'loggedin' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ✅
@app.route('/logout') 
def logout():
    session.clear()
    flash('You have been logged out', 'success')
    return redirect(url_for('login'))

# Helper function to get studio ID ✅
def get_studio_id(cursor):
    cursor.execute(
        "SELECT id FROM studios WHERE user_id=%s",
        (session['user_id'],)
    )
    studio = cursor.fetchone()
    return studio['id'] if studio else None


# ------------------------------------- Admin Panel Starts --------------------------------------------------

@app.route('/admin/login', methods=['GET','POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM admins WHERE email=%s", (email,))
        admin = cursor.fetchone()

        if admin and check_password_hash(admin['password'], password):
            session['admin_loggedin'] = True
            session['admin_id'] = admin['id']
            session['admin_name'] = admin['name']
            return redirect('/admin/dashboard')

        return "Invalid credentials"

    return render_template('admin/admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect('/admin/login')


@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_loggedin'):
        return redirect('/admin/login')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("SELECT COUNT(*) total FROM studios")
    studios = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) total FROM studio_subscriptions WHERE status='active'")
    active_subs = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) total FROM payments WHERE status='success'")
    payments = cursor.fetchone()['total']

    return render_template(
        'admin/dashboard.html',
        studios=studios,
        active_subs=active_subs,
        payments=payments,
        current_year=date.today().year
    )

@app.route('/admin/add', methods=['GET','POST'])
def admin_add():
    if not session.get('admin_loggedin'):
        return redirect('/admin/login')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':
        cursor.execute("""
            INSERT INTO admins (name, phone, email, password)
            VALUES (%s, %s, %s, %s)
        """, (
            request.form['name'],
            request.form['phone'],
            request.form['email'],
            generate_password_hash(request.form['password'])
        ))
        mysql.connection.commit()
        return redirect('/admin/add')

    # FETCH ADMINS
    cursor.execute("SELECT id, name, phone, email, created_at FROM admins ORDER BY id DESC")
    admins = cursor.fetchall()

    return render_template(
        "admin/admin_add.html",
        admins=admins,
        current_year=date.today().year
    )

@app.route('/admin/users')
def admin_users():
    if not session.get('admin_loggedin'):
        return redirect('/admin/login')

    role = request.args.get('role', '')
    search = request.args.get('search', '')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    query = "SELECT * FROM users WHERE 1=1"
    params = []

    if role:
        query += " AND role = %s"
        params.append(role)

    if search:
        query += " AND (name LIKE %s OR email LIKE %s OR phone LIKE %s)"
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

    query += " ORDER BY id DESC"

    cursor.execute(query, params)
    users = cursor.fetchall()

    return render_template(
        "admin/users.html",
        users=users,
        selected_role=role,
        search_query=search
    )


@app.route('/admin/studios')
def admin_studios():
    if not session.get('admin_loggedin'):
        return redirect('/admin/login')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('''SELECT s.*, u.*
                    FROM studios s
                    JOIN users u ON s.user_id = u.id;
                    ''')
    studios = cursor.fetchall()

    return render_template(
        "admin/admin_studios.html",
        studios=studios,
        current_year=date.today().year
    )

@app.route('/admin/studio/toggle/<int:id>')
def toggle_studio(id):
    cursor = mysql.connection.cursor()
    cursor.execute("""
        UPDATE studios
        SET is_approved = IF(is_approved = 1, 0, 1)
        WHERE id = %s
    """, (id,))
    mysql.connection.commit()
    cursor.close()
    return redirect('/admin/studios')


@app.route('/admin/plans', methods=['GET','POST'])
def admin_plans():
    if not session.get('admin_loggedin'):
        return redirect('/admin/login')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':
        cursor.execute("""
            INSERT INTO subscription_plans (name, price, duration_days, max_galleries, max_storage_gb)
            VALUES (%s,%s,%s,%s,%s)
        """, (
            request.form['name'],
            request.form['price'],
            request.form['days'],
            request.form['max_gallery'],
            request.form['max_storage']
        ))
        mysql.connection.commit()

    cursor.execute("SELECT * FROM subscription_plans ORDER BY id Asc")
    plans = cursor.fetchall()

    return render_template(
        "admin/admin_plans.html",
        plans=plans,
        current_year=date.today().year
    )

@app.route('/admin/plans/delete/<int:id>')
def admin_delete_plan(id):
    cursor = mysql.connection.cursor()
    cursor.execute('Delete From subscription_plans where id=%s',(id,))
    mysql.connection.commit()
    cursor.close()
    return redirect(request.referrer)

@app.route('/admin/plans/edit', methods=['POST'])
def edit_plan():
    cursor = mysql.connection.cursor()
    cursor.execute("""
        UPDATE subscription_plans
        SET name=%s, price=%s, duration_days=%s,
            max_galleries=%s, max_storage_gb=%s
        WHERE id=%s
    """, (
        request.form['name'],
        request.form['price'],
        request.form['days'],
        request.form['max_gallery'],
        request.form['max_storage'],
        request.form['id']
    ))
    mysql.connection.commit()
    return redirect('/admin/plans')


@app.route('/admin/payments')
def admin_payments():
    if not session.get('admin_loggedin'):
        return redirect('/admin/login')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        SELECT p.*, s.studio_name, sp.name AS plan_name
        FROM payments p
        JOIN studios s ON s.id = p.studio_id
        JOIN subscription_plans sp ON sp.id = p.plan_id
        ORDER BY p.created_at DESC
    """)
    payments = cursor.fetchall()

    return render_template(
        "admin/admin_payments.html",
        payments=payments,
        current_year=date.today().year
    )

@app.route('/admin/contact-requests')
def admin_contact_requests():
    if not session.get('admin_loggedin'):
        return redirect('/admin/login')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        SELECT id, name, email, subject, message, created_at
        FROM contact_messages
        ORDER BY id DESC
    """)
    requests = cursor.fetchall()

    return render_template(
        'admin/contact_requests.html',
        requests=requests,
        current_year=date.today().year
    )


# ------------------------------------- Studio --------------------------------------------------

# Studio Logout Page
@app.route('/studio/logout')
@login_required
def studio_logout():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    studio_id = get_studio_id(cursor)
    if not studio_id:
        return redirect('/studio/profile')

    # Fetch Studio Photos
    cursor.execute("""
                SELECT *
                FROM studio_photos
                WHERE studio_id = %s And is_home_photo=True
            """, (studio_id,))
    portfolio_photos = cursor.fetchall()
    return render_template('studio/logout.html', portfolio_photos=portfolio_photos)

# Studio Dashboard✅
@app.route('/studio/dashboard')
@login_required
def studio_dashboard():

    # Ensure only studio can access
    if session.get('role') != 'studio':
        return redirect('/login')

    user_id = session['user_id']

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # 1️⃣ Studio info
    cursor.execute("""
        SELECT s.*, u.name AS owner_name
        FROM studios s
        JOIN users u ON u.id = s.user_id
        WHERE s.user_id = %s
    """, (user_id,))
    studio = cursor.fetchone()

    if not studio:
        return redirect('/studio/profile')

    studio_id = studio['id']

    # 2️⃣ Services
    cursor.execute("""
        SELECT id, service_name, price
        FROM studio_services
        WHERE studio_id = %s
        ORDER BY id DESC
    """, (studio_id,))
    studio['services'] = cursor.fetchall()

    # 3️⃣ Recent bookings (FIXED)
    cursor.execute("""
        SELECT 
            b.id,
            b.booking_date,
            b.booking_time,
            b.status,
            u.name AS client_name,
            GROUP_CONCAT(ss.service_name SEPARATOR ', ') AS services
        FROM bookings b
        JOIN users u ON u.id = b.client_id
        JOIN booking_services bs ON bs.booking_id = b.id
        JOIN studio_services ss ON ss.id = bs.service_id
        WHERE b.studio_id = %s
        GROUP BY b.id
        ORDER BY b.id DESC
        LIMIT 5
    """, (studio_id,))
    bookings = cursor.fetchall()

    # 4️⃣ Stats
    cursor.execute(
        "SELECT COUNT(*) AS total FROM bookings WHERE studio_id=%s",
        (studio_id,)
    )
    total_bookings = cursor.fetchone()['total']

    cursor.execute("""
        SELECT COUNT(*) AS total 
        FROM enquiries 
        WHERE studio_id=%s AND status='pending'
    """, (studio_id,))
    pending_enquiries = cursor.fetchone()['total']

    # Fetch Studio Photos
    cursor.execute("""
                SELECT *
                FROM studio_photos
                WHERE studio_id = %s And is_home_photo=True
            """, (studio['id'],))
    portfolio_photos = cursor.fetchall()

    cursor.close()

    return render_template(
        'studio/dashboard.html',
        studio=studio,
        bookings=bookings,
        total_bookings=total_bookings,
        pending_enquiries=pending_enquiries,
        portfolio_photos=portfolio_photos
    )

# Studio Profile View ✅
@app.route('/studio/profile')
@login_required
def studio_profile():
    if 'user_id' not in session or session.get('role') != 'studio':
        return redirect('/login')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Fetch studio + user details
    cursor.execute("""
        SELECT 
            s.*,
            u.name AS owner_name,
            u.email,
            u.phone
        FROM studios s
        JOIN users u ON u.id = s.user_id
        WHERE s.user_id = %s
    """, (session['user_id'],))
    studio = cursor.fetchone()

    # Fetch portfolio photos
    cursor.execute("""
        SELECT * FROM studio_photos
        WHERE studio_id = %s
        ORDER BY uploaded_at DESC
    """, (studio['id'],))
    photos = cursor.fetchall()

    # Fetch Studio Photos
    cursor.execute("""
                SELECT *
                FROM studio_photos
                WHERE studio_id = %s And is_home_photo=True
            """, (studio['id'],))
    portfolio_photos = cursor.fetchall()

    cursor.close()

    return render_template(
        'studio/profile.html',
        studio=studio,
        photos=photos,
        portfolio_photos=portfolio_photos
    )

# Studio Profile Update ✅
@app.route('/studio/profile/update', methods=['POST'])
@login_required
def update_studio_profile():
    if 'user_id' not in session:
        return redirect('/login')

    owner_name = request.form['owner_name']
    email = request.form['email']
    phone = request.form['phone']
    city = request.form['city']
    address = request.form['address']
    description = request.form['description']

    cursor = mysql.connection.cursor()

    # Update users table
    cursor.execute("""
        UPDATE users
        SET name=%s, email=%s, phone=%s
        WHERE id=%s
    """, (owner_name, email, phone, session['user_id']))

    # Update studios table
    cursor.execute("""
        UPDATE studios
        SET city=%s, address=%s, description=%s
        WHERE user_id=%s
    """, (city, address, description, session['user_id']))

    mysql.connection.commit()
    return redirect('/studio/profile')

# Studio Profile Photo Upload ✅
@app.route('/studio/profile-photo/upload', methods=['POST'])
@login_required
def upload_profile_photo():
    if 'user_id' not in session:
        return redirect('/login')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Get studio
    cursor.execute(
        "SELECT id FROM studios WHERE user_id=%s",
        (session['user_id'],)
    )
    studio = cursor.fetchone()

    if not studio:
        return redirect('/studio/profile')

    file = request.files.get('profile_photo')
    if not file or file.filename == '':
        return redirect('/studio/profile')

    # Upload folder
    UPLOAD_FOLDER = os.path.join('static', 'uploads', 'studio', 'profile')
    absolute_upload_dir = os.path.join(current_app.root_path, UPLOAD_FOLDER)
    os.makedirs(absolute_upload_dir, exist_ok=True)

    # Unique filename
    ext = file.filename.rsplit('.', 1)[-1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"

    relative_path = os.path.join(UPLOAD_FOLDER, filename)
    absolute_path = os.path.join(absolute_upload_dir, filename)

    # 🔥 Delete old profile photo (DB + file)
    cursor.execute("""
        SELECT file_path FROM studio_photos
        WHERE studio_id=%s AND is_home_photo=1
    """, (studio['id'],))
    old = cursor.fetchone()

    if old:
        old_file = os.path.join(current_app.root_path, old['file_path'])
        if os.path.exists(old_file):
            os.remove(old_file)

        cursor.execute("""
            DELETE FROM studio_photos
            WHERE studio_id=%s AND is_home_photo=1
        """, (studio['id'],))

    # Save new file
    file.save(absolute_path)

    # Insert as PROFILE photo
    cursor.execute("""
        INSERT INTO studio_photos
        (studio_id, file_path, is_home_photo)
        VALUES (%s, %s, %s)
    """, (
        studio['id'],
        relative_path.replace(os.sep, '/'),
        True
    ))

    mysql.connection.commit()
    return redirect('/studio/profile')

# Studio Portfolio Images Upload ✅
@app.route('/studio/portfolio/upload', methods=['POST'])
@login_required
def upload_portfolio():
    if 'user_id' not in session:
        return redirect('/login')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute(
        "SELECT id FROM studios WHERE user_id=%s",
        (session['user_id'],)
    )
    studio = cursor.fetchone()

    if not studio:
        return redirect('/studio/profile')

    files = request.files.getlist('photos[]')

    if not files:
        flash("No files selected", "error")
        return redirect('/studio/profile')

    for file in files:
        if file and file.filename:
            ext = file.filename.rsplit('.', 1)[-1].lower()
            filename = f"{uuid.uuid4().hex}.{ext}"

            # relative path (store in DB)
            relative_path = os.path.join(UPLOAD_FOLDER, filename)

            # absolute path (save file)
            absolute_path = os.path.join(
                current_app.root_path,
                relative_path
            )

            # ✅ DOUBLE SAFETY: ensure folder exists
            os.makedirs(os.path.dirname(absolute_path), exist_ok=True)

            file.save(absolute_path)

            cursor.execute("""
                INSERT INTO studio_photos (studio_id, file_path)
                VALUES (%s, %s)
            """, (
                studio['id'],
                relative_path.replace(os.sep, '/')
            ))

    mysql.connection.commit()
    flash("Portfolio images uploaded successfully!", "success")
    return redirect('/studio/profile')

# Studio Portfolio Image Delete ✅
@app.route('/studio/portfolio/delete/<int:photo_id>')
@login_required
@login_required
def delete_portfolio_photo(photo_id):

    user_id = session['user_id']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT sp.file_path
        FROM studio_photos sp
        JOIN studios s ON s.id = sp.studio_id
        WHERE sp.id=%s AND s.user_id=%s
    """, (photo_id, user_id))

    photo = cursor.fetchone()

    if photo:
        # delete file
        if os.path.exists(photo['file_path']):
            os.remove(photo['file_path'])

        cursor.execute("DELETE FROM studio_photos WHERE id=%s", (photo_id,))
        mysql.connection.commit()

    cursor.close()
    return redirect('/studio/profile')

# Studio Services View ✅
@app.route('/studio/services')
@login_required
def studio_services():
    if 'user_id' not in session:
        return redirect('/login')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute(
        "SELECT id FROM studios WHERE user_id=%s",
        (session['user_id'],)
    )
    studio = cursor.fetchone()
    if not studio:
        return redirect('/studio/dashboard')

    cursor.execute(
        "SELECT * FROM studio_services WHERE studio_id=%s ORDER BY id DESC",
        (studio['id'],)
    )
    services = cursor.fetchall()

    return render_template(
        'studio/services.html',
        services=services
    )

# Studio Service Add ✅
@app.route('/studio/services/add', methods=['POST'])
@login_required
def add_service():

    if session.get('role') != 'studio':
        return redirect('/login')

    name = request.form['name']
    price = request.form['price']
    description = request.form['description']
    user_id = session['user_id']

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("SELECT id FROM studios WHERE user_id=%s", (user_id,))
    studio = cursor.fetchone()

    if not studio:
        return redirect('/studio/dashboard')

    cursor.execute("""
        INSERT INTO studio_services (studio_id, service_name, price, description)
        VALUES (%s, %s, %s, %s)
    """, (studio['id'], name, price, description))

    mysql.connection.commit()
    cursor.close()

    # ✅ Redirect user back to the page they came from
    return redirect(request.referrer)

# Studio Service Edit ✅
@app.route('/studio/services/update', methods=['POST'])
def update_service():
    if 'user_id' not in session:
        return redirect('/login')

    service_id = request.form['id']
    name = request.form['name']
    price = request.form['price']
    description = request.form.get('description')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        UPDATE studio_services ss
        JOIN studios s ON ss.studio_id = s.id
        SET ss.service_name=%s,
            ss.price=%s,
            ss.description=%s
        WHERE ss.id=%s AND s.user_id=%s
    """, (
        name,
        price,
        description,
        service_id,
        session['user_id']
    ))

    mysql.connection.commit()
    return redirect(request.referrer)

# Studio Service Delete ✅
@app.route('/studio/services/delete/<int:service_id>')
@login_required
def delete_service(service_id):

    user_id = session['user_id']

    cursor = mysql.connection.cursor()
    cursor.execute("""
        DELETE s FROM studio_services s
        JOIN studios st ON st.id = s.studio_id
        WHERE s.id=%s AND st.user_id=%s
    """, (service_id, user_id))

    mysql.connection.commit()
    cursor.close()

    return redirect(request.referrer)

# Studio Bookings View ✅
@app.route('/studio/bookings')
@login_required
def studio_bookings():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    studio_id = get_studio_id(cursor)
    if not studio_id:
        return redirect('/studio/profile')

    # Platform bookings (MULTI SERVICE)
    cursor.execute("""
                    SELECT 
                        b.id,
                        b.booking_date,
                        b.booking_time,
                        b.status,
                        u.name AS client_name,
                        GROUP_CONCAT(s.service_name SEPARATOR ', ') AS services
                    FROM bookings b
                    JOIN users u ON b.client_id = u.id
                    JOIN booking_services bs ON b.id = bs.booking_id
                    JOIN studio_services s ON bs.service_id = s.id
                    WHERE b.studio_id = %s
                    GROUP BY b.id
                    ORDER BY b.booking_date DESC
                """, (studio_id,))
    platform_bookings = cursor.fetchall()

    # External bookings
    cursor.execute("""
        SELECT *
        FROM external_bookings
        WHERE studio_id = %s
        ORDER BY booking_date DESC
    """, (studio_id,))
    external_bookings = cursor.fetchall()

    return render_template(
        'studio/bookings.html',
        platform_bookings=platform_bookings,
        external_bookings=external_bookings
    )

# Booking Confirm ✅
@app.route('/studio/bookings/confirm/<int:booking_id>')
@login_required
def confirm_booking(booking_id):
    if session.get('role') != 'studio':
        return redirect('/login')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    studio_id = get_studio_id(cursor)

    cursor.execute("""
        UPDATE bookings
        SET status = 'confirmed'
        WHERE id = %s AND studio_id = %s AND status = 'pending'
    """, (booking_id, studio_id))

    mysql.connection.commit()
    cursor.close()

    return redirect('/studio/bookings')


# Booking Reject ✅
@app.route('/studio/bookings/cancel/<int:booking_id>')
@login_required
def reject_booking(booking_id):
    if session.get('role') != 'studio':
        return redirect('/login')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    studio_id = get_studio_id(cursor)

    cursor.execute("""
        UPDATE bookings
        SET status = 'rejected'
        WHERE id = %s AND studio_id = %s AND status = 'pending'
    """, (booking_id, studio_id))

    mysql.connection.commit()
    cursor.close()

    return redirect('/studio/bookings')


# External Bookings View ✅
@app.route('/studio/bookings/external')
@login_required
def external_bookings():
    # studio_id = session['studio_id']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    studio_id = get_studio_id(cursor)
    if not studio_id:
        return redirect('/studio/profile')

    cursor.execute("""
        SELECT *
        FROM external_bookings
        WHERE studio_id = %s
        ORDER BY booking_date DESC
    """, (studio_id,))
    external_bookings = cursor.fetchall()

    return render_template('studio/external_bookings.html', external_bookings=external_bookings)

# External Booking Add ✅
@app.route('/studio/bookings/external/add', methods=['POST'])
@login_required
def add_external_booking():

    # studio_id = session['studio_id']
    data = request.form
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    studio_id = get_studio_id(cursor)
    if not studio_id:
        return redirect('/studio/profile')

    cursor.execute("""
        INSERT INTO external_bookings
        (studio_id, client_name, client_phone, client_email, service_name,
         booking_date, booking_time, price, notes)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s, %s)
    """, (
        studio_id,
        data['client_name'],
        data.get('client_phone'),
        data.get('client_mail'),
        data.get('service_name'),
        data['booking_date'],
        data.get('booking_time'),
        data.get('price'),
        data.get('notes')
    ))

    mysql.connection.commit()
    return redirect('/studio/bookings')

# Booking Status Update ❌ (Don't Know what is this for exactly)
@app.route('/studio/bookings/update/<int:booking_id>/<status>')
def update_booking_status(booking_id, status):
    if 'user_id' not in session:
        return redirect('/login')
    
    if status not in ['pending', 'confirmed', 'cancelled']:
        return redirect('/studio/bookings')
    
    cursor = mysql.connection.cursor()
    
    # Ensure the booking belongs to the logged-in studio
    cursor.execute("""
        UPDATE bookings b
        JOIN studios s ON b.studio_id = s.id
        SET b.status=%s
        WHERE b.id=%s AND s.user_id=%s
    """, (status, booking_id, session['user_id']))
    
    mysql.connection.commit()
    return redirect('/studio/bookings')

# View booking invoice
@app.route('/studio/bookings/invoice/<int:booking_id>')
@login_required
def studio_booking_invoice(booking_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Booking + Client
    cursor.execute("""
        SELECT 
            b.id,
            b.booking_date,
            b.advance_paid,
            b.studio_id,
            u.name  AS client_name,
            u.phone AS client_phone,
            u.email AS client_email
        FROM bookings b
        JOIN users u ON u.id = b.client_id
        WHERE b.id = %s
    """, (booking_id,))
    booking = cursor.fetchone()

    if not booking:
        cursor.close()
        abort(404)

    # Services
    cursor.execute("""
        SELECT s.service_name, s.price
        FROM booking_services bs
        JOIN studio_services s ON s.id = bs.service_id
        WHERE bs.booking_id = %s
    """, (booking_id,))
    services = cursor.fetchall()

    # ✅ TOTAL CALCULATION (IMPORTANT FIX)
    total = sum(s['price'] for s in services)
    advance = booking['advance_paid'] or 0
    balance = total - advance

    # Studio details
    cursor.execute("""
        SELECT 
            s.studio_name,
            s.city,
            u.phone AS studio_phone,
            u.email AS studio_email
        FROM studios s
        JOIN users u ON u.id = s.user_id
        WHERE s.id = %s
    """, (booking['studio_id'],))
    studio = cursor.fetchone()

    cursor.close()

    return render_template(
        'studio/invoice.html',
        booking=booking,
        services=services,
        studio=studio,
        total=total,
        balance=balance
    )


# Studio Clients View ✅
@app.route('/studio/clients')
@login_required
def studio_clients():

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    studio_id = get_studio_id(cursor)
    if not studio_id:
        return redirect('/studio/profile')
    cursor.execute("""
        SELECT c.id, u.name, u.email, c.created_at
        FROM clients c
        JOIN users u ON u.id = c.user_id
        WHERE c.studio_id = %s
        ORDER BY c.created_at DESC
    """, (studio_id,))
    
    clients = cursor.fetchall()

        # Fetch Studio Photos
    cursor.execute("""
                SELECT *
                FROM studio_photos
                WHERE studio_id = %s And is_home_photo=True
            """, (studio_id,))
    portfolio_photos = cursor.fetchall()
    cursor.close()

    return render_template('studio/clients.html', clients=clients, portfolio_photos=portfolio_photos)

# @app.route('/studio/gallery/<int:gallery_id>/photos')
# @login_required
# def studio_client_gallery_photos(gallery_id):
    # studio auth check
    # fetch gallery images
    return render_template('studio/gallery_photos.html', ...)


# Studio Contact Requests View ✅
@app.route('/studio/contact-requests')
@login_required
def studio_contact_requests():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    # Get studio_id from session
    studio_id = get_studio_id(cursor)
    if not studio_id:
        return redirect('/studio/profile')
    
    cursor.execute("""
        SELECT e.*, u.name AS client_name, u.email AS client_email, u.phone AS client_phone
        FROM users u
        JOIN enquiries e ON u.id = e.client_id
        WHERE studio_id = %s
        ORDER BY created_at DESC
    """, (studio_id,))

    enquiries = cursor.fetchall()

        # Fetch Studio Photos
    cursor.execute("""
                SELECT *
                FROM studio_photos
                WHERE studio_id = %s And is_home_photo=True
            """, (studio_id,))
    portfolio_photos = cursor.fetchall()
    cursor.close()

    return render_template(
        'studio/contact_request.html',
        enquiries=enquiries,
        portfolio_photos=portfolio_photos
    )

# ------------------------------------- Studio Galleries --------------------------------------------------

# Studio Photo Management - Galleries
@app.route('/studio/gallery-management')
@login_required
def studio_photo_management():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    studio_id = get_studio_id(cursor)
    if not studio_id:
        return redirect('/studio/profile')

    cursor.execute("""
        SELECT 
            g.id,
            g.title,
            g.password,
            g.is_download_enabled,
            u.name AS client_name,
            g.created_at
        FROM galleries g
        JOIN clients c ON g.client_id = c.id
        JOIN users u ON c.user_id = u.id
        WHERE g.studio_id = %s
        ORDER BY g.created_at DESC
    """, (studio_id,))

    galleries = cursor.fetchall()
    cursor.close()

    return render_template(
        'studio/gallery_management.html',
        galleries=galleries
    )

# --------------------------------------Subscription BAsed Code Start --------------------------------------------
# Check for subscribtions
def subscription_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):

        user_id = session.get('user_id')
        role = session.get('role')

        if not user_id or role != 'studio':
            return redirect('/login')

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Get studio_id using user_id
        cursor.execute("""
            SELECT id
            FROM studios
            WHERE user_id = %s
        """, (user_id,))
        studio = cursor.fetchone()

        if not studio:
            cursor.close()
            return redirect('/studio/profile')

        studio_id = studio['id']

        # Fetch active subscription
        cursor.execute("""
            SELECT ss.*, sp.name, sp.max_galleries, sp.max_storage_gb, sp.watermark
            FROM studio_subscriptions ss
            JOIN subscription_plans sp ON sp.id = ss.plan_id
            WHERE ss.studio_id = %s
              AND ss.status = 'active'
              AND ss.end_date >= CURDATE()
            ORDER BY ss.end_date DESC
            LIMIT 1
        """, (studio_id,))
        subscription = cursor.fetchone()
        
        if not subscription:
            cursor.close()
            return redirect('/studio/pricing')

        used_storage = get_studio_storage_usage(cursor, studio_id)
        subscription['used_storage_gb'] = round(used_storage, 2)

        cursor.close()
        return f(subscription=subscription, *args, **kwargs)

    return wrapper

# Checks if the subscription is finished
# @app.before_request
# def auto_expire_subscriptions():
#     cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
#     cursor.execute("""
#         UPDATE studio_subscriptions
#         SET status='expired'
#         WHERE status='active' AND end_date < CURDATE()
#     """)
#     mysql.connection.commit()
#     cursor.close()


# Studio Pricing Page (Route + Logic)
@app.route('/studio/pricing')
@login_required
def studio_pricing():
    if session.get('role') != 'studio':
        return redirect('/login')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    studio_id = get_studio_id(cursor)

    # All plans
    cursor.execute("""
        SELECT id, name, price, duration_days, max_galleries, watermark, max_storage_gb
        FROM subscription_plans
        ORDER BY price
    """)
    plans = cursor.fetchall()

    # Active subscription (if any)
    cursor.execute("""
        SELECT ss.*, sp.name AS plan_name
        FROM studio_subscriptions ss
        JOIN subscription_plans sp ON sp.id = ss.plan_id
        WHERE ss.studio_id=%s
          AND ss.status='active'
          AND ss.end_date >= CURDATE()
        ORDER BY ss.end_date DESC
        LIMIT 1
    """, (studio_id,))
    active_plan = cursor.fetchone()

    cursor.close()

    return render_template(
        'studio/pricing.html',
        plans=plans,
        active_plan=active_plan
    )

# Subscribe to Plan
@app.route('/studio/subscribe/<int:plan_id>')
@login_required
def studio_subscribe(plan_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    studio_id = get_studio_id(cursor)

    cursor.execute("SELECT * FROM subscription_plans WHERE id=%s", (plan_id,))
    plan = cursor.fetchone()

    if not plan:
        return abort(404)

    try:
        # Create Instamojo Payment Request
        # Note: Instamojo needs amount as a string with 2 decimals
        response = instamojo_service.api.payment_request_create(
            amount="{:.2f}".format(plan['price']),
            purpose=f"StudioPro: {plan['name']}",
            buyer_name=session.get('user_name', 'Studio Owner'),
            email=session.get('email', 'studio@example.com'),
            phone=session.get('phone', '9999999999'),
            allow_repeated_payments=False,
            redirect_url=url_for('payment_success', _external=True) # Fallback
        )

        payment_url = response['payment_request']['longurl']
        payment_request_id = response['payment_request']['id']

        # Save pending payment
        cursor.execute("""
            INSERT INTO payments (studio_id, plan_id, instamojo_id, amount, status)
            VALUES (%s, %s, %s, %s, 'pending')
        """, (studio_id, plan_id, payment_request_id, plan['price']))
        mysql.connection.commit()

        return render_template(
            "studio/instamojo_checkout.html",
            plan=plan,
            payment_url=payment_url # Pass this to JS
        )

    except Exception as e:
        print(f"Instamojo Error: {e}")
        return "Gateway Error", 500
    finally:
        cursor.close()



# Payment Success Redirect
@app.route('/payment-success')
def payment_success():
    payment_id = request.args.get('payment_id')
    payment_request_id = request.args.get('payment_request_id')
    status = request.args.get('payment_status')

    if status == "Credit": # 'Credit' means successful in Instamojo
        cursor = mysql.connection.cursor()
        cursor.execute("""
            UPDATE payments SET status='completed', payment_id=%s 
            WHERE instamojo_id=%s
        """, (payment_id, payment_request_id))
        mysql.connection.commit()
        return render_template("success.html", id=payment_id)
    
    return "Payment failed or was cancelled.", 400


# Updated Verification Route
# Since you are using fetch in JavaScript, your verification route needs to return JSON.
@app.route('/payment/verify', methods=['POST'])
@login_required
def verify_payment():
    data = request.get_json()
    payment_id = data.get('payment_id')
    request_id = data.get('payment_request_id')

    # Verify status with Instamojo API
    payment_details = instamojo_service.api.payment_request_status(request_id)
    
    if payment_details['payment_request']['status'] == 'Completed':
        cursor = mysql.connection.cursor()
        cursor.execute("""
            UPDATE payments SET status='success', payment_id=%s 
            WHERE instamojo_id=%s
        """, (payment_id, request_id))
        mysql.connection.commit()
        cursor.close()
        return {"success": True}
    
    return {"success": False}, 400





# Helper to calculate studio storage usage
def get_studio_storage_usage(cursor, studio_id):
    total_bytes = 0

    # Images
    cursor.execute("""
        SELECT gi.image_path
        FROM gallery_images gi
        JOIN galleries g ON gi.gallery_id = g.id
        WHERE g.studio_id=%s
    """, (studio_id,))
    images = cursor.fetchall()

    # Videos
    cursor.execute("""
        SELECT gv.video_path
        FROM gallery_videos gv
        JOIN galleries g ON gv.gallery_id = g.id
        WHERE g.studio_id=%s
    """, (studio_id,))
    videos = cursor.fetchall()

    for item in images + videos:
        path = item.get('image_path') or item.get('video_path')
        abs_path = os.path.join(current_app.root_path, path)
        if os.path.exists(abs_path):
            total_bytes += os.path.getsize(abs_path)

    return total_bytes / (1024 ** 3)  # GB






# --------------------------------------Subscription BAsed Code End --------------------------------------------

# Create Gallery
@app.route('/studio/gallery/create', methods=['GET', 'POST'])
@login_required
@subscription_required
def create_gallery(subscription):
    # subscription variable is provided by the @subscription_required decorator
    # It contains: id, used_galleries, max_galleries, name, etc.

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    studio_id = get_studio_id(cursor)

    # 1. 🔒 Hard Limit Check
    # We use 'used_galleries' from the subscription record, NOT a count of current rows.
    if subscription['used_galleries'] >= subscription['max_galleries']:
        cursor.close()
        return redirect('/studio/pricing?error=limit_reached')

    # 2. Fetch clients (Needed for BOTH GET and POST error cases)
    cursor.execute("""
        SELECT c.id, u.name 
        FROM clients c 
        JOIN users u ON u.id = c.user_id 
        WHERE c.studio_id = %s 
        ORDER BY u.name
    """, (studio_id,))
    clients = cursor.fetchall()

    if request.method == 'POST':
        title = request.form.get('title')
        client_id = request.form.get('client_id')
        password = request.form.get('password')
        is_download_enabled = 1 if request.form.get('is_download_enabled') else 0

        if not title or not client_id:
            # Basic validation to prevent DB errors
            return render_template('studio/create_gallery.html', 
                                 clients=clients, 
                                 error="Please fill all fields",
                                 remaining_galleries=subscription['max_galleries'] - subscription['used_galleries'],
                                 plan_name=subscription.get('name'))

        try:
            # 3. Create the gallery row
            cursor.execute("""
                INSERT INTO galleries (studio_id, client_id, title, password, is_download_enabled)
                VALUES (%s, %s, %s, %s, %s)
            """, (studio_id, client_id, title, password, is_download_enabled))

            # 4. 🚀 Increment the specific subscription counter
            cursor.execute("""
                UPDATE studio_subscriptions 
                SET used_galleries = used_galleries + 1 
                WHERE id = %s
            """, (subscription['id'],))

            mysql.connection.commit()
            cursor.close()
            return redirect('/studio/gallery-management')
            
        except Exception as e:
            mysql.connection.rollback()
            print(f"Database Error: {e}")
            return "Internal Server Error", 500

    # 5. GET request: Render the form
    cursor.close()
    return render_template(
        'studio/create_gallery.html',
        clients=clients,
        # Fixed: We calculate remaining based on 'used_galleries'
        remaining_galleries=subscription['max_galleries'] - subscription['used_galleries'],
        plan_name=subscription.get('name')
    )

# ----------------------------------Gallery Images -------------------------------------------

# Upload Images to Gallery
@app.route('/studio/gallery/<int:gallery_id>/upload', methods=['GET', 'POST'])
@login_required
@subscription_required
def upload_gallery_images(gallery_id, subscription):
    # ... (existing session and storage checks) ...

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # 1. Fetch gallery and check our NEW status column
    cursor.execute("SELECT * FROM galleries WHERE id=%s", (gallery_id,))
    gallery = cursor.fetchone()

    if request.method == 'POST':
        # PERMANENT FIX: Check the 'photos_uploaded' flag instead of the images table
        if gallery['photos_uploaded'] == 1:
            cursor.close()
            flash("Upload Locked: You have already used your one-time photo upload for this gallery.", "error")
            return redirect(f'/studio/gallery/{gallery_id}/upload')

        files = request.files.getlist('images')
        try:
            for file in files:
                if file and allowed_file(file.filename):
                    filename = f"img_{gallery_id}_{secure_filename(file.filename)}"
                    save_path = os.path.join(UPLOAD_FOLDER, filename)
                    file.save(save_path)

                    cursor.execute("INSERT INTO gallery_images (gallery_id, image_path) VALUES (%s, %s)", 
                                   (gallery_id, save_path))

            # 2. MARK AS LOCKED PERMANENTLY
            cursor.execute("UPDATE galleries SET photos_uploaded = 1 WHERE id = %s", (gallery_id,))
            
            mysql.connection.commit()
            flash("Images uploaded successfully! Upload is now locked.", "success")
        except Exception as e:
            mysql.connection.rollback()
            flash(f"Error: {str(e)}", "error")
        finally:
            cursor.close()
        return redirect(f'/studio/gallery/{gallery_id}/upload')

    # ... (rest of our GET logic)
    # --- FETCH DATA FOR DISPLAY ---
    # FETCH IMAGES
    cursor.execute("""
        SELECT * FROM gallery_images
        WHERE gallery_id=%s
        ORDER BY uploaded_at DESC
    """, (gallery_id,))
    images = cursor.fetchall()

    # FETCH VIDEOS
    cursor.execute("""
        SELECT * FROM gallery_videos
        WHERE gallery_id=%s
        ORDER BY created_at DESC
    """, (gallery_id,))
    videos = cursor.fetchall()

    cursor.close()

    return render_template(
        'studio/upload_gallery_images.html',
        gallery=gallery,
        images=images,
        videos=videos,
        subscription=subscription 
    )

# Studio Delete Gallery
@app.route('/studio/gallery/<int:gallery_id>/delete', methods=['POST'])
@login_required
def delete_gallery(gallery_id):
    # Ensure ownership check
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    studio_id = get_studio_id(cursor) # Use your existing helper to get studio_id

    # 1. Verify this gallery belongs to the logged-in studio
    cursor.execute("SELECT id FROM galleries WHERE id=%s AND studio_id=%s", (gallery_id, studio_id))
    gallery = cursor.fetchone()
    if not gallery:
        cursor.close()
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    # --- PART A: DELETE PHOTOS ---
    # Fetch paths (Use 'gallery_images' or 'gallery_photos' based on your actual table name)
    cursor.execute("SELECT image_path FROM gallery_images WHERE gallery_id=%s", (gallery_id,))
    photos = cursor.fetchall()
    
    for photo in photos:
        if photo['image_path'] and os.path.exists(photo['image_path']):
            try:
                os.remove(photo['image_path'])
            except Exception as e:
                print(f"Error deleting photo file: {e}")

    # --- PART B: DELETE VIDEOS ---
    cursor.execute("SELECT video_path FROM gallery_videos WHERE gallery_id=%s", (gallery_id,))
    videos = cursor.fetchall()
    
    for video in videos:
        if video['video_path'] and os.path.exists(video['video_path']):
            try:
                os.remove(video['video_path'])
            except Exception as e:
                print(f"Error deleting video file: {e}")

    # --- PART C: CLEANUP DATABASE ---
    try:
        # Delete related records first (if you don't have ON DELETE CASCADE setup)
        cursor.execute("DELETE FROM gallery_images WHERE gallery_id=%s", (gallery_id,))
        cursor.execute("DELETE FROM gallery_videos WHERE gallery_id=%s", (gallery_id,))
        
        # Finally delete the gallery itself
        cursor.execute("DELETE FROM galleries WHERE id=%s AND studio_id=%s", (gallery_id, studio_id))
        
        mysql.connection.commit()
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        cursor.close()

    return jsonify({'success': True})

# View specific Gallery (Or Specific Client Gallery) 
@app.route('/studio/gallery/<int:gallery_id>/photos')
@login_required
def studio_gallery_photos(gallery_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Get studio id
    cursor.execute("""
        SELECT id FROM studios WHERE user_id=%s
    """, (session['user_id'],))
    studio = cursor.fetchone()

    if not studio:
        cursor.close()
        return "Unauthorized", 403

    studio_id = studio['id']

    # Verify gallery belongs to studio
    cursor.execute("""
        SELECT id, title
        FROM galleries
        WHERE id=%s AND studio_id=%s
    """, (gallery_id, studio_id))
    gallery = cursor.fetchone()

    if not gallery:
        cursor.close()
        return "Gallery not found", 404

    # Fetch images
    cursor.execute("""
        SELECT id,
               REPLACE(image_path, '\\\\', '/') AS image_path,
               is_selected
        FROM gallery_images
        WHERE gallery_id=%s
        ORDER BY uploaded_at DESC
    """, (gallery_id,))

    photos = cursor.fetchall()
    cursor.close()

    return render_template(
        'studio/gallery_photos.html',
        gallery=gallery,
        photos=photos
    )

# 
@app.route('/studio/gallery/<int:gallery_id>/download')
@login_required
# @subscription_required
def studio_download_all(gallery_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT image_path
        FROM gallery_images
        WHERE gallery_id=%s
    """, (gallery_id,))
    images = cursor.fetchall()
    cursor.close()

    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for img in images:
            zf.write(img['image_path'], arcname=img['image_path'].split('/')[-1])

    memory_file.seek(0)
    return send_file(
        memory_file,
        download_name='studio_gallery_all.zip',
        as_attachment=True
    )

# 
@app.route('/studio/gallery/<int:gallery_id>/download-liked')
@login_required
# @subscription_required
def studio_download_liked(gallery_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT image_path
        FROM gallery_images
        WHERE gallery_id=%s AND is_selected=1
    """, (gallery_id,))
    images = cursor.fetchall()
    cursor.close()

    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for img in images:
            zf.write(img['image_path'], arcname=img['image_path'].split('/')[-1])

    memory_file.seek(0)
    return send_file(
        memory_file,
        download_name='studio_gallery_liked.zip',
        as_attachment=True
    )

# Delete single photo
@app.route('/studio/gallery/photo/<int:photo_id>/delete', methods=['POST'])
@login_required
def studio_delete_photo(photo_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Fetch the image_path BEFORE deleting the record
    cursor.execute("""
        SELECT gi.id, gi.image_path 
        FROM gallery_images gi 
        JOIN galleries g ON gi.gallery_id=g.id 
        WHERE gi.id=%s AND g.studio_id=%s
    """, (photo_id, get_studio_id(cursor)))
    
    photo = cursor.fetchone()
    
    if not photo:
        cursor.close()
        return jsonify({'success': False, 'message': 'Photo not found'}), 403

    # ✅ STEP 1: Delete physical file from disk
    file_path = photo['image_path']
    if file_path and os.path.exists(file_path):
        os.remove(file_path)

    # ✅ STEP 2: Delete record from database
    cursor.execute("DELETE FROM gallery_images WHERE id=%s", (photo_id,))
    
    mysql.connection.commit()
    cursor.close()

    return jsonify({'success': True})


# 2. Delete ALL photos in a gallery
@app.route('/studio/gallery/<int:gallery_id>/delete-all', methods=['POST'])
@login_required
def studio_delete_all_photos(gallery_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Check gallery ownership
    cursor.execute("SELECT id FROM galleries WHERE id=%s AND studio_id=%s",
                   (gallery_id, get_studio_id(cursor)))
    gallery = cursor.fetchone()
    
    if not gallery:
        cursor.close()
        return jsonify({'success': False}), 403

    # ✅ STEP 1: Fetch ALL file paths first
    cursor.execute("SELECT image_path FROM gallery_images WHERE gallery_id=%s", (gallery_id,))
    photos = cursor.fetchall()

    # ✅ STEP 2: Loop and delete each file from disk
    for photo in photos:
        file_path = photo['image_path']
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

    # ✅ STEP 3: Delete all records from database
    cursor.execute("DELETE FROM gallery_images WHERE gallery_id=%s", (gallery_id,))
    
    mysql.connection.commit()
    cursor.close()

    return jsonify({'success': True})

# ----------------------------------Gallery Videos -------------------------------------------

@app.route('/studio/gallery/<int:gallery_id>/videos')
@login_required
# @subscription_required
def studio_gallery_videos(gallery_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Get gallery + client name
    cursor.execute("""
        SELECT 
            g.*,
            u.name AS client_name
        FROM galleries g
        JOIN clients c ON g.client_id = c.id
        JOIN users u ON c.user_id = u.id
        WHERE g.id = %s
    """, (gallery_id,))
    gallery = cursor.fetchone()

    if not gallery:
        cursor.close()
        return "Gallery not found", 404

    # Get videos
    cursor.execute("""
        SELECT 
            id,
            video_path,
            is_selected
        FROM gallery_videos
        WHERE gallery_id = %s
        ORDER BY id DESC
    """, (gallery_id,))
    videos = cursor.fetchall()

    cursor.close()

    return render_template(
        'studio/gallery_videos.html',
        gallery=gallery,
        videos=videos
    )

@app.route('/studio/gallery/<int:gallery_id>/upload-video', methods=['POST'])
@login_required
def upload_video(gallery_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # 1. PERMANENT LOCK CHECK
    cursor.execute("SELECT videos_uploaded FROM galleries WHERE id = %s", (gallery_id,))
    gallery = cursor.fetchone()

    if not gallery:
        cursor.close()
        return redirect('/studio/photo-management')

    if gallery['videos_uploaded'] == 1:
        cursor.close()
        flash("Upload Locked: Video upload is only allowed once for this gallery.", "error")
        return redirect(f"/studio/gallery/{gallery_id}/upload")

    # 2. FILE HANDLING
    videos = request.files.getlist('video')
    
    if not videos or (len(videos) == 1 and videos[0].filename == ''):
        cursor.close()
        flash("No videos selected.", "error")
        return redirect(f"/studio/gallery/{gallery_id}/upload")

    upload_dir = os.path.join('static', 'uploads', 'videos')
    os.makedirs(upload_dir, exist_ok=True)

    try:
        for video in videos:
            if video and video.filename != '':
                filename = f"{gallery_id}_{secure_filename(video.filename)}"
                save_path = os.path.join(upload_dir, filename)
                db_path = f"static/uploads/videos/{filename}"
                
                # Save physical file
                video.save(save_path)

                # Save to Database
                cursor.execute("""
                    INSERT INTO gallery_videos (gallery_id, video_path)
                    VALUES (%s, %s)
                """, (gallery_id, db_path))

        # 3. PERMANENTLY MARK AS UPLOADED
        cursor.execute("UPDATE galleries SET videos_uploaded = 1 WHERE id = %s", (gallery_id,))
        mysql.connection.commit()
        flash("Videos uploaded successfully and gallery locked!", "success")

    except Exception as e:
        print(f"Upload Error: {e}")
        mysql.connection.rollback()
        flash("An error occurred during video upload.", "error")
    finally:
        cursor.close()

    return redirect(f"/studio/gallery/{gallery_id}/upload")

@app.route('/studio/video/<int:video_id>/like', methods=['POST'])
@login_required
# @subscription_required
def toggle_video_like(video_id):
    cursor = mysql.connection.cursor()
    cursor.execute("""
        UPDATE gallery_videos
        SET is_selected = NOT is_selected
        WHERE id=%s
    """, (video_id,))
    mysql.connection.commit()
    return jsonify(success=True)

@app.route('/studio/video/<int:video_id>/delete', methods=['POST'])
@login_required
def delete_video(video_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # 1. Fetch path AND verify ownership (JOIN with galleries to check studio_id)
    cursor.execute("""
        SELECT v.video_path FROM gallery_videos v
        JOIN galleries g ON v.gallery_id = g.id
        WHERE v.id=%s AND g.studio_id=%s
    """, (video_id, get_studio_id(cursor)))
    
    video = cursor.fetchone()

    if not video:
        cursor.close()
        return jsonify(success=False, message="Unauthorized or Not Found"), 403

    # 2. Delete Physical File
    # We use lstrip('/') to ensure os.path.join works correctly with BASE_DIR if needed
    if os.path.exists(video['video_path']):
        try:
            os.remove(video['video_path'])
        except Exception as e:
            print(f"Error deleting file: {e}")

    # 3. Delete Database Record
    cursor.execute("DELETE FROM gallery_videos WHERE id=%s", (video_id,))
    mysql.connection.commit()
    cursor.close()

    return jsonify(success=True)

@app.route('/studio/gallery/<int:gallery_id>/videos/delete-all', methods=['POST'])
@login_required
def delete_all_videos(gallery_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # 1. Verify gallery ownership before deleting anything
    cursor.execute("SELECT id FROM galleries WHERE id=%s AND studio_id=%s", 
                   (gallery_id, get_studio_id(cursor)))
    if not cursor.fetchone():
        cursor.close()
        return jsonify(success=False, message="Unauthorized"), 403

    # 2. Fetch all video paths
    cursor.execute("SELECT video_path FROM gallery_videos WHERE gallery_id=%s", (gallery_id,))
    videos = cursor.fetchall()

    # 3. Loop and delete each file
    for v in videos:
        if v['video_path'] and os.path.exists(v['video_path']):
            try:
                os.remove(v['video_path'])
            except Exception as e:
                print(f"Failed to delete {v['video_path']}: {e}")

    # 4. Delete all records from DB
    cursor.execute("DELETE FROM gallery_videos WHERE gallery_id=%s", (gallery_id,))
    mysql.connection.commit()
    cursor.close()

    return jsonify(success=True)

@app.route('/studio/gallery/<int:gallery_id>/videos/download')
@login_required
# @subscription_required
def download_all_videos(gallery_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT video_path
        FROM gallery_videos
        WHERE gallery_id = %s
    """, (gallery_id,))
    videos = cursor.fetchall()
    cursor.close()

    if not videos:
        return "No videos found", 404

    zip_buffer = BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for video in videos:
            file_path = video['video_path']

            if os.path.exists(file_path):
                zipf.write(
                    file_path,
                    arcname=os.path.basename(file_path)
                )

    zip_buffer.seek(0)

    return send_file(
        zip_buffer,
        as_attachment=True,
        download_name=f'gallery_{gallery_id}_all_videos.zip',
        mimetype='application/zip'
    )

@app.route('/studio/gallery/<int:gallery_id>/videos/download-liked')
@login_required
# @subscription_required
def download_liked_videos(gallery_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT video_path
        FROM gallery_videos
        WHERE gallery_id = %s AND is_selected = 1
    """, (gallery_id,))
    videos = cursor.fetchall()
    cursor.close()

    if not videos:
        return "No liked videos found", 404

    zip_buffer = BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for video in videos:
            file_path = video['video_path']

            if os.path.exists(file_path):
                zipf.write(
                    file_path,
                    arcname=os.path.basename(file_path)
                )

    zip_buffer.seek(0)

    return send_file(
        zip_buffer,
        as_attachment=True,
        download_name=f'gallery_{gallery_id}_liked_videos.zip',
        mimetype='application/zip'
    )

@app.route('/studio/analytics/2')
@login_required
def studio_analytics_2():
    # studio_id = session['studio_id']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    studio_id = get_studio_id(cursor)

    # KPIs
    cursor.execute("SELECT COUNT(*) total FROM galleries WHERE studio_id=%s", (studio_id,))
    total_galleries = cursor.fetchone()['total']

    cursor.execute("""
        SELECT COUNT(*) total FROM gallery_images gi
        JOIN galleries g ON gi.gallery_id = g.id
        WHERE g.studio_id=%s
    """, (studio_id,))
    total_images = cursor.fetchone()['total']

    cursor.execute("""
        SELECT COUNT(*) total FROM gallery_videos gv
        JOIN galleries g ON gv.gallery_id = g.id
        WHERE g.studio_id=%s
    """, (studio_id,))
    total_videos = cursor.fetchone()['total']

    cursor.execute("""
        SELECT COUNT(*) total FROM gallery_images gi
        JOIN galleries g ON gi.gallery_id = g.id
        WHERE g.studio_id=%s AND gi.is_selected=1
    """, (studio_id,))
    image_likes = cursor.fetchone()['total']

    cursor.execute("""
        SELECT COUNT(*) total FROM gallery_videos gv
        JOIN galleries g ON gv.gallery_id = g.id
        WHERE g.studio_id=%s AND gv.is_selected=1
    """, (studio_id,))
    video_likes = cursor.fetchone()['total']

    # Upload trend (last 7 days)
    cursor.execute("""
        SELECT DATE(gi.uploaded_at) d, COUNT(*) c FROM gallery_images gi
        JOIN galleries g ON gi.gallery_id=g.id
        WHERE g.studio_id=%s
        GROUP BY d ORDER BY d
    """, (studio_id,))
    image_trend = cursor.fetchall()

    cursor.execute("""
        SELECT DATE(gv.created_at) d, COUNT(*) c FROM gallery_videos gv
        JOIN galleries g ON gv.gallery_id=g.id
        WHERE g.studio_id=%s
        GROUP BY d ORDER BY d
    """, (studio_id,))
    video_trend = cursor.fetchall()

    return render_template(
        'studio/analytics_2.html',
        total_galleries=total_galleries,
        total_images=total_images,
        total_videos=total_videos,
        image_likes=image_likes,
        video_likes=video_likes,
        image_trend=image_trend,
        video_trend=video_trend
    )

@app.route('/studio/analytics')
@login_required
def studio_analytics():
    # studio_id = session['studio_id']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    studio_id = get_studio_id(cursor)

    # KPIs
    cursor.execute("SELECT COUNT(*) total FROM galleries WHERE studio_id=%s", (studio_id,))
    total_galleries = cursor.fetchone()['total']

    cursor.execute("""
        SELECT COUNT(*) total FROM gallery_images gi
        JOIN galleries g ON gi.gallery_id = g.id
        WHERE g.studio_id=%s
    """, (studio_id,))
    total_images = cursor.fetchone()['total']

    cursor.execute("""
        SELECT COUNT(*) total FROM gallery_videos gv
        JOIN galleries g ON gv.gallery_id = g.id
        WHERE g.studio_id=%s
    """, (studio_id,))
    total_videos = cursor.fetchone()['total']

    cursor.execute("""
        SELECT COUNT(*) total FROM gallery_images gi
        JOIN galleries g ON gi.gallery_id = g.id
        WHERE g.studio_id=%s AND gi.is_selected=1
    """, (studio_id,))
    image_likes = cursor.fetchone()['total']

    cursor.execute("""
        SELECT COUNT(*) total FROM gallery_videos gv
        JOIN galleries g ON gv.gallery_id = g.id
        WHERE g.studio_id=%s AND gv.is_selected=1
    """, (studio_id,))
    video_likes = cursor.fetchone()['total']

    # Upload trend (last 7 days)
    cursor.execute("""
        SELECT DATE(gi.uploaded_at) d, COUNT(*) c FROM gallery_images gi
        JOIN galleries g ON gi.gallery_id=g.id
        WHERE g.studio_id=%s
        GROUP BY d ORDER BY d
    """, (studio_id,))
    image_trend = cursor.fetchall()

    cursor.execute("""
        SELECT DATE(gv.created_at) d, COUNT(*) c FROM gallery_videos gv
        JOIN galleries g ON gv.gallery_id=g.id
        WHERE g.studio_id=%s
        GROUP BY d ORDER BY d
    """, (studio_id,))
    video_trend = cursor.fetchall()

    # Subscription
    cursor.execute("""
        SELECT sp.name, ss.end_date,
        DATEDIFF(ss.end_date, CURDATE()) AS days_left
        FROM studio_subscriptions ss
        JOIN subscription_plans sp ON ss.plan_id = sp.id
        WHERE ss.studio_id=%s AND ss.status="active"
        LIMIT 1
    """, (studio_id,))
    subscription = cursor.fetchone()

    # Bookings
    cursor.execute("""
        SELECT 
            COUNT(*) total,
            SUM(status='accepted') accepted,
            SUM(status='rejected') rejected
        FROM bookings
        WHERE studio_id=%s
    """, (studio_id,))
    bookings = cursor.fetchone()

    # External bookings
    cursor.execute("""
        SELECT COUNT(*) total
        FROM external_bookings
        WHERE studio_id=%s
    """, (studio_id,))
    external_bookings = cursor.fetchone()['total']

    # Contact requests
    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM enquiries
        WHERE studio_id = %s
    """, (studio_id,))
    contact_requests = cursor.fetchone()['total']

    # Recent Enquiries
    cursor.execute("""
        SELECT e.id, e.message, e.status, e.created_at,
            u.name AS client_name, u.email AS client_email
        FROM enquiries e
        JOIN users u ON e.client_id = u.id
        WHERE e.studio_id = %s
        ORDER BY e.created_at DESC
        LIMIT 10
    """, (studio_id,))
    recent_enquiries = cursor.fetchall()



    return render_template(
    'studio/analytics.html',
    total_galleries=total_galleries,
    total_images=total_images,
    total_videos=total_videos,
    image_likes=image_likes,
    video_likes=video_likes,
    image_trend=image_trend,
    video_trend=video_trend,
    subscription=subscription,
    bookings=bookings,
    external_bookings=external_bookings,
    contact_requests=contact_requests,
    recent_enquiries=recent_enquiries
    )






# ---------------------------------------------- Studio Marketplace--------------------------------------------

# Studio Marketplace 
@app.route('/browse', methods=['GET'])
def studio_marketplace():
    search_name = request.args.get('name', '')
    search_city = request.args.get('city', '')
    
    # Get offset from URL (how many to skip), default is 0
    offset = int(request.args.get('offset', 0))
    limit = 10 

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    query = """
        SELECT 
            s.id, s.studio_name, s.city, s.address, s.is_approved,
            u.phone, 
            MAX(sp.file_path) AS home_photo,
            COUNT(DISTINCT r.id) AS review_count,
            ROUND(AVG(r.rating), 1) AS avg_rating
        FROM studios s
        JOIN users u ON s.user_id = u.id
        LEFT JOIN studio_photos sp ON s.id = sp.studio_id AND sp.is_home_photo = 1
        LEFT JOIN studio_reviews r ON s.id = r.studio_id
        WHERE s.studio_name LIKE %s 
          AND s.city LIKE %s
        GROUP BY s.id, u.phone
        ORDER BY s.is_approved DESC, s.created_at DESC
        LIMIT %s OFFSET %s
    """
    
    cursor.execute(query, (f"%{search_name}%", f"%{search_city}%", limit, offset))
    studios = cursor.fetchall()

    for studio in studios:
        cursor.execute("SELECT service_name FROM studio_services WHERE studio_id = %s LIMIT 3", (studio['id'],))
        studio['services'] = cursor.fetchall()
        if studio['home_photo']:
            studio['home_photo'] = '/' + studio['home_photo'].lstrip('/')

    cursor.close()

    # If this is a "Load More" request, only return the list portion
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('marketplace/studios.html', studios=studios, only_list=True)

    return render_template('marketplace/studios.html', studios=studios, only_list=False)

# Studio Gallery ✅
@app.route('/studio/<int:studio_id>')
def studio_detail(studio_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # 1. Studio info + Calculated Rating
    cursor.execute("""
        SELECT s.*, u.name AS owner_name, u.phone,
               COUNT(r.id) as review_count,
               ROUND(AVG(r.rating), 1) as avg_rating
        FROM studios s
        JOIN users u ON s.user_id = u.id
        LEFT JOIN studio_reviews r ON s.id = r.studio_id
        WHERE s.id = %s
        GROUP BY s.id
    """, (studio_id,))
    studio = cursor.fetchone()

    if not studio:
        cursor.close()
        abort(404)

    # 2. Services
    cursor.execute("SELECT * FROM studio_services WHERE studio_id = %s", (studio_id,))
    services = cursor.fetchall()

    # 3. Portfolio photos
    cursor.execute("SELECT file_path FROM studio_photos WHERE studio_id = %s ORDER BY id DESC", (studio_id,))
    photos = cursor.fetchall()

    # 4. Reviews with Reviewer Names
    cursor.execute("""
        SELECT r.*, u.name as reviewer_name 
        FROM studio_reviews r
        JOIN users u ON r.user_id = u.id
        WHERE r.studio_id = %s
        ORDER BY r.created_at DESC
    """, (studio_id,))
    reviews = cursor.fetchall()

    cursor.close()
    return render_template(
        'marketplace/studio_detail.html',
        studio=studio,
        services=services,
        photos=photos,
        reviews=reviews
    )

@app.route('/add-review/<int:studio_id>', methods=['POST'])
def add_review(studio_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    rating = request.form.get('rating')
    comment = request.form.get('comment')

    cursor = mysql.connection.cursor()
    try:
        cursor.execute("""
            INSERT INTO studio_reviews (studio_id, user_id, rating, comment)
            VALUES (%s, %s, %s, %s)
        """, (studio_id, user_id, rating, comment))
        mysql.connection.commit()
    except Exception as e:
        print(f"Error adding review: {e}")
    finally:
        cursor.close()

    return redirect(url_for('studio_detail', studio_id=studio_id))

# Contact Request Send ✅
@app.route('/enquiry/<int:studio_id>', methods=['POST'])
@login_required
def send_enquiry(studio_id):
    message = request.form.get('message')
    client_id = session['user_id']

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("INSERT INTO enquiries (client_id, studio_id, message) VALUES (%s, %s, %s)",
                   (client_id, studio_id, message))
    mysql.connection.commit()
    cursor.close()

    flash('Enquiry sent successfully!', 'success')
    return redirect(url_for(request.referrer, studio_id=studio_id))

# Studio Booking ✅
@app.route('/studio/<int:studio_id>/book', methods=['GET', 'POST'])
@login_required
def book_studio(studio_id):

    if session.get('role') != 'client':
        return redirect('/login')

    client_id = session.get('user_id')
    if not client_id:
        return redirect('/login')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Studio
    cursor.execute("SELECT * FROM studios WHERE id=%s", (studio_id,))
    studio = cursor.fetchone()
    if not studio:
        abort(404)

    # Services
    cursor.execute("""
        SELECT id, service_name, price
        FROM studio_services
        WHERE studio_id=%s
    """, (studio_id,))
    services = cursor.fetchall()

    if request.method == 'POST':
        service_ids = request.form.getlist('service_ids[]')
        booking_date = request.form['booking_date']
        booking_time = request.form.get('booking_time')

        if not service_ids:
            abort(400, "Select at least one service")

        # 1️⃣ Create booking
        cursor.execute("""
            INSERT INTO bookings (studio_id, client_id, booking_date, booking_time)
            VALUES (%s, %s, %s, %s)
        """, (
            studio_id,
            client_id,
            booking_date,
            booking_time
        ))

        booking_id = cursor.lastrowid

        # 2️⃣ Attach services
        for service_id in service_ids:
            cursor.execute("""
                INSERT INTO booking_services (booking_id, service_id)
                VALUES (%s, %s)
            """, (booking_id, service_id))

        mysql.connection.commit()
        cursor.close()
        return redirect('/my-bookings')

    cursor.close()
    return render_template(
        'marketplace/book_studio.html',
        studio=studio,
        services=services
    )


# ------------------------------------- Studio Ends --------------------------------------------------



# ------------------------------------- Client Starts --------------------------------------------------

#  Clients Dashboard 
@app.route('/client/dashboard')
@login_required
def client_dashboard():
    client_id = session['user_id']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # 1. Fetch galleries with a thumbnail (Latest image from gallery_images)
    cursor.execute("""
        SELECT 
            g.id, 
            g.title, 
            g.created_at,
            (SELECT image_path FROM gallery_images 
             WHERE gallery_id = g.id 
             ORDER BY uploaded_at DESC LIMIT 1) AS cover_image
        FROM galleries g
        JOIN clients c ON g.client_id = c.id
        WHERE c.user_id = %s
        ORDER BY g.created_at DESC
    """, (client_id,))
    galleries = cursor.fetchall()

    # --- Keep your existing stats logic below ---
    total_galleries = len(galleries)

    # Total Images
    cursor.execute("""
        SELECT COUNT(*) AS total_images FROM gallery_images gi
        JOIN galleries g ON gi.gallery_id = g.id
        JOIN clients c ON g.client_id = c.id
        WHERE c.user_id=%s
    """, (client_id,))
    total_images = cursor.fetchone()['total_images']

    # Total Videos
    cursor.execute("""
        SELECT COUNT(*) AS total_videos FROM gallery_videos gv
        JOIN galleries g ON gv.gallery_id = g.id
        JOIN clients c ON g.client_id = c.id
        WHERE c.user_id=%s
    """, (client_id,))
    total_videos = cursor.fetchone()['total_videos']

    # Total Likes
    cursor.execute("""
        SELECT COUNT(*) AS total_likes
        FROM (
            SELECT gi.id FROM gallery_images gi
            JOIN galleries g ON gi.gallery_id = g.id
            JOIN clients c ON g.client_id = c.id
            WHERE c.user_id=%s AND gi.is_selected=1
            UNION ALL
            SELECT gv.id FROM gallery_videos gv
            JOIN galleries g ON gv.gallery_id = g.id
            JOIN clients c ON g.client_id = c.id
            WHERE c.user_id=%s AND gv.is_selected=1
        ) AS likes
    """, (client_id, client_id))
    total_likes = cursor.fetchone()['total_likes']

    cursor.close()

    return render_template(
        'client/dashboard.html',
        galleries=galleries,
        total_galleries=total_galleries,
        total_images=total_images,
        total_videos=total_videos,
        total_likes=total_likes
    )

# Client My Bookings ✅
@app.route('/client/my-bookings')
@login_required
def my_bookings():

    if session.get('role') != 'client':
        return redirect('/login')

    client_id = session.get('user_id')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT 
            b.id AS booking_id,
            b.booking_date,
            b.booking_time,
            b.status,
            s.studio_name,
            s.city,
            GROUP_CONCAT(ss.service_name SEPARATOR ', ') AS services,
            SUM(ss.price) AS total_price
        FROM bookings b
        JOIN studios s ON b.studio_id = s.id
        JOIN booking_services bs ON b.id = bs.booking_id
        JOIN studio_services ss ON bs.service_id = ss.id
        WHERE b.client_id = %s
        GROUP BY b.id
        ORDER BY b.created_at DESC
    """, (client_id,))

    bookings = cursor.fetchall()
    cursor.close()

    return render_template('client/my_bookings.html', bookings=bookings)

# CLIENT Image and video GALLERY LOGIN PAGE ✅
@app.route('/client/gallery/<int:gallery_id>/login/<string:gallery_type>', methods=['GET', 'POST'])
def client_gallery_login(gallery_id, gallery_type):
    if gallery_type not in ['image', 'video']:
        abort(404)

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT id, title, password
        FROM galleries
        WHERE id=%s
    """, (gallery_id,))
    gallery = cursor.fetchone()

    if not gallery:
        cursor.close()
        return "Gallery not found", 404

    if request.method == 'POST':
        entered_password = request.form.get('password')

        if entered_password == gallery['password']:

            # ✅ FETCH CLIENT
            cursor.execute("""
                SELECT id 
                FROM clients 
                WHERE user_id=%s
            """, (session['user_id'],))
            client = cursor.fetchone()

            if not client:
                cursor.close()
                return "Client not found", 403

            # ✅ SET SESSION
            session['client_id'] = client['id']
            session['client_gallery_access'] = gallery_id

            cursor.close()

            # ✅ REDIRECT BASED ON TYPE
            if gallery_type == 'image':
                return redirect(url_for('client_gallery_view', gallery_id=gallery_id))
            else:
                return redirect(url_for('client_gallery_videos', gallery_id=gallery_id))

        else:
            flash("Incorrect password", "error")

    cursor.close()
    return render_template(
        'client/gallery_login.html',
        gallery=gallery,
        gallery_type=gallery_type
    )

#  ✅
@app.route('/client/gallery/logout')
def client_gallery_logout():
    session.pop('client_gallery_access', None)
    session.pop('client_id', None)

    flash("You have been logged out from the gallery.", "success")
    return redirect('/client/dashboard')

#  ✅
@app.route('/client/gallery/<int:gallery_id>/images')
def client_gallery_view(gallery_id):
    if session.get('client_gallery_access') != gallery_id:
        return redirect(url_for('client_gallery_login',
        gallery_id=gallery_id,
        gallery_type='image')   # or 'video'
        )

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT id,
               REPLACE(image_path, '\\\\', '/') AS image_path,
               is_selected
        FROM gallery_images
        WHERE gallery_id=%s
        ORDER BY uploaded_at DESC
    """, (gallery_id,))

    photos = cursor.fetchall()
    cursor.close()

    return render_template(
        'client/gallery_view.html',
        photos=photos,
        gallery_id=gallery_id
    )

# Client selects/unselects a photo ✅
@app.route('/client/gallery/<int:gallery_id>/select/<int:photo_id>', methods=['POST'])
def client_select_photo(gallery_id, photo_id):
    if session.get('client_gallery_access') != gallery_id:
        return jsonify({'success': False}), 403

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Toggle is_selected
    cursor.execute("""
        SELECT is_selected
        FROM gallery_images
        WHERE id=%s AND gallery_id=%s
    """, (photo_id, gallery_id))

    photo = cursor.fetchone()
    if not photo:
        cursor.close()
        return jsonify({'success': False}), 404

    new_value = 0 if photo['is_selected'] else 1

    cursor.execute("""
        UPDATE gallery_images
        SET is_selected=%s
        WHERE id=%s
    """, (new_value, photo_id))

    mysql.connection.commit()
    cursor.close()

    return jsonify({
        'success': True,
        'selected': bool(new_value)
    })

# Cilent Download All images ✅
@app.route('/client/gallery/<int:gallery_id>/download-all')
def download_all_images(gallery_id):
    if session.get('client_gallery_access') != gallery_id:
        return redirect(url_for('client_gallery_login', gallery_id=gallery_id))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        SELECT image_path
        FROM gallery_images
        WHERE gallery_id=%s
    """, (gallery_id,))
    images = cursor.fetchall()
    cursor.close()

    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for img in images:
            zf.write(img['image_path'], arcname=img['image_path'].split('/')[-1])

    memory_file.seek(0)
    return send_file(
        memory_file,
        download_name='gallery_all_images.zip',
        as_attachment=True
    )

# Client Download Only Liked Images ✅
@app.route('/client/gallery/<int:gallery_id>/download-liked')
def download_liked_images(gallery_id):
    if session.get('client_gallery_access') != gallery_id:
        return redirect(url_for('client_gallery_login', gallery_id=gallery_id))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        SELECT image_path
        FROM gallery_images
        WHERE gallery_id=%s AND is_selected=1
    """, (gallery_id,))
    images = cursor.fetchall()
    cursor.close()

    if not images:
        flash("No liked images to download", "warning")
        return redirect(url_for('client_gallery_view', gallery_id=gallery_id))

    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for img in images:
            zf.write(img['image_path'], arcname=img['image_path'].split('/')[-1])

    memory_file.seek(0)
    return send_file(
        memory_file,
        download_name='gallery_liked_images.zip',
        as_attachment=True
    )

# --------------------------------- Client Video Gallery View --------------------------------

#  CLIENT VIDEO GALLERY PAGE (VIEW VIDEOS) ✅
@app.route('/client/gallery/<int:gallery_id>/videos')
def client_gallery_videos(gallery_id):

    # 🔐 CHECK PASSWORD SESSION
    if session.get('client_gallery_access') != gallery_id:
        return redirect(url_for('client_gallery_login',
        gallery_id=gallery_id,
        gallery_type='video'))   # or 'video'


    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT id, title
        FROM galleries
        WHERE id=%s
    """, (gallery_id,))
    gallery = cursor.fetchone()

    if not gallery:
        cursor.close()
        return "Gallery not found", 404

    cursor.execute("""
        SELECT id, video_path, is_selected
        FROM gallery_videos
        WHERE gallery_id=%s
        ORDER BY id DESC
    """, (gallery_id,))
    videos = cursor.fetchall()

    cursor.close()

    return render_template(
        'client/video_gallery_view.html',
        gallery=gallery,
        gallery_id=gallery_id,
        videos=videos
    )

# Helper Function for Client Videos Like/ Unlike, Download all/liked videos ✅
def validate_client_gallery_access(gallery_id):
    if 'client_gallery_access' not in session:
        abort(403)

    if session['client_gallery_access'] != gallery_id:
        abort(403)


# LIKE / UNLIKE VIDEO ( TOGGLE)
@app.route('/client/gallery/<int:gallery_id>/video/select/<int:video_id>', methods=['POST'])
def client_toggle_video_like(gallery_id, video_id):

    if session.get('client_gallery_access') != gallery_id:
        return jsonify(success=False), 403

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT is_selected
        FROM gallery_videos
        WHERE id=%s AND gallery_id=%s
    """, (video_id, gallery_id))

    video = cursor.fetchone()
    if not video:
        cursor.close()
        return jsonify(success=False), 404

    new_status = 0 if video['is_selected'] else 1

    cursor.execute("""
        UPDATE gallery_videos
        SET is_selected=%s
        WHERE id=%s
    """, (new_status, video_id))

    mysql.connection.commit()
    cursor.close()

    return jsonify(success=True, selected=new_status)

# Client Download All Videos ✅
@app.route('/client/gallery/<int:gallery_id>/videos/download-all')
def client_download_all_videos(gallery_id):

    validate_client_gallery_access(gallery_id)

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        SELECT video_path
        FROM gallery_videos
        WHERE gallery_id=%s
    """, (gallery_id,))
    videos = cursor.fetchall()
    cursor.close()

    if not videos:
        abort(404)

    zip_dir = os.path.join(app.root_path, 'zips')
    os.makedirs(zip_dir, exist_ok=True)

    zip_path = os.path.join(
        zip_dir,
        f'gallery_{gallery_id}_videos.zip'
    )

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for v in videos:
            abs_path = os.path.join(app.root_path, v['video_path'])
            if os.path.exists(abs_path):
                zipf.write(abs_path, os.path.basename(abs_path))

    return send_file(
        zip_path,
        as_attachment=True,
        download_name="gallery_videos.zip"
    )

# Client Download only liked Videos ✅
@app.route('/client/gallery/<int:gallery_id>/videos/download-liked')
def client_download_liked_videos(gallery_id):

    validate_client_gallery_access(gallery_id)

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        SELECT video_path
        FROM gallery_videos
        WHERE gallery_id=%s AND is_selected=1
    """, (gallery_id,))
    videos = cursor.fetchall()
    cursor.close()

    if not videos:
        abort(404)

    zip_dir = os.path.join(app.root_path, 'zips')
    os.makedirs(zip_dir, exist_ok=True)

    zip_path = os.path.join(
        zip_dir,
        f'gallery_{gallery_id}_liked_videos.zip'
    )

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for v in videos:
            abs_path = os.path.join(app.root_path, v['video_path'])
            if os.path.exists(abs_path):
                zipf.write(abs_path, os.path.basename(abs_path))

    return send_file(
        zip_path,
        as_attachment=True,
        download_name="liked_videos.zip"
    )




if __name__ == '__main__':
    app.run(debug=True)








