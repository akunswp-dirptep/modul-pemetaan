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
persil = ""
persil_path = ""
persilsplit = ""
persilsplit_path = ""
persilline = ""
persilline_path = ""
join_2 = "JoinPersilJalan_2"
join_2_path = ""

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "dataset":
        dataset_path = persil_config[1]
    if persil_config[0] == "persil":
        persil = persil_config[1].split(";")[0]
        persil_path = persil_config[1].split(";")[1]
    if persil_config[0] == "persilsplit":
        persilsplit = persil_config[1].split(";")[0]
        persilsplit_path = persil_config[1].split(";")[1]
    if persil_config[0] == "persilline":
        persilline = persil_config[1].split(";")[0]
        persilline_path = persil_config[1].split(";")[1]

arcpy.AddMessage("== Cek Kelas Jalan ==")

field_names = [field.name for field in arcpy.ListFields(persil_path)]
if 'kls_jln' not in field_names:
    arcpy.AddField_management(persil_path, "kls_jln", "TEXT")

exp = "kls(!s_kls_jln!)"
code_block = """
def kls(a):
    if a == 7:
        return 'Arteri Primer'
    elif a == 6:
        return 'Arteri Sekunder'
    elif a == 5:
        return 'Kolektor Primer'
    elif a == 4:
        return 'Kolektor Sekunder'
    elif a == 3:
        return 'Lokal Primer'
    elif a == 2:
        return 'Lokal Sekunder'
    elif a == 1:
        return 'Lokal Setapak'
    else:
        return 'Lokal Setapak'"""

arcpy.CalculateField_management(persil_path, 'kls_jln', exp, "PYTHON", code_block)

arcpy.AddMessage("== Hitung lebar depan ==")

field_names = [field.name for field in arcpy.ListFields(persil_path)]
if 'SUM_LebarSisi' in field_names:
    arcpy.DeleteField_management(persil_path, "SUM_LebarSisi")
if 'lb_dpn' not in field_names:
    arcpy.AddField_management(persil_path, "lb_dpn", "DOUBLE")

temp_pingjalan_diss_path = os.path.join(dataset_path, "posisi_pingjalan_diss")
temp_lain_lain_centroid_path = os.path.join(dataset_path, "posisi_lain_lain_centroid")

arcpy.JoinField_management(persil_path, "IdBidang", temp_pingjalan_diss_path, "IdBidang", ["SUM_LebarSisi"])

temp_lyr = "temp"
if arcpy.Exists(temp_lyr):
    arcpy.Delete_management(temp_lyr)

arcpy.MakeFeatureLayer_management(persil_path, temp_lyr, "SUM_LebarSisi IS NOT NULL")
arcpy.CalculateField_management(temp_lyr, "lb_dpn", "!SUM_LebarSisi!", "PYTHON")

if arcpy.Exists(temp_lyr):
    arcpy.Delete_management(temp_lyr)
if arcpy.Exists(temp_lain_lain_centroid_path):
    arcpy.Delete_management(temp_lain_lain_centroid_path)

arcpy.MakeFeatureLayer_management(persil_path, temp_lyr, "SUM_LebarSisi IS NULL")
arcpy.FeatureToPoint_management(temp_lyr, temp_lain_lain_centroid_path, "INSIDE")

arcpy.Near_analysis(temp_lain_lain_centroid_path, [persilline_path])
arcpy.JoinField_management(persil_path, "IdBidang", temp_lain_lain_centroid_path, "IdBidang", ["NEAR_DIST"])

if arcpy.Exists(temp_lyr):
    arcpy.Delete_management(temp_lyr)

arcpy.MakeFeatureLayer_management(persil_path, temp_lyr, "NEAR_DIST IS NOT NULL")
arcpy.CalculateField_management(temp_lyr, "lb_dpn", "2 * !NEAR_DIST!", "PYTHON")

field_names = [field.name for field in arcpy.ListFields(persil_path)]
if 'SUM_LebarSisi' in field_names:
    arcpy.DeleteField_management(persil_path, "SUM_LebarSisi")
if 'NEAR_DIST' in field_names:
    arcpy.DeleteField_management(persil_path, "NEAR_DIST")

if arcpy.Exists(persil):
    arcpy.Delete_management(persil)
arcpy.MakeFeatureLayer_management(persil_path, persil)
arcpy.SetParameterAsText(0, persil)

arcpy.AddMessage("== Proses selesai ==")
