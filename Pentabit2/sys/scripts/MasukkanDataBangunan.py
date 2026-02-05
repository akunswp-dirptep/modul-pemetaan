import os
import arcpy

data = arcpy.GetParameterAsText(0)
in_x = arcpy.GetParameterAsText(1)
in_y = arcpy.GetParameterAsText(2)

arcpy.AddMessage("== Proses dimulai ==")

appdata = 'c:\znt\sys'
conf_persil_path = os.path.join(appdata, "persil.dat")

conf_file = open(conf_persil_path, "r")
list_config = conf_file.readlines()
conf_file.close()

dataset_path = ""
persil = ""
persil_path = ""

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "dataset":
        dataset_path = persil_config[1]
    if persil_config[0] == "persil":
        persil = persil_config[1].split(";")[0]
        persil_path = persil_config[1].split(";")[1]

data_bangunan = "DataBangunan"
data_bangunan_path = os.path.join(dataset_path, data_bangunan)
peta_nilai_tanah_path = os.path.join(dataset_path, "PetaNilaiTanah")

if arcpy.Exists(data_bangunan):
    arcpy.Delete_management(data_bangunan)
if arcpy.Exists(data_bangunan_path):
    arcpy.Delete_management(data_bangunan_path)

sr = arcpy.Describe(peta_nilai_tanah_path).spatialReference
arcpy.MakeXYEventLayer_management(data, in_x, in_y, data_bangunan, sr)

arcpy.CopyFeatures_management(data_bangunan, data_bangunan_path)
arcpy.SetParameterAsText(3, data_bangunan)

arcpy.AddMessage("== Proses selesai ==")
