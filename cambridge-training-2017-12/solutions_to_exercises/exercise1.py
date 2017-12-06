# Add the following import at the top of the files
from omero.model import DatasetAnnotationLinkI
from omero.model import DatasetI
from omero.gateway.model import TagAnnotationData

# Insert the followig lines after the comment Exercise 1 changes to be added here
tag = TagAnnotationData("new tag 2")
tag.setTagDescription("new tag 2")

link = DatasetAnnotationLinkI()
link.setChild(tag.asAnnotation())
link.setParent(DatasetI(d.getId(), False))
dm.saveAndReturnObject(ctx, link)
