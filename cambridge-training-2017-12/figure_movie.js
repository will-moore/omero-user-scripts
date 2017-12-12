
// Creates a Movie layout for selected images
// with rows of panels showing time-points incremented by tIncrement
// and wrapped into multiple rows according to columnCount.
figureModel.panels.getSelected().forEach(p => {
    var j = p.toJSON();
	var left = j.x;
	var top = j.y;
	var columnCount = 10;
    var tIncrement = 2;
	var panelCount = 1;
    for (var t=tIncrement; t<j.sizeT; t+=tIncrement){
        // offset to the right each time we create a new panel
        j.x = left + ((panelCount % columnCount) * j.width * 1.05);
		j.y = top + (parseInt(panelCount / columnCount) * j.height * 1.05);
		panelCount++;
        // Increment T
        j.theT = t;
        // create new panel from json
        figureModel.panels.create(j);
    };
});