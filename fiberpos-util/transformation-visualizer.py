# Instead of appending, initialize an array
# No wild card imports
import desimodel.io
from desimodel.focalplane import xy2radec
import numpy as np
from astropy.table import Column
from pylab import *
from circle import Circle

fp = desimodel.io.load_fiberpos()  #- load the fiberpos.fits file
telra, teldec = 10.0, 20.0   #- telescope central pointing at this RA,dec

# Create circles at each fiberpos
circles = []
for i in range(len(fp['X'])):
    circles.append(Circle(fp['X'][i], fp['Y'][i], 6))

# circles = [Circle(-200, -300, 6)]

# Aggregate transformed points from each circle
ra_col = np.array([])
dec_col = np.array([])
for c in circles:
    x, y = c.get_points(50)
    ra, dec = xy2radec(telra, teldec, Column(x), Column(y))
    ra_col = append(ra_col, ra)
    dec_col = append(dec_col, dec)

ion()
figure(figsize=(8, 4))
# subplot(121)
# plot(fp['X'], fp['Y'], '.'); xlabel('X [mm]'); ylabel('Y [mm]')
ax = subplot(121)
plot(ra_col, dec_col, '.'); xlabel('RA [degrees]'); ylabel('dec [degrees]')

xlim([10.80, 10.90])
ylim([18.75, 18.85])

# axis_x, axis_y = zip(*c.get_axis())
# ra, dec = xy2radec(telra, teldec, Column(axis_x), Column(axis_y))
# ra1 = ra[:1]
# ra2 = ra[2:]
# dec1 = dec[:1]
# dec2 = dec[2:]
# plot(ra1, dec1, 'g.')
# plot(ra2, dec2, 'r.')

# xlim([8.5, 9])
# ylim([21, 21.5])

# xlim([8.5, 11.5])
# ylim([18.5, 21.5])
