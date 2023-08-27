import datetime
import threading
import time

import pytz
from bson.objectid import ObjectId
from flask import Flask, redirect, render_template, request, session, url_for
from pymongo import MongoClient

app = Flask(__name__, static_url_path='/static')

app.secret_key = 'your_secret_key_here'

# Initialize the MongoDB client
client = MongoClient("mongodb://95.217.186.200:27017/")
db = client["training_bot"]
trainings_collection = db["trainings"]
registrations_collection = db["registrations"]
logs_collection = db["logs"]
ping_collection = db["ping"]

# Function to send ping data to MongoDB


def send_ping_data():
    while True:
        ping_data = {
            "type": "ping",
            "datetime": datetime.datetime.now()
        }
        ping_collection.insert_one(ping_data)
        time.sleep(1)


# Start the ping data sending thread
ping_thread = threading.Thread(target=send_ping_data)
ping_thread.start()


@app.route('/training_fully_booked', methods=['GET'])
def training_fully_booked():
    return render_template('training_fully_booked.html')


@app.route('/error', methods=['GET'])
def error():
    return render_template('error_page.html')


@app.before_request
def log_request_info():
    user_agent = request.headers.get('User-Agent')
    ip_address = request.remote_addr
    url = request.url
    timestamp = datetime.datetime.now()

    log_entry = {
        "timestamp": timestamp,
        "user_agent": user_agent,
        "ip_address": ip_address,
        "url": url
    }
    logs_collection.insert_one(log_entry)


@app.route('/')
def index():
    finnish_timezone = pytz.timezone('Europe/Helsinki')
    current_time_finnish = datetime.datetime.now(finnish_timezone)

    upcoming_trainings = trainings_collection.find(
        {"datetime": {"$gte": current_time_finnish}}).sort("datetime")
    return render_template('index.html', trainings=upcoming_trainings)


@app.route('/signup_page/<training_id>', methods=['GET'])
def signup_page(training_id):
    selected_training = trainings_collection.find_one(
        {"_id": ObjectId(training_id)})

    if selected_training:
        finnish_timezone = pytz.timezone('Europe/Helsinki')
        current_time_finnish = datetime.datetime.now(finnish_timezone)
        training_datetime_finnish = selected_training['datetime'].replace(
            tzinfo=pytz.utc).astimezone(finnish_timezone)

        if training_datetime_finnish >= current_time_finnish:
            return render_template('signup_page.html', training=selected_training)
        else:
            return redirect(url_for('error'))
    else:
        return redirect(url_for('error'))


@app.route('/signup', methods=['POST'])
def signup():
    if request.method == 'POST':
        user_data = {
            "name": request.form['name'],
            "last_name": request.form['last_name'],
            "email": request.form['email'],
            "phone": request.form['phone']
        }
        training_id = ObjectId(request.form['training_id'])

        selected_training = trainings_collection.find_one({"_id": training_id})

        if selected_training:
            current_registrations = registrations_collection.count_documents(
                {"training_id": training_id})

            if current_registrations < selected_training['max_participants']:
                new_registration = {
                    "user_data": user_data,
                    "training_id": training_id
                }

                inserted_registration = registrations_collection.insert_one(
                    new_registration)
                session['user_registration_id'] = str(
                    inserted_registration.inserted_id)
                return redirect(url_for('signup_confirmation'))
            else:
                return redirect(url_for('training_fully_booked'))
        else:
            return redirect(url_for('error'))


@app.route('/signup_confirmation', methods=['GET'])
def signup_confirmation():
    user_registration_id = session.get('user_registration_id')

    if user_registration_id:
        user_registration = registrations_collection.find_one(
            {"_id": ObjectId(user_registration_id)})

        training_id = user_registration['training_id']
        associated_training = trainings_collection.find_one(
            {"_id": training_id})

        return render_template('signup_confirmation.html', user_registration=user_registration, training=associated_training)
    else:
        return redirect(url_for('error'))


@app.route('/new_training', methods=['GET', 'POST'])
def new_training():
    if request.method == 'POST':
        training_type = request.form['training_type']
        date_time = request.form['date_time']
        address = request.form['address']
        holding = request.form['holding']
        holder = request.form['holder']

        datetime_obj = datetime.datetime.strptime(date_time, '%Y-%m-%d %H:%M')

        new_training = {
            "type": training_type,
            "datetime": datetime_obj,
            "address": address,
            "holding": holding,
            "holder": holder
        }

        trainings_collection.insert_one(new_training)

        return redirect(url_for('index'))

    return render_template('new_training.html')


if __name__ == '__main__':
    app.run(debug=True)
