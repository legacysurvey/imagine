from django.conf.urls import url

from map import views
from map import cats
from map import cutouts

urlpatterns = [

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
        #views.sdss_layer.get_tile_view()),

    # DECaPS tiles
    url(r'^decaps/(\d+)/(\d+)/(\d+)/(\d+).jpg',
        views.get_tile_view('decaps')),

    # MzLS+BASS DR4 tiles
    url(r'^mzls\+bass-dr4/(\d+)/(\d+)/(\d+)/(\d+).jpg',
        views.get_tile_view('mzls+bass-dr4')),
    url(r'^mzls\+bass-dr4-model/(\d+)/(\d+)/(\d+)/(\d+).jpg',
        views.get_tile_view('mzls+bass-dr4-model')),

    # DR4 catalog
    url(r'^mzls\+bass-dr4/(\d+)/(\d+)/(\d+)/(\d+).cat.json', cats.cat_mobo_dr4),

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

    # DR3 Mosaic+Bok
    # url(r'^mobo-dr3/(\d+)/(\d+)/(\d+)/(\d+).jpg', views.map_mobo_dr3),
    # url(r'^mobo-dr3-model/(\d+)/(\d+)/(\d+)/(\d+).jpg', views.map_mobo_dr3_model),
    # url(r'^mobo-dr3-resid/(\d+)/(\d+)/(\d+)/(\d+).jpg', views.map_mobo_dr3_resid),

    # DR3 MzLS
    url(r'^mzls-dr3/(\d+)/(\d+)/(\d+)/(\d+).jpg',
        views.get_tile_view('mzls-dr3')),
        #views.mzls3_image.get_tile_view()),
    url(r'^mzls-dr3-model/(\d+)/(\d+)/(\d+)/(\d+).jpg',
        views.get_tile_view('mzls-dr3-model')),
        #views.mzls3_model.get_tile_view()),
    url(r'^mzls-dr3-resid/(\d+)/(\d+)/(\d+)/(\d+).jpg',
        views.get_tile_view('mzls-dr3-resid')),
        #views.mzls3_resid.get_tile_view()),

    # DR3
    url(r'^decals-dr3/(\d+)/(\d+)/(\d+)/(\d+).jpg',
        views.get_tile_view('decals-dr3')),
    #views.dr3_image.get_tile_view()),
    url(r'^decals-dr3-model/(\d+)/(\d+)/(\d+)/(\d+).jpg',
        views.get_tile_view('decals-dr3-model')),
        #views.dr3_model.get_tile_view()),
    url(r'^decals-dr3-resid/(\d+)/(\d+)/(\d+)/(\d+).jpg',
        views.get_tile_view('decals-dr3-resid')),
        #views.dr3_resid.get_tile_view()),

    # catalog
    url(r'^decals-dr3/(\d+)/(\d+)/(\d+)/(\d+).cat.json', cats.cat_decals_dr3),
    
    # DR2
    url(r'^decals-dr2/(\d+)/(\d+)/(\d+)/(\d+).jpg',
        views.get_tile_view('decals-dr2')),
        #views.dr2_image.get_tile_view()),
    url(r'^decals-dr2-model/(\d+)/(\d+)/(\d+)/(\d+).jpg',
        views.get_tile_view('decals-dr2-model')),
        #views.dr2_model.get_tile_view()),
    url(r'^decals-dr2-resid/(\d+)/(\d+)/(\d+)/(\d+).jpg',
        views.get_tile_view('decals-dr2-resid')),
        #views.dr2_resid.get_tile_view()),

    # catalog
    url(r'^decals-dr2/(\d+)/(\d+)/(\d+)/(\d+).cat.json', cats.cat_decals_dr2),

    url(r'^targets-dr2/(\d+)/cat.json', cats.cat_targets_dr2),

    # depth maps
    #url(r'^decam-depth/(\d+)/(\d+)/(\d+)/(\d+).jpg', views.map_decam_depth),

    # DR1k -- COSMOS
    #url(r'^decals-dr1k/(\d+)/(\d+)/(\d+)/(\d+).jpg', views.map_decals_dr1k),

    # DR1j full
    # url(r'^decals-dr1j/(\d+)/(\d+)/(\d+)/(\d+).jpg', views.map_decals_dr1j),
    # url(r'^decals-model-dr1j/(\d+)/(\d+)/(\d+)/(\d+).jpg', views.map_decals_model_dr1j),
    # url(r'^decals-resid-dr1j/(\d+)/(\d+)/(\d+)/(\d+).jpg', views.map_decals_resid_dr1j),

    # catalog
    url(r'^decals-dr1j/(\d+)/(\d+)/(\d+)/(\d+).cat.json', cats.cat_decals_dr1j),

    #url(r'^decals-nexp-dr1j/(\d+)/(\d+)/(\d+)/(\d+).jpg', views.map_decals_nexp_dr1j),
    #url(r'^decals-wl/(\d+)/(\d+)/(\d+)/(\d+).jpg', views.map_decals_wl),

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
        #views.sfd_layer.get_tile_view()),

    # Halpha map
    url(r'^halpha/(\d+)/(\d+)/(\d+)/(\d+).jpg',
        views.get_tile_view('halpha')),
    #views.halpha_layer.get_tile_view()),

    # unWISE W1/W2
    url(r'^unwise-w1w2/(\d+)/(\d+)/(\d+)/(\d+).jpg',
        views.get_tile_view('unwise-w1w2')),
        #views.unwise_layer.get_tile_view()),

    # Aaron's NEO1 unWISE W1/W2
    url(r'^unwise-neo1/(\d+)/(\d+)/(\d+)/(\d+).jpg',
        views.get_tile_view('unwise-neo1')),
    #views.unwise_neo1_layer.get_tile_view()),
    # NEO2
    url(r'^unwise-neo2/(\d+)/(\d+)/(\d+)/(\d+).jpg',
        views.get_tile_view('unwise-neo2')),

    #url(r'^unwise-w3w4-tiles/(\d+)/(\d+)/(\d+)/(\d+).jpg', views.map_unwise_w3w4),
    #url(r'^unwise-w1234-tiles/(\d+)/(\d+)/(\d+)/(\d+).jpg', views.map_unwise_w1234),

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
    url(r'^ccd/([\w-]+)/([\w-]+)', views.ccd_detail, name='ccd_detail'),
    # this one is here to provide a name for the javascript to refer to.
    url(r'^ccd/', views.nil, name='ccd_detail_blank'),
    # Exposure details
    url(r'^exposure/([\w-]+)/([\w-]+)', views.exposure_detail, name='exp_detail'),
    # this one is here to provide a name for the javascript to refer to.
    url(r'^exposure/', views.nil, name='exp_detail_blank'),

    # Image data
    url(r'^image-data/([\w-]+)/([\w-]+)', views.image_data, name='image_data'),
    url(r'^dq-data/([\w-]+)/([\w-]+)', views.dq_data, name='dq_data'),
    url(r'^iv-data/([\w-]+)/([\w-]+)', views.iv_data, name='iv_data'),

    url(r'^image-stamp/([\w-]+)/([\w-]+).jpg', views.image_stamp, name='image_stamp'),

    # fall-through
    url(r'', views.index),

]
