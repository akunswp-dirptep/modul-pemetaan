import arcpy, os, datetime, math, sys, requests, json

appdata = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

tgl_transaksi = arcpy.GetParameterAsText(0)
harga_jualbeli = arcpy.GetParameter(1)
luas_tanah = arcpy.GetParameter(2)
peruntukan = arcpy.GetParameterAsText(3)
luas_bangunan = arcpy.GetParameter(4)
tahun_pembuatan = arcpy.GetParameter(5)
tahun_renovasi = arcpy.GetParameter(6)
keadaan_fisik = arcpy.GetParameterAsText(7)
biaya_bangunan_m2 = arcpy.GetParameterAsText(8)

persentawar = arcpy.GetParameter(9)

sampel = 'Titik_Sampel_Update'
# sampel_path = os.path.join(datas, sampel)

ada_seleksi = 0
ada_seleksi = len(arcpy.Describe(sampel).FIDSet)

jeniszona = 1
if peruntukan == "Non-Pertanian":
    jeniszona = 1
elif peruntukan == "Pertanian":
    jeniszona = 2

data = {}

keadaan_fisik1 = "B"
if keadaan_fisik == "Baik":
    keadaan_fisik1 = "B"
elif keadaan_fisik == "Sedang":
    keadaan_fisik1 = "S"
elif keadaan_fisik == "Jelek":
    keadaan_fisik1 = "J"
elif keadaan_fisik == "Jelek Sekali":
    keadaan_fisik1 = "JS"
elif keadaan_fisik == "Baik Sekali":
    keadaan_fisik1 = "BS"

if ada_seleksi > 0:
    if tgl_transaksi:
        rows = arcpy.UpdateCursor(sampel)
        for row in rows:
            a = datetime.datetime.strptime(tgl_transaksi, '%d/%m/%Y')
            a = a.strftime("%Y-%m-%d")
            row.setValue("Tgl_Penawaran_Transaksi", a)
        rows.updateRow(row)
        del row
        del rows

    if harga_jualbeli:
        with arcpy.da.UpdateCursor(sampel, ["Harga_Penawaran_Transaksi", "Harga_Penyesuaian", "Jenis_Data"]) as rows:
            for row in rows:
                if harga_jualbeli:
                    if row[2] == "Penawaran":
                        row[0] = harga_jualbeli
                        row[1] = 0.9 * harga_jualbeli
                    elif row[2] == "Transaksi":
                        row[0] = harga_jualbeli
                        row[1] = harga_jualbeli
                    rows.updateRow(row)
            del row, rows

    if luas_tanah:
        arcpy.CalculateField_management (sampel,"Luas_Tanah_m2", luas_tanah)

    if peruntukan:
        rows = arcpy.UpdateCursor(sampel)
        for row in rows:
            row.setValue("Zoning", jeniszona)
            rows.updateRow(row)
        del row
        del rows

    if luas_bangunan:
        arcpy.CalculateField_management (sampel,"Luas_Bangunan", luas_bangunan)

    if tahun_pembuatan:
        arcpy.CalculateField_management(sampel, "Tahun_Pembuatan", tahun_pembuatan)

    if tahun_renovasi:
        arcpy.CalculateField_management(sampel, "Tahun_Renovasi", tahun_renovasi)

    if keadaan_fisik:
        rows = arcpy.UpdateCursor(sampel)
        for row in rows:
            row.setValue("Keadaan_Fisik", keadaan_fisik1)
            rows.updateRow(row)
        del row, rows

    if biaya_bangunan_m2:
        arcpy.CalculateField_management(sampel, "Biaya_Bangunan_m2", biaya_bangunan_m2)
    
    if persentawar:
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
    #update rumus
    rows = arcpy.UpdateCursor(sampel)
    for row in rows:
        # arcpy.AddMessage(type(int(row.getValue("Tahun_Penilaian"))))
        row.setValue("Panjang", row.getValue("Luas_Tanah_m2") / row.getValue("Lebar_Depan"))
        row.setValue("RCN", str(int(row.getValue("Biaya_Bangunan_m2")) * row.getValue("Luas_Bangunan")))

        umur_efektif = str(math.ceil(((int(row.getValue("Tahun_Penilaian")) - row.getValue("Tahun_Pembuatan")) + 2 * (int(row.getValue("Tahun_Penilaian")) - row.getValue("Tahun_Renovasi")))/3))
        row.setValue("Umur_Efektif", umur_efektif)
        if row.getValue("Luas_Bangunan") > 0:
            row.setValue("Nilai_Bangunan", str(math.ceil(int(row.getValue("RCN")) * ( 100 - int(row.getValue("Penyusutan"))) // 100)))
        
        row.setValue("Nilai_Bangunan_Rp", str(row.getValue("Nilai_Bangunan")))

        harga_tanah = (int(float(row.getValue("Harga_Penyesuaian"))))-int(float(row.getValue("Nilai_Bangunan")))
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
            "umur_efektif": umur_efektif,
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

    # #update sipetik
    # field_names = [f.name for f in arcpy.ListFields(sampel)]
    # rows = arcpy.SearchCursor(sampel)
    # for row in rows:
    #     for v in field_names:
    #         if v == "Shape":
    #             arcpy.AddMessage("")
    #         else:
    #             data[v.lower()] = row.getValue(v)
    #     del v
    # del row, rows

    # json_object = json.dumps(data)
    # # arcpy.AddMessage(json_object)

    # url = "https://sipenta.atrbpn.go.id/api/index.php/updatesample/sample"
    # session = requests.Session()
    # response = session.get(url)
    # client = requests.session()
    # client.get(url)
    # if 'tokencsrf' in client.cookies:
    #     csrftoken = client.cookies['tokencsrf']
    # else:
    #     csrftoken = client.cookies['tokencsrf']

    # cookies = {'tokencsrf': csrftoken}
    # data = {
    #     "data": json_object,
    #     "tokencsrf": csrftoken}

    # x = requests.post(url, cookies=cookies, data=data).text
    # # arcpy.AddMessage(x)
    # y = json.loads(x)

    # if y["status"] == "sukses":
    #     arcpy.AddMessage(y["message"])
    # else:
    #     arcpy.AddError(y["status"])
    #     arcpy.AddMessage(y["message"])

    # # arcpy.AddMessage(y)
