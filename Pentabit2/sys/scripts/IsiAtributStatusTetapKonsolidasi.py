import arcpy, os

def mySplitString(somestring):
    hasil = []
    lenstr = len(somestring)
    kutipcounter = 0
    myword = ""
    i = 0
    for a in somestring:
        i = i + 1
        if a == "'":
            kutipcounter = kutipcounter + 1
        if kutipcounter == 1:
            if a != "'":
                myword = myword + a
        elif kutipcounter == 2:
            kutipcounter = 0
        else:
            if a == " ":
                hasil.append(myword)
                myword = ""
            else:
                myword = myword + a
                if i == lenstr:
                    hasil.append(myword)
    return hasil

arcpy.AddMessage("== Proses dimulai ==")

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

conf_var_path = os.path.join(appdata, "def_var.dat")
conf_file = open(conf_var_path, "r")
list_config = conf_file.readlines()
conf_file.close()
line = ""
for line in list_config:
    line = line.replace("\n", "")
splitval = []
fields_dont_delete = []
field_str_type = ['bentuk', 'letak', 'kls_jln', 'elvasi', 'zonasi']
splitval = line.split(";")
for a in splitval:
    fields_dont_delete.append(mySplitString(a)[1])
    if mySplitString(a)[1].lower() in field_str_type:
        fields_dont_delete.append("s_" + mySplitString(a)[1])

persil_conf_path = os.path.join(appdata, "persil.dat")
conf_file = open(persil_conf_path, "r")
list_config = conf_file.readlines()
conf_file.close()

dataset_path = ""

for line in list_config:
    line = line.replace("\n", "")
    jalan_config = []
    jalan_config = line.split(",")
    if jalan_config[0] == "dataset":
        dataset_path = jalan_config[1]

tempdata = os.path.join(appdata, "temp")

peta_persil = "Persil_Konsolidasi"
peta_persil_path = os.path.join(dataset_path, peta_persil)
peta_hanya_konsolidasi = "PersilHanyaKonsolidasi"
peta_hanya_konsolidasi_path = os.path.join(dataset_path, peta_hanya_konsolidasi)
peta_lama = "Persil"
peta_lama_path = os.path.join(dataset_path, peta_lama)
peta_erase = "Peta_Erase"
peta_erase_path = os.path.join(dataset_path, peta_erase)
peta_nonkonsol = "Peta_NonKonsolidasi"
peta_nonkonsol_path = os.path.join(dataset_path, peta_nonkonsol)

arcpy.AddMessage("== Hanya Konsolidasi (untuk erase) ==")

if arcpy.Exists(peta_hanya_konsolidasi_path):
    arcpy.Delete_management(peta_hanya_konsolidasi_path)
if arcpy.Exists(peta_hanya_konsolidasi):
    arcpy.Delete_management(peta_hanya_konsolidasi)

arcpy.MakeFeatureLayer_management(peta_persil_path, peta_hanya_konsolidasi, "\"obj_konsol\" = 'Konsolidasi'")

arcpy.AddMessage("== Pilih persil status update lalu erase ==")

if arcpy.Exists(peta_erase):
    arcpy.Delete_management(peta_erase)
if arcpy.Exists(peta_erase_path):
    arcpy.Delete_management(peta_erase_path)

arcpy.Erase_analysis(peta_persil_path, peta_hanya_konsolidasi, peta_erase_path)

#arcpy.AddMessage("== Join ==")

if arcpy.Exists(peta_nonkonsol):
    arcpy.Delete_management(peta_nonkonsol)
if arcpy.Exists(peta_nonkonsol_path):
    arcpy.Delete_management(peta_nonkonsol_path)

arcpy.AddMessage("== Pindahkan nilai pesil status Non Konsolidasi ke dalam Peta Erase ==")

fields = arcpy.ListFields(peta_erase_path)
fields_lower = [x.name.lower() for x in fields]
fields_to_add = []
for a in fields_dont_delete:
    if a not in ['IdBidang', 'NIB', 'obj_konsol']:
        fields_to_add.append(a)
    if a in fields_lower and a not in ['IdBidang', 'NIB', 'obj_konsol']:
        arcpy.DeleteField_management(peta_erase_path, a)

arcpy.JoinField_management(peta_erase_path, "IdBidang", peta_lama_path, "IdBidang", fields_to_add)

arcpy.AddMessage("== Pindahkan nilai pesil status Non Konsolidasi ke dalam Persil Konsolidasi ==")

fields = arcpy.ListFields(peta_persil_path)
fields_lower = [x.name.lower() for x in fields]
fields_to_add = []
for a in fields_dont_delete:
    if a not in ['IdBidang', 'NIB', 'obj_konsol']:
        fields_to_add.append(a)
    if a in fields_lower and a not in ['IdBidang', 'NIB', 'obj_konsol']:
        arcpy.DeleteField_management(peta_persil_path, a)

arcpy.JoinField_management(peta_persil_path, "IdBidang", peta_erase_path, "IdBidang", fields_to_add)

if arcpy.Exists(peta_persil):
    arcpy.Delete_management(peta_persil)

sim_indikator_akhir = os.path.join(appdata, "SimbologiPersilKonsolidasi.lyr")
arcpy.MakeFeatureLayer_management(peta_persil_path, peta_persil)
arcpy.ApplySymbologyFromLayer_management(peta_persil, sim_indikator_akhir)
arcpy.SetParameterAsText(0, peta_persil)

#arcpy.AddMessage("== Proses Selesai ==")
