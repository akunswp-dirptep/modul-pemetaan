# -*- coding: utf-8 -*-

import arcpy, os, sys

arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputMFlag = "Disabled"

script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
    
from zntutils.zona_layer import get_config_values, delete_bad_file

class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox Tambah Citra Basemap"
        self.alias = "toolbox_tambah_citra_basemap"

        # List of tool classes associated with this toolbox
        self.tools = [Tambah_Citra_Basemap,
                      Tambah_Citra_Online]


class Tambah_Citra_Basemap(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Tambah Citra Basemap"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        file_citra = arcpy.Parameter(
            displayName="File Citra (.tif/.tiff)",
            name="file_citra",
            datatype="File",
            parameterType="Required",
            direction="Input"
        )

        file_citra.filter.list = ['tif', 'tiff']

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
        delete_bad_file()
        file_citra = parameters[0].valueAsText
        # Tidak bisa baca file (.ecw), Bug di Arcgis Pro 3.4, baca: https://support.esri.com/en-us/bug/when-dragging-an-enhanced-compression-wavelet-ecw-file-bug-000173123

        if not file_citra.lower().endswith(('.tif', '.tiff')):
            raise arcpy.ExecuteError("File harus berformat TIF.")

        config_dan_paths = get_config_values()
        simbology_path = os.path.join(config_dan_paths['symbology_folder'], "Simbologi_Jenis_Zona.lyrx")

        zl = "Zona_Layer"

        arcpy.SetParameter(1, file_citra)
        arcpy.management.MakeFeatureLayer(config_dan_paths['zl_path'], zl)
        arcpy.management.ApplySymbologyFromLayer(zl, simbology_path)
        arcpy.SetParameter(2, zl)
        return

class Tambah_Citra_Online(object):
    def __init__(self):
        self.label = "Tambah Citra Online"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        pilihan_sumber = arcpy.Parameter(
            displayName= "Pilih Citra",
            name = 'pilih_citra',
            datatype='GPString',
            parameterType='Required',
            direction='Input'
        )

        pilihan_sumber.filter.list = [
            'Google Maps',
            'Google Satelit',
            'Google Satelit Hybrid',
            'Google Street'
        ]

        pilihan_sumber.value = 'Google Maps'

        output_tile = arcpy.Parameter(
            displayName="Output Citra",
            name="output_citra",
            datatype="GPMapServerLayer",
            parameterType="Derived",
            direction="Output"
        )

        output_zl = arcpy.Parameter(
            displayName="Output Zona Layer",
            name="output_zl",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [pilihan_sumber, output_tile, output_zl]

    def isLicensed(self):
        return True

    def execute(self, parameters, messages):

        config_dan_paths = get_config_values()
        pilihan_sumber = parameters[0].valueAsText
        simbology_path = os.path.join(
            config_dan_paths['symbology_folder'],
            "Simbologi_Jenis_Zona.lyrx"
        )

        zl = "Zona_Layer"
        url_source_dict = {
            'Google Satelit': 'https://mt1.google.com/vt/lyrs=s&x={col}&y={row}&z={level}',
            'Google Satelit Hybrid': 'https://mt1.google.com/vt/lyrs=y&x={col}&y={row}&z={level}',
            'Google Street': 'https://mt1.google.com/vt/lyrs=h&x={col}&y={row}&z={level}',
            'Google Maps': 'https://mt1.google.com/vt/lyrs=r&x={col}&y={row}&z={level}'
        }

        url_source = url_source_dict.get(pilihan_sumber)
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        active_map = aprx.activeMap

        # Tambah Google tile layer
        google_layer = active_map.addDataFromPath(url_source)

        # Rename layer
        google_layer.name = pilihan_sumber

        # Tambah zona layer
        arcpy.management.MakeFeatureLayer(
            config_dan_paths['zl_path'],
            zl
        )

        arcpy.management.ApplySymbologyFromLayer(
            zl,
            simbology_path
        )

        arcpy.SetParameter(2, zl)

        arcpy.AddMessage("Google Satellite berhasil ditambahkan.")
