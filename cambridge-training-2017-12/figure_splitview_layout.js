
// Creates a "Split View" layout from selected panels

figureModel.getSelected().forEach(p => {
    var j = p.toJSON();
    for (var c=0; c<j.channels.length; c++){
        // offset to the right each time we create a new panel
        j.x = j.x + (j.width * 1.05);
        // turn all channels off except for the current index
        j.channels.forEach((ch, i) => {
            ch.active = i === c;
        });
        // create new panel from json
        figureModel.panels.create(j);
    };
});