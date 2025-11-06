import os
import tempfile
import numpy as np
from astrometry.util.fits import fits_table
from astrometry.libkd.spherematch import tree_build

def create_desi_spectro_kdtree(infn, outfn, racol='ra', deccol='dec'):
    with tempfile.TemporaryDirectory() as tempdir:
        sfn = os.path.join(tempdir, os.path.basename(outfn))

        cmd = 'startree -i %s -PTk -o %s -R %s -D %s' % (infn, sfn, racol, deccol)
        os.system(cmd)

        # Create a kd-tree over the targetid also
        T = fits_table(sfn, columns=['targetid'])
        ekd = tree_build(np.atleast_2d(T.targetid.copy()).T.astype(np.uint64),
                         bbox=False, split=True)
        ekd.set_name('targetid')
        efn = os.path.join(tempdir, 'ekd.fits')
        ekd.write(efn)
        # Pull out HDUs of the targetid kd-tree into individual files
        cmd = 'fitsgetext -i %s -o %s/ekd-%%02i -a' % (efn, tempdir)
        print(cmd)
        rtn = os.system(cmd)
        assert(rtn == 0)

        # Create a kd-tree over the tile and fiberid
        T = fits_table(sfn, columns=['tileid', 'fiber'])
        # the kd-tree code only exposes the double and uint64 options to python --
        # rather than expanding tileid,fiber to 2 x uint64, pack them into a single uint64
        #ekd = tree_build(np.vstack((T.tileid.copy(), T.fiber.copy())).T.astype(np.int32),
        #                 bbox=False, split=True)
        ekd = tree_build(np.atleast_2d((T.tileid.astype(np.uint64) * 10000 + T.fiber.astype(np.uint64))).T,
                         bbox=False, split=True)
        ekd.set_name('tilefiber')
        efn = os.path.join(tempdir, 'tfkd.fits')
        ekd.write(efn)
        # Pull out HDUs of the targetid kd-tree into individual files
        cmd = 'fitsgetext -i %s -o %s/tfkd-%%02i -a' % (efn, tempdir)
        print(cmd)
        rtn = os.system(cmd)
        assert(rtn == 0)

        # Concatenate all the HDUs!
        cmd = 'cat %s %s/ekd-0[12345] %s/tfkd-0[12345] > %s' % (sfn, tempdir, tempdir, outfn)
        print(cmd)
        rtn = os.system(cmd)
        assert(rtn == 0)



if __name__ == '__main__':
    #create_desi_spectro_kdtree('data/desi-spectro-daily/desi-obs-202310.fits',
    #                           'data/desi-spectro-daily/desi-obs.kd.fits')
    create_desi_spectro_kdtree('data/desi-spectro-daily/desi-obs.fits',
                               'data/desi-spectro-daily/desi-obs.kd.fits')
