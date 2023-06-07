#sys.path.append('cosmo/webapp/viewer-desi/')
import os
import numpy as np
from astrometry.util.fits import fits_table, merge_tables
from desi_spectro_kdtree import create_desi_spectro_kdtree

os.system('startree -i /global/cfs/cdirs/desi/public/edr/spectro/redux/fuji/tiles-fuji.fits -R tilera -D tiledec -PTk -o data/desi-edr/tiles2.kd.fits')

if True:
    from astrometry.util.fits import fits_table
    import numpy as np
    from scipy.spatial import ConvexHull
    desi_radius = 1.628
    release = 'edr'
    fn = os.path.join('data', 'desi-spectro-%s/tiles2.kd.fits' % release)
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
            print('Stacked points:', pts.shape)
            ch = ConvexHull(pts)
            hull = pts[ch.vertices,:]
            print('Convex hull:', hull.shape)
        else:
            hull = pts

        cluster_hulls.append(hull)
        
        plt.plot(hull[:,0], hull[:,1])
    plt.savefig('hulls.png')

    import json
    J = json.dumps([list(c.ravel()) for c in cluster_hulls])
    open('tile-clusters.json', 'w').write(J)
    sys.exit(0)

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
fn = 'data/desi-edr/zpix-all.fits'
T.writeto(fn)
create_desi_spectro_kdtree(fn, 'data/desi-edr/zpix-all.kd.fits', racol='target_ra', deccol='target_dec')
