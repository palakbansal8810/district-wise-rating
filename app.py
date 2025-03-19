from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
import joblib
import pandas as pd
import re
import requests




app = Flask(__name__)
CORS(app)  # allow CORS for all domains on all routes.
app.config['CORS_HEADERS'] = 'Content-Type'

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
@cross_origin()
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
def extract_date_time(full_time):
    if not full_time or full_time == "N/A":
        return "N/A", "N/A"

    parts = full_time.split(" / ")  
    clean_time = parts[-1]  

    date_time_parts = clean_time.split(", ")
    date = f"{date_time_parts[0].strip()}, {date_time_parts[1].strip()}"  
    time1 = date_time_parts[2].split(" (IST)")[0].strip() if len(date_time_parts) > 1 else "N/A"

    return date, time1

def get_news(location):
    url = f"https://timesofindia.indiatimes.com/topic/{location}-case"

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--log-level=3")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--disable-blink-features=AutomationControlled")

    driver = webdriver.Chrome(options=options)
    driver.get(url)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    articles = soup.find_all("div", class_="uwU81")

    news_data = []
    for article in articles:
        title_tag = article.find("span")
        link_tag = article.find("a", href=True)
        time_tag = article.find("div", class_="ZxBIG")

        if title_tag and link_tag:
            title = title_tag.text.strip()
            link = link_tag["href"]
            full_time = time_tag.text.strip() if time_tag else "N/A"
            
            date, time1 = extract_date_time(full_time)
            news_data.append({"title": title, "date": date, "time": time1, "link": link})

    return news_data

@app.route('/news', methods=['POST'])
@cross_origin()
def fetch_news():
    data = request.get_json()
    
    if not data or "location" not in data:
        return jsonify({"error": "Please provide a location in JSON format"}), 400

    location = data["location"]
    news = get_news(location)
    return jsonify(news)

if __name__ == '_main_':
    app.run(debug=True)