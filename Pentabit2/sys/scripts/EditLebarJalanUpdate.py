import os
import arcpy

arcpy.AddMessage("== Proses dimulai ==")

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

jaringanjalan = "Jaringan_Jalan"

lb_jalan = arcpy.GetParameter(0)

field_names = [field.name for field in arcpy.ListFields(jaringanjalan)]
if 'lb_jln' not in field_names:
    arcpy.AddField_management(jaringanjalan, 'lb_jln', 'DOUBLE')
if 'SimLJln2' not in field_names:
    arcpy.AddField_management(jaringanjalan, 'SimLJln2', 'TEXT')

ada_seleksi = len(arcpy.Describe(jaringanjalan).FIDSet)

if ada_seleksi > 0:
    if lb_jalan == 0:
        SimLJln2 = "0"
    elif lb_jalan > 0 and lb_jalan <= 1.5:
        SimLJln2 = "1.5"
    elif lb_jalan > 1.5 and lb_jalan <= 3:
        SimLJln2 = "3"
    elif lb_jalan > 3 and lb_jalan <= 5:
        SimLJln2 = "5"
    elif lb_jalan > 5 and lb_jalan <= 8:
        SimLJln2 = "8"
    elif lb_jalan > 8:
        SimLJln2 = "8+"

    rows = arcpy.UpdateCursor(jaringanjalan)

    for row in rows:
        row.setValue("lb_jln", lb_jalan)
        row.setValue("SimLJln2", SimLJln2)
        rows.updateRow(row)

    del row
    del rows
#edit 28/9/22
arcpy.CalculateField_management(jaringanjalan, "SimLJln2" ,'"' + SimLJln2 + '"', "PYTHON3", "")
arcpy.AddMessage("== Proses selesai ==")
    # arcpy.RefreshTOC()
    # arcpy.RefreshActiveView()
