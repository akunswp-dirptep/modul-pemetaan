import os, arcpy

arcpy.AddMessage("== Proses dimulai ==")

appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

field = "lb_jln"
field2 = "COType"
val = arcpy.GetParameterAsText(0)

lyrlokalsetapak = "Jalan_Lokal_Setapak"
lyrlokalsekunder = "Jalan_Lokal_Sekunder"
lyrlokalprimer = "Jalan_Lokal_Primer"
lyrkolektorsekunder = "Jalan_Kolektor_Sekunder"
lyrkolektorprimer = "Jalan_Kolektor_Primer"
lyrarterisekunder = "Jalan_Arteri_Sekunder"
lyrarteriprimer = "Jalan_Arteri_Primer"
jaringanjalan = "Jaringan_Jalan"

ada_seleksi = 0
if arcpy.Exists(lyrlokalsetapak):
    ada_seleksi = len(arcpy.Describe(lyrlokalsetapak).FIDSet)

if ada_seleksi > 0:
    rows = arcpy.UpdateCursor(lyrlokalsetapak)
    for row in rows:
        row.setValue(field, val)
        val_temp = row.getValue(field2)
        if len(val_temp) > 0:
            val_temp = val_temp[0]
        val_temp = val_temp + "E"
        row.setValue(field2, val_temp)
        rows.updateRow(row)
    del row
    del rows

ada_seleksi = 0
if arcpy.Exists(lyrlokalsekunder):
    ada_seleksi = len(arcpy.Describe(lyrlokalsekunder).FIDSet)

if ada_seleksi > 0 and arcpy.Exists(lyrlokalsekunder):
    rows = arcpy.UpdateCursor(lyrlokalsekunder)
    for row in rows:
        row.setValue(field, val)
        val_temp = row.getValue(field2)
        if len(val_temp) > 0:
            val_temp = val_temp[0]
        val_temp = val_temp + "E"
        row.setValue(field2, val_temp)
        rows.updateRow(row)
    del row
    del rows

ada_seleksi = 0
if arcpy.Exists(lyrlokalprimer):
    ada_seleksi = len(arcpy.Describe(lyrlokalprimer).FIDSet)

if ada_seleksi > 0 and arcpy.Exists(lyrlokalprimer):
    rows = arcpy.UpdateCursor(lyrlokalprimer)
    for row in rows:
        row.setValue(field, val)
        val_temp = row.getValue(field2)
        if len(val_temp) > 0:
            val_temp = val_temp[0]
        val_temp = val_temp + "E"
        row.setValue(field2, val_temp)
        rows.updateRow(row)
    del row
    del rows

ada_seleksi = 0
if arcpy.Exists(lyrkolektorsekunder):
    ada_seleksi = len(arcpy.Describe(lyrkolektorsekunder).FIDSet)

if ada_seleksi > 0 and arcpy.Exists(lyrkolektorsekunder):
    rows = arcpy.UpdateCursor(lyrkolektorsekunder)
    for row in rows:
        row.setValue(field, val)
        val_temp = row.getValue(field2)
        if len(val_temp) > 0:
            val_temp = val_temp[0]
        val_temp = val_temp + "E"
        row.setValue(field2, val_temp)
        rows.updateRow(row)
    del row
    del rows

ada_seleksi = 0
if arcpy.Exists(lyrkolektorprimer):
    ada_seleksi = len(arcpy.Describe(lyrkolektorprimer).FIDSet)

if ada_seleksi > 0 and arcpy.Exists(lyrkolektorprimer):
    rows = arcpy.UpdateCursor(lyrkolektorprimer)
    for row in rows:
        row.setValue(field, val)
        val_temp = row.getValue(field2)
        if len(val_temp) > 0:
            val_temp = val_temp[0]
        val_temp = val_temp + "E"
        row.setValue(field2, val_temp)
        rows.updateRow(row)
    del row
    del rows

ada_seleksi = 0
if arcpy.Exists(lyrarterisekunder):
    ada_seleksi = len(arcpy.Describe(lyrarterisekunder).FIDSet)

if ada_seleksi > 0 and arcpy.Exists(lyrarterisekunder):
    rows = arcpy.UpdateCursor(lyrarterisekunder)
    for row in rows:
        row.setValue(field, val)
        val_temp = row.getValue(field2)
        if len(val_temp) > 0:
            val_temp = val_temp[0]
        val_temp = val_temp + "E"
        row.setValue(field2, val_temp)
        rows.updateRow(row)
    del row
    del rows

ada_seleksi = 0
if arcpy.Exists(lyrarteriprimer):
    ada_seleksi = len(arcpy.Describe(lyrarteriprimer).FIDSet)

if ada_seleksi > 0 and arcpy.Exists(lyrarteriprimer):
    rows = arcpy.UpdateCursor(lyrarteriprimer)
    for row in rows:
        row.setValue(field, val)
        val_temp = row.getValue(field2)
        if len(val_temp) > 0:
            val_temp = val_temp[0]
        val_temp = val_temp + "E"
        row.setValue(field2, val_temp)
        rows.updateRow(row)
    del row
    del rows

ada_seleksi = 0
if arcpy.Exists(jaringanjalan):
    ada_seleksi = len(arcpy.Describe(jaringanjalan).FIDSet)

if ada_seleksi > 0 and arcpy.Exists(jaringanjalan):
    rows = arcpy.UpdateCursor(jaringanjalan)
    for row in rows:
        row.setValue(field, val)
        rows.updateRow(row)
    del row
    del rows
