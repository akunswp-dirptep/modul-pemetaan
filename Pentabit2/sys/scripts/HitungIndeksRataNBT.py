import os, arcpy

appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

dataset_path = ""

conf_jalan_path = os.path.join(appdata, "persil.dat")

conf_file = open(conf_jalan_path, "r")
list_config = conf_file.readlines()
conf_file.close()
for line in list_config:
    line = line.replace("\n", "")
    persil_config = []
    persil_config = line.split(",")
    if persil_config[0] == "dataset":
        dataset_path = persil_config[1]

persil = "Persil_Baru"
persil_path = os.path.join(dataset_path, persil)
indeks_path = os.path.join(dataset_path, "Titik_Indeks")
temp_path = os.path.join(dataset_path, "temp")

#Perbaikan untuk v3.1
arcpy.SpatialJoin_analysis(indeks_path, persil_path, temp_path)
temp_fields = [field.name for field in arcpy.ListFields(temp_path)]
if 'indeks_rata' not in temp_fields:
    arcpy.AddField_management("temp","indeks_rata","DOUBLE",2)
##if 'indeks_rata' in temp_fields:
##    arcpy.AddField_management("temp","indeks_rata","DOUBLE",2)

persil_fields = [field.name for field in arcpy.ListFields(persil_path)]
if 'indeks_rata' not in persil_fields:
    arcpy.AddField_management(persil_path,"indeks_rata","DOUBLE",2)

indeks_fields = [field.name for field in arcpy.ListFields(indeks_path)]
if 'indeks_rata' not in indeks_fields:
    arcpy.AddField_management(indeks_path,"indeks_rata","DOUBLE",2)

listzona = []
for rows in arcpy.SearchCursor(persil_path, where_clause = "s_zonasi is not null"):
    listzona.append(rows.s_zonasi)
del rows
listzona = [int(x) for x in listzona]
zona = list(dict.fromkeys(listzona))
        
for i in zona:
    total = 0
    j = 0
    rows = arcpy.SearchCursor(temp_path, "s_zonasi = " + str(i))
    for row in rows:
        if not row.getValue("outlier"):
            j = j + 1
            if row.getValue("indeks"):
                total = total + row.getValue("indeks")
    del rows

    if j != 0:
        rata = round((total/1.0) / j,2)
        
        rowsa = arcpy.UpdateCursor (indeks_path, where_clause = "s_zonasi = " + str (i))
        for rowa in rowsa:
            rowa.setValue ("indeks_rata", rata)
            rowsa.updateRow(rowa)

        rowsb = arcpy.UpdateCursor (persil_path, where_clause = "s_zonasi = " + str (i))
        for rowb in rowsb:
            rowb.setValue ("indeks_rata", rata)
            rowsb.updateRow(rowb)

rows = arcpy.UpdateCursor(indeks_path)
for row in rows: 
    rowsa = arcpy.UpdateCursor (persil_path, "IdBidang = " + str(row.IdBidang))
    for rowa in rowsa:
        if row.getValue("outlier") == "Indeks Outlier":
            rowa.setValue ("indeks_rata", None)
            row.setValue ("indeks_rata", None)
        rowsa.updateRow(rowa)
    rows.updateRow(row)
        
