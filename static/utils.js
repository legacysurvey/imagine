function latlong_is_ngc(latlng) {
    ra = long2ra(latlng.lng);
    dec = lat2dec(latlng.lat);
    //console.log('tile ra,dec: ' + ra + ', ' + dec);
    ux = Math.cos(ra * Math.PI / 180.0) * Math.cos(dec * Math.PI / 180.0);
    uy = Math.sin(ra * Math.PI / 180.0) * Math.cos(dec * Math.PI / 180.0);
    uz = Math.sin(dec * Math.PI / 180.0);
    // var galactic_z_vector = [-0.86766615, -0.19807637, 0.45598378];
    gx = -0.86766615;
    gy = -0.19807637;
    gz =  0.45598378;
    gdot = ux * gx + uy * gy + uz * gz;
    return (gdot >= 0);
}

function long2ra(lng) {
    var ra = 180. - lng;
    while (ra < 0) {
        ra += 360.;
    }
    while (ra > 360) {
        ra -= 360.;
    }
    return ra;
}

function wrap_long(lng, clong) {
    while (lng < clong-180) {
        lng += 360;
    }
    while (lng > clong+180) {
        lng -= 360;
    }
    return lng;
}

function ra2long_C(ra, clong) {
    var lng = 180 - ra;
    lng = wrap_long(lng, clong);
    return lng;
}

function dec2lat(dec) {
    return dec;
}
function lat2dec(lat) {
    return lat;
}

function parameterizeDec(dec) {
    // Accepts a number dec, returns a string
    // If dec is positive/zero, append 'p' to the front, otherwise append 'm'
    var decStr = Math.abs(dec).toString();
    return dec >= 0 ? 'p' + decStr : 'm' + decStr;
}

function disableMouseEventPropagation(element) {
    let container = element.getContainer();
    L.DomEvent
        .disableClickPropagation(container)
        .disableScrollPropagation(container);
}
