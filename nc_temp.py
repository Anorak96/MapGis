from netCDF4 import Dataset
import numpy as np
from mpl_toolkits.basemap import Basemap
import matplotlib.pyplot as plt

ncdf = Dataset(r'data\cdf\data_0.nc')
var = ncdf.variables['stl1']
# ['number', 'valid_time', 'latitude', 'longitude', 'expver', 'stl1', 'swvl1', 'ssr', 'evabs', 'evavt', 'u10', 'v10', 'sp', 'tp', 'lai_hv']

lats = ncdf.variables['latitude'][:]
lons = ncdf.variables['longitude'][:]
time = ncdf.variables['valid_time'][:]
temperature = ncdf.variables['stl1'][:]
temperature_celsius = temperature - 273.15

mp = Basemap(projection='merc', llcrnrlon= -0.628376, llcrnrlat= 3.053848, urcrnrlon= 18.7138812, urcrnrlat= 14.330965, resolution='i')

long, lati = np.meshgrid(lons, lats)
x,y = mp(long, lati)

c_scheme = mp.pcolor(x, y, np.squeeze(temperature_celsius[0,:,:]), cmap='jet')

mp.drawcoastlines()
mp.drawstates()
mp.drawcountries()

cbar = mp.colorbar(c_scheme, location = 'right', pad = '10%')

plt.title('Temperature')
plt.show()