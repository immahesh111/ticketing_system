from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime
import secrets
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from flask_bcrypt import Bcrypt
import logging
from pymongo import MongoClient
from bson import ObjectId
import certifi
import pytz
import os
from werkzeug.utils import secure_filename

# Import necessary libraries for sending emails with attachments
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage

# Flask App Setup
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.static_folder = 'static'
app.config['UPLOAD_FOLDER'] = 'static/uploads'  # Folder to store uploaded images

# Ensure the upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# MongoDB Connection
client = MongoClient(
    "mongodb+srv://aarushibawejaji:heya@cluster0.imgm1l7.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0",
    tlsCAFile=certifi.where()
)
db = client["ticketing_system"]
users_collection = db["users"]
tickets_collection = db["tickets"]

# Flask-Login Configuration
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'engineering_login'

# Flask-Bcrypt
bcrypt = Bcrypt(app)

# Logging
logging.basicConfig(level=logging.ERROR)

# User Model
class User(UserMixin):
    def __init__(self, user_id, username, password, role):
        self.id = user_id
        self.username = username
        self.password = password
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    user = users_collection.find_one({"_id": ObjectId(user_id)})
    if user:
        return User(str(user["_id"]), user["username"], user["password"], user["role"])
    return None

def authenticate_user(username, password):
    user = users_collection.find_one({"username": username})
    if not user:
        print(f"❌ User '{username}' not found in database!")
        return None
    print(f"✅ User found: {user['username']} - Stored Hash: {user['password']}")
    try:
        if bcrypt.check_password_hash(user["password"], password):
            print("✅ Password matched! Logging in...")
            return User(str(user["_id"]), user["username"], user["password"], user["role"])
        else:
            print("❌ Password mismatch!")
    except Exception as e:
        print(f"⚠️ Error checking password hash: {e}")
    return None

def determine_shift():
    utc_now = pytz.utc.localize(datetime.utcnow())
    ist_timezone = pytz.timezone('Asia/Kolkata')
    ist_now = utc_now.astimezone(ist_timezone)
    day_start = datetime.strptime("08:30", "%H:%M").time()
    day_end = datetime.strptime("17:30", "%H:%M").time()
    return "Day" if day_start <= ist_now.time() <= day_end else "Night"

def generate_ticket_number():
    return secrets.token_hex(5)

def send_email_notification(ticket_data):
    sender_email = "nandinimangal6@gmail.com"
    sender_password = "hlwligcygjrvonfz"
    # List of recipient email addresses
    receiver_emails = [
       # "mangalnandini6@gmail.com",
        "btbte21189_nandini@banasthali.com",  # Add more email IDs here
       # "manishamangal44@gmail.com"   # Add as many as needed
    ]
    app_url = "https://ticketing-system-ede2.onrender.com/production_form"
    subject = f"New Ticket Raised: {ticket_data['ticket_number']}"

    # Create a multipart message
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = ", ".join(receiver_emails)  # Join emails with commas for the 'To' field

    # Email body
    body = f"""
    A new ticket has been raised with the following details:

    Ticket Number: {ticket_data['ticket_number']}
    Raised By: {ticket_data['raised_by']}
    Line: {ticket_data['line']}
    Project: {ticket_data['project']}
    Station: {ticket_data['station']}
    QPL: {ticket_data['qpl']}
    Issue Description: {ticket_data['issue_description']}
    To view the ticket, click here: {app_url}
    """
    msg.attach(MIMEText(body, 'plain'))

    # Attach the image if it exists
    if ticket_data['image']:
        image_path = ticket_data['image'].lstrip('/')  # Remove leading '/' to get relative path
        try:
            with open(image_path, 'rb') as img_file:
                img = MIMEImage(img_file.read())
                img.add_header('Content-Disposition', 'attachment', filename=os.path.basename(image_path))
                msg.attach(img)
        except FileNotFoundError:
            print(f"Error: Image file {image_path} not found for attachment.")
    else:
        msg.attach(MIMEText("Image: No image uploaded", 'plain'))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(sender_email, sender_password)
            smtp.sendmail(sender_email, receiver_emails, msg.as_string())  # Send to all recipients
        print("Email notification sent successfully to multiple recipients with image attachment!")
    except Exception as e:
        print(f"Error sending email: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/setup_data')
def setup_data():
    return "Setup data function not implemented yet."

@app.route('/production_form', methods=['GET', 'POST'])
def production_form():
    utc_now = pytz.utc.localize(datetime.utcnow())
    ist_timezone = pytz.timezone('Asia/Kolkata')
    ist_now = utc_now.astimezone(ist_timezone)
    current_date = ist_now.strftime('%Y-%m-%d')
    current_shift = determine_shift()
    event_start_time = ist_now.strftime('%H:%M')
    lines = ["L01", "L02", "L03", "L04", "L05"]
    projects = ["C3F", "C3FP", "C3ZP", "C3Y2", "C3F2P"]
    stations = {
        "ME": [
            "ASM", "BTB", "CCD", "GLUE", "LENS", "LOGO CHECK 1", "LOGO CHECK 2",
            "LOGO-1", "LOGO-2", "PAMT", "PAMT-1", "PAMT-2", "PDL", "PLASMA",
            "QCPAVF2", "SCAN CODE", "TOUCH", "YH1", "YH2", "THERMAL GEL"
        ],
        "TE": [
            "ANT", "Audio", "CAMERA", "CQR", "FAMMI", "FCT", "GPS", "IDLE",
            "KEYWRITE", "KEYPARTS1", "LST", "MMI", "PDL", "RAUD", "THERMAL GEL"
        ]
    }
    qpls = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    raised_by_options = {
        "Day Shift": ["Vipin", "Ankur Sharma", "Deepak", "Debashish", "Arun", "Roshan"],
        "Night Shift": ["Shivam", "Pankaj", "Ankur", "Tubul", "Ravi", "Vakeel"]
    }
    section = "Assembly"
    issue_descriptions = {
        "ANT": ["ANT Tester Issue", "ANT Port not working", "Band Failures", "Cycle time High", "Tester not working"],
        "ASM": ["Port not working", "Screw Missing", "Affain Failed", "Machine not working", "Clamping Horn Error",
                "Device transfer alarm", "Machine NG Rate High", "Screw Loose", "Screw Feeder down", "Screw Miss",
                "Torque value not achieved"],
        "Audio": ["Post not working", "Machine down", "High Failures"],
        "BTB": ["Machine not working", "Scanning Issue", "High Rejection", "Device Struck in Conveyor",
                "Machine Power off", "Machine reset alarm", "Post not working", "Stitch control issue"],
        "CAMERA": ["Machine not working", "Fixture not coming to position"],
        "CCD": ["Alignment Fixture", "Back cover shifting issue", "CCD machine not working",
                "Jacking cylinder vacuum abnormal alarm", "Machine Power off", "Machine Y-axis abnormal alarm",
                "Object Template fail", "Search area failed", "Target Template failed", "Template are not stable",
                "Y-axis drive alarm"],
        "CQR": ["Group A, B and C not reset to home position suddenly NG",
                "CQR client tool not open in one port", "CQR Machine not working", "Mobile not discharge properly",
                "Scanner Issue", "Tester not reset", "Tool is not responding", "Tool not open"],
        "FAMMI": ["Auto Update", "Post not working"],
        "FCT": ["Communication Issue", "Post not working", "GRADIENT FAIL"],
        "GRADIENT FAIL": ["Gredinte failure issue", "Lux Fail", "PC power on issue", "Port communication issue",
                          "Tool was not working", "USB cable not connecting"],
        "GLUE": ["Tool Corrupt", "AGVI not working properly", "Camera platform drive alarm", "Device Struck issue",
                 "Device Damage", "Glue abnormal flow from the nozzle", "Glue Detection issue", "Glue improper flow",
                 "Machine not working", "Glue not purging", "Glue path NG", "Glue path offset", "Glue pattern offset",
                 "Glue weight NG", "Nozzle jam", "Pattern got NG", "Plasma machine Issue", "Sensor not working",
                 "VI section not working"],
        "GPS": ["GPS FAIL"],
        "IDLE": ["Robotic not reset", "Device return to NG Conveyor", "Camera not working", "High Failures",
                 "Device not move in Pass conveyor", "Machine not working", "Port not working", "Machine not Reset",
                 "Machine reset alarm due to Sensor feedback abnormal", "PC Boot Issue", "PC Hang", "Power Supply issue",
                 "ROBOT IS NOT GOING TO PICK UP THE DEVICE", "Robot not going to the axis position",
                 "Robot pickup sensor not detected", "Robotic not reset", "Testing not start", "Tool is not responding",
                 "Post issue"],
        "KEYPARTS1": ["Device stuck between conveyor", "High Failures", "Machine not running properly"],
        "KEYWRITE": ["Check OS ready fail", "Device dent issue", "Device Picking Robot issue", "EDI Client tool hang",
                     "Machine not working", "Machine reset alarm", "PLC hang", "PLC not connect", "PORT Hanging",
                     "Tool is not responding", "USB not connecting", "Virtual PC Issue"],
        "LENS": ["All lens coming from the NG Conveyor", "ARM issue", "Device struck up", "Left tray loading failed",
                 "Lens feeder was not working", "Lens not assembled", "Lens pick up abnormal Alarm",
                 "Lens pull cylinder was not working", "Lens tray pulling issue", "Lens not fixing properly",
                 "Hardware issue", "Machine Reset issue", "Machine reset abnormal alarm", "Feeder Issue", "Servo Alarm",
                 "Suction Alarm", "Template Issue", "Tool is not responding", "Tray Cylinder Issue",
                 "Vision tool not responding"],
        "LOGO CHECK 1": ["High Failures", "Motot Shaft issue", "Tool close issue"],
        "LOGO CHECK 2": ["Gift box failure rate is high", "Machine PC power off issue", "Program Corrupted",
                         "Quality Machine Validation fail", "High Failures", "Z axis head got open logo check 2"],
        "LOGO-1": ["Read Sensor issue", "Software Issue"],
        "LOGO-2": ["Barcode Error", "Device Fail", "Detection Fail", "Machine not working", "Cyclinder issue",
                   "Software Issue", "Weight not showing", "Tool is not responding"],
        "LST": ["GRADIENT FAIL", "Tester failure rate is high", "Tool not open"],
        "MMI": ["PC not ON"],
        "PAMT": ["Fixed scanning fail", "Tool is not responding"],
        "PAMT-1": ["Machine not working properly", "Machine conveyor not working",
                   "MES & PLC Communication alarm in the tool", "High Failures"],
        "PAMT-2": ["Machine Hang", "Machine not working", "Sampling issue", "Tool is not responding"],
        "PDL": ["PC Hang", "PORT Hang", "ALL device return to NG Conveyor", "OS Ready fail", "IMEI not scan",
                "Pick up issue", "Scanning Issue", "Device Struck", "Failure rate is too high", "Loading ARM Issue",
                "Loading Cylinder Issue", "M/C not working properly", "Machine not Reset", "Manipulator pickup problem",
                "Maximum device not scanning", "PC hang", "PDL machine is not working", "QR code not generated",
                "Scanner Issue", "The device was not holding properly", "Port Issue", "Tool is not responding",
                "USB cable not connecting"],
        "PLASMA": ["Machine Alarm Issue", "Plasma flame not coming (Cleaning exception Alarm)", "Plasma not coming",
                   "Sensor not working"],
        "QCPAVF2": ["Belt was not rotating", "Conveyor not rotating", "Gift box barcode getting fail continuously"],
        "RAUD": ["Tester is not working", "High Failures", "Tester Caliberation issue", "Tester not working"],
        "SCAN CODE": ["Device stuck between conveyor", "Machine Transfer conveyor not working"],
        "THERMAL GEL": ["Glue path NG", "Glue weight NG from SOP spec"],
        "TOUCH": ["LHS port not working", "Machine not working properly"],
        "YH1": ["Control switch fail alarm", "High Failures", "Fixed scanning fail alarm", "NG conveyor Belt not moving",
                "Pressing value is out of specs", "Switch control fail", "Y1 -axis not moving"],
        "YH2": ["Machine Reset", "Tool Corrupt", "High Failures", "Machine not working", "Belt not Rotating",
                "Device coming in NG Conveyor", "Eragon Tool is continuously disconnecting while running time",
                "Eragon Tool is not responding properly", "Front robot arm is not working", "Machine reset alarm",
                "Machine tool not communicating with MES tool", "MES Tool shutdown issue", "Switch control fail"]
    }

    if request.method == 'POST':
        selected_name = request.form['selected_name']
        line = request.form['line']
        project = request.form['project']
        station = request.form['station']
        qpl = request.form['qpl']
        issue_description = request.form['issue_description']

        if selected_name == 'other':
            selected_name = request.form['other_selected_name']
        if line == 'other':
            line = request.form['other_line']
        if project == 'other':
            project = request.form['other_project']
        if station == 'other':
            station = request.form['other_station']
        if qpl == 'other':
            qpl = request.form['other_qpl']
        if issue_description == 'other':
            issue_description = request.form['other_issue_description']

        image_file = request.files.get('image')
        image_path = None
        if image_file and image_file.filename != '':
            filename = secure_filename(image_file.filename)
            unique_filename = f"{secrets.token_hex(8)}_{filename}"
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            image_file.save(image_path)
            image_path = f"/{image_path}"  # Relative URL for serving

        new_ticket = {
            "ticket_number": generate_ticket_number(),
            "raised_by": selected_name,
            "start_time": datetime.utcnow(),
            "line": line,
            "project": project,
            "station": station,
            "qpl": qpl,
            "section": section,
            "issue_description": issue_description,
            "image": image_path,
            "status": "Open",
            "close_time": None,
            "root_cause": None,
            "corrective_action": None
        }
        ticket_id = tickets_collection.insert_one(new_ticket).inserted_id

        send_email_notification(new_ticket)
        return redirect(url_for('ticket_submitted', ticket_id=new_ticket['ticket_number']))

    return render_template('production_form.html',
                           date=current_date,
                           shift=current_shift,
                           event_start_time=event_start_time,
                           lines=lines,
                           projects=projects,
                           stations=stations,
                           qpls=qpls,
                           raised_by_options=raised_by_options,
                           section=section,
                           issue_descriptions=issue_descriptions)

@app.route('/ticket_submitted/<ticket_id>')
def ticket_submitted(ticket_id):
    return render_template('ticket_submitted.html', ticket_id=ticket_id)

@app.route('/engineering', methods=['GET', 'POST'])
def engineering_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = authenticate_user(username, password)

        if user and user.role == 'engineering':
            login_user(user)
            session['engineer_id'] = user.id
            return redirect(url_for('engineering_dashboard'))
        else:
            flash('Invalid username or password')
            return render_template('engineering_login.html', error='Invalid credentials')

    return render_template('engineering_login.html')

def sort_tickets(tickets):
    status_order = {"Open": 1, "In Progress": 2, "Closed": 3}
    return sorted(
        tickets,
        key=lambda x: (status_order.get(x.get("status"), 4),
                       -x.get("start_time").timestamp() if x.get("start_time") else float('inf')),
    )

@app.route('/engineering_dashboard')
@login_required
def engineering_dashboard():
    if 'engineer_id' not in session:
        return redirect(url_for('engineering_login'))

    all_tickets = list(tickets_collection.find())
    sorted_tickets = sort_tickets(all_tickets)
    ist_timezone = pytz.timezone('Asia/Kolkata')

    for ticket in sorted_tickets:
        if ticket.get("start_time"):
            utc_start_time = ticket["start_time"].replace(tzinfo=pytz.utc)
            ist_start_time = utc_start_time.astimezone(ist_timezone)
            ticket["start_date"] = ist_start_time.strftime('%Y-%m-%d')
            ticket["start_time_only"] = ist_start_time.strftime('%H:%M:%S')
        else:
            ticket["start_date"] = None
            ticket["start_time_only"] = None

        if ticket.get("close_time"):
            utc_close_time = ticket["close_time"].replace(tzinfo=pytz.utc)
            ist_close_time = utc_close_time.astimezone(ist_timezone)
            ticket["close_time_str"] = ist_close_time.strftime('%Y-%m-%d %H:%M:%S')
        else:
            ticket["close_time_str"] = None

    return render_template('engineering_dashboard.html', tickets=sorted_tickets)

@app.route('/ticket/<ticket_id>', methods=['GET', 'POST'])
@login_required
def view_ticket(ticket_id):
    if 'engineer_id' not in session:
        return redirect(url_for('engineering_login'))

    ticket = tickets_collection.find_one({"_id": ObjectId(ticket_id)})
    if not ticket:
        flash("Ticket not found.")
        return redirect(url_for('engineering_dashboard'))

    ist_timezone = pytz.timezone('Asia/Kolkata')

    if ticket.get("start_time"):
        utc_start_time = ticket["start_time"].replace(tzinfo=pytz.utc)
        ist_start_time = utc_start_time.astimezone(ist_timezone)
        ticket["start_time_str"] = ist_start_time.strftime('%Y-%m-%d %H:%M:%S')
    else:
        ticket["start_time_str"] = None

    if ticket.get("close_time"):
        utc_close_time = ticket["close_time"].replace(tzinfo=pytz.utc)
        ist_close_time = utc_close_time.astimezone(ist_timezone)
        ticket["close_time_str"] = ist_close_time.strftime('%Y-%m-%d %H:%M:%S')
    else:
        ticket["close_time_str"] = None

    is_closed = ticket.get('status') == 'Closed'
    engineer_options = {
        "Day Shift": [
            "Vipin", "Harish", "Rajnish", "Ankur Sharma", "Zaheer", "Alam",
            "Dharmendra", "Debashish", "Anil", "Aditya Shukla", "suraj",
            "Vijay", "Roshan", "Bikash", "Prashant"
        ],
        "Night Shift": [
            "Shivam", "Anupam", "Sachin", "Kehari", "Hitesh", "Arun",
            "Sushant", "Ankit", "Ravi", "Sabaj", "Rajesh", "Vibhishan",
            "Vakeel", "Bhagabat", "Aditya"
        ]
    }

    if request.method == 'POST' and not is_closed:
        update_data = {
            "attended_by": request.form['attended_by'],
            "status": request.form['status'],
            "issue_description": request.form['issue_description'],
            "category": request.form['category'],
            "root_cause": request.form['root_cause'],
            "corrective_action": request.form['corrective_action'],
            "spares_required": request.form['spares_required'],
        }
        if request.form['status'] == 'Closed':
            update_data['close_time'] = datetime.utcnow()
        else:
            update_data['close_time'] = None

        tickets_collection.update_one({"_id": ObjectId(ticket_id)}, {"$set": update_data})

        ticket = tickets_collection.find_one({"_id": ObjectId(ticket_id)})
        if ticket.get("start_time"):
            utc_start_time = ticket["start_time"].replace(tzinfo=pytz.utc)
            ist_start_time = utc_start_time.astimezone(ist_timezone)
            ticket["start_time_str"] = ist_start_time.strftime('%Y-%m-%d %H:%M:%S')
        if ticket.get("close_time"):
            utc_close_time = ticket["close_time"].replace(tzinfo=pytz.utc)
            ist_close_time = utc_close_time.astimezone(ist_timezone)
            ticket["close_time_str"] = ist_close_time.strftime('%Y-%m-%d %H:%M:%S')
        is_closed = ticket.get('status') == 'Closed'
        flash('Ticket updated successfully!')
        return render_template('view_ticket.html', ticket=ticket, is_closed=is_closed, engineer_options=engineer_options)

    return render_template('view_ticket.html', ticket=ticket, is_closed=is_closed, engineer_options=engineer_options)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
