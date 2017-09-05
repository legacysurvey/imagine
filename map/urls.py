from django.conf.urls import url

from map import views
from map import cats
from map import cutouts

survey_regex = r'([\w +-]+)'


urlpatterns = [

    # DR5
    url(r'^decals-dr5/(\d+)/(\d+)/(\d+)/(\d+).jpg',
        views.get_tile_view('decals-dr5')),
    url(r'^decals-dr5-model/(\d+)/(\d+)/(\d+)/(\d+).jpg',
        views.get_tile_view('decals-dr5-model')),
    url(r'^decals-dr5-resid/(\d+)/(\d+)/(\d+)/(\d+).jpg',
        views.get_tile_view('decals-dr5-resid')),
    # DR5 catalog
    url(r'^decals-dr5/(\d+)/(\d+)/(\d+)/(\d+).cat.json', cats.cat_decals_dr5),

    # MzLS+BASS DR4 tiles
    url(r'^mzls\+bass-dr4/(\d+)/(\d+)/(\d+)/(\d+).jpg',
        views.get_tile_view('mzls+bass-dr4')),
    url(r'^mzls\+bass-dr4-model/(\d+)/(\d+)/(\d+)/(\d+).jpg',
        views.get_tile_view('mzls+bass-dr4-model')),
    url(r'^mzls\+bass-dr4-resid/(\d+)/(\d+)/(\d+)/(\d+).jpg',
        views.get_tile_view('mzls+bass-dr4-resid')),
    # DR4 catalog
    url(r'^mzls\+bass-dr4/(\d+)/(\d+)/(\d+)/(\d+).cat.json', cats.cat_mobo_dr4),

    # DR3
    url(r'^decals-dr3/(\d+)/(\d+)/(\d+)/(\d+).jpg',
        views.get_tile_view('decals-dr3')),
    url(r'^decals-dr3-model/(\d+)/(\d+)/(\d+)/(\d+).jpg',
        views.get_tile_view('decals-dr3-model')),
    url(r'^decals-dr3-resid/(\d+)/(\d+)/(\d+)/(\d+).jpg',
        views.get_tile_view('decals-dr3-resid')),
    # DR3 catalog
    url(r'^decals-dr3/(\d+)/(\d+)/(\d+)/(\d+).cat.json', cats.cat_decals_dr3),
    
    # DR2
    url(r'^decals-dr2/(\d+)/(\d+)/(\d+)/(\d+).jpg',
        views.get_tile_view('decals-dr2')),
    url(r'^decals-dr2-model/(\d+)/(\d+)/(\d+)/(\d+).jpg',
        views.get_tile_view('decals-dr2-model')),
    url(r'^decals-dr2-resid/(\d+)/(\d+)/(\d+)/(\d+).jpg',
        views.get_tile_view('decals-dr2-resid')),
    # DR2 catalog
    url(r'^decals-dr2/(\d+)/(\d+)/(\d+)/(\d+).cat.json', cats.cat_decals_dr2),

    url(r'^targets-dr2/(\d+)/cat.json', cats.cat_targets_dr2),

    # DECaPS2 tiles
    url(r'^decaps2/(\d+)/(\d+)/(\d+)/(\d+).jpg',
        views.get_tile_view('decaps2')),
    url(r'^decaps2-model/(\d+)/(\d+)/(\d+)/(\d+).jpg',
        views.get_tile_view('decaps2-model')),
    url(r'^decaps2-resid/(\d+)/(\d+)/(\d+)/(\d+).jpg',
        views.get_tile_view('decaps2-resid')),
    
    # Gaia catalog
    url(r'^gaia-dr1/(\d+)/cat.json', cats.cat_gaia_dr1),

    # Upload user catalog
    url(r'^upload-cat/', cats.upload_cat),

    # AJAX retrieval of user catalogs
    url(r'^usercatalog/(\d+)/cat.json', cats.cat_user),

    # DEEP2 Spectroscopy catalog
    url(r'^spec-deep2/(\d+)/cat.json', cats.cat_spec_deep2),

    # SDSS tiled coadd
    url(r'^sdssco/(\d+)/(\d+)/(\d+)/(\d+).jpg',
        views.get_tile_view('sdssco')),

    url(r'^resdss/(\d+)/(\d+)/(\d+)/(\d+).jpg',
        views.get_tile_view('resdss')),
    
    # PS1 skycells
    url(r'^ps1/(\d+)/(\d+)/(\d+)/(\d+).jpg',
        views.get_tile_view('ps1')),
    # PS1 catalog test
    url(r'^ps1/(\d+)/cat.json', cats.cat_ps1),

    # For nova.astrometry.net: SDSS for a given WCS
    url(r'^sdss-wcs', views.sdss_wcs),

    url(r'^data-for-radec/', views.data_for_radec, name='data_for_radec'),

    url(r'^namequery/', views.name_query),

    # CCDs: list of polygons
    url(r'^ccds/', views.ccd_list),
    # Exposures: list of circles
    url(r'^exps/', views.exposure_list),

    # Tycho-2 stars
    url(r'^tycho2/(\d+)/cat.json', cats.cat_tycho2),

    # Cutouts
    url(r'^jpeg-cutout', cutouts.jpeg_cutout, name='cutout-jpeg'),
    url(r'^fits-cutout', cutouts.fits_cutout, name='cutout-fits'),

    # NGC/IC/UGC galaxies
    url(r'^ngc/(\d+)/cat.json', cats.cat_gals),
    
    # Virgo cluster catalog (VCC) objects
    #url(r'^vcc/(\d+)/cat.json', views.cat_vcc),

    # Spectroscopy
    url(r'^spec/(\d+)/cat.json', cats.cat_spec),

    # Bright stars
    url(r'^bright/(\d+)/cat.json', cats.cat_bright),

    # SFD dust map
    url(r'^sfd/(\d+)/(\d+)/(\d+)/(\d+).jpg',
        views.get_tile_view('sfd')),

    # Halpha map
    url(r'^halpha/(\d+)/(\d+)/(\d+)/(\d+).jpg',
        views.get_tile_view('halpha')),

    # Original unWISE W1/W2
    url(r'^unwise-w1w2/(\d+)/(\d+)/(\d+)/(\d+).jpg',
        views.get_tile_view('unwise-w1w2')),

    # Aaron's NEOx unWISE W1/W2
    # NEO2
    url(r'^unwise-neo2/(\d+)/(\d+)/(\d+)/(\d+).jpg',
        views.get_tile_view('unwise-neo2')),

    #url(r'^unwise-w3w4-tiles/(\d+)/(\d+)/(\d+)/(\d+).jpg', views.map_unwise_w3w4),

    # Cutouts html
    url(r'^cutouts/', views.cutouts, name='cutouts'),
    # Cutouts panel plots
    url(r'^cutout_panels/(?P<expnum>\d+)/(?P<extname>[NS]\d{1,2})/', views.cutout_panels, name='cutout_panels'),
    # Scatterplot of nearby sources for cutouts page
    url(r'^cat_plot/', views.cat_plot, name='cat_plot'),

    # bricks: list of polygons
    url(r'^bricks/', views.brick_list),

    # SDSS spectro plates: list of circles
    url(r'^sdss-plates/', views.sdss_plate_list),

    # Brick details
    url(r'^brick/(\d{4}[pm]\d{3})', views.brick_detail, name='brick_detail'),
    # this one is here to provide a name for the javascript to refer to.
    url(r'^brick/', views.nil, name='brick_detail_blank'),
    # CCD details
    url(r'^ccd/%s/([\w-]+)' % survey_regex, views.ccd_detail, name='ccd_detail'),
    # this one is here to provide a name for the javascript to refer to.
    url(r'^ccd/', views.nil, name='ccd_detail_blank'),
    # Exposure details
    url(r'^exposure/([\w-]+)/([\w-]+)', views.exposure_detail, name='exp_detail'),
    # this one is here to provide a name for the javascript to refer to.
    url(r'^exposure/', views.nil, name='exp_detail_blank'),

    # Image data
    url(r'^image-data/%s/([\w-]+)' % survey_regex, views.image_data, name='image_data'),
    url(r'^dq-data/%s/([\w-]+)' % survey_regex, views.dq_data, name='dq_data'),
    url(r'^iv-data/%s/([\w-]+)' % survey_regex, views.iv_data, name='iv_data'),

    url(r'^image-stamp/%s/([\w-]+).jpg' % survey_regex, views.image_stamp, name='image_stamp'),

    # Special DECaPS version of viewer.
    url(r'decaps', views.decaps),
    
    # fall-through
    url(r'', views.index),

]
