# -----------------------------------------------------------------------------
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
# ------------------------------------------------------------------------------

# This script downloads a file an open it in ImageJ using Bio-Formats exporter
# Error handling is omitted to ease the reading of the script but this
# should be added if used in production to make sure the services are closed
# Information can be found at
# https://docs.openmicroscopy.org/omero/5.4.1/developers/Java.html

import tempfile
import shutil

from java.lang import Float, Long
from java.lang import String
from java.lang.reflect import Array
import java


# Omero Dependencies
import omero
from omero.gateway import Gateway
from omero.gateway import LoginCredentials
from omero.gateway import SecurityContext
from omero.gateway.facility import TransferFacility
from omero.log import Logger
from omero.log import SimpleLogger

from ij import IJ, ImagePlus
from ij.plugin.frame import RoiManager


# Setup
# =====

# OMERO Server details
HOST = "outreach.openmicroscopy.org"
PORT = 4064
group_id = "-1"
#  parameters to edit
image_id = "1001"
USERNAME = "username"
PASSWORD = "password"


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


def download_image(gateway, image_id, path):
    "Download the files composing the image"

    transfer = gateway.getFacility(TransferFacility)
    user = gateway.getLoggedInUser()
    ctx = SecurityContext(user.getGroupId())
    return transfer.downloadImage(ctx, path, Long(image_id))


# Connect to OMERO
gateway = connect_to_omero()

# Download the image. This could be composed of several files
tmp_dir = tempfile.mkdtemp()
files = download_image(gateway, image_id, tmp_dir)
for f in files:
    options = "open=" + f.getAbsolutePath()
    options += " autoscale color_mode=Default "
    options += "view=[Standard ImageJ] stack_order=Default"
    IJ.run("Bio-Formats Importer", options)
    break

shutil.rmtree(tmp_dir)
gateway.disconnect()
