
// Switches the x and y coordinates for all selected
// panels in figure, to convert rows -> columns

figureModel.getSelected().forEach(function(p){
    p.set({'x':p.get('y'), 'y': p.get('x')})
});
