from django.conf.urls import patterns, include, url

urlpatterns = patterns('map.views',

    # depth maps
    url(r'^decam-depth/(\d+)/(\d+)/(\d+)/(\d+).jpg', 'map_decam_depth'),

    # DR1k -- COSMOS
    url(r'^decals-dr1k/(\d+)/(\d+)/(\d+)/(\d+).jpg', 'map_decals_dr1k'),

    # DR1j full
    url(r'^decals-dr1j/(\d+)/(\d+)/(\d+)/(\d+).jpg', 'map_decals_dr1j'),
    url(r'^decals-model-dr1j/(\d+)/(\d+)/(\d+)/(\d+).jpg', 'map_decals_model_dr1j'),
    url(r'^decals-resid-dr1j/(\d+)/(\d+)/(\d+)/(\d+).jpg', 'map_decals_resid_dr1j'),

    url(r'^decals-nexp-dr1j/(\d+)/(\d+)/(\d+)/(\d+).jpg', 'map_decals_nexp_dr1j'),

    url(r'^decals-wl/(\d+)/(\d+)/(\d+)/(\d+).jpg', 'map_decals_wl'),

    # Cutouts
    url(r'^fits-cutout-decals-dr1', 'fits_cutout_decals_dr1j'),
    url(r'^jpeg-cutout-decals-dr1', 'jpeg_cutout_decals_dr1j'),

    # NGC objects
    url(r'^ngc/(\d+)/(\d+)/(\d+)/(\d+).cat.json', 'cat_ngc'),

    # Virgo cluster catalog (VCC) objects
    url(r'^vcc/(\d+)/cat.json', 'cat_vcc'),

    # Spectroscopy
    url(r'^spec/(\d+)/cat.json', 'cat_spec'),

    # catalog
    url(r'^decals-dr1j/(\d+)/(\d+)/(\d+)/(\d+).cat.json', 'cat_decals_dr1j'),

    # SFD dust map
    url(r'^sfd-tiles/(\d+)/(\d+)/(\d+)/(\d+).jpg', 'map_sfd'),

    # Halpha map
    url(r'^halpha-tiles/(\d+)/(\d+)/(\d+)/(\d+).jpg', 'map_halpha'),

    # unWISE W1/W2
    url(r'^unwise-w1w2-tiles/(\d+)/(\d+)/(\d+)/(\d+).jpg', 'map_unwise_w1w2'),

    url(r'^unwise-w3w4-tiles/(\d+)/(\d+)/(\d+)/(\d+).jpg', 'map_unwise_w3w4'),

    url(r'^unwise-w1234-tiles/(\d+)/(\d+)/(\d+)/(\d+).jpg', 'map_unwise_w1234'),

    # Cutouts html
    url(r'^cutouts/', 'cutouts', name='cutouts'),
    # Cutouts panel plots
    url(r'^cutout_panels/(?P<expnum>\d+)/(?P<extname>[NS]\d{1,2})/', 'cutout_panels', name='cutout_panels'),
    # Scatterplot of nearby sources for cutouts page
    url(r'^cat_plot/', 'cat_plot', name='cat_plot'),

    # bricks: list of polygons
    url(r'^bricks/', 'brick_list'),
    # CCDs: list of polygons
    url(r'^ccds/', 'ccd_list'),

    # Brick details
    url(r'^brick/(\d{4}[pm]\d{3})', 'brick_detail', name='brick_detail'),
    # this one is here to provide a name for the javascript to refer to.
    url(r'^brick/', 'nil', name='brick_detail_blank'),
    # CCD details
    url(r'^ccd/([\w-]+)', 'ccd_detail', name='ccd_detail'),
    # this one is here to provide a name for the javascript to refer to.
    url(r'^ccd/', 'nil', name='ccd_detail_blank'),

    # fall-through
    url(r'', 'index'),
    )
