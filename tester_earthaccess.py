import earthaccess

# # Authenticate with Earthdata Login
# earthaccess.login()

# # Define the search parameters
# start_date = "2024-03-01T20:10:54Z"
# end_date = "2024-03-01T20:11:05Z"
# bounding_box = (-0.13698577880859378, 51.484106229235714, -0.04806518554, 51.50708371891835)

# # Search for the SWOT L2 HR PIXC data
# results = earthaccess.search_data(
#     short_name="SWOT_L2_HR_PIXC_2.0",
#     temporal=(start_date, end_date),
#     bounding_box=bounding_box
# )

# # Check how many granules were found
# print(f"Granules found: {len(results)}")

# # Download the granules
# output_directory = "./downloaded_files"
# earthaccess.download(results, local_path=output_directory)

# Authenticate with Earthdata Login
earthaccess.login()

# Define the search parameters
start_date = "2023-04-07T23:00:00Z"
end_date = "2023-04-08T00:00:00Z"
bounding_box = (-180,-90,180,90)

# Search for the SWOT L2 HR PIXC data
results = earthaccess.search_data(
    short_name="SWOT_L2_HR_Raster_1.1",
    temporal=(start_date, end_date),
    bounding_box=bounding_box
)

# Check how many granules were found
print(f"Granules found: {len(results)}")

# Download the granules
output_directory = "./downloaded_files"
earthaccess.download(results, local_path=output_directory)