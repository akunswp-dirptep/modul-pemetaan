import arcpy, os, math

arcpy.AddMessage("== Proses Dimulai ==")

# get parameter
persillama_path = arcpy.GetParameterAsText(0)
persillama = "PersilLama"
persilbaru_path = arcpy.GetParameterAsText(1)
persilbaru = "PersilBaru"

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_hasilLama_path = os.path.join(appdata, "temp", "hasil_lama.shp")
conf_hasilBaru_path = os.path.join(appdata, "temp", "hasil_baru.shp")
conf_hasilMerge_path = os.path.join(appdata, "temp", "Indikator.shp")

list_names = [f.name for f in arcpy.ListFields(persillama_path)]
if "X1" not in list_names:
    arcpy.AddField_management(persillama_path, "X1", "DOUBLE")
if "Y1" not in list_names:
    arcpy.AddField_management(persillama_path, "Y1", "DOUBLE")
if "Luas_ori" not in list_names:
    arcpy.AddField_management(persillama_path, "Luas_ori", "DOUBLE")
arcpy.CalculateField_management(persillama_path, "X1", "!SHAPE.CENTROID.X!", "PYTHON_9.3")
arcpy.CalculateField_management(persillama_path, "Y1", "!SHAPE.CENTROID.Y!", "PYTHON_9.3")
arcpy.CalculateField_management(persillama_path, "Luas_ori", "!SHAPE.AREA!", "PYTHON_9.3")

list_names = [f.name for f in arcpy.ListFields(persilbaru_path)]
if "X1" not in list_names:
    arcpy.AddField_management(persilbaru_path, "X1", "DOUBLE")
if "Y1" not in list_names:
    arcpy.AddField_management(persilbaru_path, "Y1", "DOUBLE")
if "Luas_ori" not in list_names:
    arcpy.AddField_management(persilbaru_path, "Luas_ori", "DOUBLE")
arcpy.CalculateField_management(persilbaru_path, "X1", "!SHAPE.CENTROID.X!", "PYTHON_9.3")
arcpy.CalculateField_management(persilbaru_path, "Y1", "!SHAPE.CENTROID.Y!", "PYTHON_9.3")
arcpy.CalculateField_management(persilbaru_path, "Luas_ori", "!SHAPE.AREA!", "PYTHON_9.3")

arcpy.MakeFeatureLayer_management(persillama_path, persillama)
arcpy.SelectLayerByLocation_management(persillama, "CONTAINS", persilbaru_path, "", "NEW_SELECTION", "INVERT")
if arcpy.Exists(conf_hasilLama_path):
    arcpy.Delete_management(conf_hasilLama_path)
arcpy.CopyFeatures_management(persillama, conf_hasilLama_path)

arcpy.MakeFeatureLayer_management(persilbaru_path, persilbaru)
arcpy.SelectLayerByLocation_management(persilbaru, "CONTAINS", persillama_path, "", "NEW_SELECTION", "INVERT")
if arcpy.Exists(conf_hasilBaru_path):
    arcpy.Delete_management(conf_hasilBaru_path)
arcpy.CopyFeatures_management(persilbaru, conf_hasilBaru_path)

field_nameslama = [f.name for f in arcpy.ListFields(conf_hasilLama_path)]
if "dr_pt_lm" not in field_nameslama :
   arcpy.AddField_management(persillama_path, "dr_pt_lm", "Text")
arcpy.CalculateField_management(persillama_path, "dr_pt_lm", "!NIB!", "PYTHON_9.3")

field_namesbaru = [f.name for f in arcpy.ListFields(conf_hasilBaru_path)]
if "dr_pt_br" not in field_namesbaru :
   arcpy.AddField_management(persilbaru_path, "dr_pt_br", "Text")
arcpy.CalculateField_management(persilbaru_path, "dr_pt_br", "!NIB!", "PYTHON_9.3")

list_dari_lama = [row[0] for row in arcpy.da.SearchCursor(persillama_path, ['dr_pt_lm'], "dr_pt_lm <> ''")]
list_dari_baru = [row[0] for row in arcpy.da.SearchCursor(persilbaru_path, ['dr_pt_br'], "dr_pt_br <> ''")]

if arcpy.Exists(conf_hasilMerge_path):
    arcpy.Delete_management(conf_hasilMerge_path)
arcpy.Merge_management([persillama, persilbaru], conf_hasilMerge_path)

field_merge = [f.name for f in arcpy.ListFields(conf_hasilMerge_path)]
if "update" not in field_merge:
    arcpy.AddField_management(conf_hasilMerge_path, "update", "TEXT")
if "Luas_baru" not in field_merge:
    arcpy.AddField_management(conf_hasilMerge_path, "Luas_baru", "TEXT")
if "X2" not in field_merge:
    arcpy.AddField_management(conf_hasilMerge_path, "X2", "DOUBLE")
if "Y2" not in field_merge:
    arcpy.AddField_management(conf_hasilMerge_path, "Y2", "DOUBLE")
if "abs_l" not in field_merge:
    arcpy.AddField_management(conf_hasilMerge_path, "abs_l", "DOUBLE")
if "sqr_c" not in field_merge:
    arcpy.AddField_management(conf_hasilMerge_path, "sqr_c", "DOUBLE")
if "sim_updt" not in field_merge:
    arcpy.AddField_management(conf_hasilMerge_path, "sim_updt", "TEXT")

desc = arcpy.Describe(conf_hasilMerge_path)
shapename = desc.ShapeFieldName
sel_fields = ['NIB', 'SHAPE@AREA', 'SHAPE@X', 'SHAPE@Y', 'Luas_ori', 'Luas_baru', 'X1', 'Y1', 'X2', 'Y2', 'abs_l', 'sqr_c', 'update', 'sim_updt']

with arcpy.da.UpdateCursor(conf_hasilMerge_path, sel_fields) as cur:
    for row in cur:
        row[5] = row[1]
        row[8] = row[2]
        row[9] = row[3]
        abs_c = abs(row[4]-row[1])
        row[10] = abs_c
        sqr_c = math.sqrt((math.pow((row[6]-row[2]), 2) + math.pow((row[7]-row[3]), 2)))
        row[11] = sqr_c
        if abs_c > 5 or sqr_c > math.sqrt(5):
            row[12] = "update"
        else:
            row[12] = "tetap"
        nib = row[0]
        if nib.strip() == '':
            row[13] = "kuning"
        elif nib in list_dari_baru and nib not in list_dari_lama:
            row[13] = "hijau"
        else:
            row[13] = "merah"
        cur.updateRow(row)

indikator_sim_path = os.path.join(appdata, "indikator.lyr")
if arcpy.Exists("Indikator"):
    arcpy.Delete_management("Indikator")
arcpy.MakeFeatureLayer_management(conf_hasilMerge_path, "Indikator")
arcpy.ApplySymbologyFromLayer_management("Indikator", indikator_sim_path)
arcpy.SetParameterAsText(2, "Indikator")

arcpy.AddMessage("== Proses Selesai ==")