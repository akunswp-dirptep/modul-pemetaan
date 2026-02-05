import os
import arcpy

arcpy.AddMessage("== Proses dimulai ==")

sisi_jalan_baru_path = arcpy.GetParameterAsText(1)

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_jalan_path = os.path.join(appdata, "jalan.dat")

conf_file = open(conf_jalan_path, "r")
list_config = conf_file.readlines()
conf_file.close()

sisijalan_config = ""
for line in list_config:
    line = line.replace("\n", "")
    sisijalan_config = line.split(",")
    if sisijalan_config[0] == "dataset":
        dataset_path = sisijalan_config[1]
    if sisijalan_config[0] == "sisijalan":
        sisijalan = sisijalan_config[1].split(";")[0]
        sisijalan_path = sisijalan_config[1].split(";")[1]

arcpy.AddMessage("== Backup data lama ==")

if (sisijalan_path != sisi_jalan_baru_path) and (sisi_jalan_baru_path.strip() != ""):
    sisijalan_backup = "SisiJalanBackup"
    sisijalan_backup_path = os.path.join(dataset_path, sisijalan_backup)
    if arcpy.Exists(sisijalan_backup_path):
        arcpy.AddMessage("delete backup")
        arcpy.Delete_management(sisijalan_backup_path)
    arcpy.FeatureClassToFeatureClass_conversion(sisijalan_path, dataset_path, sisijalan_backup)
    arcpy.AddMessage("delete real")
    if arcpy.Exists(os.path.join(dataset_path, "TopologiSisiJalan")):
        arcpy.Delete_management(os.path.join(dataset_path, "TopologiSisiJalan"))
    arcpy.Delete_management(sisijalan_path)
    arcpy.FeatureClassToFeatureClass_conversion(sisi_jalan_baru_path, dataset_path, sisijalan)

if arcpy.Exists(sisijalan):
    arcpy.Delete_management(sisijalan)
arcpy.MakeFeatureLayer_management(sisijalan_path, sisijalan)
arcpy.SetParameterAsText(0, sisijalan)

arcpy.AddMessage("== Menjalankan proses berhasil dilakukan. Silakan lanjutkan proses berikutnya... ==")
