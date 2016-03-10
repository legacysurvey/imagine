if __name__ == '__main__':
    import os
    os.environ['DJANGO_SETTINGS_MODULE'] = 'decals.settings'
    import django
    django.setup()
    import cat

from django.shortcuts import render
from django.http import HttpResponse, StreamingHttpResponse

from models import Candidate, Decam

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

    sql = ('SELECT *, ' +#candidate.ra as ra, candidate.dec as dec, ' +
           '-2.5*(log(greatest(1e-3,decam.gflux))-9) as g, ' +
           '-2.5*(log(greatest(1e-3,decam.rflux))-9) as r, ' +
           '-2.5*(log(greatest(1e-3,decam.zflux))-9) as z, ' +
           '-2.5*(log(greatest(1e-3,wise.w1flux))-9) as w1, ' +
           '-2.5*(log(greatest(1e-3,wise.w2flux))-9) as w2, ' +
           '-2.5*(log(greatest(1e-3,wise.w3flux))-9) as w3, ' +
           '-2.5*(log(greatest(1e-3,wise.w4flux))-9) as w4 ' +
           'FROM candidate ' +
           'LEFT OUTER JOIN decam ON (decam.cand_id = candidate.id) ' +
           'LEFT OUTER JOIN wise  ON (wise .cand_id = candidate.id) ' +
           'WHERE (q3c_poly_query(ra, dec, ARRAY[%s,%s,%s,%s,%s,%s,%s,%s]))')
    sql = 'SELECT * FROM (' + sql + ') AS t'

    if q is not None and len(q):
        sql += ' WHERE ' + q

    print('SQL:', sql)
        
    #cat = Decam.objects.raw(sql,
    cat = Candidate.objects.raw(sql,
                                params=[east,south,west,south,west,north,east,north])
    cat = cat[:1000]

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
