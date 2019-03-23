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
