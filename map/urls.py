from django.conf.urls import patterns, include, url

urlpatterns = patterns('map.views',
    # DR1j
    url(r'^decals-dr1j-edr/(\d+)/(\d+)/(\d+)/(\d+).jpg', 'map_decals_dr1j_edr'),
    url(r'^decals-model-dr1j-edr/(\d+)/(\d+)/(\d+)/(\d+).jpg', 'map_decals_model_dr1j_edr'),
    url(r'^decals-resid-dr1j-edr/(\d+)/(\d+)/(\d+)/(\d+).jpg', 'map_decals_resid_dr1j_edr'),
    # catalog
    url(r'^decals-dr1j/(\d+)/(\d+)/(\d+)/(\d+).cat.json', 'cat_decals_dr1j'),

    # SFD dust map
    url(r'^sfd-tiles/(\d+)/(\d+)/(\d+)/(\d+).jpg', 'map_sfd'),

    # unWISE W1/W2
    url(r'^unwise-w1w2-tiles/(\d+)/(\d+)/(\d+)/(\d+).jpg', 'map_unwise_w1w2'),

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
