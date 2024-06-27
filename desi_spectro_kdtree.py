import os
import tempfile
import numpy as np
from astrometry.util.fits import fits_table
from astrometry.libkd.spherematch import tree_build

def create_desi_spectro_kdtree(infn, outfn, racol='ra', deccol='dec'):
    with tempfile.TemporaryDirectory() as tempdir:
        sfn = os.path.join(tempdir, 'allzbest.kd.fits')

        cmd = 'startree -i %s -PTk -o %s -R %s -D %s' % (infn, sfn, racol, deccol)
        os.system(cmd)
    
        T = fits_table(sfn, columns=['targetid'])
        ekd = tree_build(np.atleast_2d(T.targetid.copy()).T.astype(np.uint64),
                         bbox=False, split=True)
        ekd.set_name('targetid')
        efn = os.path.join(tempdir, 'ekd.fits')
        ekd.write(efn)

        # merge
        cmd = 'fitsgetext -i %s -o %s/ekd-%%02i -a' % (efn, tempdir)
        print(cmd)
        rtn = os.system(cmd)
        assert(rtn == 0)

        cmd = 'cat %s %s/ekd-0[12345] > %s' % (sfn, tempdir, outfn)
        print(cmd)
        rtn = os.system(cmd)
        assert(rtn == 0)



if __name__ == '__main__':
    create_desi_spectro_kdtree('data/desi-spectro-daily/desi-obs-202310.fits',
                               'data/desi-spectro-daily/desi-obs.kd.fits')
