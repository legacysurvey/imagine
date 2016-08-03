import numpy as np
from astrometry.util.miscutils import clip_wcs
import os

oneyear = (3600 * 24 * 365)

def ra2long(ra):
    lng = 180. - ra
    lng += 360 * (lng < 0.)
    lng -= 360 * (lng > 360.)
    return lng

def ra2long_B(ra):
    lng = 180. - ra
    lng += 360 * (lng < -180.)
    lng -= 360 * (lng >  180.)
    return lng

def trymakedirs(fn):
    dirnm = os.path.dirname(fn)
    if not os.path.exists(dirnm):
        try:
            os.makedirs(dirnm)
        except:
            pass

def save_jpeg(fn, rgb, **kwargs):
    import pylab as plt
    import tempfile
    f,tempfn = tempfile.mkstemp(suffix='.png')
    os.close(f)
    plt.imsave(tempfn, rgb, **kwargs)
    cmd = 'pngtopnm %s | pnmtojpeg -quality 90 > %s' % (tempfn, fn)
    os.system(cmd)
    os.unlink(tempfn)

def send_file(fn, content_type, unlink=False, modsince=None, expires=3600,
              filename=None):
    import datetime
    from django.http import HttpResponseNotModified, StreamingHttpResponse
    '''
    modsince: If-Modified-Since header string from the client.
    '''
    st = os.stat(fn)
    f = open(fn)
    if unlink:
        os.unlink(fn)
    # file was last modified...
    lastmod = datetime.datetime.fromtimestamp(st.st_mtime)

    if modsince:
        #print('If-modified-since:', modsince #Sat, 22 Nov 2014 01:12:39 GMT)
        ifmod = datetime.datetime.strptime(modsince, '%a, %d %b %Y %H:%M:%S %Z')
        #print('Parsed:', ifmod)
        #print('Last mod:', lastmod)
        dt = (lastmod - ifmod).total_seconds()
        if dt < 1:
            return HttpResponseNotModified()

    res = StreamingHttpResponse(f, content_type=content_type)
    # res['Cache-Control'] = 'public, max-age=31536000'
    res['Content-Length'] = st.st_size
    if filename is not None:
        res['Content-Disposition'] = 'attachment; filename="%s"' % filename
    # expires in an hour?
    now = datetime.datetime.utcnow()
    then = now + datetime.timedelta(0, expires, 0)
    timefmt = '%a, %d %b %Y %H:%M:%S GMT'
    res['Expires'] = then.strftime(timefmt)
    res['Last-Modified'] = lastmod.strftime(timefmt)
    return res

class RARange(object):
    def __init__(self, rlo, rhi):
        c1,s1 = np.cos(np.deg2rad(rlo)), np.sin(np.deg2rad(rlo))
        c2,s2 = np.cos(np.deg2rad(rhi)), np.sin(np.deg2rad(rhi))
        cmid = (c1 + c2) / 2.
        smid = (s1 + s2) / 2.
        length = np.hypot(cmid, smid)
        cmid /= length
        smid /= length
        self.cmid = cmid
        self.smid = smid
        self.mindot = c1 * cmid + s1 * smid
        # midpoint
        self.ramid = np.rad2deg(np.arctan2(self.smid, self.cmid))
        # should be equal...?
        self.dra = min(np.abs(np.mod(self.ramid - rlo, 360.)),
                       np.abs(np.mod(self.ramid - rhi, 360.)))

    def inrange(self, r):
        r = np.deg2rad(r)
        c,s = np.cos(r), np.sin(r)
        return (c * self.cmid + s * self.smid >= self.mindot)

    def overlaps(self, rlo, rhi):
        # Offset to no-wrap-around-land?
        offset = 180.
        r1 = np.mod(offset + rlo - self.ramid, 360.)
        r2 = np.mod(offset + rhi - self.ramid, 360.)
        # Require "clockwise" relation between rlo,rhi?
        #rlo = np.minimum(r1, r2)
        #rhi = np.maximum(r1, r2)
        rlo,rhi = r1,r2
        #print 'rlo,rhi', rlo,rhi, 'vs', offset-self.dra, offset+self.dra
        return (rlo <= offset + self.dra) * (rhi >= offset - self.dra)

class MercWCSWrapper(object):
    def __init__(self, wcs, wrap):
        self.wcs = wcs
        self.wrap = float(wrap)
    def radec2pixelxy(self, ra, dec):
        X = self.wcs.radec2pixelxy(ra, dec)
        (ok,x,y) = X
        x += (x < -self.wrap/2) * self.wrap
        x -= (x >  self.wrap/2) * self.wrap
        return (ok,x,y)

    def pixelxy2radec(self, x, y):
        ok,r,d = self.wcs.pixelxy2radec(x, y)
        #assert(np.all(ok))
        return ok,r,d
    
    def __getattr__(self, name):
        return getattr(self.wcs, name)
    def __setattr__(self, name, val):
        if name in ['wcs', 'wrap']:
            self.__dict__[name] = val
            return
        return setattr(self.wcs, name, val)


def get_tile_wcs(zoom, x, y):
    from astrometry.util.util import anwcs_create_mercator_2

    zoom = int(zoom)
    zoomscale = 2.**zoom
    x = int(x)
    y = int(y)
    if zoom < 0 or x < 0 or y < 0 or x >= zoomscale or y >= zoomscale:
        raise RuntimeError('Invalid zoom,x,y %i,%i,%i' % (zoom,x,y))

    # tile size
    zoomscale = 2.**zoom
    W,H = 256,256
    if zoom == 0:
        rx = ry = 0.5
    else:
        rx = zoomscale/2 - x
        ry = zoomscale/2 - y
    rx = rx * W
    ry = ry * H
    wcs = anwcs_create_mercator_2(180., 0., rx + 0.5, ry + 0.5,
                                  zoomscale, W, H, 1)
    if wcs is not None:
        wcs = MercWCSWrapper(wcs, 2**zoom * W)

    return wcs, W, H, zoomscale, zoom,x,y



def tiles_touching_wcs(wcs, zoom):
    N = 2**zoom

    # RA and Dec tile centers (as two separate arrays)
    # We'll avoid doing a meshgrid on them so this still works at large zooms
    rr,dd = [],[]
    dlo,dhi = [],[]
    yy = np.arange(N)
    xx = yy
    for y in yy:
        twcs,W,H,zoomscale,zoom,x,y = get_tile_wcs(zoom, 0, y)
        r,d = twcs.get_center()
        dd.append(d)
        nil,d1 = twcs.pixelxy2radec(0.5, 0.5)[-2:]
        nil,d2 = twcs.pixelxy2radec(0.5, H + 0.5)[-2:]
        dlo.append(min(d1,d2))
        dhi.append(max(d1,d2))
    for x in xx:
        twcs,W,H,zoomscale,zoom,x,y = get_tile_wcs(zoom, x, 0)
        r,d = twcs.get_center()
        rr.append(r)
    rr = np.array(rr)
    dd = np.array(dd)
    dlo = np.array(dlo)
    dhi = np.array(dhi)

    # Cut dd to the range that overlaps wcs.
    r1,r2,d1,d2 = wcs.radec_bounds()
    I = np.flatnonzero((d1 <= dhi) * (d2 >= dlo))
    #print len(dd), 'tiles'
    dd = dd[I]
    yy = yy[I]
    #print len(dd), 'are within Dec range'

    # Cut rr to the range that overlaps wcs.
    #print 'RA range', r1,r2
    #print 'RAs of tiles:', rr
    # here we assume that the Mercator tiles are equally spaced in RA.
    dra = np.abs(rr[1] - rr[0])
    assert(dra < 180.)
    #print 'Delta-RA:', dra
    rrange = RARange(r1,r2)
    I = rrange.overlaps(rr - dra/2., rr + dra/2.)
    rr = rr[I]
    xx = xx[I]
    #print len(rr), 'are within RA range'

    # Now broadcast the xx,yy grid locations and do the real WCS overlap tests.
    xkeep,ykeep = [],[]
    for y in yy:
        for x in xx:
            tilewcs,W,H,zoomscale,zoom,x,y = get_tile_wcs(zoom, x, y)
            lst = clip_wcs(tilewcs, wcs)
            # no overlap
            if len(lst) == 0:
                continue
            xkeep.append(x)
            ykeep.append(y)
    xkeep = np.array(xkeep)
    ykeep = np.array(ykeep)
    return xkeep,ykeep

if __name__ == '__main__':
    r = RARange(0,10)
    rr = np.arange(-10, 30)
    inr = r.inrange(rr)
    assert(np.all(inr == ((rr >= 0) * (rr <= 10))))

    print 'RA mid', r.ramid, 'dra', r.dra
    for rl,rh,truth in [(-2, -1, False),
                        (-1,  0, True),
                        (-1,  1, True),
                        (-1, 11, True),
                        ( 1, 11, True),
                        ( 1,  9, True),
                        ( 5,  5, True),
                        (355, 60, True),
                        (9,10, True),
                        (9,11, True),
                        (10,11, True),
                        (11,12, False),
                        (-45,45, True),
                        (45,-45, False),
                        ]:
        o = r.overlaps(rl,rh)
        print 'Overlaps', rl,rh, '?', o
        assert(o == truth)
        
    r = RARange(-45, 45)
    rr = np.arange(-60, 60)
    inr = r.inrange(rr)
    #print inr
    assert(np.all(inr == ((rr >= -45) * (rr <= 45))))

    print 'RA mid', r.ramid, 'dra', r.dra
    for rl,rh,truth in [(-50, -48, False),
                        (-46,  -45, True),
                        (315, 316, True),
                        (315, 10, True),
                        ( 0, 45, True),
                        (46,90, False),
                        (91,269, False),
                        ]:
        o = r.overlaps(rl,rh)
        print 'Overlaps', rl,rh, '?', o
        assert(o == truth)



    r = RARange(315, 45)
    rr = np.arange(-60, 60)
    inr = r.inrange(rr)
    #print inr
    assert(np.all(inr == ((rr >= -45) * (rr <= 45))))

    rr = np.append(np.arange(300, 360), np.arange(0, 60))
    inr = r.inrange(rr)
    #print inr
    assert(np.all(inr == np.logical_or(rr >= 315, rr <= 45)))
