import arcpy
import os

arcpy.AddMessage("== Proses dimulai ==")

# Parameter input
peta_lama_path = arcpy.GetParameterAsText(0)
peta_lama = "PersilPetaLama"
peta_baru_path = arcpy.GetParameterAsText(1)
peta_baru = "PersilPetaBaru"

# Posisi sys
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
temp_path = os.path.join(appdata, "temp")

# Tambah field luas di persil peta lama dan baru

arcpy.AddMessage("== Tambah field luas di persil peta lama dan baru ==")

list_field_lama = [f.name for f in arcpy.ListFields(peta_lama_path)]
if "ls_asal" not in list_field_lama:
    arcpy.AddField_management(peta_lama_path, "ls_asal", "DOUBLE")
arcpy.CalculateField_management(peta_lama_path, "ls_asal", "!SHAPE.AREA!", "PYTHON_9.3")

list_field_baru = [f.name for f in arcpy.ListFields(peta_baru_path)]
if "ls_asal" not in list_field_baru:
    arcpy.AddField_management(peta_baru_path, "ls_asal", "DOUBLE")
arcpy.CalculateField_management(peta_baru_path, "ls_asal", "!SHAPE.AREA!", "PYTHON_9.3")

# Select layer by location 2 arah

arcpy.AddMessage("== Select layer by location 2 arah ==")

temp_lama_path = os.path.join(temp_path, "Peta_Temp_Lama.shp")
temp_baru_path = os.path.join(temp_path, "Peta_Temp_Baru.shp")

arcpy.MakeFeatureLayer_management(peta_lama_path, peta_lama)
arcpy.SelectLayerByLocation_management(peta_lama, "CONTAINS", peta_baru_path, "", "NEW_SELECTION", "INVERT")
if arcpy.Exists(temp_lama_path):
    arcpy.Delete_management(temp_lama_path)
arcpy.CopyFeatures_management(peta_lama, temp_lama_path)
list_field_lama = [f.name for f in arcpy.ListFields(temp_lama_path)]
if "sys_ptlm" not in list_field_lama:
    arcpy.AddField_management(temp_lama_path, "sys_ptlm", "TEXT")
arcpy.CalculateField_management(temp_lama_path, "sys_ptlm", "!NIB!", "PYTHON_9.3")

arcpy.MakeFeatureLayer_management(peta_baru_path, peta_baru)
arcpy.SelectLayerByLocation_management(peta_baru, "CONTAINS", peta_lama_path, "", "NEW_SELECTION", "INVERT")
if arcpy.Exists(temp_baru_path):
    arcpy.Delete_management(temp_baru_path)
arcpy.CopyFeatures_management(peta_baru, temp_baru_path)
list_field_baru = [f.name for f in arcpy.ListFields(temp_baru_path)]
if "sys_ptbr" not in list_field_baru:
    arcpy.AddField_management(temp_baru_path, "sys_ptbr", "TEXT")
arcpy.CalculateField_management(temp_baru_path, "sys_ptbr", "!NIB!", "PYTHON_9.3")

# Proses gabung persil

arcpy.AddMessage("== Gabung persil ==")

peta_indikator_path = os.path.join(temp_path, "Peta_Indikator.shp")

if arcpy.Exists(peta_indikator_path):
    arcpy.Delete_management(peta_indikator_path)
arcpy.Merge_management([temp_baru_path, temp_lama_path], peta_indikator_path)

list_field_indikator = [f.name for f in arcpy.ListFields(peta_indikator_path)]
if "sim_sts_2b" not in list_field_indikator:
    arcpy.AddField_management(peta_indikator_path, "sim_sts_2b", "TEXT")

list_field_lama = [row[0] for row in arcpy.da.SearchCursor(temp_lama_path, ['sys_ptlm'], "sys_ptlm <> ''")]
list_field_baru = [row[0] for row in arcpy.da.SearchCursor(temp_baru_path, ['sys_ptbr'], "sys_ptbr <> ''")]

with arcpy.da.UpdateCursor(peta_indikator_path, ["NIB", "sim_sts_2b"]) as cur:
    for row in cur:
        if row[0].strip() == "":
            row[1] = "Tanpa NIB"
        elif row[0] in list_field_lama and row[0] not in list_field_baru:
            row[1] = "NIB Hapus"
        elif row[0] in list_field_lama and row[0] in list_field_baru:
            row[1] = "NIB Duplikat"
        elif row[0] not in list_field_lama and row[0] in list_field_baru:
            row[1] = "NIB Tunggal"
        cur.updateRow(row)

peta_indikator = "Peta_Indikator"
sim_path = os.path.join(appdata, "Simbologi_Layer_2B.lyr")
sim_pathbaru = os.path.join(appdata, "SimbologiPetaUpdate.lyr")
sim_pathlama = os.path.join(appdata, "SimbologiPetaLama.lyr")

if arcpy.Exists(peta_indikator):
    arcpy.Delete_management(peta_indikator)
arcpy.MakeFeatureLayer_management(peta_indikator_path, peta_indikator)
arcpy.ApplySymbologyFromLayer_management(peta_indikator, sim_path)

if arcpy.Exists("Peta_Lama"):
    arcpy.Delete_management("Peta_Lama")
arcpy.MakeFeatureLayer_management(peta_lama_path, "Peta_Lama")
arcpy.ApplySymbologyFromLayer_management("Peta_Lama", sim_pathlama)

if arcpy.Exists("Peta_Update"):
    arcpy.Delete_management("Peta_Update")
arcpy.MakeFeatureLayer_management(peta_baru_path, "Peta_Update")
arcpy.ApplySymbologyFromLayer_management("Peta_Update", sim_pathbaru)

arcpy.SetParameterAsText(2, "Peta_Lama")
arcpy.SetParameterAsText(3, "Peta_Update")
arcpy.SetParameterAsText(4, peta_indikator)

arcpy.AddMessage("== Proses selesai ==")
