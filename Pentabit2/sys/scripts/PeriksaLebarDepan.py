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

field_names = [field.name for field in arcpy.ListFields(persil_path)]
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
if arcpy.Exists(persil):
    arcpy.Delete_management(persil)
arcpy.MakeFeatureLayer_management(persil_path, persil)
arcpy.ApplySymbologyFromLayer_management(persil, os.path.join(appdata, "SimbologiLebarDepan.lyr"))
arcpy.SetParameterAsText(0, persil)

arcpy.AddMessage("== Proses selesai ==")
