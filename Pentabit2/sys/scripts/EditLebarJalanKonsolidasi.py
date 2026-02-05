import os
import arcpy

arcpy.AddMessage("== Proses dimulai ==")

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

jaringanjalan = "Jaringan_Jalan"

lebarjalan = float(arcpy.GetParameterAsText(0))

field_names = [field.name for field in arcpy.ListFields(jaringanjalan)]
if 'lb_jln' not in field_names:
    arcpy.AddField_management(jaringanjalan, 'lb_jln', 'DOUBLE')
if 'Sim_LJln' not in field_names:
    arcpy.AddField_management(jaringanjalan, 'Sim_LJln', 'TEXT')

rows = arcpy.UpdateCursor(jaringanjalan)

for row in rows:
    row.lb_jln = lebarjalan
    row.status_jal = "Update"
    if lebarjalan > 1:
        row.Sim_LJln = "> 1"
    elif lebarjalan > 0 and lebarjalan <= 1:
        row.Sim_LJln = "0 - 1"
    else:
        row.Sim_LJln = "0"
    rows.updateRow(row)

del row
del rows

arcpy.RefreshTOC()
arcpy.RefreshActiveView()
