#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
-----------------------------------------------------------------------------
  Copyright (C) 2017 University of Dundee. All rights reserved.


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

This script uses ImageJ to Subtract Background by running a macro
"""

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
IJ_CLASSPATH = ""
SERVER_PATH = ""

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

    # Retrieve the macro to use
    macro_file_name = command_args["Macro_File_Name"]
    if not macro_file_name.endswith('.ijm'):
        macro_file_name = '%s.ijm' % macro_file_name


    object_id = object_ids[0]
    of = get_original_file(conn, data_type, object_id, macro_file_name)

    # Read the macro
    store = conn.createRawFileStore()
    file_path = scriptUtil.download_file(store, of)

    # Read the images to analyse into the specified directory
    dir_images = tempfile.mkdtemp()
    ome_tiff = load_images(conn, images, dir_images)

    # Run the macro
    tmp_dir = tempfile.mkdtemp()
    new_images = run_imagej_macro(conn, file_path, ome_tiff, tmp_dir)

    # Create a dataset to add the images to
    dataset = omero.model.DatasetI()
    dataset.name = rstring('Results_for_%s' % macro_file_name)
    dataset = conn.getUpdateService().saveAndReturnObject(dataset)
    # Upload the results back to OMERO
    upload_generated_images(client, tmp_dir, dataset.getId().getValue())

    # Delete the directories
    shutil.rmtree(dir_images)
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


def upload_generated_images(client, path_to_directory, dataset_id):
    """
    Import to OMERO the generated images in the specified folder
    """

    host = client.getProperty("omero.host")
    port = client.getProperty("omero.port")
    key = client.getSessionId()
    args = [SERVER_PATH, 'import', '-s', 'localhost', '-p', port, '-k', key,
            '-d', str(dataset_id), path_to_directory]
    import_prc = subprocess.Popen(args, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, shell=False)
    import_prc.wait()
    


def run_imagej_macro(conn, file_path, ome_tiff, tmp_dir):
    """
    Run the macro on the selected images
    The results will be saved in the specified directory
    """

    ijm_path = os.path.join(tmp_dir, "open_file.ijm")

    with open(file_path, 'r') as f:
        macro_text = f.read()

    # write the macro to a known location that we can pass to ImageJ
    value = """
setBatchMode(true);
run("Bio-Formats Macro Extensions");
"""
    new_images = []
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
            ff.write(macro_text)
            # the image has already ome.tiff as an extension
            new_name = os.path.basename(image)
            new_image_path = os.path.join(tmp_dir, new_name)
            print new_image_path
            ff.write("""run("Bio-Formats Exporter", "save=%s export compression=Uncompressed");
                     run("Quit");""" % new_image_path)
            new_images.append(new_image_path)
    try:
        # see http://forum.imagej.net/t/running-macro-in-headless-mode-on-error/161/2
        # args = ["Xvnc4 :$UID 2> /dev/null & export DISPLAY=:$UID & ",
        #        IJ_CLASSPATH, "-macro", ijm_path]
        # debug
        args = ["Xvnc4", ":$UID", "2> /dev/null", "&", "export", "DISPLAY=:$UID", "&",
                IJ_CLASSPATH, "-macro", ijm_path]
        cmd = " ".join(args)
        print "Script command = %s" % cmd

        # Run the command
        p = subprocess.Popen(args, shell=False, stdout=subprocess.PIPE,
                             stdin=subprocess.PIPE)
        results = p.communicate()
        print results[0]
        print results[1]
        print "Done running ImageJ macro"

    except OSError, e:
        print >>sys.stderr, "Execution failed:", e

    return new_images


def get_original_file(conn, object_type, object_id, file_ann_name=None):
    """
    Retrieve the file containing the macro.
    """
    if object_type == "Dataset":
        omero_object = conn.getObject("Dataset", int(object_id))
        if omero_object is None:
            sys.stderr.write("Error: Dataset does not exist.\n")
            sys.exit(1)
    else:
        omero_object = conn.getObject("Image", int(object_id))
        if omero_object is None:
            sys.stderr.write("Error: Image does not exist.\n")
            sys.exit(1)

    file_ann = None

    for ann in omero_object.listAnnotations():
        if isinstance(ann, omero.gateway.FileAnnotationWrapper):
            file_name = ann.getFile().getName()
            if (file_ann_name is None and file_name.endswith(".ijm")) or (
                    file_ann_name == file_name):
                file_ann = ann
    if file_ann is None:
        sys.stderr.write("Error: File does not exist.\n")
        sys.exit(1)

    return file_ann.getFile()._obj


def run_script():
    """
    The main entry point of the script, as called by the client via the
    scripting service, passing the required parameters.
    """

    dataTypes = [rstring('Image'), rstring('Dataset')]

    client = scripts.client(
        'omero_imagej_script.py',
        """
        This script processes an ijm file, attached to an image or dataset,
        """,

        scripts.String(
            "Data_Type", optional=False, grouping="01",
            description="The data you want to work with.", values=dataTypes,
            default="Dataset"),

        scripts.List(
            "IDs", optional=False, grouping="02",
            description="List of IDs").ofType(rlong(0)),

        scripts.String(
            "Macro_File_Name", optional=False, grouping="03",
            description="The name of the macro e.g. substract_macro"),

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
