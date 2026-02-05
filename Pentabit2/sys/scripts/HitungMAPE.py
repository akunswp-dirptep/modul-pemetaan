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

arcpy.AddMessage("== Hitung persen residual ==")

field_names = [field.name for field in arcpy.ListFields(sampel_prediksi_path)]
if 'p_residu' not in field_names:
    arcpy.AddField_management(sampel_prediksi_path, 'p_residu', "DOUBLE")
arcpy.CalculateField_management(sampel_prediksi_path, 'p_residu', "((!NILAI! - !Predicted!)/!NILAI!)*100", "PYTHON")
if 'a_p_residu' not in field_names:
    arcpy.AddField_management(sampel_prediksi_path, 'a_p_residu', "DOUBLE")
arcpy.CalculateField_management(sampel_prediksi_path, 'a_p_residu', "abs(!p_residu!)", "PYTHON")

arcpy.AddMessage("== Hitung MAPE persen residual ==")

arr = []
total = 0.0
cursor = arcpy.SearchCursor(sampel_prediksi_path)
row = None

try:
    for row in cursor:
        val = abs(row.getValue("p_residu"))
        total = total + val
        arr.append(val)
except:
    arcpy.AddMessage("Error...")
finally:
    del cursor, row

num_data = len(arr)
if num_data==0:
    num_data = 1

mape = total/(num_data * 1.0)

arcpy.AddMessage("== Nilai MAPE = " + str(mape) + " ==")
judul_bawah = "Nilai MAPE = " + str(mape) + ""

field_names = [field.name for field in arcpy.ListFields(sampel_prediksi_path)]
if 'mape' not in field_names:
    arcpy.AddField_management(sampel_prediksi_path, 'mape', "DOUBLE")
arcpy.CalculateField_management(sampel_prediksi_path, 'mape', "" + str(mape), "PYTHON")

##if arcpy.Exists(sampel_prediksi):
##    arcpy.Delete_management(sampel_prediksi)
##arcpy.MakeFeatureLayer_management(sampel_prediksi_path, sampel_prediksi)

arcpy.AddMessage("== Plot persen residual ==")

output = "graph1"
grf = os.path.join(appdata, "GrafikPersenResidual.grf")

if arcpy.Exists(output):
    arcpy.Delete_management(output)

arcpy.env.overwriteOutput = True

oid_fieldname = arcpy.Describe(sampel_prediksi_path).OIDFieldName

fieldX = arcpy.Field()
fieldY = arcpy.Field()
fields = arcpy.ListFields(sampel_prediksi_path)
for f in fields:
    if f.name == oid_fieldname:
        fieldX = f
    if f.name == "p_residu":
        fieldY = f
        
chart = arcpy.Chart('Grafik Persen Residu')
chart.type = 'line'
chart.title = 'Grafik Persen Residu'
chart.xAxis.field = oid_fieldname
chart.yAxis.field = 'p_residu'
chart.xAxis.title = judul_bawah
chart.yAxis.title = 'Persen Residu'
chart.datasource = sampel_prediksi_path

layerout = current_map.listLayers("Sampel_Prediksi")[0]
chart.addToLayer(layerout)

arcpy.AddMessage("== Proses selesai ==")

##arcpy.management.CalculateField(sampel_prediksi,'APE','abs(!Residual!/!nilai!*100)', 'PYTHON3')
##
##aprx = arcpy.mp.ArcGISProject("current")
##layers = map.listLayers()
##gwrLayer = layers[0] ## perlu dipastiin apakah dia akan selalu 0
##
##residual_chart = arcpy.Chart('selisih-prediksi-observasi')
##residual_chart.type = 'histogram'
##residual_chart.title = 'Selisih Prediksi dan Observasi'
##residual_chart.xAxis.field = 'Residual'
##residual_chart.xAxis.title = "Residu"
##residual_chart.bar.aggregation = 'COUNT'
##
##mape_chart = arcpy.Chart('MAPE')
##mape_chart.type = 'histogram'
##mape_chart.title = 'Absolute Percentage Error'
##mape_chart.xAxis.field = 'Residual'
##mape_chart.xAxis.title = "Residu"
##mape_chart.bar.aggregation = 'COUNT'
##
##residual_chart.addToLayer(gwrLayer)
##mape_chart.addToLayer(gwrLayer)
