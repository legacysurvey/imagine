import fitsio

fn = '/global/project/projectdirs/desi/spectro/data/20191105/00024859/gfa-00024859.fits.fz'

gfa_wcs = {}

F = fitsio.FITS(fn)
for i in range(2, len(F)):
    hdr = F[i].read_header()
    dev = hdr['DEVICE'].strip()
    print(dev)
    wcs = dict([(k,hdr[k]) for k in ['CD1_1', 'CD1_2', 'CD2_1', 'CD2_2',
                                     'CRPIX1', 'CRPIX2', 'CRVAL1', 'CRVAL2']])
    gfa_wcs[dev] = wcs
print(gfa_wcs)

nn = []
nmap = dict()
for k in gfa_wcs.keys():
    n = int(k[-1])
    nn.append(n)
    nmap[n] = k

import numpy as np

gfa_list = []
nn.sort()
for n in nn:
    name = nmap[n]
    gfa_list.append([name, gfa_wcs[name]])

print(gfa_list)
