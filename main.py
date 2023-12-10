from flask import Flask, render_template, send_from_directory, jsonify
import datetime
import os
import time
from tuya_connector import TuyaOpenAPI
import csv
from threading import Thread

# Your Tuya credentials and API endpoint
ACCESS_ID = "4c8jd8mfgh85g95te7cr"
ACCESS_KEY = "b6c7d79c2648457e845eace7ba349a6c"
API_ENDPOINT = "https://openapi.tuyaeu.com"

# Initialize TuyaOpenAPI
openapi = TuyaOpenAPI(API_ENDPOINT, ACCESS_ID, ACCESS_KEY)
openapi.connect()

# Initialize Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'

# Lists to store real-time data
realtime_data = {}

# Function to fetch and update real-time data
def fetch_realtime_data():
    try:
        while True:
            response = openapi.get('/v1.0/iot-03/devices/status?device_ids=bf1e6e7d32374310dd3uqk')
            print("API Response:", response)  # Debug
            current_data = response['result'][0]['status']

            # Extract relevant data
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print("Current Time:", current_time)  # Debug

            current = next((item for item in current_data if item['code'] == 'cur_current'), {}).get('value', 0)
            power = next((item for item in current_data if item['code'] == 'cur_power'), {}).get('value', 0) / 10.0
            voltage = next((item for item in current_data if item['code'] == 'cur_voltage'), {}).get('value', 0) / 10.0

            # Calculate kWh per minute
            kwh_minute = (power / 1000.0) * (1 / 60.0)  # Convert watts to kilowatts and calculate over 1 minute

            # Calculate cost per minute based on consumption and fixed cost per kWh
            cost_minute = kwh_minute * 8.84  # Assuming 8.84 is the cost per kWh

            # Update real-time data
            realtime_data['Timestamp'] = current_time
            realtime_data['Current'] = current
            realtime_data['Voltage'] = voltage
            realtime_data['Power'] = power
            realtime_data['kWh per Minute'] = kwh_minute
            realtime_data['Cost per Minute'] = cost_minute

            # Append data to the CSV file
            append_to_csv(realtime_data)

            # Sleep for 60 seconds before fetching data again
            time.sleep(60)

    except Exception as e:
        print(f"An error occurred: {str(e)}")

# Function to append data to a CSV file
def append_to_csv(data):
    file_path = 'tuya_data.csv'
    write_header = not os.path.exists(file_path)

    with open(file_path, mode='a', newline='') as file:
        fieldnames = ['Timestamp', 'Current', 'Voltage', 'Power', 'kWh per Minute', 'Cost per Minute']
        writer = csv.DictWriter(file, fieldnames=fieldnames)

        if write_header:
            writer.writeheader()

        writer.writerow(data)

# Function to read data from a CSV file
def read_csv_data(file_path):
    timestamps, currents, voltages, powers, kwh_per_minute, cost_per_minute = [], [], [], [], [], []

    with open(file_path, mode='r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            timestamps.append(row['Timestamp'])
            currents.append(float(row['Current']))
            voltages.append(float(row['Voltage']))
            powers.append(float(row['Power']))
            kwh_per_minute.append(float(row['kWh per Minute']))
            cost_per_minute.append(float(row['Cost per Minute']))

    return timestamps, currents, voltages, powers, kwh_per_minute, cost_per_minute

# Define a route to render the homepage with real-time data and charts
@app.route('/')
def home():
    # Read historical data from the CSV file
    timestamps, currents, voltages, powers, kwh_per_minute, cost_per_minute = read_csv_data('tuya_data.csv')

    # Pass the historical data to the template
    return render_template('index.html', realtime_data=realtime_data, timestamps=timestamps)

# Define a route to update real-time data and return as JSON
@app.route('/update_realtime_data')
def update_realtime_data():
    try:
        response = openapi.get('/v1.0/iot-03/devices/status?device_ids=bf1e6e7d32374310dd3uqk')
        print("API Response:", response)  # Debug
        current_data = response['result'][0]['status']

        # Extract relevant data
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print("Current Time:", current_time)  # Debug

        current = next((item for item in current_data if item['code'] == 'cur_current'), {}).get('value', 0)
        power = next((item for item in current_data if item['code'] == 'cur_power'), {}).get('value', 0) / 10.0
        voltage = next((item for item in current_data if item['code'] == 'cur_voltage'), {}).get('value', 0) / 10.0

        # Calculate kWh per minute
        kwh_minute = (power / 1000.0) * (1 / 60.0)  # Convert watts to kilowatts and calculate over 1 minute

        # Calculate cost per minute based on consumption and fixed cost per kWh
        cost_minute = kwh_minute * 8.84  # Assuming 8.84 is the cost per kWh

        # Update real-time data
        realtime_data['Timestamp'] = current_time
        realtime_data['Current'] = current
        realtime_data['Voltage'] = voltage
        realtime_data['Power'] = power
        realtime_data['kWh per Minute'] = kwh_minute
        realtime_data['Cost per Minute'] = cost_minute

        # Append data to the CSV file
        append_to_csv(realtime_data)

        # Send the updated data as JSON
        return jsonify(realtime_data)

    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == '__main__':
    # Start a background thread to fetch and update real-time data
    data_fetch_thread = Thread(target=fetch_realtime_data)
    data_fetch_thread.daemon = True
    data_fetch_thread.start()

    # Run the Flask application
    app.run(debug=True)

