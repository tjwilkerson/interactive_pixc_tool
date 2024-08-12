// Initialize the map
const map = L.map('map').setView([51.505, -0.09], 13);

// Define the standard map tile layer
const standardTiles = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
}).addTo(map);

// Define the satellite map tile layer using Esri
const satelliteTiles = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
    maxZoom: 19,
    attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
});

// Add a base layer control to switch between standard and satellite views
const baseLayers = {
    "Standard": standardTiles,
    "Satellite": satelliteTiles
};

L.control.layers(baseLayers).addTo(map);

// Track the drawing state
let drawingMode = false;
let drawnLine = null;
let markers = [];

// Function to send the drawn line's extent and date range to the server
function sendExtentToServer(minLat, maxLat, minLng, maxLng) {
    const startDateInput = document.getElementById('start-date').value;
    const endDateInput = document.getElementById('end-date').value;

    if (!startDateInput || !endDateInput) {
        alert("Please select a start and end date.");
        return;
    }

    // Create the data object with the extent and date range
    const extentData = {
        min_lat: minLat,
        max_lat: maxLat,
        min_lng: minLng,
        max_lng: maxLng,
        start_date: startDateInput + 'T00:00:00Z',  // Start date with time for API format
        end_date: endDateInput + 'T23:59:59Z'      // End date with time for API format
    };

    console.log('Sending extent to server:', extentData);

    // Send the data to the server
    fetch('http://localhost:5000/query', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(extentData)
    })
    .then(response => response.json())
    .then(data => {
        console.log('Received data:', data);
        filterAndPopulateDatesDropdown(data); // Populate the dropdown with filtered dates
    })
    .catch(error => console.error('Error:', error));
}

// Function to filter the returned granules based on the selected date range and populate the dropdown
function filterAndPopulateDatesDropdown(data) {
    const startDateInput = document.getElementById('start-date').value;
    const endDateInput = document.getElementById('end-date').value;

    if (!startDateInput || !endDateInput) {
        alert("Please select a start and end date.");
        return;
    }

    // Parse input dates
    const startDate = new Date(startDateInput);
    const endDate = new Date(endDateInput);

    console.log(`Filtering dates between ${startDate.toISOString()} and ${endDate.toISOString()}`);

    const datesDropdown = document.getElementById('dates-dropdown');
    datesDropdown.innerHTML = '<option value="">--Select a Date--</option>'; // Reset options

    const granules = data.feed.entry; // Assuming this is where the granule data is

    console.log(`Number of granules received: ${granules.length}`);

    granules.forEach(granule => {
        const timeStart = new Date(granule.time_start);
        console.log(`Checking date: ${timeStart.toISOString()}`);

        // Find the NetCDF download link
        const netCDFLink = granule.links.find(link => link.href.endsWith('.nc') && link.rel.includes('data'));

        if (timeStart >= startDate && timeStart <= endDate && netCDFLink) {
            console.log(`Adding date: ${timeStart.toISOString()}`);
            const option = document.createElement('option');
            option.value = netCDFLink.href; // Use the download link as the value
            option.textContent = `Start: ${granule.time_start}`;
            datesDropdown.appendChild(option);
        }
    });
}

// Event listener for date selection from the dropdown
document.getElementById('dates-dropdown').addEventListener('change', function(event) {
    const selectedNetCDFLink = event.target.value;
    if (selectedNetCDFLink) {
        alert(`Download selected NetCDF file here: ${selectedNetCDFLink}`);
    
    }
});

// Function to handle file input
function handleFileInput(event) {
    const file = event.target.files[0];
    if (!file) {
        alert("No file selected.");
        return;
    }
    console.log('NetCDF file selected:', file.name);

    // Optionally, display the file name on the page
    document.getElementById('file-name-display').innerText = `Selected file: ${file.name}`;
}

// Add event listener to the file input element
document.getElementById('file-input').addEventListener('change', handleFileInput);

// Add event listener for the Process Data button
document.getElementById('process-button').addEventListener('click', () => {
    const bufferDistance = document.getElementById('buffer-distance').value;
    const spacing = document.getElementById('spacing').value;

    if (!drawnLine || drawnLine.getLatLngs().length === 0) {
        alert("Please draw a line on the map first.");
        return;
    }

    const geoJsonLine = drawnLine.toGeoJSON();
    const fileInput = document.getElementById('file-input');
    if (fileInput.files.length === 0) {
        alert("Please upload a NetCDF file.");
        return;
    }
    const netCDFFile = fileInput.files[0];

    const formData = new FormData();
    formData.append('netcdf', netCDFFile);
    formData.append('geojson', JSON.stringify(geoJsonLine));
    formData.append('buffer_distance', bufferDistance);
    formData.append('spacing', spacing);

    fetch('http://localhost:5000/process', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        console.log('Processing result:', data);
        alert('Data processed successfully. Check console for details.');
    })
    .catch(error => console.error('Error processing data:', error));
});

// Enable drawing mode when the button is clicked
document.getElementById('draw-button').addEventListener('click', () => {
    drawingMode = !drawingMode; // Toggle drawing mode
    if (drawingMode) {
        alert("Drawing mode enabled. Click on the map to draw a line.");
        drawnLine = L.polyline([], { color: 'red' }).addTo(map); // Create a new line
    } else {
        alert("Drawing mode disabled.");
    }
});

// Clear the drawn line when the clear button is clicked
document.getElementById('clear-button').addEventListener('click', () => {
    if (drawnLine) {
        map.removeLayer(drawnLine); // Remove the line from the map
        drawnLine = null;           // Reset the drawn line variable
    }
    markers.forEach(marker => map.removeLayer(marker)); // Remove all markers
    markers = []; // Clear the markers array
    alert("All lines and markers cleared.");
});

// Function to handle drawing on the map
map.on('click', function(e) {
    if (drawingMode) {
        if (drawnLine.getLatLngs().length === 0) {
            // Add a marker for the first click
            const marker = L.circleMarker(e.latlng, { color: 'red', radius: 5 }).addTo(map);
            markers.push(marker);
        }
        // Add clicked point to the drawn line
        drawnLine.addLatLng(e.latlng);
    }
});

// Function to calculate the extent of the drawn line
function calculateLineExtent() {
    if (drawnLine) {
        const coordinates = drawnLine.getLatLngs();
        let minLat = coordinates[0].lat, maxLat = coordinates[0].lat;
        let minLng = coordinates[0].lng, maxLng = coordinates[0].lng;

        coordinates.forEach(point => {
            if (point.lat < minLat) minLat = point.lat;
            if (point.lat > maxLat) maxLat = point.lat;
            if (point.lng < minLng) minLng = point.lng;
            if (point.lng > maxLng) maxLng = point.lng;
        });

        // Call function to send extent to server
        sendExtentToServer(minLat, maxLat, minLng, maxLng);
    } else {
        alert("No line drawn yet.");
    }
}

// Add event listener to calculate the extent when the button is clicked
document.getElementById('calculate-extent-button').addEventListener('click', calculateLineExtent);