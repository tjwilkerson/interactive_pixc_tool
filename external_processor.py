import sys
import geopandas as gpd
import pandas as pd
import xarray as xr
from shapely.geometry import MultiPoint
from netCDF4 import Dataset
import numpy as np
from scipy.spatial import cKDTree
from pyproj import CRS

def process_data(netcdf_path, geojson_path, buffer_distance, spacing):
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

    # Dynamically detect the UTC EPSG code:
    def latlon_to_utm_epsg(min_lat, max_lat, min_lon, max_lon):
        # Use the central longitude of the bounding box to determine the UTM zone
        central_lon = (min_lon + max_lon) / 2
        central_lat = (min_lat + max_lat) / 2
        
        # Determine the UTM zone
        utm_zone = int((central_lon + 180) / 6) + 1
        
        # Determine the hemisphere based on latitude
        if central_lat >= 0:
            epsg_code = CRS.from_dict({'proj': 'utm', 'zone': utm_zone, 'south': False}).to_epsg()
        else:
            epsg_code = CRS.from_dict({'proj': 'utm', 'zone': utm_zone, 'south': True}).to_epsg()
        
        return epsg_code
    
    min_lat, max_lat = latitude.min(), latitude.max()
    min_lon, max_lon = longitude.min(), longitude.max()
    epsg_code = latlon_to_utm_epsg(min_lat, max_lat, min_lon, max_lon)

    # Convert GeoJSON line to GeoDataFrame
    geojson_gdf = gpd.read_file(geojson_path)
    river = geojson_gdf.to_crs(epsg_code)

    # Buffer the line
    river_buffered = river.buffer(float(buffer_distance), cap_style='flat')
    river_buffered_gdf = gpd.GeoDataFrame(geometry=river_buffered, crs=river.crs)

    # Interpolate points along the line
    def interpolate_points(line, distance):
        num_points = int(line.length / distance)
        return MultiPoint([line.interpolate(i * distance) for i in range(num_points + 1)])

    # Apply interpolation
    points_gdf = river.geometry.apply(lambda x: interpolate_points(x, float(spacing)))
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
    river = river.to_crs(epsg_code)  # You may need to dynamically determine the EPSG code
    ds_clipped = ds_clipped.to_crs(epsg_code)
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
    merged_df = pd.DataFrame(merged_df.drop(columns=['geometry','prev_geometry']))
    merged_df = merged_df.reset_index(drop=True)  # Resets the index, making it unique

    return merged_df

if __name__ == "__main__":
    netcdf_path = sys.argv[1]
    geojson_path = sys.argv[2]
    buffer_distance = float(sys.argv[3])
    spacing = float(sys.argv[4])

    try:
        result = process_data(netcdf_path, geojson_path, buffer_distance, spacing)
        result_json = result.to_json()  # Convert DataFrame to JSON
        print(result_json)  # Output result as JSON
    except Exception as e:
        print(f"Error processing data you dummy: {e}", file=sys.stderr)
        print(result.head())

        

# if __name__ == "__main__":
#     # Expecting arguments: netcdf_path, geojson_path, buffer_distance, spacing
#     netcdf_path = sys.argv[1]
#     geojson_path = sys.argv[2]
#     buffer_distance = float(sys.argv[3])
#     spacing = float(sys.argv[4])

#     try:
#         result = process_data(netcdf_path, geojson_path, buffer_distance, spacing)
#         print(result.to_json())  # Output result as JSON
#     except Exception as e:
#         print(f"Error processing data: {e}", file=sys.stderr)
