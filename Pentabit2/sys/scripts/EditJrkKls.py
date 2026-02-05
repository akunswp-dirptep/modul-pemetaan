import os, arcpy

arcpy.AddMessage("== Proses dimulai ==")

appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
tempdata = os.path.join(appdata, "temp")
conf_persil_path = os.path.join(appdata, "persil.dat")

conf_file = open(conf_persil_path, "r")
list_config = conf_file.readlines()
conf_file.close()

persil_path = ""

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "persil":
        persil_path = persil_config[1].split(";")[1]


persil_update = "Persil"

persil_fields = [f.name for f in arcpy.ListFields(persil_update)]

kls_jln = arcpy.GetParameterAsText(0)
jrk_jln = arcpy.GetParameter(1)
field = "jk_atrp"

if kls_jln == "Arteri Primer":
    field = "jk_atrp"
elif kls_jln == "Arteri Sekunder":
    field = "jk_atrs"
elif kls_jln == "Kolektor Primer":
    field = "jk_kolp"
elif kls_jln == "Kolektor Sekunder":
    field = "jk_kols"

persil_fields = [f.name for f in arcpy.ListFields(persil_update)]

if field not in persil_fields:
    arcpy.AddField_management(persil_path, field, "DOUBLE")
    # arcpy.AddError("Field " + field + " tidak ditemukan.")
    # raise arcpy.ExecuteError

ada_seleksi = 0
ada_seleksi = len(arcpy.Describe(persil_update).FIDSet)

if ada_seleksi <= 0:
    sys.exit()

rows = arcpy.UpdateCursor(persil_update)

for row in rows:
    row.setValue(field, jrk_jln)
    rows.updateRow(row)

del row
del rows

#update 18/10/2021
#arcpy.RefreshTOC()
#arcpy.RefreshActiveView()

arcpy.AddMessage("== Proses selesai ==")
