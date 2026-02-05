import os
import arcpy

arcpy.AddMessage("== Proses mulai ==")

appdata = 'c:\znt\sys'
conf_jalan_path = os.path.join(appdata, "jalan.dat")
conf_persil_path = os.path.join(appdata, "persil.dat")
conf_fasilitas_path = os.path.join(appdata, "fasilitas.dat")
conf_file = open(conf_jalan_path, "r")
list_config = conf_file.readlines()
conf_file.close()

dataset_template_path = ""
dataset_path = ""
datasetfasilitas_path = ""
jaringanjalan = ""
jaringanjalan_path = ""
jaringanjalan_nd_path = ""
junction_path = ""
nd_path = ""

for line in list_config:
    line = line.replace("\n", "")
    jalan_config = []
    jalan_config = line.split(",")
    if jalan_config[0] == "dataset":
        dataset_path = jalan_config[1]
    if jalan_config[0] == "jaringanjalan":
        jaringanjalan = jalan_config[1].split(";")[0]
        jaringanjalan_path = jalan_config[1].split(";")[1]
    if jalan_config[0] == "nd":
        nd_path = jalan_config[1].split(";")[1]
    if jalan_config[0] == "jaringanjalannd":
        jaringanjalan_nd_path = jalan_config[1].split(";")[1]
    if jalan_config[0] == "junction":
        junction_path = jalan_config[1].split(";")[1]

conf_file = open(conf_persil_path, "r")
list_config = conf_file.readlines()
conf_file.close()

persil = ""
persil_path = ""
persilcentroid = ""
persilcentroid_path = ""

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "persil":
        persil = persil_config[1].split(";")[0]
        persil_path = persil_config[1].split(";")[1]
    if persil_config[0] == "persilcentroid":
        persilcentroid = persil_config[1].split(";")[0]
        persilcentroid_path = persil_config[1].split(";")[1]

conf_file = open(conf_fasilitas_path, "r")
list_config = conf_file.readlines()
conf_file.close()

for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "datasetfasilitas":
        datasetfasilitas_path = persil_config[1]

dataset_template_path = os.path.dirname(jaringanjalan_nd_path)
junction_nd_path = os.path.join(os.path.dirname(jaringanjalan_nd_path), "JaringanJalan_ND_Junctions")

arcpy.AddMessage("== Persiapan ==")

outNALayerName = "hasil_kelas"
outNALayerName_path = os.path.join(dataset_template_path, outNALayerName)
impedance_attribute = "PanjangJalan"
accumulateAttributeName = ["PanjangJalan"]

arcpy.env.workspace = datasetfasilitas_path
list_fc = arcpy.ListFeatureClasses("*")
list_fasility = []

for fc in list_fc:
    list_fasility.append(fc)

# for fc in list_fasility:
hasilNAObject = arcpy.MakeClosestFacilityLayer_na(nd_path, outNALayerName, impedance_attribute, "TRAVEL_FROM", "", 1)
outNALayer = hasilNAObject.getOutput(0)
fasilitas = "ArteriPrimer"
fasilitas_path = r'E:\Projects\Waindo\BPN\WSBaru\ArteriPrimer.shp'

arcpy.AddMessage("== Hitung jarak fasilitas: " + fasilitas)

arcpy.AddLocations_na(outNALayer, "Incidents", persilcentroid_path, "", "")
arcpy.AddLocations_na(outNALayer, "Facilities", fasilitas_path, "", "")

arcpy.Solve_na(outNALayer)

arcpy.AddMessage("== Pindahkan hasil na ==")

incident_path = os.path.join(dataset_template_path, "incident_" + fasilitas)
route_path = os.path.join(dataset_template_path, "route_" + fasilitas)

if arcpy.Exists(incident_path):
    arcpy.Delete_management(incident_path)
if arcpy.Exists(route_path):
    arcpy.Delete_management(route_path)

for l in arcpy.mapping.ListLayers(outNALayer):
    if l.isGroupLayer:
        continue
    else:
        if l.name == "Incidents":
            arcpy.CopyFeatures_management(l, incident_path)
        if l.name == "Routes":
            arcpy.CopyFeatures_management(l, route_path)

arcpy.AddMessage("== Join-join ==")

temp_join = os.path.join(dataset_template_path, "temp_join1")
if arcpy.Exists(temp_join):
    arcpy.Delete_management(temp_join)

arcpy.JoinField_management(incident_path, "OBJECTID", route_path, "IncidentID", ["Total_PanjangJalan"])

fieldMappings = arcpy.FieldMappings()
fldMapIn = arcpy.FieldMap()
fldMapIn.addInputField(persil_path, "IdBidang")
fldMapOut = fldMapIn.outputField
fldMapOut.name = "IdBidang"
fldMapIn.outputField = fldMapOut
fieldMappings.addFieldMap(fldMapIn)

fldMapIn = arcpy.FieldMap()
fldMapIn.addInputField(incident_path, "Total_PanjangJalan")
fldMapOut = fldMapIn.outputField
fldMapOut.name = "Total_PanjangJalan"
fldMapIn.outputField = fldMapOut
fieldMappings.addFieldMap(fldMapIn)

arcpy.SpatialJoin_analysis(persil_path, incident_path, temp_join, "JOIN_ONE_TO_ONE", "KEEP_ALL", fieldMappings, "INTERSECT")

field_names = [field.name for field in arcpy.ListFields(persil_path)]
if 'Jarak' + fasilitas not in field_names:
    arcpy.AddField_management(persil_path, 'Jarak' + fasilitas, "DOUBLE")

arcpy.JoinField_management(persil_path, "IdBidang", temp_join, "IdBidang", ["Total_PanjangJalan"])
arcpy.CalculateField_management(persil_path, 'Jarak' + fasilitas, "!Total_PanjangJalan!", "PYTHON")
arcpy.DeleteField_management(persil_path, 'Total_PanjangJalan')

arcpy.AddMessage("== Proses selesai ==")
