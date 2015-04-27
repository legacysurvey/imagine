import sys

import django
#django.setup()
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'decals.settings'

import numpy as np

from map.views import *
from decals import settings
from desi.common import Decals

from astrometry.util.fits import *

def main():
    import optparse

    parser = optparse.OptionParser()

    parser.add_option('--mindec', type=float, default=-20, help='Minimum Dec to run')
    parser.add_option('--maxdec', type=float, default=40, help='Maximum Dec to run')
    parser.add_option('--minra', type=float, default=0, help='Minimum RA to run')
    parser.add_option('--maxra', type=float, default=360, help='Maximum RA to run')
    parser.add_option('--queue', action='store_true', default=False,
                      help='Print qdo commands')
    parser.add_option('--tag', default='image')
    parser.add_option('--imagedir', default='decals-dr1j')
    parser.add_option('--scaledir', default=None)

    opt,args = parser.parse_args()

    decals = Decals()
    #B = decals.get_bricks_readonly()
    B = fits_table('decals-bricks-in-edr.fits')

    brickinds = bricknames = None
    if len(args) == 0:
        brickinds = np.flatnonzero((B.dec > opt.mindec) * (B.dec <= opt.maxdec) *
                                   (B.ra  > opt.minra ) * (B.ra  <= opt.maxra))
        N = len(brickinds)

        if opt.queue:
            I = brickinds
            decs = np.unique(B.dec[I])
            print >> sys.stderr, 'Unique Decs:', decs
            k = 0
            for dec in decs:
                for rlo,rhi in [(-0.01,90),(90,180),(180,270),(270,360)]:
                    print ('python -u scale-images.py --mindec %f --maxdec %f --minra %f --maxra %f > scale-%02i.log 2>&1' %
                           (dec-0.01, dec+0.01, rlo, rhi, k))
                    k += 1
            return 0

    else:
        bricknames = args
        N = len(bricknames)

    basedir = os.path.join(settings.WEB_DIR, 'data')

    imagedir = opt.imagedir
    imagetag = opt.tag
    scaledir = opt.scaledir
    if scaledir is None:
        scaledir = imagedir

    # layout == 2
    basepat = os.path.join(basedir, 'coadd', imagedir, '%(brickname).3s',
                           '%(brickname)s',
                           'decals-%(brickname)s-' + imagetag + '-%(band)s.fits')
    scaled = 8

    dirnm = os.path.join(basedir, 'scaled', scaledir)
    scalepat = os.path.join(dirnm, '%(scale)i%(band)s', '%(brickname).3s', imagetag + '-%(brickname)s-%(band)s.fits')

    bands = 'grz'

    for i in range(N):
        if brickinds is not None:
            brick = B[brickinds[i]]
        else:
            brick = decals.get_brick_by_name(bricknames[i])

        for band in bands:
            # HACK -- dr1
            if not brick.get('has_%s' % band):
                print 'Brick', brick.brickname, 'does not have band', band
                continue

            print 'Scaling brick', brick.brickname, 'band', band
            fnargs = dict(band=band, brick=brick.brickid, brickname=brick.brickname)
            basefn = basepat % fnargs
            try:
                fn = get_scaled(scalepat, fnargs, scaled, basefn)
                print 'Filename:', fn
            except:
                import traceback
                traceback.print_exc()
                continue

if __name__ == '__main__':
    sys.exit(main())
