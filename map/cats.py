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
    'dr8': [1,],
    'dr8-north': [1,],
    'dr8-south': [1,],
    'decals-dr7': [1,],
    'mzls+bass-dr6': [1,],
    'decals-dr5': [1,],
    'mzls+bass-dr4': [1,],
    'ngc': [1,],
    'lslga': [1,],
    'spec': [1,],
    'spec-deep2': [1,],
    'bright': [1,],
    'tycho2': [1,],
    'targets-dr45': [1,],
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
}

test_cats = []
try:
    from map.test_layers import test_cats as tc
    for key,pretty in tc:
        catversions[key] = [1,]
except:
    pass


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


def cat_gaia_dr1(req, ver):
    import json
    from legacypipe.gaiacat import GaiaCatalog

    tag = 'gaia-dr1'
    ralo = float(req.GET['ralo'])
    rahi = float(req.GET['rahi'])
    declo = float(req.GET['declo'])
    dechi = float(req.GET['dechi'])

    ver = int(ver)
    if not ver in catversions[tag]:
        raise RuntimeError('Invalid version %i for tag %s' % (ver, tag))

    os.environ['GAIA_CAT_DIR'] = settings.GAIA_DR1_CAT_DIR
    gaia = GaiaCatalog()
    cat = gaia.get_catalog_radec_box(ralo, rahi, declo, dechi)

    return HttpResponse(json.dumps(dict(
                rd=[(float(o.ra),float(o.dec)) for o in cat],
                gmag=[float(o.phot_g_mean_mag) for o in cat],
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

    os.environ['GAIA_CAT_DIR'] = settings.GAIA_DR2_CAT_DIR
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
    ccds = sdss_ccds_near(rc[0], dc[0], rad)
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
    
    return HttpResponseRedirect(reverse(index) +
                                '?ra=%.4f&dec=%.4f&catalog=%s' % (ra, dec, catname))

galaxycats = {}
def get_random_galaxy(layer=None):
    import numpy as np
    from map.views import layer_to_survey_name

    if layer is not None:
        layer = layer_to_survey_name(layer)

    global galaxycats
    if layer == 'mzls+bass-dr4':
        galfn = os.path.join(settings.DATA_DIR, 'galaxies-in-dr4.fits')
        drnum = 4
    elif layer == 'mzls+bass-dr6':
        galfn = os.path.join(settings.DATA_DIR, 'galaxies-in-dr6.fits')
        drnum = 4
    elif layer == 'decals-dr7':
        galfn = os.path.join(settings.DATA_DIR, 'galaxies-in-dr7.fits')
        drnum = 7
    elif layer == 'decals-dr5':
        galfn = os.path.join(settings.DATA_DIR, 'galaxies-in-dr5.fits')
        drnum = 5

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

    galaxycat = galaxycats[layer]
    i = np.random.randint(len(galaxycat))
    ra = float(galaxycat.ra[i])
    dec = float(galaxycat.dec[i])
    name = galaxycat.name[i].strip()
    return ra,dec,name

def create_galaxy_catalog(galfn, drnum):
    import astrometry.catalogs
    from astrometry.util.fits import fits_table, merge_tables
    import fitsio
    from astrometry.util.util import Tan
    from astrometry.libkd.spherematch import match_radec
    import numpy as np

    fn = os.path.join(os.path.dirname(astrometry.catalogs.__file__), 'ngc2000.fits')
    NGC = fits_table(fn)
    print(len(NGC), 'NGC objects')
    NGC.name = np.array(['NGC %i' % n for n in NGC.ngcnum])
    NGC.delete_column('ngcnum')
    
    fn = os.path.join(os.path.dirname(astrometry.catalogs.__file__), 'ic2000.fits')
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
    T.writeto(os.path.join('/tmp/galaxy-cats.fits'))
    
    keep = np.zeros(len(T), bool)

    from map.views import get_survey

    bricks = None
    if drnum == 4:
        survey = get_survey('mzls+bass-dr4')
        bricks = fits_table(os.path.join(settings.DATA_DIR, 'survey-bricks-in-dr4.fits'))
    elif drnum == 6:
        survey = get_survey('mzls+bass-dr6')
        bricks = survey.get_bricks()
        bricks.cut(bricks.has_g * bricks.has_r * bricks.has_z)
    elif drnum == 5:
        survey = get_survey('decals-dr5')
    elif drnum == 7:
        survey = get_survey('decals-dr7')
    #elif drnum == 8:
    #    survey = get_survey('dr8')

    if bricks is None:
        bricks = survey.get_bricks()
        
    I,J,d = match_radec(bricks.ra, bricks.dec, T.ra, T.dec, 0.25, nearest=True)
    print('Matched', len(I), 'bricks near NGC objects')
    bricks.cut(I)

        # bricks = fits_table(os.path.join(settings.DATA_DIR, 'survey-bricks-dr4.fits'))
        # bricks.cut((bricks.nexp_g > 0) *
        #            (bricks.nexp_r > 0) *
        #            (bricks.nexp_z > 0))
        # print(len(bricks), 'bricks with grz')
        # 
        # sbricks = survey.get_bricks()
        # binds = dict([(b,i) for i,b in enumerate(sbricks.brickname)])
        # I = np.array([binds[b] for b in bricks.brickname])
        # bricks.ra1  = sbricks.ra1[I]
        # bricks.ra2  = sbricks.ra2[I]
        # bricks.dec1 = sbricks.dec1[I]
        # bricks.dec2 = sbricks.dec2[I]
        # 
        # fn = '/tmp/survey-bricks-in-dr4.fits'
        # bricks.writeto(fn)
        # print('Wrote', fn)


    for brick in bricks:
        fn = survey.find_file('nexp', brick=brick.brickname, band='r')
        if not os.path.exists(fn):
            print('Does not exist:', fn)
            continue

        I = np.flatnonzero((T.ra  >= brick.ra1 ) * (T.ra  < brick.ra2 ) *
                           (T.dec >= brick.dec1) * (T.dec < brick.dec2))
        print('Brick', brick.brickname, 'has', len(I), 'galaxies')
        if len(I) == 0:
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
    fn = '/tmp/galaxies-in-dr%i.fits' % drnum
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

def cat_targets_dr45(req, ver):
    return cat_targets_drAB(req, ver, cats=[
        os.path.join(settings.DATA_DIR, 'targets-dr5-0.20.0.kd.fits'),
        os.path.join(settings.DATA_DIR, 'targets-dr4-0.20.0.kd.fits'),
    ], tag = 'targets-dr45')

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

def cat_lslga(req, ver):
    import json
    import numpy as np
    fn = os.path.join(settings.DATA_DIR, 'lslga', 'LSLGA-v2.0.kd.fits')
    tag = 'lslga'
    # The LSLGA catalog includes radii for the galaxies, and we want galaxies
    # that touch our RA,Dec box, so can't use the standard method...
    #T = cat_kd(req, ver, tag, fn)

    ralo = float(req.GET['ralo'])
    rahi = float(req.GET['rahi'])
    declo = float(req.GET['declo'])
    dechi = float(req.GET['dechi'])
    ver = int(ver)
    if not ver in catversions[tag]:
        raise RuntimeError('Invalid version %i for tag %s' % (ver, tag))
    ra,dec,radius = radecbox_to_circle(ralo, rahi, declo, dechi)
    # max radius for LSLGA entries?!
    lslga_radius = 1.0
    T = cat_query_radec(fn, ra, dec, radius + lslga_radius)
    if T is None:
        return HttpResponse(json.dumps(dict(rd=[], name=[], radiusArcsec=[], abRatio=[], posAngle=[], pgc=[], type=[], redshift=[])),
                            content_type='application/json')

    wcs = radecbox_to_wcs(ralo, rahi, declo, dechi)
    W,H = wcs.shape
    ### cut to lslga entries possibly touching wcs box
    radius_pix = T.d25 / 2. * 60. / wcs.pixel_scale()
    print('radius_pix range:', radius_pix.min(), radius_pix.max())
    ok,xx,yy = wcs.radec2pixelxy(T.ra, T.dec)
    T.cut((xx > -radius_pix) * (xx < W+radius_pix) *
          (yy > -radius_pix) * (yy < H+radius_pix))
    print('Cut to', len(T), 'LSLGA possibly touching WCS')

    rd = list((float(r),float(d)) for r,d in zip(T.ra, T.dec))
    names = [t.strip() for t in T.galaxy]
    radius = [d * 60./2. for d in T.d25.astype(np.float32)]

    ab = [float(f) for f in T.ba.astype(np.float32)]
    pa = [float(90.-f) if np.isfinite(f) else 0. for f in T.pa.astype(np.float32)]
    pgc = [int(p) for p in T.pgc]
    z = [float(z) if np.isfinite(z) else -1. for z in T.z.astype(np.float32)]
    typ = [t.strip() if t != 'nan' else '' for t in T.get('type')]

    return HttpResponse(json.dumps(dict(rd=rd, name=names, radiusArcsec=radius,
                                        abRatio=ab, posAngle=pa, pgc=pgc, type=typ,
                                        redshift=z)),
                        content_type='application/json')


def cat_spec(req, ver):
    import json
    fn = os.path.join(settings.DATA_DIR, 'sdss', 'specObj-dr14-trimmed.kd.fits')
    tag = 'spec'
    T = cat_kd(req, ver, tag, fn)
    if T is None:
        return HttpResponse(json.dumps(dict(rd=[], name=[], mjd=[], fiber=[],plate=[])),
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
    return HttpResponse(json.dumps(dict(rd=rd, name=names, mjd=mjd, fiber=fiber, plate=plate)),
                        content_type='application/json')

def cat_kd(req, ver, tag, fn):
    ralo = float(req.GET['ralo'])
    rahi = float(req.GET['rahi'])
    declo = float(req.GET['declo'])
    dechi = float(req.GET['dechi'])
    ver = int(ver)
    if not ver in catversions[tag]:
        raise RuntimeError('Invalid version %i for tag %s' % (ver, tag))

    ra,dec,radius = radecbox_to_circle(ralo, rahi, declo, dechi)
    T = cat_query_radec(fn, ra, dec, radius)
    debug(len(T), 'spectra')
    if ralo > rahi:
        # RA wrap
        T.cut(np.logical_or(T.ra > ralo, T.ra < rahi) * (T.dec > declo) * (T.dec < dechi))
    else:
        T.cut((T.ra > ralo) * (T.ra < rahi) * (T.dec > declo) * (T.dec < dechi))
    debug(len(T), 'in cut')

    return T

def radecbox_to_wcs(ralo, rahi, declo, dechi, W=100, H=100):
    from astrometry.util.starutil_numpy import radectoxyz, xyztoradec, degrees_between
    from astrometry.util.util import Tan
    rc,dc,radius = radecbox_to_circle(ralo, rahi, declo, dechi)
    wd = degrees_between(rc, declo, rc, dechi)
    hd = degrees_between(ralo, dc, rahi, dc)
    psx = wd / W
    psy = hd / H
    wcs = Tan(rc, dc, (W+1.)/2., (H+1)/2., psx, 0., 0., -psy,
              float(W), float(H))
    ok,x,y = wcs.radec2pixelxy(ralo, declo)
    print('Lower corner:', x, y)
    ok,x,y = wcs.radec2pixelxy(rahi, dechi)
    print('Upper corner:', x, y)
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

def cat_gals(req, ver):
    return cat(req, ver, 'ngc',
               os.path.join(settings.DATA_DIR,'galaxy-cats.fits'))

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

def cat(req, ver, tag, fn):
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
    # bright stars
    if 'alt_name' in T.columns():
        rtn.update(altname = [t.strip() for t in T.alt_name])
    if 'radius' in T.columns():
        rtn.update(radiusArcsec=list(float(f) for f in T.radius * 3600.))
        
    return HttpResponse(json.dumps(rtn), content_type='application/json')

def cat_mobo_dr4(req, ver, zoom, x, y, tag='mzls+bass-dr4'):
    return cat_decals(req, ver, zoom, x, y, tag=tag, docache=False)

def cat_decals_dr5(req, ver, zoom, x, y, tag='decals-dr5'):
    return cat_decals(req, ver, zoom, x, y, tag=tag, docache=False)

def cat_mobo_dr6(req, ver, zoom, x, y, tag='mzls+bass-dr6'):
    return cat_decals(req, ver, zoom, x, y, tag=tag, docache=False)

def cat_decals_dr7(req, ver, zoom, x, y, tag='decals-dr7'):
    return cat_decals(req, ver, zoom, x, y, tag=tag, docache=False)

def cat_dr8(req, ver, zoom, x, y, tag='dr8'):
    return cat_decals(req, ver, zoom, x, y, tag=tag, docache=False)

def cat_dr8_north(req, ver, zoom, x, y, tag='dr8-north'):
    return cat_decals(req, ver, zoom, x, y, tag=tag, docache=False)

def cat_dr8_south(req, ver, zoom, x, y, tag='dr8-south'):
    return cat_decals(req, ver, zoom, x, y, tag=tag, docache=False)

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

        if 'decam_flux' in cat.get_columns():
            fluxes = [dict(g=float(g), r=float(r), z=float(z))
                      for g,r,z in zip(cat.decam_flux[:,1], cat.decam_flux[:,2],
                                       cat.decam_flux[:,4])]
            nobs = [dict(g=int(g), r=int(r), z=int(z))
                    for g,r,z in zip(cat.decam_nobs[:,1], cat.decam_nobs[:,2],
                                     cat.decam_nobs[:,4])]
        else:
            # DR4+
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
    from django.test import Client
    c = Client()
    r = c.get('/lslga/1/cat.json?ralo=259.2787&rahi=259.7738&declo=35.9422&dechi=36.1656')
    ## should contain NGC 6349

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
