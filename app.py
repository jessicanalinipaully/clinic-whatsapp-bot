from flask import Flask, request, redirect, session
from twilio.twiml.messaging_response import MessagingResponse
import sqlite3

app = Flask(__name__)
app.secret_key = "change-this-secret-key"

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "clinic123"

user_sessions = {}

doctors = {
    "1": "Dr. Kumar",
    "2": "Dr. Sharma"
}

slots = {
    "1": "10:00 AM",
    "2": "11:30 AM",
    "3": "4:00 PM"
}


def db_connection():
    return sqlite3.connect("clinic.db")


def init_db():
    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT,
            name TEXT,
            doctor TEXT,
            date TEXT,
            time TEXT,
            status TEXT DEFAULT 'Booked'
        )
    """)
    conn.commit()
    conn.close()


def update_status(appointment_id, status):
    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE appointments SET status = ? WHERE id = ?", (status, appointment_id))
    conn.commit()
    conn.close()


def delete_appointment(appointment_id):
    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM appointments WHERE id = ?", (appointment_id,))
    conn.commit()
    conn.close()


def is_slot_booked(doctor, date, time):
    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id FROM appointments
        WHERE doctor = ? AND date = ? AND time = ? AND status = 'Booked'
    """, (doctor, date, time))
    result = cursor.fetchone()
    conn.close()
    return result is not None


def save_appointment(phone, name, doctor, date, time):
    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO appointments (phone, name, doctor, date, time, status)
        VALUES (?, ?, ?, ?, ?, 'Booked')
    """, (phone, name, doctor, date, time))
    conn.commit()
    conn.close()


def cancel_latest_appointment(phone):
    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, doctor, date, time
        FROM appointments
        WHERE phone = ? AND status = 'Booked'
        ORDER BY id DESC
        LIMIT 1
    """, (phone,))
    appointment = cursor.fetchone()

    if appointment is None:
        conn.close()
        return None

    appointment_id, doctor, date, time = appointment

    cursor.execute("""
        UPDATE appointments
        SET status = 'Cancelled'
        WHERE id = ?
    """, (appointment_id,))

    conn.commit()
    conn.close()

    return {"doctor": doctor, "date": date, "time": time}


def get_latest_booked_appointment(phone):
    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, doctor, date, time
        FROM appointments
        WHERE phone = ? AND status = 'Booked'
        ORDER BY id DESC
        LIMIT 1
    """, (phone,))
    appointment = cursor.fetchone()
    conn.close()

    if appointment is None:
        return None

    return {
        "id": appointment[0],
        "name": appointment[1],
        "doctor": appointment[2],
        "date": appointment[3],
        "time": appointment[4]
    }


def update_appointment_date_time(appointment_id, new_date, new_time):
    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE appointments
        SET date = ?, time = ?
        WHERE id = ?
    """, (new_date, new_time, appointment_id))
    conn.commit()
    conn.close()


@app.route("/")
def home():
    return """
    <html>
    <head>
        <title>ClinicBot</title>
        <style>
            body {
                margin: 0;
                font-family: Arial, sans-serif;
                background: linear-gradient(135deg, #e0f2fe, #f8fafc);
                color: #0f172a;
            }
            .hero {
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 40px;
            }
            .card {
                max-width: 900px;
                background: white;
                border-radius: 24px;
                padding: 50px;
                box-shadow: 0 20px 60px rgba(15, 23, 42, 0.12);
            }
            h1 { font-size: 48px; margin-bottom: 10px; }
            p { font-size: 18px; color: #475569; line-height: 1.6; }
            .features {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 16px;
                margin-top: 30px;
            }
            .feature {
                background: #f8fafc;
                padding: 18px;
                border-radius: 16px;
                border: 1px solid #e2e8f0;
            }
            .btn {
                display: inline-block;
                margin-top: 30px;
                background: #2563eb;
                color: white;
                padding: 14px 24px;
                border-radius: 12px;
                text-decoration: none;
                font-weight: bold;
            }
        </style>
    </head>
    <body>
        <div class="hero">
            <div class="card">
                <h1>ClinicBot</h1>
                <p>WhatsApp-powered appointment automation system for clinics, doctors, and healthcare centers.</p>
                <div class="features">
                    <div class="feature">✅ Appointment Booking</div>
                    <div class="feature">✅ Cancel & Reschedule</div>
                    <div class="feature">✅ Admin Dashboard</div>
                    <div class="feature">✅ No Double Booking</div>
                    <div class="feature">✅ Patient Search</div>
                    <div class="feature">✅ Dashboard Actions</div>
                </div>
                <a class="btn" href="/login">Open Admin Dashboard</a>
            </div>
        </div>
    </body>
    </html>
    """


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect("/dashboard")

        return redirect("/login?error=1")

    error = request.args.get("error")
    error_html = "<div class='error'>Wrong username or password</div>" if error else ""

    return f"""
    <html>
    <head>
        <title>Admin Login</title>
        <style>
            body {{
                margin: 0;
                font-family: Arial, sans-serif;
                background: #eff6ff;
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
            }}
            .login-card {{
                width: 380px;
                background: white;
                padding: 36px;
                border-radius: 22px;
                box-shadow: 0 20px 50px rgba(15, 23, 42, 0.12);
            }}
            h2 {{ margin-bottom: 8px; color: #0f172a; }}
            p {{ color: #64748b; margin-bottom: 24px; }}
            input {{
                width: 100%;
                padding: 14px;
                margin-bottom: 14px;
                border: 1px solid #cbd5e1;
                border-radius: 12px;
                font-size: 15px;
            }}
            button {{
                width: 100%;
                padding: 14px;
                background: #2563eb;
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 16px;
                font-weight: bold;
                cursor: pointer;
            }}
            .error {{
                background: #fee2e2;
                color: #991b1b;
                padding: 12px;
                border-radius: 12px;
                margin-bottom: 14px;
                font-size: 14px;
            }}
        </style>
    </head>
    <body>
        <div class="login-card">
            <h2>Admin Login</h2>
            <p>Manage appointments and clinic bookings</p>
            {error_html}
            <form method="POST">
                <input name="username" placeholder="Username" required>
                <input name="password" type="password" placeholder="Password" required>
                <button type="submit">Login</button>
            </form>
            <p style="font-size:13px;margin-top:18px;">Demo: admin / clinic123</p>
        </div>
    </body>
    </html>
    """


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/appointment/<int:appointment_id>/cancel", methods=["POST"])
def dashboard_cancel(appointment_id):
    if not session.get("admin"):
        return redirect("/login")
    update_status(appointment_id, "Cancelled")
    return redirect("/dashboard")


@app.route("/appointment/<int:appointment_id>/complete", methods=["POST"])
def dashboard_complete(appointment_id):
    if not session.get("admin"):
        return redirect("/login")
    update_status(appointment_id, "Completed")
    return redirect("/dashboard")


@app.route("/appointment/<int:appointment_id>/book", methods=["POST"])
def dashboard_book(appointment_id):
    if not session.get("admin"):
        return redirect("/login")
    update_status(appointment_id, "Booked")
    return redirect("/dashboard")


@app.route("/appointment/<int:appointment_id>/delete", methods=["POST"])
def dashboard_delete(appointment_id):
    if not session.get("admin"):
        return redirect("/login")
    delete_appointment(appointment_id)
    return redirect("/dashboard")


@app.route("/dashboard")
def dashboard():
    if not session.get("admin"):
        return redirect("/login")

    search = request.args.get("search", "").strip()
    doctor_filter = request.args.get("doctor", "").strip()
    status_filter = request.args.get("status", "").strip()

    conn = db_connection()
    cursor = conn.cursor()

    query = """
        SELECT id, phone, name, doctor, date, time, status
        FROM appointments
        WHERE 1=1
    """
    params = []

    if search:
        query += " AND (name LIKE ? OR phone LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    if doctor_filter:
        query += " AND doctor = ?"
        params.append(doctor_filter)

    if status_filter:
        query += " AND status = ?"
        params.append(status_filter)

    query += " ORDER BY id DESC"
    cursor.execute(query, params)
    appointments = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM appointments")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM appointments WHERE status='Booked'")
    booked = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM appointments WHERE status='Cancelled'")
    cancelled = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM appointments WHERE status='Completed'")
    completed = cursor.fetchone()[0]

    conn.close()

    rows = ""

    for appt in appointments:
        appointment_id = appt[0]
        status = appt[6]

        badge_class = "booked"
        if status == "Cancelled":
            badge_class = "cancelled"
        elif status == "Completed":
            badge_class = "completed"

        rows += f"""
            <tr>
                <td>#{appt[0]}</td>
                <td>{appt[2]}</td>
                <td>{appt[1]}</td>
                <td>{appt[3]}</td>
                <td>{appt[4]}</td>
                <td>{appt[5]}</td>
                <td><span class="badge {badge_class}">{status}</span></td>
                <td>
                    <div class="actions">
                        <form method="POST" action="/appointment/{appointment_id}/book">
                            <button class="small blue" type="submit">Book</button>
                        </form>
                        <form method="POST" action="/appointment/{appointment_id}/complete">
                            <button class="small green" type="submit">Complete</button>
                        </form>
                        <form method="POST" action="/appointment/{appointment_id}/cancel">
                            <button class="small yellow" type="submit">Cancel</button>
                        </form>
                        <form method="POST" action="/appointment/{appointment_id}/delete" onsubmit="return confirm('Delete this appointment permanently?');">
                            <button class="small red" type="submit">Delete</button>
                        </form>
                    </div>
                </td>
            </tr>
        """

    if not rows:
        rows = """
            <tr>
                <td colspan="8" class="empty">No appointments found</td>
            </tr>
        """

    doctor_options = ""
    for doctor in doctors.values():
        selected = "selected" if doctor_filter == doctor else ""
        doctor_options += f"<option value='{doctor}' {selected}>{doctor}</option>"

    booked_selected = "selected" if status_filter == "Booked" else ""
    cancelled_selected = "selected" if status_filter == "Cancelled" else ""
    completed_selected = "selected" if status_filter == "Completed" else ""

    return f"""
    <html>
    <head>
        <title>Clinic Dashboard</title>
        <style>
            body {{
                margin: 0;
                font-family: Arial, sans-serif;
                background: #f1f5f9;
                color: #0f172a;
            }}
            .sidebar {{
                position: fixed;
                left: 0;
                top: 0;
                width: 240px;
                height: 100vh;
                background: #0f172a;
                color: white;
                padding: 28px 20px;
                box-sizing: border-box;
            }}
            .logo {{
                font-size: 24px;
                font-weight: bold;
                margin-bottom: 35px;
            }}
            .nav a {{
                display: block;
                color: #cbd5e1;
                text-decoration: none;
                padding: 12px;
                border-radius: 10px;
                margin-bottom: 8px;
            }}
            .nav a.active {{
                background: #2563eb;
                color: white;
            }}
            .main {{
                margin-left: 240px;
                padding: 32px;
            }}
            .topbar {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 28px;
            }}
            .topbar h1 {{
                margin: 0;
                font-size: 30px;
            }}
            .logout {{
                background: white;
                color: #334155;
                text-decoration: none;
                padding: 10px 16px;
                border-radius: 10px;
                border: 1px solid #e2e8f0;
            }}
            .stats {{
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 20px;
                margin-bottom: 24px;
            }}
            .stat-card {{
                background: white;
                padding: 24px;
                border-radius: 18px;
                box-shadow: 0 8px 30px rgba(15, 23, 42, 0.06);
            }}
            .stat-card p {{
                margin: 0;
                color: #64748b;
                font-size: 14px;
            }}
            .stat-card h2 {{
                margin: 8px 0 0;
                font-size: 34px;
            }}
            .filters {{
                background: white;
                padding: 20px;
                border-radius: 18px;
                margin-bottom: 24px;
                box-shadow: 0 8px 30px rgba(15, 23, 42, 0.06);
            }}
            .filters form {{
                display: grid;
                grid-template-columns: 2fr 1fr 1fr auto;
                gap: 12px;
            }}
            input, select {{
                padding: 12px;
                border-radius: 10px;
                border: 1px solid #cbd5e1;
                font-size: 14px;
            }}
            button {{
                padding: 12px 20px;
                border: none;
                background: #2563eb;
                color: white;
                border-radius: 10px;
                font-weight: bold;
                cursor: pointer;
            }}
            .table-card {{
                background: white;
                border-radius: 18px;
                overflow: hidden;
                box-shadow: 0 8px 30px rgba(15, 23, 42, 0.06);
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
            }}
            th {{
                background: #f8fafc;
                color: #475569;
                text-align: left;
                padding: 16px;
                font-size: 13px;
                text-transform: uppercase;
            }}
            td {{
                padding: 16px;
                border-top: 1px solid #e2e8f0;
                vertical-align: middle;
            }}
            .badge {{
                padding: 7px 12px;
                border-radius: 999px;
                font-size: 13px;
                font-weight: bold;
            }}
            .booked {{
                background: #dcfce7;
                color: #166534;
            }}
            .cancelled {{
                background: #fee2e2;
                color: #991b1b;
            }}
            .completed {{
                background: #dbeafe;
                color: #1d4ed8;
            }}
            .empty {{
                text-align: center;
                color: #64748b;
                padding: 30px;
            }}
            .actions {{
                display: flex;
                gap: 6px;
                flex-wrap: wrap;
            }}
            .actions form {{
                margin: 0;
            }}
            .small {{
                padding: 7px 10px;
                font-size: 12px;
                border-radius: 8px;
            }}
            .blue {{
                background: #2563eb;
            }}
            .green {{
                background: #16a34a;
            }}
            .yellow {{
                background: #f59e0b;
            }}
            .red {{
                background: #dc2626;
            }}
        </style>
    </head>
    <body>
        <div class="sidebar">
            <div class="logo">ClinicBot</div>
            <div class="nav">
                <a class="active" href="/dashboard">Dashboard</a>
                <a href="#">Appointments</a>
                <a href="#">Doctors</a>
                <a href="#">Patients</a>
                <a href="#">Settings</a>
            </div>
        </div>

        <div class="main">
            <div class="topbar">
                <div>
                    <h1>Appointments Dashboard</h1>
                    <p style="color:#64748b;">Manage WhatsApp clinic bookings</p>
                </div>
                <a class="logout" href="/logout">Logout</a>
            </div>

            <div class="stats">
                <div class="stat-card">
                    <p>Total Appointments</p>
                    <h2>{total}</h2>
                </div>
                <div class="stat-card">
                    <p>Booked</p>
                    <h2>{booked}</h2>
                </div>
                <div class="stat-card">
                    <p>Cancelled</p>
                    <h2>{cancelled}</h2>
                </div>
                <div class="stat-card">
                    <p>Completed</p>
                    <h2>{completed}</h2>
                </div>
            </div>

            <div class="filters">
                <form method="GET">
                    <input name="search" value="{search}" placeholder="Search patient name or phone">
                    <select name="doctor">
                        <option value="">All Doctors</option>
                        {doctor_options}
                    </select>
                    <select name="status">
                        <option value="">All Status</option>
                        <option value="Booked" {booked_selected}>Booked</option>
                        <option value="Cancelled" {cancelled_selected}>Cancelled</option>
                        <option value="Completed" {completed_selected}>Completed</option>
                    </select>
                    <button type="submit">Filter</button>
                </form>
            </div>

            <div class="table-card">
                <table>
                    <tr>
                        <th>ID</th>
                        <th>Patient</th>
                        <th>Phone</th>
                        <th>Doctor</th>
                        <th>Date</th>
                        <th>Time</th>
                        <th>Status</th>
                        <th>Actions</th>
                    </tr>
                    {rows}
                </table>
            </div>
        </div>
    </body>
    </html>
    """


@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    incoming_msg = request.values.get("Body", "").strip().lower()
    phone = request.values.get("From", "")

    response = MessagingResponse()
    msg = response.message()

    if phone not in user_sessions:
        user_sessions[phone] = {"step": "start"}

    current_user = user_sessions[phone]

    if incoming_msg == "cancel":
        cancelled = cancel_latest_appointment(phone)

        if cancelled:
            msg.body(
                "✅ Your latest appointment has been cancelled.\n\n"
                f"Doctor: {cancelled['doctor']}\n"
                f"Date: {cancelled['date']}\n"
                f"Time: {cancelled['time']}\n\n"
                "Type HI to book a new appointment."
            )
        else:
            msg.body(
                "You don't have any active booked appointment to cancel.\n\n"
                "Type HI to book an appointment."
            )

        user_sessions[phone] = {"step": "start"}
        return str(response)

    if incoming_msg in ["hi", "hello", "start"]:
        current_user["step"] = "menu"
        msg.body(
            "Welcome to ABC Clinic 🏥\n\n"
            "1. Book Appointment\n"
            "2. Doctor Availability\n\n"
            "Type CANCEL to cancel your latest appointment."
        )

    elif current_user["step"] == "menu":
        if incoming_msg == "1":
            current_user["step"] = "name"
            msg.body("Please enter your full name:")
        elif incoming_msg == "2":
            msg.body("Doctors Available Today:\n\n1. Dr. Kumar\n2. Dr. Sharma")
        else:
            msg.body("Please choose 1 or 2.")

    elif current_user["step"] == "name":
        current_user["name"] = incoming_msg.title()
        current_user["step"] = "doctor"
        msg.body("Choose Doctor:\n\n1. Dr. Kumar\n2. Dr. Sharma")

    elif current_user["step"] == "doctor":
        if incoming_msg in doctors:
            current_user["doctor"] = doctors[incoming_msg]
            current_user["step"] = "date"
            msg.body("Enter appointment date, example: 10 June 2026")
        else:
            msg.body("Please choose 1 or 2.")

    elif current_user["step"] == "date":
        current_user["date"] = incoming_msg.title()
        current_user["step"] = "slot"
        msg.body("Choose Time Slot:\n\n1. 10:00 AM\n2. 11:30 AM\n3. 4:00 PM")

    elif current_user["step"] == "slot":
        if incoming_msg in slots:
            doctor = current_user["doctor"]
            date = current_user["date"]
            time = slots[incoming_msg]

            if is_slot_booked(doctor, date, time):
                msg.body("Sorry, this slot is already booked. Please choose another slot.")
                return str(response)

            save_appointment(phone, current_user["name"], doctor, date, time)

            msg.body(
                "✅ Appointment Confirmed!\n\n"
                f"Name: {current_user['name']}\n"
                f"Doctor: {doctor}\n"
                f"Date: {date}\n"
                f"Time: {time}\n\n"
                "Thank you for booking with ABC Clinic."
            )

            user_sessions[phone] = {"step": "start"}
        else:
            msg.body("Please choose 1, 2, or 3.")

    else:
        msg.body("Type HI to begin.")

    return str(response)


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)