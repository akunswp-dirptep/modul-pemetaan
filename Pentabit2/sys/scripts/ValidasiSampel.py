import arcpy, os, datetime, math, sys, requests, json

appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

sampel = 'Titik_Sampel_Update'

persentawar = 0.9
persentawar = arcpy.GetParameter(0)
hm= arcpy.GetParameterAsText(1)
hgb= arcpy.GetParameterAsText(2)
hp= arcpy.GetParameterAsText(3)
tma= arcpy.GetParameterAsText(4)

# ada_seleksi = 0
# ada_seleksi = len(arcpy.Describe(sampel).FIDSet)
# if ada_seleksi > 0:

#penyesuaian persentase penawaran
with arcpy.da.UpdateCursor(sampel, ["Harga_Penyesuaian", "Jenis_Data","Harga_Penawaran_Transaksi"]) as rows:
    for row in rows:
        if persentawar:
            if row[1] == "Individual":
                row[0] = row[2]
            elif row[1] == "Penawaran":
                row[0] = persentawar / 100 * int(row [2])
            elif row [1] == "Transaksi":
                row [0] = row[2]
        else:
            arcpy.AddError("Terdapat salah entry. Jenis Data bukan Penawaran, Transaksi, maupun Individual.")
        rows.updateRow(row)
del row
del rows

with arcpy.da.UpdateCursor(sampel, ["Status_Kepemilikan","Penyesuaian_Status_Kepemilikan"]) as rows:
    for row in rows:
        if not hm:
            if row[0] == "HM":
                row[1]= "0%"
        else:
            if row[0] == "HM":
                row[1]= hm + "%"
        rows.updateRow(row)
del row
del rows

with arcpy.da.UpdateCursor(sampel, ["Status_Kepemilikan","Penyesuaian_Status_Kepemilikan"]) as rows:
    for row in rows:
        if not hgb:
            if row[0] == "HGB":
                row[1]= "5%"
        else:
            if row[0] == "HGB":
                row[1]= hgb + "%"
        rows.updateRow(row)
del row
del rows

with arcpy.da.UpdateCursor(sampel, ["Status_Kepemilikan","Penyesuaian_Status_Kepemilikan"]) as rows:
    for row in rows:
        if not hp:
            if row[0] == "HP":
                row[1]= "5%"
        else:
            if row[0] == "HP":
                row[1]= hp + "%"
        rows.updateRow(row)
del row
del rows

with arcpy.da.UpdateCursor(sampel, ["Status_Kepemilikan","Penyesuaian_Status_Kepemilikan"]) as rows:
    for row in rows:
        if not tma:
            if row[0] == "TMA":
                row[1]= "10%"
        else:
            if row[0] == "TMA":
                row[1]= tma + "%"
        rows.updateRow(row)
del row
del rows

# # Validasi Waktu
# arcpy.AddField_management(sampel,"temp_date","DATE")
# arcpy.CalculateField_management(sampel,"temp_date",'!Tgl_Penawaran_Transaksi!')
# d1 = datetime.datetime(2023, 1, 1)
# d2 = datetime.datetime(2022, 6, 30)
# arcpy.AddField_management(sampel,"temp_waktu","STRING")
# with arcpy.da.UpdateCursor(sampel, ["temp_date","temp_waktu"]) as rows:
#     for row in rows:
#         if row[0] < d2:
#             row[1] = int((d2-row[0]).days/182*5)
#         else:
#             row[1] = int((d1-row[0]).days/182*5)
#         rows.updateRow(row)
# del row
# del rows
# arcpy.CalculateField_management(sampel,"Penyesuaian_Waktu",'str(!temp_waktu!) + "%"')
# arcpy.DeleteField_management(sampel,"temp_date")
# arcpy.DeleteField_management(sampel,"temp_waktu")

#update rumus
rows = arcpy.UpdateCursor(sampel)
for row in rows:
    harga_tanah = (int(float((row.getValue("Harga_Penyesuaian")).replace(',', '.'))))-int(float(row.getValue("Nilai_Bangunan")))
    row.setValue("Harga_Tanah", str(abs(harga_tanah)))
    
    row.setValue("nilluas", str(math.ceil((1 + (int(row.getValue("Penyesuaian_Waktu").strip("%"))) / 100 + (int(row.getValue("Penyesuaian_Status_Kepemilikan").strip("%"))) / 100 ) * int(row.getValue("Harga_Tanah")) )))
    row.setValue("nilai", math.ceil(int(row.getValue("nilluas")) / row.getValue("Luas_Tanah_m2")))

    #hitung penyusutan
    url = "https://sipenta.atrbpn.go.id/api/index.php/penyusutan/cek_penyusutan"
    session = requests.Session()
    response = session.get(url)
    client = requests.session()
    client.get(url)
    if 'tokencsrf' in client.cookies:
        csrftoken = client.cookies['tokencsrf']
    else:
        csrftoken = client.cookies['tokencsrf']

    cookies = {'tokencsrf': csrftoken}
    data = {
        "kode_bangunan": row.getValue("Kd_Jenis_Bangunan"),
        "umur_efektif": row.getValue("Umur_Efektif"),
        "biaya_bangunan": row.getValue("Biaya_Bangunan_m2"),
        "keadaan_fisik": row.getValue("Keadaan_Fisik"),
        "tokencsrf": csrftoken}

    x = requests.post(url, cookies=cookies, data=data).text
    y = json.loads(x)

    row.setValue("Penyusutan", y["penyusutan"])
    row.setValue("Penyusutan_Rumah_1", y["penyusutan_rm_1"])
    row.setValue("Penyusutan_Rumah_2", y["penyusutan_rm_2"])
    row.setValue("Penyusutan_Ruko_1", y["penyusutan_rk_1"])
    row.setValue("Penyusutan_Ruko_2", y["penyusutan_rk_2"])
    rows.updateRow(row)
del row, rows