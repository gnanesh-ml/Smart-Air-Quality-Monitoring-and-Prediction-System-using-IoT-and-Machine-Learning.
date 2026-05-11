from flask import Flask, render_template, request, redirect, session, flash
import requests
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import config

app = Flask(__name__)
app.secret_key = "secret123"

users = {}

# SIMPLE AQI PREDICTION (TREND BASED)
previous_gas = None

def predict_aqi(current_gas):
    global previous_gas

    try:
        current_gas = float(current_gas)
    except:
        return "No Data"

    if previous_gas is None:
        previous_gas = current_gas
        return int(current_gas)

    diff = current_gas - previous_gas
    predicted = current_gas + diff

    previous_gas = current_gas

    return int(predicted)

def get_air_quality():
    try:
        url = f"https://api.thingspeak.com/channels/{config.THINGSPEAK_CHANNEL}/feeds/last.json?api_key={config.THINGSPEAK_READ_API}"
        
        response = requests.get(url)
        data = response.json()

        print("ThingSpeak Data:", data)  # DEBUG

        temp = data.get("field1")
        humidity = data.get("field2")
        gas = data.get("field3")

        # Convert safely
        temp = float(temp) if temp else 0
        humidity = float(humidity) if humidity else 0
        gas = float(gas) if gas else 0

        return temp, humidity, gas

    except Exception as e:
        print("Fetch Error:", e)
        return 0, 0, 0

def send_alert(user_email, value):

    print("Sending alert to:", user_email)

    message = Mail(
        from_email=config.EMAIL_SENDER,
        to_emails=user_email,
        subject="Air Quality Alert",
        html_content=f"<strong>Warning! Air Quality Level is {value}. Please take precautions.</strong>"
    )

    try:
        sg = SendGridAPIClient(config.SENDGRID_API_KEY)
        response = sg.send(message)
        print("Email Sent:", response.status_code)

    except Exception as e:
        print("Email Error:", e)

@app.route("/", methods=["GET","POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        if email in users and users[email] == password:
            session["user"] = email
            return redirect("/dashboard")

        else:
            flash("Invalid Email or Password")

    return render_template("login.html")

@app.route("/register", methods=["GET","POST"])
def register():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        users[email] = password

        return redirect("/")

    return render_template("register.html")

@app.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect("/")

    temp, humidity, gas = get_air_quality()

    gas_value = 0
    status = "GOOD"

    if gas is not None:
        gas_value = float(gas)

        if gas_value < 200:
            status = "GOOD"

        elif gas_value < 400:
            status = "MODERATE"

        else:
            status = "BAD"

        # Email alert
        if gas_value > config.AQI_THRESHOLD:
            send_alert(session["user"], gas_value)

    return render_template(
        "dashboard.html",
        temp=temp,
        humidity=humidity,
        gas=gas,
        status=status,
        user=session["user"]
    )
@app.route("/logout")
def logout():
    session.pop("user",None)
    return redirect("/")

@app.route("/api/data")
def api_data():
    temp, humidity, gas = get_air_quality()

    status = "GOOD"
    if gas:
        gas_value = float(gas)

        if gas_value < 200:
            status = "GOOD"
        elif gas_value < 400:
            status = "MODERATE"
        else:
            status = "BAD"

    # 👉 ADD THIS LINE
    prediction = predict_aqi(gas)

    return {
        "temp": temp,
        "humidity": humidity,
        "gas": gas,
        "status": status,
        "prediction": prediction   
    }

if __name__ == "__main__":
    app.run(debug=True)