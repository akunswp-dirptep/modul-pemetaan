import os
import arcpy

peta = arcpy.GetParameterAsText(0)

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

peta_nilai_tanah = "PetaNilaiTanah"
peta_nilai_tanah_path = os.path.join(dataset_path, peta_nilai_tanah)

if arcpy.Exists(peta_nilai_tanah):
    arcpy.Delete_management(peta_nilai_tanah)
if arcpy.Exists(peta_nilai_tanah_path):
    arcpy.Delete_management(peta_nilai_tanah_path)

arcpy.FeatureClassToFeatureClass_conversion(peta, dataset_path, peta_nilai_tanah)
arcpy.MakeFeatureLayer_management(peta_nilai_tanah_path, peta_nilai_tanah)
arcpy.SetParameterAsText(1, peta_nilai_tanah)

arcpy.AddMessage("== Proses selesai ==")
