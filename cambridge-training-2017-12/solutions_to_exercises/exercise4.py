#-----------------------------------------------------------------------------
#  Copyright (C) 2017 University of Dundee. All rights reserved.
#
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
#  51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
#------------------------------------------------------------------------------

# This script loads the ROIs saved into OMERO and convert them into ImageJ ROIs
# The rois are then added to the roi manager
# Error handling is omitted to ease the reading of the script but this should be added
# if used in production to make sure the services are closed
# Information can be found https://docs.openmicroscopy.org/omero/5.4.1/developers/Java.html

import os
from os import path

from javax.imageio import ImageIO
from java.awt.image import BufferedImage
from java.io import ByteArrayInputStream
from java.lang import Long
from java.lang import String
from java.util import ArrayList
import java


# Omero Dependencies
import omero
from omero.gateway import Gateway
from omero.gateway import LoginCredentials
from omero.gateway import SecurityContext
from omero.gateway.facility import BrowseFacility
from omero.gateway.facility import ROIFacility
from omero.gateway.model import EllipseData
from omero.gateway.model import PointData
from omero.gateway.model import RectangleData
from omero.log import Logger
from omero.log import SimpleLogger
from omero.model import Pixels

from ome.formats.importer import ImportConfig
from ome.formats.importer import OMEROWrapper
from ome.formats.importer import ImportLibrary
from ome.formats.importer import ImportCandidates
from ome.formats.importer.cli import ErrorHandler
from ome.formats.importer.cli import LoggingImportMonitor
import loci.common
from loci.formats.in import DefaultMetadataOptions
from loci.formats.in import MetadataLevel
from ij import IJ, ImagePlus
from ij.gui import OvalRoi, PointRoi, Roi 
from ij.process import ByteProcessor
from ij.plugin.frame import RoiManager


# Setup
# =====

# OMERO Server details
HOST = "outreach.openmicroscopy.org"
PORT = 4064
group_id = "-1"
#  parameters to edit
dataset_id = "21552"
USERNAME = "username"
PASSWORD = "password"

def open_image_plus(HOST, USERNAME, PASSWORD, PORT, group_id, image_id):
    "Open the image using the Bio-Formats Importer"

    options = ""
    options += "location=[OMERO] open=[omero:server="
    options += HOST
    options += "\nuser="
    options += USERNAME
    options += "\nport="
    options += str(PORT)
    options += "\npass="
    options += PASSWORD
    options += "\ngroupID="
    options += group_id
    options += "\niid="
    options += image_id
    options += "]"
    options += " windowless=true "
    IJ.runPlugIn("loci.plugins.LociImporter", options)


def connect_to_omero():
    "Connect to OMERO"

    credentials = LoginCredentials()
    credentials.getServer().setHostname(HOST)
    credentials.getServer().setPort(PORT)
    credentials.getUser().setUsername(USERNAME.strip())
    credentials.getUser().setPassword(PASSWORD.strip())
    simpleLogger = SimpleLogger()
    gateway = Gateway(simpleLogger)
    gateway.connect(credentials)
    return gateway


def get_images(gateway, dataset_id):
    "List all image's ids contained in a Dataset"

    browse = gateway.getFacility(BrowseFacility)
    user = gateway.getLoggedInUser()
    ctx = SecurityContext(user.getGroupId())
    ids = ArrayList(1)
    val = Long(dataset_id)
    ids.add(val)
    return browse.getImagesForDatasets(ctx, ids)


def get_rois(gateway, image_id):
    "List all rois associated to an Image"

    browse = gateway.getFacility(ROIFacility)
    user = gateway.getLoggedInUser()
    ctx = SecurityContext(user.getGroupId())
    return browse.loadROIs(ctx, image_id)


def format_shape(data, ij_shape):
    "Convert settings e.g. color"
    settings = data.getShapeSettings()
    ij_shape.setStrokeColor(settings.getStroke())
    ij_shape.setFillColor(settings.getFill())
    stroke = settings.getStrokeWidth(None)
    if stroke is not None:
        ij_shape.setStrokeWidth(settings.getStrokeWidth(None).getValue())


def convert_rectangle(data):
    "Convert a rectangle into an imageJ rectangle"
    
    shape = Roi(data.getX(), data.getY(), data.getWidth(), data.getHeight())
    format_shape(data, shape)
    return shape


def convert_ellipse(data):
    "Convert an ellipse into an imageJ ellipse"
    width = data.getRadiusX()
    height = data.getRadiusY()
    shape = OvalRoi(data.getX()-width, data.getY()-height, 2*width, 2*height)
    format_shape(data, shape)
    return shape


def convert_point(data):
    "Convert a point into an imageJ point"
    shape = PointRoi(data.getX(), data.getY())
    format_shape(data, shape)
    return shape


def convert_omero_rois_to_ij_rois(rois_results):
    "Convert the omero ROI into imageJ ROI"
   
    output = []
    for roi_result in rois_results:
        rois = roi_result.getROIs()
        for roi in rois:
            iterator = roi.getIterator()
            for s in iterator:
                for shape in s:
                    c = None
                    if isinstance(shape, RectangleData):
                        output.append(convert_rectangle(shape))
                    elif isinstance(shape, EllipseData):
                        output.append(convert_ellipse(shape))
                    elif isinstance(shape, PointData):
                        output.append(convert_point(shape)) 
    return output

# Connect to OMERO
gateway = connect_to_omero()

# Retrieve the images contained in the specified dataset
images = get_images(gateway, dataset_id)

# loop through the images
for image in images:
    print(String.valueOf(image.getId()))
    rois = get_rois(gateway, image.getId())
    open_image_plus(HOST, USERNAME, PASSWORD, PORT, group_id, String.valueOf(image.getId()))
    image = IJ.getImage()
    output = convert_omero_rois_to_ij_rois(rois)
    manager = RoiManager()
    count = 0
    for i in output:
        manager.add(image, i, count)
        count = count+1


gateway.disconnect()