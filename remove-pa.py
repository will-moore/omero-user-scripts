# coding=utf-8
""" #31344

    ~/openmicroscopy/dist/bin/omero script list|upload|replace
    ~/openmicroscopy/dist/bin/omero admin ice server start|stop Processor-0
"""
from omero.util import script_utils
from omero.gateway import BlitzGateway
from omero.rtypes import *
import omero.scripts as scripts


def run():
    """
    """
    client = scripts.client("remove-pa.py", "Remove PlateAcquisition from Plate", scripts.List("IDs", optional=False, grouping="1", description="List of Plate IDs").ofType(rlong(0)))

    try:
        scriptParams = {}
        for key in client.getInputKeys():
            if client.getInput(key):
                scriptParams[key] = client.getInput(key, unwrap=True)

            print scriptParams

        connection = BlitzGateway(client_obj=client)
        
        plateId = scriptParams["IDs"][0]
        plateObj = connection.getObject("Plate", plateId)
        if plateObj is None:
            client.setOutput("Message", rstring("ERROR: No Plate with ID %s" % plateId))
            return
        
        plateAcquisitionList = list(plateObj.listPlateAcquisitions())
        if len(plateAcquisitionList):
            updateService = connection.getUpdateService()
        
            for plateAcquisitionObj in plateAcquisitionList:
                plateAcquisitionObj.unlinkAnnotations()
                plateAcquisitionObj.save()
                
                plateObj.clearPlateAcquisitions()

                # TODO: handle children of PlateAcquisition
    
                try:
                    links = list(plateAcquisitionObj.getParentLinks(plateObj.id))
                except AttributeError:
                    pass
                else:
                    for link in links:
                        connection.deleteObjectDirect(link._obj)

            client.setOutput("Message", rstring("No errors. %d PlateAcquisitions removed from Plate." % len(plateAcquisitionList)))
        else:
            client.setOutput("Message", rstring("No errors. Found no PlateAcquisitions linked to Plate."))
    finally:
        client.closeSession()

if __name__ == "__main__":
    run()
