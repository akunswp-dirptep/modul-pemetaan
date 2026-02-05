import os, arcpy

arcpy.AddMessage("== Proses dimulai ==")

appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
tempdata = os.path.join(appdata, "temp")

jaringan_jalan = "Jaringan_Jalan"

kls_jln = arcpy.GetParameterAsText(0)
lb_jalan = arcpy.GetParameter(1)
status = arcpy.GetParameterAsText(2)
s_kls_jln = 1
SimLJln2 = "0"

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

if kls_jln == "Arteri Primer":
    s_kls_jln = 7
elif kls_jln == "Arteri Sekunder":
    s_kls_jln = 6
elif kls_jln == "Kolektor Primer":
    s_kls_jln = 5
elif kls_jln == "Kolektor Sekunder":
    s_kls_jln = 4
elif kls_jln == "Lokal Primer":
    s_kls_jln = 3
elif kls_jln == "Lokal Sekunder":
    s_kls_jln = 2
elif kls_jln == "Lokal Setapak":
    s_kls_jln = 1
else:
    s_kls_jln = 0

jalan_fields = [f.name for f in arcpy.ListFields(jaringan_jalan)]

if "kls_jln" not in jalan_fields or "lb_jln" not in jalan_fields or "s_kls_jln" not in jalan_fields:
    arcpy.AddError("Field " + "kls_jln, lb_jln, s_kls_jln" + " tidak ditemukan.")
    raise arcpy.ExecuteError

ada_seleksi = 0
ada_seleksi = len(arcpy.Describe(jaringan_jalan).FIDSet)
if ada_seleksi > 0:
    rows = arcpy.UpdateCursor(jaringan_jalan)
    for row in rows:
        row.setValue("kls_jln", kls_jln)
        row.setValue("lb_jln", lb_jalan)
        row.setValue("s_kls_jln", s_kls_jln)
        row.setValue("status_jal", status)
        rows.updateRow(row)
    del row
    del rows

# arcpy.RefreshTOC()
# arcpy.RefreshActiveView()

#edit 28/9/22
arcpy.CalculateField_management(jaringan_jalan, "kls_jln" ,'"'+ kls_jln +'"', "PYTHON3", "")
arcpy.AddMessage("== Proses selesai ==")
