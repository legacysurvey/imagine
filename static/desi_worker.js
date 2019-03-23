importScripts("desi-fiber-locations.js");
importScripts("transforms.js");

function getFiberMultiLatLngs(telra, teldec, clong) {
    multilatlngs = [];
    var radec = xyz2radec(telra, teldec, [fiberpos_projection["xs"],
                                          fiberpos_projection["ys"],
                                          fiberpos_projection["zs"]]);
    var pointsPerFiber = fiberpos_projection["pointsPerCircle"];
    var totalFibers = 5000;
    for (var i = 0; i < totalFibers; ++i) {
        var start_i = i * pointsPerFiber;
        var m_index = math.index(math.range(start_i, start_i + pointsPerFiber));
        var ras = radec[0].subset(m_index);
        var decs = radec[1].subset(m_index);
        var latlngs = [];
        for (var j = 0; j < pointsPerFiber; ++j) {
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
