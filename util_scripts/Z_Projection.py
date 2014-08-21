#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 components/tools/OmeroPy/scripts/omero/util_scripts/Z_Projection.py

-----------------------------------------------------------------------------
  Copyright (C) 2006-2014 University of Dundee. All rights reserved.


  This program is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 2 of the License, or
  (at your option) any later version.
  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License along
  with this program; if not, write to the Free Software Foundation, Inc.,
  51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

------------------------------------------------------------------------------

This script does Z-projection of input images.

"""

import omero
from omero.gateway import BlitzGateway
import omero.scripts as scripts
from omero.rtypes import rlong, rstring, robject, wrap


PROJECTIONS = {
        'Maximum': omero.constants.projection.ProjectionType.MAXIMUMINTENSITY,
        'Mean': omero.constants.projection.ProjectionType.MEANINTENSITY,
        }

def projectImage(conn, image, scriptParams, dataset=None):
    """
    Project a single image here: creating a new image

    @param imageId:             Original image
    """

    projectionService = conn.c.sf.getProjectionService()

    # image = conn.getObject("Image", imageId)
    if dataset is None:
        dataset = image.getDataset()

    tStart = scriptParams["T_Start"] - 1   # UI is 1-based
    tStart = min(tStart, image.getSizeT() - 1)

    tEnd = image.getSizeT() - 1
    if "T_End" in scriptParams:
        tEnd = min(scriptParams["T_End"]-1, tEnd)
        tEnd = max(tEnd, tStart)

    zStart = scriptParams["Z_Start"] - 1
    zStart = min(zStart, image.getSizeZ() - 1)

    zEnd = image.getSizeZ() - 1
    if "Z_End" in scriptParams:
        zEnd = min(scriptParams["Z_End"]-1, zEnd)
        zEnd = max(zEnd, zStart)

    stepping = scriptParams["Every_nth_slice"]
    name = "%s_proj" % image.getName()
    channelList = range(image.getSizeC())

    projection = 'Maximum'

    pixelsId = image.getPixelsId()
    pixelsType = image.getPrimaryPixels().getPixelsType()._obj


    imageId = projectionService.projectPixels(pixelsId,
                                        pixelsType,
                                        PROJECTIONS[projection],
                                        tStart, tEnd,
                                        channelList,
                                        stepping,
                                        zStart, zEnd,
                                        name)

    desc = """Original Image: %s
Original Image ID: %s
Projection type: %s
z-sections: %s-%s
Every nth slice: %s
Time-points: %s-%s
""" % (image.name, image.id, projection, zStart+1, zEnd+1, stepping, tStart+1, tEnd+1 )

    newImg = conn.getObject("Image", imageId)
    newImg.setDescription(desc)
    newImg.save()

    # Link image to dataset
    link = None
    if dataset and dataset.canLink():
        link = omero.model.DatasetImageLinkI()
        link.parent = omero.model.DatasetI(dataset.getId(), False)
        link.child = omero.model.ImageI(imageId, False)
        conn.getUpdateService().saveAndReturnObject(link)

    return imageId


def processImages(conn, scriptParams):
    """

    """

    images = list(conn.getObjects("Image", scriptParams['IDs']))

    dataset = None
    if "New_Dataset_Name" in scriptParams:
        # create new Dataset...
        newDatasetName = scriptParams["New_Dataset_Name"]
        dataset = omero.gateway.DatasetWrapper(conn,
                                               obj=omero.model.DatasetI())
        dataset.setName(rstring(newDatasetName))
        dataset.save()
        # add to parent Project
        parentDs = images[0].getParent()
        project = parentDs is not None and parentDs.getParent() or None
        if project is not None and project.canLink():
            link = omero.model.ProjectDatasetLinkI()
            link.parent = omero.model.ProjectI(project.getId(), False)
            link.child = omero.model.DatasetI(dataset.getId(), False)
            conn.getUpdateService().saveAndReturnObject(link)

    newImages = []
    for img in images:
        newId = projectImage(conn, img, scriptParams, dataset)
        if newId is not None:
            newImages.append(newId)

    return newImages, dataset


def runAsScript():

    dataTypes = [rstring('Image')]

    client = scripts.client(
        'Channel_Offsets.py',
        """Create new Images from existing images, applying an x, y and z \
shift to each channel independently.
See http://www.openmicroscopy.org/site/support/omero4/users/\
client-tutorials/insight/insight-util-scripts.html""",

        scripts.String(
            "Data_Type", optional=False, grouping="1",
            description="Pick Images by 'Image' ID", values=dataTypes, default="Image"),

        scripts.List(
            "IDs", optional=False, grouping="2",
            description="List of Image IDs to "
            "process.").ofType(rlong(0)),

        scripts.String(
            "New_Dataset_Name", grouping="3",
            description="If you want the new image(s) in a new Dataset, "
            "put name here"),

        scripts.String(
            "Z_Projection_Type", optional=False, grouping="4",
            description="Type of Projection", values=wrap(PROJECTIONS.keys()), default="Maximum"),

        scripts.Int(
            "Z_Start", grouping="4.1", default=1, min=1,
            description="Start of Z-projection"),

        scripts.Int(
            "Z_End", grouping="4.2", min=1,
            description="End of Z-projection. Default is last Z-section."),

        scripts.Int(
            "Every_nth_slice", grouping="4.3", min=1, default=1,
            description="Project every nth Z-section"),


        scripts.Int(
            "T_Start", grouping="6.0", default=1, min=1,
            description="Start of time-points to include in Z-projecton"),

        scripts.Int(
            "T_End", grouping="7.0", min=1,
            description="End of time-points to include. Default is last Timepoint."),

        authors=["William Moore", "OME Team"],
        institutions=["University of Dundee"],
    )

    try:
        scriptParams = client.getInputs(unwrap=True)
        print scriptParams

        # wrap client to use the Blitz Gateway
        conn = BlitzGateway(client_obj=client)

        iids, dataset = processImages(conn, scriptParams)

        # Return message, new image and new dataset (if applicable) to the
        # client

        if len(iids) == 0:
            message = "No image created."
        elif len(iids) == 1:
            message = "New image created."
            img = conn.getObject("Image", iids[0])
            if img is not None:
                client.setOutput("Image", robject(img._obj))
        else:
            message = "%s new images created." % len(iids)
            if dataset is None:
                dataset = conn.getObject("Image", iids[0]).getParent()
                if dataset is not None:
                    message += " See Dataset:"
                    client.setOutput("New Dataset", robject(dataset._obj))
        client.setOutput("Message", rstring(message))

    finally:
        client.closeSession()

if __name__ == "__main__":
    runAsScript()
