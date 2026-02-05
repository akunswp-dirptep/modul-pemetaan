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
# sim_path = os.path.join(appdata, "SimbologiZonasi8Test.lyr")
sim_update_path = os.path.join(appdata, "SimbologiPetaPersil.lyr")

persil_config = ""
for line in list_config:
    line = line.replace("\n", "")
    persil_config = line.split(",")
    if persil_config[0] == "dataset":
        dataset_path = persil_config[1]
        break

persil = "Persil_Baru_Zonasi"
persil_update = "Persil_Baru_Status"
persil_path = os.path.join(dataset_path, "Persil_Baru")

persil_edit_fields = [f.name for f in arcpy.ListFields(persil_path)]

if "zonasi" not in persil_edit_fields:
    arcpy.AddField_management(persil_edit, "zonasi", "TEXT")
if "s_zonasi" not in persil_edit_fields:
    arcpy.AddField_management(persil_edit, "s_zonasi", "DOUBLE")
if "min_lb_jln" not in persil_edit_fields:
    arcpy.AddField_management(persil_edit, "min_lb_jln", "DOUBLE")

if arcpy.Exists(persil):
    arcpy.Delete_management(persil)
arcpy.MakeFeatureLayer_management(persil_path, persil)
# arcpy.ApplySymbologyFromLayer_management(persil, sim_path)
arcpy.SetParameterAsText(0, persil)

if arcpy.Exists(persil_update):
    arcpy.Delete_management(persil_update)
arcpy.MakeFeatureLayer_management(persil_path, persil_update)
arcpy.ApplySymbologyFromLayer_management(persil_update, sim_update_path)
arcpy.SetParameterAsText(1, persil_update)

arcpy.AddMessage("== Menjalankan proses berhasil dilakukan. Silakan lanjutkan proses berikutnya... ==")
