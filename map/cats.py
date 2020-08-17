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
    'dr9sv': [1,],
    'dr9sv-north': [1,],
    'dr9sv-south': [1,],
    'dr8': [1,],
    'dr8-north': [1,],
    'dr8-south': [1,],
    'decals-dr7': [1,],
    'mzls+bass-dr6': [1,],
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
    'gaia-dr1': [1,],
    'gaia-dr2': [1,],
    'sdss-cat': [1,],
    'phat-clusters': [1,],
    'ps1': [1,],
    'desi-tiles': [1,],
    'masks-dr8': [1,],
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

def cat_gaia_dr2(req, ver):
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

    os.environ['GAIA_CAT_DIR'] = os.path.join(settings.DATA_DIR, 'gaia-dr2')
    gaia = GaiaCatalog()
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

    try:
        T = fits_table(tmpfn)
    except:
        return HttpResponse('Must upload FITS format catalog including "RA", "Dec", optionally "Name" columns')
    
    # Rename and resave columns if necessary
    if rename_cols(T):
        T.write_to(tmpfn)

    cols = T.columns()
    if not (('ra' in cols) and ('dec' in cols)):
        return HttpResponse('Must upload catalog including "RA", "Dec", optionally "Name" columns')

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
    else:
        galfn = os.path.join(settings.DATA_DIR, 'galaxies-in-dr8.fits')


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

def cat_targets_drAB(req, ver, cats=None, tag='', bgs=False, sky=False, bright=False, dark=False, color_name_func=desitarget_color_names, colprefix=''):
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

    if sky:
        fluxes = [dict(g=float(g), r=float(r), z=float(z))
                  for (g,r,z) in zip(T.apflux_g[:,0], T.apflux_r[:,0], T.apflux_z[:,0])]
        nobs = None
    else:
        fluxes = [dict(g=float(g), r=float(r), z=float(z),
                       W1=float(W1), W2=float(W2))
                  for (g,r,z,W1,W2)
                  in zip(T.flux_g, T.flux_r, T.flux_z, T.flux_w1, T.flux_w2)]
        nobs=[dict(g=int(g), r=int(r), z=int(z)) for g,r,z
              in zip(T.nobs_g, T.nobs_r, T.nobs_z)],

    rtn = dict(rd=[(t.ra, t.dec) for t in T],
               targetid=[int(t) for t in T.targetid],
               fluxes=fluxes,
           )
    if names is not None:
        rtn.update(name=names)
    if colors is not None:
        rtn.update(color=colors)
    if nobs is not None:
        rtn.update(nobs=nobs)
    
    # Convert targetid to string to prevent rounding errors
    rtn['targetid'] = [str(s) for s in rtn['targetid']]
    
    return HttpResponse(json.dumps(rtn), content_type='application/json')

def cat_sga_parent(req, ver):
    fn = os.path.join(settings.DATA_DIR, 'sga', 'SGA-parent-v3.0.kd.fits')
    return _cat_sga(req, ver, fn=fn, tag='sga', sga=True)

def cat_sga_ellipse(req, ver):
    fn = os.path.join(settings.DATA_DIR, 'sga', 'SGA-ellipse-v3.0.kd.fits')
    return _cat_sga(req, ver, ellipse=True, fn=fn, tag='sga', sga=True)

def cat_sga(req, ver):
    return _cat_sga(req, ver)

def _cat_sga(req, ver, ellipse=False, fn=None, tag='sga', sga=False):
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

    if ellipse:
        if sga:
            T.cut((T.sga_id >= 0) * (T.preburned))
        else:
            T.cut((T.id >= 0) * (T.preburned))

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
    T.radius_arcsec = T.diam / 2. * 60.
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
    fn = os.path.join(settings.DATA_DIR, 'sdss', 'specObj-dr14-trimmed.kd.fits')
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
    debug(len(T), 'spectra')
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
    debug(len(T), 'in cut')

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
    rad = degrees_between(rc, dc, ralo, declo)
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
    if 'gnobs' in cols and 'rnobs' in cols and 'znobs' in cols:
        D.update(nobs=[dict(g=int(g), r=int(r), z=int(z))
                       for g,r,z in zip(cat.gnobs, cat.rnobs, cat.znobs)])
    if 'objids' in cols:
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

def cat_bright(req, ver):
    return cat(req, ver, 'bright',
               os.path.join(settings.DATA_DIR, 'bright.fits'))

def cat_tycho2(req, ver):
    return cat(req, ver, 'tycho2',
               os.path.join(settings.DATA_DIR, 'tycho2.fits'))

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
    from map.views import layer_name_map, get_layer
    print('any_cat(', name, ver, zoom, x, y, ')')
    name = layer_name_map(name)
    layer = get_layer(name)
    if layer is None:
        return HttpResponse('no such layer: ' + name)
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

    cat,hdr = _get_decals_cat(wcs, tag=tag)

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
        fluxes = [dict(g=float(g), r=float(r), z=float(z))
                  for g,r,z in zip(cat.flux_g, cat.flux_r, cat.flux_z)]
        nobs = [dict(g=int(g), r=int(r), z=int(z))
                for g,r,z in zip(cat.nobs_g, cat.nobs_r, cat.nobs_z)]
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

    path = os.path.join(settings.DATA_DIR, 'desi-tiles.fits')
    t = fits_table(path)
    tileradec = dict()
    for tileid, ra, dec in zip(t.tileid, t.ra, t.dec):
        tileradec[tileid] = (ra,dec)
    return tileradec

def get_desi_tile_radec(tile_id):
    """Accepts a tile_id, returns a tuple of ra, dec
    Raises a RuntimeError if tile_id is not found
    """
    # Load tile radec
    tileradec = get_desi_tiles()

    if tile_id in tileradec:
        ra = tileradec[tile_id][0]
        dec = tileradec[tile_id][1]
        return ra, dec
    else:
        raise RuntimeError("DESI tile not found")

def _get_decals_cat(wcs, tag='decals'):
    from map.views import get_layer
    layer = get_layer(tag)
    return layer.get_catalog_in_wcs(wcs)


if __name__ == '__main__':
    import sys

    galfn = os.path.join(settings.DATA_DIR, 'galaxies-in-hsc2.fits')
    from map.views import get_layer
    layer = get_layer('hsc2')
    create_galaxy_catalog(galfn, None, layer=layer)


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
    r = c.get('/mzls+bass-dr6/1/14/7517/6364.cat.json')
    
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

    T=fits_table('/project/projectdirs/cosmo/data/sdss/dr14/sdss/spectro/redux/specObj-dr14.fits',
                 columns=['plate','mjd','fiberid','plug_ra','plug_dec','class','subclass','z','zwarning'])
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
    T.writeto('specObj-dr14-trimmed.fits', columns=['ra','dec','plate','mjd','fiberid','z','zwarning','label'])

    # startree -i data/specObj-dr14-trimmed.fits -o data/specObj-dr14-trimmed.kd.fits -T -k -P
