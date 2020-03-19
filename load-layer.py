from __future__ import print_function
import os
from glob import glob
import numpy as np
from astrometry.util.file import read_file
from legacypipe.survey import LegacySurveyData

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

    #rsync = True
    rsync = False
    #survey_dir = '/global/cfs/cdirs/cosmo/work/legacysurv

    side = 'north'
    #side = 'south'

    survey_dir = '/global/cscratch1/sd/ziyaoz/dr9e4/%s' % side
    indir = survey_dir
    name = 'dr9sv-%s' % side
    pretty = 'DR9-SV %s' % side

    datadir = 'data'

    survey = LegacySurveyData(survey_dir=survey_dir)

    fn = 'map/test_layers.py'
    txt = open(fn).read()
    for x in sublayers:
        txt = txt + '\n' + 'test_layers.append(("%s%s", "%s%s"))\n' % (name, x, pretty, subpretty[x])
    open(fn, 'wb').write(txt.encode())
    print('Wrote', fn)

    basedir = os.path.join(datadir, name)

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

    allbricks = survey.get_bricks_readonly()

    imagefns = glob(os.path.join(basedir, 'coadd', '*', '*', '*-image-*.fits*'))

    extraimagefns = glob(os.path.join(basedir, 'extra-images', 'coadd', '*', '*', '*-image-*.fits*'))

    print('Image filenames:', len(imagefns), 'plus', len(extraimagefns), 'extras')
    imagefns += extraimagefns

    brickset = set()
    for fn in imagefns:
        dirs = fn.split('/')
        brickname = dirs[-2]
        brickset.add(brickname)
    print(len(brickset), 'bricks found')

    I, = np.nonzero([b in brickset for b in allbricks.brickname])
    bricks = allbricks[I]

    brickfn = os.path.join(basedir, 'survey-bricks.fits.gz')
    bricks.writeto(brickfn)
    print('Wrote', brickfn)

    threads = 16
    tharg = '--threads %i ' % threads
    #tharg = ''

    for x in sublayers:
        cmd = 'python -u render-tiles.py --kind %s%s --bricks' % (name, x)
        print(cmd)
        os.system(cmd)

    # images
    for scale in range(1,8):
        cmd = 'python -u render-tiles.py --kind %s --scale --zoom %i %s' % (name, scale, tharg)
        print(cmd)
        os.system(cmd)

    # models
    for scale in range(1,8):
        cmd = 'python -u render-tiles.py --kind %s-model --scale --zoom %i %s' % (name, scale, tharg)
        print(cmd)
        os.system(cmd)

    # resids
    for scale in range(1,8):
        cmd = 'python -u render-tiles.py --kind %s-resid --scale --zoom %i %s' % (name, scale, tharg)
        print(cmd)
        os.system(cmd)

    for x in sublayers:
        cmd = 'python -u render-tiles.py --kind %s%s --top' % (name, x)
        print(cmd)
        os.system(cmd)



if __name__ == '__main__':
    main()
