from __future__ import print_function
from functools import lru_cache
import os

if __name__ == '__main__':
    import sys
    sys.path.insert(0, 'django-1.9')
    os.environ['DJANGO_SETTINGS_MODULE'] = 'viewer.settings'
    import django
    django.setup()

from django.http import HttpResponse
from viewer import settings
try:
    from django.core.urlresolvers import reverse
except:
    # django 2.0
    from django.urls import reverse
from map.utils import send_file, trymakedirs, get_tile_wcs, oneyear

debug = print
if not settings.DEBUG_LOGGING:
    def debug(*args, **kwargs):
        pass

catversions = {
    'hsc-dr2-cosmos': [1,],
    'dr9sv': [1,],
    'dr9sv-north': [1,],
    'dr9sv-south': [1,],
    'ls-dr9': [1,],
    'ls-dr9-north': [1,],
    'ls-dr9-south': [1,],
    'ls-dr8': [1,],
    'ls-dr8-north': [1,],
    'ls-dr8-south': [1,],
    'decals-dr7': [1,],
    'mzls+bass-dr6': [1,],
    'ls-dr67':[1,],
    'decals-dr5': [1,],
    'ngc': [1,],
    'GCs-PNe': [1,],
    'lslga': [1,],
    'sga': [1,],
    'spec': [1,],
    'spec-deep2': [1,],
    'manga': [1,],
    'bright': [1,],
    'tycho2': [1,],
    'targets-dr67': [1,],
    'targets-bgs-dr67': [1,],
    'targets-sky-dr67': [1,],
    'targets-bright-dr67': [1,],
    'targets-dark-dr67': [1,],
    'targets-cmx-dr7': [1,],
    'targets-dr8': [1,],
    'targets-sv-dr8': [1,],
    'targets-dr9-sv1-sec-bright':[1,],
    'targets-dr9-sv1-sec-dark':[1,],
    'targets-dr9-sv1-dark':[1,],
    'targets-dr9-sv1-bright':[1,],
    'targets-dr9-sv1-supp':[1,],
    'targets-dr9-sv3-bright':[1,],
    'targets-dr9-sv3-dark':[1,],
    'targets-dr9-sv3-sec-bright':[1,],
    'targets-dr9-sv3-sec-dark':[1,],
    'targets-dr9-main-bright':[1,],
    'targets-dr9-main-dark':[1,],
    'targets-dr9-main-sec-bright':[1,],
    'targets-dr9-main-sec-dark':[1,],
    'gaia-dr1': [1,],
    'gaia-dr2': [1,],
    'gaia-edr3': [1,],
    'sdss-cat': [1,],
    'phat-clusters': [1,],
    'ps1': [1,],
    'desi-tiles': [1,],
    'masks-dr8': [1,],
    'photoz-dr9': [1,],
    'desi-edr-tiles': [1,],
    'desi-edr-spectra': [1,],
    'desi-daily-tiles': [1,],
    'desi-daily-spectra': [1,],
    'desi-fuji-tiles': [1,],
    'desi-fuji-spectra': [1,],
    'desi-guadalupe-tiles': [1,],
    'desi-guadalupe-spectra': [1,],
    'ls-dr10': [1,],
    'ls-dr10-south': [1,],
}

test_cats = []
try:
    from map.test_layers import test_cats as tc
    for key,pretty in tc:
        catversions[key] = [1,]
except:
    pass


def gaia_stars_for_wcs(req):
    import json
    from legacypipe.gaiacat import GaiaCatalog
    from astrometry.util.util import Tan
    import os
    import numpy as np
    
    os.environ['GAIA_CAT_DIR'] = os.path.join(settings.DATA_DIR, 'gaia-dr2')

    J = json.loads(req.POST['wcs'])
    print('Got WCS values:', J)
    reply = []
    gaia = GaiaCatalog()
    for jwcs in J:
        wcs = Tan(*[float(jwcs[k]) for k in
                    ['crval1', 'crval2', 'crpix1', 'crpix2', 'cd11', 'cd12', 'cd21', 'cd22',
                     'width', 'height']])
        stars = gaia.get_catalog_in_wcs(wcs)
        I = np.argsort(stars.phot_g_mean_mag)
        stars.cut(I[:10])
        ok,xx,yy = wcs.radec2pixelxy(stars.ra, stars.dec)

        def clean(x):
            if np.isfinite(x):
                return float(x)
            return 0.

        reply.append([
            dict(ra=clean(g.ra), dec=clean(g.dec),
                 g=clean(g.phot_g_mean_mag), bp=clean(g.phot_bp_mean_mag),
                 rp=clean(g.phot_rp_mean_mag), x=clean(x), y=clean(y))
            for g,x,y in zip(stars, xx, yy)])
    return HttpResponse(json.dumps(reply),
                        content_type='application/json')

def cat_desi_release_spectra_detail(req, tile, fiber, release):
    from glob import glob
    from desispec.io import read_spectra
    import numpy as np
    import os
    from astropy.table import Table
    import astropy
    from desispec.spectra import stack
    import tempfile
    import os
    import prospect.viewer

    tile = int(tile)
    fiber = int(fiber)
    sp = fiber//500
    pat = ('/global/cfs/cdirs/desi/spectro/redux/%s/tiles/cumulative/%i/*/coadd-%i-%i-thru*.fits'
           % (release, tile, sp, tile))
    #print('Searching', pat)
    fns = glob(pat)
    fns.sort()
    fn = fns[-1]
    spectra = read_spectra(fn)
    keep = np.in1d(spectra.fibermap['FIBER'], [fiber])
    spectra = spectra[keep]

    zbests = []

    # I don't understand why some daily spectra seem to be 'zbest' and some 'redrock'
    # eg zbest https://www.legacysurvey.org/viewer-desi/desi-spectrum/daily/targetid39628433252155537
    # /global/cfs/cdirs/desi/spectro/redux/daily/tiles/cumulative/125/20210504/zbest

    # #- Read matching zbest file for this spectra/coadd file
    # if release in []:#'daily']:
    #     fntag = 'zbest'
    #     extname = 'ZBEST'
    # else:
    #     fntag = 'redrock'
    #     extname = 'REDSHIFTS'

    # Just gd try both
    for fntag,extname in [('redrock', 'REDSHIFTS'), ('zbest', 'ZBEST')]:
        zbfile = os.path.basename(fn).replace('coadd', fntag, 1)
        zbfile = os.path.join(os.path.dirname(fn), zbfile)
        if not os.path.exists(zbfile):
            continue
        zb = Table.read(zbfile, extname)
    #- Trim zb to only have TARGETIDs in filtered spectra sp
    keep = np.in1d(zb['TARGETID'], spectra.fibermap['TARGETID'])
    zb = zb[keep]
    #- spectra files can have multiple entries per TARGETID,
    #- while zbest files have only 1.  Expand to match spectra.
    #- Note: astropy.table.join changes the order
    if len(spectra.fibermap) > len(zb):
        zbx = Table()
        zbx['TARGETID'] = spectra.fibermap['TARGETID']
        zbx = astropy.table.join(zbx, zb, keys='TARGETID')
    else:
        zbx = zb
    #- Sort the zbx Table to match the order of sp['TARGETID']
    ii = np.argsort(spectra.fibermap['TARGETID'])
    jj = np.argsort(zbx['TARGETID'])
    kk = np.argsort(ii[jj])
    zbx = zbx[kk]
    zbests = zbx
    #- Confirm that we got all that expanding and sorting correct
    assert np.all(spectra.fibermap['TARGETID'] == zbests['TARGETID'])

    print('Passing to prospect: spectra:')
    print(spectra)
    print('zcatalog:')
    print(zbests)
    
    os.environ['RR_TEMPLATE_DIR'] = os.path.join(settings.DATA_DIR, 'redrock-templates')
    with tempfile.TemporaryDirectory() as d:
        prospect.viewer.plotspectra(spectra, zcatalog=zbests, html_dir=d)
        f = open(os.path.join(d, 'prospect.html')) #'specviewer_specviewer.html'))
        return HttpResponse(f)
        
    return HttpResponse('tile %i fiber %i' % (tile, fiber))

def desi_healpix_spectrum(req, obj, release):
    from glob import glob
    from desispec.io import read_spectra
    import numpy as np
    import os
    from astropy.table import Table
    import astropy
    from desispec.spectra import stack
    import tempfile
    import os
    import prospect.viewer

    prog = obj.program.strip()
    surv = obj.survey.strip()
    hp = '%i' % obj.healpix
    hp_pre = '%i' % (obj.healpix//100)

    if release == 'edr':
        basedir = '/global/cfs/cdirs/desi/public/edr/spectro/redux/fuji'
    else:
        basedir = '/global/cfs/cdirs/desi/spectro/redux/%s' % release

    
    fn = os.path.join(basedir, 'healpix', surv, prog, hp_pre, hp,
                      'coadd-%s-%s-%s.fits' % (surv, prog, hp))

    spectra = read_spectra(fn)
    spectra = spectra.select(targets=[obj.targetid])
    if spectra.num_targets() != 1:
        return HttpResponse('Expected to find 1 spectrum, got %i for TARGETID %i in file %s' %
                            (spectra.num_targets(), obj.targetid, fn))
    zbests = []
    #- Read matching zbest file for this spectra/coadd file
    zbfile = os.path.basename(fn).replace('coadd', 'redrock', 1)
    zbfile = os.path.join(os.path.dirname(fn), zbfile)
    zb = Table.read(zbfile, 'REDSHIFTS')
    #- Trim zb to only have TARGETIDs in filtered spectra sp
    keep = np.in1d(zb['TARGETID'], spectra.fibermap['TARGETID'])
    zb = zb[keep]
    assert(len(spectra.fibermap) == 1)
    assert(len(zb) == 1)
    zbests = zb
    #- Confirm that we got all that expanding and sorting correct
    assert np.all(spectra.fibermap['TARGETID'] == zbests['TARGETID'])

    os.environ['RR_TEMPLATE_DIR'] = os.path.join(settings.DATA_DIR, 'redrock-templates')
    #if True:
    #    d = tempfile.mkdtemp()
    with tempfile.TemporaryDirectory() as d:
        prospect.viewer.plotspectra(spectra, zcatalog=zbests, html_dir=d)
        f = open(os.path.join(d, 'prospect.html'))
        return HttpResponse(f)
        
def get_desi_spectro_kdfile(release):
    if release == 'edr':
        return os.path.join(settings.DATA_DIR, 'desi-spectro-edr', 'zpix-all.kd.fits')
    elif release == 'daily':
        return os.path.join(settings.DATA_DIR, 'desi-spectro-daily', 'allzbest.kd.fits')
    elif release == 'guadalupe':
        return os.path.join(settings.DATA_DIR, 'desi-spectro-guadalupe', 'zpix-all.kd.fits')
    elif release == 'fuji':
        return os.path.join(settings.DATA_DIR, 'desi-spectro-fuji', 'zpix-all.kd.fits')
    elif release == 'denali':
        return os.path.join(settings.DATA_DIR, 'desi-spectro-denali',
                            'zcatalog-denali-cumulative.kd.fits')
    return None

def lookup_targetid(targetid, release):
    from astrometry.libkd.spherematch import tree_open
    from astrometry.util.fits import fits_table
    import numpy as np
    fn = get_desi_spectro_kdfile(release)
    kd = tree_open(fn, 'targetid')
    print('Searching for targetid', targetid)
    #I = kd.search(np.array([float(targetid)]), 0.5, 0, 0)
    I = kd.search(np.array([targetid]).astype(np.uint64), 0.5, 0, 0)
    if len(I) == 0:
        return None
    print('Found', len(I), 'entries for targetid', targetid)
    # Read only the allzbest table rows within range.
    T = fits_table(fn, rows=I)
    print('Matched targetids:', T.targetid)
    I = np.flatnonzero(T.targetid == targetid)
    if len(I) == 0:
        return None
    i = I[0]
    return T[i]

def cat_desi_daily_spectra_detail(req, targetid):
    targetid = int(targetid)
    t = lookup_targetid(targetid, 'daily')
    if t is None:
        return HttpResponse('No such targetid found in DESI daily spectra: %s' % targetid)
    return cat_desi_release_spectra_detail(req, t.tileid, t.fiber, 'daily')

def cat_desi_guadalupe_spectra_detail(req, targetid):
    targetid = int(targetid)
    t = lookup_targetid(targetid, 'guadalupe')
    if t is None:
        return HttpResponse('No such targetid found in DESI Guadalupe spectra: %s' % targetid)
    return desi_healpix_spectrum(req, t, 'guadalupe')

def cat_desi_fuji_spectra_detail(req, targetid):
    targetid = int(targetid)
    t = lookup_targetid(targetid, 'fuji')
    if t is None:
        return HttpResponse('No such targetid found in DESI Fuji spectra: %s' % targetid)
    return desi_healpix_spectrum(req, t, 'fuji')

def cat_desi_edr_spectra_detail(req, targetid):
    targetid = int(targetid)
    t = lookup_targetid(targetid, 'edr')
    if t is None:
        return HttpResponse('No such targetid found in DESI EDR spectra: %s' % targetid)
    return desi_healpix_spectrum(req, t, 'edr')

def cat_desi_release_spectra(req, ver, kdfn, tag, racol='ra', deccol='dec',
                             tile_clusters=None):
    import json
    T = cat_kd(req, ver, tag, kdfn, racol=racol, deccol=deccol)
    print('Got', len(T), 'spectra')

    if T is None:
        return HttpResponse(json.dumps(dict(rd=[], name=[], color=[])), #, z=[], zerr=[])),
                            content_type='application/json')

    tileid = None
    if 'tile' in req.GET:
        try:
            tileid = int(req.GET['tile'])
        except:
            pass
    if tileid is not None:
        T.cut(T.tileid == tileid)

    J = {}
    print('Got', len(T), 'spectra')
    if len(T) > 1000:
        import numpy as np
        from scipy.spatial import ConvexHull
        
        # Split into a 3x3 grid?  Cluster?
        # Then find convex hull and send polygon & count?
        ralo = float(req.GET['ralo'])
        rahi = float(req.GET['rahi'])
        declo = float(req.GET['declo'])
        dechi = float(req.GET['dechi'])

        ra_wrap = ralo > rahi
        if ra_wrap:
            # Move RAs to +- 0
            T.ra_wrap = T.ra + -360 * (T.ra > 180)
            ralo -= 360
        else:
            T.ra_wrap = T.ra

        assert(ralo < rahi)
        assert(declo < dechi)

        cluster_edges = []
        cluster_labels = []

        Iloose = []

        from astrometry.util.miscutils import point_in_poly, clip_polygon

        Iclusters = []

        # Use pre-computed cluster membership!
        if tile_clusters is not None:
            cl = np.unique(T.tile_cluster)
            print(len(cl), 'unique clusters')
            for cl_i in cl:
                rd = tile_clusters[cl_i]
                ra,dec = rd[:,0],rd[:,1]
                if ra_wrap:
                    ra_w = ra + -360 * (ra > 180)
                else:
                    ra_w = ra
                I = np.flatnonzero(T.tile_cluster == cl_i)
                print(len(I), 'spectra in cluster', cl_i)
                Iclusters.append((I, (ra,ra_w,dec)))

        # if tile_clusters is None:
        #     tile_clusters = []
        # for cl_i,rd in enumerate(tile_clusters):
        #     #print('Tile cluster boundary:', rd.shape)
        #     ra,dec = rd[:,0],rd[:,1]
        #     if ra_wrap:
        #         ra_w = ra + -360 * (ra > 180)
        #     else:
        #         ra_w = ra
        #     # completely outside RA,Dec region?
        #     if min(ra_w) > rahi or max(ra_w) < ralo or min(dec) > dechi or max(dec) < declo:
        #         #print('Tile not nearby, skipping')
        #         continue
        #     poly = np.vstack((ra_w,dec)).T
        #     #print('Poly', poly.shape)
        #     isin = point_in_poly(T.ra_wrap, T.dec, np.vstack((ra_w,dec)).T)
        #     I = np.flatnonzero(isin)
        #     print(len(I), 'spectra in cluster', cl_i)
        #     if len(I) == 0:
        #         continue
        #     Iclusters.append((I, (ra,ra_w,dec)))

        if len(Iclusters) > 1:
            for I,(ra,ra_w,dec) in Iclusters:
                if len(I) < 100:
                    Iloose.append(I)
                    continue
                K = np.flatnonzero((ra_w > ralo) * (ra_w < rahi) * (dec > declo) * (dec < dechi))
                if len(K) > 0:
                    cra,cdec = np.mean(np.vstack((ra_w[K], dec[K])), axis=1)
                else:
                    cra = (ralo + rahi) / 2.
                    cdec = (declo + dechi) / 2.
                if cra < 0:
                    cra += 360.
                #cliprd = clip_polygon(np.vstack((ra_w,dec)).T,
                #                      np.array([[ralo,declo],[ralo,dechi],[rahi,dechi],[rahi,declo]]))
                #cliprd = np.array(cliprd)
                #ra,dec = cliprd[:,0], cliprd[:,1]
                cluster_edges.append([(float(r),float(d)) for r,d in zip(ra,dec)])
                cluster_labels.append([float(cra), float(cdec), '%i spectra' % len(I)])


            # No grid!
            nra = ndec = 0

        else:
            # grid
            nra = ndec = 3

        for i in range(ndec):
            for j in range(nra):
                r1 = ralo +  j * (rahi - ralo) / nra
                r2 = ralo + (j+1) * (rahi - ralo) / nra
                d1 = declo +  i * (dechi - declo) / ndec
                d2 = declo + (i+1) * (dechi - declo) / ndec
                I = np.flatnonzero((T.ra_wrap >= r1) * (T.ra_wrap < r2) *
                                   (T.dec >= d1)  * (T.dec < d2))
                print(len(I), 'in grid cell', j, i)
                if len(I) == 0:
                    continue

                if len(I) < 100:
                    Iloose.append(I)
                    continue

                try:
                    ch = ConvexHull(np.vstack((T.ra_wrap[I], T.dec[I])).T)
                except:
                    import traceback
                    print_exc()
                    continue
                Ivert = I[ch.vertices]
                ch = np.vstack((T.ra[Ivert], T.dec[Ivert])).T
                #print('Convex hull:', ch)
                chw = np.vstack((T.ra_wrap[Ivert], T.dec[Ivert])).T
                c = np.mean(chw, axis=0)
                cra,cdec = c
                if cra < 0:
                    cra += 360.
                #print('Center of convex hull:', cra,cdec)
                cluster_edges.append([(float(r),float(d)) for r,d in ch])
                cluster_labels.append([float(cra), float(cdec), '%i spectra' % len(I)])

        J.update(cluster_edges=cluster_edges,
                 cluster_labels=cluster_labels)
        if len(Iloose):
            I = np.hstack(Iloose)
            T.cut(I)
            # Continue to add the loose ones into J...
        else:
            return HttpResponse(json.dumps(J), content_type='application/json')

    cols = T.get_columns()
    rd = list((float(r),float(d)) for r,d in zip(T.get(racol), T.get(deccol)))
        
    # objtype -- FIXME -- can we unpack TARGETID enough to figure out SKY fibers?
    if 'objtype' in T.get_columns():
        objtype = T.objtype
    else:
        objtype = ['']*len(T)
    
    names = []
    colors = []
    for ot,t,st,z,zerr,zw in zip(objtype, T.spectype, T.subtype, T.z, T.zerr, T.zwarn):
        c = '#3388ff'
        t = t.strip()
        nm = t
        st = st.strip()
        if st != '':
            nm += ':' + st
        if t != 'STAR':
            nm += ', z = %.3f' % z

        ot = ot.strip()
        if ot == 'SKY':
            c = '#448888'
            nm = ot
        if t == 'STAR':
            c = '#ff4444'
        elif t == 'GALAXY':
            c = '#ffffff'
        elif t == 'QSO':
            c = '#4444ff'
            
        if zw > 0:
            nm += ' (ZWARN=0x%x)' %zw
            c = '#888888'
        names.append(nm)
        colors.append(c)

    J.update(dict(rd=rd, name=names, color=colors,
                  targetid=[str(i) for i in T.targetid]))
    if 'fiber' in cols:
        J.update(fiberid=[int(i) for i in T.fiber])
    if 'tileid' in cols:
        J.update(tileid=[int(i) for i in T.tileid])
    return HttpResponse(json.dumps(J), content_type='application/json')

def cat_desi_daily_spectra(req, ver):
    kdfn = get_desi_spectro_kdfile('daily')
    tag = 'desi-daily-spectra'
    return cat_desi_release_spectra(req, ver, kdfn, tag)

def cat_desi_guadalupe_spectra(req, ver):
    '''
    TT = []
    for surv,prog in [('main','dark'), ('main','bright'), ('special','dark'), ('special','bright')]:
        fn = '/global/cfs/cdirs/desi/spectro/redux/guadalupe/zcatalog/zpix-%s-%s.fits' % (surv, prog)
        T = fits_table(fn, columns=['target_ra','target_dec','targetid','z','zerr','zwarn','spectype','subtype',
                                             'healpix', 'objtype'])
        T.survey = np.array([surv]*len(T))
        T.program = np.array([prog]*len(T))
        TT.append(T)
    T = merge_tables(TT)
    T.writeto('cosmo/webapp/viewer-desi/data/desi-spectro-guadalupe/zpix-all.fits')
    '''
    # python -c "from desi_spectro_kdtree import create_desi_spectro_kdtree as create; create('data/desi-spectro-guadalupe/zpix-all.fits', 'data/desi-spectro-guadalupe/zpix-all.kd.fits', racol='target_ra', deccol='target_dec')"
    kdfn = get_desi_spectro_kdfile('guadalupe')
    tag = 'desi-guadalupe-spectra'
    return cat_desi_release_spectra(req, ver, kdfn, tag, racol='target_ra', deccol='target_dec')


def cat_desi_fuji_spectra(req, ver):
    '''
    sys.path.append('cosmo/webapp/viewer-desi/')
    from desi_spectro_kdtree import create_desi_spectro_kdtree
    TT = []
    for surv,prog in [('cmx','other'), ('special','dark'), ('sv1','backup'), ('sv1','bright'),
                     ('sv1','other'), ('sv2','backup'), ('sv2','bright'), ('sv2','dark'),
                     ('sv3','backup'), ('sv3','bright'), ('sv3','dark')]:
        fn = '/global/cfs/cdirs/desi/spectro/redux/fuji/zcatalog/zpix-%s-%s.fits' % (surv, prog)
        T = fits_table(fn, columns=['target_ra','target_dec','targetid','z','zerr','zwarn','spectype','subtype',
                                             'healpix', 'objtype'])
        T.survey = np.array([surv]*len(T))
        T.program = np.array([prog]*len(T))
        TT.append(T)
    T = merge_tables(TT)
    fn = 'cosmo/webapp/viewer-desi/data/desi-spectro-fuji/zpix-all.fits'
    T.writeto(fn)
    create_desi_spectro_kdtree(fn, 'cosmo/webapp/viewer-desi/data/desi-spectro-fuji/zpix-all.kd.fits', racol='target_ra', deccol='target_dec')
    '''
    kdfn = get_desi_spectro_kdfile('fuji')
    tag = 'desi-fuji-spectra'
    return cat_desi_release_spectra(req, ver, kdfn, tag, racol='target_ra', deccol='target_dec')

def cat_desi_edr_spectra(req, ver):
    kdfn = get_desi_spectro_kdfile('edr')
    tag = 'desi-edr-spectra'
    clusters = open(os.path.join(settings.DATA_DIR, 'desi-spectro-edr', 'tile-clusters.json')).read()
    import json
    import numpy as np
    clusters = json.loads(clusters)
    clusters = [np.array(cl).reshape(-1,2) for cl in clusters]

    return cat_desi_release_spectra(req, ver, kdfn, tag, racol='target_ra', deccol='target_dec',
                                    tile_clusters=clusters)

def cat_desi_release_tiles(req, ver, release):
    import json
    from astrometry.util.fits import fits_table
    from astrometry.libkd.spherematch import tree_open, tree_search_radec
    import numpy as np
    ver = int(ver)
    tag = 'desi-%s-tiles' % release
    if not ver in catversions[tag]:
        raise RuntimeError('Invalid version %i for tag %s' % (ver, tag))
    ralo = float(req.GET['ralo'])
    rahi = float(req.GET['rahi'])
    declo = float(req.GET['declo'])
    dechi = float(req.GET['dechi'])

    desi_radius = 1.628
    fn = os.path.join(settings.DATA_DIR, 'desi-spectro-%s/tiles2.kd.fits' % release)

    def result(T):
        res = []
        for t in T:
            name = 'Tile %i' % t.tileid
            details = []
            prog = None
            if 'program' in t.get_columns():
                prog = t.program.strip()
            else:
                prog = t.faprgrm.strip()
            if prog != 'unknown':
                details.append(prog)
            surv = t.survey.strip()
            if surv != 'unknown':
                details.append(surv)
            if len(details):
                name += ' (%s)' % ', '.join(details)

            cc = {
                ('dark','main'):  '#22aadd',
                ('bright','main'): '#cc8800',
                ('dark','special'): '#77ccee',
                ('bright','special'): '#ffbb33',
                }.get((prog, surv), '#888888')
                
            res.append(dict(name=name, ra=t.tilera, dec=t.tiledec, radius=desi_radius,
                            color=cc))
        return HttpResponse(json.dumps(dict(objs=res)),
                            content_type='application/json')

    if dechi - declo > 10:
        T = fits_table(fn)
        return result(T)
    
    rc,dc,rad = radecbox_to_circle(ralo, rahi, declo, dechi)
    kd = tree_open(fn)
    I = tree_search_radec(kd, rc, dc, rad + desi_radius)
    T = fits_table(fn, rows=I)
    return result(T)

def cat_desi_daily_tiles(req, ver):
    return cat_desi_release_tiles(req, ver, 'daily')

def cat_desi_guadalupe_tiles(req, ver):
    #startree -i /global/cfs/cdirs/desi/spectro/redux/guadalupe/tiles-guadalupe.fits -R tilera -D tiledec -PTk -o data/desi-spectro-guadalupe/tiles2.kd.fits
    return cat_desi_release_tiles(req, ver, 'guadalupe')

def cat_desi_fuji_tiles(req, ver):
    #startree -i /global/cfs/cdirs/desi/spectro/redux/fuji/tiles-fuji.fits -R tilera -D tiledec -PTk -o data/desi-spectro-fuji/tiles2.kd.fits
    return cat_desi_release_tiles(req, ver, 'fuji')

def cat_desi_edr_tiles(req, ver):
    return cat_desi_release_tiles(req, ver, 'edr')

def cat_photoz_dr9(req, ver):
    '''
    I pre-processed the photo-z sweep files like this to create a kd-tree per sweep:

    pzfns = glob('/global/cscratch1/sd/rongpu/dr9_photoz/south/sweep-*.fits')
    pzfns.sort()
    for pzfn in pzfns:
        outfn = ('/global/cfs/cdirs/cosmo/webapp/viewer-dev/data/photoz/dr9-south/'
                 + os.path.basename(pzfn).replace('.fits', '.kd.fits'))
        if os.path.exists(outfn):
            print('Exists:', outfn)
            continue
        sweepfn = pzfn.replace('/global/cscratch1/sd/rongpu/dr9_photoz/south',
                               '/global/cfs/cdirs/cosmo/data/legacysurvey/dr9/south/sweep/9.0').replace(
                            '-pz.fits', '.fits')
        PZ = fits_table(pzfn)
        if not np.any(PZ.z_phot_mean > -99):
            print('Skipping', pzfn)
            continue
        SW = fits_table(sweepfn, columns=['ra','dec'])
        assert(len(PZ) == len(SW))
        PZ.ra  = SW.ra
        PZ.dec = SW.dec
        print(pzfn)
        print('Before cut:', len(PZ))
        PZ.cut(PZ.z_phot_mean > -99)
        print('After  cut:', len(PZ))
        if len(PZ) == 0:
            continue
        PZ.writeto('/tmp/pz.fits')
        cmd = ('startree -i /tmp/pz.fits -o %s -PTk' % outfn)
        print(cmd)
        os.system(cmd)
    '''
    import numpy as np
    import json
    from astrometry.libkd.spherematch import tree_open, tree_search_radec
    from astrometry.util.fits import fits_table, merge_tables
    from astrometry.util.starutil_numpy import radectolb
    tag = 'photoz-dr9'
    ralo = float(req.GET['ralo'])
    rahi = float(req.GET['rahi'])
    declo = float(req.GET['declo'])
    dechi = float(req.GET['dechi'])
    rc,dc,rad = radecbox_to_circle(ralo, rahi, declo, dechi)

    ver = int(ver)
    if not ver in catversions[tag]:
        raise RuntimeError('Invalid version %i for tag %s' % (ver, tag))

    TT = []
    # find relevant sweep files
    rastep = 10
    decstep = 5
    r1 = rastep * np.floor(ralo / rastep).astype(int)
    r2 = rastep * np.ceil (rahi / rastep).astype(int)
    d1 = decstep * np.floor(declo / decstep).astype(int)
    d2 = decstep * np.ceil (dechi / decstep).astype(int)
    # Too big an area?
    empty = json.dumps(dict(rd=[], phot_z_mean=[], phot_z_std=[]))
    if (d2 - d1) * (r2 - r1) > 200:
        return HttpResponse(empty, content_type='application/json')

    decsplit = 32.375
    
    for hemi in ['north', 'south']:
        for d in range(d1, d2, decstep):
            for r in range(r1, r2, rastep):
                dsign = 'p' if d >= 0 else 'm'
                d2sign = 'p' if (d+decstep) >= 0 else 'm'
                fn = os.path.join(settings.DATA_DIR, 'photoz', 'dr9-' + hemi,
                                  'sweep-%03i%s%03i-%03i%s%03i-pz.kd.fits' %
                                  (r, dsign, abs(d), r+rastep, d2sign, abs(d+decstep)))
                if not os.path.exists(fn):
                    print('No such file:', fn)
                    continue
                kd = tree_open(fn)
                I = tree_search_radec(kd, rc, dc, rad)
                print('Matched', len(I), 'from', fn)
                if len(I) == 0:
                    continue
                T = fits_table(fn, rows=I)
                ll,bb = radectolb(T.ra, T.dec)
                ngc = (bb > 0.)
                if hemi == 'north':
                    T.cut((T.dec >= decsplit) * ngc)
                else:
                    T.cut(np.logical_or(T.dec <= decsplit, np.logical_not(ngc)))
                if len(T) == 0:
                    continue
                T.cut((T.ra  >= ralo ) * (T.ra  <= rahi) *
                      (T.dec >= declo) * (T.dec <= dechi))
                if len(T) == 0:
                    continue
                TT.append(T)
    if len(TT) == 0:
        return HttpResponse(empty, content_type='application/json')
    T = merge_tables(TT)
    return HttpResponse(json.dumps(dict(
        rd=[(float(r),float(d)) for r,d in zip(T.ra, T.dec)],
        phot_z_mean=[float(z) for z in T.z_phot_mean],
        phot_z_std=[float(z) for z in T.z_phot_std],
    )), content_type='application/json')
    
def cat_phat_clusters(req, ver):
    import json
    from astrometry.util.fits import fits_table, merge_tables

    tag = 'phat-clusters'
    ralo = float(req.GET['ralo'])
    rahi = float(req.GET['rahi'])
    declo = float(req.GET['declo'])
    dechi = float(req.GET['dechi'])

    ver = int(ver)
    if not ver in catversions[tag]:
        raise RuntimeError('Invalid version %i for tag %s' % (ver, tag))

    cat = fits_table(os.path.join(settings.DATA_DIR, 'phat-clusters.fits'))
    cat.cut((cat.ra  >= ralo ) * (cat.ra  <= rahi) *
            (cat.dec >= declo) * (cat.dec <= dechi))

    return HttpResponse(json.dumps(dict(
        name=[str(s.strip()) for s in cat.name],
        rd=[(float(o.ra),float(o.dec)) for o in cat],
        mag=[float(o.mag) for o in cat],
        young=[bool(o.young) for o in cat],
        velocity=[float(o.velocity) for o in cat],
        metallicity=[float(o.metallicity) for o in cat],
    )),
                        content_type='application/json')

def cat_gaia_edr3(req, ver):
    import legacypipe.gaiacat
    print('legacypipe.gaiacat:', legacypipe.gaiacat.__file__)
    catdir = os.path.join(settings.DATA_DIR, 'gaia-edr3')
    return cat_gaia_dr2(req, ver, catdir=catdir, prefix='healpix', indexing='nested')

def cat_gaia_dr2(req, ver, catdir=None, prefix=None, indexing=None):
    import json
    from legacypipe.gaiacat import GaiaCatalog
    import numpy as np

    tag = 'gaia-dr2'
    ralo = float(req.GET['ralo'])
    rahi = float(req.GET['rahi'])
    declo = float(req.GET['declo'])
    dechi = float(req.GET['dechi'])

    ver = int(ver)
    if not ver in catversions[tag]:
        raise RuntimeError('Invalid version %i for tag %s' % (ver, tag))

    if catdir is None:
        catdir = os.path.join(settings.DATA_DIR, 'gaia-dr2')

    os.environ['GAIA_CAT_DIR'] = catdir
    kwa = {}
    if prefix is not None:
        kwa.update(file_prefix=prefix)
    if indexing is not None:
        kwa.update(indexing=indexing)
    gaia = GaiaCatalog(**kwa)
    cat = gaia.get_catalog_radec_box(ralo, rahi, declo, dechi)

    for c in ['ra','dec','phot_g_mean_mag','phot_bp_mean_mag', 'phot_rp_mean_mag',
              'pmra','pmdec','parallax',
              'pmra_error', 'pmdec_error', 'parallax_error',
              'astrometric_excess_noise']:
        val = cat.get(c)
        val[np.logical_not(np.isfinite(val))] = 0.
        cat.set(c, val)

    return HttpResponse(json.dumps(dict(
        rd=[(float(o.ra),float(o.dec)) for o in cat],
        sourceid=[str(o.source_id) for o in cat],
        gmag=[float(o.phot_g_mean_mag) for o in cat],
        bpmag=[float(o.phot_bp_mean_mag) for o in cat],
        rpmag=[float(o.phot_rp_mean_mag) for o in cat],
        pmra=[float(o.pmra) for o in cat],
        pmdec=[float(o.pmdec) for o in cat],
        parallax=[float(o.parallax) for o in cat],
        pmra_err=[float(o.pmra_error) for o in cat],
        pmdec_err=[float(o.pmdec_error) for o in cat],
        parallax_err=[float(o.parallax_error) for o in cat],
        astrometric_excess_noise=[float(o.astrometric_excess_noise) for o in cat],
    )),
                        content_type='application/json')


def cat_sdss(req, ver):
    import json
    import numpy as np

    from map.views import sdss_ccds_near
    from astrometry.util.fits import fits_table, merge_tables

    tag = 'sdss-cat'
    ralo = float(req.GET['ralo'])
    rahi = float(req.GET['rahi'])
    declo = float(req.GET['declo'])
    dechi = float(req.GET['dechi'])

    ver = int(ver)
    if not ver in catversions[tag]:
        raise RuntimeError('Invalid version %i for tag %s' % (ver, tag))

    rc,dc,rad = radecbox_to_circle(ralo, rahi, declo, dechi)
    rad = rad + np.hypot(10.,14.)/2./60.
    ccds = sdss_ccds_near(rc, dc, rad)
    if ccds is None:
        print('No SDSS CCDs nearby')
        return HttpResponse(json.dumps(dict(rd=[])),
                            content_type='application/json')
    print(len(ccds), 'SDSS CCDs')

    T = []
    for ccd in ccds:
        # env/BOSS_PHOTOOBJ/301/2073/3/photoObj-002073-3-0088.fits
        fn = os.path.join(settings.SDSS_BASEDIR, 'env', 'BOSS_PHOTOOBJ',
                          str(ccd.rerun), str(ccd.run), str(ccd.camcol),
                          'photoObj-%06i-%i-%04i.fits' % (ccd.run, ccd.camcol, ccd.field))
        print('Reading', fn)
        T.append(fits_table(fn, columns='ra dec objid mode objc_type objc_flags objc_flags nchild tai expflux devflux psfflux cmodelflux fracdev mjd'.split()))
    T = merge_tables(T)
    T.cut((T.dec >= declo) * (T.dec <= dechi))
    # FIXME
    T.cut((T.ra  >= ralo) * (T.ra <= rahi))
    
    # primary
    T.cut(T.mode == 1)
    types = ['P' if t == 6 else 'C' for t in T.objc_type]
    fluxes = [p if t == 6 else c for t,p,c in zip(T.objc_type, T.psfflux, T.cmodelflux)]

    return HttpResponse(json.dumps(dict(
        rd=[(float(o.ra),float(o.dec)) for o in T],
        sourcetype=types,
        fluxes = [dict(u=float(f[0]), g=float(f[1]), r=float(f[2]),
                       i=float(f[3]), z=float(f[4])) for f in fluxes],
    )),
                        content_type='application/json')

def rename_cols(T):
    """If TARGET_RA and TARGET_DEC exists, rename them to ra, dec

    Parameters
    ----------
    T : :class:`astrometry.util.fits.tabledata`
    A table data object, parsed from user upload

    Returns
    -------
    boolean
    true if renaming took place, false if otherwise
    """
    cols = T.columns()
    if (('target_ra' in cols) and ('target_dec' in cols)
        and ('ra' not in cols) and ('dec' not in cols)):
        T.rename('target_ra', 'ra')
        T.rename('target_dec', 'dec')
        return True
    return False

def upload_cat(req):
    import tempfile
    from astrometry.util.fits import fits_table
    from django.http import HttpResponseRedirect
    from map.views import index

    if req.method != 'POST':
        return HttpResponse('POST only')
    print('Files:', req.FILES)
    cat = req.FILES['catalog']

    dirnm = settings.USER_QUERY_DIR
    if not os.path.exists(dirnm):
        try:
            os.makedirs(dirnm)
        except:
            pass
    f,tmpfn = tempfile.mkstemp(suffix='.fits', dir=dirnm)
    os.close(f)
    os.unlink(tmpfn)
    print('Saving to', tmpfn)
    with open(tmpfn, 'wb+') as destination:
        for chunk in cat.chunks():
            destination.write(chunk)
    print('Wrote', tmpfn)

    errtxt = ('<html><body>%s<p>Custom catalogs must be either a: <ul>'
              + '<li><b>FITS binary table</b> with columns named "RA", "DEC" (not case sensitive) and optionally "NAME".'
              + '<li><b>CSV text file</b> with columns "RA", "DEC", and optionally "NAME" (also not case sensitive)</ul>'
              +'See <a href="https://www.legacysurvey.org/svtips/">Tips & Tricks</a> for some hints on how to produce such a catalog.</p></body></html>')

    T = None
    emsg = ''
    try:
        T = fits_table(tmpfn)
    except Exception as e:
        emsg = str(e)
    if T is None:
        try:
            # Try CSV...
            from astropy.table import Table
            t = Table.read(tmpfn, format='ascii').write(tmpfn, overwrite=True)
            T = fits_table(tmpfn)
        except Exception as e:
            emsg += '; ' + str(e)
    if T is None:
        return HttpResponse(errtxt % ('Error: '+emsg))

    # Rename and resave columns if necessary
    if rename_cols(T):
        T.write_to(tmpfn)

    cols = T.columns()
    if not (('ra' in cols) and ('dec' in cols)):
        return HttpResponse(errtxt % '<p>Did not find column "RA" and "DEC" in table.</p>')

    ra,dec = T.ra[0], T.dec[0]
    catname = tmpfn.replace(dirnm, '').replace('.fits', '')
    if catname.startswith('/'):
        catname = catname[1:]

    try:
        import fitsio
        primhdr = fitsio.read_header(tmpfn)
        name = primhdr.get('CATNAME', '')
        color = primhdr.get('CATCOLOR', '')
        if len(name):
            catname = catname + '-n%s' % name.strip().replace(' ','_')
        if len(color):
            catname = catname + '-c%s' % color.strip()
    except:
        pass

    from map.views import my_reverse
    return HttpResponseRedirect(my_reverse(req, index) +
                                '?ra=%.4f&dec=%.4f&catalog=%s' % (ra, dec, catname))

galaxycats = {}
def get_random_galaxy(layer=None):
    import numpy as np
    from map.views import layer_to_survey_name

    if layer is not None:
        layer = layer_to_survey_name(layer)

    global galaxycats
    if layer == 'mzls+bass-dr6':
        galfn = os.path.join(settings.DATA_DIR, 'galaxies-in-dr6.fits')
        drnum = 6
    elif layer == 'decals-dr7':
        galfn = os.path.join(settings.DATA_DIR, 'galaxies-in-dr7.fits')
        drnum = 7
    elif layer == 'decals-dr5':
        galfn = os.path.join(settings.DATA_DIR, 'galaxies-in-dr5.fits')
        drnum = 5
    elif layer == 'hsc2':
        galfn = os.path.join(settings.DATA_DIR, 'galaxies-in-hsc2.fits')
    elif 'ls-dr8' in layer:
        drnum = 8
        galfn = os.path.join(settings.DATA_DIR, 'galaxies-in-dr8.fits')
    elif layer == 'ls-dr9-north':
        drnum = 9
        galfn = os.path.join(settings.DATA_DIR, 'galaxies-in-ls-dr9-north.fits')
    elif layer in ['ls-dr9-south', 'ls-dr9']:
        drnum = 9
        galfn = os.path.join(settings.DATA_DIR, 'galaxies-in-ls-dr9-south.fits')
    elif 'ls-dr10-south' in layer:
        drnum = 10
        galfn = os.path.join(settings.DATA_DIR, 'galaxies-in-ls-dr10-south.fits')
    elif 'ls-dr10' in layer:
        drnum = 10
        galfn = os.path.join(settings.DATA_DIR, 'galaxies-in-ls-dr10.fits')
    else:
        drnum = 9
        galfn = os.path.join(settings.DATA_DIR, 'galaxies-in-dr9.fits')

    if (not layer in galaxycats) and not os.path.exists(galfn):
        if settings.CREATE_GALAXY_CATALOG:
            try:
                create_galaxy_catalog(galfn, drnum)
            except:
                import traceback
                traceback.print_exc()
        if not os.path.exists(galfn):
            if drnum == 4:
                return 147.1744, 44.0812, 'NGC 2998'
            else:
                return 18.6595, -1.0210, 'NGC 442'

    if not layer in galaxycats:
        from astrometry.util.fits import fits_table

        galaxycats[layer] = fits_table(galfn)

        ### HACK
        #cat = fits_table(galfn)
        #cat.cut(cat.dec < 30.)
        #galaxycats[layer] = cat
        
    galaxycat = galaxycats[layer]
    i = np.random.randint(len(galaxycat))
    ra = float(galaxycat.ra[i])
    dec = float(galaxycat.dec[i])
    name = galaxycat.name[i].strip()
    return ra,dec,name

def create_galaxy_catalog(galfn, drnum, layer=None):
    import astrometry.catalogs
    from astrometry.util.fits import fits_table, merge_tables
    import fitsio
    from astrometry.util.util import Tan
    from astrometry.libkd.spherematch import match_radec
    import numpy as np

    #fn = os.path.join(os.path.dirname(astrometry.catalogs.__file__), 'ngc2000.fits')
    fn = os.path.join(os.path.dirname(astrometry.catalogs.__file__), 'openngc-ngc.fits')
    NGC = fits_table(fn)
    print(len(NGC), 'NGC objects')
    NGC.name = np.array(['NGC %i' % n for n in NGC.ngcnum])
    NGC.delete_column('ngcnum')
    
    #fn = os.path.join(os.path.dirname(astrometry.catalogs.__file__), 'ic2000.fits')
    fn = os.path.join(os.path.dirname(astrometry.catalogs.__file__), 'openngc-ic.fits')
    IC = fits_table(fn)
    print(len(IC), 'IC objects')
    IC.name = np.array(['IC %i' % n for n in IC.icnum])
    IC.delete_column('icnum')

    # fn = os.path.join(settings.DATA_DIR, 'ugc.fits')
    # UGC = fits_table(fn)
    # print(len(UGC), 'UGC objects')
    # UGC.name = np.array(['UGC %i' % n for n in UGC.ugcnum])
    # UGC.delete_column('ugcnum')

    #T = merge_tables([NGC, IC, UGC])
    #T.writeto(os.path.join(settings.DATA_DIR, 'galaxy-cats.fits'))

    T = merge_tables([NGC, IC])
    T.writeto(os.path.join('/tmp/ngcic.fits'))
    
    keep = np.zeros(len(T), bool)

    from map.views import get_survey

    bricks = None

    if layer is not None:
        bricks = layer.get_bricks()
        name = layer.name
        survey = None
    else:
        name = 'dr%i' % drnum
        if drnum == 6:
            survey = get_survey('mzls+bass-dr6')
            bricks = survey.get_bricks()
            bricks.cut(bricks.has_g * bricks.has_r * bricks.has_z)
        elif drnum == 5:
            survey = get_survey('decals-dr5')
        elif drnum == 7:
            survey = get_survey('decals-dr7')

    if bricks is None:
        bricks = survey.get_bricks()
        
    I,J,d = match_radec(bricks.ra, bricks.dec, T.ra, T.dec, 0.25, nearest=True)
    print('Matched', len(I), 'bricks near NGC objects')
    bricks.cut(I)

    for brick in bricks:
        I = np.flatnonzero((T.ra  >= brick.ra1 ) * (T.ra  < brick.ra2 ) *
                           (T.dec >= brick.dec1) * (T.dec < brick.dec2))
        print('Brick', brick.brickname, 'has', len(I), 'galaxies')
        if len(I) == 0:
            continue

        keep[I] = True
        
        if survey is None:
            continue
        fn = survey.find_file('nexp', brick=brick.brickname, band='r')
        if not os.path.exists(fn):
            print('Does not exist:', fn)
            continue
        
        nn,hdr = fitsio.read(fn, header=True)
        h,w = nn.shape
        #imgfn = survey.find_file('image', brick=brick.brickname, band='r')
        #wcs = Tan(imgfn)
        print('file', fn)
        wcs = Tan(hdr)

        ok,x,y = wcs.radec2pixelxy(T.ra[I], T.dec[I])
        x = np.clip((x-1).astype(int), 0, w-1)
        y = np.clip((y-1).astype(int), 0, h-1)
        n = nn[y,x]
        keep[I[n > 0]] = True

    T.cut(keep)
    fn = '/tmp/galaxies-in-%s.fits' % name
    T.writeto(fn)
    print('Wrote', fn)
    T.writeto(galfn)

def cat_targets_dr8(req, ver):
    return cat_targets_drAB(req, ver, cats=[
        os.path.join(settings.DATA_DIR, 'targets-dr8-0.31.1-main.kd.fits'),
        ], tag='targets-dr8')

def cat_targets_sv_dr8(req, ver):
    return cat_targets_drAB(req, ver, cats=[
        os.path.join(settings.DATA_DIR, 'targets-dr8-0.31.1-sv.kd.fits'),
        ], tag='targets-sv-dr8', colprefix='sv1_')

def cat_targets_cmx_dr7(req, ver):
    return cat_targets_drAB(req, ver, cats=[
        os.path.join(settings.DATA_DIR, 'targets-cmx-0.27.0.kd.fits'),
        ], tag='targets-cmx-dr7', color_name_func=desi_cmx_color_names)

def cat_targets_dr67(req, ver):
    return cat_targets_drAB(req, ver, cats=[
        os.path.join(settings.DATA_DIR, 'targets-dr6-0.22.0.kd.fits'),
        os.path.join(settings.DATA_DIR, 'targets-dr7.1-0.29.0.kd.fits'),
    ], tag = 'targets-dr67')

def cat_targets_bgs_dr67(req, ver):
    return cat_targets_drAB(req, ver, cats=[
        os.path.join(settings.DATA_DIR, 'targets-dr6-0.22.0.kd.fits'),
        os.path.join(settings.DATA_DIR, 'targets-dr7.1-0.29.0.kd.fits'),
    ], tag = 'targets-bgs-dr67', bgs=True)

def cat_targets_sky_dr67(req, ver):
    return cat_targets_drAB(req, ver, cats=[
        os.path.join(settings.DATA_DIR, 'skies-dr6-0.22.0.kd.fits'),
        os.path.join(settings.DATA_DIR, 'skies-dr7.1-0.22.0.kd.fits'),
    ], tag = 'targets-sky-dr67', sky=True)

def cat_targets_bright_dr67(req, ver):
    return cat_targets_drAB(req, ver, cats=[
        os.path.join(settings.DATA_DIR, 'targets-dr6-0.22.0.kd.fits'),
        os.path.join(settings.DATA_DIR, 'targets-dr7.1-0.29.0.kd.fits'),
    ], tag = 'targets-bright-dr67', bright=True)

def cat_targets_dark_dr67(req, ver):
    return cat_targets_drAB(req, ver, cats=[
        os.path.join(settings.DATA_DIR, 'targets-dr6-0.22.0.kd.fits'),
        os.path.join(settings.DATA_DIR, 'targets-dr7.1-0.29.0.kd.fits'),
    ], tag = 'targets-dark-dr67', dark=True)
def cat_targets_dr8b(req, ver):
    return cat_targets_drAB(req, ver, cats=[
        os.path.join(settings.DATA_DIR, 'targets-dr8b-0.29.0.kd.fits'),
    ], tag='targets-dr8b')
def cat_targets_dr8c(req, ver):
    return cat_targets_drAB(req, ver, cats=[
        os.path.join(settings.DATA_DIR, 'targets-dr8c-PR490.kd.fits'),
    ], tag='targets-dr8c')
def cat_targets_dr9_sv1_sec_bright(req, ver):
    # /global/cscratch1/sd/adamyers/dr9/0.47.0.dev4352/targets/sv1/secondary/dark/sv1targets-dark-secondary.fits
    return cat_targets_drAB(req, ver, cats=[
        os.path.join(settings.DATA_DIR,
                     'targets-dr9-0.49.0-sv1-secondary-bright.kd.fits'),
                     #'targets-sv1-secondary-dark.kd.fits'),
    ], tag='targets-dr9-sv1-sec-bright', name_func=desitarget_sv1_names, colprefix='sv1_',
    color_name_func=None)
def cat_targets_dr9_sv1_sec_dark(req, ver):
    # /global/cscratch1/sd/adamyers/dr9/0.47.0.dev4352/targets/sv1/secondary/dark/sv1targets-dark-secondary.fits
    return cat_targets_drAB(req, ver, cats=[
        os.path.join(settings.DATA_DIR,
                     'targets-dr9-0.49.0-sv1-secondary-dark.kd.fits'),
                     #'targets-sv1-secondary-dark.kd.fits'),
    ], tag='targets-dr9-sv1-sec-dark', name_func=desitarget_sv1_names, colprefix='sv1_',
    color_name_func=None)

def cat_targets_healpixed(req, ver, tag, catpat, name_func=None, colprefix='', nside=8,
                          bgs=False, sky=False, bright=False, dark=False):
    import json
    ralo = float(req.GET['ralo'])
    rahi = float(req.GET['rahi'])
    declo = float(req.GET['declo'])
    dechi = float(req.GET['dechi'])
    ver = int(ver)
    if not ver in catversions[tag]:
        raise RuntimeError('Invalid version %i for tag %s' % (ver, tag))
    from astrometry.util.fits import fits_table, merge_tables
    from astrometry.libkd.spherematch import tree_open, tree_search_radec
    from astrometry.util.util import healpix_rangesearch_radec, healpix_xy_to_nested, healpix_side_length_arcmin, healpix_rangesearch_radec_approx
    import numpy as np
    # hackily bump up the healpix search radius...
    #hpr = healpix_side_length_arcmin(nside) / 60.
    #print('Healpix side length:', hpr, 'deg')
    rplus = 0.01 * healpix_side_length_arcmin(nside) / 60.
    #rplus = 0.
    rc,dc,rad = radecbox_to_circle(ralo, rahi, declo, dechi)
    print('RA,Dec', rc,dc, 'radius', rad, 'rplus', rplus)
    hps = healpix_rangesearch_radec(rc, dc, rad+rplus, nside)
    #hps = healpix_rangesearch_radec_approx(rc, dc, np.deg2rad(rad + rplus), nside)
    print('Healpixes', hps)
    TT = []
    for hp in hps:
        from astrometry.util.util import healpix_to_radecdeg
        from astrometry.util.starutil import degrees_between
        hr,hd = healpix_to_radecdeg(hp, nside, 0.5, 0.5)
        dist = degrees_between(hr,hd, rc,dc)
        print('Healpix center:', hr,hd)
        print('Dist from HP', hp, ':', dist)
        
        hpx = healpix_xy_to_nested(hp, nside)
        fn = catpat % hpx
        if not os.path.exists(fn):
            print('No such file:', fn)
            continue
        kd = tree_open(fn)
        I = tree_search_radec(kd, rc, dc, rad)
        print('Matched', len(I), 'from', fn)
        if len(I) == 0:
            continue
        T = fits_table(fn, rows=I)
        TT.append(T)
    if len(TT) == 0:
        return HttpResponse(json.dumps(dict(rd=[], name=[])),
                            content_type='application/json')
    T = merge_tables(TT, columns='fillzero')

    # cut to RA,Dec rectangle
    margin = (dechi - declo) * 0.05
    rmargin = margin / np.cos(np.deg2rad(dc))
    T.cut((T.dec > (declo-margin)) * (T.dec < (dechi+margin)))
    if ralo > rahi:
        T.cut(np.logical_or(T.ra  > (ralo-rmargin), T.ra  < (rahi+rmargin)))
    else:
        T.cut((T.ra  > (ralo-rmargin)) * (T.ra  < (rahi+rmargin)))
    
    if bgs:
        bgs_target = T.get(colprefix + 'bgs_target')
        T.cut(bgs_target > 0)
    if bright:
        bgs_target = T.get(colprefix + 'bgs_target')
        mws_target = T.get(colprefix + 'mws_target')
        T.cut(np.logical_or(bgs_target > 0, mws_target > 0))
    if dark:
        desi_target = T.get(colprefix + 'desi_target')
        T.cut(T.desi_target > 0)

    names = None
    if name_func is not None:
        names = name_func(T, colprefix=colprefix)

    rtn = dict(rd=[(t.ra, t.dec) for t in T],
               # Convert targetid to string to prevent rounding errors in Javascript
               targetid=[str(t) for t in T.targetid])
    if names is not None:
        rtn.update(name=names)
    return HttpResponse(json.dumps(rtn), content_type='application/json')

def desitarget_main_names(T, colprefix='main_'):
    from desitarget.targetmask import desi_mask, bgs_mask, mws_mask, scnd_mask

    allnames = []
    colors = []
    cols = T.get_columns()
    for t in T:
        desibits = []
        bgsbits = []
        mwsbits = []
        secbits = []
        desi_target = int(t.get(colprefix + 'desi_target'))
        bgs_target = get_target_val(t, colprefix + 'bgs_target', cols)
        mws_target = get_target_val(t, colprefix + 'mws_target', cols)
        scnd_target = get_target_val(t, colprefix + 'scnd_target', cols)
        if 'objtype' in cols:
            obj = t.objtype
        else:
            obj = ''

        names = []

        desi_keys = ['LRG', 'ELG', 'QSO', 'QSO_HIZ', 'ELG_LOP', 'ELG_HIP', 'ELG_VLO',
                     'SKY', 'STD_FAINT', 'STD_WD', 'STD_BRIGHT', 'BAD_SKY', 'SUPP_SKY',
                     'NO_TARGET', 'BRIGHT_OBJECT', 'IN_BRIGHT_OBJECT', 'NEAR_BRIGHT_OBJECT',]
        for k in desi_keys:
            bitmask = desi_mask[k].mask
            if bitmask & desi_target:
                names.append(k)

        bgs_keys = ['BGS_FAINT', 'BGS_BRIGHT', 'BGS_WISE', 'BGS_FAINT_HIP']
        for k in bgs_keys:
            bitmask = bgs_mask[k].mask
            if bitmask & bgs_target:
                names.append(k)

        mws_keys = ['MWS_BROAD', 'MWS_WD', 'MWS_NEARBY', 'MWS_BHB', 'MWS_MAIN_BLUE',
                    'MWS_MAIN_RED', 'MWS_FAINT_BLUE', 'MWS_FAINT_RED', 'GAIA_STD_FAINT',
                    'GAIA_STD_WD', 'GAIA_STD_BRIGHT', 'BACKUP_BRIGHT', 'BACKUP_FAINT',
                    'BACKUP_VERY_FAINT']
        for k in mws_keys:
            bitmask = mws_mask[k].mask
            if bitmask & mws_target:
                names.append(k)

        scnd_keys = ['UDG', 'FIRST_MALS', 'QSO_RED', 'MWS_CLUS_GAL_DEEP', 'LOW_MASS_AGN',
                     'FAINT_HPM', 'LOW_Z_TIER1', 'LOW_Z_TIER2', 'LOW_Z_TIER3', 'BHB', 'SPCV',
                     'DC3R2_GAMA', 'PSF_OUT_BRIGHT', 'PSF_OUT_DARK', 'HPM_SOUM', 'SN_HOSTS',
                     'GAL_CLUS_BCG', 'GAL_CLUS_2ND', 'GAL_CLUS_SAT', 'STRONG_LENS',
                     'WISE_VAR_QSO', 'Z5_QSO', 'MWS_MAIN_CLUSTER_SV', 'BRIGHT_HPM',
                     'WD_BINARIES_BRIGHT', 'WD_BINARIES_DARK', 'PV_BRIGHT_HIGH',
                     'PV_BRIGHT_MEDIUM', 'PV_BRIGHT_LOW', 'PV_DARK_HIGH', 'PV_DARK_MEDIUM',
                     'PV_DARK_LOW', 'GC_BRIGHT', 'GC_DARK', 'DWF_BRIGHT_HI', 'DWF_BRIGHT_LO',
                     'DWF_DARK_HI', 'DWF_DARK_LO', 'BRIGHT_TOO_LOP', 'BRIGHT_TOO_HIP',
                     'DARK_TOO_LOP', 'DARK_TOO_HIP']
        for k in scnd_keys:
            bitmask = scnd_mask[k].mask
            if bitmask & scnd_target:
                names.append(k)

        if obj == 'SKY':
            names.append('SKY')
        if obj == 'BAD':
            names.append('BAD')
        if len(names) == 0:
            names.append('0x%x' % desi_target)
        allnames.append(', '.join(names))
    return allnames

def cat_targets_dr9_main_sec_bright(req, ver):
    # startree -i /global/cfs/cdirs/desi/target/catalogs/dr9/0.58.0/targets/main/secondary/bright/targets-bright-secondary.fits -o data/targets-dr9-0.58.0-main-sec-bright.kd.fits -TPk
    return cat_targets_drAB(req, ver, cats=[
        os.path.join(settings.DATA_DIR,
                     'targets-dr9-0.58.0-main-sec-bright.kd.fits'),
    ], tag='targets-dr9-main-sec-bright', name_func=desitarget_main_names, colprefix='',
    color_name_func=None)

def cat_targets_dr9_main_sec_dark(req, ver):
    # startree -i /global/cfs/cdirs/desi/target/catalogs/dr9/0.58.0/targets/main/secondary/dark/targets-dark-secondary.fits -o data/targets-dr9-0.58.0-main-sec-dark.kd.fits -TPk
    return cat_targets_drAB(req, ver, cats=[
        os.path.join(settings.DATA_DIR,
                     'targets-dr9-0.58.0-main-sec-dark.kd.fits'),
    ], tag='targets-dr9-main-sec-dark', name_func=desitarget_main_names, colprefix='',
    color_name_func=None)


def cat_targets_dr9_main_dark(req, ver):
    # for x in /global/cfs/cdirs/desi/target/catalogs/dr9/0.58.0/targets/main/resolve/dark/targets-dark-hp-*.fits;
    # do echo $x; startree -i $x -o data/targets-dr9-0.58.0-main-dark/$(basename $x .fits).kd.fits -TPk; done
    return cat_targets_healpixed(req, ver, 'targets-dr9-main-dark',
                                 os.path.join(settings.DATA_DIR,
                                              'targets-dr9-0.58.0-main-dark',
                                              'targets-dark-hp-%i.kd.fits'),
                                 name_func=desitarget_main_names, colprefix='')
def cat_targets_dr9_main_bright(req, ver):
    # for x in /global/cfs/cdirs/desi/target/catalogs/dr9/0.58.0/targets/main/resolve/bright/targets-bright-hp-*.fits;
    # do echo $x; startree -i $x -o data/targets-dr9-0.58.0-main-bright/$(basename $x .fits).kd.fits -TPk; done
    return cat_targets_healpixed(req, ver, 'targets-dr9-main-bright',
                                 os.path.join(settings.DATA_DIR,
                                              'targets-dr9-0.58.0-main-bright',
                                              'targets-bright-hp-%i.kd.fits'),
                                 name_func=desitarget_main_names, colprefix='')





def cat_targets_dr9_sv3_sec_bright(req, ver):
    # startree -i /global/cfs/cdirs/desi/target/catalogs/dr9/0.57.0/targets/sv3/secondary/bright/sv3targets-bright-secondary.fits -o data/targets-dr9-0.57.0-sv3-sec-bright.kd.fits -TPk
    return cat_targets_drAB(req, ver, cats=[
        os.path.join(settings.DATA_DIR,
                     'targets-dr9-0.57.0-sv3-sec-bright.kd.fits'),
    ], tag='targets-dr9-sv3-sec-bright', name_func=desitarget_sv3_names, colprefix='sv3_',
    color_name_func=None)

def cat_targets_dr9_sv3_sec_dark(req, ver):
    # startree -i /global/cfs/cdirs/desi/target/catalogs/dr9/0.57.0/targets/sv3/secondary/dark/sv3targets-dark-secondary.fits -o data/targets-dr9-0.57.0-sv3-sec-dark.kd.fits -TPk
    return cat_targets_drAB(req, ver, cats=[
        os.path.join(settings.DATA_DIR,
                     'targets-dr9-0.57.0-sv3-sec-dark.kd.fits'),
    ], tag='targets-dr9-sv3-sec-dark', name_func=desitarget_sv3_names, colprefix='sv3_',
    color_name_func=None)


def cat_targets_dr9_sv3_dark(req, ver):
    # for x in /global/cfs/cdirs/desi/target/catalogs/dr9/0.57.0/targets/sv3/resolve/dark/sv3targets-dark-hp-*.fits;
    # do echo $x; startree -i $x -o data/targets-dr9-0.57.0-sv3-dark/$(basename $x .fits).kd.fits -TPk; done
    return cat_targets_healpixed(req, ver, 'targets-dr9-sv3-dark',
                                 os.path.join(settings.DATA_DIR,
                                              #'targets-dr9-0.47.0.dev4352-sv1-dark',
                                              'targets-dr9-0.57.0-sv3-dark',
                                              'sv3targets-dark-hp-%i.kd.fits'),
                                 name_func=desitarget_sv3_names, colprefix='sv3_')
def cat_targets_dr9_sv3_bright(req, ver):
    return cat_targets_healpixed(req, ver, 'targets-dr9-sv3-bright',
                                 os.path.join(settings.DATA_DIR,
                                              'targets-dr9-0.57.0-sv3-bright',
                                              'sv3targets-bright-hp-%i.kd.fits'),
                                 name_func=desitarget_sv3_names, colprefix='sv3_')

def cat_targets_dr9_sv1_dark(req, ver):
    # for x in /global/cscratch1/sd/adamyers/dr9/0.47.0.dev4352/targets/sv1/resolve/dark/*.fits;
    #  do echo $x; startree -i $x -o data/targets-dr9-0.47.0.dev4352-sv1-dark/$(basename $x .fits).kd.fits -TPk; done
    return cat_targets_healpixed(req, ver, 'targets-dr9-sv1-dark',
                                 os.path.join(settings.DATA_DIR,
                                              #'targets-dr9-0.47.0.dev4352-sv1-dark',
                                              'targets-dr9-0.49.0-sv1-dark',
                                              'sv1targets-dark-hp-%i.kd.fits'),
                                 name_func=desitarget_sv1_names, colprefix='sv1_')
def cat_targets_dr9_sv1_bright(req, ver):
    return cat_targets_healpixed(req, ver, 'targets-dr9-sv1-bright',
                                 os.path.join(settings.DATA_DIR,
                                              #'targets-dr9-0.47.0.dev4352-sv1-bright',
                                              'targets-dr9-0.49.0-sv1-bright',
                                              'sv1targets-bright-hp-%i.kd.fits'),
                                 name_func=desitarget_sv1_names, colprefix='sv1_')
def cat_targets_dr9_sv1_supp(req, ver):
    pass
# /global/cscratch1/sd/adamyers/dr9/0.47.0.dev4352/targets/sv1/resolve/dark/
# /global/cscratch1/sd/adamyers/dr9/0.47.0.dev4352/targets/sv1/resolve/bright/
# /global/cscratch1/sd/adamyers/gaiadr2/0.47.0.dev4352/targets/sv1/resolve/supp/

def desitarget_cmx_names(T):
    names = []
    colors = []
    for t in T:
        cmxbits = []
        cmx_target = int(t.cmx_target)
        obj = t.objtype
        for bit in range(64):
            if (1 << bit) & cmx_target:
                cmxbits.append(bit)
            # https://github.com/desihub/desitarget/blob/master/py/desitarget/cmx/data/cmx_targetmask.yaml
            cmxnames = [{
                0:  'STD_GAIA',
                1:  'SV0_STD_FAINT',
                2:  'SV0_STD_BRIGHT',
                3:  'STD_TEST',
                4:  'STD_CALSPEC',
                5:  'STD_DITHER',
                6:  'SV0_MWS_CLUSTER',
                7:  'SV0_MWS_CLUSTER_VERYBRIGHT',
                8:  'SV0_BGS',
                9:  'SV0_MWS',
                10: 'SV0_LRG',
                11: 'SV0_ELG',
                12: 'SV0_QSO',
                13: 'SV0_WD',
                14: 'SV0_QSO_Z5',
                15: 'BACKUP_BRIGHT',
                16: 'BACKUP_FAINT',
                18: 'M31_STD_BRIGHT',
                19: 'M31_H2PN',      
                20: 'M31_GC',        
                21: 'M31_QSO',       
                22: 'M31_VAR',       
                23: 'M31_BSPL',      
                24: 'M31_M31cen',    
                25: 'M31_M31out',    
                26: 'ORI_STD_BRIGHT',
                27: 'ORI_QSO',       
                28: 'ORI_ORI',       
                29: 'ORI_HA',        
                30: 'ROS_STD_BRIGHT',
                31: 'ROS_QSO',       
                38: 'ROS_ROSM17',    
                39: 'ROS_ROS1',      
                40: 'ROS_HA',        
                41: 'ROS_ROS2',      
                42: 'M33_STD_BRIGHT',
                43: 'M33_H2PN',      
                44: 'M33_GC',        
                45: 'M33_QSO',       
                46: 'M33_M33cen',    
                47: 'M33_M33out',    
                53: 'MINI_SV_LRG',       
                54: 'MINI_SV_ELG',       
                55: 'MINI_SV_QSO',       
                56: 'MINI_SV_BGS_BRIGHT',
                57: 'SV0_MWS_FAINT',     
                58: 'STD_DITHER_GAIA',   
                32: 'SKY',
                33: 'STD_FAINT',
                35: 'STD_BRIGHT',
                36: 'BAD_SKY',
                37: 'SUPP_SKY',
            }.get(b) for b in cmxbits]
        bitnames = [n for n in cmxnames if n is not None]
        if obj == 'SKY':
            bitnames.append('SKY')
        if obj == 'BAD':
            bitnames.append('BAD')
        names.append(', '.join(bitnames))
    return names

def get_target_val(t, nm, cols):
    if nm in cols:
        return int(t.get(nm))
    return 0


def desitarget_sv3_names(T, colprefix='sv3_'):
    names = []
    colors = []
    cols = T.get_columns()
    for t in T:
        desibits = []
        bgsbits = []
        mwsbits = []
        secbits = []
        desi_target = int(t.get(colprefix + 'desi_target'))
        bgs_target = get_target_val(t, colprefix + 'bgs_target', cols)
        mws_target = get_target_val(t, colprefix + 'mws_target', cols)
        sec_target = get_target_val(t, colprefix + 'scnd_target', cols)
        if 'objtype' in cols:
            obj = t.objtype
        else:
            obj = ''
        for bit in range(64):
            if (1 << bit) & desi_target:
                desibits.append(bit)
            if (1 << bit) & bgs_target:
                bgsbits.append(bit)
            if (1 << bit) & mws_target:
                mwsbits.append(bit)
            if (1 << bit) & sec_target:
                secbits.append(bit)
        # https://github.com/desihub/desitarget/blob/master/py/desitarget/sv1/data/sv1_targetmask.yaml
        desinames = [{
            0:  'LRG',
            1:  'ELG',
            2:  'QSO',
            3:  'LRG_LOWDENS',
            4:  'QSO_HIZ',
            5:  'ELG_LOP',
            6:  'ELG_HIP',
            #- Calibration targets
            32: 'SKY',
            33: 'STD_FAINT',
            34: 'STD_WD',
            35: 'STD_BRIGHT',
            36: 'BAD_SKY',
            37: 'SUPP_SKY',

            60: 'BGS_ANY',
            61: 'MWS_ANY',
            62: 'SCND_ANY',
            }.get(b) for b in desibits]
        bgsnames = [{
            0:  'BGS_FAINT',
            1:  'BGS_BRIGHT',
            2:  'BGS_WISE',
            3:  'BGS_FAINT_HIP',
            }.get(b) for b in bgsbits]
        mwsnames = [{
            0:  'MWS_BROAD',
            1:  'MWS_WD',
            2:  'MWS_NEARBY',
            #- (skip) 4: MWS_MAIN north/south splits
            6:  'MWS_BHB',
            33: 'GAIA_STD_FAINT',
            34: 'GAIA_STD_WD',
            35: 'GAIA_STD_BRIGHT',
            60: 'BACKUP_BRIGHT',
            61: 'BACKUP_FAINT',
            62: 'BACKUP_VERY_FAINT',
            }.get(b) for b in mwsbits]
        secondarynames = [{
            0:  'SCND_VETO',
            1:  'SCND_UDG',
            2:  'SCND_FIRST_MALS',
            5:  'SCND_QSO_RED',
            10: 'SCND_MWS_CLUS_GAL_DEEP',
            11: 'SCND_LOW_MASS_AGN',
            12: 'SCND_FAINT_HPM',
            15: 'SCND_LOW_Z_TIER1',
            16: 'SCND_LOW_Z_TIER2',
            17: 'SCND_LOW_Z_TIER3',
            18: 'SCND_BHB',
            19: 'SCND_SPCV',
            20: 'SCND_DC3R2_GAMA',
            25: 'SCND_PSF_OUT_BRIGHT',
            26: 'SCND_PSF_OUT_DARK',
            27: 'SCND_HPM_SOUM',
            28: 'SCND_SN_HOSTS',
            29: 'SCND_GAL_CLUS_BCG',
            30: 'SCND_GAL_CLUS_2ND',
            31: 'SCND_GAL_CLUS_SAT',
            34: 'SCND_STRONG_LENS',
            35: 'SCND_WISE_VAR_QSO',
            36: 'SCND_Z5_QSO',
            38: 'SCND_MWS_MAIN_CLUSTER_SV',
            40: 'SCND_BRIGHT_HPM',
            41: 'SCND_WD_BINARIES_BRIGHT',
            42: 'SCND_WD_BINARIES_DARK',
            43: 'SCND_PV_BRIGHT_HIGH',
            44: 'SCND_PV_BRIGHT_MEDIUM',
            45: 'SCND_PV_BRIGHT_LOW',
            46: 'SCND_PV_DARK_HIGH',
            47: 'SCND_PV_DARK_MEDIUM',
            48: 'SCND_PV_DARK_LOW',
            59: 'SCND_BRIGHT_TOO_LOP',
            60: 'SCND_BRIGHT_TOO_HIP',
            61: 'SCND_DARK_TOO_LOP',
            62: 'SCND_DARK_TOO_HIP',
            }.get(b) for b in secbits]
        bitnames = [n for n in desinames + bgsnames + mwsnames + secondarynames if n is not None]
        if obj == 'SKY':
            bitnames.append('SKY')
        if obj == 'BAD':
            bitnames.append('BAD')

        if len(bitnames) == 0:
            bitnames.append('0x%x' % desi_target)
        names.append(', '.join(bitnames))
    return names #, colors


def desitarget_sv1_names(T, colprefix='sv1_'):
    names = []
    colors = []
    cols = T.get_columns()
    for t in T:
        desibits = []
        bgsbits = []
        mwsbits = []
        secbits = []
        desi_target = int(t.get(colprefix + 'desi_target'))
        bgs_target = get_target_val(t, colprefix + 'bgs_target', cols)
        mws_target = get_target_val(t, colprefix + 'mws_target', cols)
        sec_target = get_target_val(t, colprefix + 'scnd_target', cols)
        if 'objtype' in cols:
            obj = t.objtype
        else:
            obj = ''
        for bit in range(64):
            if (1 << bit) & desi_target:
                desibits.append(bit)
            if (1 << bit) & bgs_target:
                bgsbits.append(bit)
            if (1 << bit) & mws_target:
                mwsbits.append(bit)
            if (1 << bit) & sec_target:
                secbits.append(bit)
        # https://github.com/desihub/desitarget/blob/master/py/desitarget/sv1/data/sv1_targetmask.yaml
        desinames = [{
            0:  'LRG',
            1:  'ELG',
            2:  'QSO',
            3:  'LRG_OPT',
            4:  'LRG_IR',
            5:  'LRG_SV_OPT',
            6:  'LRG_SV_IR',
            7:  'LOWZ_FILLER',
            8:  'ELG_SV_GTOT',
            9:  'ELG_SV_GFIB',
            10: 'ELG_FDR_GTOT',
            11: 'ELG_FDR_GFIB',
            12: 'QSO_COLOR_4PASS',
            13: 'QSO_RF_4PASS',
            14: 'QSO_COLOR_8PASS',
            15: 'QSO_RF_8PASS',
            16: 'QSO_HZ_F',
            17: 'QSO_Z5',
            # (skip)
            #- North vs. South selections for different sub-classes
            #- Calibration targets
            32: 'SKY',
            33: 'STD_FAINT',
            34: 'STD_WD',
            35: 'STD_BRIGHT',
            36: 'BAD_SKY',
            37: 'SUPP_SKY',

            60: 'BGS_ANY',
            61: 'MWS_ANY',
            #62: 'SCND_ANY',
            }.get(b) for b in desibits]
        bgsnames = [{
            0:  'BGS_FAINT',
            1:  'BGS_BRIGHT',
            2:  'BGS_FAINT_EXT',
            3:  'BGS_LOWQ',
            4:  'BGS_FIBMAG',
            #- (skip) BGS North vs. South selections
            40: 'BGS_KNOWN_ANY',
            }.get(b) for b in bgsbits]
        mwsnames = [{
            0:  'MWS_MAIN_BROAD',
            1:  'MWS_WD',
            2:  'MWS_NEARBY',
            #- (skip) 4: MWS_MAIN north/south splits
            6:  'MWS_BHB',
            14: 'MWS_MAIN_FAINT',
            }.get(b) for b in mwsbits]
        secondarynames = [{
            0:  'SCND_VETO',
            1:  'SCND_UDG',
            2:  'SCND_FIRST_MALS',
            3:  'SCND_WD_BINARIES',
            4:  'SCND_LBG_TOMOG',
            5:  'SCND_QSO_RED',
            6:  'SCND_M31_KNOWN',
            7:  'SCND_M31_QSO',
            8:  'SCND_M31_STAR',
            10: 'SCND_MWS_CLUS_GAL_DEEP',
            11: 'SCND_LOW_MASS_AGN',
            12: 'SCND_FAINT_HPM',
            13: 'SCND_GW190412',
            14: 'SCND_IC134191',
            15: 'SCND_PV_BRIGHT',
            16: 'SCND_PV_DARK',
            17: 'SCND_LOW_Z',
            18: 'SCND_BHB',
            19: 'SCND_SPCV',
            20: 'SCND_DC3R2_GAMA',
            21: 'SCND_UNWISE_BLUE',
            22: 'SCND_UNWISE_GREEN',
            23: 'SCND_HETDEX_MAIN',
            24: 'SCND_HEXDEX_HP',
            27: 'SCND_HPM_SOUM',
            28: 'SCND_SN_HOSTS',
            29: 'SCND_GAL_CLUS_BCG',
            30: 'SCND_GAL_CLUS_2ND',
            31: 'SCND_GAL_CLUS_SAT',
            32: 'SCND_HSC_HIZ_SNE',
            33: 'SCND_ISM_CGM_QGP',
            34: 'SCND_STRONG_LENS',
            35: 'SCND_WISE_VAR_QSO',
            36: 'SCND_MWS_CALIB',
            37: 'SCND_BACKUP_CALIB',
            38: 'SCND_MWS_MAIN_CLUSTER_SV',
            39: 'SCND_MWS_RRLYR',
            }.get(b) for b in secbits]
        bitnames = [n for n in desinames + bgsnames + mwsnames + secondarynames if n is not None]
        if obj == 'SKY':
            bitnames.append('SKY')
        if obj == 'BAD':
            bitnames.append('BAD')

        if len(bitnames) == 0:
            bitnames.append('0x%x' % desi_target)
        names.append(', '.join(bitnames))
        # cc = 'white'
        # if 'QSO' in nn:
        #     cc = 'cyan'
        # elif 'LRG' in nn:
        #     cc = 'red'
        # elif 'ELG' in nn:
        #     cc = 'gray'
        # elif 'BGS' in nn:
        #     cc = 'orange'
        # colors.append(cc)
    return names #, colors


def desitarget_color_names(T, colprefix=''):
    names = []
    colors = []
    for t in T:
        desibits = []
        bgsbits = []
        mwsbits = []
        desi_target = int(t.get(colprefix + 'desi_target'))
        bgs_target = int(t.get(colprefix + 'bgs_target'))
        mws_target = int(t.get(colprefix + 'mws_target'))
        for bit in range(64):
            if (1 << bit) & desi_target:
                desibits.append(bit)
            if (1 << bit) & bgs_target:
                bgsbits.append(bit)
            if (1 << bit) & mws_target:
                mwsbits.append(bit)
        # https://github.com/desihub/desitarget/blob/master/py/desitarget/data/targetmask.yaml
        desinames = [{
            0:  'LRG',
            1:  'ELG',
            2:  'QSO',
            8:  'LRG_NORTH',
            9:  'ELG_NORTH',
            10: 'QSO_NORTH',
            16: 'LRG_SOUTH',
            17: 'ELG_SOUTH',
            18: 'QSO_SOUTH',
            32: 'SKY',
            33: 'STD_FSTAR',
            34: 'STD_WD',
            35: 'STD_BRIGHT',
            36: 'BADSKY',
            50: 'BRIGHT_OBJECT',
            51: 'IN_BRIGHT_OBJECT',
            52: 'NEAR_BRIGHT_OBJECT',
            60: 'BGS_ANY',
            61: 'MWS_ANY',
            62: 'ANCILLARY_ANY',
        }.get(b) for b in desibits]
        bgsnames = [{
            0:  'BGS_FAINT',
            1:  'BGS_BRIGHT',
            8:  'BGS_FAINT_NORTH',
            9:  'BGS_BRIGHT_NORTH',
            16: 'BGS_FAINT_SOUTH',
            17: 'BGS_BRIGHT_SOUTH',
            40: 'BGS_KNOWN_ANY',
            41: 'BGS_KNOWN_COLLIDED',
            42: 'BGS_KNOWN_SDSS',
            43: 'BGS_KNOWN_BOSS',
        }.get(b) for b in bgsbits]
        mwsnames = [{
            0:  'MWS_MAIN',
            1:  'MWS_WD',
            2:  'MWS_NEARBY',
            16: 'MWS_MAIN_VERY_FAINT',
        }.get(b) for b in mwsbits]

        bitnames = [n for n in desinames + bgsnames + mwsnames if n is not None]
        # If any of the names in value exists, remove the key in bitnames
        # Example: if 'ELG' exists, remove 'ELG_SOUTH' and 'ELG_NORTH'
        bitnames_veto = {
            'ELG_SOUTH': ['ELG'],
            'ELG_NORTH': ['ELG'],
            'QSO_SOUTH': ['QSO'],
            'QSO_NORTH': ['QSO'],
            'LRG_NORTH': ['LRG'],
            'LRG_SOUTH': ['LRG'],
            'BGS_FAINT_NORTH': ['BGS_FAINT'],
            'BGS_FAINT_SOUTH': ['BGS_FAINT'],
            'BGS_BRIGHT_NORTH': ['BGS_BRIGHT'],
            'BGS_BRIGHT_SOUTH': ['BGS_BRIGHT'],
            'BGS_ANY': ['BGS_FAINT', 'BGS_BRIGHT', 'BGS_FAINT_NORTH',
                        'BGS_BRIGHT_NORTH', 'BGS_FAINT_SOUTH', 'BGS_BRIGHT_SOUTH',
                        'BGS_KNOWN_ANY', 'BGS_KNOWN_COLLIDED', 'BGS_KNOWN_SDSS',
                        'BGS_KNOWN_BOSS'],
            'MWS_ANY': ['MWS_MAIN', 'MWS_WD', 'MWS_NEARBY', 'MWS_MAIN_VERY_FAINT'],
        }
        for name in bitnames[:]:
            # As described in the comment above, if any of the better_names
            # exist in bitnames, remove the current name
            if any([better_name in bitnames for better_name in bitnames_veto.get(name, [])]):
                bitnames.remove(name)
        names.append(', '.join(bitnames))

        nn = ' '.join(bitnames)
        cc = 'white'
        if 'QSO' in nn:
            cc = 'cyan'
        elif 'LRG' in nn:
            cc = 'red'
        elif 'ELG' in nn:
            cc = 'gray'
        elif 'BGS' in nn:
            cc = 'orange'
        colors.append(cc)
    return names, colors

def desi_cmx_color_names(T, colprefix=None):
    names = []
    colors = []
    for bits in T.cmx_target:
        bitnames = []
        for bitval,name in [(0x1, 'STD_GAIA'),
                            (0x2, 'SV0_STD_BRIGHT'),
                            (0x4, 'STD_TEST'),
                            (0x8, 'CALSPEC'),
                            (0x100, 'SV0_BGS'),
                            (0x200, 'SV0_MWS'),]:
            if bits & bitval:
                bitnames.append(name)

        nn = ' '.join(bitnames)
        names.append(nn)

        cc = 'white'
        if 'BGS' in nn:
            cc = 'orange'
        elif 'MWS' in nn:
            cc = 'cyan'
        elif 'Gaia' in nn:
            cc = 'gray'
        else:
            cc = 'white'
        colors.append(cc)

    return names, colors

def cat_targets_drAB(req, ver, cats=None, tag='', bgs=False, sky=False, bright=False, dark=False, color_name_func=desitarget_color_names, colprefix='', name_func=None):
    '''
    color_name_func: function that selects names and colors for targets
    (eg based on targeting bit values)
    '''
    if cats is None:
        cats = []

    import json
    ralo = float(req.GET['ralo'])
    rahi = float(req.GET['rahi'])
    declo = float(req.GET['declo'])
    dechi = float(req.GET['dechi'])

    ver = int(ver)
    if not ver in catversions[tag]:
        raise RuntimeError('Invalid version %i for tag %s' % (ver, tag))

    from astrometry.util.fits import fits_table, merge_tables
    from astrometry.libkd.spherematch import tree_open, tree_search_radec
    import numpy as np

    rc,dc,rad = radecbox_to_circle(ralo, rahi, declo, dechi)

    '''
    startree -i /project/projectdirs/desi/target/catalogs/targets-dr4-0.20.0.fits -o data/targets-dr4-0.20.0.kd.fits -P -k -T
    '''
    TT = []
    for fn in cats:
        kd = tree_open(fn)
        I = tree_search_radec(kd, rc, dc, rad)
        print('Matched', len(I), 'from', fn)
        if len(I) == 0:
            continue
        T = fits_table(fn, rows=I)
        TT.append(T)
    if len(TT) == 0:
        return HttpResponse(json.dumps(dict(rd=[], name=[])),
                            content_type='application/json')
    T = merge_tables(TT, columns='fillzero')

    if bgs:
        bgs_target = T.get(colprefix + 'bgs_target')
        T.cut(bgs_target > 0)

    if bright:
        bgs_target = T.get(colprefix + 'bgs_target')
        mws_target = T.get(colprefix + 'mws_target')
        T.cut(np.logical_or(bgs_target > 0, mws_target > 0))

    if dark:
        desi_target = T.get(colprefix + 'desi_target')
        T.cut(T.desi_target > 0)

    names = None
    colors = None
    if color_name_func is not None:
        names,colors = color_name_func(T, colprefix=colprefix)
    if name_func is not None:
        names = name_func(T, colprefix=colprefix)

    rtn = dict(rd=[(t.ra, t.dec) for t in T],
               targetid=[str(t) for t in T.targetid])

    fluxes = None
    nobs = None
    if sky:
        fluxes = [dict(g=float(g), r=float(r), z=float(z))
                  for (g,r,z) in zip(T.apflux_g[:,0], T.apflux_r[:,0], T.apflux_z[:,0])]
    else:
        if 'flux_g' in T.get_columns():
            if 'flux_w1' in T.get_columns():
                fluxes = [dict(g=float(g), r=float(r), z=float(z),
                               W1=float(W1), W2=float(W2))
                          for (g,r,z,W1,W2)
                          in zip(T.flux_g, T.flux_r, T.flux_z, T.flux_w1, T.flux_w2)]
            else:
                fluxes = [dict(g=float(g), r=float(r), z=float(z))
                          for (g,r,z)
                          in zip(T.flux_g, T.flux_r, T.flux_z)]
        if 'nobs_g' in T.get_columns():
            nobs=[dict(g=int(g), r=int(r), z=int(z)) for g,r,z
                  in zip(T.nobs_g, T.nobs_r, T.nobs_z)],

    if names is not None:
        rtn.update(name=names)
    if colors is not None:
        rtn.update(color=colors)
    if nobs is not None:
        rtn.update(nobs=nobs)
    if fluxes is not None:
        rtn.update(fluxes=fluxes)
    # Convert targetid to string to prevent rounding errors
    rtn['targetid'] = [str(s) for s in rtn['targetid']]
    
    return HttpResponse(json.dumps(rtn), content_type='application/json')

def cat_sga_parent(req, ver):
    fn = os.path.join(settings.DATA_DIR, 'sga', 'SGA-parent-v3.0.kd.fits')
    return _cat_sga(req, ver, fn=fn, tag='sga')

def cat_sga_ellipse(req, ver):
    # T = fits_table('cosmo/webapp/viewer-dev/data/sga/SGA-ellipse-v3.2.kd.fits')
    # T.cut((T.sga_id >= 0) * (T.preburned))
    # cols = ['ra','dec','diam', 'galaxy', 'pgc', 'morphtype', 'ba', 'pa', 'z_leda', 'group_name']
    # T.writeto('sga-cut.fits', columns=cols)
    # startree -i ~/sga-cut.fits -o data/sga/SGA-ellipse-v3.2-cut.kd.fits -PTk
    #fn = os.path.join(settings.DATA_DIR, 'sga', 'SGA-ellipse-v3.2.kd.fits')
    #fn = os.path.join(settings.DATA_DIR, 'sga', 'SGA-ellipse-v3.2-cut.kd.fits')
    fn = os.path.join(settings.DATA_DIR, 'sga', 'SGA-2020.kd.fits')
    print('Reading', fn)
    return _cat_sga(req, ver, ellipse=True, fn=fn, tag='sga')

def _cat_sga(req, ver, ellipse=False, fn=None, tag='sga'):
    import json
    import numpy as np
    # The SGA catalog includes radii for the galaxies, and we want galaxies
    # that touch our RA,Dec box, so can't use the standard method...
    #T = cat_kd(req, ver, tag, fn)

    ralo = float(req.GET['ralo'])
    rahi = float(req.GET['rahi'])
    declo = float(req.GET['declo'])
    dechi = float(req.GET['dechi'])
    ver = int(ver)
    if not ver in catversions[tag]:
        raise RuntimeError('Invalid version %i for tag %s' % (ver, tag))

    T = query_sga_radecbox(fn, ralo, rahi, declo, dechi)
    if T is None:
        return HttpResponse(json.dumps(dict(rd=[], name=[], radiusArcsec=[], abRatio=[],
                                            posAngle=[], pgc=[], type=[], redshift=[])),
                            content_type='application/json')
    T.cut(np.argsort(-T.radius_arcsec))

    rd = list((float(r),float(d)) for r,d in zip(T.ra, T.dec))
    names = [t.strip() for t in T.galaxy]
    pgc = [int(p) for p in T.pgc]
    typ = [t.strip() if t != 'nan' else '' for t in T.get('morphtype')]

    radius = [float(r) for r in T.radius_arcsec.astype(np.float32)]
    ab = [float(f) for f in T.ba.astype(np.float32)]

    pax = T.pa.copy().astype(np.float32)
    pax[np.logical_not(np.isfinite(pax))] = 0.
    pax[pax < 0] += 180.
    pax[pax >= 180.] -= 180.

    pa = [float(90.-f) for f in pax]
    pa_disp = [float(f) for f in pax]
    if ellipse:
        color = ['#377eb8']*len(T)
        #'#ff3333'
    else:
        color = ['#e41a1c']*len(T)
        #'#3388ff'
    z = [float(z) if np.isfinite(z) else -1. for z in T.z_leda.astype(np.float32)]
    groupnames = [t.strip() for t in T.group_name]

    return HttpResponse(json.dumps(dict(rd=rd, name=names, radiusArcsec=radius,
                                        groupname=groupnames,
                                        abRatio=ab, posAngle=pa, pgc=pgc, type=typ,
                                        redshift=z, color=color, posAngleDisplay=pa_disp)),
                        content_type='application/json')

def query_sga_radecbox(fn, ralo, rahi, declo, dechi):
    ra,dec,radius = radecbox_to_circle(ralo, rahi, declo, dechi)
    # max radius for SGA entries?!
    sga_radius = 2.0
    T = cat_query_radec(fn, ra, dec, radius + sga_radius)
    if T is None:
        return None
    wcs = radecbox_to_wcs(ralo, rahi, declo, dechi)
    H,W = wcs.shape
    # cut to sga entries possibly touching wcs box
    cols = T.get_columns()
    if 'diam' in cols:
        T.radius_arcsec = T.diam / 2. * 60.
    else:
        T.radius_arcsec = T.d26 / 2. * 60.
    radius_pix = T.radius_arcsec / wcs.pixel_scale()
    ok,xx,yy = wcs.radec2pixelxy(T.ra, T.dec)
    T.cut((xx > -radius_pix) * (xx < W+radius_pix) *
          (yy > -radius_pix) * (yy < H+radius_pix))
    if len(T) == 0:
        return None
    return T

def cat_manga(req, ver):
    import json
    import numpy as np
    # DR16
    # startree -i data/manga/drpall-v2_4_3.fits -o data/manga/drpall-v2_4_3.kd.fits \
    #     -P -T -k -R ifura -D ifudec
    fn = os.path.join(settings.DATA_DIR, 'manga', 'drpall-v2_4_3.kd.fits')
    tag = 'manga'
    T = cat_kd(req, ver, tag, fn, racol='ifura', deccol='ifudec')
    if T is not None and len(T)>0:
        T.cut(T.ifudesignsize > 0)
        if len(T) == 0:
            T = None
    if T is None:
        return HttpResponse(json.dumps(dict(rd=[], name=[], mjd=[], fiber=[],plate=[])),
                            content_type='application/json')
    # plate = req.GET.get('plate', None)
    # if plate is not None:
    #     plate = int(plate, 10)
    #     T.cut(T.plate == plate)

    rd = list((float(r),float(d)) for r,d in zip(T.ifura, T.ifudec))
    #names = [t.strip() for t in T.label]
    names = [t.strip() for t in T.nsa_iauname]
    #mjd   = [int(x) for x in T.mjd]
    #fiber = [int(x) for x in T.fiberid]
    plate = [int(x) for x in T.plate]
    ifudsgn = [int(x) for x in T.ifudsgn]
    z = [float(z) for z in T.z]
    ifusize = [int(x) for x in T.ifudesignsize]

    hexes = []
    fibers = []
    
    dradec = manga_ifu_offsets()
    for sz,(r,d) in zip(ifusize, rd):
        radius = { 127: 6,
                   91: 5,
                   61: 4,
                   37: 3,
                   19: 2 }
        rr = radius[sz]
        hexx = []
        fibs = []
        cosdec = np.cos(np.deg2rad(d))
        # hexagon
        for i in range(7):
            j = (i % 6) + 1
            hexx.append((float(r + (rr + 0.5) * dradec[j][0] / 3600. / cosdec),
                         float(d + (rr + 0.5) * dradec[j][1] / 3600. )))

        for dr,dd in dradec[:sz]:
            fibs.append((float(r + dr / 3600. / cosdec),
                         float(d + dd / 3600.)))
        hexes.append(hexx)
        fibers.append(fibs)

    #ifudsgn (= plate-ifu)
    #plateifu
    #mangaid
    #nsa_iauname
    #ifudesignsize
    #z
    return HttpResponse(json.dumps(dict(rd=rd, name=names, plate=plate, ifudsgn=ifudsgn, z=z,
                                        hexes=hexes, fibers=fibers)),
                        content_type='application/json')

def manga_ifu_offsets():
    return [(0.0, 0.0), (-1.25, -2.16506), (1.25, -2.16506), (2.5, 0.0), (1.25, 2.16506), (-1.25, 2.16506), (-2.5, 0.0), (-2.5, -4.33013), (0.0, -4.33013), (2.5, -4.33013), (3.75, -2.16506), (5.0, 0.0), (3.75, 2.16506), (2.5, 4.33013), (0.0, 4.33013), (-2.5, 4.33013), (-3.75, 2.16506), (-5.0, 0.0), (-3.75, -2.16506), (-3.75, -6.49519), (-1.25, -6.49519), (1.25, -6.49519), (3.75, -6.49519), (5.0, -4.33013), (6.25, -2.16506), (7.5, 0.0), (6.25, 2.16506), (5.0, 4.33013), (3.75, 6.49519), (1.25, 6.49519), (-1.25, 6.49519), (-3.75, 6.49519), (-5.0, 4.33013), (-6.25, 2.16506), (-7.5, 0.0), (-6.25, -2.16506), (-5.0, -4.33013), (-5.0, -8.66025), (-2.5, -8.66025), (0.0, -8.66025), (2.5, -8.66025), (5.0, -8.66025), (6.25, -6.49519), (7.5, -4.33013), (8.75, -2.16506), (10.0, 0.0), (8.75, 2.16506), (7.5, 4.33013), (6.25, 6.49519), (5.0, 8.66025), (2.5, 8.66025), (0.0, 8.66025), (-2.5, 8.66025), (-5.0, 8.66025), (-6.25, 6.49519), (-7.5, 4.33013), (-8.75, 2.16506), (-10.0, 0.0), (-8.75, -2.16506), (-7.5, -4.33013), (-6.25, -6.49519), (-6.25, -10.8253), (-3.75, -10.8253), (-1.25, -10.8253), (1.25, -10.8253), (3.75, -10.8253), (6.25, -10.8253), (7.5, -8.66025), (8.75, -6.49519), (10.0, -4.33013), (11.25, -2.16506), (12.5, 0.0), (11.25, 2.16506), (10.0, 4.33013), (8.75, 6.49519), (7.5, 8.66025), (6.25, 10.8253), (3.75, 10.8253), (1.25, 10.8253), (-1.25, 10.8253), (-3.75, 10.8253), (-6.25, 10.8253), (-7.5, 8.66025), (-8.75, 6.49519), (-10.0, 4.33013), (-11.25, 2.16506), (-12.5, 0.0), (-11.25, -2.16506), (-10.0, -4.33013), (-8.75, -6.49519), (-7.5, -8.66025), (-7.5, -12.9904), (-5.0, -12.9904), (-2.5, -12.9904), (0.0, -12.9904), (2.5, -12.9904), (5.0, -12.9904), (7.5, -12.9904), (8.75, -10.8253), (10.0, -8.66025), (11.25, -6.49519), (12.5, -4.33013), (13.75, -2.16506), (15.0, 0.0), (13.75, 2.16506), (12.5, 4.33013), (11.25, 6.49519), (10.0, 8.66025), (8.75, 10.8253), (7.5, 12.9904), (5.0, 12.9904), (2.5, 12.9904), (0.0, 12.9904), (-2.5, 12.9904), (-5.0, 12.9904), (-7.5, 12.9904), (-8.75, 10.8253), (-10.0, 8.66025), (-11.25, 6.49519), (-12.5, 4.33013), (-13.75, 2.16506), (-15.0, 0.0), (-13.75, -2.16506), (-12.5, -4.33013), (-11.25, -6.49519), (-10.0, -8.66025), (-8.75, -10.8253)]

def cat_spec(req, ver):
    import json
    fn = os.path.join(settings.DATA_DIR, 'sdss', 'specObj-dr16-trimmed.kd.fits')
    tag = 'spec'
    T = cat_kd(req, ver, tag, fn)
    if T is None:
        return HttpResponse(json.dumps(dict(rd=[], name=[], mjd=[], fiber=[],
                                            plate=[], zwarning=[])),
                            content_type='application/json')
    plate = req.GET.get('plate', None)
    if plate is not None:
        plate = int(plate, 10)
        T.cut(T.plate == plate)

    rd = list((float(r),float(d)) for r,d in zip(T.ra, T.dec))
    names = [t.strip() for t in T.label]
    # HACK
    #names = [t.split()[0] for t in names]
    mjd   = [int(x) for x in T.mjd]
    fiber = [int(x) for x in T.fiberid]
    plate = [int(x) for x in T.plate]
    zwarning = [int(x) for x in T.zwarning]
    return HttpResponse(json.dumps(dict(rd=rd, name=names, mjd=mjd, fiber=fiber, plate=plate,
                                        zwarning=zwarning)),
                        content_type='application/json')

def cat_masks_dr9(req, ver):
    import json
    import os
    import numpy as np
    from legacypipe.reference import get_reference_sources
    from legacypipe.survey import LegacySurveyData
    ralo = float(req.GET['ralo'])
    rahi = float(req.GET['rahi'])
    declo = float(req.GET['declo'])
    dechi = float(req.GET['dechi'])
    wcs = radecbox_to_wcs(ralo, rahi, declo, dechi)
    os.environ['TYCHO2_KD_DIR'] = settings.DATA_DIR
    #os.environ['LARGEGALAXIES_CAT'] = os.path.join(settings.DATA_DIR, 'sga', 'SGA-v7.0.kd.fits')
    os.environ['LARGEGALAXIES_CAT'] = os.path.join(settings.DATA_DIR, 'sga', 'SGA-ellipse-v3.0.kd.fits')
    os.environ['GAIA_CAT_DIR'] = os.path.join(settings.DATA_DIR, 'gaia-dr2')
    os.environ['GAIA_CAT_VER'] = '2'
    os.environ['GAIA_CAT_SCHEME'] = 'ring'
    os.environ['GAIA_CAT_PREFIX'] = 'chunk'

    survey = LegacySurveyData(survey_dir=os.getcwd())
    pixscale = wcs.pixel_scale()
    T,_ = get_reference_sources(survey, wcs, pixscale, None)
    T.about()
    
    if T is None:
        return HttpResponse(json.dumps(dict(rd=[], name=[], radiusArcsec=[])),
                            content_type='application/json')

    from functools import reduce
    #T.cut(reduce(np.logical_or, [T.isbright, T.iscluster, T.islargegalaxy, T.ismedium]))
    T.cut(reduce(np.logical_or, [T.isbright, T.iscluster, T.islargegalaxy, T.ismedium, T.isgaia]))
    # sort by radius to improve the layering
    T.cut(np.argsort(-T.radius))

    rd = []
    radius = []
    color = []
    ab = []
    PA = []
    PA_disp = []
    names = []

    for medium, bright,cluster,gal,dup,ptsrc,aen,ra,dec,rad,mag,zguess,freeze,refid,ba,pa in zip(
            T.ismedium, T.isbright, T.iscluster, T.islargegalaxy, T.donotfit, T.pointsource,
            T.astrometric_excess_noise, T.ra, T.dec, T.radius,
            T.mag, T.zguess, T.freezeparams, T.ref_id, T.ba, T.pa):
        rd.append((float(ra), float(dec)))
        radius.append(3600. * float(rad))

        if dup:
            color.append('#aaaaaa')
        elif cluster:
            color.append('yellow')
        #elif bright:
        #    color.append('orange')
        elif gal:
            color.append('#33ff88')
        elif medium and ptsrc:
            color.append('#3388ff')
        elif medium:
            color.append('#8833ff')
        else:
            color.append('#888888')

        if dup:
            names.append('DUP')
        elif cluster:
            names.append('CLUSTER')
        elif gal:
            # freezeparams, ref_id
            name = 'SGA %i' % refid
            # We're not pointing to the 'model' version
            #if freeze:
            #    name += ' (frozen)'
            names.append(name)
        elif medium:
            if bright:
                name = 'BRIGHT mag=%.2f' % mag
            else:
                name = 'MEDIUM G=%.2f' % mag
            if np.isfinite(zguess) * (zguess+1 < mag):
                zg = ', zguess=%.2f' % (zguess)
                name += zg
            if ptsrc:
                name += ', ptsrc'
            name += ', aen=%.2g' % aen
            oname = name
            if bright:
                name = 'MED/'+name
            names.append(name)
        else:
            if ptsrc:
                names.append('ptsrc')
            else:
                names.append('')

        if ba == 0.:
            ba = 1.
        ab.append(float(ba))

        if not np.isfinite(pa):
            pa = 0.
        if pa < 0:
            pa += 180.
        if pa >= 180.:
            pa -= 180.
        PA.append(float(90.-pa))
        PA_disp.append(float(pa))

        if bright:
            # Double entry at half radius!
            rd.append((float(ra), float(dec)))
            radius.append(0.5 * 3600. * float(rad))
            color.append('orange')
            names.append(oname)
            ab.append(float(ba))
            PA.append(float(90.-pa))
            PA_disp.append(float(pa))

    return HttpResponse(json.dumps(dict(rd=rd, name=names, radiusArcsec=radius, color=color,
                                        abRatio=ab, posAngle=PA, posAngleDisplay=PA_disp)),
                        content_type='application/json')

def cat_gaia_mask(req, ver):
    import json
    '''
    fitscopy data/gaia-mask.fits"[col ra;dec;ref_cat;ref_id;radius;phot_g_mean_mag;pointsource;ismedium;isbright]" data/gaia-mask-sub.fits
    startree -i data/gaia-mask-sub.fits -o data/gaia-mask.kd.fits -P -T -k
    '''
    fn = os.path.join(settings.DATA_DIR, 'gaia-mask.kd.fits')
    tag = 'masks-dr8'
    T = cat_kd(req, ver, tag, fn)
    if T is None:
        return HttpResponse(json.dumps(dict(rd=[], name=[], radiusArcsec=[])),
                            content_type='application/json')
    rd = list((float(r),float(d)) for r,d in zip(T.ra, T.dec))
    names = ['G=%.2f' % g for g in T.phot_g_mean_mag]
    radius = [3600. * float(r) for r in T.radius]
    color = ['orange' if bright else '#3388ff' for bright in T.isbright]
    #G = [float(r) for r in T.phot_g_mean_mag]
    return HttpResponse(json.dumps(dict(rd=rd, name=names, radiusArcsec=radius, color=color)),
                        content_type='application/json')

def cat_hsc_dr2_cosmos(req, ver):
    import json
    import numpy as np
    fn = os.path.join(settings.DATA_DIR, 'hsc-dr2', 'cosmos-cat.kd.fits')
    T = cat_kd(req, ver, 'hsc-dr2-cosmos', fn)
    if T is None:
        return HttpResponse(json.dumps(dict(rd=[], name=[], color=[])),
                            content_type='application/json')

    if len(T) > 5000:
        T = T[:5000]

    rd = list((float(r),float(d)) for r,d in zip(T.ra, T.dec))
    names = []
    psf_g = 30. -2.5*np.log10(T.g_psfflux_flux)
    psf_r = 30. -2.5*np.log10(T.r_psfflux_flux)
    psf_i = 30. -2.5*np.log10(T.i_psfflux_flux)
    psf_z = 30. -2.5*np.log10(T.z_psfflux_flux)
    cm_g = 30. -2.5*np.log10(T.g_cmodel_flux)
    cm_r = 30. -2.5*np.log10(T.r_cmodel_flux)
    cm_i = 30. -2.5*np.log10(T.i_cmodel_flux)
    cm_z = 30. -2.5*np.log10(T.z_cmodel_flux)
    # in the cosmos region it only takes values 0.0 and 1.0
    e = (T.i_extendedness_value > 0.5)
    color = ['orange' if ext else '#3388ff' for ext in e]
    g = np.where(e, cm_g, psf_g)
    r = np.where(e, cm_r, psf_r)
    i = np.where(e, cm_i, psf_i)
    z = np.where(e, cm_z, psf_z)
    for ext,gg,rr,ii,zz in zip(e,g,r,i,z):
        names.append('%s g=%.2f, r=%.2f, i=%.2f, z=%.2f' % ('Galaxy' if ext else 'Star', gg, rr, ii, zz))
    return HttpResponse(json.dumps(dict(rd=rd, name=names, color=color)),
                        content_type='application/json')

def cat_kd(req, ver, tag, fn, racol=None, deccol=None):
    ralo = float(req.GET['ralo'])
    rahi = float(req.GET['rahi'])
    declo = float(req.GET['declo'])
    dechi = float(req.GET['dechi'])
    ver = int(ver)
    if not ver in catversions[tag]:
        raise RuntimeError('Invalid version %i for tag %s' % (ver, tag))

    ra,dec,radius = radecbox_to_circle(ralo, rahi, declo, dechi)
    T = cat_query_radec(fn, ra, dec, radius)
    if T is None:
        debug('No objects in query')
        return None
    #debug(len(T), 'spectra')
    if racol is not None:
        T.ra = T.get(racol)
    if deccol is not None:
        T.dec = T.get(deccol)
    if ralo > rahi:
        import numpy as np
        # RA wrap
        T.cut(np.logical_or(T.ra > ralo, T.ra < rahi) * (T.dec > declo) * (T.dec < dechi))
    else:
        T.cut((T.ra > ralo) * (T.ra < rahi) * (T.dec > declo) * (T.dec < dechi))
    #debug(len(T), 'in cut')
    return T

def radecbox_to_wcs(ralo, rahi, declo, dechi):
    from astrometry.util.starutil_numpy import radectoxyz, xyztoradec, degrees_between
    from astrometry.util.util import Tan
    import numpy as np
    rc,dc,radius = radecbox_to_circle(ralo, rahi, declo, dechi)
    wd = degrees_between(ralo, dc, rahi, dc)
    hd = degrees_between(rc, declo, rc, dechi)
    W = 1000.
    pixsc = wd / W
    H = hd / pixsc
    wcs = Tan(rc, dc, (W+1.)/2., (H+1.)/2., -pixsc, 0., 0., pixsc,
              float(W), float(H))
    ok,x,y = wcs.radec2pixelxy(ralo, declo)
    ok,x,y = wcs.radec2pixelxy(ralo, dechi)
    ok,x,y = wcs.radec2pixelxy(rahi, declo)
    ok,x,y = wcs.radec2pixelxy(rahi, dechi)
    return wcs

def radecbox_to_circle(ralo, rahi, declo, dechi):
    from astrometry.util.starutil_numpy import radectoxyz, xyztoradec, degrees_between
    import numpy as np
    xyz1 = radectoxyz(ralo, declo)
    xyz2 = radectoxyz(rahi, dechi)
    xyz = (xyz1 + xyz2)/2.
    xyz /= np.sqrt(np.sum(xyz**2))
    rc,dc = xyztoradec(xyz)
    rc = rc[0]
    dc = dc[0]
    rad = max(degrees_between(rc, dc, ralo, declo),
              degrees_between(rc, dc, rahi, dechi))
    return rc, dc, rad
    
def cat_query_radec(kdfn, ra, dec, radius):
    from astrometry.libkd.spherematch import tree_open, tree_search_radec
    from astrometry.util.fits import fits_table
    kd = tree_open(kdfn)
    I = tree_search_radec(kd, ra, dec, radius)
    #print('Matched', len(I), 'from', fn)
    if len(I) == 0:
        return None
    T = fits_table(kdfn, rows=I)
    return T

def cat_spec_deep2(req, ver):
    import json
    tag = 'spec-deep2'
    ralo = float(req.GET['ralo'])
    rahi = float(req.GET['rahi'])
    declo = float(req.GET['declo'])
    dechi = float(req.GET['dechi'])
    ver = int(ver)
    if not ver in catversions[tag]:
        raise RuntimeError('Invalid version %i for tag %s' % (ver, tag))

    from astrometry.util.fits import fits_table, merge_tables
    import numpy as np

    TT = []
    T = fits_table(os.path.join(settings.DATA_DIR, 'deep2-zcat-dr4-uniq.fits'))
    debug(len(T), 'spectra')
    if ralo > rahi:
        # RA wrap
        T.cut(np.logical_or(T.ra > ralo, T.ra < rahi) * (T.dec > declo) * (T.dec < dechi))
    else:
        T.cut((T.ra > ralo) * (T.ra < rahi) * (T.dec > declo) * (T.dec < dechi))
    debug(len(T), 'in cut')

    rd = list((float(r),float(d)) for r,d in zip(T.ra, T.dec))
    names = []

    classes = T.get('class')
    subclasses = T.subclass
    zbests = T.zbest
    zq = T.zquality
    for i in range(len(T)):
        clazz = classes[i]
        clazz = clazz[0] + clazz[1:].lower()

        #if zq[i] >= 3:
        nm = clazz
        sc = subclasses[i].strip()
        if sc != 'NONE':
            nm += ' ' + sc
        if not (zq[i] == -1 and clazz.strip() == 'Star'):
            nm += ' z=%.2f, q=%i' % (zbests[i], zq[i])
        names.append(nm)

    return HttpResponse(json.dumps(dict(rd=rd, name=names)),
                        content_type='application/json')

def cat_user(req, ver):
    from astrometry.util.fits import fits_table
    import json
    import re

    cat = str(req.GET.get('cat'))
    if not re.match('\w?', cat):
        print('Catalog "%s" did not match regex' % cat)
        return

    haverd = False
    havei = False
    
    if ('ralo'  in req.GET and 'rahi'  in req.GET and
        'declo' in req.GET and 'dechi' in req.GET):
        ralo = float(req.GET['ralo'])
        rahi = float(req.GET['rahi'])
        declo = float(req.GET['declo'])
        dechi = float(req.GET['dechi'])
        haverd = True
    elif ('start' in req.GET and 'N' in req.GET):
        start = int(req.GET['start'])
        N = int(req.GET['N'])
        havei = True
    else:
        return HttpResponse('need {ra,dec}{lo,hi} or start,N')
    
    fn = os.path.join(settings.USER_QUERY_DIR, cat+'.fits')
    if not os.path.exists(fn):
        print('Does not exist:', fn)
        return
    cat = fits_table(fn)
    if haverd:
        if ralo > rahi:
            import numpy as np
            # RA wrap
            cat.cut(np.logical_or(cat.ra > ralo, cat.ra < rahi) *
                    (cat.dec > declo) * (cat.dec < dechi))
        else:
            cat.cut((cat.ra > ralo) * (cat.ra < rahi) *
            (cat.dec > declo) * (cat.dec < dechi))
        print(len(cat), 'user catalog sources after RA,Dec cut')
    elif havei:
        cat = cat[start:start+N]

    rd = list(zip(cat.ra.astype(float), cat.dec.astype(float)))

    D = dict(rd=rd)
    cols = cat.columns()
    if 'name' in cols:
        D.update(names=cat.name.tolist())
    if 'type' in cols:
        try:
            v = list([t[0] for t in cat.get('type')])
            json.dumps(v)
            D.update(sourcetype=v)
        except:
            print('failed to convert column "type".  Traceback:')
            import traceback
            traceback.print_exc()
    if 'g' in cols and 'r' in cols and 'z' in cols:
        D.update(fluxes=[dict(g=float(g), r=float(r), z=float(z))
                         for g,r,z in zip(10.**((cat.g - 22.5)/-2.5),
                                          10.**((cat.r - 22.5)/-2.5),
                                          10.**((cat.z - 22.5)/-2.5))])
    else:
        fluxbands = []
        fluxes = []
        for band in 'griz':
            if 'flux_'+band in cols:
                fluxbands.append(band)
                fluxes.append(cat.get('flux_'+band))
        if len(fluxbands) > 0:
            allfluxes = []
            for srcfluxes in zip(*fluxes):
                #print('srcfluxes:', srcfluxes)
                #print('zip:', dict(zip(fluxbands, srcfluxes)))
                allfluxes.append(dict(zip(fluxbands, [float(f) for f in srcfluxes])))
            D.update(fluxes = allfluxes)

    if 'gnobs' in cols and 'rnobs' in cols and 'znobs' in cols:
        D.update(nobs=[dict(g=int(g), r=int(r), z=int(z))
                       for g,r,z in zip(cat.gnobs, cat.rnobs, cat.znobs)])
    if 'objid' in cols:
        D.update(objids=[int(x) for x in cat.objid])
    if 'brickname' in cols:
        D.update(bricknames=cat.brickname.tolist())
    if 'radius' in cols:
        D.update(radius=list([float(r) for r in cat.radius]))
    if 'color' in cols:
        D.update(color=list([c.strip() for c in cat.color]))
    if 'abratio' in cols:
        D.update(abratio=list([float(r) for r in cat.abratio]))
    if 'posangle' in cols:
        D.update(posangle=list([float(r) for r in cat.posangle]))

    #for k,v in D.items():
    #    print('Cat', k, v)

    return HttpResponse(json.dumps(D).replace('NaN','null'),
                        content_type='application/json')

def desi_fiberassign_filename(tileid):
    tilestr = '%06i' % tileid
    fn = os.path.join(settings.DATA_DIR, 'desi-tiles',
                      tilestr[:3], 'fiberassign-%s.fits.gz'%tilestr)
    return fn

def cat_desi_all_tiles(req, subset, ver):
    import numpy as np
    import json
    ralo = float(req.GET['ralo'])
    rahi = float(req.GET['rahi'])
    declo = float(req.GET['declo'])
    dechi = float(req.GET['dechi'])

    tag = 'desi-all-tiles'
    ver = int(ver)
    if not ver in catversions[tag]:
        raise RuntimeError('Invalid version %i for tag %s' % (ver, tag))

    from astropy.table import Table
    t = Table.read('data/tiles-main.ecsv')
    from astrometry.util.fits import fits_table
    T = fits_table()
    T.tileid = t['TILEID'].data
    T.ra = t['RA'].data
    T.dec = t['DEC'].data
    T.in_desi = t['IN_DESI'].data
    T.program = t['PROGRAM'].data

    T.cut(T.in_desi)
    margin = 0.8
    # not exactly right...
    cosdec = np.cos(np.deg2rad((declo+dechi)/2.))
    r0 = ralo - margin/cosdec
    r1 = rahi + margin/cosdec
    d0 = declo - margin
    d1 = dechi + margin

    T.cut((T.dec > d0) * (T.dec < d1))
    if ralo > rahi:
        # RA wrap
        T.cut(np.logical_or(T.ra > r0, T.ra < r1))
    else:
        T.cut((T.ra > r0) * (T.ra < r1))

    if subset == 'dark':
        T.cut(T.program == 'DARK')
    elif subset == 'bright':
        T.cut(T.program == 'BRIGHT')

    # rd = list((float(r),float(d)) for r,d in zip(T.ra, T.dec))
    # tid = list(int(t) for t in T.tileid)
    # rtn = dict(rd=rd, tileid=list(tid), program=list(T.program))
    # return HttpResponse(json.dumps(rtn), content_type='application/json')
    objs = []
    for r,d,prog,tid in zip(T.ra, T.dec, T.program, T.tileid):
        objs.append(dict(name='Tile %i (%s)' % (tid, prog),
                         ra=r,
                         dec=d,
                         radius=1.6))
    return HttpResponse(json.dumps({'objs':objs}), content_type='application/json')

def cat_desi_tile(req, ver):
    from astrometry.util.fits import fits_table
    import json
    import re

    tile = int(req.GET.get('tile','0'), 10)
    if tile == 0:
        return 'bad tile'
    haverd = False
    if ('ralo'  in req.GET and 'rahi'  in req.GET and
        'declo' in req.GET and 'dechi' in req.GET):
        ralo = float(req.GET['ralo'])
        rahi = float(req.GET['rahi'])
        declo = float(req.GET['declo'])
        dechi = float(req.GET['dechi'])
        haverd = True

    fn = desi_fiberassign_filename(tile)
    if not os.path.exists(fn):
        print('Does not exist:', fn)
        return
    print('Reading', fn)
    cat = fits_table(fn)
    cat.ra  = cat.target_ra
    cat.dec = cat.target_dec
    
    if haverd:
        if ralo > rahi:
            import numpy as np
            # RA wrap
            cat.cut(np.logical_or(cat.ra > ralo, cat.ra < rahi) *
                    (cat.dec > declo) * (cat.dec < dechi))
        else:
            cat.cut((cat.ra > ralo) * (cat.ra < rahi) *
            (cat.dec > declo) * (cat.dec < dechi))
        print(len(cat), 'DESI tile sources after RA,Dec cut')

    rd = list(zip(cat.ra.astype(float), cat.dec.astype(float)))
    D = dict(rd=rd)

    cols = cat.columns()
    print('Columns:', cols)
    if 'sv3_desi_target' in cols:
        bitnames = desitarget_sv3_names(cat)
        D.update(bits=bitnames)
    elif 'sv1_desi_target' in cols:
        bitnames = desitarget_sv1_names(cat)
        D.update(bits=bitnames)
    elif 'cmx_target' in cols:
        bitnames = desitarget_cmx_names(cat)
        D.update(bits=bitnames)
    # Main targets
    elif 'desi_target' in cols:
        from desitarget.targets import desi_mask, bgs_mask, mws_mask, scnd_mask
        bitnames = []
        for desi,bgs,mws,scnd in zip(cat.desi_target, cat.bgs_target, cat.mws_target, cat.scnd_target):
            sec = scnd_mask.names(scnd)
            sec = ['sec:'+k for k in sec]
            names = desi_mask.names(desi) + bgs_mask.names(bgs) + mws_mask.names(mws) + sec
            for kill in ['LRG_SOUTH', 'ELG_SOUTH', 'QSO_SOUTH', 'ELG_VLO_SOUTH', 'SCND_ANY',
                         'MWS_MAIN_BLUE_SOUTH', ]:
                if kill in names:
                    names.remove(kill)
            bitnames.append(', '.join(names))
        D.update(bits=bitnames)
    if 'targetid' in cols:
        D.update(targetid=['%i'%i for i in cat.targetid])
    if 'fiber' in cols:
        D.update(fiberid=[int(i) for i in cat.fiber])

    return HttpResponse(json.dumps(D).replace('NaN','null'),
                        content_type='application/json')

def cat_bright(req, ver):
    return cat(req, ver, 'bright',
               os.path.join(settings.DATA_DIR, 'bright.fits'))

def cat_tycho2(req, ver):
    #return cat(req, ver, 'tycho2',
    #           os.path.join(settings.DATA_DIR, 'tycho2.fits'))
    import json
    T = cat_kd(req, ver, 'tycho2', os.path.join(settings.DATA_DIR, 'tycho2-sub.kd.fits'))
    if T is None:
        rtn = dict(rd=[], name=[])
    else:
        rd = list((float(r),float(d)) for r,d in zip(T.ra, T.dec))
        rtn = dict(rd=rd)
        if 'name' in T.columns():
            names = [t.strip() for t in T.name]
            rtn['name'] = names
            for i,name in enumerate(names):
                try:
                    # Parse name as "Tycho-2 ###-###-###", then form Simbad link from the parsed
                    # numbers.
                    words = name.split()
                    nums = words[1].split('-')
                    tyc1 = int(nums[0])
                    tyc2 = int(nums[1])
                    tyc3 = int(nums[2])
                    url = 'http://simbad.cds.unistra.fr/simbad/sim-id?Ident=TYC++%i+%i+%i&NbIdent=1' % (tyc1, tyc2, tyc3)
                    names[i] = '<a href="%s">%s</a>' % (url, name)
                except:
                    pass
    return HttpResponse(json.dumps(rtn), content_type='application/json')

def cat_ngc(req, ver):
    return cat(req, ver, 'ngc',
               os.path.join(settings.DATA_DIR, 'ngcic.fits'))

def cat_GCs_PNe(req, ver):
    from astrometry.util.fits import fits_table
    import numpy as np
    T = fits_table(os.path.join(settings.DATA_DIR,'NGC-star-clusters.fits'))
    #T.alt_name = np.array(['' if n.startswith('N/A') else n.strip() for n in T.commonnames])
    T.posAngle = T.pa
    T.abRatio = T.ba
    return cat(req, ver, 'GCs-PNe', None, T=T)

def cat_ps1(req, ver):
    ralo = float(req.GET['ralo'])
    rahi = float(req.GET['rahi'])
    declo = float(req.GET['declo'])
    dechi = float(req.GET['dechi'])
    # We have the EDR region and a block around 0,0
    if (rahi > 241) and (ralo < 246) * (dechi >= 6.5) * (declo < 11.5):
        return cat(req, ver, 'ps1',
                   os.path.join(settings.DATA_DIR,'ps1-cat-edr.fits'))
    return cat(req, ver, 'ps1',
               os.path.join(settings.DATA_DIR,'ps1-cat.fits'))

def cat(req, ver, tag, fn, T=None):
    import json
    ralo = float(req.GET['ralo'])
    rahi = float(req.GET['rahi'])
    declo = float(req.GET['declo'])
    dechi = float(req.GET['dechi'])

    ver = int(ver)
    if not ver in catversions[tag]:
        raise RuntimeError('Invalid version %i for tag %s' % (ver, tag))

    from astrometry.util.fits import fits_table
    import numpy as np

    if T is None:
        T = fits_table(fn)
        debug(len(T), 'catalog objects')
    if ralo > rahi:
        # RA wrap
        T.cut(np.logical_or(T.ra > ralo, T.ra < rahi) * (T.dec > declo) * (T.dec < dechi))
    else:
        T.cut((T.ra > ralo) * (T.ra < rahi) * (T.dec > declo) * (T.dec < dechi))
    debug(len(T), 'in cut')

    rd = list((float(r),float(d)) for r,d in zip(T.ra, T.dec))
    rtn = dict(rd=rd)

    # PS1
    if 'ndetections' in T.columns():
        T.name = np.array(['%i' % n for n in T.ndetections])

    if 'name' in T.columns():
        names = [t.strip() for t in T.name]
        rtn['name'] = names
    # bright stars, GCs/PNe
    if 'alt_name' in T.columns():
        rtn.update(altname = [t.strip() for t in T.alt_name])

    # if 'majax' in T.columns() and 'minax' in T.columns() and 'pa' in T.columns():
    #     # GCs/PNe catalog
    #     T.abRatio = T.minax / T.majax
    #     T.posAngle = T.pa
    #     T.rename('majax', 'radius')

    if 'radius' in T.columns():
        rtn.update(radiusArcsec=list(float(f) for f in T.radius * 3600.))

    if 'posAngle' in T.columns() and 'abRatio' in T.columns():
        rtn.update(posAngle=list(float(f) for f in T.posAngle),
                   abRatio =list(float(f) for f in T.abRatio))
        
    return HttpResponse(json.dumps(rtn), content_type='application/json')

def any_cat(req, name, ver, zoom, x, y, **kwargs):
    from map.views import get_layer
    #print('any_cat(', name, ver, zoom, x, y, ')')
    layer = get_layer(name)
    if layer is None:
        return HttpResponse('no such layer')
    return cat_decals(req, ver, zoom, x, y, tag=name, docache=False)

def cat_decals(req, ver, zoom, x, y, tag='decals', docache=True):
    import json
    zoom = int(zoom)
    if zoom < 12:
        return HttpResponse(json.dumps(dict(rd=[])),
                            content_type='application/json')

    try:
        wcs, W, H, zoomscale, zoom,x,y = get_tile_wcs(zoom, x, y)
    except RuntimeError as e:
        print('e:', e)
        return HttpResponse(e.strerror)
    ver = int(ver)
    if not ver in catversions[tag]:
        raise RuntimeError('Invalid version %i for tag %s' % (ver, tag))

    basedir = settings.DATA_DIR
    sendfile_kwargs = dict()
    if docache:
        cachefn = os.path.join(basedir, 'cats-cache', tag,
                               '%i/%i/%i/%i.cat.json' % (ver, zoom, x, y))
        if os.path.exists(cachefn):
            return send_file(cachefn, 'application/json',
                             modsince=req.META.get('HTTP_IF_MODIFIED_SINCE'),
                             expires=oneyear)
        sendfile_kwargs.update(expires=oneyear)
    else:
        import tempfile
        f,cachefn = tempfile.mkstemp(suffix='.json')
        os.close(f)
        sendfile_kwargs.update(unlink=True)

    from map.views import get_layer
    layer = get_layer(tag)
    cat,hdr = layer.get_catalog_in_wcs(wcs)

    if cat is None:
        rd = []
        types = []
        fluxes = []
        bricknames = []
        objids = []
        nobs = []
    else:
        rd = list(zip(cat.ra, cat.dec))
        types = list([t[0] for t in cat.get('type')])

        havebands = []
        havefluxes = []
        havenobs = []
        cols = cat.get_columns()
        for band in 'griz':
            if 'flux_'+band in cols:
                havebands.append(band)
                havefluxes.append(cat.get('flux_' + band))
                havenobs.append(cat.get('nobs_' + band))
        fluxes = []
        for F in zip(*havefluxes):
            fluxes.append(dict([(b,float(f)) for b,f in zip(havebands, F)]))
        nobs = []
        for N in zip(*havenobs):
            nobs.append(dict([(b,int(f)) for b,f in zip(havebands, N)]))
        #fluxes = [dict(g=float(g), r=float(r), z=float(z))
        #          for g,r,z in zip(cat.flux_g, cat.flux_r, cat.flux_z)]
        #nobs = [dict(g=int(g), r=int(r), z=int(z))
        #        for g,r,z in zip(cat.nobs_g, cat.nobs_r, cat.nobs_z)]
        bricknames = list(cat.brickname)
        objids = [int(x) for x in cat.objid]

    json = json.dumps(dict(rd=rd, sourcetype=types, fluxes=fluxes, nobs=nobs,
                                 bricknames=bricknames, objids=objids))
    if docache:
        trymakedirs(cachefn)

    f = open(cachefn, 'w')
    f.write(json)
    f.close()
    return send_file(cachefn, 'application/json', **sendfile_kwargs)

@lru_cache(maxsize=1)
def get_desi_tiles():
    """Returns a dictionary mapping of tileid: (ra, dec) of desi tiles
    """
    from astrometry.util.fits import fits_table

    #path = os.path.join(settings.DATA_DIR, 'desi-tiles.fits')
    path = os.path.join(settings.DATA_DIR, 'desi-spectro-daily', 'tiles2.kd.fits')
    t = fits_table(path)
    tileradec = dict()
    for tileid, ra, dec in zip(t.tileid, t.ra, t.dec):
        tileradec[tileid] = (ra,dec)
    return tileradec

def get_desi_tile_radec(tileid, fiberid=None):
    tilerd = get_desi_tiles()
    return tilerd.get(tileid, None)

    #### OLD - read from fiberassign file.
    """Accepts a tile_id, returns a tuple of ra, dec
    Raises a RuntimeError if tile_id is not found
    """
    import fitsio
    fn = desi_fiberassign_filename(tileid)
    if not os.path.exists(fn):
        raise RuntimeError("DESI tile not found")
    hdr = fitsio.read_header(fn)
    ra = hdr['TILERA']
    dec = hdr['TILEDEC']

    if fiberid is not None:
        from astrometry.util.fits import fits_table
        import numpy as np
        T = fits_table(fn, columns=['target_ra', 'target_dec', 'fiber'])
        I = np.flatnonzero(T.fiber == fiberid)
        if len(I) == 1:
            i = I[0]
            return T.target_ra[i], T.target_dec[i]
    
    return ra,dec
    # # Load tile radec
    # tileradec = get_desi_tiles()
    # if tile_id in tileradec:
    #     ra = tileradec[tile_id][0]
    #     dec = tileradec[tile_id][1]
    #     return ra, dec
    # else:
    #     raise RuntimeError("DESI tile not found")

if __name__ == '__main__':
    import sys

    if False:
        from map.views import get_layer
        #galfn = os.path.join(settings.DATA_DIR, 'galaxies-in-hsc2.fits')
        #layer = get_layer('hsc2')
        #create_galaxy_catalog(galfn, None, layer=layer)
    
        galfn = os.path.join(settings.DATA_DIR, 'galaxies-in-dr10.fits')
        layer = get_layer('ls-dr10')
        create_galaxy_catalog(galfn, None, layer=layer)
        sys.exit(0)
    
    # galfn = os.path.join(settings.DATA_DIR, 'galaxies-in-dr9.fits')
    # layer = get_layer('ls-dr9-north')
    # create_galaxy_catalog(galfn, None, layer=layer)
    # sys.exit(0)

    if False:
        # Create SDSS DR16 Spectra file (specObj-dr16-trimmed.kd.fits):
        from astrometry.util.fits import fits_table
        import numpy as np
        T=fits_table('/global/cfs/cdirs/cosmo/data/sdss/dr16/sdss/spectro/redux/specObj-dr16.fits',
                     columns=['plate','mjd','fiberid','plug_ra','plug_dec','class','subclass','z','zwarning'])
        print('Read', len(T))
        T.rename('plug_ra', 'ra')
        T.rename('plug_dec','dec')
        labels = []
        for t in T:
            sub = t.subclass
            sub = sub.split()
            sub = ' '.join([s for s in sub if s[0] != '('])
            cla = t.get('class').strip()
            txt = cla
            if len(sub):
                txt += ' (' + sub + ')'
            if cla in ['GALAXY', 'QSO']:
                txt += ' z=%.3f' % t.z
            labels.append(txt)
        T.label = np.array(labels)
        print('Writing trimmed...')
        T.writeto('data/sdss/specObj-dr16-trimmed.fits', columns=['ra','dec','plate','mjd','fiberid','z','zwarning','label'])
        print('Creating kdtree...')
        os.system('startree -i data/sdss/specObj-dr16-trimmed.fits -o data/sdss/specObj-dr16-trimmed.kd.fits -T -k -P')
        sys.exit(0)

    #t = lookup_targetid(39627788403084375)
    #print('Targetid:', t)
    #t.about()
    
    from django.test import Client
    c = Client()
    #r = c.get('/sga/1/cat.json?ralo=259.2787&rahi=259.7738&declo=35.9422&dechi=36.1656')
    #r = c.get('/sga/1/cat.json?ralo=259.5726&rahi=260.0677&declo=35.9146&dechi=36.1382')
    #r = c.get('/usercatalog/1/cat.json?ralo=350.0142&rahi=350.0761&declo=-9.6430&dechi=-9.6090&cat=tmppboi50xv')
    ## should contain NGC 6349

    #r = c.get('/dr8-south/1/12/3572/2187.cat.json')
    #r = c.get('/dr8-north/1/14/8194/5895.cat.json')
    #r = c.get('/dr8/1/14/8194/5895.cat.json')
    #r = c.get('/decals-dr7/1/14/8639/7624.cat.json')
    #r = c.get('/mzls+bass-dr6/1/14/7517/6364.cat.json')
    #r = c.get('/targets-dr9-main-dark/1/cat.json?ralo=189.1391&rahi=189.2628&declo=27.5179&dechi=27.5791')
    #r = c.get('/desi-spec-daily/1/cat.json?ralo=154.1814&rahi=154.3175&declo=-2.6274&dechi=-2.5515')
    #r = c.get('/targets-dr9-main-dark/1/cat.json?ralo=189.1391&rahi=189.2628&declo=27.5179&dechi=27.5791')
    #r = c.get('/desi-tile/1/cat.json?ralo=238.1458&rahi=238.4181&declo=-0.0750&dechi=0.0748&tile=1000')
    #r = c.get('/desi-tile/1/cat.json?ralo=190.9733&rahi=191.6270&declo=10.1426&dechi=10.5060&tile=8786')
    #r = c.get('/targets-dr9-main-dark/1/cat.json?ralo=189.1391&rahi=189.2628&declo=27.5179&dechi=27.5791')
    #r = c.get('/desi-spectrum/daily/targetid39628158961452744')
    #r = c.get('/desi-spectrum/daily/targetid39633049259870731')

    # tile = 6834
    # print('Tile', tile, 'rd', get_desi_tile_radec(tile))
    # sys.exit(0)
    
    #r = c.get('/desi-spectrum/guadalupe/targetid39633049259870731')
    #r = c.get('/desi-spectrum/daily/targetid43977408013222855')
    #r = c.get('/ls-dr9/1/15/29479/18709.cat.json')
    #r = c.get('/usercatalog/1/cat.json?ralo=61.2789&rahi=61.3408&declo=-74.8711&dechi=-74.8622&cat=tmpbclfdga8')
    r = c.get('/desi-spectrum/edr/targetid39627883857055540')

    f = open('out', 'wb')
    for x in r:
        f.write(x)
    f.close()

    sys.exit(0)
    
    #print('Random galaxy:', get_random_galaxy(layer='mzls+bass-dr4'))
    #create_galaxy_catalog('/tmp/dr8.fits', 8)

    
    from astrometry.util.fits import *
    T6 = fits_table('data/galaxies-in-dr6.fits')
    T7 = fits_table('data/galaxies-in-dr7.fits')
    T8 = merge_tables([T6, T7], columns='fillzero')
    T8.writeto('data/galaxies-in-dr8.fits')

    #specObj-dr14.fits
    #T = fits_table('/project/projectdirs/cosmo/data/sdss/dr14/sdss/spectro/redux/specObj-dr14.fits')

    from django.test import Client
    c = Client()
    c.get('/usercatalog/1/cat.json?ralo=200.2569&rahi=200.4013&declo=47.4930&dechi=47.5823&cat=tmpajwai3dx')
    sys.exit(0)
