import os
import arcpy

arcpy.AddMessage("== Proses dimulai ==")

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_persil_path = os.path.join(appdata, "persil.dat")

conf_file = open(conf_persil_path, "r")
list_config = conf_file.readlines()
conf_file.close()

dataset_path = ""
persil = ""
persil_path = ""
simbologi_path = os.path.join(appdata, "SimbologiBentukPersil.lyr")

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "persil":
        persil = persil_config[1].split(";")[0]
        persil_path = persil_config[1].split(";")[1]

if arcpy.Exists(persil):
    arcpy.Delete_management(persil)

# arcpy.AddMessage(persil)
# arcpy.AddMessage(persil_path)

arcpy.MakeFeatureLayer_management(persil_path, persil)
arcpy.ApplySymbologyFromLayer_management(persil, simbologi_path)

arcpy.SetParameterAsText(0, persil)

arcpy.AddMessage("== Proses selesai ==")
