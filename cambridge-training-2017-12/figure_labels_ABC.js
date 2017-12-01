
// Add labels A, B, C, etc to selected panels.
// position is 'topleft', but can be 'bottomright', left', 'leftvert', 'right', 'top' etc.

figureModel.getSelected().forEach(function(p, i){
    p.add_labels([{text: String.fromCharCode(65 + i),
    			   size: 14,
    			   position: 'topleft',
    			   color: 'ffffff'}]);
});