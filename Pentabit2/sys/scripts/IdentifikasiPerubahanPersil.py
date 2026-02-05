import arcpy, os

# def mySplitString(somestring):
#     hasil = []
#     lenstr = len(somestring)
#     kutipcounter = 0
#     myword = ""
#     i = 0
#     for a in somestring:
#         i = i + 1
#         if a == "'":
#             kutipcounter = kutipcounter + 1
#         if kutipcounter == 1:
#             if a != "'":
#                 myword = myword + a
#         elif kutipcounter == 2:
#             kutipcounter = 0
#         else:
#             if a == " ":
#                 hasil.append(myword)
#                 myword = ""
#             else:
#                 myword = myword + a
#                 if i == lenstr:
#                     hasil.append(myword)
#     return hasil

arcpy.AddMessage("== Proses dimulai ==")

# Parameter input
peta_lama_path = arcpy.GetParameterAsText(0)
peta_lama = "PersilLama"
peta_baru_path = arcpy.GetParameterAsText(1)
peta_baru = "PersilBaru"

dataset_path = ""

# Posisi sys
# appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

# conf_var_path = os.path.join(appdata, "def_var.dat")
# conf_file = open(conf_path, "r")
# list_config = conf_file.readlines()
# conf_file.close()
# line = ""
# for line in list_config:
#     line = line.replace("\n", "")
# splitval = []
# fields_dont_delete = []
# splitval = line.split(";")
# for a in splitval:
#     fields_dont_delete.append(mySplitString(a)[1])
#     fields_dont_delete.append("s_" + mySplitString(a)[1])

#arcpy.AddMessage(fields_dont_delete)
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

# backup_script = os.path.join(appdata, "Scripts", "SaveConfig.py")
# exec(open(backup_script).read())

conf_path = os.path.join(appdata, "config.dat")
# conf_file = open(conf_path, "r")
# list_config = conf_file.readlines()
# conf_file.close()

persil_conf_path = os.path.join(appdata, "persil.dat")
# conf_file = open(persil_conf_path, "r")
# list_config = conf_file.readlines()
# conf_file.close()

conf_path = os.path.join(appdata, "config.dat")
jalan_conf_path = os.path.join(appdata, "jalan.dat")

# for line in list_config:
#     line = line.replace("\n", "")
#     jalan_config = []
#     jalan_config = line.split(",")
#     if jalan_config[0] == "dataset":
#         dataset_path = jalan_config[1]

temp_path = os.path.join(appdata, "temp")

# Tambah field luas di persil peta lama dan baru

arcpy.AddMessage("== Pindah Peta Lama dan Peta Baru ke GDB ==")

dest_lama_path = os.path.join(dataset_path, peta_lama)
dest_baru_path = os.path.join(dataset_path, peta_baru)

if arcpy.Exists(dest_lama_path):
    arcpy.Delete_management(dest_lama_path)
if arcpy.Exists(peta_lama):
    arcpy.Delete_management(peta_lama)
if arcpy.Exists(dest_baru_path):
    arcpy.Delete_management(dest_baru_path)
if arcpy.Exists(peta_baru):
    arcpy.Delete_management(peta_baru)

arcpy.FeatureClassToFeatureClass_conversion(peta_lama_path, dataset_path, peta_lama)
arcpy.FeatureClassToFeatureClass_conversion(peta_baru_path, dataset_path, peta_baru)

fields = arcpy.ListFields(os.path.join(dataset_path, peta_lama))

for f in fields:
    if not (f.type == "Geometry" or f.type == "OID" or f.name == "IdBidang" or f.name == "NIB" or "shape".lower() in str(f.name).lower() or f.name in fields_dont_delete or str(f.name).lower() == "NILAI".lower() or str(f.name).lower() == "Predicted".lower() or f.name=="FID"):
        arcpy.DeleteField_management(os.path.join(dataset_path, peta_lama), f.name)
        # arcpy.AddMessage(f.name + " deleted")

fields = arcpy.ListFields(os.path.join(dataset_path, peta_baru))

for f in fields:
    if not (f.type == "Geometry" or f.type == "OID" or f.name == "IdBidang" or f.name == "NIB" or "shape".lower() in str(f.name).lower() or f.name in fields_dont_delete or str(f.name).lower() == "NILAI".lower() or str(f.name).lower() == "Predicted".lower() or f.name=="FID"):
        arcpy.DeleteField_management(os.path.join(dataset_path, peta_baru), f.name)
        # arcpy.AddMessage(f.name + " deleted")

arcpy.AddMessage("== Tambah field luas di persil peta lama dan baru ==")

list_field_lama = [f.name for f in arcpy.ListFields(dest_lama_path)]
if "ls_asal" not in list_field_lama:
    arcpy.AddField_management(dest_lama_path, "ls_asal", "DOUBLE")
arcpy.CalculateField_management(dest_lama_path, "ls_asal", "!SHAPE.AREA!", "PYTHON_9.3")

list_field_baru = [f.name for f in arcpy.ListFields(dest_baru_path)]
if "ls_asal" not in list_field_baru:
    arcpy.AddField_management(dest_baru_path, "ls_asal", "DOUBLE")
arcpy.CalculateField_management(dest_baru_path, "ls_asal", "!SHAPE.AREA!", "PYTHON_9.3")

# Select layer by location 2 arah

arcpy.AddMessage("== Select layer by location 2 arah ==")

temp_lama_path = os.path.join(dataset_path, "Peta_Temp_Lama")
temp_baru_path = os.path.join(dataset_path, "Peta_Temp_Baru")

if arcpy.Exists(peta_lama):
    arcpy.Delete_management(peta_lama)

arcpy.MakeFeatureLayer_management(dest_lama_path, peta_lama)
arcpy.SelectLayerByLocation_management(peta_lama, "CONTAINS", dest_baru_path, "", "NEW_SELECTION", "INVERT")
if arcpy.Exists(temp_lama_path):
    arcpy.Delete_management(temp_lama_path)
arcpy.CopyFeatures_management(peta_lama, temp_lama_path)

arcpy.MakeFeatureLayer_management(dest_baru_path, peta_baru)
arcpy.SelectLayerByLocation_management(peta_baru, "CONTAINS", dest_lama_path, "", "NEW_SELECTION", "INVERT")
if arcpy.Exists(temp_baru_path):
    arcpy.Delete_management(temp_baru_path)
arcpy.CopyFeatures_management(peta_baru, temp_baru_path)

# Proses gabung persil

arcpy.AddMessage("== Gabung persil ==")

peta_indikator = "Indikator_Perubahan_Persil"
peta_indikator_path = os.path.join(dataset_path, peta_indikator)

if arcpy.Exists(peta_indikator_path):
    arcpy.Delete_management(peta_indikator_path)
arcpy.Merge_management([temp_baru_path, temp_lama_path], peta_indikator_path)

if arcpy.Exists(peta_indikator):
    arcpy.Delete_management(peta_indikator)
arcpy.MakeFeatureLayer_management(peta_indikator_path, peta_indikator)

list_field_indikator = [f.name for f in arcpy.ListFields(peta_indikator_path)]
if "sim_sts_2b" not in list_field_indikator:
    arcpy.AddField_management(peta_indikator_path, "sim_sts_2b", "TEXT")

arcpy.SelectLayerByLocation_management(peta_indikator, "WITHIN", peta_baru_path, "", "NEW_SELECTION", "INVERT")
arcpy.CalculateField_management(peta_indikator, "sim_sts_2b", "'Indikator Hapus'", "PYTHON")

if arcpy.Exists(peta_indikator):
    arcpy.Delete_management(peta_indikator)
arcpy.MakeFeatureLayer_management(peta_indikator_path, peta_indikator)

with arcpy.da.UpdateCursor(peta_indikator_path, ["sim_sts_2b"]) as cur:
    for row in cur:
        if row[0] != "Indikator Hapus":
            row[0] = "Indikator Periksa"
        cur.updateRow(row)

fields = arcpy.ListFields(peta_indikator_path)

for f in fields:
    if not (f.type == "Geometry" or f.type == "OID" or f.name == "IdBidang" or f.name == "NIB" or "shape".lower() in str(f.name).lower() or "sim_sts_2b" == str(f.name).lower() or "ls_asal" == str(f.name).lower() or "ls_tnh" == str(f.name).lower() or str(f.name).lower() == "NILAI".lower() or str(f.name).lower() == "Predicted".lower() or f.name=="FID"):
        arcpy.DeleteField_management(os.path.join(dataset_path, peta_indikator_path), f.name)
        # arcpy.AddMessage(f.name + " deleted")

sim_path = os.path.join(appdata, "Simbologi_Layer_2B.lyr")
sim_pathbaru = os.path.join(appdata, "SimbologiPetaUpdate.lyr")
sim_pathlama = os.path.join(appdata, "SimbologiPetaLama.lyr")

if arcpy.Exists(peta_indikator):
    arcpy.Delete_management(peta_indikator)
arcpy.MakeFeatureLayer_management(peta_indikator_path, peta_indikator)
arcpy.ApplySymbologyFromLayer_management(peta_indikator, sim_path)

if arcpy.Exists("Peta_Lama"):
    arcpy.Delete_management("Peta_Lama")
arcpy.MakeFeatureLayer_management(dest_lama_path, "Peta_Lama")
arcpy.ApplySymbologyFromLayer_management("Peta_Lama", sim_pathlama)

if arcpy.Exists("Peta_Baru"):
    arcpy.Delete_management("Peta_Baru")
arcpy.MakeFeatureLayer_management(dest_baru_path, "Peta_Baru")
arcpy.ApplySymbologyFromLayer_management("Peta_Baru", sim_pathbaru)

arcpy.SetParameterAsText(2, "Peta_Lama")
arcpy.SetParameterAsText(3, "Peta_Baru")
arcpy.SetParameterAsText(4, peta_indikator)

arcpy.AddMessage("== Proses selesai ==")

# Problem:
# a) Ada 2 bidang tanah
# b) Bidang baru mengalami perubahan2:
#    1) Penambahan
#    2) Penghapusan
#    3) Pemecahan bidang
#    3) Penggabungan bidang
#    5) Pergeseran


# 1) Tarik inputan (poligon bidang tanah tahun lalu)
# 2) Tarik inputan (poligon bidang tanah tahun ini)

