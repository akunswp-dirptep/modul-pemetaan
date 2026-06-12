from datetime import datetime
import json
import sys
import arcpy, os, math

# Tambahkan parent directory ke sys.path
script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
gp_dir = os.path.dirname(parent_dir)
if gp_dir not in sys.path:
    sys.path.insert(0, gp_dir)

from nbtutils import persil, constant

class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Generate_Konfigurasi_Zonasi,
                      Deklarasi_Zonasi_Update,
                      Seleksi_Zonasi_Terisolasi,
                      Edit_Zonasi_Update]


class Generate_Konfigurasi_Zonasi(object):

    def __init__(self):

        self.label = "Generate Konfigurasi Zonasi"
        self.description = ""
        self.canRunInBackground = False

    # =====================================================
    # PARAMETER
    # =====================================================

    def getParameterInfo(self):

        output_persil = arcpy.Parameter(
            displayName="Output Persil",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [output_persil]

    # =====================================================
    # LICENSE
    # =====================================================

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    # =====================================================
    # UTIL
    # =====================================================

    def delete_if_exists(self, path):

        if arcpy.Exists(path):

            try:
                arcpy.management.Delete(path)

            except:
                pass

    def add_field_if_not_exists(
        self,
        fc,
        field_name,
        field_type
    ):

        fields = [
            f.name
            for f in arcpy.ListFields(fc)
        ]

        if field_name not in fields:

            arcpy.management.AddField(
                fc,
                field_name,
                field_type
            )

    # =====================================================
    # EXECUTE
    # =====================================================

    def execute(self, parameters, messages):

        messages.addMessage(
            "== Proses dimulai =="
        )

        configs = persil.get_config_values()

        dataset_path = configs[
            "project_config"
        ]["dataset_path"]

        ws_path = configs[
            "project_config"
        ]["ws_path"]

        # =====================================================
        # PERSIL
        # =====================================================

        persil_name = "Persil_Layer"

        persil_path = os.path.join(
            dataset_path,
            persil_name
        )

        # =====================================================
        # VALIDASI FIELD
        # =====================================================

        self.add_field_if_not_exists(
            persil_path,
            "min_lb_jln",
            "DOUBLE"
        )

        # =====================================================
        # REFRESH LAYER
        # =====================================================

        self.delete_if_exists(
            persil_name
        )

        arcpy.management.MakeFeatureLayer(
            persil_path,
            persil_name
        )

        # =====================================================
        # HITUNG MINIMUM PER ZONASI
        # =====================================================

        messages.addMessage(
            "== Hitung minimum lebar jalan zonasi =="
        )

        zonasi_dict = {}

        with arcpy.da.SearchCursor(
            persil_name,
            [
                "ZONASI",
                "s_zonasi",
                "LBRJLN"
            ]
        ) as rows:

            for row in rows:

                zonasi = row[0]
                s_zonasi = row[1]
                lb_jalan = row[2]

                if not zonasi:
                    continue

                try:
                    lb_jalan = float(lb_jalan)

                except:
                    lb_jalan = 0

                # =========================================
                # INIT
                # =========================================

                if zonasi not in zonasi_dict:

                    zonasi_dict[zonasi] = {
                        "s_zonasi": int(
                            s_zonasi or 0
                        ),
                        "min_lb_jln": lb_jalan
                    }

                # =========================================
                # UPDATE MINIMUM
                # =========================================

                else:

                    if (
                        lb_jalan <
                        zonasi_dict[
                            zonasi
                        ]["min_lb_jln"]
                    ):

                        zonasi_dict[
                            zonasi
                        ]["min_lb_jln"] = (
                            lb_jalan
                        )

        # =====================================================
        # UPDATE KE PERSIL
        # =====================================================

        messages.addMessage(
            "== Update min_lb_jln ke persil =="
        )

        with arcpy.da.UpdateCursor(
            persil_name,
            [
                "ZONASI",
                "min_lb_jln"
            ]
        ) as rows:

            for row in rows:

                zonasi = row[0]

                if zonasi in zonasi_dict:

                    row[1] = zonasi_dict[
                        zonasi
                    ]["min_lb_jln"]

                    rows.updateRow(row)

        # =====================================================
        # SIMPAN JSON
        # =====================================================

        messages.addMessage(
            "== Generate konfigurasi zonasi =="
        )

        zonasi_config_path = os.path.join(
            ws_path,
            "zonasiupdate.json"
        )

        if os.path.exists(
            zonasi_config_path
        ):

            os.remove(
                zonasi_config_path
            )

        with open(
            zonasi_config_path,
            "w+",
            encoding="utf-8"
        ) as f:

            json.dump(
                zonasi_dict,
                f,
                indent=4,
                ensure_ascii=False
            )

        # =====================================================
        # OUTPUT
        # =====================================================

        parameters[0].value = (
            persil_name
        )

        messages.addMessage(
            f"== Konfigurasi tersimpan: {zonasi_config_path} =="
        )

        messages.addMessage(
            "== Proses selesai =="
        )

        return
    
class Deklarasi_Zonasi_Update(object):

    def __init__(self):

        self.label = "Deklarasi Zonasi Update"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):

        define_zonasi = arcpy.Parameter(
            displayName="Jenis Zonasi",
            name="define_zonasi",
            datatype="GPValueTable",
            parameterType="Required",
            direction="Input"
        )

        define_zonasi.columns = [
            ["GPString", "Jenis Zonasi"],
            ["GPLong", "Skor"],
            ["GPDouble", "Minimum Lebar Jalan"]
        ]

        return [define_zonasi]

    def isLicensed(self):
        return True

    # =====================================================
    # UPDATE PARAMETER
    # =====================================================

    def updateParameters(self,parameters):

        if parameters[0].altered:
            return

        try:

            configs=persil.get_config_values()

            zonasi_config_path=os.path.join(
                configs["project_config"]["ws_path"],
                "zonasiupdate.json"
            )

            if not os.path.exists(zonasi_config_path):
                return

            with open(
                zonasi_config_path,
                "r",
                encoding="utf-8"
            ) as f:

                zonasi_json=json.load(f)

            value_table=[]
            for key,value in zonasi_json.items():
                value_table.append([
                    key,
                    value.get("s_zonasi",0),
                    value.get("min_lb_jln",0)
                ])

            parameters[0].value=value_table

        except:
            pass

        return
    
    def updateMessages(self, parameters):
        return

    def execute(self,parameters,messages):
        
        configs = persil.get_config_values()

        messages.addMessage("== Proses dimulai ==")

        zonasi_values=parameters[0].values

        jumlah_zonasi=len(zonasi_values)

        if jumlah_zonasi<3 or jumlah_zonasi>30:

            messages.addErrorMessage(
                "== Jenis Zonasi tidak boleh "
                "kurang dari 3 dan "
                "tidak boleh lebih dari 30 =="
            )

            raise arcpy.ExecuteError

        zonasi_names=[]
        zonasi_scores=[]

        for row in zonasi_values:

            nama_zonasi=row[0]
            skor_zonasi=row[1]
            min_lb_jln=row[2]

            if (
                nama_zonasi is None
                or skor_zonasi is None
                or min_lb_jln is None
            ):

                messages.addErrorMessage(
                    "== Nilai zonasi, skor, "
                    "dan minimum lebar jalan "
                    "tidak boleh kosong =="
                )

                raise arcpy.ExecuteError

            if nama_zonasi in zonasi_names:

                messages.addErrorMessage(
                    f"== Zonasi '{nama_zonasi}' duplikat =="
                )

                raise arcpy.ExecuteError

            if skor_zonasi in zonasi_scores:

                messages.addErrorMessage(
                    f"== Skor '{skor_zonasi}' duplikat =="
                )

                raise arcpy.ExecuteError

            zonasi_names.append(nama_zonasi)
            zonasi_scores.append(skor_zonasi)

        zonasi_json={}

        for row in zonasi_values:

            nama_zonasi=row[0]

            zonasi_json[nama_zonasi]={
                "s_zonasi":int(row[1]),
                "min_lb_jln":float(row[2])
            }



        zonasi_config_path=os.path.join(
            configs["project_config"]["ws_path"],
            "zonasiupdate.json"
        )

        with open(
            zonasi_config_path,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                zonasi_json,
                f,
                indent=4,
                ensure_ascii=False
            )

        messages.addMessage(
            "== Konfigurasi zonasi berhasil disimpan =="
        )

        messages.addMessage(zonasi_config_path)
        messages.addMessage("== Proses selesai ==")

        return


class Seleksi_Zonasi_Terisolasi(object):

    def __init__(self):
        self.label = "Seleksi Zonasi Terisolasi"
        self.description = "Menyeleksi persil target yang terisolasi pada radius dan zonasi tertentu, dengan opsi batasan wilayah."
        self.canRunInBackground = False

    def getParameterInfo(self):
        pilih_zonasi = arcpy.Parameter(
            displayName="Pilih Zonasi",
            name="pilih_zonasi",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        pilih_zonasi.filter.type = "ValueList"
        pilih_zonasi.filter.list = [
            "Sempadan dan Lindung",
            "Pertanian",
            "Permukiman Sederhana",
            "Permukiman Menengah",
            "Permukiman Mewah",
            "Industri",
            "Perdagangan dan Jasa",
            "Semua Zonasi"
        ]
        pilih_zonasi.value = "Sempadan dan Lindung"

        # Parameter BARU: Pilih Kecamatan/Kelurahan
        pilih_kecamatan = arcpy.Parameter(
            displayName="Batas Wilayah Pencarian Target (WADMKD)",
            name="pilih_kecamatan",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        # List akan diisi secara dinamis melalui updateParameters()
        pilih_kecamatan.value = "Semua Wilayah" 

        max_jarak = arcpy.Parameter(
            displayName="Jarak Maksimal Radius (Meter)",
            name="max_jarak",
            datatype="GPLong",
            parameterType="Required",
            direction="Input"
        )
        max_jarak.value = 100

        min_pembanding = arcpy.Parameter(
            displayName="Jumlah Minimum Zonasi dalam Radius",
            name="min_pembanding",
            datatype="GPLong",
            parameterType="Required",
            direction="Input"
        )
        min_pembanding.value = 3

        # Parameter output untuk menampilkan hasil seleksi di Map
        out_layer = arcpy.Parameter(
            displayName="Layer Hasil Seleksi",
            name="out_layer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        # Pastikan list return disesuaikan urutannya
        return [pilih_zonasi, pilih_kecamatan, max_jarak, min_pembanding, out_layer]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        # Mengisi Dropdown List WADMKD secara dinamis saat tool dibuka
        if not parameters[1].altered or not parameters[1].filter.list:
            try:
                # Mengambil path dataset 
                configs = persil.get_config_values()
                dataset_path = configs["project_config"]["dataset_path"]
                persil_path = os.path.join(dataset_path, "Persil_Layer")

                if arcpy.Exists(persil_path):
                    # Gunakan 'set' untuk mengambil nilai unik dengan lebih cepat
                    unik_wadmkd = set()
                    with arcpy.da.SearchCursor(persil_path, ["WADMKD"]) as cursor:
                        for row in cursor:
                            if row[0]: # Pastikan tidak null/kosong
                                unik_wadmkd.add(row[0])
                    
                    # Ubah ke list, urutkan, dan tambahkan opsi "Semua Wilayah"
                    list_kecamatan = sorted(list(unik_wadmkd))
                    list_kecamatan.insert(0, "Semua Wilayah")
                    
                    parameters[1].filter.list = list_kecamatan
            except Exception:
                pass
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        messages.addMessage("== Proses Seleksi Dimulai ==")

        # Sesuaikan indeks berdasarkan getParameterInfo
        zonasi = parameters[0].valueAsText
        kecamatan = parameters[1].valueAsText
        max_jarak = parameters[2].value
        min_pembanding = parameters[3].value

        # Menentukan list zonasi
        if zonasi == "Semua Zonasi":
            main_zonasi = [1, 2, 3, 4, 5, 6, 7]
        else:
            main_zonasi = [constant.SKORING_ZONASI[zonasi]]

        zonasi_str = ",".join(map(str, main_zonasi))

        # Mengambil path dataset
        configs = persil.get_config_values()
        dataset_path = configs["project_config"]["dataset_path"]
        persil_path = os.path.join(dataset_path, "Persil_Layer")

        target_layer = "target_layer_temp"
        kandidat_layer = "kandidat_layer_temp"
        near_table = "memory\\bulk_near_table_seleksi" 

        # Bersihkan memori jika ada sisa proses sebelumnya
        arcpy.management.Delete(target_layer) if arcpy.Exists(target_layer) else None
        arcpy.management.Delete(kandidat_layer) if arcpy.Exists(kandidat_layer) else None
        arcpy.management.Delete(near_table) if arcpy.Exists(near_table) else None

        # 1. Kumpulkan OBJECTID Target (Dengan Filter WADMKD jika dipilih)
        target_where = f"S_ZONASI IN ({zonasi_str})"
        if kecamatan and kecamatan != "Semua Wilayah":
            # Tambahkan filter batas pencarian target
            target_where += f" AND WADMKD = '{kecamatan}'"

        target_oids = []
        with arcpy.da.SearchCursor(persil_path, ["OBJECTID"], target_where) as cursor:
            for row in cursor:
                target_oids.append(row[0])

        if not target_oids:
            messages.addWarningMessage(f"Tidak ada persil target pada zonasi '{zonasi}' di wilayah '{kecamatan}'.")
            return

        messages.addMessage(f"Ditemukan {len(target_oids)} persil target di area pencarian. Melakukan pencarian pembanding dari seluruh bidang...")

        # 2. Buat Feature Layer untuk Near Table
        # PERHATIKAN: Kandidat tetap mengambil dari semua wilayah (tanpa filter WADMKD)
        kandidat_where = f"S_ZONASI IN ({zonasi_str}) AND perubahan IS NULL"
        
        arcpy.management.MakeFeatureLayer(persil_path, target_layer, target_where)
        arcpy.management.MakeFeatureLayer(persil_path, kandidat_layer, kandidat_where)

        # 3. Eksekusi Near Table
        arcpy.analysis.GenerateNearTable(
            in_features=target_layer,
            near_features=kandidat_layer,
            out_table=near_table,
            search_radius=f"{max_jarak} Meters",
            location="NO_LOCATION",
            angle="NO_ANGLE",
            closest="ALL"
        )

        # 4. Hitung jumlah pembanding yang ditemukan untuk masing-masing target
        kandidat_count = {oid: 0 for oid in target_oids} # Inisiasi semua target dengan 0
        
        with arcpy.da.SearchCursor(near_table, ["IN_FID"]) as rows:
            for row in rows:
                in_fid = row[0]
                if in_fid in kandidat_count:
                    kandidat_count[in_fid] += 1

        # 5. Identifikasi persil yang kurang dari min_pembanding
        persil_bermasalah = []
        for oid, count in kandidat_count.items():
            if count < min_pembanding:
                persil_bermasalah.append(str(oid))

        # Bersihkan Workspace Memory
        arcpy.management.Delete(target_layer)
        arcpy.management.Delete(kandidat_layer)
        arcpy.management.Delete(near_table)

        # 6. Lakukan Seleksi pada Layer Asli
        if persil_bermasalah:
            jml_masalah = len(persil_bermasalah)
            messages.addMessage(f"Ditemukan {jml_masalah} persil terisolasi yang tidak memiliki minimal {min_pembanding} persil pembanding di sekitarnya.")
            
            # Membuat Feature Layer baru
            layer_name = "Persil_Terisolasi"
            query_seleksi = f"OBJECTID IN ({','.join(persil_bermasalah)})"
            
            arcpy.management.MakeFeatureLayer(persil_path, layer_name, query_seleksi)
            
            # Mengatur output parameter (Indeks disesuaikan ke 4)
            parameters[4].value = layer_name
            messages.addMessage(f"== Layer '{layer_name}' berhasil dibuat dan diseleksi ==")
        else:
            messages.addMessage(f"Semua persil target di '{kecamatan}' memenuhi syarat minimal {min_pembanding} pembanding.")

        return
    
class Edit_Zonasi_Update(object):

    def __init__(self):

        self.label = "Edit Informasi Zonasi Pada Persil"
        self.description = ""
        self.canRunInBackground = False


    def getParameterInfo(self):

        pilih_zona = arcpy.Parameter(
            displayName="Pilih Zonasi",
            name="pilih_zona",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )

        simpan_sebagai_perubahan = arcpy.Parameter(
            displayName= "Simpan Sebagai Perubahan",
            name="simpan_sebagai_perubahan",
            datatype="GPBoolean",
            parameterType="Required",
            direction="Input"
        )
        simpan_sebagai_perubahan.value = True

        output_data = arcpy.Parameter(
            name="persil_layer",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )



        return [pilih_zona, simpan_sebagai_perubahan, output_data]

    def isLicensed(self):
        return True

    # =====================================================
    # UPDATE PARAMETER
    # =====================================================

    def updateParameters(self, parameters):
        if parameters[0].altered:
            return

        try:
            configs = persil.get_config_values()
            zonasi_config_path=os.path.join(
                        configs["project_config"]["ws_path"],
                        "zonasiupdate.json"
                    )
            if not os.path.exists(
                zonasi_config_path
            ):

                return

            with open(
                zonasi_config_path,
                "r",
                encoding="utf-8"
            ) as f:

                zonasi_json = json.load(
                    f
                )
            
            parameters[0].filter.type = "ValueList"
            parameters[0].filter.list = list(
                zonasi_json.keys()
            )

        except:

            pass

        return

    def updateMessages(self, parameters):
        return


    def add_field_if_not_exists(
        self,
        feature_class,
        field_name,
        field_type
    ):

        field_names = [
            field.name
            for field in arcpy.ListFields(
                feature_class
            )
        ]

        if field_name not in field_names:

            arcpy.management.AddField(
                feature_class,
                field_name,
                field_type
            )

    def execute(self,parameters,messages):


        messages.addMessage("== Proses dimulai ==")

        zonasi=parameters[0].valueAsText
        simpan_sebagai_data_baru = parameters[1].value

        configs=persil.get_config_values()

        zonasi_config_path=os.path.join(
            configs["project_config"]["ws_path"],
            "zonasiupdate.json"
        )

        if not os.path.exists(zonasi_config_path):

            messages.addErrorMessage(
                "== File konfigurasi zonasi tidak ditemukan =="
            )

            raise arcpy.ExecuteError

        with open(
            zonasi_config_path,
            "r",
            encoding="utf-8"
        ) as f:

            zonasi_json=json.load(f)

        if zonasi not in zonasi_json:

            messages.addErrorMessage(
                f"== Zonasi '{zonasi}' tidak ditemukan =="
            )

            raise arcpy.ExecuteError

        s_zonasi=zonasi_json[zonasi].get("s_zonasi",  0)

        min_lb_jln=zonasi_json[zonasi].get(
            "min_lb_jln",
            1.5
        )

        dataset_path=configs["project_config"]["dataset_path"]

        persil_edit="Persil_Layer"

        persil_edit_path=os.path.join(
            dataset_path,
            persil_edit
        )

        self.add_field_if_not_exists(
            persil_edit_path,
            "min_lb_jln",
            "DOUBLE"
        )

        required_fields=[
            "ZONASI",
            "S_ZONASI",
            "min_lb_jln",
            "status_per"
        ]

        persil_fields=[f.name for f in arcpy.ListFields(persil_edit_path) ]

        missing_fields=[]

        for field_name in required_fields:
            if field_name not in persil_fields:
                missing_fields.append(field_name)

        if len(missing_fields)>0:

            messages.addErrorMessage(
                "== Field berikut tidak ditemukan: {} ==".format(
                    ", ".join(missing_fields)
                )
            )

            raise arcpy.ExecuteError

        ada_seleksi=len(
            arcpy.Describe(persil_edit).FIDSet
        )

        if ada_seleksi==0:

            messages.addWarningMessage(
                "== Tidak ada persil yang dipilih =="
            )

            return

        messages.addMessage(
            "== Update informasi zonasi =="
        )


        with arcpy.da.UpdateCursor(
            persil_edit,
            [
                "ZONASI",
                "S_ZONASI",
                "min_lb_jln",
                "status_per"
            ]
        ) as rows:

            for row in rows:
                row[0]=zonasi
                row[1]=s_zonasi
                row[2]=min_lb_jln

                if simpan_sebagai_data_baru:
                    row[3]="update"
                
                rows.updateRow(row)

        messages.addMessage("== Proses selesai ==")
        simbology_path = r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Simbologi_Zonasi_Persil_Layer.lyrx"

        arcpy.management.MakeFeatureLayer(persil_edit_path, "Persil_Layer")
        arcpy.management.ApplySymbologyFromLayer("Persil_Layer", simbology_path)

        arcpy.SetParameter(2, "Persil_Layer")
        return