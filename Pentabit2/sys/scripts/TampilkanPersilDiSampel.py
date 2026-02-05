import os
import arcpy

arcpy.AddMessage("== Proses dimulai ==")

persil_skor_baru = arcpy.GetParameterAsText(0)

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_persil_path = os.path.join(appdata, "persil.dat")

conf_file = open(conf_persil_path, "r")
list_config = conf_file.readlines()
conf_file.close()

persil = ""
persil_path = ""
dataset_path = ""

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "persil":
        persil = persil_config[1].split(";")[0]
        persil_path = persil_config[1].split(";")[1]
    if persil_config[0] == "dataset":
        dataset_path = persil_config[1]

arcpy.AddMessage("== Backup data lama ==")

if (persil_path != persil_skor_baru) and (persil_skor_baru.strip() != ""):
    persil_skor_backup = "PersilSkorBackup"
    persil_backup_path = os.path.join(dataset_path, persil_skor_backup)
    if arcpy.Exists(persil_backup_path):
        arcpy.Delete_management(persil_backup_path)
    arcpy.FeatureClassToFeatureClass_conversion(persil_path, dataset_path, persil_skor_backup)
    arcpy.Delete_management(persil_path)
    arcpy.FeatureClassToFeatureClass_conversion(persil_skor_baru, dataset_path, persil)

if arcpy.Exists(persil):
    arcpy.Delete_management(persil)

arcpy.MakeFeatureLayer_management(persil_path, persil)
arcpy.SetParameterAsText(1, persil)

arcpy.AddMessage("== Proses selesai ==")
