import arcpy
import os

arcpy.AddMessage("== Proses dimulai ==")

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

jaringan_jalan = "Jaringan_Jalan"
kls_jln = arcpy.GetParameterAsText(0)
lb_jalan = float(arcpy.GetParameterAsText(1))
sts_jalan = arcpy.GetParameterAsText(2)
s_kls_jln = 1

if kls_jln == "Arteri Primer":
    s_kls_jln = 5
elif kls_jln == "Arteri Sekunder":
    s_kls_jln = 4
elif kls_jln == "Kolektor Primer":
    s_kls_jln = 3
elif kls_jln == "Kolektor Sekunder":
    s_kls_jln = 2
else:
    s_kls_jln = 1
SimLJln2 = "0"

sampel_fields = [f.name for f in arcpy.ListFields(jaringan_jalan)]

if "status_jal" not in sampel_fields or "kls_jln" not in sampel_fields or "lb_jln" not in sampel_fields or "s_kls_jln" not in sampel_fields:
    arcpy.AddError("Field " + "kls_jln, lb_jln, s_kls_jln" + " tidak ditemukan.")
    raise arcpy.ExecuteError

if "SimLJln2" not in jaringan_jalan:
    arcpy.AddField_management(jaringan_jalan, "SimLJln2", "TEXT")

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

rows = arcpy.UpdateCursor(jaringan_jalan)

for row in rows:
    row.setValue("kls_jln", kls_jln)
    row.setValue("lb_jln", float(lb_jalan))
    row.setValue("SimLJln2", SimLJln2)
    row.setValue("s_kls_jln", float(s_kls_jln))
    row.setValue("status_jal", sts_jalan)
    rows.updateRow(row)

del row
del rows

arcpy.RefreshTOC()
arcpy.RefreshActiveView()

