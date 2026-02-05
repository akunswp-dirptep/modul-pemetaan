import os
import arcpy

arcpy.AddMessage("== Proses dimulai ==")

sampel_baru_path = arcpy.GetParameterAsText(0)

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_persil_path = os.path.join(appdata, "persil.dat")
conf_file = open(conf_persil_path, "r")
list_config = conf_file.readlines()
conf_file.close()

dataset_path = ""
sampelmodel = ""
sampelmodel_path = ""

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "dataset":
        dataset_path = persil_config[1]

sampelmodel = "Sampel_Model"
sampelmodel_path = os.path.join(dataset_path, sampelmodel)

arcpy.AddMessage("== Backup data lama ==")

if (sampelmodel_path != sampel_baru_path) and (sampel_baru_path.strip() != ""):
    sampelmodel_backup = "SampelModelBackup"
    sampelmodel_backup_path = os.path.join(dataset_path, sampelmodel_backup)
    if arcpy.Exists(sampelmodel_backup_path):
        arcpy.AddMessage("delete backup")
        arcpy.Delete_management(sampelmodel_backup_path)
    arcpy.FeatureClassToFeatureClass_conversion(sampelmodel_path, dataset_path, sampelmodel_backup)
    arcpy.AddMessage("delete real")
    if arcpy.Exists(sampelmodel_path):
        arcpy.Delete_management(sampelmodel_path)
    arcpy.FeatureClassToFeatureClass_conversion(sampel_baru_path, dataset_path, sampelmodel)

if arcpy.Exists(sampelmodel):
    arcpy.Delete_management(sampelmodel)

arcpy.MakeFeatureLayer_management(sampelmodel_path, sampelmodel)
arcpy.SetParameterAsText(1, sampelmodel)

arcpy.AddMessage("== Proses Selesai ==")
