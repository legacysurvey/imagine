
var DesiTileLayer = CatalogOverlay.extend({
    initialize: function(name, pretty, kwargs) {
        CatalogOverlay.prototype.initialize.call(this, name, pretty, kwargs);
        this.color = '#00ff00';
        this.rscale = kwargs['rscale'] || 1.0;
    },

    getLayer: function(result) {
        //return decals_getLayer(result, 10, this.color, this.getTooltipStyle());
        var targetids = result['targetid'];
        var rdlist = result['rd'];
        var bitnames = result['bits'];
        var fiber = result['fiberid'];
        if (bitnames === undefined) {
            // target functions vs tile function
            bitnames = result['name'];
        }

        var circleList = [];
        var clong = map.getCenter().lng;
        var zoom = map.getZoom();
        for (var i=0, len=rdlist.length; i<len; i++) {
            var r = rdlist[i][0];
            var d = rdlist[i][1];
            var lat = dec2lat(d);
            var lng = ra2long_C(r, clong);

            var poptxt = ('RA,Dec ' + r.toFixed(4) + ', ' + d.toFixed(4) + '<br/>' +
                       bitnames[i] + '<br/>' +
                          'Targetid: ' + targetids[i]);
            var popf = function(t, e) {
                popup.setLatLng(e.latlng).setContent(t).openOn(map);
                L.DomEvent.stopPropagation(e);
            };
            var dopop = popf.bind(null, poptxt);

            if (fiber != undefined)
                var txt = 'Fiber ' + fiber[i] + ': ' + bitnames[i];
            else
                var txt = bitnames[i];
            //var txt = '';
            //var bits = bitnames[i].split(', ');
            // var bset = new Set();
            // for (var j=0, blen=bits.length; j<blen; j++) {
            //     var words = bits[j].split('_');
            //     bset.add(words[0]);
            // }
            // //var txt = bitnames[i];
            // var txt = '';
            // for (let b of bset) {
            //     if (txt.length)
            //         txt += ', ';
            //     txt += b;
            // }
            var rscale = this.rscale;
            
            var got = false;
            if (bitnames[i].includes('ELG')) {
                var circ = L.circle([lat, lng], 300. * rscale,
                                    {'color': '#88CCEE', 'fillOpacity':0,
                                     'weight': 3, 'opacity': 0.8});
                //circ.bindTooltip(txt, {permanent:true, interactive:true});
                circ.bindTooltip(txt, {permanent:false, interactive:true});
                circ.on('click', dopop);
                circleList.push(circ);
                got = true;
            }
            if (bitnames[i].includes('QSO')) {
                var circ = L.circle([lat, lng], 500. * rscale,
                                    {'color': 'green', 'fillOpacity':0,
                                     'weight': 3, 'opacity': 0.8});
                //circ.bindTooltip(txt, {permanent:true, interactive:true});
                circ.bindTooltip(txt, {permanent:false, interactive:true});
                circ.on('click', dopop);
                circleList.push(circ);
                got = true;
            }
            if (bitnames[i].includes('LRG')) {
                var circ = L.circle([lat, lng], 400. * rscale,
                                    {'color': 'red', 'fillOpacity':0,
                                     'weight': 3, 'opacity': 0.8});
                //circ.bindTooltip(txt, {permanent:true, interactive:true});
                circ.bindTooltip(txt, {permanent:false, interactive:true});
                circ.on('click', dopop);
                circleList.push(circ);
                got = true;
            }
            if (bitnames[i].includes('MWS')) {
                var circ = L.circle([lat, lng], 600. * rscale,
                                    {'color': 'yellow', 'fillOpacity':0,
                                     'weight': 3, 'opacity': 0.8});
                //circ.bindTooltip(txt, {permanent:true, interactive:true});
                circ.bindTooltip(txt, {permanent:false, interactive:true});
                circ.on('click', dopop);
                circleList.push(circ);
                got = true;
            }
            if (bitnames[i].includes('BGS')) {
                var circ = L.circle([lat, lng], 700. * rscale,
                                    {'color': 'white', 'fillOpacity':0,
                                     'weight': 3, 'opacity': 0.8});
                //circ.bindTooltip(txt, {permanent:true, interactive:true});
                circ.bindTooltip(txt, {permanent:false, interactive:true});
                circ.on('click', dopop);
                circleList.push(circ);
                got = true;
            }
            if (bitnames[i].includes('STD')) {
                var circ = L.circle([lat, lng], 700. * rscale,
                                    {'color': '#CCCCCC', 'fillOpacity':0,
                                     'weight': 3, 'opacity': 0.8});
                //circ.bindTooltip(txt, {permanent:true, interactive:true});
                circ.bindTooltip(txt, {permanent:false, interactive:true});
                circ.on('click', dopop);
                circleList.push(circ);
                got = true;
            }
            if (bitnames[i].includes('SCND')) {
                var circ = L.circle([lat, lng], 700. * rscale,
                                    {'color': 'orange', 'fillOpacity':0,
                                     'weight': 3, 'opacity': 0.8});
                //circ.bindTooltip(txt, {permanent:true, interactive:true});
                circ.bindTooltip(txt, {permanent:false, interactive:true});
                circ.on('click', dopop);
                circleList.push(circ);
                got = true;
            }
            // SKY
            if (!got) {
                var circ = L.circle([lat, lng], 400. * rscale,
                                    {'color': '#888888', 'fillOpacity':0,
                                     'weight': 3, 'opacity': 0.8});
                //circ.bindTooltip(txt, {permanent:true, interactive:true});
                circ.bindTooltip(txt, {permanent:false, interactive:true});
                circ.on('click', dopop);
                circleList.push(circ);
            }
    
            // circ.ra = r;
            // circ.dec = d;
            // //circ.type = typ;
            // circ.fluxes = (fluxes     ? fluxes[i] : {});
            // circ.nobs   = (nobs       ? nobs  [i] : {});
            // circ.targetid = targetids ? targetids[i] : '';
            // circ.on('click', onTargetClick);
            // circleList[i] = circ;
        }
        return L.layerGroup(circleList);
    },

    //getTooltipStyle() {
    //    return { permanent: true, interactive: true,
    //             className: 'tooltipbg', };
    //},
});


var added_desi_tiles = [];

// Overlay tree objects.
var desi_tile_list = [];

var addDesiTile = function(tileid) {
    console.log('addDesiTile('+tileid+')');
    // no duplicates!
    if (added_desi_tiles.includes(tileid)) {
        return;
    }
    added_desi_tiles.push(tileid);
    
    var name = 'desitile-' + tileid;
    var pretty = 'DESI Tile '+tileid;
    var layer = new DesiTileLayer(name, pretty,
        {'url': desitile_url, 'url_args': {'tile': ''+tileid}});
    var group = layer.getGroup();
    group._name = name;
    //overlayTree.push({ label: pretty,
    //                   layer: group });
    var layer = { label: pretty,
                  layer: group };
    desi_tile_list.push(layer);
    map.addLayer(group);
    return layer;
}
                             
