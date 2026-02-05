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
simbologi_path = os.path.join(appdata, "SimbologiZonasiCluster.lyr")

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "dataset":
        dataset_path = persil_config[1]

untukcluster_path = os.path.join(dataset_path, "PersilUntukCluster")
hasil_cluster = "Hasil_Cluster"

arcpy.AddMessage(untukcluster_path)

if arcpy.Exists(hasil_cluster):
    arcpy.Delete_management(hasil_cluster)

arcpy.MakeFeatureLayer_management(untukcluster_path, hasil_cluster)
arcpy.ApplySymbologyFromLayer_management(hasil_cluster, simbologi_path)

arcpy.SetParameterAsText(0, hasil_cluster)

arcpy.AddMessage("== Proses selesai ==")
