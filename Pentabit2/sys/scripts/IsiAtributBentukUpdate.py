import arcpy, os

arcpy.AddMessage("== Proses dimulai ==")

appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

conf_path = os.path.join(appdata, "persil.dat")
conf_file = open(conf_path, "r")
list_config = conf_file.readlines()
conf_file.close()

dataset_path = ""

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "dataset":
        dataset_path = persil_config[1]

src = "Persil_Update"
src_path = os.path.join(dataset_path, src)
trg = "Persil_Baru"
trg_path = os.path.join(dataset_path, trg)

joinfields = ['IdBidang', 'bentuk', 's_bentuk']
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

aprx = arcpy.mp.ArcGISProject('CURRENT')
current_map = aprx.activeMap
tab_name = []
for m in aprx.listMaps():
    for lyr in m.listLayers():
        m.removeLayer(lyr)

arcpy.MakeFeatureLayer_management(trg_path, trg)
arcpy.SetParameterAsText(0, trg)
arcpy.DeleteField_management(trg,"Shape_Leng")
arcpy.AddMessage("== Proses selesai ==")
