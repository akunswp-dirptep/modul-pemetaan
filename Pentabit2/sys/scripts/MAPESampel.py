import os
import arcpy

# src_layer = arcpy.GetParameterAsText(0)

# appdata = u'c:\znt\sys'
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

# Hasil GWR
dbffile = os.path.join(appdata, "results", "Source_Sampel.dbf")
#shpfile = os.path.join(appdata, "results", "Source_Sampel.shp")

arcpy.AddMessage("== Proses dimulai ==")

arcpy.AddMessage("== Simpan Sampel Prediksi ke dalam GDB ==")

sampel_prediksi = "Sampel_Prediksi"
sampel_prediksi_path = os.path.join(dataset_path, sampel_prediksi)

##if arcpy.Exists(sampel_prediksi):
##    arcpy.Delete_management(sampel_prediksi)
    
#if arcpy.Exists(sampel_prediksi_path):
#    arcpy.Delete_management(sampel_prediksi_path)

#arcpy.FeatureClassToFeatureClass_conversion(shpfile, dataset_path, sampel_prediksi)

arcpy.AddMessage("== Hitung persen residual ==")

field_names = [field.name for field in arcpy.ListFields(sampel_prediksi_path)]
if 'p_residu' not in field_names:
    arcpy.AddField_management(sampel_prediksi_path, 'p_residu', "DOUBLE")
arcpy.CalculateField_management(sampel_prediksi_path, 'p_residu', "((!NILAI! - !Predicted!)/!NILAI!)*100", "PYTHON")
if 'a_p_residu' not in field_names:
    arcpy.AddField_management(sampel_prediksi_path, 'a_p_residu', "DOUBLE")
#update 19/10/2021
#arcpy.CalculateField_management(sampel_prediksi_path, 'a_p_residu', "Abs ( [p_residu]  )", "VB")
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

if arcpy.Exists(sampel_prediksi):
    arcpy.Delete_management(sampel_prediksi)
# arcpy.MakeFeatureLayer_management(sampel_prediksi_path, sampel_prediksi)
# arcpy.SetParameterAsText(0, sampel_prediksi)

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

#update 22/10/2021
#graph = arcpy.Graph()
#graph.addSeriesLineHorizontal(sampel_prediksi_path, fieldX, fieldY, fieldX)

## arcpy.MakeGraph_management(grf, graph, output)

#arcpy.MakeGraph_management(grf,"SERIES=line:vertical " + \
#                           "DATA=" + sampel_prediksi_path + " " + \
#                           "X=" + oid_fieldname + " Y=p_residu LABEL=" + oid_fieldname + " SORT=ASC;" + \
#                           "GRAPH=general TITLE=Grafik Persen Residu;" + \
#                           "LEGEND=general;" + \
#                           "AXIS=left TITLE=Persen Residu;AXIS=right;" + \
#                           "AXIS=bottom TITLE=" + judul_bawah + ";AXIS=top",
#                           output)

chart = arcpy.Chart('Grafik Persen Residu')
chart.type = 'line'
chart.title = 'Grafik Persen Residu'
#chart.description = 'sample'
chart.xAxis.field = oid_fieldname
chart.yAxis.field = 'p_residu'
chart.xAxis.title = judul_bawah
chart.yAxis.title = 'Persen Residu'
chart.datasource = sampel_prediksi_path

aprx = arcpy.mp.ArcGISProject("current")
current_map = aprx.activeMap
current_map.addDataFromPath(sampel_prediksi_path)
m = aprx.listMaps()[0]
layerout = m.listLayers('Sampel_Prediksi')[0]
chart.addToLayer(layerout)

# arcpy.SetParameterAsText(1, output)
del output

arcpy.AddMessage("== Proses selesai ==")
