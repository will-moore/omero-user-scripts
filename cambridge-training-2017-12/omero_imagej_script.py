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

import omero.util.script_utils as scriptUtil
from omero.gateway import BlitzGateway
from omero.rtypes import rstring, rlong, robject

IMAGEJ_CLASSPATH = "/Applications/Fiji.app/Contents/MacOS/ImageJ-macosx"


def run_macro(conn, command_args):
    """
    This processes the script parameters, adding defaults if needed.
    Then calls a method to execute the macro.

    @param: session         The OMERO session
    @param: command_args    Map of String:Object parameters for the script.
                            Objects are not rtypes, since getValue() was
                            called when the map was processed below.
                            But, list and map objects may contain rtypes (need
                            to call getValue())

    @return:                the id of the originalFileLink child. (ID object,
                            not value)
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
    macro_file_id = long(command_args["Macro_File_ID"])
    object_id = object_ids[0]
    of = get_original_file(conn, data_type, object_id, macro_file_id)

    # Read the file
    store = conn.createRawFileStore()
    file_path = scriptUtil.download_file(store, of)


def run_imagej(conn, file_path):
	"""
    Run the macro on the selected images
    """
    ijm_path = "macro.ijm"

    with open(file_path,'r') as f:
        macro_text = f.read()

    # write the macro to a known location that we can pass to ImageJ
    with open(ijm_path, 'w') as ff:
        ff.write(macro_text)
    
    try:
        # Xvcn : reference : http://forum.imagej.net/t/running-macro-in-headless-mode-on-error/161/2
        args = ["Xvnc4 :$UID 2> /dev/null & export DISPLAY=:$UID & ", IMAGEJ_CLASSPATH, "-macro",
                ijm_path]

        # debug
        cmd = " ".join(args)
        print "Script command = %s" % cmd

        # Run the command
        results = subprocess.Popen(args, stdout=subprocess.PIPE, stdin=subprocess.PIPE).communicate()
        std_out = results[0]
        std_err = results[1]
        print std_out
        print std_err
        print "Done running ImageJ macro"
    
    except OSError, e:
        print >>sys.stderr, "Execution failed:", e 


def get_original_file(conn, object_type, object_id, file_ann_id=None):
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
            # Pick file by Ann ID (or name if ID is None)
            if (file_ann_id is None and file_name.endswith(".ijm")) or (
                    ann.getId() == file_ann_id):
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
        This script processes a ijm file, attached to an image or dataset,
        """,

        scripts.String(
            "Data_Type", optional=False, grouping="01",
            description="The data you want to work with.", values=dataTypes,
            default="Dataset"),

        scripts.List(
            "IDs", optional=False, grouping="02",
            description="List of IDs").ofType(rlong(0)),

        scripts.String(
            "Macro_File_ID", optional=False, grouping="03",
            description="The File ID corresponding to the macro .ijm"),

        authors=["OME team"],
        institutions=["University of Dundee"],
        contact="ome-users@lists.openmicroscopy.org.uk",
    )

    try:
        conn = BlitzGateway(client_obj=client)

        command_args = client.getInputs(unwrap=True)

        # call the main script, attaching resulting figure to Image. Returns
        # the id of the originalFileLink child. (ID object, not value)
        file_annotation, message = run_macro(conn, command_args)

        # Return message and file annotation (if applicable) to the client
        client.setOutput("Message", rstring(message))
        if file_annotation is not None:
            client.setOutput("File_Annotation", robject(file_annotation._obj))

    finally:
        client.closeSession()


if __name__ == "__main__":
    run_script()
