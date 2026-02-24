# -*- coding: utf-8 -*-

import sys
import arcpy
import os
arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputMFlag = "Disabled"
script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from zntutils.zona_layer import get_config_values


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Impor Titik Sampel Dari Excel Toolbox"
        self.alias = "ImporTitikSampelDariExcel"

        # List of tool classes associated with this toolbox
        self.tools = [Impor_Titik_Sampel_Dari_Excel]


class Impor_Titik_Sampel_Dari_Excel(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Impor Titik Sampel Dari Excel"
        self.description = "Tool untuk mengimpor titik sampel dari file Excel ke dalam feature class."
        self.canRunInBackground = False
        # Daftar field target yang harus di-mapping ke kolom Excel


    def getParameterInfo(self):
        """Define parameter definitions"""
        # Parameter untuk memilih file Excel yang akan diimpor
        excel_param = arcpy.Parameter(
            displayName="File Excel",
            name="excel_file",
            datatype="File",
            parameterType="Required",
            direction="Input",
        )

        excel_param.filter.list = ["xlsx", "xls"]

        
        return [excel_param]

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return
    
    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        # Ambil path file Excel yang dipilih pengguna
        config_dan_paths = get_config_values()
        self.dataset_path = config_dan_paths['dataset_path']
        temp_folder = config_dan_paths['temp_folder']
        self.gdb_path = os.path.dirname(self.dataset_path)
        
         # Membuat file geodatabase sementara untuk menyimpan tabel impor
        temp_gdb = arcpy.management.CreateFileGDB(temp_folder, 'Sampel_Dari_Excel.gdb')[0]
        arcpy.management.CreateFeatureDataset(temp_gdb, 'temp_dataset', arcpy.SpatialReference(4326))  # WGS 84
        ds_path = os.path.join(temp_gdb, 'temp_dataset')
        excel_path = parameters[0].valueAsText
        output_table = os.path.join(temp_gdb, "Titik_Sampel_Excel")

        arcpy.conversion.ExcelToTable(excel_path, output_table, 'data')

        # Mengubah nama field menjadi tanpa spasi dan huruf kecil
        fields = arcpy.ListFields(output_table)
        for field in fields:
            new_name = field.name.replace('_', '').lower()
            if new_name != field.name:
                try:
                    if new_name =='konstantahargapenyesuaianpenawaran':
                        new_name = 'khpp'
                        arcpy.management.AlterField(output_table, field.name, new_name, new_name)
                    else:
                        arcpy.management.AlterField(output_table, field.name, new_name, new_name)
                except Exception as e:
                    arcpy.AddWarning(f"Gagal mengubah nama field {field.name} menjadi {new_name}: {e}")
        
        penyetaraan_header = [
            {
                'excel_field': 'nomorsampel',
                'excel_type': 'INTEGER',
                'target_field': 'Nomor_Entry',
                'target_type': 'INTEGER',
                'target_alias': 'Nomor Sampel'
            },
            {
                'excel_field': 'nomoridentifikasi',
                'excel_type': 'STRING',
                'target_field': 'No_Identifikasi',
                'target_type': 'STRING',
                'target_alias': 'Nomor Identifikasi'
            },
            {
                'excel_field': 'namasurveyor',
                'excel_type': 'STRING',
                'target_field': 'Surveyor',
                'target_type': 'STRING',
                'target_alias': 'Nama Surveyor'
            },
            {
                'excel_field': 'tanggalpelaksanaan',
                'excel_type': 'STRING',
                'target_field': 'Tanggal_Pelaksanaan',
                'target_type': 'STRING',
                'target_alias': 'Tanggal Pelaksanaan'
            },
            {
                'excel_field': 'bangunanbrukortanahkosongtk',
                'excel_type': 'STRING',
                'target_field': 'Kd_Jenis_Bangunan',
                'target_type': 'STRING',
                'target_alias': 'Bangunan (B)/Ruko(R)/ Tanah Kosong (TK)'
            },
            {
                'excel_field': 'alamat',
                'excel_type': 'STRING',
                'target_field': 'Alamat',
                'target_type': 'STRING',
                'target_alias': 'Alamat'
            },
            {
                'excel_field': 'kelurahan',
                'excel_type': 'STRING',
                'target_field': 'Kelurahan',
                'target_type': 'STRING',
                'target_alias': 'Kelurahan'
            },
            {
                'excel_field': 'kecamatan',
                'excel_type': 'STRING',
                'target_field': 'Kecamatan',
                'target_type': 'STRING',
                'target_alias': 'Kecamatan'
            },
            {
                'excel_field': 'x',
                'excel_type': 'DOUBLE',
                'target_field': 'X',
                'target_type': 'DOUBLE',
                'target_alias': 'X'
            },
            {
                'excel_field': 'y',
                'excel_type': 'DOUBLE',
                'target_field': 'Y',
                'target_type': 'DOUBLE',
                'target_alias': 'Y'
            },
            {
                'excel_field': 'statuskepemilikan',
                'excel_type': 'STRING',
                'target_field': 'Status_Kepemilikan',
                'target_type': 'STRING',
                'target_alias': 'Status Kepemilikan'
            },
            {
                'excel_field': 'jenisdata',
                'excel_type': 'STRING',
                'target_field': 'Jenis_Data',
                'target_type': 'STRING',
                'target_alias': 'Jenis Data'
            },
            {
                'excel_field': 'tanggalpenawarantransaksi',
                'excel_type': 'STRING',
                'target_field': 'Tgl_Penawaran_Transaksi',
                'target_type': 'STRING',
                'target_alias': 'Tanggal Penawaran/Transaksi'
            },
            {
                'excel_field': 'hargapenawarantransaksirp',
                'excel_type': 'BIGINTEGER',
                'target_field': 'Harga_Penawaran_Transaksi',
                'target_type': 'DOUBLE',
                'target_alias': 'Harga Penawaran/Transaksi'
            },
            {
                'excel_field': 'luastanahm2',
                'excel_type': 'DOUBLE',
                'target_field': 'Luas_Tanah_m2',
                'target_type': 'DOUBLE',
                'target_alias': 'Luas Tanah (m2)'
            },
            {
                'excel_field': 'lebardepanm',
                'excel_type': 'DOUBLE',
                'target_field': 'Lebar_Depan',
                'target_type': 'DOUBLE',
                'target_alias': 'Lebar Depan'
            },
            {
                'excel_field': 'panjangkebelakangm',
                'excel_type': 'INTEGER',
                'target_field': 'Panjang_Kebelakang',
                'target_type': 'DOUBLE',
                'target_alias': 'Panjang Kebelakang'
            },
            {
                'excel_field': 'bentuktanah',
                'excel_type': 'STRING',
                'target_field': 'Bentuk_Tanah',
                'target_type': 'STRING',
                'target_alias': 'Bentuk Tanah'
            },
            {
                'excel_field': 'elevasidarijalan',
                'excel_type': 'STRING',
                'target_field': 'Elevasi_Dari_Jalan',
                'target_type': 'STRING',
                'target_alias': 'Elevasi Dari Jalan'
            },
            {
                'excel_field': 'letaktanah',
                'excel_type': 'STRING',
                'target_field': 'Letak_Tanah',
                'target_type': 'STRING',
                'target_alias': 'Letak Tanah'
            },
            {
                'excel_field': 'kelasjalan',
                'excel_type': 'STRING',
                'target_field': 'Kelas_Jalan',
                'target_type': 'STRING',
                'target_alias': 'Kelas Jalan'
            },
            {
                'excel_field': 'lebarjalan',
                'excel_type': 'DOUBLE',
                'target_field': 'Lebar_Jalan',
                'target_type': 'DOUBLE',
                'target_alias': 'Lebar Jalan'
            },
            {
                'excel_field': 'aksesibilitas',
                'excel_type': 'STRING',
                'target_field': 'Aksebilitas',
                'target_type': 'STRING',
                'target_alias': 'Aksebilitas'
            },
            {
                'excel_field': 'drainase',
                'excel_type': 'STRING',
                'target_field': 'Drainase',
                'target_type': 'STRING',
                'target_alias': 'Drainase'
            },
            {
                'excel_field': 'utilitas',
                'excel_type': 'STRING',
                'target_field': 'Utilitas',
                'target_type': 'STRING',
                'target_alias': 'Utilitas'
            },
            {
                'excel_field': 'fasilitas',
                'excel_type': 'STRING',
                'target_field': 'Fasilitas',
                'target_type': 'STRING',
                'target_alias': 'Fasilitas'
            },
            {
                'excel_field': 'zoningperuntukan',
                'excel_type': 'STRING',
                'target_field': 'Zoning',
                'target_type': 'INTEGER',
                'target_alias': 'Zoning/Peruntukan'
            },
            {
                'excel_field': 'luasbangunan',
                'excel_type': 'STRING',
                'target_field': 'Luas_Bangunan',
                'target_type': 'DOUBLE',
                'target_alias': 'Luas Bangunan'
            },
            {
                'excel_field': 'jenis',
                'excel_type': 'STRING',
                'target_field': 'Jenis',
                'target_type': 'STRING',
                'target_alias': 'Jenis'
            },
            {
                'excel_field': 'jumlahlantai',
                'excel_type': 'STRING',
                'target_field': 'Jumlah_Lantai',
                'target_type': 'INTEGER',
                'target_alias': 'Jumlah Lantai'
            },
            {
                'excel_field': 'tahunpembuatan',
                'excel_type': 'STRING',
                'target_field': 'Tahun_Pembuatan',
                'target_type': 'INTEGER',
                'target_alias': 'Tahun Pembuatan'
            },
            {
                'excel_field': 'tahunrenovasi',
                'excel_type': 'STRING',
                'target_field': 'Tahun_Renovasi',
                'target_type': 'INTEGER',
                'target_alias': 'Tahun Renovasi'
            },
            {
                'excel_field': 'konstruksiatas',
                'excel_type': 'STRING',
                'target_field': 'Kontruksi_Atas',
                'target_type': 'STRING',
                'target_alias': 'Kontruksi Atas'
            },
            {
                'excel_field': 'konstruksibawah',
                'excel_type': 'STRING',
                'target_field': 'Kontruksi_bawah',
                'target_type': 'STRING',
                'target_alias': 'Kontruksi Bawah'
            },
            {
                'excel_field': 'atap',
                'excel_type': 'STRING',
                'target_field': 'Atap',
                'target_type': 'STRING',
                'target_alias': 'Atap'
            },
            {
                'excel_field': 'dinding',
                'excel_type': 'STRING',
                'target_field': 'Dinding',
                'target_type': 'STRING',
                'target_alias': 'Dinding'
            },
            {
                'excel_field': 'langitlangit',
                'excel_type': 'STRING',
                'target_field': 'LangitLangit',
                'target_type': 'STRING',
                'target_alias': 'Langit Langit'
            },
            {
                'excel_field': 'lantai',
                'excel_type': 'STRING',
                'target_field': 'Lantai',
                'target_type': 'STRING',
                'target_alias': 'Lantai'
            },
            {
                'excel_field': 'pagar',
                'excel_type': 'STRING',
                'target_field': 'Pagar',
                'target_type': 'STRING',
                'target_alias': 'Pagar'
            },
            {
                'excel_field': 'panjangpagar',
                'excel_type': 'STRING',
                'target_field': 'Panjang_Pagar',
                'target_type': 'DOUBLE',
                'target_alias': 'Panjang Pagar'
            },
            {
                'excel_field': 'luascarport',
                'excel_type': 'STRING',
                'target_field': 'Luas_Carport',
                'target_type': 'DOUBLE',
                'target_alias': 'Luas Carport'
            },
            {
                'excel_field': 'pintujendela',
                'excel_type': 'STRING',
                'target_field': 'Pintu_Jendela',
                'target_type': 'STRING',
                'target_alias': 'Pintu/Jendela'
            },
            {
                'excel_field': 'jumlahfasilitas',
                'excel_type': 'STRING',
                'target_field': 'Jumlah_Fasilitas',
                'target_type': 'DOUBLE',
                'target_alias': 'Jumlah Fasilitas'
            },
            # { (sTRING)
            #     'excel_field': 'keadaanfisikumumnya',
            #     'excel_type': 'STRING',
            #     'target_field': 'Keadaan_Fisik',
            #     'target_type': 'DOUBLE',
            #     'target_alias': 'Keadaan Fisik'
            # },
            {
                'excel_field': 'biayaperm2bangunan',
                'excel_type': 'INTEGER',
                'target_field': 'Biaya_Bangunan_m2',
                'target_type': 'DOUBLE',
                'target_alias': 'Biaya Bangunan (m2)'
            },
            { 
                'excel_field': 'rcnbiayapembuatanbangunanbaru',
                'excel_type': 'STRING',
                'target_field': 'RCN',
                'target_type': 'DOUBLE',
                'target_alias': 'RCN'
            },
            {
                'excel_field': 'tahunpenilaian',
                'excel_type': 'INTEGER',
                'target_field': 'Tahun_Penilaian',
                'target_type': 'INTEGER',
                'target_alias': 'Tahun Penilaian'
            },
            {
                'excel_field': 'umurefektif',
                'excel_type': 'INTEGER',
                'target_field': 'Umur_Efektif',
                'target_type': 'DOUBLE',
                'target_alias': 'Umur Efektif'
            },
            {
                'excel_field': 'penyusutan',
                'excel_type': 'DOUBLE',
                'target_field': 'Penyusutan',
                'target_type': 'DOUBLE',
                'target_alias': 'Penyusutan'
            },
            { 
                'excel_field': 'nilaibangunan',
                'excel_type': 'STRING',
                'target_field': 'Nilai_Bangunan',
                'target_type': 'DOUBLE',
                'target_alias': 'Nilai Bangunan'
            },
            {
                'excel_field': 'hargapenyesuaianpenawaran',
                'excel_type': 'DOUBLE',
                'target_field': 'Harga_Penyesuaian',
                'target_type': 'DOUBLE',
                'target_alias': 'Harga Penyesuaian'
            },
            { 
                'excel_field': 'nilaibangunanrp',
                'excel_type': 'STRING',
                'target_field': 'Nilai_Bangunan_Rp',
                'target_type': 'DOUBLE',
                'target_alias': 'Nilai Bangunan (Rp)'
            },
            {
                'excel_field': 'hargatanahrp',
                'excel_type': 'STRING',
                'target_field': 'Harga_Tanah_Rp',
                'target_type': 'STRING',
                'target_alias': 'Harga Tanah (Rp)'
            },
            {
                'excel_field': 'penyesuaianwaktu',
                'excel_type': 'DOUBLE',
                'target_field': 'Penyesuaian_Waktu',
                'target_type': 'DOUBLE',
                'target_alias': 'Penyesuaian Waktu'
            },
            {
                'excel_field': 'penyesuaianstatuskepemilikan',
                'excel_type': 'INTEGER',
                'target_field': 'Penyesuaian_Status_Kepemilikan',
                'target_type': 'DOUBLE',
                'target_alias': 'Penyesuaian Status Kepemilikan'
            },
            {
                'excel_field': 'nilaitanah',
                'excel_type': 'STRING',
                'target_field': 'nilluas',
                'target_type': 'DOUBLE',
                'target_alias': 'Nilai Tanah'
            },
            {
                'excel_field': 'nilaitanahm2',
                'excel_type': 'STRING',
                'target_field': 'nilai',
                'target_type': 'DOUBLE',
                'target_alias': 'Nilai Tanah (m2)'
            },
            {
                'excel_field': 'akses',
                'excel_type': 'STRING',
                'target_field': 'akses',
                'target_type': 'STRING',
                'target_alias': 'Akses'
            },
            {
                'excel_field': 'penyusutanrumah',
                'excel_type': 'DOUBLE',
                'target_field': 'Penyusutan_Rumah',
                'target_type': 'DOUBLE',
                'target_alias': 'Penyusutan Rumah (%)'
            },
            {
                'excel_field': 'penyusutanruko',
                'excel_type': 'DOUBLE',
                'target_field': 'Penyusutan_Ruko',
                'target_type': 'DOUBLE',
                'target_alias': 'Penyusutan Ruko (%)'
            },
            {
                'excel_field': 'keterangan',
                'excel_type': 'STRING',
                'target_field': 'Keterangan',
                'target_type': 'STRING',
                'target_alias': 'Keterangan'
            },
            {
                'excel_field': 'pembanding',
                'excel_type': 'STRING',
                'target_field': 'Pembanding',
                'target_type': 'STRING',
                'target_alias': 'Pembanding'
            },
            {
                'excel_field': 'penyusut1',
                'excel_type': 'DOUBLE',
                'target_field': 'Penyusutan_Rumah_1',
                'target_type': 'DOUBLE',
                'target_alias': 'Penyusutan Rumah 1 (%)'
            },
            {
                'excel_field': 'penyusut2',
                'excel_type': 'DOUBLE',
                'target_field': 'Penyusutan_Ruko_1',
                'target_type': 'DOUBLE',
                'target_alias': 'Penyusutan Ruko 1 (%)'
            },
            {
                'excel_field': 'colbp',
                'excel_type': 'DOUBLE',
                'target_field': 'Penyusutan_Rumah_2',
                'target_type': 'DOUBLE',
                'target_alias': 'Penyusutan Rumah 2 (%)'
            },
            {
                'excel_field': 'colbr',
                'excel_type': 'DOUBLE',
                'target_field': 'Penyusutan_Ruko_2',
                'target_type': 'DOUBLE',
                'target_alias': 'Penyusutan Ruko 2 (%)'
            },
            {
                'excel_field': 'nsementara',
                'excel_type': 'STRING',
                'target_field': 'N_Sementara',
                'target_type': 'STRING',
                'target_alias': 'N Sementara'
            },
            {
                'excel_field': 'responden',
                'excel_type': 'STRING',
                'target_field': 'Responden',
                'target_type': 'STRING',
                'target_alias': 'Responden'
            },
            {
                'excel_field': 'catatan',
                'excel_type': 'STRING',
                'target_field': 'Catatan',
                'target_type': 'STRING',
                'target_alias': 'Catatan'
            },
        ]
        
        for mapping in penyetaraan_header:
            try:
                arcpy.management.AlterField(
                    in_table=output_table,
                    field=mapping['excel_field'],
                    new_field_name=mapping['target_field'],
                    new_field_alias=mapping['target_alias']
                )
            except Exception as e:
                arcpy.AddWarning(f"Gagal mengubah field {mapping['excel_field']} menjadi {mapping['target_field']}: {e}")

        try:
            mapped_targets = [m['target_field'] for m in penyetaraan_header]
            existing_fields = [f.name for f in arcpy.ListFields(output_table)]
            # fields to preserve (common system fields)
            preserve_lower = ['objectid', 'fid', 'shape', 'shape_length', 'shape_area']
            fields_to_delete = [f for f in existing_fields if f.lower() not in [t.lower() for t in mapped_targets] and f.lower() not in preserve_lower]
            if fields_to_delete:
                arcpy.management.DeleteField(output_table, fields_to_delete)
                arcpy.AddMessage(f"Menghapus field tidak ter-mapping: {', '.join(fields_to_delete)}")
        except Exception as e:
            arcpy.AddWarning(f"Gagal menghapus field tidak ter-mapping: {e}")

        # Konversi tipe data: dari STRING -> INTEGER/DOUBLE bila diminta, dengan validasi nilai
        for mapping in penyetaraan_header:
            try:
                excel_type = str(mapping.get('excel_type','')).upper()
                target_type = str(mapping.get('target_type','')).upper()
                target_field = mapping.get('target_field')
                target_alias = mapping.get('target_alias')
                if excel_type == 'STRING' and target_type in ('DOUBLE', 'INTEGER'):
                    field_names = [f.name for f in arcpy.ListFields(output_table)]
                    if target_field not in field_names:
                        # Jika field hasil rename tidak ada (mungkin sudah dihapus), skip
                        arcpy.AddWarning(f"Field {target_field} tidak ditemukan untuk konversi tipe; dilewati.")
                        continue
                    invalid_examples = []
                    with arcpy.da.SearchCursor(output_table, [target_field]) as cursor:
                        for row in cursor:
                            val = row[0]
                            if val is None:
                                continue
                            s = str(val).strip()
                            # Abaikan sel kosong dan kode error Excel (mis. #DIV/0!, #VALUE!, #N/A, dll.)
                            if s == '' or s.startswith('#'):
                                continue
                            # normalize comma decimal separator to dot for parsing
                            s_norm = s.replace(',','.')
                            if target_type == 'INTEGER':
                                # cek apakah dapat diparse sebagai angka utuh
                                try:
                                    num = float(s_norm)
                                    if not num.is_integer():
                                        invalid_examples.append(s)
                                except Exception:
                                    invalid_examples.append(s)
                            else:
                                # DOUBLE: cek apakah dapat diubah ke float
                                try:
                                    float(s_norm)
                                except Exception:
                                    invalid_examples.append(s)
                            if len(invalid_examples) >= 5:
                                break
                    if invalid_examples:
                        arcpy.AddError(f"Field {target_field} tidak dapat diubah menjadi {target_type}. Contoh nilai tidak valid: {invalid_examples}")
                        return
                    # Semua nilai valid: lakukan konversi dengan membuat field sementara, menghitung, lalu mengganti nama
                    tmp_field = f"{target_field}_convtmp"
                    field_type = 'LONG' if target_type == 'INTEGER' else 'DOUBLE'
                    try:
                        if tmp_field in [f.name for f in arcpy.ListFields(output_table)]:
                            arcpy.management.DeleteField(output_table, [tmp_field])
                        arcpy.management.AddField(output_table, tmp_field, field_type)
                        # Use a small code block to avoid CalculateField parsing issues
                        if field_type == 'LONG':
                            expr = f"convert_to_int(!{target_field}!)"
                            code_block = (
                                "def convert_to_int(v):\n"
                                "    if v is None:\n"
                                "        return 0\n"
                                "    s = str(v).strip()\n"
                                "    # Abaikan sel kosong dan error Excel yang diawali '#'\n"
                                "    if s == '' or s.startswith('#'):\n"
                                "        return 0\n"
                                "    s = s.replace(',','.')\n"
                                "    try:\n"
                                "        return int(float(s))\n"
                                "    except Exception:\n"
                                "        return 0\n"
                            )
                        else:
                            expr = f"convert_to_float(!{target_field}!)"
                            code_block = (
                                "def convert_to_float(v):\n"
                                "    if v is None:\n"
                                "        return 0.0\n"
                                "    s = str(v).strip()\n"
                                "    # Abaikan sel kosong dan error Excel yang diawali '#'\n"
                                "    if s == '' or s.startswith('#'):\n"
                                "        return 0.0\n"
                                "    s = s.replace(',','.')\n"
                                "    try:\n"
                                "        return float(s)\n"
                                "    except Exception:\n"
                                "        return 0.0\n"
                            )
                        arcpy.management.CalculateField(output_table, tmp_field, expr, 'PYTHON3', code_block)
                        arcpy.management.DeleteField(output_table, [target_field])
                        arcpy.management.AlterField(output_table, tmp_field, target_field, new_field_alias=target_alias)
                        arcpy.AddMessage(f"Field {target_field} berhasil dikonversi menjadi {target_type}.")
                    except Exception as e:
                        arcpy.AddError(f"Gagal mengkonversi field {target_field} menjadi {target_type}: {e}")
                        return
            except Exception as e:
                arcpy.addWarning(f"Kesalahan saat memproses konversi untuk {mapping.get('target_field')}: {e}")

        check_no_sampel = []
        for row in arcpy.da.SearchCursor(output_table, ['Nomor_Entry']):
            if row[0] not in check_no_sampel:
                check_no_sampel.append(row[0])
            else:
                arcpy.AddError(f'Terdapat Nomor Sampel yang sama: {row[0]}. Silakan periksa kembali data Anda.')
                return

        temp_path = os.path.join(ds_path, "Titik_Sampel_Excel_Point")
        ts_path =  os.path.join(self.dataset_path, "Titik_Sampel")
        ts_table_path = os.path.join(self.gdb_path, "Titik_Sampel")

        try:
            arcpy.management.XYTableToPoint(
            in_table=output_table,
            out_feature_class=temp_path,
            x_field="Y",
            y_field="X",    
            coordinate_system=arcpy.SpatialReference(4326)
        )
        except Exception as e:
            if arcpy.Exists(ts_table_path):
                arcpy.management.Delete(ts_table_path)
            arcpy.AddError(f"Gagal mengkonversi tabel ke titik: {e}")
            return

        arcpy.management.CopyFeatures(temp_path, ts_path)

        # arcpy.management.Delete(temp_gdb)
        aprx = arcpy.mp.ArcGISProject('CURRENT')
        cm = aprx.activeMap
        cm.addDataFromPath(ts_path)

        arcpy.AddMessage("Proses impor titik sampel dari Excel selesai.")

        
        
        return
    




