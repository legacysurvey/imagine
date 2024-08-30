{% load static %}

// DESI Footprint
// from gfa-corners.fits from Bailey, 2019-03-18
var gfa_radius = [
    [1.54426530072, 1.5999816327800001, 1.6054123220500001, 1.54995479059],
    [1.54426530072, 1.5999816327800001, 1.6054123220500001, 1.54995479059],
    [1.54426530072, 1.5999816327800001, 1.6054123220500001, 1.54995479059],
    [1.54426530072, 1.5999816327800001, 1.6054123220500001, 1.54995479059],
    [1.54426530072, 1.5999816327800001, 1.6054123220500001, 1.54995479059],
    [1.54426530072, 1.5999816327800001, 1.6054123220500001, 1.54995479059],
    [1.54426530072, 1.5999816327800001, 1.6054123220500001, 1.54995479059],
    [1.54426530072, 1.5999816327800001, 1.6054123220500001, 1.54995479059],
    [1.54426530072, 1.5999816327800001, 1.6054123220500001, 1.54995479059],
    [1.54426530072, 1.5999816327800001, 1.6054123220500001, 1.54995479059]
];
var gfa_phi = [
    [287.31935812, 287.34502698699998, 283.02060759099999, 282.82671929999998],
    [323.31935812, 323.34502698699998, 319.02060759099999, 318.82671929999998],
    [359.31935812, 359.34502698699998, 355.02060759099999, 354.82671929999998],
    [35.319358120399997, 35.345026987399997, 31.020607590600001, 30.826719299699999],
    [71.319358120399997, 71.345026987400004, 67.020607590599994, 66.826719299700002],
    [107.31935812, 107.345026987, 103.020607591, 102.82671929999999],
    [143.31935812, 143.34502698700001, 139.02060759099999, 138.82671930000001],
    [179.31935812, 179.34502698700001, 175.02060759099999, 174.82671930000001],
    [215.31935812, 215.34502698700001, 211.02060759099999, 210.82671930000001],
    [251.31935812, 251.34502698700001, 247.02060759099999, 246.82671930000001]
];

var gfa_names = [
    'GUIDE0', 'FOCUS1', 'GUIDE2', 'GUIDE3', 'FOCUS4',
    'GUIDE5', 'FOCUS6', 'GUIDE7', 'GUIDE8', 'FOCUS9', ];

var desi_radius=1.6274810767584347;

// Commissioning instrument CCDs
//CIW: RA,Dec boundaries relative to boresight (0,0):
var ci_radecs = {'CIW':
                 [[-1.60636765, -1.5335968 , -1.5335968 , -1.60636765],
                  [-0.0503096, -0.0503096,  0.0488675,  0.0488675]],
                 'CIS':
                 [[5.46111024e-02, 5.46093498e-02, -5.30440012e-02, -5.30457037e-02],
                  [-1.60352809, -1.53643771, -1.53643775, -1.60352813]],
                 'CIC':
                 [[-5.68333564e-02, -5.68333564e-02, 5.52042579e-02, 5.52042579e-02],
                  [ 0.03787655, -0.03791358, -0.03791358,  0.03787655]],
                 'CIN':
                 [[-5.46111024e-02, -5.46093498e-02,5.30440012e-02, 5.30457037e-02],
                  [1.60352809, 1.53643771, 1.53643775, 1.60352813]],
                 'CIE':
                 [[1.60636765, 1.5335968 , 1.5335968 , 1.60636765],
                  [ 0.0503096,  0.0503096, -0.0488675, -0.0488675]],
                };

var desiLocationStack = [];

var DesiOverlay = CatalogOverlay.extend({
    ready: function() {
        CatalogOverlay.prototype.ready.call(this);
    },
    overlayAdded: function(e) {
        if (!layerMatchesEvent(this, e)) {
            return;
        }
        this._show = true;

        var latlng;
        if (desiLocationStack.length > 0) { // If a previous DesiOverlay is being displayed
            latlng = desiLocationStack[0];  // set latlng to its location
        } else if (this._got_initial_position) { // If radec is specified by url
            latlng = L.latLng(dec2lat(this.dec), ra2long_C(this.ra, 180))
        } else {
            latlng = map.getCenter();
        }

        this.moveTo(latlng);
        desiLocationStack.push(latlng);
        this._group.addLayer(this._layer);
    },
    overlayRemoved: function(e) {
        CatalogOverlay.prototype.overlayRemoved.call(this, e);
        if (layerMatchesEvent(this, e)) {
            desiLocationStack.pop();
        }
    },
    load: function() {
    },
    getLinkHere: function() {
        return this._url_term + '=' + this.ra.toFixed(4) + ',' + this.dec.toFixed(4);
    },
    initLinkHere: function(val) {
        val = String(val);
        words = val.split(',');
        if (words.length != 2) {
            return;
        }
        var r = Number.parseFloat(words[0]);
        var d = Number.parseFloat(words[1]);
        this.ra = r;
        this.dec = d;
        console.log('Desi Overlay: ra,dec', r, d);
        this._show = true;
        this._got_initial_position = true;
    },
})

var DesiFiberPos = DesiOverlay.extend({
    initialize: function(name, pretty, kwargs) {
        DesiOverlay.prototype.initialize.call(this, name, pretty, kwargs);
        this._layer = L.layerGroup([]);
    },
    moveTo: function(c) {
        var clong = c.lng
        var d0 = lat2dec(c.lat);
        var r0 = long2ra(clong);
        this.ra = r0;
        this.dec = d0;

        if (this._show) {
            // Create worker if worker does not exist
            if (!this._worker) {
                this._worker = new Worker('{% static "desi_worker.js" %}');
                var _this = this;
                this._worker.addEventListener('message', function(e) {
                    var fiberpos = L.layerGroup();
                    // Add fiber outlines
                    var polyline = L.polyline(e.data['multilatlngs'], {color: 'DeepSkyBlue', smoothFactor: 0.5, opacity: 0.2});
                    fiberpos.addLayer(polyline);
                    // Add invisible circles to display fiber number
                    for (var i = 0; i < e.data['hiddenCircles'].length; ++i) {
                        var circ = L.circle([e.data['hiddenCircles'][i][0], e.data['hiddenCircles'][i][1]], { radius: 1500, opacity: 0, fillOpacity: 0 });
                        circ.bindTooltip('Fiber: ' + e.data['hiddenCircles'][i][2].toString(), { permanent: false, interactive: false });
                        fiberpos.addLayer(circ);
                    }
                    // Remove the previous fiberpos layer if exists
                    if (_this._fiberpos) {
                        _this._layer.removeLayer(_this._fiberpos);
                        _this._fiberpos = undefined;
                    }
                    // Discard result if desi footprint is not being displayed
                    if (_this._show) {
                        _this._fiberpos = fiberpos;
                        _this._layer.addLayer(_this._fiberpos);
                    }
                    // Update displayed status
                    _this._status && _this._status.html('');
                }, false);
            }
            // Tell worker to initiate calculation
            this._worker.postMessage([r0, d0, clong]);
            this._status && this._status.html('calculating...');
        }
    },
    overlayRemoved: function(e) {
        DesiOverlay.prototype.overlayRemoved.call(this, e);
        if (layerMatchesEvent(this, e)) {
            if (this._fiberpos) {
                this._layer.removeLayer(this._fiberpos);
                this._fiberpos = undefined;
            }
            this._show = false;
        }
    },
});

var DesiFootprint = DesiOverlay.extend({
    initialize: function(name, pretty, kwargs) {
        DesiOverlay.prototype.initialize.call(this, name, pretty, kwargs);
        this._got_initial_position = false;
        var group = [];
        var clong = 180;
        this._circle = L.circle(L.latLng(dec2lat(0), ra2long_C(0, clong)),
                                arcsecToMeters(desi_radius * 3600.),
                                {color:'yellow', fill:false}); //fillOpacity:0.01});
        group.push(this._circle);
        this._gfa_rds = [];
        this._gfa_label_rds = [];
        this._gfa_labels = [];
        this._petal_rds = [];
        var polys = [];
        var labels = [];
        for (var i=0; i<gfa_radius.length; i++) {
            var ll = [];
            var rd = [];
            var N = gfa_radius[i].length;
            for (var j=0; j<N+1; j++) {
                var phi = gfa_phi[i][j%N] * Math.PI / 180.0;
                var ddec =  gfa_radius[i][j%N] * Math.sin(phi);
                var dra  = -gfa_radius[i][j%N] * Math.cos(phi);
                rd.push([dra, ddec]);
                ll.push([dec2lat(ddec), ra2long_C(dra, clong)]);
            }
            this._gfa_rds.push(rd);
            polys.push(ll);

            var mean_phi = 0.;
            var mean_radius = 0.;
            for (var j=0; j<N; j++) {
                mean_phi += gfa_phi[i][j];
                mean_radius += gfa_radius[i][j];
            }
            mean_phi /= N;
            mean_radius /= N;
            mean_phi *= Math.PI / 180.0;
            var ddec =  mean_radius * Math.sin(mean_phi);
            var dra  = -mean_radius * Math.cos(mean_phi)
            this._gfa_label_rds.push([dra,ddec]);

            var latlng = [dec2lat(ddec), ra2long_C(dra, clong)];
            var circ = L.circle(latlng, 0., {'color':'red', 'opacity':0.,
                                         'fillOpacity':0, 'weight':5});
            circ.bindTooltip(gfa_names[i],
                             {interactive: true, permanent: true,
                              direction: 'center', className: 'gfa-label' });
            this._gfa_labels.push(circ);
            group.push(circ);
        }
        this._gfa = L.polyline(polys, {color: 'magenta'});
        group.push(this._gfa);
        
        this._ci_rds = [];
        polys = [];
        for (var k in ci_radecs) {
            var rrdd = ci_radecs[k];
            var ll = [];
            var rd = [];
            var N = rrdd[0].length;
            for (var j=0; j<N+1; j++) {
                var dra  = rrdd[0][j%N];
                var ddec = rrdd[1][j%N];
                rd.push([dra, ddec]);
                ll.push([dec2lat(ddec), ra2long_C(dra, clong)]);
            }
            this._ci_rds.push(rd);
            polys.push(ll);
        }
        this._ci = L.polyline(polys, {color: 'green'});
        group.push(this._ci);

        var rd = [];
        // central
        var dra = -0.0834; var ddec = 0.0000;
        rd.push([dra, ddec]);
        // outer arc
        dra = -1.6164; ddec = 0.0000;
        var angle1 = Math.atan2(ddec, dra);
        var radius = Math.hypot(dra, ddec);
        dra = -1.2861; ddec = 0.9313;
        var angle2 = Math.atan2(ddec, dra);
        var steps = 10;
        var da = (angle2 - angle1) / (steps - 1);
        for (var j=0; j<steps; j++) {
            angle = angle1 + da * j;
            dra  = radius * Math.cos(angle);
            ddec = radius * Math.sin(angle);
            rd.push([dra, ddec]);
        }
        // central point again -- central arc
        dra = -0.0834; ddec = 0.0576;
        angle1 = Math.atan2(ddec, dra);
        // first point
        dra = -0.0834; ddec = 0.0000;
        radius = Math.hypot(dra, ddec);
        angle2 = Math.PI;
        steps = 10;
        da = (angle2 - angle1) / (steps - 1);
        for (var j=0; j<steps; j++) {
            angle = angle1 + da * j;
            dra  = radius * Math.cos(angle);
            ddec = radius * Math.sin(angle);
            rd.push([dra, ddec]);
        }
        var rds0 = rd;

        var polys = [];
        // Make 10 petal rotated copies
        for (var i=0; i<10; i++) {
            var ll = [];
            var rd = [];
            var angle0 = i * Math.PI / 5.;

            for (var j=0; j<rds0.length; j++) {
                dra  = rds0[j][0];
                ddec = rds0[j][1];
                angle = Math.atan2(ddec, dra);
                angle += angle0;
                radius = Math.hypot(dra, ddec);
                dra  = radius * Math.cos(angle);
                ddec = radius * Math.sin(angle);
                rd.push([dra, ddec]);
                ll.push([dec2lat(ddec), ra2long_C(dra, clong)]);
            }

            this._petal_rds.push(rd);
            polys.push(ll);
        }

        this._petals = L.polyline(polys, {color: 'gray'});
        group.push(this._petals);

        this._layer = L.layerGroup(group);
        //map.on('mapMoved', this.mapMoved.bind(this));
    },
    ready: function() {
        DesiOverlay.prototype.ready.call(this);
        this._gfa.redraw();
    },
    moveTo: function(c) {
        this._circle.setLatLng(c);
        var clong = c.lng;
        var d0 = lat2dec(c.lat);
        var r0 = long2ra(clong);
        this.ra = r0;
        this.dec = d0;
        var cosdec = Math.cos(d0 * Math.PI / 180.0);
        var polys = [];
        for (var i=0; i<this._gfa_rds.length; i++) {
            var ll = [];
            var rd = this._gfa_rds[i];
            var N = rd.length;
            for (var j=0; j<N; j++) {
                ll.push([dec2lat(d0 + rd[j][1]),
                         ra2long_C(r0 + rd[j][0] / cosdec, clong)]);
            }
            polys.push(ll);
        }
        this._gfa.setLatLngs(polys);
        this._gfa.redraw();

        for (var i=0; i<this._gfa_label_rds.length; i++) {
            rd = this._gfa_label_rds[i];
            this._gfa_labels[i].setLatLng([dec2lat(d0 + rd[1]),
                                           ra2long_C(r0 + rd[0] / cosdec, clong)]);
        }

        var polys = [];
        for (var i=0; i<this._ci_rds.length; i++) {
            var ll = [];
            var rd = this._ci_rds[i];
            var N = rd.length;
            for (var j=0; j<N; j++) {
                ll.push([dec2lat(d0 + rd[j][1]),
                         ra2long_C(r0 + rd[j][0] / cosdec, clong)]);
            }
            polys.push(ll);
        }
        this._ci.setLatLngs(polys);
        this._ci.redraw();

        var polys = [];
        for (var i=0; i<this._petal_rds.length; i++) {
            var ll = [];
            var rd = this._petal_rds[i];
            var N = rd.length;
            for (var j=0; j<N; j++) {
                ll.push([dec2lat(d0 + rd[j][1]),
                         ra2long_C(r0 + rd[j][0] / cosdec, clong)]);
            }
            polys.push(ll);
        }
        this._petals.setLatLngs(polys);
        this._petals.redraw();
        
    },
});
