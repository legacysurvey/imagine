#sys.path.append('cosmo/webapp/viewer-desi/')
import os
import numpy as np
from astrometry.util.fits import fits_table, merge_tables
from desi_spectro_kdtree import create_desi_spectro_kdtree

os.system('startree -i /global/cfs/cdirs/desi/public/edr/spectro/redux/fuji/tiles-fuji.fits -R tilera -D tiledec -PTk -o data/desi-edr/tiles2.kd.fits')

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
