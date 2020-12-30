from django.conf.urls import url

from map import views
from map import cats
from map import cutouts

survey_regex = r'[\w\. +-]+'
layer_regex = r'\{id\}|' + survey_regex

urlpatterns = [

    url(r'^tst', views.tst),
    url(r'^cat', views.cat),

    url(r'^urls', views.urls, name='urls'),

    url(r'^gfas', views.gfas),
    url(r'^ci', views.ci),

    url(r'^hsc-dr2-cosmos/(\d+)/cat.json', cats.cat_hsc_dr2_cosmos),

    url(r'^gaia-stars-for-wcs', cats.gaia_stars_for_wcs),

    url(r'^masks-dr8/(\d+)/cat.json', cats.cat_gaia_mask),

    url(r'^masks-dr9/(\d+)/cat.json', cats.cat_masks_dr9),

    # PHAT cluster catalog
    url(r'^phat-clusters/(\d+)/cat.json', cats.cat_phat_clusters),

     # DR6/7 DESI targets
    url(r'^targets-dr67/(\d+)/cat.json', cats.cat_targets_dr67),

     # DR6/7 DESI targets, BGS survey only
    url(r'^targets-bgs-dr67/(\d+)/cat.json', cats.cat_targets_bgs_dr67),

    # DR6/7 DESI sky fibers
    url(r'^targets-sky-dr67/(\d+)/cat.json', cats.cat_targets_sky_dr67),

    url(r'^targets-dark-dr67/(\d+)/cat.json', cats.cat_targets_dark_dr67),
    url(r'^targets-bright-dr67/(\d+)/cat.json', cats.cat_targets_bright_dr67),

    url(r'^targets-cmx-dr7/(\d+)/cat.json', cats.cat_targets_cmx_dr7),

    # DR8
    url(r'^targets-dr8/(\d+)/cat.json', cats.cat_targets_dr8),
    url(r'^targets-sv-dr8/(\d+)/cat.json', cats.cat_targets_sv_dr8),

    # Gaia catalog
    url(r'^gaia-dr2/(\d+)/cat.json', cats.cat_gaia_dr2),

    # Upload user catalog
    url(r'^upload-cat/', cats.upload_cat, name='upload-cat'),

    # AJAX retrieval of user catalogs
    url(r'^usercatalog/(\d+)/cat.json', cats.cat_user),
    # AJAX retrieval of DESI tiles
    url(r'^desi-tile/(\d+)/cat.json', cats.cat_desi_tile),

    # DEEP2 Spectroscopy catalog
    url(r'^spec-deep2/(\d+)/cat.json', cats.cat_spec_deep2),

    # SDSS Catalog
    url(r'^sdss-cat/(\d+)/cat.json', cats.cat_sdss),

    # PS1 catalog test
    url(r'^ps1/(\d+)/cat.json', cats.cat_ps1),

    # For nova.astrometry.net: SDSS for a given WCS
    url(r'^sdss-wcs', views.sdss_wcs),

    # Used by the CI image viewer: render image into given WCS
    # (eg http://legacysurvey.org/viewer-dev/ci?ra=195&dec=60)
    url(r'^cutout-wcs', views.cutout_wcs),

    url(r'^data-for-radec/', views.data_for_radec, name='data_for_radec'),

    url(r'^namequery/', views.name_query, name='object-query'),

    # CCDs: list of polygons
    url(r'^ccds/', views.ccd_list, name='ccd-list'),
    # Exposures: list of circles
    url(r'^exps/', views.exposure_list, name='exposure-list'),

    # Tycho-2 stars
    url(r'^tycho2/(\d+)/cat.json', cats.cat_tycho2),

    # Cutouts
    url(r'^cutout.jpg', cutouts.jpeg_cutout, name='cutout-jpeg'),
    url(r'^cutout.fits', cutouts.fits_cutout, name='cutout-fits'),
    url(r'^jpeg-cutout', cutouts.jpeg_cutout),
    url(r'^fits-cutout', cutouts.fits_cutout),

    # NGC/IC/UGC galaxies
    url(r'^ngc/(\d+)/cat.json', cats.cat_ngc),

    # SGA galaxies
    url(r'^sga-parent/(\d+)/cat.json', cats.cat_sga_parent),
    url(r'^sga/(\d+)/cat.json', cats.cat_sga_ellipse),

    url(r'^GCs-PNe/(\d+)/cat.json', cats.cat_GCs_PNe),

    # Virgo cluster catalog (VCC) objects
    #url(r'^vcc/(\d+)/cat.json', views.cat_vcc),

    # SDSS Spectroscopy
    url(r'^spec/(\d+)/cat.json', cats.cat_spec),

    url(r'^manga/(\d+)/cat.json', cats.cat_manga),

    # Bright stars
    url(r'^bright/(\d+)/cat.json', cats.cat_bright),

    # hackish -- pattern for small catalogs
    url(r'^\{id\}/\{ver\}/cat.json\?ralo=\{ralo\}&rahi=\{rahi\}&declo=\{declo\}&dechi=\{dechi\}',
        cats.cat_bright,
        name='cat-json-pattern'),
    
    # Generic tile layers
    url(r'^(%s)/(\d+)/(\d+)/(\d+)/(\d+).jpg' % layer_regex,
        views.any_tile_view),
    # tiled catalog
    url(r'^(%s)/(\d+)/(\d+)/(\d+)/(\d+).cat.json' % layer_regex,
        cats.any_cat, name='cat-json-tiled'),

    # FITS catalog cutout
    url(r'^(%s)/cat.fits' % layer_regex, views.any_fits_cat, name='cat-fits'),

    ## hackish -- the pattern (using leaflet's template format) for cat-json-tiled
    url(r'^\{id\}/\{ver\}/\{z\}/\{x\}/\{y\}.cat.json', cats.any_cat, name='cat-json-tiled-pattern'),

    # Single exposures html
    url(r'^exposures/', views.exposures, name='exposures'),
    # Cutouts panel plots
    url(r'^exposure_panels/(?P<layer>.*)/(?P<expnum>\d+)/(?P<extname>\w+)/', views.exposure_panels,
        name='exposure_panels'),

    # PSF for a single expnum/ccdname -- half-finished.
    #url(r'^cutout_psf/(?P<layer>.*)/(?P<expnum>\d+)/(?P<extname>\w+)/', views.cutout_psf,
    #name='cutout_psf'),

    url(r'^exposures-tgz/', views.exposures_tgz, name='exposures_tgz'),

    url(r'^coadd-psf/', views.coadd_psf, name='coadd_psf'),

    # Look up this position, date, observatory in JPL Small Bodies database
    url(r'^jpl_lookup/?$', views.jpl_lookup),
    # Redirect to other URLs on the JPL site.
    url(r'^jpl_lookup/(?P<jpl_url>.*)', views.jpl_redirect),

    # bricks: list of polygons
    url(r'^bricks/', views.brick_list, name='brick-list'),

    # SDSS spectro plates: list of circles
    url(r'^sdss-plates/', views.sdss_plate_list, name='sdss-plate-list'),

    # Brick details
    url(r'^brick/(\d{4}[pm]\d{3})', views.brick_detail, name='brick_detail'),
    # this one is here to provide a name for the javascript to refer to.
    url(r'^brick/', views.nil, name='brick_detail_blank'),
    # CCD details
    url(r'^ccd/(%s)/([\w-]+)' % survey_regex, views.ccd_detail, name='ccd_detail'),
    # hahahah, Safari cares what the filename suffix is
    url(r'^ccd/(%s)/([\w-]+).xhtml' % survey_regex, views.ccd_detail, name='ccd_detail_xhtml'),
    # this one is here to provide a name for the javascript to refer to.
    url(r'^ccd/', views.nil, name='ccd_detail_blank'),
    # Exposure details
    url(r'^exposure/([\w-]+)/([\w-]+)', views.exposure_detail, name='exp_detail'),
    # this one is here to provide a name for the javascript to refer to.
    url(r'^exposure/', views.nil, name='exp_detail_blank'),

    # Image data
    url(r'^image-data/(%s)/([\w-]+)' % survey_regex, views.image_data, name='image_data'),
    url(r'^dq-data/(%s)/([\w-]+)' % survey_regex, views.dq_data, name='dq_data'),
    url(r'^iv-data/(%s)/([\w-]+)' % survey_regex, views.iv_data, name='iv_data'),

    url(r'^image-stamp/(%s)/([\w-]+).jpg' % survey_regex, views.image_stamp, name='image_stamp'),
    url(r'^iv-stamp/(%s)/([\w-]+).jpg' % survey_regex, views.iv_stamp, name='iv_stamp'),
    url(r'^dq-stamp/(%s)/([\w-]+).jpg' % survey_regex, views.dq_stamp, name='dq_stamp'),

    # Special DECaPS version of viewer.
    url(r'decaps', views.decaps),

    # Special M33 version of viewer.
    url(r'm33', views.m33),

    # DR5 version of the viewer.
    url(r'dr5', views.dr5),
    # DR6 version of the viewer.
    url(r'dr6', views.dr6),

    # PHAT version of the viewer.
    url(r'^phat/?$', views.phat),

    # fall-through
    url(r'', views.index, name='index'),

]
