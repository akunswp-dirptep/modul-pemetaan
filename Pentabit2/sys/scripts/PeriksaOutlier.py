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
simbologi_path = os.path.join(appdata, "SimbologiOutlier.lyr")

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "dataset":
        dataset_path = persil_config[1]

hasil_cluster = "Persil_Prediksi"
untukcluster_path = os.path.join(dataset_path, hasil_cluster)

field_names = [field.name for field in arcpy.ListFields(untukcluster_path)]
if 'sim_type' not in field_names:
    arcpy.AddField_management(untukcluster_path, 'sim_type', "TEXT")
exp = "get(!oCOType!)"
# code_block = """
# def get(a):
#     if a in ['HH','LL','HL','LH']:
#         return '0'
#     else:
#         return '1'"""
code_block = """
def get(a):
    if a == 'HH':
        return '1'
    elif a == 'LL':
        return '2'
    elif a == 'HL':
        return '3'
    elif a == 'LH':
        return '4'
    else:
        return '5'"""
arcpy.CalculateField_management(untukcluster_path, 'sim_type', exp, "PYTHON", code_block)

if arcpy.Exists(hasil_cluster + "_Outlier"):
    arcpy.Delete_management(hasil_cluster + "_Outlier")

arcpy.MakeFeatureLayer_management(untukcluster_path, hasil_cluster + "_Outlier")
arcpy.ApplySymbologyFromLayer_management(hasil_cluster + "_Outlier", simbologi_path)

arcpy.SetParameterAsText(0, hasil_cluster + "_Outlier")

arcpy.AddMessage("== Proses selesai ==")
