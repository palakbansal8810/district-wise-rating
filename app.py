from flask import Flask, request, jsonify
import joblib
import pandas as pd
import re
import requests

app = Flask(__name__)

model = joblib.load('model.pkl')
district_mapping = pd.read_csv('dataset/district_mapping.csv')
state_mapping = pd.read_csv('dataset/state_mapping.csv')

API_KEY = "abf2228f88dc447083607cb6ba0f38f5"

def get_location(lat, lng, api_key):
    url = f"https://api.opencagedata.com/geocode/v1/json?q={lat}+{lng}&key={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data['results']:
            components = data['results'][0]['components']
            district = components.get('state_district', None)
            state = components.get('state', None)
            return district, state
    return None, None

def predict_rating(year, district, state):
    
    district = re.sub(r'[^a-zA-Z0-9]', '', district).lower()
    state = re.sub(r'[^a-zA-Z0-9]', '', state).lower()

    if district in district_mapping['District'].values:
        district = district_mapping[district_mapping['District'] == district]['Encoded_Value'].values[0]
    else:
        district = 0

    if state in state_mapping['State'].values:
        state = state_mapping[state_mapping['State'] == state]['Encoded_Value'].values[0]
    else:
        state = 0

    result = model.predict([[state, district, year]])
    return result[0]

@app.route('/predict', methods=['POST'])
def predict():
    
    data = request.json
    lat = data.get('latitude')
    lng = data.get('longitude')
    year = 2025

    if not lat or not lng:
        return jsonify({"error": "Latitude and Longitude are required"}), 400

    district, state = get_location(lat, lng, API_KEY)
    if not district:
        district = 'north'
    
    safety_index = predict_rating(year, district, state)
    return jsonify({
        "district": district,
        "state": state,
        "year": year,
        "safety_index": safety_index
    })

if __name__ == '__main__':
    app.run(debug=True)
