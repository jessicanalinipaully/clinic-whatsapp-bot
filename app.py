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

    return {
        "doctor": doctor,
        "date": date,
        "time": time
    }


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
    <h1>Clinic WhatsApp Appointment System</h1>
    <p>Bot is running successfully.</p>
    <a href="/login">Admin Login</a>
    """


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect("/dashboard")

        return "Wrong username or password. Go back and try again."

    return """
    <h2>Admin Login</h2>
    <form method="POST">
        <input name="username" placeholder="Username" required><br><br>
        <input name="password" type="password" placeholder="Password" required><br><br>
        <button type="submit">Login</button>
    </form>
    """


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/dashboard")
def dashboard():
    if not session.get("admin"):
        return redirect("/login")

    conn = db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, phone, name, doctor, date, time, status
        FROM appointments
        ORDER BY id DESC
    """)

    appointments = cursor.fetchall()
    conn.close()

    html = """
    <html>
    <head>
        <title>Clinic Dashboard</title>
        <style>
            body { font-family: Arial; padding: 30px; background: #f4f4f4; }
            h1 { color: #333; }
            table { width: 100%; border-collapse: collapse; background: white; }
            th, td { padding: 12px; border: 1px solid #ddd; text-align: left; }
            th { background: #007bff; color: white; }
            .logout { float: right; }
            .Booked { color: green; font-weight: bold; }
            .Cancelled { color: red; font-weight: bold; }
        </style>
    </head>
    <body>
        <a class="logout" href="/logout">Logout</a>
        <h1>Clinic Appointments Dashboard</h1>
        <table>
            <tr>
                <th>ID</th>
                <th>Phone</th>
                <th>Name</th>
                <th>Doctor</th>
                <th>Date</th>
                <th>Time</th>
                <th>Status</th>
            </tr>
    """

    for appt in appointments:
        status = appt[6]
        html += f"""
            <tr>
                <td>{appt[0]}</td>
                <td>{appt[1]}</td>
                <td>{appt[2]}</td>
                <td>{appt[3]}</td>
                <td>{appt[4]}</td>
                <td>{appt[5]}</td>
                <td class="{status}">{status}</td>
            </tr>
        """

    html += """
        </table>
    </body>
    </html>
    """

    return html


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

    if incoming_msg == "reschedule":
        appointment = get_latest_booked_appointment(phone)

        if appointment is None:
            msg.body(
                "You don't have any active appointment to reschedule.\n\n"
                "Type HI to book an appointment."
            )
            user_sessions[phone] = {"step": "start"}
            return str(response)

        current_user["step"] = "reschedule_date"
        current_user["reschedule_id"] = appointment["id"]
        current_user["reschedule_doctor"] = appointment["doctor"]
        current_user["reschedule_name"] = appointment["name"]

        msg.body(
            "Your current appointment:\n\n"
            f"Doctor: {appointment['doctor']}\n"
            f"Date: {appointment['date']}\n"
            f"Time: {appointment['time']}\n\n"
            "Please enter your new appointment date.\n"
            "Example: 15 June 2026"
        )
        return str(response)

    if incoming_msg in ["hi", "hello", "start"]:
        current_user["step"] = "menu"
        msg.body(
            "Welcome to ABC Clinic 🏥\n\n"
            "1. Book Appointment\n"
            "2. Doctor Availability\n\n"
            "Type CANCEL to cancel your latest appointment.\n"
            "Type RESCHEDULE to reschedule your latest appointment."
        )

    elif current_user["step"] == "menu":
        if incoming_msg == "1":
            current_user["step"] = "name"
            msg.body("Please enter your full name:")
        elif incoming_msg == "2":
            msg.body(
                "Doctors Available Today:\n\n"
                "1. Dr. Kumar\n"
                "2. Dr. Sharma\n\n"
                "Type HI to return to menu."
            )
        else:
            msg.body("Please choose 1 or 2.")

    elif current_user["step"] == "name":
        current_user["name"] = incoming_msg.title()
        current_user["step"] = "doctor"
        msg.body(
            "Choose Doctor:\n\n"
            "1. Dr. Kumar\n"
            "2. Dr. Sharma"
        )

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
        msg.body(
            "Choose Time Slot:\n\n"
            "1. 10:00 AM\n"
            "2. 11:30 AM\n"
            "3. 4:00 PM"
        )

    elif current_user["step"] == "slot":
        if incoming_msg in slots:
            doctor = current_user["doctor"]
            date = current_user["date"]
            time = slots[incoming_msg]

            if is_slot_booked(doctor, date, time):
                msg.body(
                    "Sorry, this slot is already booked.\n\n"
                    "Please choose another time slot:\n\n"
                    "1. 10:00 AM\n"
                    "2. 11:30 AM\n"
                    "3. 4:00 PM"
                )
                return str(response)

            save_appointment(phone, current_user["name"], doctor, date, time)

            msg.body(
                "✅ Appointment Confirmed!\n\n"
                f"Name: {current_user['name']}\n"
                f"Doctor: {doctor}\n"
                f"Date: {date}\n"
                f"Time: {time}\n\n"
                "Thank you for booking with ABC Clinic.\n"
                "To cancel, type CANCEL.\n"
                "To reschedule, type RESCHEDULE."
            )

            user_sessions[phone] = {"step": "start"}
        else:
            msg.body("Please choose 1, 2, or 3.")

    elif current_user["step"] == "reschedule_date":
        current_user["new_date"] = incoming_msg.title()
        current_user["step"] = "reschedule_slot"
        msg.body(
            "Choose new time slot:\n\n"
            "1. 10:00 AM\n"
            "2. 11:30 AM\n"
            "3. 4:00 PM"
        )

    elif current_user["step"] == "reschedule_slot":
        if incoming_msg in slots:
            appointment_id = current_user["reschedule_id"]
            doctor = current_user["reschedule_doctor"]
            name = current_user["reschedule_name"]
            new_date = current_user["new_date"]
            new_time = slots[incoming_msg]

            if is_slot_booked(doctor, new_date, new_time):
                msg.body(
                    "Sorry, this new slot is already booked.\n\n"
                    "Please choose another time slot:\n\n"
                    "1. 10:00 AM\n"
                    "2. 11:30 AM\n"
                    "3. 4:00 PM"
                )
                return str(response)

            update_appointment_date_time(appointment_id, new_date, new_time)

            msg.body(
                "✅ Appointment Rescheduled!\n\n"
                f"Name: {name}\n"
                f"Doctor: {doctor}\n"
                f"New Date: {new_date}\n"
                f"New Time: {new_time}\n\n"
                "Thank you. Your appointment has been updated."
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