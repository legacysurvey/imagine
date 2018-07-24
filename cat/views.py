from __future__ import print_function

if __name__ == '__main__':
    import os
    os.environ['DJANGO_SETTINGS_MODULE'] = 'viewer.settings'
    import django
    django.setup()
    import cat

import os
from django.shortcuts import render
from django.http import HttpResponse, StreamingHttpResponse, HttpResponseRedirect, HttpResponseBadRequest, QueryDict
from django import forms
try:
    from django.core.urlresolvers import reverse
except:
    # django-2.0
    from django.urls import reverse
    
from django.views.generic import ListView, DetailView

from cat.models import Bricks, Tractor

from map.views import index, send_file

from astrometry.util.ttime import Time

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

    sql = ('SELECT id, ra, dec, type, g, r, z, w1, w2, w3, w4 ' +
           'FROM tractor ' +
           'WHERE (q3c_poly_query(ra, dec, ARRAY[%s,%s,%s,%s,%s,%s,%s,%s]))')

    if q is not None and len(q):
        sql += ' AND ' + q

    print('SQL:', sql, '\nParams:', [east,south,west,south,west,north,east,north])
    #print('Literal', sql.replace('%s', '%f') % (east,south,west,south,west,north,east,north))
    cat = Tractor.objects.raw(sql,
                              params=[east,south,west,south,west,north,east,north])
    #print('Got', len(cat), 'results')
    cat = cat[:1000]

    return HttpResponse(json.dumps(dict(rd=[(c.ra, c.dec) for c in cat])),
                        content_type='application/json')

# def sql_where(req):
#     import json
# 
#     q = req.GET.get('q', None)
# 
#     # sql = ('SELECT *, ' +
#     #        '-2.5*(log(greatest(1e-3,decam.gflux))-9) as g, ' +
#     #        '-2.5*(log(greatest(1e-3,decam.rflux))-9) as r, ' +
#     #        '-2.5*(log(greatest(1e-3,decam.zflux))-9) as z, ' +
#     #        '-2.5*(log(greatest(1e-3,wise.w1flux))-9) as w1, ' +
#     #        '-2.5*(log(greatest(1e-3,wise.w2flux))-9) as w2, ' +
#     #        '-2.5*(log(greatest(1e-3,wise.w3flux))-9) as w3, ' +
#     #        '-2.5*(log(greatest(1e-3,wise.w4flux))-9) as w4 ' +
#     #        'FROM candidate ' +
#     #        'LEFT OUTER JOIN decam ON (decam.cand_id = candidate.id) ' +
#     #        'LEFT OUTER JOIN wise  ON (wise .cand_id = candidate.id)')
#     # #sql = 'SELECT * FROM (' + sql + ') AS t'
# 
#     #SELECT photom.cand_id as cand_id, photom.ra as ra, photom.dec as dec,g,r,z,w1,w2,w3,w4,gmr,rmz,zmw1 FROM photom ' +
#     sql = ('SELECT * FROM photom ' +
#            'LEFT OUTER JOIN candidate ON (candidate.id  = photom.cand_id) ' +
#            'LEFT OUTER JOIN decam     ON (decam.cand_id = photom.cand_id) ' +
#            'LEFT OUTER JOIN wise      ON (wise .cand_id = photom.cand_id)')
# 
#     ### FIXME -- parse SQL...?
#     q = q.lower().replace('ra', 'photom.ra').replace('dec', 'photom.dec')
#     
#     if q is not None and len(q):
#         sql += ' WHERE ' + q
# 
#     print('SQL:', sql)
#         
#     #cat = Candidate.objects.raw(sql)
#     cat = Photom.objects.raw(sql)
#     cat = cat[:1000]
#     cat = cat.values()
# 
#     print('Catalog:', cat)
# 
#     #fields = Candidate._meta.get_fields()
#     #print('Candidate fields:', fields)
# 
#     return HttpResponse(json.dumps(cat),
#                         content_type='application/json')


def cat_search(req):
    if 'coord' in req.GET:
        v = CatalogSearchList.as_view()
        return v(req)
    else:
        form = CatalogSearchForm()

    return render(req, 'cat_search.html', {
        'form': form,
        'url': reverse(cat_search),
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

# class RaDecSearchForm(forms.Form):
#     ra  = forms.FloatField(required=False, validators=[parse_ra])
#     dec = forms.FloatField(required=False, validators=[parse_dec])
#     radius = forms.FloatField(required=False)
# 
# class RaDecBoxSearchForm(forms.Form):
#     ralo  = forms.FloatField(required=False, validators=[parse_ra])
#     rahi  = forms.FloatField(required=False, validators=[parse_ra])
#     declo = forms.FloatField(required=False, validators=[parse_dec])
#     dechi = forms.FloatField(required=False, validators=[parse_dec])

#shortNum = forms.NumberInput(attrs={'size': '10'})
shortNum = forms.TextInput(attrs={'size': '10'})

class CatalogSearchForm(CoordSearchForm):

    spatial_choices = (('allsky', 'All Sky'),
                       ('cone', 'Cone Search'),
                       )

    spatial = forms.ChoiceField(widget=forms.RadioSelect,
                                choices=spatial_choices, initial='allsky',
                                required=True)

    type_choices = (('PSF', 'PSF'),
                    ('SIMP', 'SIMP'),
                    ('DEV', 'DEV'),
                    ('EXP', 'EXP'),
                    ('COMP', 'COMP'))
    sourcetypes = forms.MultipleChoiceField(choices=type_choices, required=False,
                                            widget=forms.CheckboxSelectMultiple)
    
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

    # from http://stackoverflow.com/questions/6766994/in-a-django-form-how-do-i-render-a-radio-button-so-that-the-choices-are-separat
    def spatial_choices(self):
        field = self['spatial']
        widget = field.field.widget
        attrs = {}
        auto_id = field.auto_id
        if auto_id and 'id' not in widget.attrs:
            attrs['id'] = auto_id
        name = field.html_name
        return widget.get_renderer(name, field.value(), attrs=attrs)

    def sourcetypes_choices(self):
        field = self['sourcetypes']
        widget = field.field.widget
        attrs = {}
        auto_id = field.auto_id
        if auto_id and 'id' not in widget.attrs:
            attrs['id'] = auto_id
        name = field.html_name
        return widget.get_renderer(name, field.value(), attrs=attrs)

    
class CatalogSearchList(ListView):
    template_name = 'cat_list.html'
    paginate_by = 20
    model = Tractor

    def __init__(self, *args, **kwargs):
        super(CatalogSearchList, self).__init__(*args, **kwargs)
        self.querydesc = ''
        self.form = None
        self.radecradius = None

    def get_queryset(self):
        print('get_queryset called')
        t0 = Time()

        req = self.request
        self.form = CatalogSearchForm(req.GET)

        if not self.form.is_valid():
            print('FORM NOT VALID!')
            return []

        desc = ''

        spatial = str(self.form.cleaned_data['spatial'])
        print('Spatial search type: "%s"' % spatial)
        print('type', type(spatial))

        if spatial == 'cone':
            ra,dec = parse_coord(self.form.cleaned_data['coord'])
            rad = self.form.cleaned_data['radius']
            if rad is None:
                rad = 0.
            rad = max(0., rad)
            # 1 degree max!
            # rad = min(rad, 1.)
            self.radecradius = (ra, dec, rad)
            print('q3c radial query:', ra, dec, rad)
            cat = Tractor.objects.extra(where=['q3c_radial_query(tractor.ra, tractor.dec, %.4f, %.4f, %g)'
                                              % (ra, dec, rad)])
            desc += 'near RA,Dec = (%.4f, %.4f) radius %f degrees' % (ra, dec, rad)

        elif spatial == 'allsky':
            cat = Tractor.objects.all()
            desc += 'all sky'
        else:
            print('Invalid spatial type "%s"' % spatial)
            return []

        terms = []

        types = self.form.cleaned_data['sourcetypes']
        print('Search for types:', types)

        if len(types):
            tt = []
            for t in types:
                if len(t) == 3:
                    t = t + ' '
                tt.append(str(t))

            if len(tt) == 1:
                terms.append('Type is %s' % tt[0])
                cat = cat.filter(type=tt[0])
            else:
                terms.append('Type in %s' % tt)
                cat = cat.filter(type__in=tt)

        for k in ['g', 'r', 'z', 'w1']: #, 'gmr', 'rmz', 'zmw1']:
            gt = self.form.cleaned_data[k + '_gt']
            lt = self.form.cleaned_data[k + '_lt']
            #print('Limits for', k, ':', gt, lt)
            if gt is not None:
                cat = cat.filter(**{ k+'__gt': gt})
            if lt is not None:
                cat = cat.filter(**{ k+'__lt': lt})

            if gt is not None and lt is not None:
                terms.append(k + ' between %g and %g' % (gt, lt))
            elif gt is not None:
                terms.append(k + ' > %g' % gt)
            elif lt is not None:
                terms.append(k + ' < %g' % lt)

        for k in ['gmr', 'rmz', 'zmw1']:
            gt = self.form.cleaned_data[k + '_gt']
            lt = self.form.cleaned_data[k + '_lt']

            k1,k2 = k.split('m')

            # DR2 -> DR3 -- "gmr" -> "g_r"
            if k == 'gmr':
                dbk = 'g_r'
                if gt is not None:
                    cat = cat.filter(**{ dbk+'__gt': gt})
                if lt is not None:
                    cat = cat.filter(**{ dbk+'__lt': lt})
            else:
                if gt is not None:
                    cat = cat.extra(where=['(%s - %s) > %f' % (k1, k2, gt)])
                if lt is not None:
                    cat = cat.extra(where=['(%s - %s) < %f' % (k1, k2, lt)])

            k = '(%s-%s)' % (k1,k2)
            if gt is not None and lt is not None:
                terms.append(k + ' between %g and %g' % (gt, lt))
            elif gt is not None:
                terms.append(k + ' > %g' % gt)
            elif lt is not None:
                terms.append(k + ' < %g' % lt)


        if len(terms):
            desc += ' where ' + ' and '.join(terms)

        cat = cat[:1000]

        self.querydesc = desc
        #print('Got:', cat.count(), 'hits')

        print('SQL:', cat.query)

        print('Set query description:', desc)
        print('Finished get_queryset in', Time()-t0)
        
        return cat
    
    def get_context_data(self, **kwargs):
        print('get_context_data called')
        t0 = Time()

        from viewer import settings

        print('Using query description:', self.querydesc)

        context = super(CatalogSearchList, self).get_context_data(**kwargs)
        print('Got context data', context, 'in', Time()-t0)
        context.update(root_url=settings.ROOT_URL,
                       search_description=self.querydesc,
                       )
        req = self.request
        args = req.GET.copy()
        args.pop('page', None)

        qstring = '?' + '&'.join(['%s=%s' % (k,v)
                                  for k,v in args.items() if len(v)])

        context['myurl'] = req.path + qstring

        context['fitsurl'] = reverse(fits_results) + qstring
        context['viewurl'] = reverse(viewer_results) + qstring

        pager = context.get('paginator')
        context['total_items'] = pager.count

        print('Done updating context:', Time()-t0)
        return context


def catalog_to_fits(cat):
    from astrometry.util.fits import fits_table
    import numpy as np

    cols = ['ra','dec','g','r','z','w1','w2','w3','w4',
            'brickid', 'brickname', 'objid', 'type',]
    values = cat.values_list(*cols)

    def convert_nan(x):
        if x is None:
            return np.nan
        return x

    T = fits_table()
    for i,c in enumerate(cols):
        v = values[0][i]
        convert = None
        if isinstance(v, unicode):
            convert = str
        if isinstance(v, float):
            convert = convert_nan
        #print('Type of column', c, 'is', type(v), 'eg', v)
        cname = c
        if convert is None:
            T.set(cname, np.array([v[i] for v in values]))
        else:
            T.set(cname, np.array([convert(v[i]) for v in values]))

    return T

def fits_results(req):
    import tempfile

    search = CatalogSearchList()
    search.request = req
    cat = search.get_queryset()
    T = catalog_to_fits(cat)

    f,tmpfn = tempfile.mkstemp(suffix='.fits')
    os.close(f)
    os.unlink(tmpfn)
    T.writeto(tmpfn)
    return send_file(tmpfn, 'image/fits', unlink=True, filename='decals-dr3-query.fits')

def viewer_results(req):
    import tempfile
    from viewer import settings

    search = CatalogSearchList()
    search.request = req
    cat = search.get_queryset()
    T = catalog_to_fits(cat)

    dirnm = settings.USER_QUERY_DIR
    if not os.path.exists(dirnm):
        try:
            os.makedirs(dirnm)
        except:
            pass
    f,tmpfn = tempfile.mkstemp(suffix='.fits', dir=dirnm)
    os.close(f)
    os.unlink(tmpfn)
    T.writeto(tmpfn)
    print('Wrote', tmpfn)

    tmpfn = tmpfn.replace(dirnm, '').replace('.fits', '')
    if tmpfn.startswith('/'):
        tmpfn = tmpfn[1:]

    # if search.radecradius is None:
    #     # arbitrarily center on one point...?
    #     ra,dec = T.ra[0], T.dec[0]
    # else:
    #     ra,dec,nil = search.radecradius

    ra,dec = T.ra[0], T.dec[0]

    return HttpResponseRedirect(reverse(index) +
                                '?ra=%.4f&dec=%.4f&catalog=%s' % (ra, dec, tmpfn))

if __name__ == '__main__':
    import os
    import sys
    #os.environ['DJANGO_SETTINGS_MODULE'] = 'viewer.settings'
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
