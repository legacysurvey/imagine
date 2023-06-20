#sys.path.append('cosmo/webapp/viewer-desi/')
import os
import numpy as np
from astrometry.util.fits import fits_table, merge_tables
from desi_spectro_kdtree import create_desi_spectro_kdtree
from collections import Counter

basedir = 'data/desi-spectro-edr'

os.system('startree -i /global/cfs/cdirs/desi/public/edr/spectro/redux/fuji/tiles-fuji.fits -R tilera -D tiledec -PTk -o %s/tiles2.kd.fits' % basedir)

if True:
    from astrometry.util.fits import fits_table
    import numpy as np
    from scipy.spatial import ConvexHull
    #desi_radius = 1.628 # 114 / 297
    #desi_radius = 1.629 # 114 / 266
    #desi_radius = 1.630 # 114 / 238
    #desi_radius = 1.640 # 111 /  86
    #desi_radius = 1.650 # 109 /  33
    #desi_radius = 1.660 # 108 /  17
    #desi_radius = 1.670 # 107 /   8
    #desi_radius = 1.680 # 106 /   1
    desi_radius = 1.690 # 106 /   1
    release = 'edr'
    fn = os.path.join(basedir, 'tiles2.kd.fits')
    tiles = fits_table(fn)
    print(len(tiles), 'tiles')

    from astrometry.libkd.spherematch import cluster_radec
    print('Clustering...')
    cl,sing = cluster_radec(tiles.tilera, tiles.tiledec, 2. * desi_radius, singles=True)
    print('Found', len(cl), 'tile clusters and', len(sing), 'singleton tiles')
    #print('clusters:', cl)
    #print('singletons:', sing)
    #print('tilera range:', tiles.tilera.min(), tiles.tilera.max())

    # Tile RA range is 4.0 to 356.0 degrees -- hence no RA wrap-around!  Convenient!
    
    import pylab as plt
    plt.clf()

    cluster_hulls = []
    for I,cluster in [(c,True) for c in cl] + [([s],False) for s in sing]:
        pts = []
        angles = np.linspace(0., 2.*np.pi, 40, endpoint=False)
        sa = np.sin(angles)
        ca = np.cos(angles)
        for i in I:
            # Generate points on the radius of the tile
            dec = tiles.tiledec[i] + desi_radius * sa
            ra  = tiles.tilera [i] + desi_radius * ca / np.cos(np.deg2rad(dec))
            # Add to points on the hull
            pts.append(np.vstack((ra, dec)).T)
        pts = np.vstack(pts)
        if cluster:
            #print('Stacked points:', pts.shape)
            ch = ConvexHull(pts)
            hull = pts[ch.vertices,:]
            #print('Convex hull:', hull.shape)
        else:
            hull = pts

        cluster_hulls.append(hull)
        
        plt.plot(hull[:,0], hull[:,1])
    plt.savefig('hulls.png')

    import json
    J = json.dumps([list(c.ravel()) for c in cluster_hulls])
    open(os.path.join(basedir, 'tile-clusters.json'), 'w').write(J)

    tile_clusters = cluster_hulls



if False:
    TT = []
    for surv,prog in [('cmx','other'), ('special','dark'),
                      ('sv1','backup'), ('sv1','bright'), ('sv1','dark'), ('sv1','other'),
                      ('sv2','backup'), ('sv2','bright'), ('sv2','dark'),
                      ('sv3','backup'), ('sv3','bright'), ('sv3','dark'),
                      ]:
        #fn = '/global/cfs/cdirs/desi/spectro/redux/fuji/zcatalog/zpix-%s-%s.fits' % (surv, prog)
        fn = '/global/cfs/cdirs/desi/public/edr/spectro/redux/fuji/zcatalog/zpix-%s-%s.fits' % (surv, prog)
        
        T = fits_table(fn, columns=['target_ra','target_dec','targetid','z','zerr','zwarn','spectype','subtype',
                                    'healpix', 'objtype'])
        T.survey = np.array([surv]*len(T))
        T.program = np.array([prog]*len(T))
        TT.append(T)
    T = merge_tables(TT)

else:
    T = fits_table('/global/cfs/cdirs/desi/public/edr/spectro/redux/fuji/zcatalog/zall-pix-fuji.fits',
                   columns=['survey', 'program', 'zcat_primary', 'target_ra','target_dec','targetid',
                            'z','zerr','zwarn','spectype','subtype', 'healpix', 'objtype'])
    print(len(T), 'zall')
    print('ZCAT_PRIMARY', Counter(T.zcat_primary))
    T.cut(np.flatnonzero(T.zcat_primary))
    T.delete_column('zcat_primary')
    
in_cluster = np.zeros(len(T), bool)

T.tile_cluster = np.zeros(len(T), np.int16)
T.tile_cluster[:] = -1

from astrometry.util.miscutils import point_in_poly

for cl_i,rd in enumerate(tile_clusters):
    ra,dec = rd[:,0],rd[:,1]
    #if ra_wrap:
    #ra_w = ra + -360 * (ra > 180)
    #else:
    ra_w = ra
    poly = np.vstack((ra_w,dec)).T

    #isin = point_in_poly(T.ra_wrap, T.dec, np.vstack((ra_w,dec)).T)
    isin = point_in_poly(T.target_ra, T.target_dec, np.vstack((ra_w,dec)).T)
    I = np.flatnonzero(isin)
    print(len(I), 'spectra in cluster', cl_i)
    assert(np.all(in_cluster[I] == False))
    T.tile_cluster[I] = cl_i
    in_cluster[I] = True

from collections import Counter
print('Tile_cluster membership:', Counter(T.tile_cluster))
print('In a cluster:', Counter(in_cluster))

print('not in a cluster:')
I = np.flatnonzero(T.tile_cluster == -1)
for i in I:
    print('https://www.legacysurvey.org/viewer/?ra=%.4f&dec=%.4f&layer=ls-dr9&zoom=8&desi-tiles-edr&desi-spec-edr' % (T.target_ra[i], T.target_dec[i]))
assert(len(I) == 0)

fn = os.path.join(basedir, 'zpix-all.fits')
T.writeto(fn)
create_desi_spectro_kdtree(fn, '%s/zpix-all.kd.fits' % basedir, racol='target_ra', deccol='target_dec')
