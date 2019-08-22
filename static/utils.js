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

String.prototype.format = function() {
    var formatted = this;
    for (var i = 0; i < arguments.length; i++) {
        var regexp = new RegExp('\\{'+i+'\\}', 'gi');
        formatted = formatted.replace(regexp, arguments[i]);
    }
    return formatted;
}
