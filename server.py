from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

def query_nasa_data(min_lat, max_lat, min_lng, max_lng, start_date, end_date):
    url = "https://cmr.earthdata.nasa.gov/search/granules.json"
    page_size = 2000  # Set the maximum page size to retrieve as many results as possible
    params = {
        "collection_concept_id": "C2799438266-POCLOUD",
        "bounding_box": f"{min_lng},{min_lat},{max_lng},{max_lat}",
        "temporal": f"{start_date},{end_date}",
        "page_size": page_size,
    }
    results = []
    page_num = 1

    while True:
        params['page_num'] = page_num
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            entries = data.get('feed', {}).get('entry', [])
            if not entries:
                break
            results.extend(entries)
            if len(entries) < page_size:
                break
            page_num += 1
        else:
            raise Exception(f"Failed to retrieve data: {response.status_code}")

    return {'feed': {'entry': results}}

@app.route('/query', methods=['POST'])
def query_nasa():
    data = request.json
    min_lat = data['min_lat']
    max_lat = data['max_lat']
    min_lng = data['min_lng']
    max_lng = data['max_lng']
    start_date = data['start_date']
    end_date = data['end_date']

    try:
        result = query_nasa_data(min_lat, max_lat, min_lng, max_lng, start_date, end_date)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
