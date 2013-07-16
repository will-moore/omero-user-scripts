# coding=utf-8
""" #1687

    ~/openmicroscopy/dist/bin/omero script list|upload|replace
    ~/openmicroscopy/dist/bin/omero admin ice server start|stop Processor-0
    
    print wellObj
        <_WellWrapper id=5841>
    
    
"""
from omero.util import script_utils
from omero.gateway import BlitzGateway
from omero.rtypes import *
from omero.model import *
import omero.scripts as scripts


def run():
    """
    """
    client = scripts.client("AddPlateAcquisition.py", "Add PlateAcquisition to Plate", scripts.List("IDs", optional=False, grouping="1", description="List of Plate IDs").ofType(rlong(0)))

    try:
        scriptParams = {}
        for key in client.getInputKeys():
            if client.getInput(key):
                scriptParams[key] = client.getInput(key, unwrap=True)

        connection = BlitzGateway(client_obj=client)

        plateId = scriptParams["IDs"][0]
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

        client.setOutput("Message", rstring("No errors. Linked new PlateAcquisition with ID %d to Plate." % plateAcquisitionId))
    finally:
        client.closeSession()

if __name__ == "__main__":
    run()