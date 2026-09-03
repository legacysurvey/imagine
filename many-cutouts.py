from map.views import get_layer, NoOverlapError
from astrometry.util.fits import fits_table
from astrometry.util.multiproc import multiproc
import numpy as np
import os

def run_one(args):
    (layername, ra, dec, pixscale, W, H, out, bands, fits, jpeg) = args
    layer = get_layer(layername)
    tempfiles = []
    tmp_out = os.path.join(os.path.dirname(out), 'tmp-'+os.path.basename(out))
    try:
        layer.write_cutout(ra, dec, pixscale, W, H, tmp_out,
                           bands=bands, fits=fits, jpeg=jpeg, tempfiles=tempfiles)
        os.rename(tmp_out, out)
        print('Wrote %s' % out)
    except NoOverlapError:
        print('No overlap')
    for fn in tempfiles:
        os.unlink(fn)

def main():
    import argparse
    import os
    parser = argparse.ArgumentParser()
    parser.add_argument('table', help='Table of cutouts to produce')
    parser.add_argument('--outdir', help='Directory prefix to add to output filenames')
    parser.add_argument('--pixscale', type=float, default=None, help='Pixel scale (arcsec/pix)')
    parser.add_argument('--size', type=int, default=None, help='Pixel size of output')
    parser.add_argument('--width', type=int, default=None, help='Pixel width of output')
    parser.add_argument('--height', type=int, default=None, help='Pixel height of output')
    parser.add_argument('--bands', default=None, help='Bands to select for output')
    parser.add_argument('--layer', default=None, help='Map layer to render')
    parser.add_argument('--force', default=False, help='Overwrite existing output file?  Default is to quit.')
    parser.add_argument('--threads', type=int, default=1, help='Multiprocessing')
    opt = parser.parse_args()

    T = fits_table(opt.table)

    # Fill in defaults for any missing columns
    cols = T.get_columns()
    if not 'pixscale' in cols:
        if opt.pixscale is None:
            opt.pixscale = 0.262
    if not 'size' in cols and not ('width' in cols and 'height' in cols):
        if opt.size is None and opt.width is None and opt.height is None:
            opt.size = 256
    if not 'bands' in cols:
        opt.bands = 'grz'
    if not 'layer' in cols:
        opt.layer = 'ls-dr8'
    
    if opt.pixscale is not None:
        T.pixscale = np.array([opt.pixscale] * len(T))
    if opt.size is not None:
        T.size = np.array([opt.size] * len(T))
    if opt.width is not None:
        T.width = np.array([opt.width] * len(T))
    if opt.height is not None:
        T.height = np.array([opt.height] * len(T))
    if opt.bands is not None:
        T.bands = np.array([opt.bands] * len(T))
    if opt.layer is not None:
        T.layer = np.array([opt.layer] * len(T))
    cols = T.get_columns()

    args = []
    #for t in T:

    H,W = None,None
    if 'size' in cols:
        H = W = T.size
    if 'height' in cols:
        H = T.height
    if 'width' in cols:
        W = T.width

    for out,ww,hh,layer,bands,ra,dec,pixscale in zip(T.output, W, H, T.layer, T.bands,
                                                     T.ra, T.dec, T.pixscale):
        out = out.strip()
        layer = layer.strip()
        bands = bands.strip()

        fits = out.endswith('.fits')
        jpeg = (out.endswith('.jpg') or out.endswith('.jpeg'))
        if not (fits or jpeg):
            print('Output filename MUST end with .fits or .jpg or .jpeg: "%s"' % out)
            return -1

        if opt.outdir:
            out = os.path.join(opt.outdir, out)
        if os.path.exists(out) and not opt.force:
            print('Exists:', out)
            continue

        # Create directory if required
        dirnm = os.path.dirname(out)
        if not os.path.exists(dirnm):
            try:
                os.makedirs(dirnm)
            except:
                pass

        args.append((layer, ra, dec, pixscale, ww, hh, out, bands, fits, jpeg))

    mp = multiproc(opt.threads)
    mp.map(run_one, args)
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main())



