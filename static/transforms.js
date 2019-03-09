function radians(degrees) {
    return degrees * math.pi / 180;
}

function degrees(rad) {
    return rad * 180 / math.pi;
}

/**
* Retrieve a row from a matrix
* @param {Matrix | Array} matrix
* @param {number} index    Zero based row index
* @return {Matrix | Array} Returns the row as a vector
* @source https://github.com/josdejong/mathjs/issues/230
*/
function row(matrix, index) {
    var rows = math.size(matrix).valueOf()[1];
    return math.flatten(math.subset(matrix, math.index(index, math.range(0, rows))));
}

function xyz2radec(telra, teldec, v) {
    // Clockwise rotation around y axis by declination of the tile center
    var decrotate = math.zeros(3, 3);
    var teldec_rad = radians(teldec);
    decrotate.subset(math.index(0, [0, 1, 2]), [math.cos(teldec_rad), 0, -math.sin(teldec_rad)])
    decrotate.subset(math.index(1, [0, 1, 2]), [0, 1, 0])
    decrotate.subset(math.index(2, [0, 1, 2]), [math.sin(teldec_rad), 0, math.cos(teldec_rad)])

    // Counter-clockwise rotation around the z-axis by the right ascension of the tile center
    var rarotate = math.zeros(3,3)
    var telra_rad = radians(telra)
    rarotate.subset(math.index(0, [0, 1, 2]), [math.cos(telra_rad), -math.sin(telra_rad), 0])
    rarotate.subset(math.index(1, [0, 1, 2]), [math.sin(telra_rad), math.cos(telra_rad), 0])
    rarotate.subset(math.index(1, [0, 1, 2]), [0, 0, 1])

    v3 = math.dot(rarotate, math.dot(decrotate, v))
    // cols = math.size(v3)[1]
    // console.log(cols)
    x3 = row(v3, 0)
    y3 = row(v3, 1)
    z3 = row(v3, 2)

    ra_rad = math.atan2(y3, x3)
    dec_rad = (math.pi/2) - math.acos(z3)

    return [ra_rad, dec_rad]
}
