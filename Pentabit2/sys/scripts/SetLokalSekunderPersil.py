import arcpy, os ,sys

arcpy.env.overwriteOutput = True

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_jalan_path = os.path.join(appdata, "persil.dat")

conf_file = open(conf_jalan_path, "r")
list_config = conf_file.readlines()
conf_file.close()

persil = ""

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "persil":
        persil = persil_config[1].split(";")[0]
        persil_path = persil_config[1].split(";")[1]


arcpy.AddMessage("== Proses dimulai ==")
seleksi = arcpy.da.Describe(persil)['FIDSet']

if seleksi == None:
    arcpy.AddWarning("== Mohon Lakukan Seleksi ==")
    sys.exit()

with arcpy.da.UpdateCursor(persil,['kls_jln', 's_kls_jln']) as cur:
    for row in cur:
        row[0] = 'Lokal Sekunder'
        row[1] = 2
        cur.updateRow(row)

simbologi_path = os.path.join(appdata, "SimbologiKelasJalanPersilUpdate.lyr")
arcpy.ApplySymbologyFromLayer_management(persil, simbologi_path)
