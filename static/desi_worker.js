importScripts("desi-fiber-locations.js");
importScripts("transforms.js");

function getFiberMultiLatLngs(telra, teldec, clong) {
    multilatlngs = []
    for (var i = 0; i < 5000; ++i) { // TODO: Get rid of this magic constant
        var circle = fiberpos_projection[i];
        var radec = xyz2radec(telra, teldec, [circle["xs"], circle["ys"], circle["zs"]])
        ras = radec[0];
        decs = radec[1];
        length = ras.size()[0]
        var latlngs = [];
        for (var j = 0; j < length; ++j) {
            ra = ras.subset(math.index(j));
            dec = decs.subset(math.index(j));
            ra_deg = degrees(ra);
            dec_deg = degrees(dec);
            latlngs.push([dec2lat(dec_deg), ra2long_C(ra_deg, clong)]);
        }
        latlngs.push(latlngs[0]);
        multilatlngs.push(latlngs);
    }
    return multilatlngs;
}

onmessage = function(e) {
    postMessage(getFiberMultiLatLngs(e.data[0], e.data[1], e.data[2]));
}
