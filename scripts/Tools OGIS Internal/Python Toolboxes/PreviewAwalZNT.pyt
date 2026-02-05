# -*- coding: utf-8 -*-
from ogisinternalutils.document import get_credentials as _get_creds_for_flag
import arcpy


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Preview Awal ZNT"
        self.alias = ""

        # List of tool classes associated with this toolbox
        self.tools = [Preview_Awal_ZNT_Data_Sipenta]


class Preview_Awal_ZNT_Data_Sipenta(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Preview Awal ZNT Data Sipenta"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        nik = arcpy.Parameter(
            displayName="Nomor Induk Kependudukan (NIK)",
            name="username",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        nomor_berkas = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="project_id",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        tahun = arcpy.Parameter(
            displayName="Tahun",
            name="tahun",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        pembulatan = arcpy.Parameter(
            displayName="Pembulatan",
            name="pembulatan",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        server = arcpy.Parameter(
            displayName="Server Sipenta",
            name="link",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        

        server.filter.type = "ValueList"
        server.filter.list = ["Produksi", "Belajar"]
        
        params = [nik, nomor_berkas, tahun, pembulatan]
        # Periksa ulang status saat membuka parameter agar mengikuti login terbaru
        self.is_gis_internal = bool(_get_creds_for_flag(credential_type="OperatorGISInternal", use_for_tools_validity=True))
        if self.is_gis_internal:
            params.append(server)
            return params
        else:
            return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        return
