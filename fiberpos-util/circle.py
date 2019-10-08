import numpy as np
from math import cos, sin

def rotation_matrix(theta):
    return np.array([
        [cos(theta), -sin(theta)],
        [sin(theta), cos(theta)]
    ])

def normalize(v):
    """Takes in an vector and normalizes it.
    The return value in the form of an np.array
    """
    v = np.asarray(v)
    return v / np.linalg.norm(v)

class Circle:
    def __init__(self, x, y, radius):
        self.radius = radius
        self.x = x
        self.y = y

    def get_points(self, samples=20):
        """Returns sample number of points on the circle perimeter in two
        arrays, x and y
        """
        theta = 0
        delta = np.pi * 2 / samples
        points = []
        start_pos = np.array([0, self.radius])
        for _ in range(samples):
            theta += delta
            points.append(np.matmul(rotation_matrix(theta), start_pos))
        points = map(lambda p: (p[0] + self.x, p[1] + self.y), points)
        return zip(*points)

    def get_axis_points(self):
        """Returns four vectors that points from the center to the perimeter.
        """
        center = np.array([self.x, self.y])
        origin = np.array([0, 0])
        axis0_p0 = normalize(center - origin) * self.radius
        axis0_p1 = -1 * axis0_p0
        axis1_p0 = np.array([-axis0_p0[1], axis0_p0[0]]) # rotate axis0_p0 90 degrees
        axis1_p1 = -1 * axis1_p0
        return map(lambda p: p + center, [axis1_p0, axis1_p1, axis0_p0, axis0_p1])

class Ellipse:
    def __init__(self, x, y, width, height, angle):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.angle = angle
