import arcpy, os

arcpy.AddMessage("== Proses dimulai ==")

appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_persil_path = os.path.join(appdata, "persil.dat")

conf_file = open(conf_persil_path, "r")
list_config = conf_file.readlines()
conf_file.close()

dataset_path = ""

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "dataset":
        dataset_path = persil_config[1]

arcpy.AddMessage("== Midpoint persil update ==")

persil = "Persil_Update"
persil_path = os.path.join(dataset_path, persil)
persil_split = "PersilSplitUpdate"
persil_split_path = os.path.join(dataset_path, persil_split)
persil_split_midpoint = "PersilMidpointUpdate"
persil_split_midpoint_path = os.path.join(dataset_path, persil_split_midpoint)
jaringan_jalan = "Jaringan_Jalan"
jaringan_jalan_path = os.path.join(dataset_path, jaringan_jalan)

field_names = [field.name for field in arcpy.ListFields(jaringan_jalan_path)]
if 'IdJalan' not in field_names:
    arcpy.AddField_management(jaringan_jalan_path, 'IdJalan', "LONG")
arcpy.CalculateField_management(jaringan_jalan_path, "IdJalan", "!OBJECTID!", "PYTHON")

if arcpy.Exists(persil_split_midpoint):
    arcpy.Delete_management(persil_split_midpoint)
if arcpy.Exists(persil_split_midpoint_path):
    arcpy.Delete_management(persil_split_midpoint_path)

arcpy.FeatureToPoint_management(persil_split_path, persil_split_midpoint_path, "INSIDE")

arcpy.AddMessage("== Persiapan konstruksi garis ==")

field_names = [field.name for field in arcpy.ListFields(persil_split_midpoint_path)]

if 'X' not in field_names:
    arcpy.AddField_management(persil_split_midpoint_path, 'X', "DOUBLE")
exp = "!Shape.firstpoint.x!"
code_block = """
def get(b):
    return b.split(' ')[0]"""
# arcpy.CalculateField_management(persil_split_midpoint_path, "X", exp, "PYTHON", code_block)
arcpy.CalculateField_management(persil_split_midpoint_path, "X", exp, "PYTHON")

if 'Y' not in field_names:
    arcpy.AddField_management(persil_split_midpoint_path, 'Y', "DOUBLE")
# exp = "get(!shape.firstpoint!)"
# code_block = """
# def get(b):
#     return float(b.split(' ')[1])"""
exp = "!Shape.firstpoint.y!"
code_block = """
def get(b):
    return b.split(' ')[1]"""
# arcpy.CalculateField_management(persil_split_midpoint_path, "Y", exp, "PYTHON", code_block)
arcpy.CalculateField_management(persil_split_midpoint_path, "Y", exp, "PYTHON")

if 'NEAR_DIST' in field_names:
    arcpy.DeleteField_management(persil_split_midpoint_path, 'NEAR_DIST')
if 'NEAR_FID' in field_names:
    arcpy.DeleteField_management(persil_split_midpoint_path, 'NEAR_FID')
if 'NEAR_X' in field_names:
    arcpy.DeleteField_management(persil_split_midpoint_path, 'NEAR_X')
if 'NEAR_Y' in field_names:
    arcpy.DeleteField_management(persil_split_midpoint_path, 'NEAR_Y')
if 'NEAR_ANGLE' in field_names:
    arcpy.DeleteField_management(persil_split_midpoint_path, 'NEAR_ANGLE')

arcpy.AddMessage("== Tentukan titik terdekat ==")

arcpy.Near_analysis(persil_split_midpoint_path, jaringan_jalan_path, "200", "LOCATION", "ANGLE")

arcpy.AddMessage("== Konstruksi garis ke titik terdekat ==")

oid_fieldname = arcpy.Describe(persil_split_midpoint_path).OIDFieldName
field_names = [field.name for field in arcpy.ListFields(persil_split_midpoint_path)]
if 'IdJoinLine' not in field_names:
    arcpy.AddField_management(persil_split_midpoint_path, 'IdJoinLine', "LONG")
arcpy.CalculateField_management(persil_split_midpoint_path, 'IdJoinLine', "!" + oid_fieldname + "!", "PYTHON")


joinline = "JoinLine"
joinline_path = os.path.join(dataset_path, joinline)
joinlinetemp_path = os.path.join(appdata, "temporary.gdb", joinline)

if arcpy.Exists(joinlinetemp_path):
    arcpy.Delete_management(joinlinetemp_path)
if arcpy.Exists(joinline_path):
    arcpy.Delete_management(joinline_path)
if arcpy.Exists(joinline):
    arcpy.Delete_management(joinline)

sr = arcpy.Describe(persil_split_midpoint_path).spatialReference
arcpy.XYToLine_management(persil_split_midpoint_path, joinlinetemp_path, "X", "Y", "NEAR_X", "NEAR_Y", "GEODESIC", "IdJoinLine", sr)
arcpy.CopyFeatures_management(joinlinetemp_path, joinline_path)

arcpy.AddMessage("== Join 1 ==")

arcpy.JoinField_management(joinline_path, "IdJoinLine", persil_split_midpoint_path, "IdJoinLine", ["IdBidang", "LebarSisi"])

arcpy.AddMessage("== Join 2 ==")

join_2 = "JoinPersilJalan_2"
join_2_path = os.path.join(dataset_path, join_2)

if arcpy.Exists(join_2):
    arcpy.Delete_management(join_2)
if arcpy.Exists(join_2_path):
    arcpy.Delete_management(join_2_path)

arcpy.SpatialJoin_analysis(joinline_path, jaringan_jalan_path, join_2_path, "JOIN_ONE_TO_ONE", "KEEP_ALL", "", "INTERSECT")

arcpy.AddMessage("== Pilih-pilih kelas dan lebar ==")

diss_1 = "DissPersilJalan_1"
diss_1_path = os.path.join(dataset_path, diss_1)
diss_2 = "DissPersilJalan_2"
diss_2_path = os.path.join(dataset_path, diss_2)

if arcpy.Exists(diss_1):
    arcpy.Delete_management(diss_1)
if arcpy.Exists(diss_1_path):
    arcpy.Delete_management(diss_1_path)
if arcpy.Exists(diss_2):
    arcpy.Delete_management(diss_2)
if arcpy.Exists(diss_2_path):
    arcpy.Delete_management(diss_2_path)

arcpy.Dissolve_management(join_2_path, diss_1_path, ["IdBidang", "IdJalan"], [["s_kls_jln", "MAX"], ["lb_jln", "MAX"]], "MULTI_PART", "DISSOLVE_LINES")
arcpy.Dissolve_management(diss_1_path, diss_2_path, ["IdBidang"], [["MAX_s_kls_jln", "MAX"], ["MAX_lb_jln", "MAX"]], "MULTI_PART", "DISSOLVE_LINES")

arcpy.AddMessage("== Simpan di persil ==")

field_names = [field.name for field in arcpy.ListFields(persil_path)]
if 's_kls_jln' not in field_names:
    arcpy.AddField_management(persil_path, 's_kls_jln', "DOUBLE")
if 'lb_jln' not in field_names:
    arcpy.AddField_management(persil_path, 'lb_jln', "DOUBLE")

arcpy.JoinField_management(persil_path, "IdBidang", diss_2_path, "IdBidang", ["MAX_MAX_s_kls_jln", "MAX_MAX_lb_jln"])
arcpy.CalculateField_management(persil_path, 's_kls_jln', "!MAX_MAX_s_kls_jln!", "PYTHON")
arcpy.CalculateField_management(persil_path, 'lb_jln', "!MAX_MAX_lb_jln!", "PYTHON")
# arcpy.DeleteField_management(persil_path, ["MAX_MAX_s_kls_jln", "MAX_MAX_lb_jln"])

# joinfields = ['IdBidang', 'bentuk', 's_bentuk']
# joindict = {}
#
# with arcpy.da.SearchCursor(persil_path, joinfields) as rows:
#     for row in rows:
#         joinval = row[0]
#         val1 = row[1]
#         val2 = row[2]
#         joindict[joinval] = [val1, val2]
# del rows, row
#
# with arcpy.da.UpdateCursor(trg_path, joinfields) as rows:
#     for row in rows:
#         keyval = row[0]
#         if joindict.has_key(keyval):
#             row[1] = joindict[keyval][0]
#             row[2] = joindict[keyval][1]
#             rows.updateRow(row)
# del rows, row



if arcpy.Exists(persil):
    arcpy.Delete_management(persil)

arcpy.MakeFeatureLayer_management(persil_path, persil)
# arcpy.SetParameterAsText(0, persil)

src = "Persil_Update"
src_path = os.path.join(dataset_path, src)
trg = "Persil_Baru"
trg_path = os.path.join(dataset_path, trg)

joinfields = ['IdBidang', 's_kls_jln' ,'lb_jln']
joindict = {}

with arcpy.da.SearchCursor(src_path, joinfields) as rows:
    for row in rows:
        joinval = row[0]
        val1 = row[1]
        val2 = row[2]
        joindict[joinval] = [val1, val2]
del rows, row

with arcpy.da.UpdateCursor(trg_path, joinfields) as rows:
    for row in rows:
        keyval = row[0]
        if keyval in joindict:
            row[1] = joindict[keyval][0]
            row[2] = joindict[keyval][1]
            rows.updateRow(row)
del rows, row

if arcpy.Exists(trg):
    arcpy.Delete_management(trg)

if 'kls_jln' not in field_names:
    arcpy.AddField_management(trg_path, 'kls_jln', "TEXT")

with arcpy.da.UpdateCursor(trg_path,['kls_jln', 's_kls_jln']) as cur:
    for row in cur:
        if not row[1]:
            row[1] == 1
            row[0] ='Lokal Setapak'
        else:
            if int(row[1]) == 7:
                row[0] = 'Arteri Primer'
            elif int(row[1]) == 6:
                row[0] = 'Arteri Sekunder'
            elif int(row[1]) == 5:
                row[0] = 'Kolektor Primer'
            elif int(row[1]) == 4:
                row[0] = 'Kolektor Sekunder'
            elif int(row[1]) == 3:
                row[0] = 'Lokal Primer'
            elif int(row[1]) == 2:
                row[0] = 'Lokal Sekunder'
            elif int(row[1]) == 1:
                row[0] = 'Lokal Setapak'
        cur.updateRow(row)

arcpy.MakeFeatureLayer_management(trg_path, trg)
arcpy.SetParameterAsText(0, trg)

arcpy.SelectLayerByAttribute_management(trg,  "NEW_SELECTION", '"s_kls_jln" is null')
arcpy.CalculateField_management(trg, "s_kls_jln" ,"1", "PYTHON3", "")


arcpy.AddMessage("== Proses selesai ==")
