from __future__ import print_function
import os
from glob import glob
import numpy as np
from astrometry.util.file import read_file, write_file
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

    indir = '/global/cscratch1/sd/dstn/dr8test007/'
    name = 'dr8-test7'
    pretty = 'DR8 test7 (outliers)'

    # sublayers = ['', '-model', '-resid']
    # subpretty = {'':' images', '-model':' models', '-resid':' residuals'}
    # survey_dir = '/global/cscratch1/sd/desiproc/dr7'

    sublayers = ['']
    subpretty = {'':' images'}
    survey_dir = '/global/cscratch1/sd/dstn/dr8'

    datadir = 'data'

    survey = LegacySurveyData(survey_dir=survey_dir)

    fn = 'map/test_layers.py'
    txt = open(fn).read()
    for x in sublayers:
        txt = txt + '\n' + 'test_layers.append(("%s%s", "%s%s"))\n' % (name, x, pretty, subpretty[x])
    open(fn, 'wb').write(txt.encode())
    print('Wrote', fn)


    cmd = 'rsync -LRarv %s/./{coadd/*/*/*-{image-,model-,ccds}*.fits*,tractor} %s/%s' % (indir, datadir, name)
    print(cmd)
    os.system(cmd)

    # ...?
    cmd = 'rsync -Rarv %s/./{images,survey-ccds*.fits} %s/%s' % (survey_dir, datadir, name)
    print(cmd)
    os.system(cmd)

    basedir = os.path.join(datadir, name)

    allbricks = survey.get_bricks_readonly()

    imagefns = glob(os.path.join(basedir, 'coadd', '*', '*', '*-image-*.fits*'))
    print('Image filenames:', len(imagefns))
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

    threads = 8
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
