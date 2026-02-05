import os
import arcpy

arcpy.AddMessage("== Proses dimulai ==")

in_persil_update = arcpy.GetParameterAsText(0)
in_persil_lama = arcpy.GetParameterAsText(1)

persil_lama = "Persil_Lama"
persil_update = "Persil_Update"

appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
lama_sim_path = os.path.join(appdata, "Simbologi_Persil_Lama.lyr") #tanya mba helda nanti tentang simbiologi
update_sim = os.path.join(appdata, "Simbologi_Persil_Updating.lyr") #tanya mba helda nanti tentang simbiologi

if arcpy.Exists(persil_update):
    arcpy.Delete_management(persil_update)
arcpy.MakeFeatureLayer_management(in_persil_update, persil_update)
#arcpy.ApplySymbologyFromLayer_management(persil_update, update_sim)

if arcpy.Exists(persil_lama):
    arcpy.Delete_management(persil_lama)
arcpy.MakeFeatureLayer_management(in_persil_lama, persil_lama)
#arcpy.ApplySymbologyFromLayer_management(in_persil_lama, lama_sim_path)

arcpy.SetParameterAsText(2, persil_update)
arcpy.SetParameterAsText(3, persil_lama)

arcpy.AddMessage("== Proses selesai ==")
