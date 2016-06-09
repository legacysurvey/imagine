from __future__ import print_function

if __name__ == '__main__':
    import os
    os.environ['DJANGO_SETTINGS_MODULE'] = 'decals.settings'
    import django
    django.setup()
    import cat

from django.shortcuts import render
from django.http import HttpResponse, StreamingHttpResponse, HttpResponseRedirect, HttpResponseBadRequest, QueryDict
from django import forms
from django.core.urlresolvers import reverse

from django.views.generic import ListView, DetailView

from models import Candidate, Decam, Photom

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

    # sql = ('SELECT * FROM photom ' +
    #        'LEFT OUTER JOIN candidate ON (candidate.id  = photom.cand_id) ' +
    #        'LEFT OUTER JOIN decam     ON (decam.cand_id = photom.cand_id) ' +
    #        'LEFT OUTER JOIN wise      ON (wise .cand_id = photom.cand_id) ' +
    #        'WHERE (q3c_poly_query(photom.ra, photom.dec, ARRAY[%s,%s,%s,%s,%s,%s,%s,%s]))')
           
    sql = 'SELECT * FROM (' + sql + ') AS t'
    
    if q is not None and len(q):
        sql += ' WHERE ' + q

    print('SQL:', sql)
    #print('Literal', sql.replace('%s', '%f') % (east,south,west,south,west,north,east,north))
    
    #cat = Decam.objects.raw(sql,
    cat = Candidate.objects.raw(sql,
    #cat = Photom.objects.raw(sql,
                             params=[east,south,west,south,west,north,east,north])
    cat = cat[:1000]

    return HttpResponse(json.dumps(dict(rd=[(c.ra, c.dec) for c in cat])),
                        content_type='application/json')

def sql_where(req):
    import json

    q = req.GET.get('q', None)

    # sql = ('SELECT *, ' +
    #        '-2.5*(log(greatest(1e-3,decam.gflux))-9) as g, ' +
    #        '-2.5*(log(greatest(1e-3,decam.rflux))-9) as r, ' +
    #        '-2.5*(log(greatest(1e-3,decam.zflux))-9) as z, ' +
    #        '-2.5*(log(greatest(1e-3,wise.w1flux))-9) as w1, ' +
    #        '-2.5*(log(greatest(1e-3,wise.w2flux))-9) as w2, ' +
    #        '-2.5*(log(greatest(1e-3,wise.w3flux))-9) as w3, ' +
    #        '-2.5*(log(greatest(1e-3,wise.w4flux))-9) as w4 ' +
    #        'FROM candidate ' +
    #        'LEFT OUTER JOIN decam ON (decam.cand_id = candidate.id) ' +
    #        'LEFT OUTER JOIN wise  ON (wise .cand_id = candidate.id)')
    # #sql = 'SELECT * FROM (' + sql + ') AS t'

    #SELECT photom.cand_id as cand_id, photom.ra as ra, photom.dec as dec,g,r,z,w1,w2,w3,w4,gmr,rmz,zmw1 FROM photom ' +
    sql = ('SELECT * FROM photom ' +
           'LEFT OUTER JOIN candidate ON (candidate.id  = photom.cand_id) ' +
           'LEFT OUTER JOIN decam     ON (decam.cand_id = photom.cand_id) ' +
           'LEFT OUTER JOIN wise      ON (wise .cand_id = photom.cand_id)')

    ### FIXME -- parse SQL...?
    q = q.lower().replace('ra', 'photom.ra').replace('dec', 'photom.dec')
    
    if q is not None and len(q):
        sql += ' WHERE ' + q

    print('SQL:', sql)
        
    #cat = Candidate.objects.raw(sql)
    cat = Photom.objects.raw(sql)
    cat = cat[:1000]
    cat = cat.values()

    print('Catalog:', cat)

    #fields = Candidate._meta.get_fields()
    #print('Candidate fields:', fields)

    return HttpResponse(json.dumps(cat),
                        content_type='application/json')


def cone_search(req):
    if 'coord' in req.GET:
        v = CoordSearchCatalogList.as_view()
        return v(req)
    # form = CoordSearchForm(req.GET)
    # 
    #     if form.is_valid():
    #         # Process the data in form.cleaned_data
    #         ra,dec = parse_coord(form.cleaned_data['coord'])
    #         try:
    #             radius = float(form.cleaned_data['radius'])
    #         except:
    #             radius = 0.
    #         print('ra,dec,radius', ra,dec,radius)
    # 
    #         from decals import settings
    #         
    #         ## FIXME -- URL lookup
    #         return HttpResponseRedirect(settings.ROOT_URL +
    #                                     '/catalog_near/?ra=%g&dec=%g&radius=%g' %
    #  (ra, dec, radius))
    else:
        form = CatalogSearchForm()

    return render(req, 'coordsearch.html', {
        'form': form,
        'url': reverse('cat.views.cone_search'),
    })    


        
def parse_ra(rastr):
    try:
        ra = float(rastr)
    except:
        try:
            ra = hmsstring2ra(rastr)
        except:
            raise ValidationError('Failed to parse RA string: "%s" -- allowed formats are decimal degrees or HH:MM:SS' % rastr)
    return ra
        
def parse_dec(decstr):
    try:
        dec = float(decstr)
    except:
        try:
            dec = dmsstring2dec(decstr)
        except:
            raise ValidationError('Failed to parse Dec string: "%s" -- allowed formats are decimal degrees or +-DD:MM:SS' % decstr)
    return dec

def parse_coord(txt):
    words = txt.split()
    if not len(words) == 2:
        raise ValidationError('Need RA and Dec (as two space-separated words)')
    rastr,decstr = words
    ra = parse_ra(rastr)
    dec = parse_dec(decstr)
    return ra,dec

class CoordSearchForm(forms.Form):
    coord = forms.CharField(required=True, validators=[parse_coord],
                            initial='180.0 20.0')
    radius = forms.FloatField(required=False, initial=0.1)

class RaDecSearchForm(forms.Form):
    ra  = forms.FloatField(required=False, validators=[parse_ra])
    dec = forms.FloatField(required=False, validators=[parse_dec])
    radius = forms.FloatField(required=False)

class RaDecBoxSearchForm(forms.Form):
    ralo  = forms.FloatField(required=False, validators=[parse_ra])
    rahi  = forms.FloatField(required=False, validators=[parse_ra])
    declo = forms.FloatField(required=False, validators=[parse_dec])
    dechi = forms.FloatField(required=False, validators=[parse_dec])

#shortNum = forms.NumberInput(attrs={'size': '10'})
shortNum = forms.TextInput(attrs={'size': '10'})

class CatalogSearchForm(CoordSearchForm):
    g_gt = forms.FloatField(required=False, widget=shortNum)
    g_lt = forms.FloatField(required=False, widget=shortNum)

    r_gt = forms.FloatField(required=False, widget=shortNum)
    r_lt = forms.FloatField(required=False, widget=shortNum)

    z_gt = forms.FloatField(required=False, widget=shortNum)
    z_lt = forms.FloatField(required=False, widget=shortNum)

    w1_gt = forms.FloatField(required=False, widget=shortNum)
    w1_lt = forms.FloatField(required=False, widget=shortNum)

    gmr_gt = forms.FloatField(required=False, widget=shortNum)
    gmr_lt = forms.FloatField(required=False, widget=shortNum)

    rmz_gt = forms.FloatField(required=False, widget=shortNum)
    rmz_lt = forms.FloatField(required=False, widget=shortNum)
    
    zmw1_gt = forms.FloatField(required=False, widget=shortNum)
    zmw1_lt = forms.FloatField(required=False, widget=shortNum)
    
class CoordSearchCatalogList(ListView):
    template_name = 'cat_list.html'
    paginate_by = 20
    model = Photom

    # def get(self, req, *args, **kwargs):
    #     if 'coord' in req.GET:
    #         form = CoordSearchForm(req.GET)
    #         if form.is_valid():
    #             # Process the data in form.cleaned_data
    #             ra,dec = parse_coord(form.cleaned_data['coord'])
    #             try:
    #                 radius = float(form.cleaned_data['radius'])
    #             except:
    #                 radius = 0.
    #             print('ra,dec,radius', ra,dec,radius)
    #             return self.as_view

    def get_queryset(self):
        req = self.request
        #form = RaDecSearchForm(req.GET)
        #form = CoordSearchForm(req.GET)
        form = CatalogSearchForm(req.GET)

        if not form.is_valid():
            return []
        ra,dec = parse_coord(form.cleaned_data['coord'])
        # ra  = form.cleaned_data['ra']
        # if ra is None:
        #     ra = 0.
        # dec = form.cleaned_data['dec']
        # if dec is None:
        #     dec = 0
        rad = form.cleaned_data['radius']
        if rad is None:
            rad = 0.
        rad = max(0., rad)
        # 1 degree max!
        rad = min(rad, 1.)
        
        print('q3c radial query:', ra, dec, rad)
        cat = Photom.objects.extra(where=['q3c_radial_query(ra, dec, %.4f, %.4f, %g)' %
                                          (ra, dec, rad)])

        for k in ['g', 'r', 'z', 'w1', 'gmr', 'rmz', 'zmw1']:
            gt = form.cleaned_data[k + '_gt']
            lt = form.cleaned_data[k + '_lt']
            print('Limits for', k, ':', gt, lt)
            if gt is not None:
                cat = cat.filter(**{ k+'__gt': gt})
            if lt is not None:
                cat = cat.filter(**{ k+'__lt': lt})
        
        # g_gt = form.cleaned_data['g_gt']
        # g_lt = form.cleaned_data['g_lt']
        # print('g band limits', g_lt, g_gt)
        # if g_gt is not None:
        #     cat = cat.filter(g__gt=g_gt)
        # if g_lt is not None:
        #     cat = cat.filter(g__lt=g_lt)
        # 
        # r_gt = form.cleaned_data['r_gt']
        # r_lt = form.cleaned_data['r_lt']
        # print('r band limits', r_lt, r_gt)
        # if r_gt is not None:
        #     cat = cat.filter(r__gt=r_gt)
        # if r_lt is not None:
        #     cat = cat.filter(r__lt=r_lt)
        # 
        # z_gt = form.cleaned_data['z_gt']
        # z_lt = form.cleaned_data['z_lt']
        # print('z band limits', z_lt, z_gt)
        # if z_gt is not None:
        #     cat = cat.filter(z__gt=z_gt)
        # if z_lt is not None:
        #     cat = cat.filter(z__lt=z_lt)


            
        print('Got:', cat)
        return cat
    
    def get_context_data(self, **kwargs):
        from decals import settings

        context = super(CoordSearchCatalogList, self).get_context_data(**kwargs)
        context.update(root_url=settings.ROOT_URL,
                       #gtltbands = ['g','r','z','w1']
        )
        req = self.request
        args = req.GET.copy()
        args.pop('page', None)
        pager = context.get('paginator')
        context['total_items'] = pager.count
        #context['myurl'] = req.path + '?' + args.urlencode()
        form = CatalogSearchForm(req.GET)
        form.is_valid()
        ra,dec = parse_coord(form.cleaned_data['coord'])
        context['ra'] = ra
        context['dec'] = dec
        rad = form.cleaned_data['radius']
        rad = max(0., rad)
        # 1 degree max!
        rad = min(rad, 1.)
        context['radius'] = rad
        # context['ra'] = args.pop('ra', [0])[0]
        # context['dec'] = args.pop('dec', [0])[0]
        # context['radius'] = args.pop('radius', [0])[0]
        # ??
        #context['version'] = args.pop('version', ['1'])[0]
        return context

if __name__ == '__main__':
    import os
    import sys
    #os.environ['DJANGO_SETTINGS_MODULE'] = 'decals.settings'
    #django.setup()

    class duck(object):
        pass

    req = duck()
    req.META = dict()
    req.GET = dict()

    req.GET['q'] = 'ra between 0 and 0.03 and dec between 0 and 0.03'
    r = sql_where(req)

    # sys.exit(0)

    north  = 19.0543
    west   = 139.3825
    east   = 138.9798
    south  = 18.8595

    req.GET.update(north=north, south=south, east=east, west=west)

    req.GET.update(q='rflux > 100')
    
    r = sql_box(req)

    print('Got', r)
    
    sys.exit(0)
    
    cat = Decam.objects.select_related('cand')
    cat = cat.extra(select={'ra': 'cand.ra', 'dec': 'cand.dec'}, tables=['cand'])
    cat = cat.extra(where=["q3c_poly_query(ra, dec, ARRAY[%s,%s,%s,%s,%s,%s,%s,%s])"],
                    params=[east,south,west,south,west,north,east,north])
    
    print(cat)
