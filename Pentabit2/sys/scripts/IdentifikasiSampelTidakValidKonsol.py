import os, arcpy

arcpy.AddMessage("== Proses dimulai ==")

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_jalan_path = os.path.join(appdata, "persil.dat")

conf_file = open(conf_jalan_path, "r")
list_config = conf_file.readlines()
conf_file.close()

dataset_path = ""
persil_baru = "Persil_Konsolidasi"
persil_baru_path = ""
titiksampel = "Titik_Sampel_Konsolidasi"
sampelskorupdate = "Sampel_Skor_Valid"
sim_path = os.path.join(appdata, "SimbologiSampelValid.lyr")

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "dataset":
        dataset_path = persil_config[1]

persil_baru_path = os.path.join(dataset_path, persil_baru)
titiksampel_path = os.path.join(dataset_path, titiksampel)
outjoin = os.path.join(dataset_path, sampelskorupdate)

if arcpy.Exists(outjoin):
    arcpy.Delete_management(outjoin)

arcpy.SpatialJoin_analysis(persil_baru_path, titiksampel_path, outjoin)

list_field_update = [f.name for f in arcpy.ListFields(outjoin)]
if 'status_sam' not in list_field_update:
    arcpy.AddField_management(outjoin, 'status_sam', "TEXT")

fields = ['obj_konsol', 'status_sam']

with arcpy.da.UpdateCursor(outjoin, fields) as rows:
    for row in rows:
        if row[0] == "Konsolidasi":
            row[1] = "Tidak Valid"
        else:
            row[1] = "Valid"
        rows.updateRow(row)
del rows, row

if arcpy.Exists(sampelskorupdate):
    arcpy.Delete_management(sampelskorupdate)

arcpy.MakeFeatureLayer_management(outjoin, sampelskorupdate)
arcpy.SelectLayerByAttribute_management(sampelskorupdate, "NEW_SELECTION", "NILAI IS NULL")
arcpy.DeleteFeatures_management(sampelskorupdate)

if arcpy.Exists(sampelskorupdate):
    arcpy.Delete_management(sampelskorupdate)
arcpy.MakeFeatureLayer_management(outjoin, sampelskorupdate)
arcpy.ApplySymbologyFromLayer_management(sampelskorupdate, sim_path)
arcpy.SetParameterAsText(0, sampelskorupdate)

arcpy.AddMessage("== Proses Selesai ==")
