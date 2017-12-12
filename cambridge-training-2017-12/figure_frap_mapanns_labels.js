

// To be used as part of the FRAP workflow
// Expects map annotation on each image with key-value pairs
// [theT, intensity]
// for each time-point in the movie.
// This script loads map-annotations for namespace 'ns'
// and creates a label from the Value of the nth key-value pair
// where n = theT for that panel

// NB: This is not the most efficient solution since we load
// the same data many times for panels of the same image, but
// the code is a lot simpler like this.

figureModel.getSelected().forEach(function(p){
    var image_id = p.get('imageId');
    var ns = 'demo.frap_data';
    var url = WEBINDEX_URL + "api/annotations/?type=map&image=" + image_id;
    url += '&ns=' + ns;
    var theT = p.get('theT');

    $.getJSON(url, function(data){
        // Use only the values from the first annotation
        var values = data.annotations[0].values;
        var labels = [{
                'text': "" + parseInt(values[theT][1]),
                'size': 12,
                'position': "topleft",
                'color': "ffffff"
            }]
        p.add_labels(labels);
    });
});