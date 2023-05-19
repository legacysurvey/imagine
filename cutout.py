from map.views import get_layer

# if it looks like a duck and quacks like a duck...
class duck(object):
    pass

def main():
    import argparse
    import os
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, help='Output filename (*.jpg or *.fits)')
    parser.add_argument('--ra', type=float, required=True, help='RA (deg)')
    parser.add_argument('--dec', type=float, required=True, help='Dec (deg)')
    parser.add_argument('--pixscale', type=float, default=0.262, help='Pixel scale (arcsec/pix)')
    parser.add_argument('--size', type=int, default=256, help='Pixel size of output')
    parser.add_argument('--width', type=int, default=None, help='Pixel width of output')
    parser.add_argument('--height', type=int, default=None, help='Pixel height of output')
    parser.add_argument('--bands', default='grz', help='Bands to select for output')
    parser.add_argument('--layer', default='ls-dr8', help='Map layer to render')
    parser.add_argument('--force', default=False, action='store_true', help='Overwrite existing output file?  Default is to quit.')

    opt = parser.parse_args()
    if os.path.exists(opt.output) and not opt.force:
        print('Exists:', opt.output)
        return 0
    H = opt.size
    if opt.height is not None:
        H = opt.height
    W = opt.size
    if opt.width is not None:
        W = opt.width

    req = duck()
    req.GET = {}

    fits = opt.output.endswith('.fits')
    jpeg = (opt.output.endswith('.jpg') or opt.output.endswith('.jpeg'))
    if not (fits or jpeg):
        print('Output filename MUST end with .fits or .jpg or .jpeg')
        return -1

    layer = get_layer(opt.layer)
    tempfiles = []
    layer.write_cutout(opt.ra, opt.dec, opt.pixscale, W, H, opt.output,
                       bands=opt.bands, fits=fits, jpeg=jpeg, tempfiles=tempfiles, req=req)
    for fn in tempfiles:
        os.unlink(fn)
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main())



