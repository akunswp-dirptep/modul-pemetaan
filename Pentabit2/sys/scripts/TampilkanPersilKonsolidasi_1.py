import os, arcpy

arcpy.AddMessage("== Proses dimulai ==")

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_persil_path = os.path.join(appdata, "persil.dat")

# in_fc = arcpy.GetParameter(0)
dataset_path = ""
sim_path = os.path.join(appdata, "SimbologiPersilKonsolidasi.lyr")

conf_file = open(conf_persil_path, "r")
list_config = conf_file.readlines()
conf_file.close()

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "dataset":
        dataset_path = persil_config[1]

persil_konsolidasi = "Persil_Konsolidasi"
persil_konsolidasi_path = os.path.join(dataset_path, persil_konsolidasi)

# if arcpy.Exists(persil_konsolidasi):
#     arcpy.Delete_management(persil_konsolidasi)
# if arcpy.Exists(persil_konsolidasi_path):
#     arcpy.Delete_management(persil_konsolidasi_path)
#
# arcpy.FeatureClassToFeatureClass_conversion(in_fc, dataset_path, persil_konsolidasi)

field_names = [field.name for field in arcpy.ListFields(persil_konsolidasi_path)]
if 'obj_konsol' not in field_names:
    arcpy.AddField_management(persil_konsolidasi_path, 'obj_konsol', "TEXT")

with arcpy.da.UpdateCursor(persil_konsolidasi_path, ["obj_konsol"]) as rows:
    for row in rows:
        if row[0] == "Konsolidasi":
            row[0] = "Konsolidasi"
        else:
            row[0] = "Non Konsolidasi"
        rows.updateRow(row)
del rows, row

if arcpy.Exists(persil_konsolidasi):
    arcpy.Delete_management(persil_konsolidasi)
arcpy.MakeFeatureLayer_management(persil_konsolidasi_path, persil_konsolidasi)
arcpy.ApplySymbologyFromLayer_management(persil_konsolidasi, sim_path)
arcpy.SetParameterAsText(0, persil_konsolidasi)

arcpy.AddMessage("== Proses selesai ==")
