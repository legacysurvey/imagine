from __future__ import print_function
import os
from glob import glob
import numpy as np
from astrometry.util.file import read_file
from legacypipe.survey import LegacySurveyData

def delete_scaled_images(name, new_bricks, bands=None):
    from map.views import get_layer
    layer = get_layer(name)
    modlayer = get_layer(name + '-model')
    if bands is None:
        bands = layer.get_bands()
    print('Got layer:', layer)
    print('Got model layer:', modlayer)
    for scale in range(1, 8):
        #if scale >= len(old_bricks):
        #    print('No old bricks for scale', scale)
        #    break
        sbricks = set()
        delfiles = set()
        scale_bricks = layer.get_bricks_for_scale(scale)
        for b in new_bricks:
            SB = layer.bricks_touching_radec_box(b.ra1, b.ra2, b.dec1, b.dec2,
                                                 scale=scale, bricks=scale_bricks)
            #band = 'r'
            #bwcs = layer.get_scaled_wcs(b, band, scale-1)
            #SB = layer.bricks_touching_aa_wcs(bwcs, scale=scale)
            for sb in SB.brickname:
                sbricks.add(sb)
            for sb in SB:
                for band in bands:
                    fn = layer.get_scaled_filename(sb, band, scale)
                    delfiles.add(fn)
                    fn = modlayer.get_scaled_filename(sb, band, scale)
                    delfiles.add(fn)

        print(len(sbricks), 'scaled bricks at scale', scale, 'are updated')
        print('Deleting', len(delfiles), 'scaled files (if they exist!)')
        ndel = 0
        for fn in delfiles:
            if os.path.exists(fn):
                #print('  Removing', fn)
                os.remove(fn)
                ndel += 1
        print('Actually deleted', ndel, 'scaled files at scale', scale)
        allbricks = layer.get_bricks_for_scale(scale)
        I_touched = np.array([i for i,b in enumerate(allbricks.brickname)
                              if b in sbricks])
        new_bricks = allbricks[I_touched]

def print_tiles(bricks):
    for zoom in range(6, 15):
        zoomscale = 2.**zoom
        W,H = 256,256
        xyset = set()
        for brick in bricks:
            x1 = int(np.floor((360. - brick.ra2)/360. * zoomscale))
            x2 = int(np.floor((360. - brick.ra1)/360. * zoomscale))
            y1 = int(zoomscale * 1./(2.*np.pi) * (np.pi - np.log(np.tan(np.pi/4. + np.deg2rad(brick.dec2)/2.))))
            y2 = int(zoomscale * 1./(2.*np.pi) * (np.pi - np.log(np.tan(np.pi/4. + np.deg2rad(brick.dec1)/2.))))
            for x in range(x1, x2+1):
                for y in range(y1, y2+1):
                    xyset.add((x,y))
        xyset = list(xyset)
        xyset.sort()
        for x,y in xyset:
            # cat update3.txt | xargs -n 6 -P 32 python render-tiles.py --kind ls-dr9-north --ignore
            print('-z %i -x %i -y %i' % (zoom, x, y))
        

def main():
    if False:
        from astrometry.util.fits import fits_table
        from map.views import get_layer
        layer = get_layer('ls-dr10-early')

        r1,r2 = 34.1, 36.75
        d1,d2 = -7.8, -6.7
        
        scale = 8
        #b1 = fits_table('data/ls-dr10-early/survey-bricks-%i.fits.gz' % scale)
        SB = layer.bricks_touching_radec_box(r1, r2, d1, d2,
                                             scale=scale)#, bricks=b1)
        ndel = 0.
        for sb in SB:
            for band in layer.get_bands():
                fn = layer.get_scaled_filename(sb, band, scale)
                if os.path.exists(fn):
                    print('Delete', fn)
                    os.remove(fn)
                    ndel += 1
        print('Actually deleted', ndel, 'scaled files at scale', scale)
        sys.exit(0)
        
    if False:
        from astrometry.util.fits import fits_table
        scale = 4
        b1 = fits_table('data/ls-dr10-early/survey-bricks-%i.fits.gz' % scale)
        brickset = set(b1.brickname)
        print('Scale', scale)
        print('Bricks:', len(brickset))
        fns = glob('data/scaled/ls-dr10-early/%i*/*/image-*.fits.fz' % scale)
        print('Scaled images:', len(fns))
        fns.sort()
        ndel = 0
        keepbricks = set()
        for fn in fns:
            b = fn.split('-')[-2]
            print('file', fn, 'brick', b)
            if not b in brickset:
                print('delete!')
                os.remove(fn)
                ndel += 1
            else:
                keepbricks.add(b)
        print('Deleted', ndel)
        print('Bricks:', len(brickset))
        print('Kept bricks:', len(keepbricks))
        sys.exit(0)
        
    if False:
        from astrometry.util.fits import fits_table
        from map.views import get_layer
        layer = get_layer('ls-dr10-early')
    
        bricks = open('/global/homes/d/dstn/legacypipe/py/deep.txt').read().split('\n')
        bricks = [b.strip() for b in bricks]
        bricks = [b for b in bricks if len(b)]
        #brickset = set(bricks)
    
        b0 = fits_table('data/ls-dr10-early/survey-bricks.fits.gz')
        b1 = fits_table('data/ls-dr10-early/survey-bricks-1.fits.gz')
        bind = dict([(name,i) for i,name in enumerate(b0.brickname)])
        sbricks = set()
        delfiles = set()
        scale = 1
        for bn in bricks:
            i = bind[bn]
            b = b0[i]
    
            SB = layer.bricks_touching_radec_box(b.ra1, b.ra2, b.dec1, b.dec2,
                                                 scale=scale, bricks=b1)
            for sb in SB.brickname:
                sbricks.add(sb)
            for sb in SB:
                for band in layer.get_bands():
                    fn = layer.get_scaled_filename(sb, band, scale)
                    delfiles.add(fn)
        print(len(sbricks), 'scaled bricks at scale', scale, 'to delete')
        print(len(delfiles), 'files to delete')
        ndel = 0
        for fn in delfiles:
            if os.path.exists(fn):
                #print('  Removing', fn)
                os.remove(fn)
                ndel += 1
        print('Actually deleted', ndel, 'scaled files at scale', scale)
    
        exit(-1)
    
    

    sublayers = ['', '-model', '-resid']
    subpretty = {'':' images', '-model':' models', '-resid':' residuals'}

    rsync = False
    symlink = False
    update = True
    queue = False
    custom_brick = False

    survey_dir = '/global/cfs/cdirs/cosmo/work/legacysurvey/dr10/'
    indir = 'data/ls-dr10-early'
    name = 'ls-dr10-early'
    pretty = 'LS DR10 early'

    # /global/cscratch1/sd/dstn/wiro-C/coadd/cus/custom-034600m04950/legacysurvey-custom-034600m04950-*.jpg
    
    #survey_dir = '/global/cscratch1/sd/dstn/wiro-C/'
    # indir = 'data/wiro-C'
    # survey_dir = indir
    # name = 'wiro-C'
    # pretty = 'WIRO C filter'

    indir = 'data/suprime-L484'
    survey_dir = indir
    name = 'suprime-L484'
    pretty = 'Suprime IA-L484 filter'

    indir = '/pscratch/sd/d/dstn/suprime'
    survey_dir = indir
    name = 'suprime-ia-v1'
    pretty = 'Suprime IA v1'
    rsync = True
    
    custom_brick = False
    update = False

    datadir = 'data'

    survey = LegacySurveyData(survey_dir=survey_dir)
    if not custom_brick:
        allbricks = survey.get_bricks_readonly()
    else:
        from astrometry.util.fits import fits_table
        from astrometry.util.util import Tan
        allbricks = fits_table()
        # just look for maskbits because it's the only one that's not band-specific
        pat = os.path.join(survey_dir, 'coadd', 'cus', 'custom-*', 'legacysurvey-custom-*-maskbits.fits.fz')
        ims = glob(pat)
        print('Maskbits files:', pat, '->', ims)
        allbricks.brickname = []
        allbricks.ra = []
        allbricks.dec = []
        allbricks.ra1 = []
        allbricks.ra2 = []
        allbricks.dec1 = []
        allbricks.dec2 = []
        for fn in ims:
            wcs = Tan(fn, 1)
            brickname = fn.split('/')[-2]
            allbricks.brickname.append(brickname)
            H,W = wcs.shape
            rr,dd = wcs.pixelxy2radec( [ (W+1)/2., 1, W, (W+1)/2., (W+1)/2. ],
                                       [ (H+1)/2., (H+1)/2., (H+1)/2., 1, H ] )
            allbricks.ra.append(rr[0])
            allbricks.dec.append(dd[0])
            allbricks.ra1.append(rr[2])
            allbricks.ra2.append(rr[1])
            allbricks.dec1.append(dd[3])
            allbricks.dec2.append(dd[4])
        allbricks.to_np_arrays()
        allbricks.writeto(os.path.join(survey_dir, 'survey-bricks.fits.gz'))
        survey.bricks = allbricks
                
    basedir = os.path.join(datadir, name)

    from astrometry.util.fits import fits_table
    
    if update:
        old_bricks_dir = None
        for i in range(100):
            old_bricks_dir = os.path.join(basedir, 'old-bricks-%i' % i)
            if os.path.exists(old_bricks_dir):
                #print('exists:', old_bricks_dir)
                continue
            os.makedirs(old_bricks_dir)
            print('Created', old_bricks_dir)
            break
        if old_bricks_dir is None:
            sys.exit(-1)

        old_bricks = []
        for scale in range(8):
            if scale == 0:
                fn = 'survey-bricks.fits.gz'
            else:
                fn = 'survey-bricks-%i.fits.gz' % scale
            pathfn = os.path.join(basedir, fn)
            if os.path.exists(pathfn):
                T = fits_table(pathfn)
                print('Read', len(T), 'old bricks from', pathfn)
                old_bricks.append(T)
                ####
                os.rename(pathfn, os.path.join(old_bricks_dir, fn))

    if rsync:
        for sub in ['image-g', 'image-r', 'image-z', 'model-g', 'model-r', 'model-z', 'ccds']:
            cmd = 'rsync -LRarv %s/./coadd/*/*/*-%s*.fits* %s/%s' % (indir, sub, datadir, name)
            print(cmd)
            os.system(cmd)

        cmd = 'rsync -LRarv %s/./tractor %s/%s' % (indir, datadir, name)
        print(cmd)
        os.system(cmd)
        
        # cmd = 'rsync -LRarv %s/./{coadd/*/*/*-{image-,model-,ccds}*.fits*,tractor} %s/%s' % (indir, datadir, name)
        # print(cmd)
        # os.system(cmd)

        # ...?
        cmd = 'rsync -Rarv %s/./{images,survey-ccds*.fits} %s/%s' % (survey_dir, datadir, name)
        print(cmd)
        os.system(cmd)
    if symlink:
        # symlink
        if os.path.exists(basedir):
            print('Not symlinking', indir, 'to', basedir, ': already exists!')
        else:
            os.makedirs(basedir)
            for subdir in ['coadd', 'tractor']:
                os.symlink(os.path.join(indir, subdir), os.path.join(basedir, subdir), target_is_directory=True)
            for subdir in ['images', 'calib']:
                os.symlink(os.path.join(indir, subdir), os.path.join(basedir, subdir), target_is_directory=True)
            for pat in ['survey-ccds-*']:
                fns = glob(os.path.join(indir, pat))
                print('fns', fns)
                for fn in [os.path.basename(f) for f in fns]:
                    print('symlink', os.path.join(indir, subdir), os.path.join(basedir, subdir))
                    os.symlink(os.path.join(indir, fn), os.path.join(basedir, fn), target_is_directory=False)

    # Find new available bricks
    # print('Searching for new extra-image files...')
    extraimagefns = glob(os.path.join(basedir, 'extra-images', 'coadd', '*', '*', '*-image-*.fits*'))
    print('Found', len(extraimagefns), 'extra images')

    # Update all bricks in extra-images...
    if False and update:
        brickset = set()

        # Read list of new bricks
        # f = open('bricks.txt')
        # for line in f.readlines():
        #     brickname = line.strip()
        #     brickset.add(brickname)
        brickset.add('0610m432')
        # for fn in extraimagefns:
        #     dirs = fn.split('/')
        #     brickname = dirs[-2]
        #     brickset.add(brickname)
        print(len(brickset), 'bricks found')
        I, = np.nonzero([b in brickset for b in allbricks.brickname])
        bricks = allbricks[I]

        # Find and delete tiles that overlap each new brick.
        #print_tiles(bricks)
        delete_scaled_images(name, bricks)

        sys.exit(0)

    if False:
        print('Searching for new coadd image files...')
        imagefns = glob(os.path.join(basedir, 'coadd', '*', '*', '*-image-*.fits*'))
        print('Image filenames:', len(imagefns), 'plus', len(extraimagefns), 'extras')
        imagefns += extraimagefns
    
        brickset = set()
        for fn in imagefns:
            dirs = fn.split('/')
            brickname = dirs[-2]
            brickset.add(brickname)

    if False:
        #B = fits_table('/global/cfs/cdirs/cosmo/data/legacysurvey/dr9/south/survey-bricks-dr9-south.fits.gz')
        #     brickset = set(B.brickname)

        bricks = open('/global/homes/d/dstn/legacypipe/py/deep.txt').read().split('\n')
        bricks = [b.strip() for b in bricks]
        bricks = [b for b in bricks if len(b)]
        brickset = set(bricks)

        print(len(brickset), 'bricks found')
        I, = np.nonzero([b in brickset for b in allbricks.brickname])
        bricks = allbricks[I]
    
        brickfn = os.path.join(basedir, 'survey-bricks.fits.gz')
        bricks.writeto(brickfn)
        print('Wrote', brickfn)

    for x in sublayers:
        cmd = 'python3 -u render-tiles.py --kind %s%s --bricks' % (name, x)
        print(cmd)
        os.system(cmd)

    if update:
        # Find and remove existing scaled images touching new bricks.
        old = old_bricks[0]
        old_names = set([str(b) for b in old.brickname])
        I_new = np.array([i for i,b in enumerate(bricks.brickname)
                          if not str(b) in old_names])
        # Newly added bricks
        new_bricks = bricks[I_new]
        print('Added', len(new_bricks), 'bricks')

        print_tiles(new_bricks)
        delete_scaled_images(name, old_bricks, new_bricks)

    fn = 'map/test_layers.py'
    txt = open(fn).read()
    for x in sublayers:
        txt = txt + '\n' + 'test_layers.append(("%s%s", "%s%s"))\n' % (name, x, pretty, subpretty[x])
    open(fn, 'wb').write(txt.encode())
    print('Wrote', fn)

    threads = 32
    tharg = '--threads %i ' % threads
    #tharg = ''

    if queue:

        # from map.views import get_layer
        # imglayer = get_layer(name)
        # modlayer = get_layer(name + '-model')

        ras = np.linspace(0, 360, 361)
        for scale in range(1,8):
            #for layer,layerobj in [(name,imglayer), (name+'-model',modlayer)]:
            for layer in [name, name+'-model']:
                for ralo,rahi in zip(ras, ras[1:]):
                    cmd = 'python3 -u render-tiles.py --kind %s --scale --zoom %i --minra %f --maxra %f' % (layer, scale, ralo, rahi)
                    print(cmd)
        return

    # images
    for scale in range(1,8):
        cmd = 'python3 -u render-tiles.py --kind %s --scale --zoom %i %s' % (name, scale, tharg)
        print(cmd)
        os.system(cmd)

    # models
    for scale in range(1,8):
        cmd = 'python3 -u render-tiles.py --kind %s-model --scale --zoom %i %s' % (name, scale, tharg)
        print(cmd)
        os.system(cmd)

    # resids
    for scale in range(1,8):
        cmd = 'python3 -u render-tiles.py --kind %s-resid --scale --zoom %i %s' % (name, scale, tharg)
        print(cmd)
        os.system(cmd)

    for x in sublayers:
        cmd = 'python3 -u render-tiles.py --kind %s%s --top' % (name, x)
        print(cmd)
        os.system(cmd)



if __name__ == '__main__':
    main()
