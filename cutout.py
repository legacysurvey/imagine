from map.views import get_layer

# if it looks like a duck and quacks like a duck...
class duck(object):
    pass

CUTOUT_PIXSCALE_DEFAULT = 0.262
CUTOUT_SIZE_DEFAULT = 256
CUTOUT_BANDS_DEFAULT = ['g','r','z']
CUTOUT_LAYER_DEFAULT = 'ls-dr9'

def cutout_main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, help='Output filename (*.jpg or *.fits)')
    parser.add_argument('--ra', type=float, required=True, help='RA (deg)')
    parser.add_argument('--dec', type=float, required=True, help='Dec (deg)')
    parser.add_argument('--pixscale', type=float, default=CUTOUT_PIXSCALE_DEFAULT, help='Pixel scale (arcsec/pix), default %default')
    parser.add_argument('--size', type=int, default=CUTOUT_SIZE_DEFAULT, help='Pixel size of output, default %default')
    parser.add_argument('--width', type=int, default=None, help='Pixel width of output')
    parser.add_argument('--height', type=int, default=None, help='Pixel height of output')
    parser.add_argument('--bands', default=','.join(CUTOUT_BANDS_DEFAULT), help='Bands to select for output, default %default')
    parser.add_argument('--layer', default=CUTOUT_LAYER_DEFAULT, help='Map layer to render, default %default')
    parser.add_argument('--invvar', default=False, action='store_true', help='Include Invvar extension for FITS outputs?')
    parser.add_argument('--maskbits', default=False, action='store_true', help='Include Maskbits extension for FITS outputs?')
    parser.add_argument('--no-image', default=False, action='store_true', help='Omit image pixels when doing --invvar or --maskbits')
    parser.add_argument('--force', default=False, action='store_true', help='Overwrite existing output file?  Default is to quit.')

    opt = parser.parse_args()
    bands = opt.bands.split(',')

    return cutout(opt.ra, opt.dec, opt.output,
                  pixscale=opt.pixscale,
                  width=opt.width, height=opt.height, size=opt.size,
                  bands=bands,
                  invvar=opt.invvar, maskbits=opt.invvar, no_image=opt.no_image,
                  force=opt.force)

def cutout(ra, dec, output,
           pixscale=CUTOUT_PIXSCALE_DEFAULT,
           width=None,
           height=None,
           size=CUTOUT_SIZE_DEFAULT,
           bands=CUTOUT_BANDS_DEFAULT,
           layer=CUTOUT_LAYER_DEFAULT,
           invvar=False,
           maskbits=False,
           no_image=False,
           force=False):
    import os

    if os.path.exists(output) and not force:
        print('Exists:', output)
        return 0
    H = size
    if height is not None:
        H = height
    W = size
    if width is not None:
        W = width

    fits = output.lower().endswith('.fits')
    jpeg = (output.lower().endswith('.jpg') or output.lower().endswith('.jpeg'))
    if not (fits or jpeg):
        print('Output filename MUST end with .fits or .jpg or .jpeg')
        return -1

    kwa = {}
    if fits:
        kwa.update(with_invvar=invvar,
                   with_maskbits=maskbits)
        if no_image:
            kwa.update(with_image=False)

    req = duck()
    req.GET = {}

    layer = get_layer(layer)
    tempfiles = []
    layer.write_cutout(ra, dec, pixscale, W, H, output,
                       bands=bands, fits=fits, jpeg=jpeg, tempfiles=tempfiles, req=req,
                       **kwa)
    for fn in tempfiles:
        os.unlink(fn)
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(cutout_main())
