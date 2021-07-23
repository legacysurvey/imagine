from __future__ import print_function
import os
from glob import glob
import numpy as np
from astrometry.util.file import read_file
from legacypipe.survey import LegacySurveyData

def delete_scaled_images(name, old_bricks, new_bricks):
    from map.views import get_layer
    layer = get_layer(name)
    modlayer = get_layer(name + '-model')
    print('Got layer:', layer)
    print('Got model layer:', modlayer)
    for scale in range(1, 8):
        if scale >= len(old_bricks):
            print('No old bricks for scale', scale)
            break
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
                for band in ['g','r','z']:
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

    # indir = '/global/cscratch1/sd/dstn/dr8test-1'
    # name = 'dr8-test1'
    # pretty = 'DR8 test1'

    # indir = '/scratch1/scratchdirs/desiproc/dr8test002/'
    # name = 'dr8-test2'
    # pretty = 'DR8 test2 (outliers)'

    # indir = '/scratch1/scratchdirs/desiproc/dr8test003/'
    # name = 'dr8-test3'
    # pretty = 'DR8 test3 (outliers)'
    # 
    # indir = '/scratch1/scratchdirs/desiproc/dr8test004/'
    # name = 'dr8-test4'
    # pretty = 'DR8 test4 (large-galaxies)'

    # indir = '/global/cscratch1/sd/dstn/dr8test005/'
    # name = 'dr8-test5'
    # pretty = 'DR8 test5 (trident)'

    # indir = '/global/cscratch1/sd/dstn/dr8test006/'
    # name = 'dr8-test6'
    # pretty = 'DR8 test6 (sky)'

    # indir = '/global/cscratch1/sd/dstn/dr8test007/'
    # name = 'dr8-test7'
    # pretty = 'DR8 test7 (outliers)'

    #indir = '/global/cscratch1/sd/dstn/dr8test14/'
    #name = 'dr8-test14'
    #pretty = 'DR8 test14 (rc)'

    #indir = '/global/project/projectdirs/cosmo/work/legacysurvey/dr8a/'
    #name = 'dr8a'
    #pretty = 'DR8a (rc)'

    # indir = '/global/project/projectdirs/cosmo/work/legacysurvey/dr8b/runbrick-decam/'
    # name = 'dr8b-decam'
    # pretty = 'DR8b DECam'
    # survey_dir = '/global/project/projectdirs/cosmo/work/legacysurvey/dr8b/runbrick-decam'

    # indir = '/global/project/projectdirs/cosmo/work/legacysurvey/dr8b/runbrick-90prime-mosaic/'
    # name = 'dr8b-90p-mos'
    # pretty = 'DR8b BASS+MzLS'
    # survey_dir = '/global/project/projectdirs/cosmo/work/legacysurvey/dr8b/runbrick-90prime-mosaic'

    rsync = False
    #indir = '/global/project/projectdirs/cosmo/work/legacysurvey/dr8c/90prime-mosaic/'
    #name = 'dr8c-90p-mos'
    #pretty = 'DR8c BASS+MzLS'
    survey_dir = '/global/cscratch1/sd/landriau/dr8'
    # ln -s /global/project/projectdirs/cosmo/work/legacysurvey/dr8b/runbrick-decam/coadds-only/coadd/ .

    #indir = '/scratch1/scratchdirs/desiproc/dr8/decam/'
    indir = 'data/dr8c-decam'
    name = 'dr8c-decam'
    pretty = 'DR8c DECam'
    #rsync = True

    indir = 'data/dr8i-decam'
    name = 'dr8i-decam'
    pretty = 'DR8i DECam'

    indir = 'data/dr8i-90p-mos'
    name = 'dr8i-90p-mos'
    pretty = 'DR8i MzLS+BASS'



    sublayers = ['', '-model', '-resid']
    subpretty = {'':' images', '-model':' models', '-resid':' residuals'}
    
    # #indir = '/global/cscratch1/sd/ziyaoz/dr9c/'
    # #indir = '/global/cscratch1/sd/dstn/dr9c-fpack/'
    # #rsync = True
    # indir = 'data/dr9c'
    # name = 'dr9c'
    # pretty = 'DR9c'
    # survey_dir = indir
    # 
    # indir = '/global/cscratch1/sd/ziyaoz/dr9d-south/'
    # #rsync = True
    # name = 'dr9d-south'
    # pretty = 'DR9d south'
    # survey_dir = indir

    
    # indir = '/global/cscratch1/sd/ziyaoz/dr9d-north/'
    # #rsync = True
    # name = 'dr9d-north'
    # pretty = 'DR9d north'
    # survey_dir = indir

    # code runs:
    #    rsync -LRarv /global/cscratch1/sd/ziyaoz/dr9d-south//./{coadd/*/*/*-{image-,model-,ccds}*.fits*,tractor} data/dr9d-south
    # add my image-coadds:
    #    rsync -LRarv /global/cscratch1/sd/dstn/dr9d-coadds/./coadd/*/*/*-{image-,ccds}*.fits* data/dr9d-south
    
    # survey_dir = '/global/cscratch1/sd/desiproc/dr7'

    # sublayers = ['']
    # subpretty = {'':' images'}
    
    #survey_dir = '/global/cscratch1/sd/dstn/dr8-depthcut'
    #survey_dir = '/global/project/projectdirs/cosmo/work/legacysurvey/dr8a/'

    rsync = True
    #survey_dir = '/global/cfs/cdirs/cosmo/work/legacysurv

    side = 'north'
    #side = 'south'

    survey_dir = '/global/cscratch1/sd/ziyaoz/dr9e4/%s' % side
    indir = survey_dir
    name = 'dr9sv-%s' % side
    pretty = 'DR9-SV %s' % side

    rsync = False
    survey_dir = '/global/cfs/cdirs/cosmo/work/legacysurvey/dr9'
    indir = '/global/cscratch1/sd/dstn/fornax'
    name = 'fornax'
    pretty = 'Fornax'

    rsync = True
    survey_dir = '/global/cfs/cdirs/cosmo/work/legacysurvey/dr9'
    indir = '/global/cscratch1/sd/dstn/dr9.2'
    name = 'dr9-test-9.2'
    pretty = 'DR9.2 test'

    survey_dir = '/global/cscratch1/sd/ziyaoz/dr9j/south'
    indir = survey_dir
    name = 'dr9j-south'
    pretty = 'DR9j south'

    rsync = False
    if True:
        #indir = '/global/cscratch1/sd/ziyaoz/dr9m/north/'
        indir = '/global/cfs/cdirs/cosmo/work/legacysurvey/dr9m/north'
        name = 'dr9m-north'
        pretty = 'DR9m-north'
        survey_dir = '/global/cfs/cdirs/cosmo/work/legacysurvey/dr9m'

    if True:
        indir = '/global/cfs/cdirs/cosmo/work/legacysurvey/dr9/south'
        name = 'ls-dr9-south'
        pretty = 'Legacy Surveys DR9 south'
        survey_dir = '/global/cfs/cdirs/cosmo/work/legacysurvey/dr9'

    update = True
    update = False
    queue = False


    # indir = '/global/cfs/cdirs/cosmo/work/legacysurvey/dr9.1.1'
    # indir = '/global/cscratch1/sd/landriau/dr9.1.1'
    # indir = 'fake-dr9.1.1'
    # name = 'ls-dr9.1.1'
    # pretty = 'DR9.1.1 COSMOS deep'
    # survey_dir = indir

    # rsync = True
    # update = False
    # queue = False
    # indir = '/global/cscratch1/sd/dstn/m33-2/south/'
    # name = 'dr9-m33'
    # pretty = 'DR9m-M33'
    # survey_dir = '/global/cfs/cdirs/cosmo/work/legacysurvey/dr9m'
    

    indir = 'data/asteroids-i'
    name = 'asteroids-i'
    pretty = 'Asteroids test'
    survey_dir = indir
    
    datadir = 'data'

    survey = LegacySurveyData(survey_dir=survey_dir)
    allbricks = survey.get_bricks_readonly()
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
    else:
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
        delete_scaled_images(name, old_bricks, bricks)

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
    else:
        B = fits_table('/global/cfs/cdirs/cosmo/data/legacysurvey/dr9/south/survey-bricks-dr9-south.fits.gz')
        brickset = set(B.brickname)

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
