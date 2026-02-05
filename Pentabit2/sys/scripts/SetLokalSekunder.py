import sys, os
import arcpy

arcpy.AddMessage("== Proses dimulai ==")

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_jalan_path = os.path.join(appdata, "jalan.dat")

conf_file = open(conf_jalan_path, "r")
list_config = conf_file.readlines()
conf_file.close()

dataset_path = ""
jaringanjalan = ""
jaringanjalan_path = ""
simbologi_path = ""

for line in list_config:
    line = line.replace("\n", "")
    jalan_config = []
    jalan_config = line.split(",")
    if jalan_config[0] == "jaringanjalan":
        jaringanjalan = jalan_config[1].split(";")[0]
        jaringanjalan_path = jalan_config[1].split(";")[1]
    if jalan_config[0] == "simbologikelasjalan":
        simbologi_path = jalan_config[1].split(";")[1]

field_names = [field.name for field in arcpy.ListFields(jaringanjalan_path)]
if 'kls_jln' not in field_names:
    arcpy.AddField_management(jaringanjalan_path, 'kls_jln', 'DOUBLE')
if 's_kls_jln' not in field_names:
    arcpy.AddField_management(jaringanjalan_path, 's_kls_jln', 'DOUBLE')

ada_seleksi = 0
ada_seleksi = len(arcpy.Describe(jaringanjalan).FIDSet)

if ada_seleksi <= 0:
    sys.exit()

rows = arcpy.UpdateCursor(jaringanjalan)

for row in rows:
    row.kls_jln = "Lokal Sekunder"
    row.s_kls_jln = 2
    rows.updateRow(row)

del row
del rows

if arcpy.Exists(jaringanjalan):
    arcpy.ApplySymbologyFromLayer_management(jaringanjalan, simbologi_path)
