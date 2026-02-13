# -*- coding: utf-8 -*-

import arcpy, os, sys
script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
from zntutils.zona_layer import get_config_values

class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox Tambah Citra Basemap"
        self.alias = "toolbox_tambah_citra_basemap"

        # List of tool classes associated with this toolbox
        self.tools = [Tambah_Citra_Basemap]


class Tambah_Citra_Basemap(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Tambah Citra Basemap"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        file_citra = arcpy.Parameter(
            displayName="File Citra",
            name="file_citra",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Input")
        
        output_citra = arcpy.Parameter(
            name="output_citra",
            datatype="GPRasterLayer",
            parameterType="Derived",
            direction="Output"
        )

        output_zl = arcpy.Parameter(
            name="output_zl",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [file_citra, output_citra, output_zl]


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
        file_citra = parameters[0].valueAsText
        citra_layer = "citra_layer"
        arcpy.management.MakeRasterLayer(file_citra, citra_layer)

        config_dan_paths = get_config_values()
        simbology_path = os.path.join(config_dan_paths['symbology_folder'], "Simbologi_Jenis_Zona.lyrx")

        zl = "Zona_Layer"
        arcpy.management.DefineProjection(citra_layer, config_dan_paths['coor'])
        arcpy.SetParameter(1, citra_layer)
        arcpy.management.MakeFeatureLayer(config_dan_paths['zl_path'], zl)
        arcpy.management.ApplySymbologyFromLayer(zl, simbology_path)
        arcpy.SetParameter(2, zl)
        return
