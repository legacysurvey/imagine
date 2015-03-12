from django.conf.urls import patterns, include, url

urlpatterns = patterns('map.views',
    # url(r'^image/(\d*)/(\d*)/(\d*).jpg', 'map_image'),
    url(r'^cosmos-grz/(\d+)/(\d+)/(\d+)/(\d+).jpg', 'map_cosmos_grz'),
    # url(r'^cosmos-urz/(\d*)/(\d*)/(\d*).jpg', 'map_cosmos_urz'),

    # Tiles
    url(r'^decals/(\d+)/(\d+)/(\d+)/(\d+).jpg', 'map_decals'),
    url(r'^decals-pr/(\d+)/(\d+)/(\d+)/(\d+).jpg', 'map_decals_pr'),
    url(r'^decals-model/(\d+)/(\d+)/(\d+)/(\d+).jpg', 'map_decals_model'),
    url(r'^decals-model-pr/(\d+)/(\d+)/(\d+)/(\d+).jpg', 'map_decals_model_pr'),
    url(r'^des-stripe82/(\d+)/(\d+)/(\d+)/(\d+).jpg', 'map_des_stripe82'),
    url(r'^des-pr/(\d+)/(\d+)/(\d+)/(\d+).jpg', 'map_des_pr'),

    # "EDR2"
    url(r'^decals-edr2/(\d+)/(\d+)/(\d+)/(\d+).jpg', 'map_decals_edr2'),
    url(r'^decals-model-edr2/(\d+)/(\d+)/(\d+)/(\d+).jpg', 'map_decals_model_edr2'),

    # EDR2 residuals
    url(r'^decals-resid-edr2/(\d+)/(\d+)/(\d+)/(\d+).jpg', 'map_decals_resid_edr2'),

    # EDR3
    url(r'^decals-edr3/(\d+)/(\d+)/(\d+)/(\d+).jpg', 'map_decals_edr3'),
    url(r'^decals-model-edr3/(\d+)/(\d+)/(\d+)/(\d+).jpg', 'map_decals_model_edr3'),

    # EDR3 residuals
    url(r'^decals-resid-edr3/(\d+)/(\d+)/(\d+)/(\d+).jpg', 'map_decals_resid_edr3'),


    # SFD dust map
    url(r'^sfd-tiles/(\d+)/(\d+)/(\d+)/(\d+).jpg', 'map_sfd'),

    ## Cutouts
    url(r'^cutouts/', 'cutouts', name='cutouts'),

    url(r'^cutout_panels/(?P<expnum>\d+)/(?P<extname>[NS]\d{1,2})/', 'cutout_panels', name='cutout_panels'),


    url(r'^cat_plot/', 'cat_plot', name='cat_plot'),

    # Catalogs
    url(r'^decals/(\d+)/(\d+)/(\d+)/(\d+).cat.json', 'cat_decals'),

    url(r'^decals-edr2/(\d+)/(\d+)/(\d+)/(\d+).cat.json', 'cat_decals_edr2'),
    url(r'^decals-edr3/(\d+)/(\d+)/(\d+)/(\d+).cat.json', 'cat_decals_edr3'),

    # brick list of polygons
    url(r'^bricks/', 'brick_list'),
    # CCD list of polygons
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
