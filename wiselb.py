
import sys

###
sys.path.insert(0, 'django-1.7')
###

import matplotlib
matplotlib.use('Agg')
import pylab as plt
from decals import settings
from map.views import _unwise_to_rgb
import fitsio
from astrometry.util.util import *
from astrometry.util.fits import *
from astrometry.util.resample import *
from astrometry.util.starutil_numpy import *


ver = 1
patdata = dict(ver=ver)

# basescale = 5
# tilesize = 256
# tiles = 2**basescale
# side = tiles * tilesize

H,W = 4096,8192
scalelevel = 5

#H,W = 8192,16384
#scalelevel = 4

wcs = anwcs_create_allsky_hammer_aitoff2(0., 0., W, H)

#w1bfn = 'w1lb-%i.fits' % basescale
#w2bfn = 'w2lb-%i.fits' % basescale

T = fits_table('allsky-atlas.fits')

imgs = []

for band in [1,2,3,4]:
    outfn = 'w%i-lb-%i-%i.fits' % (band, scalelevel, H)
    if os.path.exists(outfn):
        outfn = outfn.replace('.fits', '-u.fits')
        img = fitsio.read(outfn)
        imgs.append(img)
        continue

    img = np.zeros((H,W), np.float32)
    uimg = np.zeros((H,W), np.float32)
    nimg = np.zeros((H,W), np.uint8)

    for i,brick in enumerate(T.coadd_id):
        #fn = os.path.join('data/scaled/unwise/7w%i' % band, brick[:3],
        fn = os.path.join('data/scaled/unwise/%iw%i' % (scalelevel, band), brick[:3],
                          'unwise-%s-w%i.fits' % (brick, band))
        print 'Reading', fn
        I = fitsio.read(fn)
        bwcs = Tan(fn, 0)
        bh,bw = I.shape
    
        xx,yy = np.meshgrid(np.arange(bw), np.arange(bh))
        rr,dd = bwcs.pixelxy2radec(xx, yy)
    
        #print 'rr,dd', rr.shape, dd.shape
    
        ll,bb = radectolb(rr.ravel(), dd.ravel())
        ll = ll.reshape(rr.shape)
        bb = bb.reshape(rr.shape)
    
        ok,ox,oy = wcs.radec2pixelxy(ll, bb)
        #print 'ok:', np.unique(ok)
        ox = np.round(ox - 1).astype(int)
        oy = np.round(oy - 1).astype(int)
        K = ((ox >= 0) * (ox < W) * (oy >= 0) * (oy < H) * (ok == 0))
        #print 'K:', K.dtype, K.shape
    
        img [oy[K], ox[K]] += I[K]
        uimg[oy[K], ox[K]] += (I[K] * (nimg[oy[K], ox[K]] == 0))
        nimg[oy[K], ox[K]] += 1
    
        #if i >= 100:
        #    break
            
    img /= np.maximum(nimg, 1)
    fitsio.write(outfn, img, clobber=True)
    fitsio.write(outfn.replace('.fits', '-u.fits'), uimg, clobber=True)
    fitsio.write(outfn.replace('.fits', '-n.fits'), nimg, clobber=True)
    imgs.append(img)

#plt.clf()
#plt.imshow(img, interpolation='nearest', origin='lower')
#plt.savefig('w1.png')


w1,w2 = imgs
S,Q = 3000,25
rgb = _unwise_to_rgb([w1, w2], S=S, Q=Q)
plt.imsave('wlb.jpg', rgb, origin='lower')

