import arcpy, webbrowser, os

arcpy.env.overwriteOutput = True

appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_path = os.path.join(appdata, "config.dat")

conf_file = open(conf_path, "r")
list_config = conf_file.readlines()
conf_file.close()

dataset_path = ""
gdb_path = ""
ws_path = ""

for line in list_config:
    line = line.replace("\n", "")
    p_config = []
    p_config = line.split(",")
    
    if p_config[0] == "dataset":
        dataset_path= p_config[1]
    elif p_config[0] == "gdb":
        gdb_path= p_config[1]
    elif p_config[0] == "ws":
        ws_path= p_config[1]

sample = os.path.join(dataset_path, "Sampel_Prediksi")
input_field = "STDRESID"
conceptualization = "INVERSE_DISTANCE"
distance_method = "EUCLIDEAN_DISTANCE"
standardization = "NONE"

moran = arcpy.stats.SpatialAutocorrelation(sample, input_field, 'GENERATE_REPORT', conceptualization, distance_method, standardization)

index_moran = moran.getOutput(0)
z_score = moran.getOutput(1)
p_value = moran.getOutput(2)
report = moran.getOutput(3)

webbrowser.open(report)
arcpy.AddMessage("== Summary ==")
arcpy.AddMessage("index_moran :" + str(index_moran))
arcpy.AddMessage("z_score :" + str(z_score))
arcpy.AddMessage("p_value :" + str(p_value))
arcpy.AddMessage("report :" + str(report))

arcpy.AddMessage("== Proses Selesai ==")
