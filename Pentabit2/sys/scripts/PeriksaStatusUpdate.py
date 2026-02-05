import arcpy, os, math

arcpy.AddMessage("== Proses dimulai ==")

dataset_path = ""

appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
persil_conf_path = os.path.join(appdata, "persil.dat")
conf_file = open(persil_conf_path, "r")
list_config = conf_file.readlines()
conf_file.close()

for line in list_config:
    line = line.replace("\n", "")
    jalan_config = []
    jalan_config = line.split(",")
    if jalan_config[0] == "dataset":
        dataset_path = jalan_config[1]

tempdata = os.path.join(appdata, "temp")

arcpy.AddMessage("== Join dengan Persil Update ==")

peta_baru = "PersilPetaBaru"
peta_lama = "PersilPetaLama"
peta_indikator = "Indikator_Perubahan_Persil"
peta_indikator_path = os.path.join(dataset_path, peta_indikator)
peta_indikator_update_path = os.path.join(dataset_path, "Peta_Indikator_Update")
peta_update_path = os.path.join(dataset_path, peta_baru)
peta_lama_path = os.path.join(dataset_path, peta_lama)

radius = arcpy.GetParameter(1)

toleransi_m2 = math.pi * (radius ** 2)
#toleransi_m2 = math.pi * radius

if arcpy.Exists(peta_indikator_update_path):
    arcpy.Delete_management(peta_indikator_update_path)

arcpy.SpatialJoin_analysis(peta_indikator_path, peta_update_path, peta_indikator_update_path, 
                           "JOIN_ONE_TO_ONE", "KEEP_ALL", 
                           "OBJECTID \"OBJECTID\" true true false 9 Long 0 9 ,First,#," + 
                           peta_indikator_path + ",OBJECTID,-1,-1;NIB \"NIB\" true true false 5 Long 0 0 ,First,#," + 
                           peta_indikator_path + ",NIB,-1,-1;IdBidang \"IdBidang\" true true false 9 Long 0 9 ,First,#," + 
                           peta_indikator_path + ",IdBidang,-1,-1;Predicted \"Predicted\" true true false 19 Double 0 0 ,First,#," + 
                           peta_indikator_path + ",Predicted,-1,-1;Shape_Area \"Shape_Area\" true true false 19 Double 0 0 ,First,#," + 
                           peta_indikator_path + ",Shape_Area,-1,-1;ls_asal \"ls_asal\" true true false 19 Double 0 0 ,First,#," + 
                           peta_indikator_path + ",ls_asal,-1,-1;ls_tnh \"ls_tnh\" true true false 19 Double 0 0 ,First,#," + 
                           peta_indikator_path + ",ls_tnh,-1,-1;sim_sts_2b \"sim_sts_2b\" true true false 254 Text 0 0 ,First,#," + 
                           peta_indikator_path + ",sim_sts_2b,-1,-1;ls_dr_baru \"ls_dr_baru\" true true false 50 Double 0 0 ,First,#," + 
                           peta_update_path + ",ls_asal,-1,-1; cluster \"cluster\" true true false 2 Short 0 0,First,#," + 
                           #peta_indikator_update_path + ",cluster,-1,-1", "WITHIN", "", "")
                           peta_indikator_update_path + ",cluster,-1,-1", "INTERSECT", "", "")

list_field_update = [f.name for f in arcpy.ListFields(peta_indikator_update_path)]
if "sts_persil" not in list_field_update:
    arcpy.AddField_management(peta_indikator_update_path, "sts_persil", "TEXT")
if "selisih_ba" not in list_field_update:
    arcpy.AddField_management(peta_indikator_update_path, "selisih_ba", "DOUBLE")
exp = "myabs(!ls_asal!, !ls_dr_baru!)"
code_block = """
def myabs(asal, baru):
    if asal is None:
        asal = 0
    if baru is None:
        baru = 0
    return math.fabs((asal-baru))"""
arcpy.CalculateField_management(peta_indikator_update_path, "selisih_ba", exp, "PYTHON", code_block)
exp = "get(!selisih_ba!, " + str(toleransi_m2) + ")"
code_block = """
def get(b, toleransi):
    if b > toleransi:
        return 'update'
    else:
        return 'tetap'"""
arcpy.CalculateField_management(peta_indikator_update_path, "sts_persil", exp, "PYTHON", code_block)

arcpy.AddMessage("== Join dengan Persil Lama ==")

peta_indikator_lama_path = os.path.join(dataset_path, "Peta_Indikator_Lama")

if arcpy.Exists(peta_indikator_lama_path):
    arcpy.Delete_management(peta_indikator_lama_path)

arcpy.SpatialJoin_analysis(peta_indikator_path, peta_lama_path, peta_indikator_lama_path,
                           "JOIN_ONE_TO_ONE", "KEEP_ALL", "OBJECTID \"OBJECTID\" true true false 9 Long 0 9 ,First,#," +
                           peta_indikator_path + ",OBJECTID,-1,-1;NIB \"NIB\" true true false 5 Long 0 0 ,First,#," +
                           peta_indikator_path + ",NIB,-1,-1;IdBidang \"IdBidang\" true true false 9 Long 0 9 ,First,#," +
                           peta_indikator_path + ",IdBidang,-1,-1;Predicted \"Predicted\" true true false 19 Double 0 0 ,First,#," +
                           peta_indikator_path + ",Predicted,-1,-1;Shape_Area \"Shape_Area\" true true false 19 Double 0 0 ,First,#," +
                           peta_indikator_path + ",Shape_Area,-1,-1;ls_asal \"ls_asal\" true true false 19 Double 0 0 ,First,#," +
                           peta_indikator_path + ",ls_asal,-1,-1;ls_tnh \"ls_tnh\" true true false 19 Double 0 0 ,First,#," +
                           peta_indikator_path + ",ls_tnh,-1,-1;sim_sts_2b \"sim_sts_2b\" true true false 254 Text 0 0 ,First,#," +
                           peta_indikator_path + ",sim_sts_2b,-1,-1;ls_dr_lama \"ls_dr_lama\" true true false 50 Double 0 0 ,First,#," +
                           #peta_lama_path + ",ls_asal,-1,-1", "WITHIN", "", "")
                           peta_lama_path + ",ls_asal,-1,-1", "INTERSECT", "", "")

list_field_lama = [f.name for f in arcpy.ListFields(peta_indikator_lama_path)]
if "sts_persil" not in list_field_lama:
    arcpy.AddField_management(peta_indikator_lama_path, "sts_persil", "TEXT")
if "selisih_ba" not in list_field_lama:
    arcpy.AddField_management(peta_indikator_lama_path, "selisih_ba", "DOUBLE")
exp = "myabs(!ls_asal!, !ls_dr_lama!)"
code_block = """
def myabs(asal, lama):
    if asal is None:
        asal = 0
    if lama is None:
        lama = asal
    return math.fabs((asal-lama))"""
arcpy.CalculateField_management(peta_indikator_lama_path, "selisih_ba", exp, "PYTHON", code_block)
exp = "get(!selisih_ba!, " + str(toleransi_m2) + ")"
code_block = """
def get(b, toleransi):
    if b > toleransi:
        return 'update'
    else:
        return 'tetap'"""
arcpy.CalculateField_management(peta_indikator_lama_path, "sts_persil", exp, "PYTHON", code_block)

arcpy.AddMessage("== Join dengan Persil Lama dan Update ==")

peta_indikator_akhir_path = os.path.join(dataset_path, "Indikator_Akhir")

if arcpy.Exists(peta_indikator_akhir_path):
    arcpy.Delete_management(peta_indikator_akhir_path)

fields = arcpy.ListFields(peta_indikator_lama_path,"cluster","SHORT")
if len(fields) == 0:
	arcpy.AddField_management(peta_indikator_lama_path,"cluster","SHORT")

arcpy.SpatialJoin_analysis(peta_indikator_lama_path, peta_indikator_update_path, 
                           peta_indikator_akhir_path, "JOIN_ONE_TO_ONE", "KEEP_COMMON", 
                           "NIB \"NIB\" true true false 5 Long 0 0 ,First,#," + 
                           peta_indikator_lama_path + ",NIB,-1,-1;IdBidang \"IdBidang\" true true false 9 Long 0 9 ,First,#," + 
                           peta_indikator_lama_path + ",IdBidang,-1,-1;ls_asal \"ls_asal\" true true false 19 Double 0 0 ,First,#," + 
                           peta_indikator_lama_path + ",ls_asal,-1,-1;sim_sts_2b \"sim_sts_2b\" true true false 254 Text 0 0 ,First,#," + 
                           peta_indikator_lama_path + ",sim_sts_2b,-1,-1;ls_dr_lama \"ls_dr_lama\" true true false 19 Double 0 0 ,First,#," + 
                           peta_lama_path + ",ls_asal,-1,-1;sts_per_la \"sts_per_la\" true true false 254 Text 0 0 ,First,#," + 
                           peta_indikator_lama_path + ",sts_persil,-1,-1;selisih_la \"selisih_la\" true true false 19 Double 0 0 ,First,#," + 
                           peta_indikator_lama_path + ",selisih_ba,-1,-1;ls_dr_baru \"ls_dr_baru\" true true false 50 Double 0 0 ,First,#," + 
                           peta_indikator_update_path + ",ls_dr_baru,-1,-1;sts_per_ba \"sts_per_ba\" true true false 50 Text 0 0 ,First,#," + 
                           peta_indikator_update_path + ",sts_persil,-1,-1;selisih_up \"selisih_up\" true true false 50 Double 0 0 ,First,#," + 
                           peta_indikator_update_path + ",selisih_ba,-1,-1;cluster \"cluster\" true true false 2 Short 0 0,First,#," + 
                           peta_indikator_update_path + ",cluster,-1,-1", "WITHIN", "", "")
                           #peta_indikator_update_path + ",cluster,-1,-1", "INTERSECT", "", "")

list_field_lama = [f.name for f in arcpy.ListFields(peta_indikator_akhir_path)]
if "status_per" not in list_field_lama:
    arcpy.AddField_management(peta_indikator_akhir_path, "status_per", "TEXT")
exp = "get(!sts_per_la!, !sts_per_ba!)"
code_block = """
def get(a, b):
    if a == 'tetap' and b == 'tetap':
        return 'tetap'
    else:
        return 'update'"""
arcpy.CalculateField_management(peta_indikator_akhir_path, "status_per", exp, "PYTHON", code_block)

if arcpy.Exists(peta_indikator_path):
    arcpy.Delete_management(peta_indikator_path)

arcpy.management.DeleteField(peta_indikator_akhir_path, ["ls_dr_lama","sts_per_la","selisih_la","ls_dr_baru","sts_per_ba","selisih_up","cluster"])

arcpy.CopyFeatures_management(peta_indikator_akhir_path, peta_indikator_path)
sim_indikator_akhir = os.path.join(appdata, "Simbologi_Persil_Updating_Final.lyr")
if arcpy.Exists("Indikator_Perubahan_Persil"):
    arcpy.Delete_management("Indikator_Perubahan_Persil")
arcpy.MakeFeatureLayer_management(peta_indikator_path, "Indikator_Perubahan_Persil")
arcpy.ApplySymbologyFromLayer_management("Indikator_Perubahan_Persil", sim_indikator_akhir)

arcpy.SetParameterAsText(0, "Indikator_Perubahan_Persil")

arcpy.AddMessage("== Proses selesai ==")
