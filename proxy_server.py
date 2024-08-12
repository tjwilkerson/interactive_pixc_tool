from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

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

@app.route('/download', methods=['GET'])
def download_file():
    url = request.args.get('url')
    if not url:
        return {'error': 'No URL provided'}, 400

    response = requests.get(url, stream=True)  # Use .netrc for authentication

    if response.status_code == 200:
        # Save the file temporarily
        file_path = '/tmp/temp.nc'
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return send_file(file_path, as_attachment=True, download_name='SWOT_data.nc')
    else:
        return {'error': 'Failed to fetch file'}, response.status_code

if __name__ == '__main__':
    app.run(debug=True)
