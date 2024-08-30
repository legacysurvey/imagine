'''
CP files got moved around after DR8... update the CCDs file.
'''

import os
import sys
import pylab as plt
import numpy as np
from glob import glob
import fitsio
from collections import Counter
from astrometry.util.fits import *
from astrometry.util.util import *
from astrometry.libkd.spherematch import match_radec
from tractor import *
from astrometry.util.starutil_numpy import *

#C = fits_table('/global/cfs/cdirs/cosmo/data/legacysurvey/dr8/survey-ccds-decam-dr8.kd.fits')
C = fits_table('data/ls-dr8-south/survey-ccds-dr8-decam-all.kd.fits')
print(Counter(C.plver))

paths = [fn.strip() for fn in C.image_filename]
fns = [p.split('/')[-1] for p in paths]

newfns = []
for plver in np.unique(C.plver):
    plver = plver.strip()
    g = glob('/global/cfs/cdirs/cosmo/staging/decam/CP/' + plver + '/*/*_ooi_*')
    print(len(g), 'in', plver)
    newfns.extend(g)

fnmap = dict()
for i,full in enumerate(newfns):
    fn = full.strip().split('/')[-1]
    full = '/'.join(full.split('/')[6:])
    if not fn in fnmap:
        fnmap[fn] = [full]
    else:
        fnmap[fn].append(full)

#for fn in fns:
#    assert(len(fnmap[fn]) == 1)

found = []
newfns = []
for i,fn in enumerate(fns):
    mapped = fnmap.get(fn, [])
    if len(mapped) != 1:
        print('file', fn, 'got', mapped)
    if len(mapped) == 0:
        continue
    found.append(i)
    newfns.append(mapped[0])

C.cut(np.array(found))
C.image_filename = np.array(newfns)

#C.new_filename = np.array([fnmap[fn][0] for fn in fns])
#C.rename('new_filename', 'image_filename')
C.writeto('/global/cfs/cdirs/cosmo/webapp/viewer-dev/survey-ccds-dr8-fixed.fits')
