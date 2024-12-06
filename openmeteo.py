import openmeteo_requests
import matplotlib.pyplot as plt
import requests_cache
import pandas as pd
from retry_requests import retry

# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession('.cache', expire_after = -1)
retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
openmeteo = openmeteo_requests.Client(session = retry_session)

# Make sure all required weather variables are listed here
# The order of variables in hourly or daily is important to assign them correctly below
url = "https://archive-api.open-meteo.com/v1/archive"
params = {
	"latitude": 7.8526,
	"longitude": 3.9312,
	"start_date": "2000-11-13",
	"end_date": "2024-11-27",
	"daily": ["temperature_2m_max", "precipitation_sum"]
}
responses = openmeteo.weather_api(url, params=params)

# Process first location. Add a for-loop for multiple locations or weather models
response = responses[0]
print(f"Coordinates {response.Latitude()}°N {response.Longitude()}°E")
print(f"Elevation {response.Elevation()} m asl")
print(f"Timezone {response.Timezone()} {response.TimezoneAbbreviation()}")
print(f"Timezone difference to GMT+0 {response.UtcOffsetSeconds()} s")

# Process daily data. The order of variables needs to be the same as requested.
daily = response.Daily()
daily_temperature_2m_max = daily.Variables(0).ValuesAsNumpy()
daily_precipitation_sum = daily.Variables(1).ValuesAsNumpy()

daily_data = {"date": pd.date_range(
	start = pd.to_datetime(daily.Time(), unit = "s", utc = True),
	end = pd.to_datetime(daily.TimeEnd(), unit = "s", utc = True),
	freq = pd.Timedelta(seconds = daily.Interval()),
	inclusive = "left"
)}
daily_data["temperature_2m_max"] = daily_temperature_2m_max
daily_data["precipitation_sum"] = daily_precipitation_sum

daily_dataframe = pd.DataFrame(data = daily_data)
print(daily_dataframe)
fig, ax1 = plt.subplots(figsize=(12, 12))

ax1.plot(daily_data['date'], daily_data["temperature_2m_max"], color='red', label='Temperature Max(°C)')
ax1.plot(daily_data['date'], daily_data['precipitation_sum'], color='blue', label='Precipitation(mm)')

ax1.tick_params(axis='y', labelcolor='black')

ax1.set_xlabel('Date')
ax1.set_ylabel('°C')

fig.suptitle('Weather Data: Temperature Time Series (Model)')

lines_1, labels_1 = ax1.get_legend_handles_labels()
ax1.legend(lines_1, labels_1, loc='upper left')

ax1.grid(True, linestyle='--', alpha=0.6)
fig.autofmt_xdate()

plt.show()