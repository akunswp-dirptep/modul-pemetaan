import os, arcpy

arcpy.AddMessage("== Proses dimulai ==")

appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
tempdata = os.path.join(appdata, "temp")
conf_jalan_path = os.path.join(appdata, "persil.dat")
conf_file = open(conf_jalan_path, "r")
list_config = conf_file.readlines()
conf_file.close()

dataset_path = ""
jaringan_jalan = "Jaringan_Jalan"
jaringan_jalan_path = ""
persil_baru = "Persil_Baru"

for line in list_config:
    line = line.replace("\n", "")
    jalan_config = []
    jalan_config = line.split(",")
    if jalan_config[0] == "dataset":
        dataset_path = jalan_config[1]

persil_baru_path = os.path.join(dataset_path, persil_baru)
jaringan_jalan_path = os.path.join(dataset_path, jaringan_jalan)

sim_persil_path = os.path.join(appdata, "SimbologiPersilUpdate_i3.lyr")
sim_jarjal_path = os.path.join(appdata, "SimbologiJaringanJalanUpdate_i3.lyr")

#if jaringan_jalan_path.strip() == "":
#    jaringan_jalan_path = os.path.join(dataset_path, jaringan_jalan)
#else:
#    temp_path = os.path.join(dataset_path, jaringan_jalan)
#    if arcpy.Exists(temp_path):
#        arcpy.Delete_management(temp_path)
#    arcpy.CopyFeatures_management(jaringan_jalan_path, temp_path)
#    jaringan_jalan_path = temp_path

if arcpy.Exists(jaringan_jalan):
    arcpy.Delete_management(jaringan_jalan)
if arcpy.Exists(persil_baru):
    arcpy.Delete_management(persil_baru)

# aprx = arcpy.mp.ArcGISProject('CURRENT')
# current_map = aprx.activeMap
# tab_name = []
# for m in aprx.listMaps():
#     for lyr in m.listLayers():
#         m.removeLayer(lyr)

arcpy.MakeFeatureLayer_management(jaringan_jalan_path, jaringan_jalan)
arcpy.ApplySymbologyFromLayer_management(jaringan_jalan, sim_jarjal_path)
arcpy.MakeFeatureLayer_management(persil_baru_path, persil_baru)
arcpy.ApplySymbologyFromLayer_management(persil_baru, sim_persil_path)

arcpy.SetParameterAsText(0, persil_baru)
arcpy.SetParameterAsText(1, jaringan_jalan)

arcpy.AddMessage("== Proses selesai ==")


