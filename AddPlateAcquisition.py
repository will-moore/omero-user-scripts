# coding=utf-8
""" Add a PlateAcquisition to a given Plate.
"""
from omero.util import script_utils
from omero.gateway import BlitzGateway
from omero.rtypes import *
from omero.model import *
import omero.scripts as scripts


def run():
    """
    """
    client = scripts.client("AddPlateAcquisition.py", "Add a PlateAcquisition to Plate", scripts.List("IDs", optional=False, grouping="1", description="List of Plate IDs").ofType(rlong(0)))

    try:
        scriptParams = {}
        for key in client.getInputKeys():
            if client.getInput(key):
                scriptParams[key] = client.getInput(key, unwrap=True)

        connection = BlitzGateway(client_obj=client)

        createdIdTuples = []
        
        for plateId in scriptParams["IDs"]:
            plateObj = connection.getObject("Plate", plateId)
            if plateObj is None:
                client.setOutput("Message", rstring("ERROR: No Plate with ID %s" % plateId))
                return
    
            updateService = connection.getUpdateService()
    
            plateAcquisitionObj = PlateAcquisitionI()
            plateAcquisitionObj.setPlate(PlateI(plateObj.getId(), False))
            
            wellGrid = plateObj.getWellGrid()
            for axis in wellGrid:
                for wellObj in axis:
                    wellSampleList = wellObj.copyWellSamples()
                    plateAcquisitionObj.addAllWellSampleSet(wellSampleList)
            
            plateAcquisitionObj = updateService.saveAndReturnObject(plateAcquisitionObj)
            plateAcquisitionId = plateAcquisitionObj.getId()._val

            createdIdTuples.append("new PlateAcquisition with ID %d to Plate with ID %d" % (plateAcquisitionId, plateId))

        createdStr = ", ".join(createdIdTuples)

        client.setOutput("Message", rstring("No errors. Linked %s." % createdStr))
    finally:
        client.closeSession()

if __name__ == "__main__":
    run()