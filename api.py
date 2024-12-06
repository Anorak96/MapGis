import requests
import time
from datetime import datetime, timedelta
import folium
from folium.plugins import HeatMapWithTime

API_KEY = "9c835bd5ab284dbe87e73324241111"
# lat, lon =  9.176, 7.181
heat_data_time = []
locations = [
    {"state": "Abia", "lat": 5.5320, "lon": 7.4860},
    {"state": "Adamawa", "lat": 9.3265, "lon": 12.3984},
    {"state": "Akwa Ibom", "lat": 5.0369, "lon": 7.9128},
    {"state": "Anambra", "lat": 6.2100, "lon": 7.0700},
    {"state": "Bauchi", "lat": 10.3142, "lon": 9.8463},
    {"state": "Bayelsa", "lat": 4.8450, "lon": 6.0794},
    {"state": "Benue", "lat": 7.1904, "lon": 8.1291},
    {"state": " Borno", "lat": 11.8333, "lon": 13.1500},
    {"state": "Cross River", "lat": 5.9651, "lon": 8.5986},
    {"state": "Delta", "lat": 5.8904, "lon": 5.6800},
    {"state": "Ebonyi", "lat": 6.2518, "lon": 8.0873},
    {"state": "Edo", "lat": 6.5244, "lon": 5.8987},
    {"state": "Ekiti", "lat": 7.7186, "lon": 5.3125},
    {"state": "Enugu", "lat": 6.5244, "lon": 7.5170},
    {"state": "Gombe", "lat": 10.2897, "lon": 11.1673},
    {"state": "Imo", "lat": 5.5720, "lon": 7.0588},
    {"state": "Jigawa", "lat": 12.1447, "lon": 9.9903},
    {"state": "Kaduna", "lat": 10.5105, "lon": 7.4165},
    {"state": "Kano", "lat": 12.0022, "lon": 8.5919},
    {"state": "Katsina", "lat": 12.9887, "lon": 7.6223},
    {"state": "Kebbi", "lat": 12.4539, "lon": 4.1975},
    {"state": "Kogi", "lat": 7.7339, "lon": 6.6906},
    {"state": "Kwara", "lat": 8.9669, "lon": 4.5624},
    {"state": "Lagos", "lat": 6.5244, "lon": 3.3792},
    {"state": "Nasarawa", "lat": 8.5380, "lon": 8.3659},
    {"state": "Niger", "lat": 9.9306, "lon": 5.5983},
    {"state": "Ogun", "lat": 7.1475, "lon": 3.3619},
    {"state": "Ondo", "lat": 7.2500, "lon": 5.1962},
    {"state": "Osun", "lat": 7.5629, "lon": 4.5200},
    {"state": "Oyo", "lat": 7.8734, "lon": 3.9324},
    {"state": "Plateau", "lat": 9.2182, "lon": 9.5175},
    {"state": "Rivers", "lat": 4.8242, "lon": 7.0336},
    {"state": "Sokoto", "lat": 13.0059, "lon": 5.2476},
    {"state": "Taraba", "lat": 8.8937, "lon": 11.3764},
    {"state": "Yobe", "lat": 12.0001, "lon": 11.5001},
    {"state": "Zamfara", "lat": 12.1228, "lon": 6.2236},
    {"state": "Federal Capital Territory (Abuja)", "lat": 9.0579, "lon": 7.4951}
]

n = 0
for _ in range(50):
    current_heat_data = []
    for location in locations:
        url = f"https://api.weatherapi.com/v1/current.json?key={API_KEY}&q={location['lat']}, {location['lon']}&aqi=no"
        response = requests.get(url).json()

        temp = response['current']['temp_c']
        current_heat_data.append([location["lat"], location["lon"], temp])
    n = n + 1
    print(n)

    heat_data_time.append(current_heat_data)
    time.sleep(1)

weather_map = folium.Map(location=[9.176, 7.181], zoom_start=10)

time_index = [
    (datetime.now() + k * timedelta(hours=1)).strftime("%Y-%m-%d %H:%M") for k in range(len(heat_data_time))
]

HeatMapWithTime(heat_data_time, index=time_index, auto_play=True, max_opacity=0.8).add_to(weather_map)

weather_map.save("heatmap.html")