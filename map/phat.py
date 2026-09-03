from map.views import MapLayer
from viewer import settings

import os

class ducky(object):
    pass

class PhatLayer(MapLayer):
    def __init__(self, name, **kwargs):
        import fitsio
        from astrometry.util.util import Tan
        super().__init__(name, **kwargs)
        self.nativescale = 17
        self.pixscale = 0.05
        #fn = os.path.join(settings.DATA_DIR, 'm31_full.fits')
        #self.fits = fitsio.FITS(fn)[0]
        #self.wcs = Tan(fn, 0)
        #print('WCS:', self.wcs)

    def read_image(self, brick, band, scale, slc, fn=None):
        import numpy as np
        img = super(PhatLayer,self).read_image(brick, band, scale, slc, fn=fn)
        return img.astype(np.float32)

    def get_bands(self):
        ### FIXME
        return 'BGR'

    def get_base_filename(self, brick, band, **kwargs):
        return os.path.join(settings.DATA_DIR, 'phat', 'm31_full_%s.fits' % band)

    def get_scaled_filename(self, brick, band, scale):
        return os.path.join(settings.DATA_DIR, 'phat',
                            'm31_full_%s_scale%i.fits' % (band, scale))

    def render_into_wcs(self, wcs, zoom, x, y, bands=None, general_wcs=False,
                        scale=None, tempfiles=None,
                        invvar=False, maskbits=False):
        import numpy as np
        from astrometry.util.resample import resample_with_wcs, OverlapError

        assert(invvar == False)
        assert(maskbits == False)

        if scale is None:
            scale = self.get_scale(zoom, x, y, wcs)

        #if bricks is None or len(bricks) == 0:
        #    print('No bricks touching WCS')
        #    return None

        if bands is None:
            bands = self.get_bands()

        W = int(wcs.get_width())
        H = int(wcs.get_height())
        r,d = wcs.pixelxy2radec([1,1,1,W/2,W,W,W,W/2],
                                [1,H/2,H,H,H,H/2,1,1])[-2:]

        #print('Tile RA,Decs:', r,d)

        rimgs = []
        # scaled down.....
        # call get_filename to possibly generate scaled version
        for band in bands:
            brick = ducky()
            brick.brickname = 'quack'
            fn = self.get_filename(brick, band, scale, tempfiles=tempfiles)
            print('scale', scale, 'band', band, 'fn', fn)
            try:
                bwcs = self.read_wcs(brick, band, scale, fn=fn)
                if bwcs is None:
                    print('No such file:', brick, band, scale, 'fn', fn)
                    continue
            except:
                print('Failed to read WCS:', brick, band, scale, 'fn', fn)
                savecache = False
                import traceback
                import sys
                traceback.print_exc(None, sys.stdout)
                continue

            # Check for pixel overlap area
            ok,xx,yy = bwcs.radec2pixelxy(r, d)
            xx = xx.astype(np.int32)
            yy = yy.astype(np.int32)
            imW,imH = int(bwcs.get_width()), int(bwcs.get_height())
            M = 10
            xlo = np.clip(xx.min() - M, 0, imW)
            xhi = np.clip(xx.max() + M, 0, imW)
            ylo = np.clip(yy.min() - M, 0, imH)
            yhi = np.clip(yy.max() + M, 0, imH)

            #print('My WCS xx,yy', xx, yy, 'imW,H', imW, imH, 'xlohi', xlo,xhi, 'ylohi', ylo,yhi)

            if xlo >= xhi or ylo >= yhi:
                print('No pixel overlap')
                return

            subwcs = bwcs.get_subimage(xlo, ylo, xhi-xlo, yhi-ylo)
            slc = slice(ylo,yhi), slice(xlo,xhi)

            try:
                img = self.read_image(brick, band, scale, slc, fn=fn)
            except:
                print('Failed to read image:', brickname, band, scale, 'fn', fn)
                savecache = False
                import traceback
                import sys
                traceback.print_exc(None, sys.stdout)
                continue

            #print('Read image slice', img.shape)

            try:
                Yo,Xo,Yi,Xi,nil = resample_with_wcs(wcs, subwcs, [], 3)
            except OverlapError:
                #debug('Resampling exception')
                return

            rimg = np.zeros((H,W), np.float32)
            rimg[Yo,Xo] = img[Yi,Xi]
            rimgs.append(rimg)

        return rimgs

    def get_rgb(self, imgs, bands, **kwargs):
        import numpy as np
        sz = imgs[0].shape
        #mapping = np.zeros(256, np.uint8)
        lo,hi = 0.15, 0.8
        mapping = np.clip(np.round((np.arange(256) - lo*255) / (hi - lo)), 0, 255).astype(np.uint8)
        rgb = np.zeros((sz[0],sz[1],3), np.uint8)
        for i,img in zip([2,1,0], imgs):
            rgb[:,:,i] = mapping[img.astype(int)]
        return rgb

class M33Layer(PhatLayer):
    '''
# Image files:
tifftopnm data/m33/M33_F814W_F475W_mosaic_181216_MJD.tif | ppmtorgb3 -
pamflip -tb -- -.red | an-pnmtofits -o data/m33/m33-R.fits -v &
pamflip -tb -- -.grn | an-pnmtofits -o data/m33/m33-G.fits -v &
pamflip -tb -- -.blu | an-pnmtofits -o data/m33/m33-B.fits -v &

# WCS header:
hdr = fitsio.read_header('/Users/dstn/Downloads/F475W_wcs.fits')
outhdr = fitsio.FITSHDR()
for key in ['SIMPLE', 'BITPIX', 'NAXIS', 'WCSAXES', 'CRPIX1', 'CRPIX2', 'CTYPE1', 'CTYPE2', 'CRVAL1', 'CRVAL2']:
    v = hdr[key]
    outhdr[key] = v
outhdr
outhdr['CD1_1'] = hdr['CDELT1'] * hdr['PC1_1']
outhdr['CD1_2'] = hdr['CDELT1'] * hdr['PC1_2']
outhdr['CD2_1'] = hdr['CDELT2'] * hdr['PC2_1']
outhdr['CD2_2'] = hdr['CDELT2'] * hdr['PC2_2']
outhdr['IMAGEW'] = 32073
outhdr['IMAGEH'] = 41147
fitsio.write('/tmp/m33-wcs.fits', None, header=outhdr)
'''

    def __init__(self, name, **kwargs):
        ## HACK -- don't call the PhatLayer constructor!
        #super(M33Layer, self).__init__(name, **kwargs)
        super(PhatLayer, self).__init__(name, **kwargs)
        self.nativescale = 17
        self.pixscale = 0.035
        #fn = self.get_base_filname(None, None)
        #self.fits = fitsio.FITS(fn)[0]
        #fn = os.path.join(settings.DATA_DIR, 'm33', 'F475W_wcs.fits')
        #fn = os.path.join(settings.DATA_DIR, 'm33', 'm33-wcs.fits')
        fn = os.path.join(settings.DATA_DIR, 'm33', 'm33-wcs814.fits')
        #self.wcs = anwcs_open_wcslib(fn, 0)
        from astrometry.util.util import Tan
        self.wcs = Tan(fn, 0)
        print('M33 WCS: center', self.wcs.radec_center())

    def read_wcs(self, brick, band, scale, fn=None):
        if scale == 0:
            return self.wcs
        return super(M33Layer, self).read_wcs(brick, band, scale, fn=fn)

    def get_bands(self):
        return 'RGB'

    def get_base_filename(self, brick, band, **kwargs):
        return os.path.join(settings.DATA_DIR, 'm33', 'm33-%s.fits' % band)

    def get_scaled_filename(self, brick, band, scale):
        return os.path.join(settings.DATA_DIR, 'm33', 'm33-%s-scale%i.fits' % (band, scale))

    def get_rgb(self, imgs, bands, **kwargs):
        import numpy as np
        #for img in imgs:
        #    print('Image', img.shape, img.dtype, img.min(), img.max())
        return np.dstack(imgs) / 255.
        # sz = imgs[0].shape
        # rgb = np.zeros((sz[0],sz[1],3), np.uint8)
        # for i,img in enumerate(imgs):
        #     rgb[:,:,i] = img
        # return rgb

class PhastLayer(PhatLayer):
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)
        self.fits = None
        self.wcs = None

    def get_bands(self):
        return ['f475w', 'f814w']

    def get_base_filename(self, brick, band, **kwargs):
        return os.path.join(
            settings.DATA_DIR, 'phast',
            'hlsp_phast_hst_acs_m31-all_%s_v1.0_drz_f32_nan.fits' % band)

    def get_scaled_filename(self, brick, band, scale):
        return os.path.join(
            settings.DATA_DIR, 'phast',
            'hlsp_phast_hst_acs_m31-all_%s_v1.0_drz_f32_nan_scale%i.fits' %
            (band, scale))

    def get_rgb(self, imgs, bands, **kwargs):

        scale1 = 300.
        scale2 = 100.
        arcsinh=1./20.
        mn=-20.
        mx=10000.
        w1weight=1.

        import numpy as np
        img = imgs[0]
        H,W = img.shape
        ## FIXME
        assert(bands == ['f475w', 'f814w'])
        w1,w2 = imgs
        rgb = np.zeros((H, W, 3), np.uint8)
        img1 = w1 * scale1
        img2 = w2 * scale2

        if arcsinh is not None:
            def nlmap(x):
                return np.arcsinh(x * arcsinh) / np.sqrt(arcsinh)

            # intensity -- weight W1 more?
            bright = (w1weight * img1 + img2) / (w1weight + 1.)
            I = nlmap(bright)

            # color -- abs here prevents weird effects when, eg, W1>0 and W2<0.
            mean = np.maximum(1e-6, (np.abs(img1)+np.abs(img2))/2.)
            img1 = np.abs(img1)/mean * I
            img2 = np.abs(img2)/mean * I

            mn = nlmap(mn)
            mx = nlmap(mx)

        img1 = (img1 - mn) / (mx - mn)
        img2 = (img2 - mn) / (mx - mn)

        rgb[:,:,2] = (np.clip(img1, 0., 1.) * 255).astype(np.uint8)
        rgb[:,:,0] = (np.clip(img2, 0., 1.) * 255).astype(np.uint8)
        rgb[:,:,1] = rgb[:,:,0]/2 + rgb[:,:,2]/2

        return rgb
