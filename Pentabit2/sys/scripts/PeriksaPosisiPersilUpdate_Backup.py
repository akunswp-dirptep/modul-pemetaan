import os, arcpy

arcpy.AddMessage("== Proses dimulai ==")

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_jalan_path = os.path.join(appdata, "jalan.dat")
conf_persil_path = os.path.join(appdata, "persil.dat")

conf_file = open(conf_jalan_path, "r")
list_config = conf_file.readlines()
conf_file.close()

dataset_path = ""
jaringanjalan = ""
jaringanjalan_path = ""

for line in list_config:
    line = line.replace("\n", "")
    jalan_config = []
    jalan_config = line.split(",")
    if jalan_config[0] == "dataset":
        dataset_path = jalan_config[1]
    if jalan_config[0] == "jaringanjalan":
        jaringanjalan = jalan_config[1].split(";")[0]
        jaringanjalan_path = jalan_config[1].split(";")[1]

conf_file = open(conf_persil_path, "r")
list_config = conf_file.readlines()
conf_file.close()

arcpy.AddMessage("== Persiapan Awal ==")

persil = "Persil_Update"
persil_path = os.path.join(dataset_path, persil)

persilall = "Persil_Baru"
persilall_path = os.path.join(dataset_path, persilall)

leftofer = "JoinPersilJalan_2"
leftofer_path = os.path.join(dataset_path, leftofer)
posisi_dataawal = "cp_datawal_posisi"
posisi_dataawal_path = os.path.join(dataset_path, posisi_dataawal)
simbologi_path = os.path.join(appdata, "SimbologiLetakPersilUpdate.lyr")

arcpy.AddMessage("== Persiapan ==")

if arcpy.Exists(posisi_dataawal):
    arcpy.Delete_management(posisi_dataawal)
if arcpy.Exists(posisi_dataawal_path):
    arcpy.Delete_management(posisi_dataawal_path)

arcpy.CopyFeatures_management(leftofer_path, posisi_dataawal_path)

field_names = [field.name for field in arcpy.ListFields(posisi_dataawal_path)]
if 'Join_count' in field_names:
    arcpy.DeleteField_management(posisi_dataawal_path, 'Join_Count')
if 'TARGET_FID' in field_names:
    arcpy.DeleteField_management(posisi_dataawal_path, 'TARGET_FID')
if 'PanjangNearLine' not in field_names:
    arcpy.AddField_management(posisi_dataawal_path, 'PanjangNearLine', "DOUBLE")
arcpy.CalculateField_management(posisi_dataawal_path, 'PanjangNearLine', "!shape.length!", "PYTHON")

posisi_erase = "PosisiErase"
posisi_erase_path = os.path.join(dataset_path, posisi_erase)

if arcpy.Exists(posisi_erase):
    arcpy.Delete_management(posisi_erase)
if arcpy.Exists(posisi_erase_path):
    arcpy.Delete_management(posisi_erase_path)

arcpy.Erase_analysis(posisi_dataawal_path, persilall_path, posisi_erase_path)

field_names = [field.name for field in arcpy.ListFields(posisi_erase_path)]
if 'PanjangErase' not in field_names:
    arcpy.AddField_management(posisi_erase_path, 'PanjangErase', "DOUBLE")
arcpy.CalculateField_management(posisi_erase_path, 'PanjangErase', "!shape.length!", "PYTHON")
if 'Pengurangan' not in field_names:
    arcpy.AddField_management(posisi_erase_path, 'Pengurangan', "DOUBLE")
arcpy.CalculateField_management(posisi_erase_path, 'Pengurangan', "!PanjangErase! - !PanjangNearLine!", "PYTHON")

arcpy.AddMessage("== Lain-lain atau pinggir jalan ==")

if 'letak' not in field_names:
    arcpy.AddField_management(posisi_erase_path, 'letak', "TEXT")
exp = "get(!Pengurangan!)"
code_block = """
def get(b):
    if b < -0.1:
        return 'Lain-lain'
    else:
        return 'Pinggir Jalan'"""
arcpy.CalculateField_management(posisi_erase_path, 'letak', exp, "PYTHON", code_block)

temp_lain_lain = "posisi_lain_lain"
temp_lain_lain_path = os.path.join(dataset_path, temp_lain_lain)
temp_lain_lain_diss_path = os.path.join(dataset_path, "posisi_lain_lain_diss")
temp_pinggir_jalan = "posisi_pinggir_jalan"
temp_pinggir_jalan_path = os.path.join(dataset_path, temp_pinggir_jalan)
temp_pingjalan_diss_path = os.path.join(dataset_path, "posisi_pingjalan_diss")
temp_pingjalan_join1_path = os.path.join(dataset_path, "posisi_pingjalan_join1")

if arcpy.Exists(temp_lain_lain):
    arcpy.Delete_management(temp_lain_lain)
if arcpy.Exists(temp_lain_lain_path):
    arcpy.Delete_management(temp_lain_lain_path)
if arcpy.Exists(temp_pinggir_jalan):
    arcpy.Delete_management(temp_pinggir_jalan)
if arcpy.Exists(temp_pinggir_jalan_path):
    arcpy.Delete_management(temp_pinggir_jalan_path)
if arcpy.Exists(persil):
    arcpy.Delete_management(persil)

arcpy.MakeFeatureLayer_management(posisi_erase_path, temp_lain_lain, "letak = 'Lain-lain'")
arcpy.MakeFeatureLayer_management(posisi_erase_path, temp_pinggir_jalan, "letak = 'Pinggir Jalan'")

arcpy.CopyFeatures_management(temp_lain_lain, temp_lain_lain_path)

field_names = [field.name for field in arcpy.ListFields(temp_lain_lain_path)]
if 'selisih' not in field_names:
    arcpy.AddField_management(temp_lain_lain_path, 'selisih', "DOUBLE")
arcpy.CalculateField_management(temp_lain_lain_path, 'selisih', "!PanjangErase! - (!lb_jln! / 2)", "PYTHON")

if arcpy.Exists(temp_lain_lain_diss_path):
    arcpy.Delete_management(temp_lain_lain_diss_path)

arcpy.Dissolve_management(temp_lain_lain_path, temp_lain_lain_diss_path, ["IdBidang"], [["selisih", "MEAN"]], "MULTI_PART", "DISSOLVE_LINES")

arcpy.AddMessage("== Olah pinggir jalan ==")

if arcpy.Exists(temp_pingjalan_diss_path):
    arcpy.Delete_management(temp_pingjalan_diss_path)

arcpy.CopyFeatures_management(temp_pinggir_jalan, temp_pinggir_jalan_path)
arcpy.Dissolve_management(temp_pinggir_jalan_path, temp_pingjalan_diss_path, ["IdBidang"], [["LebarSisi", "SUM"]])

field_names = [field.name for field in arcpy.ListFields(persil_path)]
if "SUM_LebarSisi" in field_names:
    arcpy.DeleteField_management(persil_path, "SUM_LebarSisi")
arcpy.JoinField_management(persil_path, "IdBidang", temp_pingjalan_diss_path, "IdBidang", ["SUM_LebarSisi"])
arcpy.CalculateField_management(persil_path, "lb_dpn", "!SUM_LebarSisi!", "PYTHON")
field_names = [field.name for field in arcpy.ListFields(persil_path)]
if "SUM_LebarSisi" in field_names:
    arcpy.DeleteField_management(persil_path, "SUM_LebarSisi")

arcpy.MakeFeatureLayer_management(persil_path, persil)
arcpy.SelectLayerByLocation_management(persil, "INTERSECT", temp_pingjalan_diss_path)
arcpy.CalculateField_management(persil, 'letak', "'Pinggir Jalan'", "PYTHON")
arcpy.CalculateField_management(persil, 's_letak', "0", "PYTHON")

if arcpy.Exists(persil):
    arcpy.Delete_management(persil)
arcpy.MakeFeatureLayer_management(persil_path, persil, "s_letak > 0 or s_letak is null")
arcpy.CalculateField_management(persil, 'letak', "'Lain-lain'", "PYTHON")
arcpy.CalculateField_management(persil, 's_letak', "1", "PYTHON")

arcpy.AddMessage("== Cari hook dan normal ==")

temp_pingjalan_diss2_path = os.path.join(dataset_path, "posisi_pingjalan_diss2")
temp_pingjalan_diss3_path = os.path.join(dataset_path, "posisi_pingjalan_diss3")

if arcpy.Exists(temp_pingjalan_diss2_path):
    arcpy.Delete_management(temp_pingjalan_diss2_path)
if arcpy.Exists(temp_pingjalan_diss3_path):
    arcpy.Delete_management(temp_pingjalan_diss3_path)

arcpy.Dissolve_management(temp_pinggir_jalan_path, temp_pingjalan_diss2_path, ["IdBidang", "IdJalan"], [["LebarSisi", "SUM"], ["s_kls_jln", "SUM"]])
arcpy.Dissolve_management(temp_pingjalan_diss2_path, temp_pingjalan_diss3_path, ["IdBidang"], [["IdJalan", "COUNT"], ["SUM_s_kls_jln", "MAX"]])

temp_lyr = "temp"

if arcpy.Exists(temp_lyr):
    arcpy.Delete_management(temp_lyr)
if arcpy.Exists(persil):
    arcpy.Delete_management(persil)

arcpy.MakeFeatureLayer_management(persil_path, persil)
arcpy.MakeFeatureLayer_management(temp_pingjalan_diss3_path, temp_lyr, "COUNT_IdJalan > 1")
arcpy.SelectLayerByLocation_management(persil, "INTERSECT", temp_lyr)
arcpy.CalculateField_management(persil, 'letak', "'Hook'", "PYTHON")
arcpy.CalculateField_management(persil, 's_letak', "4", "PYTHON")

if arcpy.Exists(persil):
    arcpy.Delete_management(persil)
arcpy.MakeFeatureLayer_management(persil_path, persil, "letak= 'Pinggir Jalan'")
# arcpy.SelectLayerByAttribute_management(persil, "NEW_SELECTION", "letak= 'Pinggir Jalan'")
arcpy.CalculateField_management(persil, 'letak', "'Normal'", "PYTHON")
arcpy.CalculateField_management(persil, 's_letak', "3", "PYTHON")

arcpy.AddMessage("== Hook sisa ==")

temp_lyr = "temp_lyr"
if arcpy.Exists(temp_lyr):
    arcpy.Delete_management(temp_lyr)
arcpy.MakeFeatureLayer_management(persil_path, temp_lyr, "letak = 'Normal' or letak = 'Hook'")

persil_hook_sisa_path = os.path.join(dataset_path, "persil_hook_sisa_path")
if arcpy.Exists(persil_hook_sisa_path):
    arcpy.Delete_management(persil_hook_sisa_path)
arcpy.CopyFeatures_management(temp_lyr, persil_hook_sisa_path)

centroid_hook_sisa_path = os.path.join(dataset_path, "centroid_hook_sisa")
persilline_hook_sisa_path = os.path.join(dataset_path, "persil_line_hook_sisa")
if arcpy.Exists(centroid_hook_sisa_path):
    arcpy.Delete_management(centroid_hook_sisa_path)
if arcpy.Exists(persilline_hook_sisa_path):
    arcpy.Delete_management(persilline_hook_sisa_path)
arcpy.FeatureToPoint_management(persil_hook_sisa_path, centroid_hook_sisa_path, "INSIDE")
arcpy.PolygonToLine_management(persil_hook_sisa_path, persilline_hook_sisa_path, "IGNORE_NEIGHBORS")

field_names = [field.name for field in arcpy.ListFields(centroid_hook_sisa_path)]
if 'NEAR_DIST' in field_names:
    arcpy.DeleteField_management(centroid_hook_sisa_path, "NEAR_DIST")
if 'NEAR_X' in field_names:
    arcpy.DeleteField_management(centroid_hook_sisa_path, "NEAR_X")
if 'NEAR_Y' in field_names:
    arcpy.DeleteField_management(centroid_hook_sisa_path, "NEAR_Y")
if 'NEAR_FID' in field_names:
    arcpy.DeleteField_management(centroid_hook_sisa_path, "NEAR_FID")

arcpy.AddMessage("== Near cari lebar sementara ==")

arcpy.Near_analysis(centroid_hook_sisa_path, persilline_hook_sisa_path, 100, "LOCATION")
field_names = [field.name for field in arcpy.ListFields(centroid_hook_sisa_path)]
if 'Lebar_S' not in field_names:
    arcpy.AddField_management(centroid_hook_sisa_path, "Lebar_S", "DOUBLE")
arcpy.CalculateField_management(centroid_hook_sisa_path, "Lebar_S", "2 * !NEAR_DIST!", "PYTHON")
field_names = [field.name for field in arcpy.ListFields(persil_hook_sisa_path)]
if 'NEAR_DIST' in field_names:
    arcpy.DeleteField_management(persil_hook_sisa_path, "NEAR_DIST")
if 'NEAR_X' in field_names:
    arcpy.DeleteField_management(persil_hook_sisa_path, "NEAR_X")
if 'NEAR_Y' in field_names:
    arcpy.DeleteField_management(persil_hook_sisa_path, "NEAR_Y")
if 'NEAR_FID' in field_names:
    arcpy.DeleteField_management(persil_hook_sisa_path, "NEAR_FID")
if 'Lebar_S' in field_names:
    arcpy.DeleteField_management(persil_path, "Lebar_S")
arcpy.JoinField_management(persil_hook_sisa_path, "IdBidang", centroid_hook_sisa_path, "IdBidang", ["Lebar_S"])

junctionfinal_path = os.path.join(dataset_path, "JunctionFinal")

arcpy.AddMessage("== Near bidang ke junction ==")

arcpy.Near_analysis(persil_hook_sisa_path, junctionfinal_path, 100, "LOCATION")
arcpy.JoinField_management(persil_hook_sisa_path, "NEAR_FID", junctionfinal_path, "OBJECTID", ["MAX_s_kls_jln", "MAX_lb_jln"])

field_names = [field.name for field in arcpy.ListFields(persil_hook_sisa_path)]
if 'Posisi_H' in field_names:
    arcpy.DeleteField_management(persil_hook_sisa_path, "Posisi_H")
arcpy.AddField_management(persil_hook_sisa_path, "Posisi_H", "TEXT")
if 'S_Keliling' in field_names:
    arcpy.DeleteField_management(persil_hook_sisa_path, "S_Keliling")
arcpy.AddField_management(persil_hook_sisa_path, "S_Keliling", "DOUBLE")
if 'Posisi_N' in field_names:
    arcpy.DeleteField_management(persil_hook_sisa_path, "Posisi_N")
arcpy.AddField_management(persil_hook_sisa_path, "Posisi_N", "TEXT")
if 'Posisi_Fix' in field_names:
    arcpy.DeleteField_management(persil_hook_sisa_path, "Posisi_Fix")
arcpy.AddField_management(persil_hook_sisa_path, "Posisi_Fix", "TEXT")

arcpy.AddMessage("== Cari hook 1 ==")

if arcpy.Exists(temp_lyr):
    arcpy.Delete_management(temp_lyr)
arcpy.MakeFeatureLayer_management(persil_hook_sisa_path, temp_lyr, "letak = 'Hook'")
exp = "get(!NEAR_DIST!, !MAX_lb_jln!)"
code_block = """
def get(b,c):
    if b < (2 * c):
        return 'Hook Baru'
    else:
        return 'Normal'"""
arcpy.CalculateField_management(temp_lyr, 'Posisi_H', exp, "PYTHON", code_block)
arcpy.CalculateField_management(persil_hook_sisa_path, 'S_Keliling', "0.5 * !shape.length!", "PYTHON")

if arcpy.Exists(temp_lyr):
    arcpy.Delete_management(temp_lyr)
arcpy.MakeFeatureLayer_management(persil_hook_sisa_path, temp_lyr, "Posisi_H IS NULL OR Posisi_H = 'Normal'")

arcpy.AddMessage("== Cari hook 2 ==")

exp = "get(!lb_dpn!, !S_Keliling!, !Lebar_S!)"
code_block = """
def get(a,b,c):
    if a > (b-c):
        return 'Hook Baru'
    else:
        return 'Normal'"""
arcpy.CalculateField_management(temp_lyr, 'Posisi_N', exp, "PYTHON", code_block)

arcpy.AddMessage("== Pindah ke Posisi_Fix ==")

if arcpy.Exists(temp_lyr):
    arcpy.Delete_management(temp_lyr)
arcpy.MakeFeatureLayer_management(persil_hook_sisa_path, temp_lyr, "Posisi_H = 'Normal'")
arcpy.CalculateField_management(temp_lyr, "Posisi_Fix", "'Normal'", "PYTHON")
if arcpy.Exists(temp_lyr):
    arcpy.Delete_management(temp_lyr)
arcpy.MakeFeatureLayer_management(persil_hook_sisa_path, temp_lyr, "Posisi_H = 'Hook Baru'")
arcpy.CalculateField_management(temp_lyr, "Posisi_Fix", "'Hook'", "PYTHON")

if arcpy.Exists(temp_lyr):
    arcpy.Delete_management(temp_lyr)
arcpy.MakeFeatureLayer_management(persil_hook_sisa_path, temp_lyr, "Posisi_N = 'Normal'")
arcpy.CalculateField_management(temp_lyr, "Posisi_Fix", "'Normal'", "PYTHON")
if arcpy.Exists(temp_lyr):
    arcpy.Delete_management(temp_lyr)
arcpy.MakeFeatureLayer_management(persil_hook_sisa_path, temp_lyr, "Posisi_N = 'Hook Baru'")
arcpy.CalculateField_management(temp_lyr, "Posisi_Fix", "'Hook'", "PYTHON")

if arcpy.Exists(temp_lyr):
    arcpy.Delete_management(temp_lyr)
arcpy.MakeFeatureLayer_management(persil_hook_sisa_path, temp_lyr, "Posisi_Fix = 'Normal'")

arcpy.AddMessage("== Cari tusuk sate ==")

field_names = [field.name for field in arcpy.ListFields(persil_hook_sisa_path)]
if 'Posisi_T_N' in field_names:
    arcpy.DeleteField_management(persil_hook_sisa_path, "Posisi_T_N")
arcpy.AddField_management(persil_hook_sisa_path, "Posisi_T_N", "TEXT")
exp = "get(!NEAR_DIST!, !MAX_lb_jln!)"
code_block = """
def get(a,b):
    if a < b:
        return 'Tusuk Sate'
    else:
        return 'Normal'"""
arcpy.CalculateField_management(temp_lyr, 'Posisi_T_N', exp, "PYTHON", code_block)

if arcpy.Exists(temp_lyr):
    arcpy.Delete_management(temp_lyr)
arcpy.MakeFeatureLayer_management(persil_hook_sisa_path, temp_lyr, "Posisi_T_N = 'Tusuk Sate'")
arcpy.CalculateField_management(temp_lyr, "Posisi_Fix", "'Tusuk Sate'", "PYTHON")

arcpy.AddMessage("== Finalisasi ==")

field_names = [field.name for field in arcpy.ListFields(persil_path)]
if 'Posisi_Fix' in field_names:
    arcpy.DeleteField_management(persil_path, "Posisi_Fix")
# arcpy.AddField_management(persil_path, "Posisi_Fix", "TEXT")
if 'MAX_s_kls_jln' in field_names:
    arcpy.DeleteField_management(persil_path, "MAX_s_kls_jln")
if 'MAX_lb_jln' in field_names:
    arcpy.DeleteField_management(persil_path, "MAX_lb_jln")
arcpy.JoinField_management(persil_path, "IdBidang", persil_hook_sisa_path, "IdBidang", ["Posisi_Fix", "MAX_s_kls_jln", "MAX_lb_jln"])

if arcpy.Exists(temp_lyr):
    arcpy.Delete_management(temp_lyr)
arcpy.MakeFeatureLayer_management(persil_path, temp_lyr, "Posisi_Fix is not null")
arcpy.CalculateField_management(temp_lyr, "letak", "!Posisi_Fix!", "PYTHON")

if arcpy.Exists(temp_lyr):
    arcpy.Delete_management(temp_lyr)
arcpy.MakeFeatureLayer_management(persil_path, temp_lyr, "Posisi_Fix = 'Hook' or Posisi_Fix = 'Tusuk Sate'")
arcpy.CalculateField_management(temp_lyr, "lb_jln", "!MAX_lb_jln!", "PYTHON")
arcpy.CalculateField_management(temp_lyr, "s_kls_jln", "!MAX_s_kls_jln!", "PYTHON")

exp = "get(!Posisi_Fix!)"
code_block = """
def get(a):
    if a == 'Hook':
        return 4
    elif a == 'Normal':
        return 3
    elif a == 'Tusuk Sate':
        return 2
    else:
        return 1"""
arcpy.CalculateField_management(persil_path, 's_letak', exp, "PYTHON", code_block)

field_names = [field.name for field in arcpy.ListFields(persil_path)]
if 'Posisi_Fix' in field_names:
    arcpy.DeleteField_management(persil_path, "Posisi_Fix")
# arcpy.AddField_management(persil_path, "Posisi_Fix", "TEXT")
if 'MAX_s_kls_jln' in field_names:
    arcpy.DeleteField_management(persil_path, "MAX_s_kls_jln")
if 'MAX_lb_jln' in field_names:
    arcpy.DeleteField_management(persil_path, "MAX_lb_jln")

if arcpy.Exists(persil):
    arcpy.Delete_management(persil)
arcpy.MakeFeatureLayer_management(persil_path, persil)
arcpy.SetParameterAsText(0, persil)
arcpy.ApplySymbologyFromLayer_management(persil, simbologi_path)

arcpy.AddMessage("== Proses selesai ==")
