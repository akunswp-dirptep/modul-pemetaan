import arcpy, os

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


sample = arcpy.GetParameterAsText(0)
explanatory_fields = arcpy.GetParameterAsText(1)
out_sample_features = arcpy.GetParameterAsText(2)
neighborhood_type = arcpy.GetParameterAsText(3)
neighborhood_selection_method = arcpy.GetParameterAsText(4)
minimum_number_of_neighbors = arcpy.GetParameterAsText(5)
maximum_number_of_neighbors = arcpy.GetParameterAsText(6)
minimum_search_distance = arcpy.GetParameterAsText(7)
maximum_search_distance = arcpy.GetParameterAsText(8)
number_of_neighbors_increment = arcpy.GetParameterAsText(9)
search_distance_increment = arcpy.GetParameterAsText(10)
number_of_increment = arcpy.GetParameterAsText(11)
number_of_neighbors = arcpy.GetParameterAsText(12)
distance_band = arcpy.GetParameterAsText(13)
local_weighting_scheme = arcpy.GetParameterAsText(14)

sampel_prediksi = "Sampel_Prediksi"
sampel_prediksi_path = os.path.join(dataset_path, sampel_prediksi)

arcpy.stats.GWR(sample, 'nilai', 'CONTINUOUS', explanatory_fields, sampel_prediksi_path, neighborhood_type, 
    neighborhood_selection_method, minimum_number_of_neighbors, maximum_number_of_neighbors,
    minimum_search_distance, maximum_search_distance, number_of_neighbors_increment,
    search_distance_increment, number_of_increment, number_of_neighbors, distance_band,
    robust_prediction = "ROBUST" , local_weighting_scheme= "GAUSSIAN")

aprx = arcpy.mp.ArcGISProject('CURRENT')
current_map = aprx.activeMap
current_map.addDataFromPath(sampel_prediksi_path)

arcpy.AddMessage("== Proses selesai ==")
