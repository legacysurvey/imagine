import desimodel.io
from desimodel.focalplane import xy2radec
import numpy as np
from numpy.linalg import eig, inv
from math import cos, sin
from astropy.table import Column
from pylab import * # change this
from circle import Circle, Ellipse
import json

telra, teldec = 0, 0   #- telescope central pointing at this RA,dec
fp = desimodel.io.load_fiberpos()  #- load the fiberpos.fits file

def xy2xyz(x, y):
    """Transforms points from focal plane coordinates to points on
    a unit sphere
    """
    r_rad = np.radians(get_radius_deg(x, y))
    q = np.degrees(np.arctan2(y, x))
    q_rad = np.radians(q)
    
    x1 = np.cos(r_rad)
    y1 = -np.sin(r_rad)
    z1 = np.zeros_like(x1)

    x2 = x1
    y2 = y1*np.cos(q_rad)           # z1=0 so drop sin(q_rad) term
    z2 = -y1*np.sin(q_rad)          # z1=0 so drop cos(q_rad) term
    v2 = {
        'xs': list(x2),
        'ys': list(y2),
        'zs': list(z2)
    }
    return v2

def transform2radec(telra, teldec, v):
    """Transforms a single point to radec
    Temporary utility function. Can be replaced by xy2radec
    """
    ra, dec = xy2radec(telra, teldec, Column([v[0]]), Column(v[1]))
    return np.array([ra[0], dec[0]])

def create_circles(step=1):
    # Added step parameter to make rendering faster by skipping step - 1 fiberpos
    """Create circles at each fiberpos
    
    Returns
    -------
    list
        A list of Circle objects (as defined in circle.py) centered at each
        fiber position
    """
    circles = np.empty(len(range(0, len(fp['X']), step)), dtype=object)
    j = 0
    for i in range(0, len(fp['X']), step):
        circles[j] = Circle(fp['X'][i], fp['Y'][i], 6)
        j += 1 
    return circles

def calculate_ellipses(circles):
    """
    Parameters
    ----------
    circles :
        A list of Circle objects (as defined in circle.py) on the focal plane

    Returns
    -------
    list
        A list of Ellipse objects representing the
        area of sky covered by a circle on the focal plane.
    """
    # ellipses = np.empty(len(circles)*2, dtype=object)
    ellipses = []
    for i, c in enumerate(circles):
        axis_points = list(map(lambda p: transform2radec(telra, teldec, p), c.get_axis_points()))
        center = transform2radec(telra, teldec, [c.x, c.y]) # circle center
        axis0_len = np.linalg.norm(axis_points[1] - axis_points[0])
        axis1_len = np.linalg.norm(axis_points[3] - axis_points[2])
        shifted_axis0_p0 = axis_points[0] - center # Shift vector back to origin so arctan can be used to calculate angle
        # angle = np.degrees(arctan(center[1] / center[0])) + 90
        angle = np.degrees(arctan(shifted_axis0_p0[1] / shifted_axis0_p0[0]))
        ellipses.append(Ellipse(center[0], center[1], axis0_len, axis1_len, angle))
        # ellipses[i] = Ellipse(center[0], center[1], axis0_len * 2, axis1_len, angle)
        # ellipses[i * 2 + 1] = Ellipse(center[0], center[1], axis0_len, axis1_len * 2, angle)
    return ellipses

def plot_ellipse(ax, e):
    """
    Parameters
    ----------
    ax : matplotlib Axes object
    e : Ellipse object
        The Ellipse to be plotted
    """
    e = matplotlib.patches.Ellipse(xy=[e.x, e.y],
                            width=e.width, height=e.height, angle=e.angle)
    ax.add_artist(e)
    e.set_alpha(np.random.rand())
    e.set_facecolor(np.random.rand(3))

def plot_circle_axis(ax, circle):
    """Transforms results returned by get_axis_points to radec and plots them
    """
    axis_points = list(map(lambda p: transform2radec(telra, teldec, p), circle.get_axis_points()))
    x, y = zip(*axis_points)
    plot([x[0]], [y[0]], "r.")
    plot(x[1:], y[1:], "g.")
    # plot([x[2], telra], [y[2], teldec], marker='o')


def plot_circles_radec(ax, circles, sample_per_circle):
    """ Transforms points on a list of circles into radec and plots them
    Parameters
    ----------
    ax : matplotlib Axes object
    circles : list
        A list of Circle objects that needs plotting
    sample_per_circle:
        Number of points to plot around a circle
    """
    ra_col = np.array([])
    dec_col = np.array([])
    for c in circles:
        x, y = c.get_points(sample_per_circle)
        ra, dec = xy2radec(telra, teldec, Column(x), Column(y))
        ra_col = append(ra_col, ra)
        dec_col = append(dec_col, dec)
    plot(ra_col, dec_col, '.')

def export_ellipses(ellipses, file):
    d = {}
    for i, e in enumerate(ellipses):
        d[i] = {
            "ra": e.x,
            "dec": e.y,
            "width": e.width,
            "height": e.height,
            "angle": e.angle
        }
    json.dump(d, file)

def export_points(circles, file):
    point_groups = {
        "pointsPerCircle": 20,
        "xs": [],
        "ys": [],
        "zs": []
    }
    for c in circles:
        x, y = c.get_points(20)
        transformed = xy2xyz(Column(x), Column(y))
        point_groups["xs"].extend(transformed["xs"])
        point_groups["ys"].extend(transformed["ys"])
        point_groups["zs"].extend(transformed["zs"])
    json.dump(point_groups, file)

####################################
# Copy Pasta
# Source: http://nicky.vanforeest.com/misc/fitEllipse/fitEllipse.html
####################################

def fitEllipse(x,y):
    x = x[:,np.newaxis]
    y = y[:,np.newaxis]
    D =  np.hstack((x*x, x*y, y*y, x, y, np.ones_like(x)))
    S = np.dot(D.T,D)
    C = np.zeros([6,6])
    C[0,2] = C[2,0] = 2; C[1,1] = -1
    E, V =  eig(np.dot(inv(S), C))
    n = np.argmax(np.abs(E))
    a = V[:,n]
    return a

def ellipse_center(a):
    b,c,d,f,g,a = a[1]/2, a[2], a[3]/2, a[4]/2, a[5], a[0]
    num = b*b-a*c
    x0=(c*d-b*f)/num
    y0=(a*f-b*d)/num
    return np.array([x0,y0])


def ellipse_angle_of_rotation( a ):
    b,c,d,f,g,a = a[1]/2, a[2], a[3]/2, a[4]/2, a[5], a[0]
    return 0.5*np.arctan(2*b/(a-c))


def ellipse_axis_length( a ):
    b,c,d,f,g,a = a[1]/2, a[2], a[3]/2, a[4]/2, a[5], a[0]
    up = 2*(a*f*f+c*d*d+g*b*b-2*b*d*f-a*c*g)
    down1=(b*b-a*c)*( (c-a)*np.sqrt(1+4*b*b/((a-c)*(a-c)))-(c+a))
    down2=(b*b-a*c)*( (a-c)*np.sqrt(1+4*b*b/((a-c)*(a-c)))-(c+a))
    res1=np.sqrt(up/down1)
    res2=np.sqrt(up/down2)
    return np.array([res1, res2])

def ellipse_angle_of_rotation2( a ):
    b,c,d,f,g,a = a[1]/2, a[2], a[3]/2, a[4]/2, a[5], a[0]
    if b == 0:
        if a > c:
            return 0
        else:
            return np.pi/2
    else:
        if a > c:
            return np.arctan(2*b/(a-c))/2
        else:
            return np.pi/2 + np.arctan(2*b/(a-c))/2

####################################
# End of Copy Pasta
####################################


def transform_circle_radec(circle, sample):
    x, y = circle.get_points(sample)
    ra, dec = xy2radec(telra, teldec, Column(x), Column(y))
    return ra, dec

def interoplate_ellipses(circles):
    ellipses = []
    for c in circles:
        a = fitEllipse(*transform_circle_radec(c, 20))
        center = ellipse_center(a)
        angle = ellipse_angle_of_rotation2(a)
        axes = ellipse_axis_length(a)
        ellipses.append(Ellipse(center[0], center[1], axes[0]*2, axes[1]*2, angle * 180 / np.pi + 90))
        # Source for the above line: https://stackoverflow.com/questions/52818206/fitting-an-ellipse-to-a-set-of-2-d-points
    return ellipses

# circles = [Circle(0, 0, 6)]
circles = create_circles()
# ellipses = interoplate_ellipses(circles)
# ellipses = calculate_ellipses(circles)

def display():
    fig, ax = plt.subplots(subplot_kw={'aspect': 'equal'})
    for e in ellipses:
        plot_ellipse(ax, e)
    for c in circles:
        plot_circle_axis(ax, c)
    plot_circles_radec(ax, circles, 50)
    plt.show()

# display()

# f = open('ellipses', "w")
# export_ellipses(ellipses, f)

f = open('points-aggregated', "w")
export_points(circles, f)
