import os, arcpy

appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_jalan_path = os.path.join(appdata, "jalan.dat")

conf_file = open(conf_jalan_path, "r")
list_config = conf_file.readlines()
conf_file.close()

dataset_path = ""
jaringanjalan = ""
jaringanjalan_path = ""

simbologipersil_path = os.path.join(appdata, "Simbologi_PersilPrediksi.lyrx")
simbologijalan_path = os.path.join(appdata, "Simbologi_JaringanJalan.lyrx")

for line in list_config:
    line = line.replace("\n", "")
    jalan_config = []
    jalan_config = line.split(",")
    if jalan_config[0] == "dataset":
        dataset_path = jalan_config[1]

aprx = arcpy.mp.ArcGISProject("CURRENT")
for m in aprx.listMaps():
    print(f"Map: {m.name}")
    for lyr in m.listLayers():
        print(f"\t{lyr.name}")
        if lyr.supports("NAME"):
            m.removeLayer(lyr)

jaringanjalan = "Jaringan_Jalan"
jaringanjalan_path = os.path.join(dataset_path, jaringanjalan)

persil = "Persil_Prediksi"
persil_path = os.path.join(dataset_path, persil)

arcpy.MakeFeatureLayer_management(jaringanjalan_path, jaringanjalan)
arcpy.ApplySymbologyFromLayer_management(jaringanjalan, simbologijalan_path)
arcpy.SetParameterAsText(0, jaringanjalan)

arcpy.MakeFeatureLayer_management(persil_path, persil)
arcpy.ApplySymbologyFromLayer_management(persil, simbologipersil_path)
arcpy.SetParameterAsText(1, persil)

arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputMFlag = "Disabled"

temp = 'C:/PenilaianTanah/Pentabit2/sys/NBT.pagx'
aprx = arcpy.mp.ArcGISProject('CURRENT')
# m = aprx.listMaps("CURRENT")[0]
m = aprx.activeMap

def doSomething():
    for lyt in aprx.listLayouts():
        if lyt.name != 'NBT':
            aprx.importDocument(temp)
            lyt.name = 'NBT'
        
        # for elem in lyt.listElements():
        #     if elem.type == 'MAPFRAME_ELEMENT':
        #         elem.map = m

if not aprx.listLayouts():
    aprx.importDocument(temp)
    doSomething()
else :           
    doSomething()

aprx.save()
del aprx
