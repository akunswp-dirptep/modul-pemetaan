import arcpy
import os, math

arcpy.AddMessage("== Proses dimulai ==")

# appdata = u'c:\znt\sys'
appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

Sampel_Prediksi = "Sampel_Prediksi"
Persil_Model = "Persil_Model"
Sampel_Model = "Sampel_Model"

kls_jln = arcpy.GetParameterAsText(0)
lb_jalan = arcpy.GetParameter(1)
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

prediksi_fields = [f.name for f in arcpy.ListFields(Sampel_Prediksi)]
persil_fields = [f.name for f in arcpy.ListFields(Persil_Model)]
sampel_fields = [f.name for f in arcpy.ListFields(Sampel_Model)]

if "kls_jln" not in prediksi_fields or "lb_jln" not in prediksi_fields or "s_kls_jln" not in prediksi_fields:
    arcpy.AddError("Field " + "kls_jln, lb_jln, s_kls_jln" + " tidak ditemukan.")
    raise arcpy.ExecuteError

if "kls_jln" not in persil_fields or "lb_jln" not in persil_fields or "s_kls_jln" not in persil_fields:
    arcpy.AddError("Field " + "kls_jln, lb_jln, s_kls_jln" + " tidak ditemukan.")
    raise arcpy.ExecuteError

if "kls_jln" not in sampel_fields or "lb_jln" not in sampel_fields or "s_kls_jln" not in sampel_fields:
    arcpy.AddError("Field " + "kls_jln, lb_jln, s_kls_jln" + " tidak ditemukan.")
    raise arcpy.ExecuteError

ada_seleksi = 0
ada_seleksi = len(arcpy.Describe(Sampel_Prediksi).FIDSet)

if ada_seleksi > 0:
    rows = arcpy.UpdateCursor(Sampel_Prediksi)
    for row in rows:
        if "ln_lb_jln" in prediksi_fields:
            row.setValue("ln_lb_jln", math.log(lb_jalan))
        if "iv_lb_jln" in prediksi_fields and lb_jalan != 0:
            row.setValue("iv_lb_jln", 1.0 / lb_jalan)
        if "ln_kls_jln" in prediksi_fields:
            row.setValue("ln_kls_jln", math.log(s_kls_jln))
        if "iv_kls_jln" in prediksi_fields and s_kls_jln != 0:
            row.setValue("iv_kls_jln", 1.0 / s_kls_jln)
        row.setValue("kls_jln", kls_jln)
        row.setValue("lb_jln", lb_jalan)
        row.setValue("s_kls_jln", s_kls_jln)
        rows.updateRow(row)
    del row
    del rows

ada_seleksi = 0
ada_seleksi = len(arcpy.Describe(Persil_Model).FIDSet)

if ada_seleksi > 0:
    rows = arcpy.UpdateCursor(Persil_Model)
    for row in rows:
        if "ln_lb_jln" in persil_fields:
            row.setValue("ln_lb_jln", math.log(lb_jalan))
        if "iv_lb_jln" in persil_fields and lb_jalan != 0:
            row.setValue("iv_lb_jln", 1.0 / lb_jalan)
        if "ln_kls_jln" in persil_fields:
            row.setValue("ln_kls_jln", math.log(s_kls_jln))
        if "iv_kls_jln" in persil_fields and s_kls_jln != 0:
            row.setValue("iv_kls_jln", 1.0 / s_kls_jln)
        row.setValue("kls_jln", kls_jln)
        row.setValue("lb_jln", lb_jalan)
        row.setValue("s_kls_jln", s_kls_jln)
        rows.updateRow(row)
    del row
    del rows

ada_seleksi = 0
ada_seleksi = len(arcpy.Describe(Sampel_Model).FIDSet)

if ada_seleksi > 0:
    rows = arcpy.UpdateCursor(Sampel_Model)
    for row in rows:
        if "ln_lb_jln" in sampel_fields:
            row.setValue("ln_lb_jln", math.log(lb_jalan))
        if "iv_lb_jln" in sampel_fields and lb_jalan != 0:
            row.setValue("iv_lb_jln", 1.0 / lb_jalan)
        if "ln_kls_jln" in sampel_fields:
            row.setValue("ln_kls_jln", math.log(s_kls_jln))
        if "iv_kls_jln" in sampel_fields and s_kls_jln != 0:
            row.setValue("iv_kls_jln", 1.0 / s_kls_jln)
        row.setValue("kls_jln", kls_jln)
        row.setValue("lb_jln", lb_jalan)
        row.setValue("s_kls_jln", s_kls_jln)
        rows.updateRow(row)
    del row
    del rows

#update 19/10/2021
#arcpy.RefreshTOC()
#arcpy.RefreshActiveView()

