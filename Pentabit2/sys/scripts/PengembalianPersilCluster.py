import arcpy, os

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

persil = "Indikator_Perubahan_Persil"

ada_seleksi = 0
ada_seleksi = len(arcpy.Describe(persil).FIDSet)

if ada_seleksi <= 0:
    sys.exit()

rows = arcpy.UpdateCursor(persil)
for row in rows:
    row.clusternew = None
    rows.updateRow(row)   
del row, rows

sim_path = os.path.join(appdata, "Indikator_Perubahan_Persil.lyrx")

if arcpy.Exists("Indikator_Perubahan_Persil"):
    arcpy.Delete_management("Indikator_Perubahan_Persil")
arcpy.MakeFeatureLayer_management(os.path.join(dataset_path, "Indikator_Perubahan_Persil"), "Indikator_Perubahan_Persil")
arcpy.ApplySymbologyFromLayer_management("Indikator_Perubahan_Persil", sim_path)

arcpy.SetParameterAsText(0, "Indikator_Perubahan_Persil")