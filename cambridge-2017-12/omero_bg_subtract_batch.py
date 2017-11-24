import os
from os import path

from java.lang import Long
from java.lang import String
from java.lang.Long import longValue
from java.util import ArrayList
from jarray import array
from java.lang.reflect import Array
import java

# Omero Dependencies
from omero.gateway import Gateway
from omero.gateway import LoginCredentials
from omero.gateway import SecurityContext
from omero.gateway.exception import DSAccessException
from omero.gateway.exception import DSOutOfServiceException
from omero.gateway.facility import BrowseFacility
from omero.gateway.facility import DataManagerFacility
from omero.gateway.model import DatasetData
from omero.gateway.model import ExperimenterData
from omero.gateway.model import ProjectData
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
from ij import IJ


# Setup
# =====

# OMERO Server details
HOST = "outreach.openmicroscopy.org"
PORT = 4064
PASSWORD = ""
group_id = "-1"

#  parameters to edit
dataset_id = ""
USERNAME = "user-x"


def open_image_plus(HOST, USERNAME, PASSWORD, PORT, group_id, image_id):

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


def get_image_ids(gateway, dataset_id):
    "List all image's ids contained in a Dataset"

    browse = gateway.getFacility(BrowseFacility)
    user = gateway.getLoggedInUser()
    ctx = SecurityContext(user.getGroupId())
    ids = ArrayList(1)
    val = Long(dataset_id)
    ids.add(val)
    images = browse.getImagesForDatasets(ctx, ids)
    j = images.iterator()
    image_ids = []
    while j.hasNext():
        image = j.next()
        image_ids.append(String.valueOf(image.getId()))
    return image_ids


def upload_image(path, gateway):
    "Upload an image to omero"

    user = gateway.getLoggedInUser()
    sessionKey = gateway.getSessionId(user)

    config = ImportConfig()
    config.debug.set('false')
    config.hostname.set(HOST)
    config.sessionKey.set(sessionKey)
    value = "omero.model.Dataset:"
    value += str(dataset_id)
    config.target.set(value)

    loci.common.DebugTools.enableLogging("DEBUG")

    store = config.createStore()
    reader = OMEROWrapper(config)

    library = ImportLibrary(store, reader)
    error_handler = ErrorHandler(config)

    library.addObserver(LoggingImportMonitor())
    candidates = ImportCandidates(reader, path, error_handler)
    reader.setMetadataOptions(DefaultMetadataOptions(MetadataLevel.ALL))
    return library.importCandidates(config, candidates)


# Prototype analysis example
gateway = connect_to_omero()
image_ids = get_image_ids(gateway, dataset_id)

for image_id in image_ids:
    print(""+image_id)
    open_image_plus(HOST, USERNAME, PASSWORD, PORT, group_id, image_id)
    IJ.run("Enhance Contrast...", "saturated=0.3")
    IJ.run("Subtract Background...", "rolling=50 stack")

    # Save modified image as OME-TIFF using Bio-Formats
    imp = IJ.getImage()
    path = imp.getTitle() + ".ome.tiff"
    print(path)
    options = "save=" + path + " export compression=Uncompressed"
    IJ.run(imp, "Bio-Formats Exporter", options)
    imp.changes = False
    imp.close()

    # Upload the generated OME-TIFF to OMERO
    print("uploading...")
    str2d = java.lang.reflect.Array.newInstance(java.lang.String, [1])
    str2d[0] = path
    success = upload_image(str2d, gateway)
    # delete the local OME-TIFF image
    os.remove(path)
    print("imported")

print("Done")
gateway.disconnect()
