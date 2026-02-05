import os
import arcpy

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

persil = "Persil_Baru"
persil_path = os.path.join(dataset_path, persil)
sampel = "Titik_Sampel_Update"
sampel_path = os.path.join(dataset_path, sampel)

arcpy.Identity_analysis(sampel_path, persil_path, "identity")

listcluster = []
for rows in arcpy.SearchCursor("identity", where_clause = "perubahan = 'mengelompok'"):
    listcluster.append(rows.clusternew)
del rows

for i in list(dict.fromkeys(listcluster)):
    listtitik =[]
    for t_rows in arcpy.SearchCursor("identity", "clusternew = " + str(i)):
        listtitik.append(t_rows.OBJECTID)
    if len(listtitik) > 3:
        arcpy.AddWarning("Cluster [" +str(i)+ "] memiliki titik sampel lebih dari 3.")
    if len(listtitik) < 3:
        arcpy.AddWarning("Cluster [" +str(i)+ "] memiliki titik sampel kurang dari 3.")

