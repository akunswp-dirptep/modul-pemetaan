import os
import arcpy

arcpy.AddMessage("== Proses dimulai ==")

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
persil_conf_path = os.path.join(appdata, "persil.dat")
conf_file = open(persil_conf_path, "r")
list_config = conf_file.readlines()
conf_file.close()

dataset_path = ""

for line in list_config:
    line = line.replace("\n", "")
    jalan_config = []
    jalan_config = line.split(",")
    if jalan_config[0] == "dataset":
        dataset_path = jalan_config[1]

tempdata = os.path.join(appdata, "temp")
sim_path = os.path.join(appdata, "SimbologiPersilKonsolidasi.lyr")

# peta_persil = os.path.join(tempdata, "Peta_Akhir")
peta_persil = "Persil_Konsolidasi"
# peta_persil_path = os.path.join(tempdata, "Peta_Akhir.shp")\
peta_persil_path = os.path.join(dataset_path, peta_persil)

field_names = [field.name for field in arcpy.ListFields(peta_persil_path)]
if 'ls_tnh' not in field_names:
    arcpy.AddField_management(peta_persil_path, 'ls_tnh', "DOUBLE")

persil_buat_luas = "Persil_Hitung_Luas"
persil_buat_luas_path = os.path.join(dataset_path, persil_buat_luas)

if arcpy.Exists(persil_buat_luas):
    arcpy.Delete_management(persil_buat_luas)
if arcpy.Exists(persil_buat_luas_path):
    arcpy.Delete_management(persil_buat_luas_path)

arcpy.MakeFeatureLayer_management(peta_persil_path, persil_buat_luas, "obj_konsol='Konsolidasi'")
arcpy.CalculateField_management(persil_buat_luas, 'ls_tnh', "!shape.area!", "PYTHON")

if arcpy.Exists(peta_persil):
    arcpy.Delete_management(peta_persil)

arcpy.MakeFeatureLayer_management(peta_persil_path, peta_persil)
arcpy.ApplySymbologyFromLayer_management(peta_persil, sim_path)
arcpy.SetParameterAsText(0, peta_persil)

arcpy.AddMessage("== Proses selesai ==")
