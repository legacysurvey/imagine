from django.urls import path,re_path

from map import views
from map import cats
from map import cutouts

from viewer import settings

survey_regex = r'[\w\. +-]+'
layer_regex = r'\{id\}|' + survey_regex

urlpatterns_desi = [
]

# DESI public
urlpatterns_desi.extend([
    # All DESI tiles (tiles-main.ecsv)
    re_path(r'^desi-all-tiles/(\w+)/(\d+)/cat.json', cats.cat_desi_all_tiles),

    # DESI EDR tiles
    re_path(r'^desi-tiles/edr/(\d+)/cat.json', cats.cat_desi_edr_tiles),
    # DESI EDR spectra overlay
    re_path(r'^desi-spec-edr/(\d+)/cat.json', cats.cat_desi_edr_spectra),
    # DESI EDR spectrum viewer
    re_path(r'^desi-spectrum/edr/targetid(\d+)', cats.cat_desi_edr_spectra_detail),

    # DESI daily observations
    re_path(r'^desi-obs-daily/(\d+)/cat.json', cats.cat_desi_daily_obs),
    # DESI daily observations -- details per object
    re_path(r'^desi-obs/daily/targetid(\d+)', cats.cat_desi_daily_obs_detail),
])

if settings.ENABLE_DESI_DATA:
    # Private
    urlpatterns_desi.extend([
        # All DESI tiles (tiles-main.ecsv)
        #re_path(r'^desi-all-tiles/(\w+)/(\d+)/cat.json', cats.cat_desi_all_tiles),

        # DESI spectroscopy -- DR1
        re_path(r'^desi-tiles/dr1/(\d+)/cat.json', cats.cat_desi_dr1_tiles),
        re_path(r'^desi-spec-dr1/(\d+)/cat.json', cats.cat_desi_dr1_spectra),
        re_path(r'^desi-spectrum/dr1/targetid(-?\d+)', cats.cat_desi_dr1_spectra_detail),

        # DESI spectroscopy -- daily
        re_path(r'^desi-tiles/daily/(\d+)/cat.json', cats.cat_desi_daily_tiles),
        re_path(r'^desi-spec-daily/(\d+)/cat.json', cats.cat_desi_daily_spectra),
        re_path(r'^desi-spec-daily-sky/(\d+)/cat.json', cats.cat_desi_daily_sky_spectra),
        #re_path(r'^desi-spectrum/daily/tile(\d+)/fiber(\d+)', cats.cat_desi_daily_spectra_detail),
        re_path(r'^desi-spectrum/daily/targetid(-?\d+)', cats.cat_desi_daily_spectra_detail),

        # DESI spectroscopy -- Guadalupe
        re_path(r'^desi-tiles/guadalupe/(\d+)/cat.json', cats.cat_desi_guadalupe_tiles),
        re_path(r'^desi-spec-guadalupe/(\d+)/cat.json', cats.cat_desi_guadalupe_spectra),
        re_path(r'^desi-spectrum/guadalupe/targetid(-?\d+)', cats.cat_desi_guadalupe_spectra_detail),

        # DESI spectroscopy -- Fuji
        re_path(r'^desi-tiles/fuji/(\d+)/cat.json', cats.cat_desi_fuji_tiles),
        re_path(r'^desi-spec-fuji/(\d+)/cat.json', cats.cat_desi_fuji_spectra),
        re_path(r'^desi-spectrum/fuji/targetid(-?\d+)', cats.cat_desi_fuji_spectra_detail),
    ])

urlpatterns = ([

    re_path(r'^alive', views.alive),
    re_path(r'^checkflavour/([\w-]+)', views.checkflavour),
    re_path(r'^cutout/checkflavour/([\w-]+)', views.checkflavour),

    re_path(r'^urls', views.urls, name='urls'),

    re_path(r'^gfas', views.gfas),
    re_path(r'^ci', views.ci),

    # Rongpu's DR9 photo-zs
    re_path(r'^photoz-dr9/(\d+)/cat.json', cats.cat_photoz_dr9),

    re_path(r'^hsc-dr2-cosmos/(\d+)/cat.json', cats.cat_hsc_dr2_cosmos),

    re_path(r'^gaia-stars-for-wcs', cats.gaia_stars_for_wcs),

    re_path(r'^masks-dr8/(\d+)/cat.json', cats.cat_gaia_mask),

    re_path(r'^masks-dr9/(\d+)/cat.json', cats.cat_masks_dr9),

    # PHAT cluster catalog
    re_path(r'^phat-clusters/(\d+)/cat.json', cats.cat_phat_clusters),

] + urlpatterns_desi + [

    # DR9 MAIN targets
    re_path(r'^targets-dr9-main-sec-dark/(\d+)/cat.json', cats.cat_targets_dr9_main_sec_dark),
    re_path(r'^targets-dr9-main-sec-bright/(\d+)/cat.json', cats.cat_targets_dr9_main_sec_bright),
    re_path(r'^targets-dr9-main-dark/(\d+)/cat.json', cats.cat_targets_dr9_main_dark),
    re_path(r'^targets-dr9-main-bright/(\d+)/cat.json', cats.cat_targets_dr9_main_bright),

    # DR9 SV3 targets
    re_path(r'^targets-dr9-sv3-sec-dark/(\d+)/cat.json', cats.cat_targets_dr9_sv3_sec_dark),
    re_path(r'^targets-dr9-sv3-sec-bright/(\d+)/cat.json', cats.cat_targets_dr9_sv3_sec_bright),
    re_path(r'^targets-dr9-sv3-dark/(\d+)/cat.json', cats.cat_targets_dr9_sv3_dark),
    re_path(r'^targets-dr9-sv3-bright/(\d+)/cat.json', cats.cat_targets_dr9_sv3_bright),
    #re_path(r'^targets-dr9-sv1-supp/(\d+)/cat.json', cats.cat_targets_dr9_sv1_supp),
    # DR9 SV1 targets
    re_path(r'^targets-dr9-sv1-dark/(\d+)/cat.json', cats.cat_targets_dr9_sv1_dark),
    re_path(r'^targets-dr9-sv1-bright/(\d+)/cat.json', cats.cat_targets_dr9_sv1_bright),
    re_path(r'^targets-dr9-sv1-supp/(\d+)/cat.json', cats.cat_targets_dr9_sv1_supp),
    # DR9 SV1 secondary targets
    re_path(r'^targets-dr9-sv1-sec-bright/(\d+)/cat.json', cats.cat_targets_dr9_sv1_sec_bright),
    re_path(r'^targets-dr9-sv1-sec-dark/(\d+)/cat.json', cats.cat_targets_dr9_sv1_sec_dark),

     # DR6/7 DESI targets
    re_path(r'^targets-dr67/(\d+)/cat.json', cats.cat_targets_dr67),

     # DR6/7 DESI targets, BGS survey only
    re_path(r'^targets-bgs-dr67/(\d+)/cat.json', cats.cat_targets_bgs_dr67),

    # DR6/7 DESI sky fibers
    re_path(r'^targets-sky-dr67/(\d+)/cat.json', cats.cat_targets_sky_dr67),

    re_path(r'^targets-dark-dr67/(\d+)/cat.json', cats.cat_targets_dark_dr67),
    re_path(r'^targets-bright-dr67/(\d+)/cat.json', cats.cat_targets_bright_dr67),

    re_path(r'^targets-cmx-dr7/(\d+)/cat.json', cats.cat_targets_cmx_dr7),

    # DR8
    re_path(r'^targets-dr8/(\d+)/cat.json', cats.cat_targets_dr8),
    re_path(r'^targets-sv-dr8/(\d+)/cat.json', cats.cat_targets_sv_dr8),

    # Gaia catalog
    re_path(r'^gaia-dr2/(\d+)/cat.json', cats.cat_gaia_dr2),
    re_path(r'^gaia-edr3/(\d+)/cat.json', cats.cat_gaia_edr3),

    # Upload user catalog
    re_path(r'^upload-cat/', cats.upload_cat, name='upload-cat'),

    # AJAX retrieval of user catalogs
    re_path(r'usercatalog/(\d+)/cat.json', cats.cat_user),
    # AJAX retrieval of DESI tiles
    re_path(r'^desi-tile/(\d+)/cat.json', cats.cat_desi_tile),

    # DEEP2 Spectroscopy catalog
    re_path(r'^spec-deep2/(\d+)/cat.json', cats.cat_spec_deep2),

    # SDSS Catalog
    re_path(r'^sdss-cat/(\d+)/cat.json', cats.cat_sdss),

    # PS1 catalog test
    re_path(r'^ps1/(\d+)/cat.json', cats.cat_ps1),

    # For nova.astrometry.net: SDSS for a given WCS
    re_path(r'^sdss-wcs', views.sdss_wcs),

    # Used by the CI image viewer: render image into given WCS
    # (eg http://legacysurvey.org/viewer-dev/ci?ra=195&dec=60)
    re_path(r'^cutout-wcs', views.cutout_wcs),

    re_path(r'^data-for-radec/', views.data_for_radec, name='data_for_radec'),

    re_path(r'^namequery/', views.name_query, name='object-query'),

    # CCDs: list of polygons
    re_path(r'^ccds/', views.ccd_list, name='ccd-list'),
    # Exposures: list of circles
    re_path(r'^exps/', views.exposure_list, name='exposure-list'),

    # Tycho-2 stars
    re_path(r'^tycho2/(\d+)/cat.json', cats.cat_tycho2),

    # Cutouts
    re_path(r'^cutout.jpg', cutouts.jpeg_cutout, name='cutout-jpeg'),
    re_path(r'^cutout.fits', cutouts.fits_cutout, name='cutout-fits'),
    re_path(r'^jpeg-cutout', cutouts.jpeg_cutout),
    re_path(r'^fits-cutout', cutouts.fits_cutout),

    # NGC/IC/UGC galaxies
    re_path(r'^ngc/(\d+)/cat.json', cats.cat_ngc),

    # SGA galaxies
    re_path(r'^sga-parent/(\d+)/cat.json', cats.cat_sga_parent),
    re_path(r'^sga/(\d+)/cat.json', cats.cat_sga_ellipse),

    re_path(r'^GCs-PNe/(\d+)/cat.json', cats.cat_GCs_PNe),

    # Virgo cluster catalog (VCC) objects
    #re_path(r'^vcc/(\d+)/cat.json', views.cat_vcc),

    # SDSS Spectroscopy
    re_path(r'^spec/(\d+)/cat.json', cats.cat_spec),

    re_path(r'^manga/(\d+)/cat.json', cats.cat_manga),

    # Bright stars
    re_path(r'^bright/(\d+)/cat.json', cats.cat_bright),

    # hackish -- pattern for small catalogs
    re_path(r'^\{id\}/\{ver\}/cat.json\?ralo=\{ralo\}&rahi=\{rahi\}&declo=\{declo\}&dechi=\{dechi\}',
        cats.cat_bright,
        name='cat-json-pattern'),

    # Generic tile layers
    re_path(r'^(%s)/(\d+)/(\d+)/(\d+)/(\d+).jpg' % layer_regex,
        views.any_tile_view),
    # tiled catalog
    re_path(r'^(%s)/(\d+)/(\d+)/(\d+)/(\d+).cat.json' % layer_regex,
        cats.any_cat, name='cat-json-tiled'),

    # FITS catalog cutout
    re_path(r'^(%s)/cat.fits' % layer_regex, views.any_fits_cat, name='cat-fits'),

    # HTML catalog output
    re_path(r'^(%s)/cat' % layer_regex, views.any_cat_table, name='cat-table'),

    ## hackish -- the pattern (using leaflet's template format) for cat-json-tiled
    re_path(r'^\{id\}/\{ver\}/\{z\}/\{x\}/\{y\}.cat.json', cats.any_cat, name='cat-json-tiled-pattern'),

    # Single exposures html
    re_path(r'^exposures/', views.exposures, name='exposures'),
    # Cutouts panel plots
    re_path(r'^exposure_panels/(?P<layer>.*)/(?P<expnum>\d+)/(?P<extname>\w+)/', views.exposure_panels,
        name='exposure_panels'),

    # PSF for a single expnum/ccdname -- half-finished.
    #re_path(r'^cutout_psf/(?P<layer>.*)/(?P<expnum>\d+)/(?P<extname>\w+)/', views.cutout_psf,
    #name='cutout_psf'),

    re_path(r'^exposures-tgz/', views.exposures_tgz, name='exposures_tgz'),

    re_path(r'^coadd-psf/', views.coadd_psf, name='coadd_psf'),

    # # Look up this position, date, observatory in JPL Small Bodies database
    # re_path(r'^jpl_lookup/?$', views.jpl_lookup),
    # # Redirect to other URLs on the JPL site.
    # re_path(r'^jpl_lookup/(?P<jpl_url>.*)', views.jpl_redirect),

    # bricks: list of polygons
    re_path(r'^bricks/', views.brick_list, name='brick-list'),

    # SDSS spectro plates: list of circles
    re_path(r'^sdss-plates/', views.sdss_plate_list, name='sdss-plate-list'),

    # Brick details
    re_path(r'^brick/(\d{4}[pm]\d{3})', views.brick_detail, name='brick_detail'),
    # this one is here to provide a name for the javascript to refer to.
    re_path(r'^brick/', views.nil, name='brick_detail_blank'),
    # CCD details
    re_path(r'^ccd/(%s)/([\w-]+)' % survey_regex, views.ccd_detail, name='ccd_detail'),
    # hahahah, Safari cares what the filename suffix is
    re_path(r'^ccd/(%s)/([\w-]+).xhtml' % survey_regex, views.ccd_detail, name='ccd_detail_xhtml'),
    # this one is here to provide a name for the javascript to refer to.
    re_path(r'^ccd/', views.nil, name='ccd_detail_blank'),
    # Exposure details
    re_path(r'^exposure/([\w-]+)/([\w-]+)', views.exposure_detail, name='exp_detail'),
    # this one is here to provide a name for the javascript to refer to.
    re_path(r'^exposure/', views.nil, name='exp_detail_blank'),

    # Image data
    re_path(r'^image-data/(%s)/([\w-]+)' % survey_regex, views.image_data, name='image_data'),
    re_path(r'^dq-data/(%s)/([\w-]+)' % survey_regex, views.dq_data, name='dq_data'),
    re_path(r'^iv-data/(%s)/([\w-]+)' % survey_regex, views.iv_data, name='iv_data'),

    re_path(r'^image-stamp/(%s)/([\w-]+).jpg' % survey_regex, views.image_stamp, name='image_stamp'),
    re_path(r'^iv-stamp/(%s)/([\w-]+).jpg' % survey_regex, views.iv_stamp, name='iv_stamp'),
    re_path(r'^dq-stamp/(%s)/([\w-]+).jpg' % survey_regex, views.dq_stamp, name='dq_stamp'),
    re_path(r'^outlier-stamp/(%s)/([\w-]+).jpg' % survey_regex, views.outlier_stamp, name='outlier_stamp'),
    re_path(r'^sky-stamp/(%s)/([\w-]+).jpg' % survey_regex, views.sky_stamp, name='sky_stamp'),
    re_path(r'^skysub-stamp/(%s)/([\w-]+).jpg' % survey_regex, views.skysub_stamp, name='skysub_stamp'),

    # Special DESI-EDR version of viewer.
    re_path(r'desi-edr', views.desi_edr),

    # Special DESI-DR1 version of viewer.
    re_path(r'desi-dr1', views.desi_dr1),

    # Special DECaPS version of viewer.
    re_path(r'decaps', views.decaps),

    # Special M33 version of viewer.
    re_path(r'm33', views.m33),

    # DR5 version of the viewer.
    re_path(r'dr5', views.dr5),
    # DR6 version of the viewer.
    re_path(r'dr6', views.dr6),

    # PHAT version of the viewer.
    re_path(r'^phat/?$', views.phat),

    # fall-through
    re_path(r'/?', views.index, name='index'),

])
