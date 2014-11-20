import os
import tempfile

from django.shortcuts import render

from django.http import HttpResponse

from astrometry.util.util import *
from astrometry.blind.plotstuff import *


def map_image(req, zoom, x, y):
    print 'map_image', zoom, x, y

    zoom = int(zoom)
    x = int(x)
    y = int(y)
    
    zoomscale = 2.**zoom
    
    #rc = 360. * (x+0.5) / zoomscale
    #dc = 90 + -180. * (y+0.5) / zoomscale

    W,H = 256,256
    #wcs = anwcs_create_mercator(rc, dc, zoomscale, 256, 256, 1)
    #rx,ry = W/2 + 0.5, H/2 + 0.5

    print 'zoomscale', zoomscale

    if zoom == 0:
        rx = ry = 0.5
    else:
        rx = zoomscale/2 - x
        #rx = zoomscale/2 - (zoomscale - 1 - x)
        #ry = -zoomscale/2 + 1 + y
        ry = zoomscale/2 - y

    rx1,ry1 = rx,ry

    print 'Refx, refy', rx,ry

    rx = rx * W
    ry = ry * H
    
    #rx = (x + 0.5) * zoomscale * W + 0.5
    #ry = (y + 0.5) * zoomscale * H + 0.5
    
    wcs = anwcs_create_mercator_2(180., 0., rx, ry,
                                  zoomscale, W, H, 1)
    # print 'WCS'
    # s = anwcs_wcslib_to_string(wcs)
    # while len(s):
    #     print s[:80]
    #     s = s[80:]

    # print 'RA,Dec 0,0 ->', wcs.radec2pixelxy(0., 0.)
    # print 'RA,Dec 90,0 ->', wcs.radec2pixelxy(90., 0.)
    # print 'RA,Dec 180,0 ->', wcs.radec2pixelxy(180., 0.)
    # print 'RA,Dec 270,0 ->', wcs.radec2pixelxy(270., 0.)
    # print 'RA,Dec -90,0 ->', wcs.radec2pixelxy(-90., 0.)
    # 
    # print 'RA,Dec 0,45 ->', wcs.radec2pixelxy(0., 45.)
    # print 'RA,Dec 0,60 ->', wcs.radec2pixelxy(0., 60.)
    # print 'RA,Dec 0,80 ->', wcs.radec2pixelxy(0., 80.)
    # print 'RA,Dec 0,85 ->', wcs.radec2pixelxy(0., 85.)
    # print 'RA,Dec 0,90 ->', wcs.radec2pixelxy(0., 90.)
    
    plot = Plotstuff(size=(256,256), outformat='jpg')
    plot.wcs = wcs
    plot.color = 'gray'

    grid = 30
    if zoom >= 2:
        grid = 10
    if zoom >= 4:
        grid = 5
    if zoom >= 6:
        grid = 1
    if zoom >= 8:
        grid = 0.5
    if zoom >= 10:
        grid = 0.1
    plot.plot_grid(grid*2, grid, ralabelstep=grid*2, declabelstep=grid)

    plot.color = 'white'
    plot.apply_settings()
    ok,r,d = wcs.pixelxy2radec(W/2+0.5, H/2+0.5)
    print 'RA,Dec at center:', r,d
    plot.text_xy(W/2, H/2, 'zoom%i (%i,%i)' % (zoom,x,y))
    #plot.text_xy(W/2, H/2+20, 'x %i -> %.1f' % (x, rx1))
    #plot.text_xy(W/2, H/2+40, 'y %i -> %.1f' % (y, ry1))
    plot.stroke()
    plot.color = 'green'
    plot.lw = 2.
    plot.alpha = 0.3
    plot.apply_settings()
    M = 5
    plot.polygon([(M,M),(W-M,M),(W-M,H-M),(M,H-M)])
    plot.close_path()
    plot.stroke()
    
    f,fn = tempfile.mkstemp()
    os.close(f)
    plot.write(fn)
    f = open(fn)
    os.unlink(fn)
    return HttpResponse(f, content_type="image/jpeg")
