import os, arcpy

arcpy.AddMessage("== Proses dimulai ==")

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_persil_path = os.path.join(appdata, "persil.dat")

dataset_path = ""
sim_path = os.path.join(appdata, "SimbologiPersilTaru.lyr")

conf_file = open(conf_persil_path, "r")
list_config = conf_file.readlines()
conf_file.close()

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "dataset":
        dataset_path = persil_config[1]

# persil_centroid = "PersilCentroid"
# persil_centroid_path = os.path.join(dataset_path, persil_centroid)
persil_taru = "Persil_Taru"
persil_taru_path = os.path.join(dataset_path, persil_taru)

arcpy.AddMessage("== Masukkan data persil taru ==")

if arcpy.Exists(persil_taru):
    arcpy.Delete_management(persil_taru)

arcpy.MakeFeatureLayer_management(persil_taru_path, persil_taru)
arcpy.ApplySymbologyFromLayer_management(persil_taru, sim_path)
arcpy.SetParameterAsText(0, persil_taru)

arcpy.AddMessage("== Proses selesai ==")
