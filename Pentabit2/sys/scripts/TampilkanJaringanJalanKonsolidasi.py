import os
import arcpy

arcpy.AddMessage("== Proses dimulai ==")

in_jaringan_jalan = arcpy.GetParameterAsText(0)

jaringan_jalan = "Jaringan_Jalan"
jaringan_jalan_path = ""
dataset_path = ""
peta_baru = "Persil_Konsolidasi"
peta_baru_path = ""

JaringanJalanTopoUpdate = "Topo_Jaringan_Jalan_Update"
JaringanJalanTopoAwal = "TopologiJaringanJalan"
JaringanJalanTopoTaru = "Topo_Jaringan_Jalan_Taru"
JaringanJalanTopoKonsol = "Topo_Jaringan_Jalan_Konsolidasi"

appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
persil_conf_path = os.path.join(appdata, "jalan.dat")
conf_file = open(persil_conf_path, "r")
list_config = conf_file.readlines()
conf_file.close()

for line in list_config:
    line = line.replace("\n", "")
    jalan_config = []
    jalan_config = line.split(",")
    if jalan_config[0] == "dataset":
        dataset_path = jalan_config[1]

# tempdata = os.path.join(appdata, "temp")
no_sim_path = os.path.join(appdata, "SimbologiJaringanJalanUpdate.lyr")

#out_shp = "Peta_Jaringan_Jalan_Update"
#out_path = os.path.join(tempdata, out_shp)
#out_path = os.path.join(dataset_path, out_shp)
jaringan_jalan_path = os.path.join(dataset_path, jaringan_jalan)
peta_baru_path = os.path.join(dataset_path, peta_baru)

jarjaltop_update_path = os.path.join(dataset_path, JaringanJalanTopoUpdate)
jarjaltop_awal_path = os.path.join(dataset_path, JaringanJalanTopoAwal)
jarjaltop_taru_path = os.path.join(dataset_path, JaringanJalanTopoTaru)
jarjaltop_konsol_path = os.path.join(dataset_path, JaringanJalanTopoKonsol)

arcpy.AddMessage("== Simpan input jaringan jalan ke gdb ==")

if (jaringan_jalan_path != in_jaringan_jalan):
    if arcpy.Exists(jarjaltop_update_path):
        arcpy.Delete_management(jarjaltop_update_path)
    if arcpy.Exists(jarjaltop_awal_path):
        arcpy.Delete_management(jarjaltop_awal_path)
    if arcpy.Exists(jarjaltop_taru_path):
        arcpy.Delete_management(jarjaltop_taru_path)
    if arcpy.Exists(jarjaltop_konsol_path):
        arcpy.Delete_management(jarjaltop_konsol_path)
    if arcpy.Exists(jaringan_jalan_path):
        arcpy.Delete_management(jaringan_jalan_path)
    arcpy.FeatureClassToFeatureClass_conversion(in_jaringan_jalan, dataset_path, jaringan_jalan)

arcpy.AddMessage("== Tambah field status_jal ==")

list_names = [f.name for f in arcpy.ListFields(jaringan_jalan_path)]
if "status_jal" in list_names:
    arcpy.DeleteField_management(jaringan_jalan_path, "status_jal")
arcpy.AddField_management(jaringan_jalan_path, "status_jal", "Text")
arcpy.CalculateField_management(jaringan_jalan_path, "status_jal", "'Tetap'", "PYTHON")

arcpy.AddMessage("== Pindahkan shapefile ke temp ==")

# if arcpy.Exists(out_path):
#     arcpy.Delete_management(out_path)
#
# arcpy.CopyFeatures_management(in_jaringan_jalan, out_path)

if arcpy.Exists(jaringan_jalan):
    arcpy.Delete_management(jaringan_jalan)

arcpy.MakeFeatureLayer_management(jaringan_jalan_path, jaringan_jalan)
arcpy.ApplySymbologyFromLayer_management(jaringan_jalan, no_sim_path)

if arcpy.Exists(peta_baru):
    arcpy.Delete_management(peta_baru)

sim_indikator_akhir = os.path.join(appdata, "SimbologiPersilKonsolidasi.lyr")
arcpy.MakeFeatureLayer_management(peta_baru_path, peta_baru)
arcpy.ApplySymbologyFromLayer_management(peta_baru, sim_indikator_akhir)

arcpy.SetParameterAsText(1, jaringan_jalan)
arcpy.SetParameterAsText(2, peta_baru)

arcpy.AddMessage("== Proses selesai ==")
