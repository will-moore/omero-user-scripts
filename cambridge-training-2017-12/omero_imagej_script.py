#!/usr/bin/env python
# -*- coding: utf-8 -*-
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

# This script uses ImageJ to Subtract Background by running a macro

import os
import shutil
import tempfile
import subprocess
import sys
import omero
import omero.scripts as scripts
import omero.util.script_utils as scriptUtil
from omero.gateway import BlitzGateway
from omero.rtypes import rstring, rlong, robject


# Path to the Fiji, to be modified
IJ_CLASSPATH = "/opt/omero/Fiji/Fiji.app/ImageJ-linux64"
DROPBOX = "/OMERO/DropBox/"

MACRO_TEXT = """
run("Enhance Contrast...", "saturated=0.3");
run("Subtract Background...", "rolling=50 stack");
"""

def run_macro(conn, client, command_args):
    """
    This processes the script parameters, adding defaults if needed.
    Then calls a method to execute the macro.

    @param: session         The OMERO session
    @param: command_args    Map of String:Object parameters for the script.
                            Objects are not rtypes, since getValue() was
                            called when the map was processed below.
                            But, list and map objects may contain rtypes (need
                            to call getValue())
    """

    images = []
    object_ids = command_args["IDs"]
    # Retrieve the images to analyse
    data_type = command_args.get("Data_Type")
    if data_type == 'Image':
        objects = conn.getObjects("Image", object_ids)
        images = list(objects)
    elif data_type == 'Dataset':
        for d_id in object_ids:
            dataset = conn.getObject("Dataset", d_id)
            if dataset:
                for image in dataset.listChildren():
                    images.append(image)

    # Read the images to analyse into the specified directory
    tmp_dir = tempfile.mkdtemp()
    ome_tiff = load_images(conn, images, tmp_dir)

    # Run the macro. The resulted images will be added to
    # OMERO.dropbox
    new_images = run_imagej_macro(conn, ome_tiff, tmp_dir)

    # Delete the directories
    shutil.rmtree(tmp_dir)

    return "macro run"


def load_images(conn, images, tmp_dir):
    """
    Loads the images from OMERO as ome-tiff.
    """
    ome_tiff = []
    size = 1000000
    for image in images:
        try:
            exporter = conn.createExporter()
            exporter.addImage(image.getId())
            exporter.generateTiff()
            name = '%s.ome.tiff' % (image.getName())
            image_path = os.path.join(tmp_dir, name)
            ome_tiff.append(image_path)
            with open(image_path, 'wb') as out:
                read = 0
                while True:
                    buf = exporter.read(read, size)
                    out.write(buf)
                    if len(buf) < size:
                        break
                    read += len(buf)
        except Exception, e:
            raise e
        finally:
            exporter.close()
    return ome_tiff


def run_imagej_macro(conn, ome_tiff, tmp_dir):
    """
    Run the macro on the selected images
    The results will be saved in the specified directory
    """

    ijm_path = os.path.join(tmp_dir, "open_file.ijm")

    # write the macro to a known location that we can pass to ImageJ
    value = """
setBatchMode(true);
run("Bio-Formats Macro Extensions");
"""
    new_images = []
    box_path = os.path.join(DROPBOX, conn.getUser().omeName)
    print box_path
    with open(ijm_path, 'wb') as ff:
        # run the macro on each ome_tiff
        for i, image in enumerate(ome_tiff):
            if i == 0:
                header = value
            else:
                header = ""

            ff.write("""%s
                imps = Ext.openImagePlus("%s")
            """ % (header, image))
            ff.write(MACRO_TEXT)
            # the image has already ome.tiff as an extension
            new_name = os.path.basename(image)
            new_image_path = os.path.join(box_path, new_name)
            print new_image_path
            ff.write("""run("Bio-Formats Exporter", "save=%s export compression=Uncompressed");
                     run("Quit");""" % new_image_path)
            new_images.append(new_image_path)
    try:
        args = [IJ_CLASSPATH, "--headless", "-macro", ijm_path]
        cmd = " ".join(args)
        print "Script command = %s" % cmd

        # Run the command
        p = subprocess.Popen(args, shell=False, stdout=subprocess.PIPE,
                             stdin=subprocess.PIPE)
        print "Done running ImageJ macro"

    except OSError, e:
        print >>sys.stderr, "Execution failed:", e

    return new_images


def run_script():
    """
    The main entry point of the script, as called by the client via the
    scripting service, passing the required parameters.
    """

    dataTypes = [rstring('Image'), rstring('Dataset')]

    client = scripts.client(
        'omero_imagej_script.py',
        """
        This script runs an ImageJ macro and imports the generated images
        to OMERO using OMERO DropBox
        """,

        scripts.String(
            "Data_Type", optional=False, grouping="01",
            description="The data you want to work with.", values=dataTypes,
            default="Dataset"),

        scripts.List(
            "IDs", optional=False, grouping="02",
            description="List of IDs").ofType(rlong(0)),

        authors=["OME team"],
        institutions=["University of Dundee"],
        contact="ome-users@lists.openmicroscopy.org.uk",
    )

    try:
        conn = BlitzGateway(client_obj=client)

        command_args = client.getInputs(unwrap=True)

        message = run_macro(conn, client, command_args)

        # Return message and file annotation (if applicable) to the client
        client.setOutput("Message", rstring(message))

    finally:
        client.closeSession()


if __name__ == "__main__":
    run_script()
