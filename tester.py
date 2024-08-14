import subprocess

output_directory = "tempfolder"

command = [
    "podaac-data-downloader",
    "-c", "SWOT_L2_HR_PIXC_2.0",      # Use the collection short name
    "-d", output_directory,      # Specify the output directory
    "--start-date", "2024-05-04T19:48:32Z",
    "--end-date", "2024-05-14T19:48:43Z",
    "-b=-0.13698577880859378,51.484106229235714,-0.04806518554,52.50708371891835"  # Bounding box, formatted as a single argument
]

try:
    subprocess.run(command, check=True)
    print("File downloaded successfully.")
except subprocess.CalledProcessError as e:
    print(f"An error occurred: {e}")
