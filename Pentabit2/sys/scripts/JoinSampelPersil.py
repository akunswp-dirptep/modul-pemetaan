import os
import arcpy

arcpy.AddMessage("== Proses dimulai ==")

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_jalan_path = os.path.join(appdata, "persil.dat")

conf_file = open(conf_jalan_path, "r")
list_config = conf_file.readlines()
conf_file.close()

dataset_path = ""
persil = ""
persil_path = ""
simbologi_path = os.path.join(appdata, "SimbologiBentukPersil.lyr")
persil_line_path = ""
persil_split_path = ""
titiksampel = "TitikSampel"

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "dataset":
        dataset_path = persil_config[1]
    if persil_config[0] == "persil":
        persil = persil_config[1].split(";")[0]
        persil_path = persil_config[1].split(";")[1]

titiksampel_path = os.path.join(dataset_path, titiksampel)
outjoin = os.path.join(dataset_path, "Sampel_Skor")

if arcpy.Exists(outjoin):
    arcpy.Delete_management(outjoin)

arcpy.SpatialJoin_analysis(persil_path, titiksampel_path, outjoin)

# if arcpy.Exists("temp"):
#     arcpy.Delete_management("temp")
# arcpy.MakeFeatureLayer_management(outjoin, "temp", "NILAI is NULL OR NILAI=0")
# arcpy.DeleteFeatures_management(outjoin)

if arcpy.Exists("Sampel_Skor"):
    arcpy.Delete_management("Sampel_Skor")

arcpy.MakeFeatureLayer_management(outjoin, "Sampel_Skor")
arcpy.SelectLayerByAttribute_management("Sampel_Skor", "NEW_SELECTION", "NILAI IS NULL")
arcpy.DeleteFeatures_management("Sampel_skor")

if arcpy.Exists("Sampel_Skor"):
    arcpy.Delete_management("Sampel_Skor")
arcpy.MakeFeatureLayer_management(outjoin, "Sampel_Skor")
arcpy.SetParameterAsText(0, "Sampel_Skor")

arcpy.AddMessage("== Proses Selesai ==")
