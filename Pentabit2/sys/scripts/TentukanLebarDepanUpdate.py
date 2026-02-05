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

persil = "Persil_Baru"
persil_path = os.path.join(dataset_path, persil)
persilline = "PersilLineUpdate"
persilline_path = os.path.join(dataset_path, persilline)

arcpy.AddMessage("== Hitung lebar depan ==")

field_names = [field.name for field in arcpy.ListFields(persil_path)]
if 'SUM_LebarSisi' in field_names:
    arcpy.DeleteField_management(persil_path, "SUM_LebarSisi")

temp_pingjalan_diss_path = os.path.join(dataset_path, "posisi_pingjalan_diss")
temp_lain_lain_centroid_path = os.path.join(dataset_path, "posisi_lain_lain_centroid")

arcpy.JoinField_management(persil_path, "IdBidang", temp_pingjalan_diss_path, "IdBidang", ["SUM_LebarSisi"])

temp_lyr = "temp"
if arcpy.Exists(temp_lyr):
    arcpy.Delete_management(temp_lyr)

arcpy.MakeFeatureLayer_management(persil_path, temp_lyr, "SUM_LebarSisi IS NOT NULL AND status_per = 'update'")
arcpy.CalculateField_management(temp_lyr, "lb_dpn", "!SUM_LebarSisi!", "PYTHON")

if arcpy.Exists(temp_lyr):
    arcpy.Delete_management(temp_lyr)
if arcpy.Exists(temp_lain_lain_centroid_path):
    arcpy.Delete_management(temp_lain_lain_centroid_path)

arcpy.MakeFeatureLayer_management(persil_path, temp_lyr, "SUM_LebarSisi IS NULL AND status_per = 'update'")
arcpy.FeatureToPoint_management(temp_lyr, temp_lain_lain_centroid_path, "INSIDE")

arcpy.Near_analysis(temp_lain_lain_centroid_path, [persilline_path])
arcpy.JoinField_management(persil_path, "IdBidang", temp_lain_lain_centroid_path, "IdBidang", ["NEAR_DIST"])

if arcpy.Exists(temp_lyr):
    arcpy.Delete_management(temp_lyr)

arcpy.MakeFeatureLayer_management(persil_path, temp_lyr, "NEAR_DIST IS NOT NULL AND status_per = 'update'")
arcpy.CalculateField_management(temp_lyr, "lb_dpn", "2 * !NEAR_DIST!", "PYTHON")

field_names = [field.name for field in arcpy.ListFields(persil_path)]
if 'SUM_LebarSisi' in field_names:
    arcpy.DeleteField_management(persil_path, "SUM_LebarSisi")
if 'NEAR_DIST' in field_names:
    arcpy.DeleteField_management(persil_path, "NEAR_DIST")

field_names = [field.name for field in arcpy.ListFields(persil_path)]
if "SimLbDpn" not in field_names:
    arcpy.AddField_management(persil_path, "SimLbDpn", "TEXT")

with arcpy.da.UpdateCursor(persil_path, ["lb_dpn", "SimLbDpn"]) as rows:
    for row in rows:
        if not row[0]:
            row[0] = 0
            row[1] = "0"
        else:
            if row[0] >= 0 and row[0] <= 3:
                row[1] = "3"
            elif row[0] > 3:
                row[1] = "3+"
            else:
                row[1] = "0"
        rows.updateRow(row)
del rows, row

if 'sim_l_dpn' not in field_names:
    arcpy.AddField_management(persil_path, 'sim_l_dpn', "TEXT")
exp = "get(!lb_dpn!)"
code_block = """
def get(b):
    if b > 3:
        return '1'
    else:
        return '0'"""
arcpy.CalculateField_management(persil_path, 'sim_l_dpn', exp, "PYTHON", code_block)

simbologi_path = os.path.join(appdata, "SimbologiLebarDepanUpdate.lyr")

if arcpy.Exists(persil):
    arcpy.Delete_management(persil)
arcpy.MakeFeatureLayer_management(persil_path, persil)
arcpy.ApplySymbologyFromLayer_management(persil, simbologi_path)
arcpy.SetParameterAsText(0, persil)

arcpy.AddMessage("== Proses selesai ==")
