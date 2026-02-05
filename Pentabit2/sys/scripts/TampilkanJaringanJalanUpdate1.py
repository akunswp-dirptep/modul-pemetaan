import os
import arcpy

arcpy.AddMessage("== Proses dimulai ==")

in_jaringan_jalan = arcpy.GetParameterAsText(0)
in_persil_update = arcpy.GetParameterAsText(1)

jaringan_jalan = "Jaringan_Jalan"
persil_update = "Persil_Update"

appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
no_sim_path = os.path.join(appdata, "Simbologi_Jalan_Updating.lyr")
no_sim = os.path.join(appdata, "Simbologi_Persil_Updating_Final.lyr")

list_names = [f.name for f in arcpy.ListFields(in_jaringan_jalan)]
if "sts_jalan" not in list_names:
    arcpy.AddField_management(in_jaringan_jalan, "sts_jalan", "Text")
with arcpy.da.UpdateCursor(in_jaringan_jalan, "sts_jalan") as cur:
    for row in cur:
        row[0] = "Tetap"
        cur.updateRow(row)

if arcpy.Exists(jaringan_jalan):
    arcpy.Delete_management(jaringan_jalan)
arcpy.MakeFeatureLayer_management(in_jaringan_jalan, jaringan_jalan)
arcpy.ApplySymbologyFromLayer_management(jaringan_jalan, no_sim_path)

if arcpy.Exists(persil_update):
    arcpy.Delete_management(persil_update)
arcpy.MakeFeatureLayer_management(in_persil_update, persil_update)
arcpy.ApplySymbologyFromLayer_management(persil_update, no_sim)

arcpy.SetParameterAsText(2, jaringan_jalan)
arcpy.SetParameterAsText(3, persil_update)

arcpy.AddMessage("== Proses selesai ==")
