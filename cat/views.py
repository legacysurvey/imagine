from django.shortcuts import render
from django.http import HttpResponse, StreamingHttpResponse

from models import Candidate

# Create your views here.
def sql_box(req):
    import json

    north = float(req.GET['north'])
    south = float(req.GET['south'])
    east  = float(req.GET['east'])
    west  = float(req.GET['west'])

    if east < 0:
        east += 360.
        west += 360.

    #cat = Candidate.objects.extra(where=["q3c_poly_query(ra, dec, ((%f,%f),(%f,%f),(%f,%f),(%f,%f)))" %
    #                                     (east,south,west,south,west,north,east,north)])

    cat = Candidate.objects.extra(where=["q3c_poly_query(ra, dec, ARRAY[%s,%s,%s,%s,%s,%s,%s,%s])"],
                                         params=[east,south,west,south,west,north,east,north])

    #cat = Candidate.objects.extra(where=["q3c_poly_query(ra, dec, ARRAY[%f,%f,%f,%f,%f,%f,%f,%f])" %
    #                                     (east,south,west,south,west,north,east,north)])

    #cat = Candidate.objects.extra(where=["q3c_poly_query(ra, dec, ARRAY[CAST(%s AS double precision),CAST(%s AS double precision),CAST(%s AS double precision),CAST(%s AS double precision),CAST(%s AS double precision),CAST(%s AS double precision),CAST(%s AS double precision),CAST(%s AS double precision)])"],
    # params=[east,south,west,south,west,north,east,north])

    #cat = Candidate.objects.extra(where=["public.q3c_poly_query(ra, dec, ARRAY[CAST(%s AS double precision),CAST(%s AS double precision),CAST(%s AS double precision),CAST(%s AS double precision),CAST(%s AS double precision),CAST(%s AS double precision),CAST(%s AS double precision),CAST(%s AS double precision)])"],
    # params=[east,south,west,south,west,north,east,north])
                                         

    #cat = Candidate.objects.extra(where=["q3c_poly_query(ra, dec, %s)"],
    #                              params=[ ((east,south),(west,south), (west, north), (east, north)) ])
                                  #params=[[east, south, west, south, west, north, east, north]])
                                  #params=['{%f, %f, %f, %f, %f, %f, %f, %f}' %
                                  #(east, south, west, south, west, north, east, north)])

    print('Cat:', cat.count())

    # SELECT * FROM mytable WHERE
    # q3c_poly_query(ra, dec, '{0, 0, 2, 0, 2, 1, 0, 1}');

    return HttpResponse(json.dumps(dict(rd=[(c.ra, c.dec) for c in cat])),
                        content_type='application/json')
