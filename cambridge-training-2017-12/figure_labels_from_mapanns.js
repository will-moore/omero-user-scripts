
// Adds labels to image panels in OMERO.figure
// using Key Value pairs (map annotations) on the images.
//
// To use, open the OMERO.figure file in your browser.
// Select the image panels you want to add labels to.
// Open devtools in Chrome / Firefox and select Console tab.
// Copy the code below into the console.
// This will load map annotations JSON for each selected image and create labels.
// Can observe under the Network tab in devtools to see JSON loaded.


figureModel.getSelected().forEach(function(p){
    var image_id = p.get('imageId');
    var url = WEBINDEX_URL + "api/annotations/?type=map&image=" + image_id;

    $.getJSON(url, function(data){
        data.annotations.forEach(function(a){
            var labels = a.values.map(function(keyValue){
                return {
                    'text': keyValue.join(": "),
                    'size': 4,
                    'position': "top",
                    'color': "000000"
                }
            });
            p.add_labels(labels);
        });
    });
});