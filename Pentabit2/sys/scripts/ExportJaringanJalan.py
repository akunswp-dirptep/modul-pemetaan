import os
import arcpy

arcpy.AddMessage("== Proses dimulai ==")

out = arcpy.GetParameterAsText(0)
kab_kota = arcpy.GetParameterAsText(1)
nama_kab_kota = arcpy.GetParameterAsText(2)
tahun = arcpy.GetParameter(3)
# shp = arcpy.GetParameterAsText(1)

arcpy.env.overwriteOutput = True

# if ".shp" not in shp:
#     shp = shp + ".shp"

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
conf_jalan_path = os.path.join(appdata, "jalan.dat")

conf_file = open(conf_jalan_path, "r")
list_config = conf_file.readlines()
conf_file.close()

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

oid_fieldname = arcpy.Describe(jaringanjalan_path).OIDFieldName
field_names = [field.name for field in arcpy.ListFields(jaringanjalan_path)]

for nm in field_names:
    if "OBJECTID" in nm and nm != oid_fieldname:
        arcpy.DeleteField_management(jaringanjalan_path, nm)

# shp = "jaringan_jalan.shp"
shp = "Peta Jaringan Jalan " + kab_kota + " " + nama_kab_kota + " Tahun " + str(tahun) + ".shp"
output = os.path.join(out, shp)
#update 12/10/2022
exp = "get(!s_kls_jln!, !lb_jln!)"
code_block = """
def get(b,c):
    if c is None:
        c = 0
    if b == 7:
        if c < 11:
            return 11
        else:
            return c
    elif b == 6:
        if c < 8:
            return 8
        else:
            return c
    elif b == 5:
        if c < 6:
            return 6
        else:
            return c
    elif b == 4:
        if c < 5:
            return 5
        else:
            return c
    elif b == 3:
        if c < 1.5:
            return 1.5
        else:
            return c
    elif b == 2:
        if c < 1.5:
            return 1.5
        else:
            return c
    elif b == 1:
        if c < 1.5:
            return 1.5
        else:
            return c"""
arcpy.CalculateField_management(jaringanjalan_path, u'lb_jln', exp, "PYTHON", code_block)

#exp = "lbr"
#code_block = """
#Dim lbr
#If IsNull([lb_jln]) Then
#    lbr = 0
#end if
#If [s_kls_jln] = 5 Then
#    if [lb_jln] < 11 Then
#        lbr = 11
#    else
#        lbr = [lb_jln]
#    end if
#elseif [s_kls_jln] = 4 Then
#    if [lb_jln] < 8 Then
#        lbr = 8
#    else
#        lbr = [lb_jln]
#    end if
#elseif [s_kls_jln] = 3 Then
#    if [lb_jln] < 6 Then
#        lbr = 6
#    else
#        lbr = [lb_jln]
#    end if
#elseif [s_kls_jln] = 2 Then
#    if [lb_jln] < 5 Then
#        lbr = 5
#    else
#        lbr = [lb_jln]
#    end if
#elseif [s_kls_jln] = 1 Then
#    if [lb_jln] < 1.5 Then
#        lbr = 1.5
#    else
#        lbr = [lb_jln]
#    end if
#end if"""
#arcpy.CalculateField_management(jaringanjalan_path, "lb_jln", exp, "PYTHON", code_block)

if arcpy.Exists(output):
    arcpy.Delete_management(output)

arcpy.CopyFeatures_management(jaringanjalan_path, os.path.join(out, shp))
# arcpy.FeatureClassToShapefile_conversion([jaringanjalan_path], out)

arcpy.AddMessage("== Proses selesai ==")
