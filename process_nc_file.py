from flask import Flask, request, jsonify
from flask_cors import CORS
import geopandas as gpd
import pandas as pd
import xarray as xr
from shapely.geometry import MultiPoint, LineString
from netCDF4 import Dataset
import numpy as np
from scipy.spatial import cKDTree
import tempfile
import os

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

def process_data(netcdf_path, geojson_line, buffer_distance, spacing):
    # Load NetCDF file
    nc = Dataset(netcdf_path, 'r')
    pixel_cloud = nc.groups['pixel_cloud']

    # Extract variables
    latitude = pixel_cloud.variables['latitude'][:]
    longitude = pixel_cloud.variables['longitude'][:]
    height = pixel_cloud.variables['height'][:]
    water_frac = pixel_cloud.variables['water_frac'][:]
    coherent_power = pixel_cloud.variables['coherent_power'][:]
    classification = pixel_cloud.variables['classification'][:]
    missed_detection_rate = pixel_cloud.variables['missed_detection_rate'][:]
    geolocation_qual = pixel_cloud.variables['geolocation_qual'][:]
    nc.close()

    # Create a pandas DataFrame
    df_PIXC = pd.DataFrame({
        'latitude': latitude,
        'longitude': longitude,
        'height': height,
        'water_frac': water_frac,
        'coherent_power': coherent_power,
        'classification': classification,
        'missed_detection_rate': missed_detection_rate,
        'geolocation_qual': geolocation_qual
    })

    # Convert the DataFrame to an xarray Dataset
    ds = xr.Dataset.from_dataframe(df_PIXC)

    # Convert GeoJSON line to GeoDataFrame
    geojson_gdf = gpd.GeoDataFrame.from_features(geojson_line['features'])
    river = geojson_gdf.set_crs("EPSG:4326")

    # Buffer the line
    river_buffered = river.buffer(buffer_distance, cap_style='flat')
    river_buffered_gdf = gpd.GeoDataFrame(geometry=river_buffered, crs=river.crs)

    # Interpolate points along the line
    def interpolate_points(line, distance):
        num_points = int(line.length / distance)
        return MultiPoint([line.interpolate(i * distance) for i in range(num_points + 1)])

    # Apply interpolation
    points_gdf = river.geometry.apply(lambda x: interpolate_points(x, spacing))
    points_gdf = points_gdf.explode(index_parts=True).reset_index(drop=True)
    river_points = gpd.GeoDataFrame(geometry=points_gdf)

    # Calculate cumulative distance
    def calculate_cumulative_distance(gdf):
        gdf['prev_geometry'] = gdf['geometry'].shift()
        gdf['distance_to_prev'] = gdf.apply(lambda row: row['geometry'].distance(row['prev_geometry']) if pd.notna(row['prev_geometry']) else 0, axis=1)
        gdf['cumulative_distance'] = gdf['distance_to_prev'].cumsum()
        return gdf

    river = calculate_cumulative_distance(river_points)
    river.reset_index(drop=True, inplace=True)

    river_cum_dis = river['cumulative_distance'].values

    river_buffered_gdf = river_buffered_gdf.to_crs('epsg:4326')

    # Convert 'ds' to GeoDataFrame and clip to buffer
    ds_gdf = gpd.GeoDataFrame({
        'latitude': latitude,
        'longitude': longitude,
        'height': height,
        'water_frac': water_frac,
        'coherent_power': coherent_power,
        'classification': classification,
        'missed_detection_rate': missed_detection_rate,
        'geolocation_qual': geolocation_qual
    }, geometry=gpd.points_from_xy(df_PIXC['longitude'], df_PIXC['latitude']), crs="EPSG:4326")
    ds_clipped = gpd.sjoin(ds_gdf, river_buffered_gdf, how='inner', predicate='within')

    # Find nearest river point to each ds point
    river = river.to_crs('EPSG:32633')  # You may need to dynamically determine the EPSG code
    ds_coords_utm = np.column_stack((ds_clipped.geometry.x, ds_clipped.geometry.y))
    river_coords_utm = np.column_stack((river.geometry.x, river.geometry.y))
    tree_river = cKDTree(river_coords_utm)

    distances, indices = tree_river.query(ds_coords_utm)
    nearest_GNSS_dist = river_cum_dis[indices]
    ds_clipped['nearest_GNSS_dist'] = nearest_GNSS_dist
    ds_clipped['nearest_index'] = indices
    ds_clipped['distance_to_nearest'] = distances

    # Merge DataFrames
    columns_to_keep = [col for col in ds_clipped.columns if col not in river.columns or col == 'nearest_index']
    ds_clipped_subset = ds_clipped[columns_to_keep]
    merged_df = river.merge(ds_clipped_subset, left_index=True, right_on='nearest_index', how='left')

    return merged_df

@app.route('/process', methods=['POST'])
def process_request():
    netcdf_file = request.files.get('netcdf')
    geojson_line = request.form.get('geojson')
    buffer_distance = float(request.form.get('buffer_distance'))
    spacing = float(request.form.get('spacing'))

    # Save NetCDF file temporarily
    temp_nc_file = tempfile.NamedTemporaryFile(delete=False)
    netcdf_file.save(temp_nc_file.name)

    # Process the data
    try:
        geojson_data = eval(geojson_line)  # Use JSON deserialization instead of eval in production
        result = process_data(temp_nc_file.name, geojson_data, buffer_distance, spacing)
        os.unlink(temp_nc_file.name)  # Clean up temp file

        # Return result as JSON
        return jsonify(result.to_json()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
