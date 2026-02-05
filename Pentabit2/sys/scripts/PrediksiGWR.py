import os, arcpy

arcpy.env.overwriteOutput = True

### mengambil config dari sistem pentabit
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

## delete feature class lama di gdb
arcpy.env.workspace = gdb_path
for za in arcpy.ListDatasets("C_*"):
    if za:
        arcpy.Delete_management(za)
for zb in arcpy.ListDatasets("Hasil_GWR_Sampel_*"):
    if zb:
        arcpy.Delete_management(zb)

### deklarasi variabel dari input parameter agp
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
population = arcpy.GetParameterAsText(14)
explanatory_variables_to_match = arcpy.GetParameterAsText(15)
out_predicted_features = arcpy.GetParameterAsText(16)
coefficient_raster_workspace = arcpy.GetParameterAsText(17)
local_weighting_scheme = arcpy.GetParameterAsText(18)

persil_prediksi = os.path.join(dataset_path, "Persil_Prediksi")
sampel_prediksi = os.path.join(dataset_path, "Sampel_Prediksi")

###Merubah value input untuk digunakan pada arcpy
def inputDialogueToArcpy (variable):
    return variable.upper().replace(" ", "_")

neighborhood_type = inputDialogueToArcpy(neighborhood_type)
neighborhood_selection_method = inputDialogueToArcpy(neighborhood_selection_method)

### GWR
arcpy.AddMessage("=== Menjalankan GWR ===")
arcpy.stats.GWR( sample, 'nilai', 'CONTINUOUS', explanatory_fields, out_sample_features, neighborhood_type, 
    neighborhood_selection_method, minimum_number_of_neighbors, maximum_number_of_neighbors,
    minimum_search_distance, maximum_search_distance, number_of_neighbors_increment,
    search_distance_increment, number_of_increment, number_of_neighbors, distance_band, population, 
    explanatory_variables_to_match, out_predicted_features, "ROBUST", "GAUSSIAN",
    coefficient_raster_workspace)

arcpy.AddMessage("=== Membuat Titik dalam Persil ===")

poin_persil = os.path.join(dataset_path,"PoinPersil")
arcpy.FeatureToPoint_management(population, poin_persil,"INSIDE")

arcpy.AddMessage("=== Proses Interpolasi ===")
arcpy.env.extent = population

field_names = [f.name for f in arcpy.ListFields(out_sample_features, "C_*")]

for field in field_names:
    arcpy.AddMessage(f"=== Interpolasi {field} ===")
    arcpy.ga.EmpiricalBayesianKriging(out_sample_features, field, "", os.path.join(gdb_path,field))

rasters_name = [os.path.join(gdb_path,field) for field in field_names]

arcpy.AddMessage("=== Extract data ke Poin Persil ===")
arcpy.sa.ExtractMultiValuesToPoints(poin_persil, rasters_name)

arcpy.AddMessage("=== Delete fields coefisien lama ===")
if arcpy.Exists(persil_prediksi):
    coef_lama = [g.name for g in arcpy.ListFields(persil_prediksi, "C_*")]
    if coef_lama:
        arcpy.DeleteField_management(persil_prediksi, coef_lama)

arcpy.AddMessage("=== Join Poin Persil ke Persil ===")
arcpy.management.JoinField(out_predicted_features, 'SOURCE_ID', poin_persil, 'ORIG_FID', field_names)

arcpy.AddMessage("=== Proses Pembuatan Persil Prediksi dan Sampel Prediksi ===")

field_names.append('PREDICTED')

arcpy.CopyFeatures_management(population, persil_prediksi)
arcpy.management.JoinField(persil_prediksi, 'OBJECTID', out_predicted_features, 'SOURCE_ID', field_names)

arcpy.CopyFeatures_management(sample, sampel_prediksi)
arcpy.management.JoinField(sampel_prediksi, 'OBJECTID', out_sample_features, 'SOURCE_ID', ['PREDICTED', 'RESIDUAL', 'STDRESID'])

aprx = arcpy.mp.ArcGISProject('CURRENT')
current_map = aprx.activeMap
current_map.addDataFromPath(persil_prediksi)
current_map.addDataFromPath(sampel_prediksi)
