
var DesiTileLayer = CatalogOverlay.extend({
    initialize: function(name, pretty, kwargs) {
        CatalogOverlay.prototype.initialize.call(this, name, pretty, kwargs);
        this.color = '#00ff00';
    },

    getLayer: function(result) {
        //return decals_getLayer(result, 10, this.color, this.getTooltipStyle());
        var targetids = result['targetid'];
        var rdlist = result['rd'];
        var bitnames = result['bits'];

        var circleList = []; //new Array(rdlist.length);
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
            var dopop = function(e) {
                popup.setLatLng(e.latlng).setContent(poptxt).openOn(map);
                e.stopPropagation();
            };

            var txt = '';
            var bits = bitnames[i].split(', ');
            var bset = new Set();
            for (var j=0, blen=bits.length; j<blen; j++) {
                var words = bits[j].split('_');
                bset.add(words[0]);
            }
            //var txt = bitnames[i];
            var txt = '';
            for (let b of bset) {
                if (txt.length)
                    txt += ', ';
                txt += b;
            }
            
            var got = false;
            if (bitnames[i].includes('ELG')) {
                var circ = L.circle([lat, lng], 300.,
                                    {'color': '#88CCEE', 'fillOpacity':0,
                                     'weight': 3, 'opacity': 0.8});
                circ.bindTooltip(txt, {permanent:true, interactive:true});
                circ.on('click', dopop);
                circleList.push(circ);
                got = true;
            }
            if (bitnames[i].includes('QSO')) {
                var circ = L.circle([lat, lng], 500.,
                                    {'color': 'green', 'fillOpacity':0,
                                     'weight': 3, 'opacity': 0.8});
                circ.bindTooltip(txt, {permanent:true, interactive:true});
                circ.on('click', dopop);
                circleList.push(circ);
                got = true;
            }
            if (bitnames[i].includes('LRG')) {
                var circ = L.circle([lat, lng], 400.,
                                    {'color': 'red', 'fillOpacity':0,
                                     'weight': 3, 'opacity': 0.8});
                circ.bindTooltip(txt, {permanent:true, interactive:true});
                circ.on('click', dopop);
                circleList.push(circ);
                got = true;
            }
            if (!got) {
                var circ = L.circle([lat, lng], 600.,
                                    {'color': '#888888', 'fillOpacity':0,
                                     'weight': 3, 'opacity': 0.8});
                circ.bindTooltip(txt, {permanent:true, interactive:true});
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


var addDesiTiles = function() {
  {% for tileid in desitiles %}
    var name = 'desitile-' + '{{tileid}}';
    var pretty = 'DESI Tile {{tileid}}';
    var layer = new DesiTileLayer(name, pretty,
        {'url': desitile_url, 'url_args': {'tile': '{{tileid}}'}});
    var group = layer.getGroup();
    group._name = name;
    overlayTree.push({ label: pretty,
                       layer: group });
    map.addLayer(group);
  {% endfor %}
}
                             
