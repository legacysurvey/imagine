if __name__ == '__main__':
    import os
    os.environ['DJANGO_SETTINGS_MODULE'] = 'decals.settings'
    import django
    django.setup()
    import cat

from django.shortcuts import render
from django.http import HttpResponse, StreamingHttpResponse

from django.db.models import Avg

from models import Candidate, Decam

# Create your views here.
def sql_box(req):
    import json

    north = float(req.GET['north'])
    south = float(req.GET['south'])
    east  = float(req.GET['east'])
    west  = float(req.GET['west'])

    q = req.GET.get('q', None)

    if east < 0:
        east += 360.
        west += 360.

    # cat = Decam.objects.select_related('cand')
    # cat = cat.extra(select=dict(ra='candidate.ra', dec='candidate.dec'))
    # cat = cat.extra(select=dict(g='-2.5*(log(greatest(1e-3,decam.gflux))-9)', r='-2.5*(log(greatest(1e-3,decam.rflux))-9)', z='-2.5*(log(greatest(1e-3,decam.zflux))-9)'))
    # cat = cat.extra(where=["q3c_poly_query(ra, dec, ARRAY[%s,%s,%s,%s,%s,%s,%s,%s])"],
    #                 params=[east,south,west,south,west,north,east,north])

    # cat = Decam.objects.select_related('cand')
    # cat = cat.extra(select=dict(ra='candidate.ra', dec='candidate.dec'))
    # cat = cat.extra(select=dict(g='-2.5*(log(greatest(1e-3,decam.gflux))-9)', r='-2.5*(log(greatest(1e-3,decam.rflux))-9)', z='-2.5*(log(greatest(1e-3,decam.zflux))-9)'))
    # cat = cat.extra(where=["q3c_poly_query(ra, dec, ARRAY[%s,%s,%s,%s,%s,%s,%s,%s])"],
    #                 params=[east,south,west,south,west,north,east,north])
    #if q is not None and len(q):
    #    cat = cat.extra(where=[q])

    sql = ('SELECT *, candidate.ra as ra, candidate.dec as dec, ' +
           '-2.5*(log(greatest(1e-3,decam.gflux))-9) as g, ' +
           '-2.5*(log(greatest(1e-3,decam.rflux))-9) as r, ' +
           '-2.5*(log(greatest(1e-3,decam.zflux))-9) as z ' +
           'FROM decam LEFT OUTER JOIN candidate ON (decam.cand_id = candidate.id) ' +
           'WHERE (q3c_poly_query(ra, dec, ARRAY[%s,%s,%s,%s,%s,%s,%s,%s]))')
    sql = 'SELECT * FROM (' + sql + ') AS t'

    if q is not None and len(q):
        sql += ' WHERE ' + q

    cat = Decam.objects.raw(sql,
                            params=[east,south,west,south,west,north,east,north])

    cat = cat[:1000]

    #return HttpResponse(json.dumps(dict(rd=[(c.ra, c.dec) for c in cat])),

    return HttpResponse(json.dumps(dict(rd=[(c.ra, c.dec) for c in cat])),
                        content_type='application/json')




if __name__ == '__main__':
    import os
    os.environ['DJANGO_SETTINGS_MODULE'] = 'decals.settings'

    north  = 19.0543
    west   = 139.3825
    east   = 138.9798
    south  = 18.8595

    cat = Decam.objects.select_related('cand')
    cat = cat.extra(select={'ra': 'cand.ra', 'dec': 'cand.dec'}, tables=['cand'])
    cat = cat.extra(where=["q3c_poly_query(ra, dec, ARRAY[%s,%s,%s,%s,%s,%s,%s,%s])"],
                    params=[east,south,west,south,west,north,east,north])
    
    print(cat)
