from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from datetime import datetime, timezone, timedelta
import secrets
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from flask_bcrypt import Bcrypt
import logging
from pymongo import MongoClient
from bson import ObjectId
import certifi
import pytz
import smtplib
from email.mime.text import MIMEText
from io import BytesIO
import openpyxl  # For Excel generation

# Flask App Setup
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.static_folder = 'static'

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
login_manager.login_view = 'login'

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

# Determine Shift
def determine_shift():
    utc_now = datetime.now(timezone.utc)
    ist_timezone = pytz.timezone('Asia/Kolkata')
    ist_now = utc_now.astimezone(ist_timezone)
    day_start = datetime.strptime("08:30", "%H:%M").time()
    day_end = datetime.strptime("17:30", "%H:%M").time()
    return "Day" if day_start <= ist_now.time() <= day_end else "Night"

# Generate Ticket Number
def generate_ticket_number():
    return secrets.token_hex(5)

# Function to send email
def send_email_notification(ticket_data):
    sender_email = "nandinimangal6@gmail.com"
    sender_password = "hlwligcygjrvonfz"
    receiver_email = "mangalnandini6@gmail.com"
    app_url = "https://ticketing-system-ede2.onrender.com/ticket/" + str(ticket_data['_id'])
    subject = f"New Ticket Raised: {ticket_data['ticket_number']}"
    body = f"""
    A new ticket has been raised with the following details:
    Ticket Number: {ticket_data['ticket_number']}
    Raised By: {ticket_data['raised_by']}
    Line: {ticket_data['line']}
    Project: {ticket_data['project']}
    Station: {ticket_data['station']}
    QPL: {ticket_data['qpl']}
    Production Issue Description: {ticket_data['production_issue_description']}
    To view the ticket, click here: {app_url}
    """
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = receiver_email
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(sender_email, sender_password)
            smtp.sendmail(sender_email, receiver_email, msg.as_string())
        print("Email notification sent successfully!")
    except Exception as e:
        print(f"Error sending email: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/setup_data')
def setup_data():
    return "Setup data function not implemented yet."

@app.route('/production', methods=['GET', 'POST'])
def production():
    print("Accessed /production route")
    return redirect(url_for('production_form'))

@app.route('/production_form', methods=['GET', 'POST'])
def production_form():
    print("Accessed /production_form route")
    utc_now = datetime.now(timezone.utc)
    ist_timezone = pytz.timezone('Asia/Kolkata')
    ist_now = utc_now.astimezone(ist_timezone)
    current_date = ist_now.strftime('%Y-%m-%d')
    current_shift = determine_shift()
    event_start_time = ist_now.strftime('%H:%M')
    lines = ["L01", "L02", "L03", "L04", "L05"]
    projects = ["C3F", "C3FP", "C3ZP", "C3Y2", "C3F2P"]
    stations = {
        "ME": ["ASM", "BTB", "CCD", "GLUE", "LENS", "LOGO CHECK 1", "LOGO CHECK 2",
               "LOGO-1", "LOGO-2", "PAMT", "PAMT-1", "PAMT-2", "PDL", "PLASMA",
               "QCPAVF2", "SCAN CODE", "TOUCH", "YH1", "YH2", "THERMAL GEL"],
        "TE": ["ANT", "Audio", "CAMERA", "CQR", "FAMMI", "FCT", "GPS", "IDLE",
               "KEYWRITE", "KEYPARTS1", "LST", "MMI", "PDL", "RAUD", "THERMAL GEL"]
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
        "BTB": ["Machine not working", "Scanning Issue", "High Rejection", "Device Struck in Conveyor", "Machine Power off",
                "Machine reset alarm", "Post not working", "Stitch control issue (Light Box control fail) New issue"],
        "CAMERA": ["Machine not working", "Fixture not coming to position"],
        "CCD": ["Alignment Fixture", "Back cover shifting issue", "CCD machine not working",
                "Jacking cylinder vacuum abnormal alarm", "Machine Power off", "Machine Y-axis abnormal alarm",
                "Object Template fail", "Search area failed", "Target Template failed", "Template are not stable",
                "Y-axis drive alarm"],
        "CQR": ["Group A, B and C not reset to home position suddenly NG",
                "\"CQR client tool not open in one port ( AT the same time one backup port also running fine)\"",
                "CQR Machine not working", "Mobile not discharge properly", "Scanner Issue", "Tester not reset",
                "Tool is not responding", "Tool not open"],
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
                 "\"Lens pull cylinder was not working \"", "Lens tray pulling issue", "Lens not fixing properly",
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
        print("Processing POST request in production_form")
        print(f"Form data received: {request.form}")
        selected_name = request.form.get('selected_name', '')
        line = request.form.get('line', '')
        project = request.form.get('project', '')
        station = request.form.get('station', '')
        qpl = request.form.get('qpl', '')
        production_issue_description = request.form.get('issue_description', '')

        # Handle "other" selections
        if selected_name == 'other':
            selected_name = request.form.get('other_selected_name', '')
            print(f"Using other_selected_name: {selected_name}")
        if line == 'other':
            line = request.form.get('other_line', '')
            print(f"Using other_line: {line}")
        if project == 'other':
            project = request.form.get('other_project', '')
            print(f"Using other_project: {project}")
        if station == 'other':
            station = request.form.get('other_station', '')
            print(f"Using other_station: {station}")
        if qpl == 'other':
            qpl = request.form.get('other_qpl', '')
            print(f"Using other_qpl: {qpl}")
        if production_issue_description == 'other':
            production_issue_description = request.form.get('other_issue_description', '')
            print(f"Using other_issue_description: {production_issue_description}")

        print(f"Final values - selected_name: {selected_name}, line: {line}, project: {project}, station: {station}, qpl: {qpl}, production_issue_description: {production_issue_description}")

        # Validation for required fields
        if not all([selected_name, line, project, station, qpl, production_issue_description]):
            flash("All fields, including Production Issue Description, are required.")
            print("Validation failed: Missing required fields")
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

        new_ticket = {
            "ticket_number": generate_ticket_number(),
            "raised_by": selected_name,
            "start_time": datetime.now(timezone.utc),
            "line": line,
            "project": project,
            "station": station,
            "qpl": qpl,
            "section": section,
            "production_issue_description": production_issue_description,
            "sme_issue_description": "",
            "status": "Open",
            "close_time": None,
            "root_cause": None,
            "corrective_action": None,
            "attended_by": None,
            "category": None,
            "spares_required": None
        }
        ticket_id = tickets_collection.insert_one(new_ticket).inserted_id
        new_ticket['_id'] = ticket_id
        print(f"Ticket inserted with ID: {ticket_id}, Data: {new_ticket}")
        send_email_notification(new_ticket)
        return redirect(url_for('ticket_submitted', ticket_id=ticket_id))

    print("Rendering production_form.html")
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
            if ticket.get("status") == "Closed" and ticket.get("start_time"):
                start_time_utc = ticket["start_time"].replace(tzinfo=pytz.utc)
                close_time_utc = ticket["close_time"].replace(tzinfo=pytz.utc)
                elapsed_time = (close_time_utc - start_time_utc).total_seconds() / 60
                ticket["elapsed_time"] = round(elapsed_time, 2)
            else:
                ticket["elapsed_time"] = None
        else:
            ticket["close_time_str"] = None
            ticket["elapsed_time"] = None
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
    ticket.setdefault("ticket_number", "")
    ticket.setdefault("raised_by", "")
    ticket.setdefault("start_time", None)
    ticket.setdefault("line", "")
    ticket.setdefault("project", "")
    ticket.setdefault("station", "")
    ticket.setdefault("qpl", "")
    ticket.setdefault("production_issue_description", "")
    ticket.setdefault("sme_issue_description", "")
    ticket.setdefault("status", "Open")
    ticket.setdefault("close_time", None)
    ticket.setdefault("root_cause", "")
    ticket.setdefault("corrective_action", "")
    ticket.setdefault("attended_by", "")
    ticket.setdefault("category", "")
    ticket.setdefault("spares_required", "")
    ist_timezone = pytz.timezone('Asia/Kolkata')
    if ticket.get("start_time"):
        utc_start_time = ticket["start_time"].replace(tzinfo=pytz.utc)
        ist_start_time = utc_start_time.astimezone(ist_timezone)
        ticket["start_time"] = ist_start_time.strftime('%Y-%m-%d %H:%M:%S')
    else:
        ticket["start_time"] = None
    if ticket.get("close_time"):
        utc_close_time = ticket["close_time"].replace(tzinfo=pytz.utc)
        ist_close_time = utc_close_time.astimezone(ist_timezone)
        ticket["close_time"] = ist_close_time.strftime('%Y-%m-%d %H:%M:%S')
    else:
        ticket["close_time"] = None
    is_closed = ticket.get('status') == 'Closed'
    engineer_options = {
        "Day Shift": ["Vipin", "Harish", "Rajnish", "Ankur Sharma", "Zaheer", "Alam",
                      "Dharmendra", "Debashish", "Anil", "Aditya Shukla", "suraj",
                      "Vijay", "Roshan", "Bikash", "Prashant"],
        "Night Shift": ["Shivam", "Anupam", "Sachin", "Kehari", "Hitesh", "Arun",
                        "Sushant", "Ankit", "Ravi", "Sabaj", "Rajesh", "Vibhishan",
                        "Vakeel", "Bhagabat", "Aditya"]
    }
    if request.method == 'POST' and not is_closed:
        update_data = {
            "attended_by": request.form.get('attended_by', ''),
            "status": request.form.get('status', 'Open'),
            "sme_issue_description": request.form.get('sme_issue_description', ''),
            "category": request.form.get('category', ''),
            "root_cause": request.form.get('root_cause', ''),
            "corrective_action": request.form.get('corrective_action', ''),
            "spares_required": request.form.get('spares_required', ''),
        }
        if update_data['status'] == 'Closed':
            update_data['close_time'] = datetime.now(timezone.utc)
        else:
            update_data['close_time'] = None
        tickets_collection.update_one({"_id": ObjectId(ticket_id)}, {"$set": update_data})
        ticket = tickets_collection.find_one({"_id": ObjectId(ticket_id)})
        ticket.setdefault("ticket_number", "")
        ticket.setdefault("raised_by", "")
        ticket.setdefault("start_time", None)
        ticket.setdefault("line", "")
        ticket.setdefault("project", "")
        ticket.setdefault("station", "")
        ticket.setdefault("qpl", "")
        ticket.setdefault("production_issue_description", "")
        ticket.setdefault("sme_issue_description", "")
        ticket.setdefault("status", "Open")
        ticket.setdefault("close_time", None)
        ticket.setdefault("root_cause", "")
        ticket.setdefault("corrective_action", "")
        ticket.setdefault("attended_by", "")
        ticket.setdefault("category", "")
        ticket.setdefault("spares_required", "")
        if ticket.get("start_time"):
            utc_start_time = ticket["start_time"].replace(tzinfo=pytz.utc)
            ist_start_time = utc_start_time.astimezone(ist_timezone)
            ticket["start_time"] = ist_start_time.strftime('%Y-%m-%d %H:%M:%S')
        if ticket.get("close_time"):
            utc_close_time = ticket["close_time"].replace(tzinfo=pytz.utc)
            ist_close_time = utc_close_time.astimezone(ist_timezone)
            ticket["close_time"] = ist_close_time.strftime('%Y-%m-%d %H:%M:%S')
        is_closed = ticket.get('status') == 'Closed'
        flash('Ticket updated successfully!')
        return render_template('view_ticket.html', ticket=ticket, is_closed=is_closed, engineer_options=engineer_options)
    return render_template('view_ticket.html', ticket=ticket, is_closed=is_closed, engineer_options=engineer_options)

@app.route('/export_ticket_excel/<ticket_id>')
@login_required
def export_ticket_excel(ticket_id):
    if 'engineer_id' not in session:
        return redirect(url_for('engineering_login'))
    ticket = tickets_collection.find_one({"_id": ObjectId(ticket_id)})
    if not ticket or ticket.get('status') != 'Closed':
        flash("Ticket not found or not closed.")
        return redirect(url_for('engineering_dashboard'))

    # Set default values for missing fields
    ticket.setdefault("ticket_number", "")
    ticket.setdefault("raised_by", "")
    ticket.setdefault("start_time", None)
    ticket.setdefault("line", "")
    ticket.setdefault("project", "")
    ticket.setdefault("station", "")
    ticket.setdefault("qpl", "")
    ticket.setdefault("production_issue_description", "")
    ticket.setdefault("sme_issue_description", "")
    ticket.setdefault("status", "Closed")
    ticket.setdefault("close_time", None)
    ticket.setdefault("root_cause", "")
    ticket.setdefault("corrective_action", "")
    ticket.setdefault("attended_by", "")
    ticket.setdefault("category", "")
    ticket.setdefault("spares_required", "")

    ist_timezone = pytz.timezone('Asia/Kolkata')
    start_time_str = ticket["start_time"].astimezone(ist_timezone).strftime('%Y-%m-%d %H:%M:%S') if ticket.get("start_time") else "N/A"
    close_time_str = ticket["close_time"].astimezone(ist_timezone).strftime('%Y-%m-%d %H:%M:%S') if ticket.get("close_time") else "N/A"

    # Create a new Excel workbook and sheet
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Ticket_{ticket['ticket_number']}"

    # Add headers
    headers = ["Field", "Value"]
    ws.append(headers)

    # Add ticket data with additional columns
    ticket_data = [
        ["Ticket Number", ticket['ticket_number']],
        ["Raised By", ticket['raised_by']],
        ["Start Time", start_time_str],
        ["Line", ticket['line']],
        ["Project", ticket['project']],
        ["Station", ticket['station']],  # Station from production form
        ["QPL", ticket['qpl']],  # QPL from production form
        ["Issue Description (Production)", ticket['production_issue_description']],
        ["Attended By", ticket['attended_by'] or 'N/A'],  # Attended By from view ticket
        ["Status", ticket['status']],
        ["Issue Description (SME)", ticket['sme_issue_description'] or 'N/A'],
        ["Category", ticket['category'] or 'N/A'],
        ["Root Cause", ticket['root_cause'] or 'N/A'],
        ["Corrective Action", ticket['corrective_action'] or 'N/A'],
        ["Spares Required", ticket['spares_required'] or 'N/A'],
        ["Close Time", close_time_str],
    ]
    for row in ticket_data:
        ws.append(row)

    # Adjust column widths for better readability
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = (max_length + 2)
        ws.column_dimensions[column].width = adjusted_width

    # Save to BytesIO buffer
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"ticket_{ticket['ticket_number']}.xlsx",
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@app.route('/export_tickets_excel', methods=['POST'])
@login_required
def export_tickets_excel():
    start_date_str = request.form['start_date']
    end_date_str = request.form['end_date']
    try:
        start_date_ist = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date_ist = datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1) - timedelta(seconds=1)
    except ValueError:
        flash("Invalid date format. Please use YYYY-MM-DD.")
        return redirect(url_for('engineering_dashboard'))

    ist_timezone = pytz.timezone('Asia/Kolkata')
    start_date_ist = ist_timezone.localize(start_date_ist)
    end_date_ist = ist_timezone.localize(end_date_ist)
    start_date_utc = start_date_ist.astimezone(pytz.utc).replace(tzinfo=None)
    end_date_utc = end_date_ist.astimezone(pytz.utc).replace(tzinfo=None)

    tickets = list(tickets_collection.find({
        "start_time": {"$gte": start_date_utc, "$lte": end_date_utc}
    }))
    if not tickets:
        flash("No tickets found in the selected date range.")
        return redirect(url_for('engineering_dashboard'))

    # Process ticket data
    for ticket in tickets:
        if ticket.get("start_time"):
            utc_start_time = ticket["start_time"].replace(tzinfo=pytz.utc)
            ist_start_time = utc_start_time.astimezone(ist_timezone)
            ticket["start_date"] = ist_start_time.strftime('%Y-%m-%d')
            ticket["start_time_only"] = ist_start_time.strftime('%H:%M:%S')
        else:
            ticket["start_date"] = 'N/A'
            ticket["start_time_only"] = 'N/A'
        if ticket.get("close_time"):
            utc_close_time = ticket["close_time"].replace(tzinfo=pytz.utc)
            ist_close_time = utc_close_time.astimezone(ist_timezone)
            ticket["close_time_str"] = ist_close_time.strftime('%Y-%m-%d %H:%M:%S')
        else:
            ticket["close_time_str"] = 'N/A'
        if ticket.get("status") == "Closed" and ticket.get("start_time") and ticket.get("close_time"):
            start_time_utc = ticket["start_time"].replace(tzinfo=pytz.utc)
            close_time_utc = ticket["close_time"].replace(tzinfo=pytz.utc)
            elapsed_time = (close_time_utc - start_time_utc).total_seconds() / 60
            ticket["elapsed_time"] = round(elapsed_time, 2)
        else:
            ticket["elapsed_time"] = 'N/A'

    # Create a new Excel workbook and sheet
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Tickets"

    # Add headers with additional columns
    headers = [
        "Ticket Number", "Raised By", "Start Date", "Start Time", "Station", "QPL",  # Added Station and QPL
        "Status", "Closed Time", "Elapsed Time (Minutes)", "Attended By",  # Added Attended By
        "Root Cause", "Corrective Action"
    ]
    ws.append(headers)

    # Add ticket data with additional columns
    for ticket in tickets:
        ws.append([
            ticket.get('ticket_number', 'N/A'),
            ticket.get('raised_by', 'N/A'),
            ticket.get('start_date', 'N/A'),
            ticket.get('start_time_only', 'N/A'),
            ticket.get('station', 'N/A'),  # Station from production form
            ticket.get('qpl', 'N/A'),  # QPL from production form
            ticket.get('status', 'N/A'),
            ticket.get('close_time_str', 'N/A'),
            ticket.get('elapsed_time', 'N/A'),
            ticket.get('attended_by', 'N/A'),  # Attended By from view ticket
            ticket.get('root_cause', 'N/A'),
            ticket.get('corrective_action', 'N/A')
        ])

    # Adjust column widths for better readability
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = (max_length + 2)
        ws.column_dimensions[column].width = adjusted_width

    # Save to BytesIO buffer
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"tickets_{start_date_str}_to_{end_date_str}.xlsx",
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = authenticate_user(username, password)
        if user:
            login_user(user)
            session['user_id'] = user.id
            if user.role == 'engineering':
                return redirect(url_for('engineering_dashboard'))
            else:
                return redirect(url_for('production_form'))
        else:
            flash('Invalid username or password')
            return render_template('login.html', error='Invalid credentials')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if users_collection.find_one({"username": username}):
            flash("Username already taken")
            return redirect(url_for('signup'))
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        users_collection.insert_one({"username": username, "password": hashed_password, "role": "production"})
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
