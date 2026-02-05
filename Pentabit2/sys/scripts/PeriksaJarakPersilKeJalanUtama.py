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
persil = ""
persil_path = ""
simbologi_path = ""

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "persil":
        persil = persil_config[1].split(";")[0]
        persil_path = persil_config[1].split(";")[1]

j_5 = "Jarak_Persil_Ke_ArteriPrimer"
j_4 = "Jarak_Persil_Ke_ArteriSekunder"
j_3 = "Jarak_Persil_Ke_KolektorPrimer"
j_2 = "Jarak_Persil_Ke_KolektorSekunder"

field_names = [field.name for field in arcpy.ListFields(persil_path)]
if 'J_Kls5' in field_names:
    if 'sim_j_5' not in field_names:
        arcpy.AddField_management(persil_path, 'sim_j_5', "TEXT")
    exp = "get(!J_Kls5!)"
    code_block = """
def get(b):
    if b == 0:
        return '0'
    else:
        return '1'"""
    arcpy.CalculateField_management(persil_path, 'sim_j_5', exp, "PYTHON", code_block)
    if arcpy.Exists(j_5):
        arcpy.Delete_management(j_5)
    arcpy.MakeFeatureLayer_management(persil_path, j_5)
    arcpy.ApplySymbologyFromLayer_management(j_5, os.path.join(appdata, "SimbologiEditJarakKls5.lyr"))
    arcpy.SetParameterAsText(3, j_5)

if 'J_Kls4' in field_names:
    if 'sim_j_4' not in field_names:
        arcpy.AddField_management(persil_path, 'sim_j_4', "TEXT")
    exp = "get(!J_Kls4!)"
    code_block = """
def get(b):
    if b == 0:
        return '0'
    else:
        return '1'"""
    arcpy.CalculateField_management(persil_path, 'sim_j_4', exp, "PYTHON", code_block)
    if arcpy.Exists(j_4):
        arcpy.Delete_management(j_4)
    arcpy.MakeFeatureLayer_management(persil_path, j_4)
    arcpy.ApplySymbologyFromLayer_management(j_4, os.path.join(appdata, "SimbologiEditJarakKls4.lyr"))
    arcpy.SetParameterAsText(2, j_4)

if 'J_Kls3' in field_names:
    if 'sim_j_3' not in field_names:
        arcpy.AddField_management(persil_path, 'sim_j_3', "TEXT")
    exp = "get(!J_Kls3!)"
    code_block = """
def get(b):
    if b == 0:
        return '0'
    else:
        return '1'"""
    arcpy.CalculateField_management(persil_path, 'sim_j_3', exp, "PYTHON", code_block)
    if arcpy.Exists(j_3):
        arcpy.Delete_management(j_3)
    arcpy.MakeFeatureLayer_management(persil_path, j_3)
    arcpy.ApplySymbologyFromLayer_management(j_3, os.path.join(appdata, "SimbologiEditJarakKls3.lyr"))
    arcpy.SetParameterAsText(1, j_3)

if 'J_Kls2' in field_names:
    if 'sim_j_2' not in field_names:
        arcpy.AddField_management(persil_path, 'sim_j_2', "TEXT")
    exp = "get(!J_Kls2!)"
    code_block = """
def get(b):
    if b == 0:
        return '0'
    else:
        return '1'"""
    arcpy.CalculateField_management(persil_path, 'sim_j_2', exp, "PYTHON", code_block)
    if arcpy.Exists(j_2):
        arcpy.Delete_management(j_2)
    arcpy.MakeFeatureLayer_management(persil_path, j_2)
    arcpy.ApplySymbologyFromLayer_management(j_2, os.path.join(appdata, "SimbologiEditJarakKls2.lyr"))
    arcpy.SetParameterAsText(0, j_2)

arcpy.AddMessage("== Proses selesai ==")
