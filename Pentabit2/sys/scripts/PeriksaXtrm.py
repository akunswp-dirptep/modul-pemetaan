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
simbologi_path = os.path.join(appdata, "SimbologiXtrm.lyr")

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "dataset":
        dataset_path = persil_config[1]

hasil_cluster = "Persil_Prediksi"
untukcluster_path = os.path.join(dataset_path, hasil_cluster)

field_names = [field.name for field in arcpy.ListFields(untukcluster_path)]
if 'sim_xtrm' not in field_names:
    arcpy.AddField_management(untukcluster_path, 'sim_xtrm', "TEXT")
exp = "get(!sim_cov!,!Simpang!,!MEAN_Predicted!,!Koef_Var!)"
# code_block = """
# def get(a,b,c,d):
#     if a == '0':
#         return 'Aman'
#     else:
#         if (b/c) > 30:
#             return 'Di luar simpangan baku'
#         else:
#             return 'Di dalam simpangan baku'"""

code_block = """
def get(a,b,c,d):
    if (b/c) > 0.3:
        return 'Prediksi tinggi / rendah'
    else:
        return 'Prediksi rata-rata'"""
arcpy.CalculateField_management(untukcluster_path, 'sim_xtrm', exp, "PYTHON", code_block)

if arcpy.Exists(hasil_cluster + "_Ekstrim"):
    arcpy.Delete_management(hasil_cluster + "_Ekstrim")

arcpy.MakeFeatureLayer_management(untukcluster_path, hasil_cluster + "_Ekstrim")
arcpy.ApplySymbologyFromLayer_management(hasil_cluster + "_Ekstrim", simbologi_path)

arcpy.SetParameterAsText(0, hasil_cluster + "_Ekstrim")

arcpy.AddMessage("== Proses selesai ==")
