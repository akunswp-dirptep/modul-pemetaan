import os
import arcpy

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

if arcpy.Exists(os.path.join(appdata, "results", "GWR_Sampel.shp")):
    if arcpy.Exists("HasilGWR_Sampel"):
        arcpy.Delete_management("HasilGWR_Sampel")
    arcpy.MakeFeatureLayer_management(os.path.join(appdata, "results", "GWR_Sampel.shp"), "HasilGWR_Sampel")
    arcpy.SetParameterAsText(0, "HasilGWR_Sampel")
