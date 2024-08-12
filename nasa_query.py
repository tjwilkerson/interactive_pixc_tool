import requests
import json

def query_nasa_data(min_lat, max_lat, min_lng, max_lng):
    url = "https://cmr.earthdata.nasa.gov/search/granules.json"
    params = {
        "collection_concept_id": "C2799438266-POCLOUD",
        "bounding_box": f"{min_lng},{min_lat},{max_lng},{max_lat}",
        "temporal": "2000-01-01T00:00:00Z,2023-12-31T23:59:59Z",
        "page_size": 10,
        "page_num": 1
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to retrieve data: {response.status_code}")

if __name__ == "__main__":
    # Example extent
    min_lat, max_lat = -30.0, -29.0
    min_lng, max_lng = -73.0, -72.0
    try:
        extent_data = query_nasa_data(min_lat, max_lat, min_lng, max_lng)
        print(json.dumps(extent_data, indent=2))
    except Exception as e:
        print(f"Error: {e}")
