import os
import arcpy

arcpy.AddMessage("== Proses dimulai ==")

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_jalan_path = os.path.join(appdata, "persil.dat")

conf_file = open(conf_jalan_path, "r")
list_config = conf_file.readlines()
conf_file.close()

persil_config = ""
for line in list_config:
    line = line.replace("\n", "")
    persil_config = line.split(",")
    if persil_config[0] == "persil":
        break
persil = persil_config[1].split(";")[0]
persil_path = persil_config[1].split(";")[1]

field_names = [field.name for field in arcpy.ListFields(persil_path)]
if 'LuasBidang' not in field_names:
    arcpy.AddField_management(persil_path, 'LuasBidang', "DOUBLE")
#arcpy.CalculateField_management(persil_path, u'LuasBidang', "!shape.area!", "PYTHON")

if arcpy.Exists(persil):
    arcpy.arcpy.Delete_management(persil)
arcpy.MakeFeatureLayer_management(persil_path, persil)

arcpy.AddGeometryAttributes_management(persil, "AREA", "", "SQUARE_METERS")
#update 14/10/2021
#arcpy.CalculateField_management(persil_path, 'LuasBidang', "[POLY_AREA]", "VB")
arcpy.CalculateField_management(persil_path, 'LuasBidang', "!POLY_AREA!", "PYTHON")

if 'ls_tnh' not in field_names:
    arcpy.AddField_management(persil_path, 'ls_tnh', "DOUBLE")
#arcpy.CalculateField_management(persil_path, u'ls_tnh', "!shape.area!", "PYTHON")
#update 14/10/2021
#arcpy.CalculateField_management(persil_path, 'ls_tnh', "[POLY_AREA]", "VB")
arcpy.CalculateField_management(persil_path, 'ls_tnh', "!POLY_AREA!", "PYTHON")
arcpy.DeleteField_management(persil_path, 'POLY_AREA')

if arcpy.Exists(persil):
    arcpy.Delete_management(persil)

arcpy.MakeFeatureLayer_management(persil_path, persil)
arcpy.SetParameterAsText(0, persil)

arcpy.AddMessage("== Proses selesai ==")
