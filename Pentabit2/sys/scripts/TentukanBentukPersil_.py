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
simbologi_path = os.path.join(appdata, "SimbologiBentukPersil.lyr")
persil_line_path = ""
persil_split_path = ""

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
        persil_split_path = persil_config[1].split(";")[1]

persil_dissolve_bentuk = "PersilDissolveBentuk"
persil_dissolve_bentuk_path = os.path.join(dataset_path, persil_dissolve_bentuk)

if arcpy.Exists(persil_dissolve_bentuk):
    arcpy.Delete_management(persil_dissolve_bentuk)
if arcpy.Exists(persil_dissolve_bentuk_path):
    arcpy.Delete_management(persil_dissolve_bentuk_path)

arcpy.Dissolve_management(persil_split_path, persil_dissolve_bentuk_path, ["IdBidang"], [["ATrans", "RANGE"]], "MULTI_PART", "DISSOLVE_LINES")

field_names = [field.name for field in arcpy.ListFields(persil_path)]
if 'Bentuk' not in field_names:
    arcpy.AddField_management(persil_path, 'bentuk', "TEXT")
if 'S_Bentuk' not in field_names:
    arcpy.AddField_management(persil_path, 's_bentuk', "DOUBLE")
if 'Range_ATrans' in field_names:
    arcpy.DeleteField_management(persil_path, 'Range_ATrans')

arcpy.JoinField_management(persil_path, 'IdBidang', persil_dissolve_bentuk_path, 'IdBidang', ["Range_ATrans"])

exp = "trans(float(!Range_ATrans!))"
code_block = """
def trans(trans):
    if trans < 16.3:
        return 'Persegi'
    elif trans >= 16.3 and trans <= 58:
        return 'Trapesium'
    else:
        return 'Tidak beraturan'"""

arcpy.CalculateField_management(persil_path, 'bentuk', exp, "PYTHON", code_block)

exp = "skor(!bentuk!)"
code_block = """
def skor(b):
    if b == 'Persegi':
        return 3
    elif b == 'Trapesium':
        return 2
    else:
        return 1"""

arcpy.CalculateField_management(persil_path, 's_bentuk', exp, "PYTHON", code_block)

if arcpy.Exists(persil):
    arcpy.Delete_management(persil)

arcpy.MakeFeatureLayer_management(persil_path, persil)
arcpy.ApplySymbologyFromLayer_management(persil, simbologi_path)

arcpy.SetParameterAsText(0, persil)

# cur = arcpy.UpdateCursor(persil_path)
#
# try:
#     for row in cur:
#         sercur = arcpy.SearchCursor(persil_dissolve_bentuk_path, "IdBidang=" + `row.IdBidang`)
#         for row2 in sercur:
#             if row2.Range_ATrans < 16.3:
#                 row.Bentuk = 'Persegi'
#                 row.SkorBentuk = 3
#             elif row2.Range_ATrans >= 16.3 and row2.Range_ATrans <= 58:
#                 row.Bentuk = 'Trapesium'
#                 row.SkorBentuk = 2
#             else:
#                 row.Bentuk = 'Tidak beraturan'
#                 row.SkorBentuk = 1
#         cur.updateRow(row)
#         del sercur
# except:
#     del cur
#     exit(1)
# del cur

# exp = "trans(float(!Range_ATrans!))"
# code_block = """
# def trans(trans):
#     if trans < 16.3:
#         return 'Persegi'
#     elif trans >= 16.3 and trans <= 58:
#         return 'Trapesium'
#     else:
#         return 'Tidak beraturan'"""
#
# field_names = [field.name for field in arcpy.ListFields(persil_dissolve_bentuk_path)]
# if u'Bentuk' not in field_names:
#     arcpy.AddField_management(persil_dissolve_bentuk_path, u'Bentuk', "TEXT")
#
# arcpy.CalculateField_management(persil_dissolve_bentuk_path, u'Bentuk', exp, "PYTHON", code_block)

arcpy.AddMessage("== Proses Selesai ==")
