import os
import arcpy

arcpy.AddMessage("== Proses mulai ==")

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_jalan_path = os.path.join(appdata, "jalan.dat")
conf_persil_path = os.path.join(appdata, "persil.dat")
conf_file = open(conf_jalan_path, "r")
list_config = conf_file.readlines()
conf_file.close()

dataset_template_path = ""
dataset_path = ""
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

# conf_file = open(conf_persil_path, "r")
# list_config = conf_file.readlines()
# conf_file.close()

persil = "Persil_Taru"
persil_path = os.path.join(dataset_path, persil)
persilcentroid = "Persil_Taru_Centroid"
persilcentroid_path = os.path.join(dataset_path, persilcentroid)

if arcpy.Exists(persilcentroid_path):
    arcpy.Delete_management(persilcentroid_path)

arcpy.FeatureToPoint_management(persil_path, persilcentroid_path, "INSIDE")

# for line in list_config:
#     line = line.replace("\n", "")
#     persil_config = []
#     persil_config = line.split(",")
#     if persil_config[0] == "persil":
#         persil = persil_config[1].split(";")[0]
#         persil_path = persil_config[1].split(";")[1]
#     if persil_config[0] == "persilcentroid":
#         persilcentroid = persil_config[1].split(";")[0]
#         persilcentroid_path = persil_config[1].split(";")[1]

dataset_template_path = os.path.dirname(jaringanjalan_nd_path)
junction_nd_path = os.path.join(os.path.dirname(jaringanjalan_nd_path), "JaringanJalan_ND_Junctions")

arcpy.AddMessage("== Persiapan ==")

jalan_fields = [f.name for f in arcpy.ListFields(jaringanjalan_path)]
if 'P_Jalan' not in jalan_fields:
    arcpy.AddField_management(jaringanjalan_path, 'P_Jalan', 'DOUBLE')
arcpy.CalculateField_management(jaringanjalan_path, 'P_Jalan', '!shape.length!', 'PYTHON')

outNALayerName = "hasil_kelas"
outNALayerName_path = os.path.join(dataset_template_path, outNALayerName)
impedance_attribute = "P_Jalan"
accumulateAttributeName = ["P_Jalan"]

dataset_kelas_jalan_path = os.path.join(os.path.dirname(dataset_path), "kelas_jalan")

# arcpy.AddMessage(nd_path)

arcpy.env.workspace = dataset_kelas_jalan_path
list_fc = arcpy.ListFeatureClasses("*")
list_fasility = []

namafield = ["jk_kols", "jk_kolp", "jk_atrs", "jk_atrp"]

for fc in list_fc:
    if "JunctionKls1" in fc:
        continue
    temp_path = os.path.join(dataset_kelas_jalan_path, fc)
    hsl = arcpy.GetCount_management(temp_path)
    if hsl[0] > 0:
        list_fasility.append(fc)

for fc in list_fasility:
    hasilNAObject = arcpy.MakeClosestFacilityLayer_na(nd_path, outNALayerName, impedance_attribute, "TRAVEL_FROM", "", 1)
    outNALayer = hasilNAObject.getOutput(0)
    fasilitas = fc
    namafield_ = namafield[int(fasilitas.replace("JunctionKls", "")) - 2]
    kls = fc.replace("JunctionKls", "")
    fasilitas_path = os.path.join(dataset_kelas_jalan_path, fasilitas)

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

    arcpy.JoinField_management(incident_path, "OBJECTID", route_path, "IncidentID", ["Total_P_Jalan"])

    # fieldMappings = arcpy.FieldMappings()
    # fldMapIn = arcpy.FieldMap()
    # fldMapIn.addInputField(persil_path, "IdBidang")
    # fldMapOut = fldMapIn.outputField
    # fldMapOut.name = "IdBidang"
    # fldMapIn.outputField = fldMapOut
    # fieldMappings.addFieldMap(fldMapIn)
    #
    # fldMapIn = arcpy.FieldMap()
    # fldMapIn.addInputField(incident_path, "Total_P_Jalan")
    # fldMapOut = fldMapIn.outputField
    # fldMapOut.name = "Total_P_Jalan"
    # fldMapIn.outputField = fldMapOut
    # fieldMappings.addFieldMap(fldMapIn)
    #
    # arcpy.SpatialJoin_analysis(persil_path, incident_path, temp_join, "JOIN_ONE_TO_ONE", "KEEP_ALL", fieldMappings, "INTERSECT")
    arcpy.SpatialJoin_analysis(persil_path, incident_path, temp_join, "JOIN_ONE_TO_ONE", "KEEP_ALL", "IdBidang \"IdBidang\" true true false 4 Long 0 0 ,First,#," + persil_path + ",IdBidang,-1,-1;Total_P_Jalan \"Total_P_Jalan\" true true false 8 Double 0 0 ,First,#," + incident_path + ",Total_P_Jalan,-1,-1", "INTERSECT", "", "")

    field_names = [field.name for field in arcpy.ListFields(persil_path)]
    if namafield_ not in field_names:
        arcpy.AddField_management(persil_path, namafield_, "DOUBLE")

    arcpy.JoinField_management(persil_path, "IdBidang", temp_join, "IdBidang", ["Total_P_Jalan"])
    arcpy.CalculateField_management(persil_path, namafield_, "!Total_P_Jalan!", "PYTHON")
    arcpy.DeleteField_management(persil_path, 'Total_P_Jalan')

    if arcpy.Exists("lyr"):
        arcpy.Delete_management("lyr")
    arcpy.MakeFeatureLayer_management(persil_path, "lyr", "s_kls_jln=" + kls)
    arcpy.CalculateField_management("lyr", namafield_, "!lb_jln!", "PYTHON")

if arcpy.Exists(persil):
    arcpy.Delete_management(persil)
arcpy.MakeFeatureLayer_management(persil_path, persil)
arcpy.SetParameterAsText(0, persil)

arcpy.AddMessage("== Proses selesai ==")
