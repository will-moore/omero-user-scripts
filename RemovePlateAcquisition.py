# coding=utf-8
""" Remove all PlateAcquisitions from a given Plate.
"""
from omero.util import script_utils
from omero.gateway import BlitzGateway
from omero.rtypes import *
from omero.model import *
import omero.scripts as scripts


def run():
    """
    """
    client = scripts.client("RemovePlateAcquisition.py", "Remove all PlateAcquisitions from Plate", scripts.List("IDs", optional=False, grouping="1", description="List of Plate IDs").ofType(rlong(0)))

    try:
        scriptParams = {}
        for key in client.getInputKeys():
            if client.getInput(key):
                scriptParams[key] = client.getInput(key, unwrap=True)

            print scriptParams

        connection = BlitzGateway(client_obj=client)
        
        processedIdMessages = []
        
        for plateId in scriptParams["IDs"]:
            plateObj = connection.getObject("Plate", plateId)
            if plateObj is None:
                client.setOutput("Message", rstring("ERROR: No Plate with ID %s" % plateId))
                return
            
            updateService = connection.getUpdateService()
            queryService = connection.getQueryService()
            
            params = omero.sys.ParametersI()
            params.addId(plateId)
    
            queryString = """
                FROM PlateAcquisition AS pa
                LEFT JOIN FETCH pa.wellSample
                LEFT OUTER JOIN FETCH pa.annotationLinks
                    WHERE pa.plate.id = :id
                """
            plateAcquisitionList = queryService.findAllByQuery(queryString, params, connection.SERVICE_OPTS)
            if plateAcquisitionList:        
                for plateAcquisitionObj in plateAcquisitionList:
                    for wellSampleObj in plateAcquisitionObj.copyWellSample(): # actually, it's a list
                        wellSampleObj.setPlateAcquisition(None)
                        updateService.saveObject(wellSampleObj)
                
                    plateAcquisitionObj.clearWellSample()
                    plateAcquisitionObj.clearAnnotationLinks()
    
                    plateAcquisitionObj = updateService.saveAndReturnObject(plateAcquisitionObj)
                    updateService.deleteObject(plateAcquisitionObj)
                    
            processedIdMessages.append("%d PlateAcquisition(s) removed from Plate with ID %d" % (len(plateAcquisitionList), plateId))

        processedStr = ", ".join(processedIdMessages)

        client.setOutput("Message", rstring("No errors. %s." % processedStr))
    finally:
        client.closeSession()

if __name__ == "__main__":
    run()