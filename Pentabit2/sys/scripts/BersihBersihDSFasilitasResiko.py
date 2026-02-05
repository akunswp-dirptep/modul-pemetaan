import os
import arcpy

arcpy.AddMessage("== Proses mulai ==")

appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

conf_fasilitas_path = os.path.join(appdata, "fasilitas.dat")
conf_file = open(conf_fasilitas_path, "r")
list_config = conf_file.readlines()
conf_file.close()

datasetfasilitas_path = ""

for line in list_config:
    line = line.replace("\n", "")
    fas_config = []
    fas_config = line.split(",")
    if fas_config[0] == "datasetfasilitas":
        datasetfasilitas_path = fas_config[1]

arcpy.env.workspace = datasetfasilitas_path

list_fc = arcpy.ListFeatureClasses("*")

arcpy.AddMessage("== Hapus Fasilitas ==")

for fc in list_fc:
    if arcpy.Exists(fc):
        arcpy.Delete_management(fc)
    fas_path = os.path.join(datasetfasilitas_path, fc)
    if arcpy.Exists(fas_path):
        arcpy.Delete_management(fas_path)
    arcpy.AddMessage("Fasilitas " + fc + " dihapus")

conf_resiko_path = os.path.join(appdata, "resiko.dat")
conf_file = open(conf_resiko_path, "r")
list_config = conf_file.readlines()
conf_file.close()

datasetresiko_path = ""

for line in list_config:
    line = line.replace("\n", "")
    res_config = []
    res_config = line.split(",")
    if res_config[0] == "datasetresiko":
        datasetresiko_path = res_config[1]

arcpy.env.workspace = datasetresiko_path
list_res = arcpy.ListFeatureClasses("*")

arcpy.AddMessage("== Hapus Resiko ==")

for fc in list_res:
    if arcpy.Exists(fc):
        arcpy.Delete_management(fc)
    res_path = os.path.join(datasetresiko_path, fc)
    if arcpy.Exists(res_path):
        arcpy.Delete_management(res_path)
    arcpy.AddMessage("Resiko " + fc + " dihapus")

arcpy.AddMessage("== Proses selesai ==")
