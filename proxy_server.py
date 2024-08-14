from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import os
import tempfile
import subprocess
from netCDF4 import Dataset

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
        
        return jsonify({'message': 'File downloaded successfully', 'directory': save_directory}), 200

    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}")
        return jsonify({'error': str(e)}), 500

# @app.route('/download_and_process', methods=['POST'])
# def download_and_process():
#     # Get data from the request
#     data = request.json
#     url = data.get('url')

#     if not url:
#         return jsonify({'error': 'No URL provided'}), 400

#     try:
#         # Create a temporary directory to save files
#         with tempfile.TemporaryDirectory() as tmpdirname:
#             # Download the file
#             filename = os.path.basename(url)
#             local_filename = os.path.join(tmpdirname, filename)

#             print(f"Attempting to download file from URL: {url}")
#             response = requests.get(url, stream=False, timeout=(100, 200))  # Use .netrc for authentication
#             if response.status_code == 200:
#                 with open(local_filename, 'wb') as f:
#                     for chunk in response.iter_content(chunk_size=8192):
#                         f.write(chunk)

#                 print(f"File successfully downloaded to: {local_filename}")

#                 return jsonify({'message': 'File downloaded successfully', 'file_path': local_filename}), 200
#             else:
#                 print(f"Failed to download file. Status code: {response.status_code}")
#                 return jsonify({'error': f'Failed to fetch file with status code {response.status_code}'}), response.status_code

#     except requests.exceptions.RequestException as e:
#         print(f"RequestException: {str(e)}")
#         return jsonify({'error': str(e)}), 500

#     except Exception as e:
#         print(f"An error occurred: {str(e)}")
#         return jsonify({'error': str(e)}), 500

# @app.route('/download_and_process', methods=['POST'])
# def download_and_process():
#     # Get data from the request
#     data = request.json
#     url = data.get('url')

#     if not url:
#         return jsonify({'error': 'No URL provided'}), 400

#     try:
#         # Create a temporary directory to save files
#         with tempfile.TemporaryDirectory() as tmpdirname:
#             # Download the file
#             filename = os.path.basename(url)
#             local_filename = os.path.join(tmpdirname, filename)

#             print(f"Attempting to download file from URL: {url}")
#             response = requests.get(url, stream=True, timeout=(100, 200))  # Use .netrc for authentication
#             if response.status_code == 200:
#                 with open(local_filename, 'wb') as f:
#                     for chunk in response.iter_content(chunk_size=8192):
#                         f.write(chunk)

#                 print(f"File successfully downloaded to: {local_filename}")

#                 return jsonify({'message': 'File downloaded successfully', 'file_path': local_filename}), 200
#             else:
#                 print(f"Failed to download file. Status code: {response.status_code}")
#                 return jsonify({'error': 'Failed to fetch file'}), response.status_code

#     except Exception as e:
#         print(f"An error occurred: {str(e)}")
#         return jsonify({'error': str(e)}), 500



# @app.route('/download_and_process', methods=['POST'])
# def download_and_process():
#     # Get data from the request
#     data = request.json
#     url = data.get('url')
#     geojson_line = data.get('geojson')
#     buffer_distance = float(data.get('buffer_distance'))
#     spacing = float(data.get('spacing'))

#     if not url:
#         return jsonify({'error': 'No URL provided'}), 400

#     try:
#         # Create a temporary directory to save files
#         with tempfile.TemporaryDirectory() as tmpdirname:
#             # Download the file
#             filename = os.path.basename(url)
#             local_filename = os.path.join(tmpdirname, filename)

#             response = requests.get(url, stream=True, timeout=(100, 200))  # Use .netrc for authentication
#             if response.status_code == 200:
#                 with open(local_filename, 'wb') as f:
#                     for chunk in response.iter_content(chunk_size=8192):
#                         f.write(chunk)

#                 # Save GeoJSON line temporarily
#                 temp_geojson_file = os.path.join(tmpdirname, 'geojson_line.json')
#                 with open(temp_geojson_file, 'w') as f:
#                     f.write(geojson_line)

#                 # Call the external Python script to process the data
#                 result = subprocess.run(
#                     ["python", "external_processor.py", local_filename, temp_geojson_file, str(buffer_distance), str(spacing)],
#                     capture_output=True,
#                     text=True
#                 )

#                 if result.returncode == 0:
#                     return jsonify({"result": result.stdout}), 200
#                 else:
#                     return jsonify({"error": result.stderr}), 500

#             else:
#                 return jsonify({'error': 'Failed to fetch file'}), response.status_code

#     except Exception as e:
#         return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)