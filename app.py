import os
from flask import Flask, render_template,jsonify, request, redirect, url_for, session, flash
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
from datetime import datetime, timedelta
import mysql.connector
from flask import send_from_directory
from urllib.parse import urlparse
import random
import string
import base64
import secrets
reset_token = secrets.token_urlsafe(32)




app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "your_secret_key")
#CORS(app)

# Parse the MYSQL_URL environment variable
db_url = os.getenv("MYSQL_URL")
url = urlparse(db_url)

# Updated database connection setup
db = mysql.connector.connect(
    host=url.hostname,
    user=url.username,
    password=url.password,
    database=url.path.lstrip("/"),
    port=url.port
)

# Use dictionary=True so fetched rows can be accessed like dicts
cursor = db.cursor(dictionary=True)

# Database connection function
def connect_db():
    conn = mysql.connector.connect(
        host=url.hostname,
        user=url.username,
        password=url.password,
        database=url.path.lstrip("/"),
        port=url.port
    )
    return conn


# Directory to store uploaded profile pictures
UPLOAD_FOLDER = 'static/uploads'  # Ensure this folder exists  # Ensure this matches your folder structure
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

bcrypt = Bcrypt(app)
from flask_mail import Mail, Message

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = "ajp3489@gmail.com"
app.config['MAIL_PASSWORD'] = "aroi ycdt nvab skas"
app.config['MAIL_DEFAULT_SENDER'] = "ajp3489@gmail.com"

mail = Mail(app)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


# Signup Route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password_hash']
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        # Check if user already exists
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        if user:
            flash('User already exists. Please login.', 'danger')
            return redirect(url_for('login'))
        else:
            # Add new user to the database
            cursor.execute("INSERT INTO users (name,email,phone, password_hash) VALUES (%s,%s,%s,%s)", (name,email, phone,hashed_password))
            db.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))

    return render_template('signup.html')
@app.route('/login', methods=['GET', 'POST']) 
def login():
    print("Login route accessed")  # Debugging line
    if request.method == 'POST':
        print("POST request received")  # Debugging line
        
        email = request.form['email']
        password = request.form['password']

        cursor.execute("SELECT id, email, password_hash, name, phone, role FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if user is None:
            flash('User not found. Please register first.', 'danger')
            return redirect(url_for('login'))

        if bcrypt.check_password_hash(user['password_hash'], password):  
            session['user_id'] = user['id']
            session['role'] = user['role']  # Store role in session
            print("Login successful!")  # Debugging line
            flash('Login successful!', 'success')

            # ✅ Correct admin redirect
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('home'))
        else:
            print("Invalid password!")  # Debugging line
            flash('Invalid email or password. Please try again.', 'danger')

    return render_template('login.html', user_details=None)





@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()

        try:
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
        except Exception:
            flash("Database error. Please try again.", "danger")
            return redirect(url_for('reset_password_request'))

        if user:
            reset_token = secrets.token_urlsafe(32)  # More secure token
            reset_token_expiry = datetime.now() + timedelta(hours=1)

            cursor.execute("UPDATE users SET reset_token = %s, reset_token_expiry = %s WHERE email = %s", 
                           (reset_token, reset_token_expiry, email))
            db.commit()

            reset_link = url_for('reset_password_otp', token=reset_token, _external=True)

            msg = Message('Password Reset Request', sender='your_email@gmail.com', recipients=[email])
            msg.body = f'Click the following link to reset your password: {reset_link}'
            mail.send(msg)

            flash('A password reset link has been sent to your email.', 'info')
            return redirect(url_for('login'))
        else:
            flash('Email not found.', 'danger')

    return render_template('reset_password_request.html')

@app.route('/reset_password_otp/<token>', methods=['GET', 'POST'])
def reset_password_otp(token):
    try:
        cursor.execute("SELECT * FROM users WHERE reset_token = %s AND reset_token_expiry > %s", 
                       (token, datetime.now()))
        user = cursor.fetchone()
    except Exception:
        flash("Database error. Please try again.", "danger")
        return redirect(url_for('login'))

    if not user:
        flash('The reset link is invalid or has expired.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        new_password = request.form['new_password']

        if len(new_password) < 8:
            flash('Password must be at least 8 characters long.', 'danger')
            return redirect(url_for('reset_password_otp', token=token))

        hashed_password = generate_password_hash(new_password)

        cursor.execute("UPDATE users SET password_hash = %s, reset_token = NULL, reset_token_expiry = NULL WHERE reset_token = %s", 
                       (hashed_password, token))
        db.commit()

        flash('Your password has been reset successfully. Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('reset_password_otp.html', token=token)

# Home Route (Default)
@app.route('/')
def home():
    if 'user_id' in session:
        return render_template('index.html')
    else:
        return redirect(url_for('login'))

# Route to serve the feedback.html page
@app.route('/feedback')
def feedback_page():
    return render_template('feedback.html')

# Route to handle feedback submission
@app.route('/submit-feedback', methods=['POST'])
def submit_feedback():
    if request.is_json:  # Ensure request contains JSON data
        data = request.get_json()
        rating = data.get('rating')
        feedback_text = data.get('feedback')

        # Here, you can store the feedback in a database or a file
        return jsonify({'feedback': {'rating': rating, 'feedback': feedback_text}})
    
    return jsonify({"error": "Unsupported Media Type"}), 415  # Return 415 if not JSON
@app.route('/faq')
def faq():
    return "<h1>FAQs</h1><p>Coming soon...</p>"

@app.route('/contact')
def contact():
    return "<h1>Contact Us</h1><p>Email: support@roamio.com</p>"


# ------------------ Dashboard Route ------------------
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Redirect if not logged in

    user_id = session['user_id']

    with db.cursor() as cur:
        # Fetch user details
        cur.execute("SELECT name, email, phone, photo FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        print("User data:", user)
        if not user:
            flash("User not found!", "danger")

            return redirect(url_for('login'))

        # Fetch bookings
        cur.execute("SELECT package_type, travel_date, status FROM bookings WHERE user_id = %s", (user_id,))
        bookings = cur.fetchall()

    photo_filename = None
    if user[3]:  # If photo is not None
        photo_filename = f"uploads/{user[3].decode('utf-8')}" if isinstance(user[3], bytes) else f"uploads/{user[3]}"
        photo_filename = photo_filename.lstrip('/')  # Remove any unintended leading slashes

 # Ensure the correct relative path

    # Organize bookings into categories
    current_bookings = [b for b in bookings if b[2] == 'Confirmed']
    previous_bookings = [b for b in bookings if b[2] == 'Pending']
    cancelled_bookings = [b for b in bookings if b[2] == 'Cancelled']

    return render_template('dashboard.html', 
                           current_user={
                               'name': user[0], 
                               'email': user[1], 
                               'phone': user[2], 
                               'photo': photo_filename or 'images/default-profile.jpg'  # Fallback image
                           },
                           current_bookings=current_bookings, 
                           previous_bookings=previous_bookings, 
                           cancelled_bookings=cancelled_bookings)



# ------------------ Edit Profile Route ------------------
@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    cur = db.cursor()

    if request.method == 'POST':
        email = request.form['email']
        phone = request.form['phone']
        file = request.files['profile_picture']
        
        # Default photo path (in case user doesn't upload a new one)
        photo_filename = None

        # If user uploaded a file, save it
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            photo_filename = filename  # Save the filename

        # Update user details in database
        if photo_filename:
            cur.execute("UPDATE users SET email=%s, phone=%s, photo=%s WHERE id=%s", 
                        (email, phone, photo_filename, user_id))
        else:
            cur.execute("UPDATE users SET email=%s, phone=%s WHERE id=%s", 
                        (email, phone, user_id))
        
        db.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for('dashboard'))

    # Fetch existing user details
    cur.execute("SELECT name, email, phone, photo FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()

    return render_template('edit_profile.html', current_user={'name': user[0], 'email': user[1], 'phone': user[2], 'photo': user[3]})

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    
# Error Page
@app.route('/not_found')
def error_page():
    return "<h1>Page Not Found</h1><p>The search term does not match any known destinations.</p>"

@app.route("/nature")
def nature():
    return render_template("nature.html")


@app.route('/kerala')
def kerala():
    return render_template('kerala.html')

@app.route('/train')
def train():
    return render_template('train.html')
@app.route('/international')
def international():
    return render_template('international.html')

# Booking page
@app.route('/booking')
def booking():
    return render_template('booking.html')

# Route for booking_form.html
@app.route('/booking_form', methods=['GET', 'POST'])
def booking_form():
    if request.method == 'POST':
        full_name = request.form.get('name')
        email = request.form.get('email')
        phone_number = request.form.get('phone')
        adults = request.form.get('adults')
        children = request.form.get('children')
        package_type = request.form.get('package_type')
        travel_date = request.form.get('date')
        
        user_id = session.get('user_id')

        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO bookings (user_id, full_name, email, phone_number, adults, children, package_type, travel_date, status) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (user_id, full_name, email, phone_number, adults, children, package_type, travel_date, 'Pending'))
        db.commit()
        return redirect(url_for('dashboard'))

    return render_template('booking_form.html')


# Route for one_day.html
@app.route('/one_day')
def one_day():
    return render_template('one_day.html')

# Route for two_days.html
@app.route('/two_days')
def two_days():
    return render_template('two_days.html')

# Route for one_day_two_night.html
@app.route('/one_day_two_night')
def one_day_two_night():
    return render_template('one_day_two_night.html')

 #Route for one_day_two_night.html
@app.route('/two_days_three_nights')
def two_days_three_nights():
    return render_template('two_days_three_nights.html')


 #Route for three_days.html
@app.route('/three-days')
def three_days():
    return render_template('three_days.html')

 #Route for three_days_four_nights.html
@app.route('/three_days_four_nights')
def three_days_four_nights():
    return render_template('three_days_four_nights.html')

 #Route for four_days_five_nights.html
@app.route('/four_days_five_nights')
def four_days_five_nights():
    return render_template('four_days_five_nights.html')
 
 #Route for five_days_six_nights.html
@app.route('/five_days_six_nights')
def five_days_six_nights():
    return render_template('five_days_six_nights.html')

    
@app.route('/confirm-booking', methods=['POST'])
def confirm_booking():
    if request.method == 'POST':
        #Get form data
        name = request.form.get('name')
        phone = request.form.get('phone')
        email = request.form.get('email')
        category = request.form.get('category')

        # Process booking details (you can store them in a database if needed)
        
        return render_template('booking_form.html', message="You have Registered for the Tour! Now sit back and relax while our executive contacts you shortly.")


@app.route('/chatbot')
def chatbot():
    return render_template('chatbot.html')

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message", "").lower()
    print(f"Received message: {user_message}")  # Debugging line

    # Define redirection links
    redirections = {
        "home": "/",
        "dashboard": "/dashboard",
        "booking": "/booking",
        "help": "/help-center"
    }

    # Check if message matches a redirection command
    if user_message in redirections:
        redirect_url = redirections[user_message]
        print(f"Redirecting to: {redirect_url}")  # Debugging line
        return jsonify({"response": f"Redirecting to {redirect_url}..."}), 200

    print("No redirection matched.")  # Debugging line
    return jsonify({"response": "Sorry, I didn't understand that."}), 400


@app.route("/admin_dashboard")
def admin_dashboard():
    if not session.get('is_admin'):
        return redirect(url_for('login')) 
    cursor.execute("SELECT * FROM bookings")
    bookings = cursor.fetchall()
    return render_template("admin_dashboard.html", bookings=bookings)

@app.route('/set_admin_session', methods=['POST'])
def set_admin_session():
    session['is_admin'] = True
    return '', 204  # No content response


@app.route("/update_booking_status/<int:booking_id>", methods=["POST"])
def update_booking_status(booking_id):
    new_status = request.form.get("status")
    cursor.execute("UPDATE bookings SET status = %s WHERE id = %s", (new_status, booking_id))
    db.commit()
    flash("Booking status updated!", "success")
    return redirect(url_for("admin_dashboard"))

@app.route('/update_packages', methods=['GET', 'POST'])
def update_packages():
    # Your package update logic here
    return render_template('update_packages.html')

@app.route("/search_user", methods=["GET", "POST"])
def search_user():
    if request.method == "POST":
        email = request.form['email']
        
        # Fetch user details by email
        cursor.execute("SELECT id, name, email, phone FROM users WHERE email = %s", (email,))
        user_data = cursor.fetchone()

        if user_data:
            # Fetch the booking history for the found user
            cursor.execute("""
                SELECT id, package_type, booking_date, status 
                FROM bookings WHERE user_id = %s
                """, (user_data['id'],))
            bookings = cursor.fetchall()
            
            return render_template('search_user.html', user_data=user_data, bookings=bookings)
        else:
            flash("User not found!", "danger")
            return redirect(url_for('search_user'))

    return render_template('search_user.html', user_data=None, bookings=None)



def send_booking_email(destination, date):
    msg = Message(
        subject="New Booking Alert!",
        sender="yourcompany@gmail.com",
        recipients=["owner@example.com"]
    )
    msg.body = f"New Booking:\nDestination: {destination}\nDate: {date}"
    mail.send(msg)
   
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form['password']
        if password == 'appas_123@@':
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return "Invalid admin password!"
    return render_template('admin_login.html')

@app.route("/admin_logout")
def admin_logout():
    # Remove admin session variable if it exists
    session.pop('admin_logged_in', None)
    flash("Logged out successfully!", "success")
    return redirect(url_for('login'))  # Redirect to the login page


# Logout Route
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
