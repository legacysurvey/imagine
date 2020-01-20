importScripts("desi-fiber-locations.js");
importScripts("transforms.js");
/*global fiberpos_projection*/

function getFiberMultiLatLngs(telra, teldec, clong) {
    var multilatlngs = [];
    var hiddenCircles = []; // Fomart: [lat, lng, fiber_number]
    var radec = xyz2radec(telra, teldec, [fiberpos_projection["xs"],
                                          fiberpos_projection["ys"],
                                          fiberpos_projection["zs"]]);
    var pointsPerFiber = fiberpos_projection["pointsPerCircle"];
    var totalFibers = 5000;
    for (var i = 0; i < totalFibers; ++i) {
        var start_i = i * pointsPerFiber;
        var m_index = math.index(math.range(start_i, start_i + pointsPerFiber));
        var ras = radec[0].subset(m_index), decs = radec[1].subset(m_index);
        var latlngs = [];
        var centerLat = 0, centerLng = 0;
        for (var j = 0; j < pointsPerFiber; ++j) {
            var ra = ras.subset(math.index(j));
            var dec = decs.subset(math.index(j));
            var ra_deg = degrees(ra);
            var dec_deg = degrees(dec);
            var latlng = [dec2lat(dec_deg), ra2long_C(ra_deg, clong)];
            centerLat += latlng[0];
            centerLng += latlng[1];
            latlngs.push(latlng);
        }
        // Calculate latlng average
        centerLat /= pointsPerFiber;
        centerLng /= pointsPerFiber;
        // Complete the polygon
        latlngs.push(latlngs[0]);
        // Add to return value
        multilatlngs.push(latlngs);
        hiddenCircles.push([centerLat, centerLng, fiberpos_projection["fibers"][parseInt(i)]]);
    }
    return { multilatlngs, hiddenCircles };
}

onmessage = function(e) {
    postMessage(getFiberMultiLatLngs(e.data[0], e.data[1], e.data[2]));
};
