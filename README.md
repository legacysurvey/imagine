# Imagine Sky Viewer

A web service to allow interactive browsing of data from the DESI
Imaging Legacy Surveys (and other surveys) data releases.

Uses the LeafletJS library on the client side, the Django Python web framework on the server side, and a
whack of code in between.

Running at https://www.legacysurvey.org/viewer


## Running a copy

Dependencies include:

-  astrometry.net
-  tractor
-  legacypipe
-  astropy
-  Django

You will need to create a `viewer/settings.py` file for your site.
There is a `viewer/settings_common.py` file with defaults, and
settings files for a number of sites, as a guide.

## Setting up layers

Each available layer (image layer) and overlay (catalog or markers)
requires some data (not included in this repository).  Many layers
follow the pattern of having:

-  `data/LAYER` contains (symlinks to) the raw imaging data
-  `data/tiles/LAYER` contains pre-rendered JPEG tiles
-  `data/scaled/LAYER` contains scaled-down images

The overlays are less regular in their data layouts, but:

-  Gaia-DR2: we expect `data/gaia-dr2/` to contain healpixed tiles named `chunk-#####.fits`


