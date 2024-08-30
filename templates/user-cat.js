var userCatN = 100;

var UserCatalogLayer = CatalogOverlay.extend({
    initialize: function(name, pretty, kwargs) {
        CatalogOverlay.prototype.initialize.call(this, name, pretty, kwargs);
        this.color = '#00ff00';
        this._catname = this._url_args['cat'];
        this._catdata = null;
        this._catindex = 0;
        this._catoffset = 0;
    },

    ready: function() {
        console.log(this._name + ' ready function called (UserCatalogLayer)');
        this._checkbox = getOverlayCheckbox(this._pretty);
        // _checkbox is a jQuery node
        //console.log('checkbox:', this._checkbox);
        var nxt = this._checkbox.next();

        // add a 'next' button after the layer name span
        var nextbutton = L.DomUtil.create('a', 'layer-next');
        var nextbuttonid = this._name + '_next';
        nextbutton.id = nextbuttonid;
        nxt.after(nextbutton);
        nxt.after('&nbsp;');
        // find it with jQuery
        var jbutton = $('#' + nextbuttonid);
        jbutton.attr('href', '#');
        jbutton.click(this.nextObject.bind(this));
        jbutton.html('next');

        // catalog index
        var indx = L.DomUtil.create('span', 'layer-index');
        var indxid = this._name + '_indx';
        indx.id = indxid;
        nxt.after(indx);
        nxt.after('&nbsp;');
        // find it with jQuery
        this._index = $('#' + indxid);
        this._index.html('[' + (this._catoffset + this._catindex) + ']');

        // prev catalog entry
        var prevbutton = L.DomUtil.create('a', 'layer-prev');
        var prevbuttonid = this._name + '_prev';
        prevbutton.id = prevbuttonid;
        nxt.after(prevbutton);
        nxt.after('&nbsp;');
        // find it with jQuery
        var jbutton = $('#' + prevbuttonid);
        jbutton.attr('href', '#');
        jbutton.click(this.prevObject.bind(this));
        jbutton.html('prev');

        // add status span after the layer name span
        var stat = L.DomUtil.create('span', 'layer-status');
        var statid = this._name + '_status';
        stat.id = statid
        nxt.after(stat);
        nxt.after('&nbsp;');
        // find it with jQuery
        this._status = $('#' + statid);

    },

    nextObject: function() {
      console.log('next object for catalog ' + this._catname);
      if (this._catdata != null) {
        this._catindex += 1;
        console.log('catalog index now ', this._catindex);
        if (this._catindex >= this._catdata.length) {
          console.log('index exceeds catalog length: ' + this._catdata.length);
          this._catoffset += this._catdata.length;
          this._catindex = -1;
        } else {
          this._index.html('[' + (this._catoffset + this._catindex) + ']');
          ra  = this._catdata[this._catindex][0];
          dec = this._catdata[this._catindex][1];
          console.log('New RA,Dec ' + ra + ', ' + dec);
          lat = dec2lat(dec);
          lng = ra2long_C(ra, 0);
          map.panTo(L.latLng(lat,lng));
          return;
        }
      }

      // retrieve next chunk.

      var url = L.Util.template(usercat2_url, {
        s: subdomains[0],
        cat: this._catname,
        start: this._catoffset,
        N: userCatN,
      });
      console.log('Loading catalog: ' + this._catname + ' from ' + url);
      $.getJSON(url, this.catLoaded.bind(this, true));
    },

    prevObject: function() {
      console.log('prev object for catalog ' + this._catname);
      if (this._catindex + this._catoffset < 0) {
        // don't go negative
        return;
      }
      if (this._catdata != null) {
        this._catindex -= 1;
        console.log('catalog index now ', this._catindex);
        if (this._catindex < 0) {
          console.log('index negative');
          this._catoffset -= this._catdata.length;
          this._catindex = -1;
        } else {
          this._index.html('[' + (this._catoffset + this._catindex) + ']');
          ra  = this._catdata[this._catindex][0];
          dec = this._catdata[this._catindex][1];
          console.log('New RA,Dec ' + ra + ', ' + dec);
          lat = dec2lat(dec);
          lng = ra2long_C(ra, 0);
          map.panTo(L.latLng(lat,lng));
          return;
        }
      }

      // retrieve prev chunk.
      var url = L.Util.template(usercat2_url, {
        s: subdomains[0],
        cat: this._catname,
        start: this._catoffset,
        N: userCatN,
      });
      console.log('Loading catalog: ' + this._catname + ' from ' + url);
      $.getJSON(url, this.catLoaded.bind(this, false));
    },

    catLoaded: function(nxt, result) {
      console.log('User catalog loaded: ' + this._catname);
      this._catdata = result['rd'];
      if (nxt) {
        this.nextObject();
      } else {
        this._catindex = this._catdata.length;
        this.prevObject();
      }
    },

    getLayer: function(result) {
        return decals_getLayer(result, 10, this.color, this.getTooltipStyle());
    },

    getTooltipStyle() {
        return { permanent: true, interactive: true,
                 className: 'tooltipbg', };
    },
});


var addUserCatalogs = function() {
  {% for cat,name,color in usercatalogs %}
    var name = 'usercatalog-' + '{{name}}';
    var pretty = 'User Catalog {{name}}';
    var usercat = new UserCatalogLayer(name, pretty,
        {'url': usercat_url, 'url_args': {'cat': '{{cat}}'}});
    var color = '{{color}}';
    if (color.length > 0) {
      usercat.color = color;
    }
    var group = usercat.getGroup();
    group._name = name;
    overlayTree.push({ label: pretty,
                       layer: group });
    map.addLayer(group);
  {% endfor %}
}
                             
