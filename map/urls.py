from django.conf.urls import patterns, include, url

from map import views

urlpatterns = [
    # SDSS
    #url(r'^sdss/(\d+)/(\d+)/(\d+)/(\d+).jpg', views.map_sdss),
    #url(r'^jpeg-cutout-sdss', views.jpeg_cutout_sdss),
    #url(r'^fits-cutout-sdss', views.fits_cutout_sdss),

    # SDSS tiled coadd
    url(r'^sdssco/(\d+)/(\d+)/(\d+)/(\d+).jpg', views.map_sdssco),

    # DR2
    url(r'^decals-dr2/(\d+)/(\d+)/(\d+)/(\d+).jpg', views.map_decals_dr2),
    url(r'^decals-dr2-model/(\d+)/(\d+)/(\d+)/(\d+).jpg', views.map_decals_dr2_model),
    url(r'^decals-dr2-resid/(\d+)/(\d+)/(\d+)/(\d+).jpg', views.map_decals_dr2_resid),
    # catalog
    url(r'^decals-dr2/(\d+)/(\d+)/(\d+)/(\d+).cat.json', views.cat_decals_dr2),

    # depth maps
    #url(r'^decam-depth/(\d+)/(\d+)/(\d+)/(\d+).jpg', views.map_decam_depth),

    # DR1k -- COSMOS
    #url(r'^decals-dr1k/(\d+)/(\d+)/(\d+)/(\d+).jpg', views.map_decals_dr1k),

    # DR1j full
    url(r'^decals-dr1j/(\d+)/(\d+)/(\d+)/(\d+).jpg', views.map_decals_dr1j),
    url(r'^decals-model-dr1j/(\d+)/(\d+)/(\d+)/(\d+).jpg', views.map_decals_model_dr1j),
    url(r'^decals-resid-dr1j/(\d+)/(\d+)/(\d+)/(\d+).jpg', views.map_decals_resid_dr1j),

    # catalog
    url(r'^decals-dr1j/(\d+)/(\d+)/(\d+)/(\d+).cat.json', views.cat_decals_dr1j),

    #url(r'^decals-nexp-dr1j/(\d+)/(\d+)/(\d+)/(\d+).jpg', views.map_decals_nexp_dr1j),
    #url(r'^decals-wl/(\d+)/(\d+)/(\d+)/(\d+).jpg', views.map_decals_wl),

    # Cutouts
    url(r'^fits-cutout-decals-dr1', views.fits_cutout_decals_dr1j),
    url(r'^jpeg-cutout-decals-dr1', views.jpeg_cutout_decals_dr1j),

    url(r'^jpeg-cutout-decals-dr2', views.jpeg_cutout_decals_dr2),
    url(r'^fits-cutout-decals-dr2', views.fits_cutout_decals_dr2),

    # NGC objects
    url(r'^ngc/(\d+)/(\d+)/(\d+)/(\d+).cat.json', views.cat_ngc),

    # Virgo cluster catalog (VCC) objects
    #url(r'^vcc/(\d+)/cat.json', views.cat_vcc),

    # Spectroscopy
    url(r'^spec/(\d+)/cat.json', views.cat_spec),

    # Bright stars
    url(r'^bright/(\d+)/cat.json', views.cat_bright),

    # SFD dust map
    url(r'^sfd-tiles/(\d+)/(\d+)/(\d+)/(\d+).jpg', views.map_sfd),

    # Halpha map
    url(r'^halpha-tiles/(\d+)/(\d+)/(\d+)/(\d+).jpg', views.map_halpha),

    # unWISE W1/W2
    url(r'^unwise-w1w2-tiles/(\d+)/(\d+)/(\d+)/(\d+).jpg', views.map_unwise_w1w2),

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
    # CCDs: list of polygons
    url(r'^ccds/', views.ccd_list),

    # Exposures: list of circles
    url(r'^exps/', views.exposure_list),

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

    # fall-through
    url(r'', views.index),
]
