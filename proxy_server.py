from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import os
import tempfile
import subprocess
from netCDF4 import Dataset
from pathlib import Path
import geopandas as gpd
import sys
import pandas as pd
from io import BytesIO
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')


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



    

@app.route('/download_and_process', methods=['POST'])
def download_and_process():
    data = request.json
    
    # Extract the start date, end date, and bounding box from the request data
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    min_lat = data.get('min_lat')
    max_lat = data.get('max_lat')
    min_lng = data.get('min_lng')
    max_lng = data.get('max_lng')
    geojson_line = data.get('geojson')
    buffer_distance = float(data.get('buffer_distance'))
    spacing = float(data.get('spacing'))

    if not start_date or not end_date or not min_lat or not max_lat or not min_lng or not max_lng:
        return jsonify({'error': 'Missing required parameters'}), 400

    try:
        # Format the start and end dates to remove milliseconds
        formatted_start_date = start_date.split('.')[0] + "Z"
        formatted_end_date = end_date.split('.')[0] + "Z"

        save_directory = 'tempdir'
        if not os.path.exists(save_directory):
            os.makedirs(save_directory)

        # Create the bounding box argument as a single string
        bounding_box = f"-b={min_lng},{min_lat},{max_lng},{max_lat}"

        # Construct the podaac-data-downloader command
        command = [
            "podaac-data-downloader",
            "-c", "SWOT_L2_HR_PIXC_2.0",  # Use the correct collection short name
            "-d", save_directory,  # Specify the output directory
            "--start-date", formatted_start_date,
            "--end-date", formatted_end_date,
            bounding_box  # Bounding box as a single argument
        ]

        # Run the downloader command
        subprocess.run(command, check=True)
        print("File downloaded successfully.")

        # Assume the file is downloaded with a known file name structure, or you could iterate over files in the directory
        downloaded_file = next(Path(save_directory).glob('*.nc'))  # Find the first .nc file in the directory

        # Save GeoJSON line temporarily
        temp_geojson_file = os.path.join(save_directory, 'geojson_line.json')
        with open(temp_geojson_file, 'w') as f:
            f.write(geojson_line)

        print(downloaded_file)
        print(temp_geojson_file)
        print(buffer_distance)
        print(spacing)
        
        # Call the external Python script to process the data
        result = subprocess.run(
            [sys.executable, "external_processor.py", str(downloaded_file), str(temp_geojson_file), str(buffer_distance), str(spacing)],
            capture_output=True,
            text=True
        )
        print(f'result.returncode: {result.returncode}')
        if result.returncode == 0:
            result_json = result.stdout
            df = pd.read_json(result_json)
            print(df.head())

            # Plot the data
            fig = plt.figure(figsize=(15, 8))
            ax = fig.add_subplot(111)

            # Apply filter to keep points where classification is greater than 2 and not 5
            df_filtered = df[(df['classification'] > 2) & (df['classification'] != 5)]

            sc = ax.scatter(df_filtered['cumulative_distance'], df_filtered['height'], 
                            c=df_filtered['geolocation_qual'], cmap='viridis', zorder=2, label='SWOT WSE data')

            ax.legend()
            ax.set_title('Water Surface Elevation vs Distance for selected reach')
            ax.set_xlabel('Distance Downstream')
            ax.set_ylabel('WSE (m)')

            # Add color bar
            cbar = plt.colorbar(sc, ax=ax)
            cbar.set_label('Coherent Power')

            # Save plot to a BytesIO object
            img = BytesIO()
            plt.savefig(img, format='png')
            img.seek(0)

            return send_file(img, mimetype='image/png')

        else:
            return jsonify({"error": result.stderr}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)