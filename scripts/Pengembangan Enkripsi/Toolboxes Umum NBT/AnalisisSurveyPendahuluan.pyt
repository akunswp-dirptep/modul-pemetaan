from datetime import datetime
import json
import sys
import arcpy, os, requests, zipfile, csv

# Tambahkan parent directory ke sys.path
script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from nbtutils import constant, persil
from zntutils.document import validate_document_type, get_credentials
from zntutils.system_utils import get_user_data, clear_user_data, get_all_berkas_id, setup_user_data
from zntutils.constant import PREFERRED_BERKAS_ID, CREDENTIAL_KEY, PREFERRED_SERVER_KEY, AUTH_KEY, NAMA_PROVINSI, KAB_KOTA
from zntutils.upload_utils import upload_feature_layer_to_sipenta


class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Ambil_Survey_Pendahuluan_Dari_Sipenta,
                      Tampilkan_Dataset_Survey,
                      Tampilkan_Fasilitas,
                      Setujui_Sampel_Fasilitas,
                      Hitung_Jarak_Fasilitas]


class Ambil_Survey_Pendahuluan_Dari_Sipenta(object):

    def __init__(self):
        self.label = "Ambil Survey Pendahuluan"
        self.description = "Tampilkan Survey Pendahuluan dari SIPENTA"
        self.canRunInBackground = False

    def getParameterInfo(self):
        # 1. Penyederhanaan pengolahan list dengan List Comprehension
        berkas_list = get_all_berkas_id()
        if berkas_list:
            berkas_show = [str(berkas[0]) for berkas in berkas_list]
        else:
            berkas_show = ['Tidak ada berkas yang dapat dipilih']

        berkas = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="berkas",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        berkas.filter.type = "ValueList"
        berkas.filter.list = berkas_show

        if berkas_list:
            preferred_berkas = get_user_data(PREFERRED_BERKAS_ID)
            berkas.value = preferred_berkas if preferred_berkas else berkas_show[0]
        else:
            berkas.value = 'Tidak ada berkas yang dapat dipilih'

        output_fasilitas = arcpy.Parameter(
            name="Survey_Fasilitas",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        output_jalan = arcpy.Parameter(
            name="Survey_Jalan",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        output_zona = arcpy.Parameter(
            name="Survey_Zonasi",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        output_resiko = arcpy.Parameter(
            name="Survey_Resiko",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )
        
        penjelasan = arcpy.Parameter(
            displayName="Informasi Tools",
            name="petunjuk",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )
        
        penjelasan.value = (
            "Login terlebih dahulu untuk mengakses fitur ini.\n\n"
            "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
            "Kementerian ATR/BPN.\n"
            f"Tahun: {datetime.now().year}\n"
        )
        
        return [berkas, output_fasilitas, output_jalan, output_zona, output_resiko, penjelasan]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        berkas = parameters[0]
        penjelasan = parameters[5]

        is_login = get_user_data(CREDENTIAL_KEY)

        if is_login is None:
            berkas.enabled = False
            penjelasan.enabled = True
        else:
            berkas.enabled = True
            penjelasan.enabled = False
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        user_data = get_user_data(CREDENTIAL_KEY)

        if user_data is None:
            messages.addErrorMessage("Silakan login terlebih dahulu.")
            raise arcpy.ExecuteError

        token = user_data.get(AUTH_KEY, None)
        nomor_berkas = parameters[0].valueAsText
        server = get_user_data(PREFERRED_SERVER_KEY)
        
        # 2. Penyederhanaan logika pengecekan server
        use_production = server in ("Produksi", None)

        configs = persil.get_config_values()
        dataset_path = configs['project_config']["dataset_path"]

        api_data = self.call_lbt_api(
            token=token,
            nomor_berkas=nomor_berkas,
            use_production=use_production
        )

        if not api_data.get("success"):
            messages.addErrorMessage("API mengembalikan status gagal.")
            raise arcpy.ExecuteError

        data = api_data.get("data", {})

        layers_mapping = {
            "fasilitas": ["Survey_Fasilitas", r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Survey_Fasilitas.lyrx"],
            "jalan": ["Survey_Jalan", r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Survey_Jalan.lyrx"],
            "zona": ["Survey_Zonasi", r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Survey_Zonasi.lyrx"],
            "resiko": ["Survey_Risiko", r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Survey_Risiko.lyrx"]
        }

        parameter_index = {
            "Survey_Fasilitas": 1,
            "Survey_Jalan": 2,
            "Survey_Zonasi": 3,
            "Survey_Risiko": 4
        }

        for api_key, fc_data in layers_mapping.items():
            fc_name = fc_data[0]
            fc_symbol = fc_data[1]
            geojson = data.get(api_key)

            if not geojson:
                messages.addWarningMessage(f"{fc_name} tidak ditemukan.")
                continue

            features = geojson.get("features", [])
            if not features:
                messages.addWarningMessage(f"{fc_name} kosong.")
                continue

            json_path = os.path.join(configs['project_config']["ws_path"], f"{fc_name}.json")

            try:
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(geojson, f, ensure_ascii=False)

                output_fc = os.path.join(dataset_path, fc_name)

                if arcpy.Exists(output_fc):
                    arcpy.management.Delete(output_fc)

                messages.addMessage(f"Membuat {fc_name}...")
                arcpy.conversion.JSONToFeatures(json_path, output_fc)

                arcpy.management.MakeFeatureLayer(output_fc, fc_name)
                arcpy.management.ApplySymbologyFromLayer(fc_name, fc_symbol)
                
                # Update output parameter
                arcpy.SetParameter(parameter_index[fc_name], fc_name)

            except Exception as e:
                messages.addErrorMessage(f"Gagal memproses {fc_name}: {str(e)}")
            finally:
                # 3. Memastikan temporary file selalu dihapus meskipun terjadi error
                if os.path.exists(json_path):
                    try:
                        arcpy.management.Delete(json_path)
                    except Exception:
                        pass

        messages.addMessage("\n== Proses selesai ==")
        return

    def call_lbt_api(self, token, nomor_berkas, use_production=True):
        test_url = "https://belajar.atrbpn.go.id/sipenta/tatausaha-2/api/pemetaan/data-lbt/"
        prod_url = "https://sipenta.atrbpn.go.id/tatausaha/api/pemetaan/data-lbt"

        url = prod_url if use_production else test_url

        try:
            arcpy.AddMessage("Mengambil data Survey...")
            
            # 4. Memperbaiki Bug User-Agent yang sebelumnya tidak ada di konfigurasi header
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
                        
            payload = {
                "no_berkas": nomor_berkas
            }
            
            response = requests.get(
                url, 
                headers=headers, 
                params=payload, 
                timeout=60,
                verify=True
            )
            
            response.raise_for_status()
            data = response.json()
            
            if not data:
                arcpy.AddError("Server tidak mengirim data.")
                
            return data

        except requests.exceptions.HTTPError as e:
            response = e.response
            try:
                error_json = response.json()
                message = error_json.get("message", "")
            except Exception:
                message = ""

            if response.status_code == 403 and "expired" in message.lower():
                clear_user_data()
                raise Exception("Token kadaluarsa. Silakan login ulang.")
            elif response.status_code == 403:
                raise Exception("Akses ditolak (403). Pastikan Anda memiliki akses yang valid.")
            else:
                raise Exception(f"HTTP Error: {e}")

        except requests.exceptions.RequestException as e:
            arcpy.AddError(f"Error API: {str(e)}")
            raise arcpy.ExecuteError

class Tampilkan_Dataset_Survey(object):
    def __init__(self):
        self.label = "Tampilkan Dataset Survey"
        self.description = "Memanggil Feature Class Survey dari dataset path dan menerapkan simbologi."
        self.canRunInBackground = False
        
        # Mapping nama layer dengan path simbologinya
        self.layers_mapping = {
            "Survey_Fasilitas": r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Survey_Fasilitas.lyrx",
            "Survey_Jalan": r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Survey_Jalan.lyrx",
            "Survey_Zonasi": r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Survey_Zonasi.lyrx",
            "Survey_Risiko": r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Survey_Risiko.lyrx"
        }

    def getParameterInfo(self):
        p_layers = arcpy.Parameter(
            displayName="Pilih Layer Survey",
            name="pilih_layer",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
            multiValue=True
        )
        
        daftar_layer = list(self.layers_mapping.keys())
        p_layers.filter.type = "ValueList"
        p_layers.filter.list = daftar_layer
        p_layers.value = daftar_layer


        p_out_layers = arcpy.Parameter(
            displayName="Output Layers",
            name="out_layers",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output",
            multiValue=True
        )

        return [p_layers, p_out_layers]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        selected_layers = parameters[0].valueAsText.split(";")
        
        selected_layers = [lyr.strip("'").strip() for lyr in selected_layers]
        try:
            configs = persil.get_config_values()
            dataset_path = configs['project_config']["dataset_path"]
        except Exception as e:
            messages.addErrorMessage("Gagal membaca konfigurasi persil. Pastikan project_config valid.")
            raise arcpy.ExecuteError

        output_layer_names = []

        for layer_name in selected_layers:
            fc_path = os.path.join(dataset_path, layer_name)
            symbology_path = self.layers_mapping.get(layer_name)
            if arcpy.Exists(fc_path):
                try:
                    messages.addMessage(f"Memproses {layer_name}...")
                    arcpy.management.MakeFeatureLayer(fc_path, layer_name)
                    

                    if os.path.exists(symbology_path):
                        arcpy.management.ApplySymbologyFromLayer(layer_name, symbology_path)
                    else:
                        messages.addWarningMessage(f"File simbologi untuk {layer_name} tidak ditemukan di path yang ditentukan.")

                    output_layer_names.append(layer_name)
                
                except Exception as e:
                    messages.addWarningMessage(f"Gagal memuat layer {layer_name}: {str(e)}")
            else:
                messages.addWarningMessage(f"Feature Class '{layer_name}' tidak ditemukan di: {fc_path}")
        if output_layer_names:
            parameters[1].value = output_layer_names
            messages.addMessage(f"\nBerhasil memuat {len(output_layer_names)} layer.")
        else:
            messages.addWarningMessage("Tidak ada layer yang berhasil dimuat.")

        return

class Tampilkan_Fasilitas(object):
    def __init__(self):
        self.label = "Tampilkan Fasilitas ke Map"
        self.description = "Menampilkan layer fasilitas dari Geodatabase ke dalam Map aktif beserta simbologi standarnya."
        self.canRunInBackground = False

    def getParameterInfo(self):
        pilih_fasilitas = arcpy.Parameter(
            displayName="Pilih Fasilitas yang Ingin Ditampilkan",
            name="pilih_fasilitas",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
            multiValue=True
        )

        p_out_layers = arcpy.Parameter(
            displayName="Output Layers",
            name="out_layers",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output",
            multiValue=True
        )
        return [pilih_fasilitas, p_out_layers]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        pilih_fasilitas = parameters[0]
        
        # Mengambil daftar fasilitas dari konfigurasi untuk mengisi dropdown pilihan
        if not pilih_fasilitas.hasBeenValidated:
            try:
                configs = persil.get_config_values()
                ds_path = configs["project_config"]['gdb_path']
                fasilitas_workspace = os.path.join(ds_path, 'fasilitas_ds') 
                
                if arcpy.Exists(fasilitas_workspace):
                    arcpy.env.workspace = fasilitas_workspace
                    fc_list = arcpy.ListFeatureClasses(feature_type="Point")
                    
                    if fc_list:
                        pilih_fasilitas.filter.list = fc_list
                    else:
                        pilih_fasilitas.filter.list = ["Tidak ada fasilitas ditemukan"]
                else:
                    pilih_fasilitas.filter.list = ["Dataset fasilitas tidak ditemukan"]
            except Exception as e:
                pilih_fasilitas.filter.list = ["Gagal memuat dataset"]
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        arcpy.AddMessage("== Memulai proses menampilkan fasilitas ==")
        
        fasilitas_terpilih = parameters[0].valueAsText.split(';')
        fasilitas_terpilih = [f.strip("'") for f in fasilitas_terpilih]
        try:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            active_map = aprx.activeMap
            if active_map is None:
                arcpy.AddError("Tidak ada Map yang terbuka/aktif. Silakan buka Map terlebih dahulu.")
                return
        except Exception:
            arcpy.AddError("Tool ini hanya dapat dijalankan di dalam antarmuka ArcGIS Pro dengan Map yang terbuka.")
            return

        configs = persil.get_config_values()
        ds_path = configs["project_config"]['gdb_path']
        fasilitas_workspace = os.path.join(ds_path, 'fasilitas_ds')
        symbology_mapping = {
            'CBD': r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Fasilitas_CBD.lyrx",
            'KES': r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Fasilitas_KES.lyrx",
            'PDDKN': r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Fasilitas_PDDKN.lyrx",
            'PMRNTH': r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Fasilitas_PMRNTH.lyrx",
            'TRANSP': r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Fasilitas_TRANSP.lyrx",
        }
        default_symbology = r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Fasilitas_LAINNYA.lyrx"
        
        output_layer_names = []
        for nama_fasilitas in fasilitas_terpilih:
            fc_path = os.path.join(fasilitas_workspace, nama_fasilitas)
            nama_layer = f"Fasilitas_{nama_fasilitas}"
            
            if not arcpy.Exists(fc_path):
                messages.AddWarningMessage(f"Data {nama_fasilitas} tidak ditemukan di Geodatabase.")
                continue

            arcpy.AddMessage(f"Menambahkan {nama_fasilitas} ke map...")

            arcpy.management.MakeFeatureLayer(fc_path, nama_layer)
            simbology_file = symbology_mapping.get(nama_fasilitas.upper(), default_symbology)

            if os.path.exists(simbology_file):
                try:

                    arcpy.management.ApplySymbologyFromLayer(
                        nama_layer, simbology_file
                    )
                    arcpy.AddMessage(f"  -> Simbologi diterapkan untuk {nama_layer}")
                except Exception as e:
                    messages.AddWarningMessage(f"  -> Gagal menerapkan simbologi untuk {nama_layer}: {str(e)}")
            else:
                messages.AddWarningMessage(f"  -> File simbologi tidak ditemukan: {simbology_file}")
            output_layer_names.append(nama_layer)

        if output_layer_names:
            parameters[1].value = output_layer_names
            messages.addMessage(f"\nBerhasil memuat {len(output_layer_names)} layer.")
        else:
            messages.addWarningMessage("Tidak ada layer yang berhasil dimuat.")

        arcpy.AddMessage("== Proses selesai ==")
        return
    


class Setujui_Sampel_Fasilitas(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Setujui Sampel Fasilitas"
        self.description = "Memasukkan data titik dari Survey_Fasilitas ke layer fasilitas yang dipilih atau membuat fasilitas baru, memindahkan atribut nama_fasilitas ke Keterangan, lalu menghapus titik dari survey."

    def getParameterInfo(self):
        """Define the tool parameters."""
        
        mode_input = arcpy.Parameter(
            displayName="Mode Pemasukan Fasilitas",
            name="mode_input",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        mode_input.filter.type = "ValueList"
        mode_input.filter.list = ["Pilih Fasilitas Existing", "Buat Fasilitas Baru"]
        mode_input.value = "Pilih Fasilitas Existing"

        target_fasilitas = arcpy.Parameter(
            displayName="Pilih Layer Fasilitas Tujuan",
            name="target_fasilitas",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )
        target_fasilitas.filter.type = "ValueList"
        
        nama_fasilitas_baru = arcpy.Parameter(
            displayName="Nama Fasilitas Baru (Maks 8 Huruf)",
            name="nama_fasilitas_baru",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )

        p_out_layers = arcpy.Parameter(
            displayName="Output Layers",
            name="out_layers",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output",
            multiValue=True
        )

        return [mode_input, target_fasilitas, nama_fasilitas_baru, p_out_layers]

    def isLicensed(self):
        """Set whether the tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal validation."""
        mode_input = parameters[0].valueAsText
        target_fasilitas = parameters[1]
        nama_fasilitas_baru = parameters[2]
        
        # 1. Atur Enable/Disable Parameter Berdasarkan Mode
        if mode_input == "Pilih Fasilitas Existing":
            target_fasilitas.enabled = True
            nama_fasilitas_baru.enabled = False
        elif mode_input == "Buat Fasilitas Baru":
            target_fasilitas.enabled = False
            nama_fasilitas_baru.enabled = True

        # 2. Update List untuk Fasilitas Existing
        try:
            configs = persil.get_config_values()
            ds_path = configs["project_config"]['gdb_path']
            fasilitas_workspace = os.path.join(ds_path, 'fasilitas_ds')
            
            if arcpy.Exists(fasilitas_workspace):
                arcpy.env.workspace = fasilitas_workspace
                fc_list = arcpy.ListFeatureClasses(feature_type="Point")
                
                if fc_list:
                    target_fasilitas.filter.list = fc_list
                else:
                    target_fasilitas.filter.list = ["Tidak ada layer Fasilitas ditemukan"]
            else:
                target_fasilitas.filter.list = ["Workspace fasilitas tidak ditemukan"]
                
        except Exception as e:
            target_fasilitas.filter.list = ["Gagal memuat daftar layer Fasilitas"]
            
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation."""
        mode_input = parameters[0].valueAsText
        
        if mode_input == "Buat Fasilitas Baru":
            nama_baru = parameters[2].valueAsText
            if nama_baru:
                # Validasi jumlah karakter maksimal 8 huruf dan tidak ada spasi
                if len(nama_baru) > 8:
                    parameters[2].setErrorMessage("Nama fasilitas maksimal 8 huruf.")
                if " " in nama_baru:
                    parameters[2].setErrorMessage("Nama fasilitas tidak boleh mengandung spasi.")
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        input_lbt = 'Survey_Fasilitas'
        
        mode_input = parameters[0].valueAsText
        target_fasilitas_exist = parameters[1].valueAsText
        nama_fasilitas_baru = parameters[2].valueAsText

        reload_symbology = []
        # 1. Validasi eksistensi layer input di map
        if not arcpy.Exists(input_lbt):
            arcpy.AddError(f"Layer input '{input_lbt}' tidak ditemukan pada map saat ini.")
            return

        # 2. Validasi apakah ada titik yang di-select
        desc = arcpy.Describe(input_lbt)
        if hasattr(desc, "FIDSet") and not desc.FIDSet:
            arcpy.AddError(f"Tidak ada titik yang di-select pada layer '{input_lbt}'. Silakan select titik terlebih dahulu.")
            return

        # 3. Muat Konfigurasi
        try:
            configs = persil.get_config_values()
            ds_path = configs["project_config"]['gdb_path']
            fasilitas_dataset = os.path.join(ds_path, 'fasilitas_ds')
            persil_path = os.path.join(configs["project_config"]["dataset_path"], "Persil_Layer")
            dataset_survey_fasilitas = os.path.join(configs["project_config"]["dataset_path"], "Survey_Fasilitas")
            reload_symbology.append((input_lbt, dataset_survey_fasilitas))
        except Exception as e:
            arcpy.AddError(f"Gagal memuat konfigurasi path: {str(e)}")
            return

        # 4. Tentukan Target Name & Handle Buat Fasilitas Baru
        if mode_input == "Buat Fasilitas Baru":
            if not nama_fasilitas_baru:
                arcpy.AddError("Nama fasilitas baru harus diisi.")
                return
                
            target_name = nama_fasilitas_baru.upper()
            target_path = os.path.join(fasilitas_dataset, target_name)
            reload_symbology.append((f'Fasilitas_{target_name}', target_path))
            
            # Buat Feature Class Baru jika belum ada
            if not arcpy.Exists(target_path):
                arcpy.AddMessage(f"Membuat Layer Fasilitas Baru: {target_name}")
                sr = arcpy.Describe(input_lbt).spatialReference
                arcpy.management.CreateFeatureclass(fasilitas_dataset, target_name, "POINT", spatial_reference=sr)
                
                # Menambahkan field di Persil_Layer & mendaftarkan di config
                field_fasilitas = f"JK{target_name}"
                existing_fields = [f.name.upper() for f in arcpy.ListFields(persil_path)]
                
                if field_fasilitas.upper() not in existing_fields:
                    arcpy.AddMessage(f"Menambahkan field {field_fasilitas} ke Persil_Layer...")
                    arcpy.management.AddField(persil_path, field_fasilitas, "DOUBLE")
                
                # Update Config mapping
                if "fasilitas_config" in configs:
                    mapping = configs["fasilitas_config"].get("mapping_fasilitas", {})
                    mapping[field_fasilitas] = {
                        "nama_fasilitas": target_name,
                        "file_path": target_path
                    }
                    configs["fasilitas_config"]["mapping_fasilitas"] = mapping
                    try:
                        persil.set_config_values(configs)
                    except Exception as e:
                        arcpy.AddWarningMessage(f"Gagal menyimpan config fasilitas baru: {str(e)}")

        else:
            target_name = target_fasilitas_exist
            target_path = os.path.join(fasilitas_dataset, target_name)
            reload_symbology.append((f'Fasilitas_{target_name}', target_path))

        # Validasi akhir path target
        if not arcpy.Exists(target_path):
            arcpy.AddError(f"Layer tujuan '{target_name}' tidak ditemukan di path: {target_path}")
            return

        # --- FITUR BARU: Pastikan layer target memiliki field 'Keterangan' (Poin 3) ---
        target_fields = [f.name.lower() for f in arcpy.ListFields(target_path)]
        if "keterangan" not in target_fields:
            arcpy.AddMessage(f"Menambahkan field 'Keterangan' pada layer {target_name}...")
            arcpy.management.AddField(target_path, "Keterangan", "TEXT", field_length=255)

        # 5. Eksekusi Pemindahan Geometri & Atribut, serta Penghapusan Titik Input
        jumlah_titik = 0
        try:
            in_fields = ["SHAPE@", "nama_fasilitas"]
            out_fields = ["SHAPE@", "Keterangan"]
            
            data_to_move = []
            
            # Langkah 5a: Baca dan simpan data terpilih ke memori menggunakan SearchCursor
            with arcpy.da.SearchCursor(input_lbt, in_fields) as search_cursor:
                for row in search_cursor:
                    geometry = row[0]
                    nama_fas = row[1]
                    if geometry is not None:
                        data_to_move.append((geometry, nama_fas))

            # Langkah 5b: Eksekusi pemindahan dan penghapusan jika ada data
            if data_to_move:
                # Insert data ke layer target
                with arcpy.da.InsertCursor(target_path, out_fields) as insert_cursor:
                    for geom, n_fas in data_to_move:
                        insert_cursor.insertRow([geom, n_fas])
                        jumlah_titik += 1
                
                # Menghapus titik yang telah dipindah dari layer input
                # Karena input_lbt (Survey_Fasilitas) sedang memiliki selection,
                # DeleteFeatures HANYA akan menghapus fitur yang terseleksi.
                arcpy.management.DeleteFeatures(input_lbt)

            arcpy.AddMessage(f"Berhasil memindahkan {jumlah_titik} titik terpilih ke layer {target_name} dan menghapusnya dari {input_lbt}.")
            
        except Exception as e:
            arcpy.AddError(f"Terjadi kesalahan saat mendistribusikan titik: {str(e)}")
            return # Hentikan eksekusi jika gagal agar tidak memicu error lanjutan di tahap symbology
            
        # 6. Menangani Reload Symbology
        layers_reload_symbology = []        
        for data in reload_symbology:
            layer_name = data[0]
            path_file = data[1]
            arcpy.AddMessage(path_file)
            
            if layer_name == "Survey_Fasilitas":
                sym_file = r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Survey_Fasilitas.lyrx"
            else:
                file_name = os.path.basename(path_file) 
                
                symbology_mapping = {
                    'CBD': r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Fasilitas_CBD.lyrx",
                    'KES': r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Fasilitas_KES.lyrx",
                    'PDDKN': r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Fasilitas_PDDKN.lyrx",
                    'PMRNTH': r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Fasilitas_PMRNTH.lyrx",
                    'TRANSP': r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Fasilitas_TRANSP.lyrx",
                }
                default_symbology = r"C:\PenilaianTanah\ui\symbology\Nilai Bidang Tanah\Fasilitas_LAINNYA.lyrx"
                sym_file = symbology_mapping.get(file_name, default_symbology)
            
                arcpy.AddMessage(f"Menambahkan {file_name} ke map...")

            arcpy.management.MakeFeatureLayer(path_file, layer_name)
            
            if os.path.exists(sym_file):
                try:
                    arcpy.management.ApplySymbologyFromLayer(layer_name, sym_file)
                    arcpy.AddMessage(f"  -> Simbologi diterapkan untuk {layer_name}")
                except Exception as e:
                    messages.addWarningMessage(f"  -> Gagal menerapkan simbologi untuk {layer_name}: {str(e)}")
            else:
                messages.addWarningMessage(f"  -> File simbologi tidak ditemukan: {sym_file}")
                
            layers_reload_symbology.append(layer_name)

        if layers_reload_symbology:
            parameters[3].value = layers_reload_symbology
            messages.addMessage(f"\nBerhasil memuat {len(layers_reload_symbology)} layer.")
        else:
            messages.addWarningMessage("Tidak ada layer yang berhasil dimuat.")
            
        return
       
class Hitung_Jarak_Fasilitas(object):

    def __init__(self):
        self.label = "Hitung Jarak Fasilitas"
        self.description = "Menghitung jarak terdekat dari persil ke berbagai fasilitas menggunakan Network Analyst."
        self.canRunInBackground = False

    def getParameterInfo(self):
        simpan_temp = arcpy.Parameter(
            displayName="Simpan ke Layer Sementara",
            name="simpan_temp",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        simpan_temp.value = False

        hanya_update = arcpy.Parameter(
            displayName="Hanya Persil Perubahan",
            name="hanya_update",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        hanya_update.value = True
        
        hanya_null_nol = arcpy.Parameter(
            displayName="Hanya Nilai Jarak Fasilitas Masih Null/Kosong",
            name="hanya_null_nol",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input"
        )
        hanya_null_nol.value = False

        output_persil = arcpy.Parameter(
            displayName="Output Persil",
            name="output_persil",
            datatype="GPFeatureLayer",
            parameterType="Derived",
            direction="Output"
        )

        return [hanya_update, hanya_null_nol, simpan_temp, output_persil]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def delete_if_exists(self, path):
        if arcpy.Exists(path):
            try:
                arcpy.management.Delete(path)
            except Exception:
                pass

    def add_field_if_not_exists(self, feature_class, field_name, field_type):
        field_names = [field.name.lower() for field in arcpy.ListFields(feature_class)]
        if field_name.lower() not in field_names:
            arcpy.management.AddField(feature_class, field_name, field_type)

    def execute(self, parameters, messages):
        arcpy.AddMessage("== Proses mulai ==")

        # 1. Mengambil Konfigurasi dari config file
        configs = persil.get_config_values()
        dataset_path = configs["project_config"]["dataset_path"]
        gdb_path = configs["project_config"]["gdb_path"]
        jaringanjalan_path = os.path.join(dataset_path, "Jaringan_Jalan")
        jarjal_ds_path = os.path.join(gdb_path, constant.FD_TEMPLATE_JARINGAN_JALAN)
        nd_path = os.path.join(jarjal_ds_path, constant.TEMPLATE_LAYER_NETWORK_DATASET_JARINGAN_JALAN)
        jaringanjalan_nd_path = os.path.join(jarjal_ds_path, constant.TEMPLATE_LAYER_FEATURE_CLASS_JARINGAN_JALAN)

        # 2. Mengambil nilai parameter
        hanya_update = parameters[0].value
        hanya_null_nol = parameters[1].value
        simpan_temp = parameters[2].value 

        # 3. Mempersiapkan path untuk dataset dan output sementara
        persil_fc = os.path.join(dataset_path, "Persil_Layer")
        temp_output_name = "Analisis_Persil_Dengan_Fasilitas_Temp"
        temp_output_fc = os.path.join(dataset_path, temp_output_name)
        dataset_fasilitas_path = os.path.join(os.path.dirname(dataset_path), "fasilitas_ds")

        if simpan_temp:
            self.delete_if_exists(temp_output_fc)
            arcpy.AddMessage("== Membuat layer sementara ==")
            arcpy.management.CopyFeatures(persil_fc, temp_output_fc)
            update_fc = temp_output_fc
        else:
            update_fc = persil_fc

        # --- Mengambil list fasilitas ---
        arcpy.env.workspace = dataset_fasilitas_path
        list_fc = arcpy.ListFeatureClasses("*")
        list_fasilitas = []
        
        if list_fc:
            for fc in list_fc:
                temp_path = os.path.join(dataset_fasilitas_path, fc)
                jumlah_fc = int(arcpy.management.GetCount(temp_path)[0])
                if jumlah_fc > 0:
                    list_fasilitas.append(fc)

        # 4. Menentukan layer untuk analisis dan melakukan seleksi
        persil_layer = "persil_input"
        self.delete_if_exists(persil_layer)
        arcpy.management.MakeFeatureLayer(update_fc, persil_layer)

        # Membangun Query Seleksi Dinamis
        queries = []
        if hanya_update:
            queries.append("(UPPER(perubahan) IS NOT NULL")
            
        if hanya_null_nol:
            existing_fields = [f.name.lower() for f in arcpy.ListFields(persil_layer)]
            null_queries = []
            
            for fasilitas in list_fasilitas:
                nama_field = f"JK{fasilitas}"
                if nama_field.lower() in existing_fields:
                    null_queries.append(f"({nama_field} IS NULL OR {nama_field} = 0)")
                else:
                    null_queries.append("(1=1)")
                    
            if null_queries:
                null_sql = " OR ".join(null_queries)
                queries.append(f"({null_sql})")

        # Eksekusi seleksi
        if queries:
            final_query = " AND ".join(queries)
            arcpy.AddMessage(f"== Query Seleksi: {final_query} ==")
            arcpy.management.SelectLayerByAttribute(
                persil_layer,
                "NEW_SELECTION",
                final_query
            )

        # 5. Validasi jumlah feature yang akan diproses
        jumlah = int(arcpy.management.GetCount(persil_layer)[0])
        if jumlah == 0:
            arcpy.AddWarningMessage("== Tidak ada feature yang diproses (Semua mungkin sudah terhitung) ==")
            parameters[3].value = temp_output_name if simpan_temp else "Persil_Layer"
            return

        persilcentroid = "Centroid_Persil"
        gdb_temp = arcpy.env.scratchGDB
        persilcentroid_path = os.path.join(gdb_temp, persilcentroid)

        # 6. Membuat centroid dari persil
        arcpy.AddMessage(f"== Membuat centroid persil untuk {jumlah} data ==")
        arcpy.management.FeatureToPoint(persil_layer, persilcentroid_path, "INSIDE")
        
        oid_to_idbidang = {}
        oid_field = arcpy.Describe(persilcentroid_path).OIDFieldName
        with arcpy.da.SearchCursor(persilcentroid_path, [oid_field, "IDBIDANG"]) as rows:
            for oid, idbidang in rows:
                oid_to_idbidang[oid] = idbidang

        # 7. Persiapan field pada jaringan jalan untuk analisis jaringan
        arcpy.AddMessage("== Persiapan field jalan ==")
        self.add_field_if_not_exists(jaringanjalan_path, "P_Jalan", "DOUBLE")
        arcpy.management.CalculateField(jaringanjalan_path, "P_Jalan", "!shape.length!", "PYTHON3")

        outNALayerName = "hasil_analisis"
        impedance_attribute = "P_Jalan"
        dataset_template_path = os.path.dirname(jaringanjalan_nd_path)
        
        arcpy.AddMessage(f"== Fasilitas yang diproses: {list_fasilitas} ==")
        
        hasilNAObject = arcpy.na.MakeClosestFacilityLayer(
            in_network_dataset=nd_path,
            out_network_analysis_layer=outNALayerName,
            impedance_attribute=impedance_attribute,
            travel_from_to="TRAVEL_TO",
            default_cutoff=500000,
            default_number_facilities_to_find=1
        )
            
        outNALayer = hasilNAObject.getOutput(0)
        arcpy.na.AddLocations(outNALayer, "Incidents", persilcentroid_path)
        
        jarak_dict = {}
        daftar_nama_field = []
        
        for fasilitas in list_fasilitas:
            # 8. Melakukan analisis jaringan
            arcpy.AddMessage(f"== Hitung jarak fasilitas: {fasilitas} ==")
            fasilitas_path = os.path.join(dataset_fasilitas_path, fasilitas)
            nama_field_target = f"JK{fasilitas}"
            daftar_nama_field.append(nama_field_target)

            # Tambahkan Field ke Persil_Layer jika belum ada
            self.add_field_if_not_exists(update_fc, nama_field_target, "DOUBLE")

            arcpy.na.AddLocations(
                in_network_analysis_layer=outNALayer,
                sub_layer="Facilities",
                in_table=fasilitas_path,
                append="CLEAR"
            )

            solve_result = arcpy.na.Solve(outNALayer)
            if solve_result.getMessages(1):
                arcpy.AddWarningMessage(f"Peringatan Solve NA: {solve_result.getMessages(1)}")

            incident_path = os.path.join(dataset_template_path, f"incident_{fasilitas}")
            route_path = os.path.join(dataset_template_path, f"route_{fasilitas}")

            self.delete_if_exists(incident_path)
            self.delete_if_exists(route_path)

            for lyr in outNALayer.listLayers():
                if lyr.isGroupLayer:
                    continue
                if lyr.name == "Incidents":
                    arcpy.management.CopyFeatures(lyr, incident_path)
                elif lyr.name == "Routes":
                    arcpy.management.CopyFeatures(lyr, route_path)

            # 9. Mengambil nilai Total_P_Jalan ke Incident
            arcpy.management.JoinField(
                in_data=incident_path,
                in_field="OBJECTID",
                join_table=route_path,
                join_field="IncidentID",
                fields=["Total_P_Jalan"]
            )

            # 10. Menyimpan data panjang rute
            with arcpy.da.SearchCursor(incident_path, ["SourceOID", "Total_P_Jalan"]) as rows:
                for source_oid, jarak in rows:
                    if jarak is None:
                        continue # Skip jika tidak ada rute yang ditemukan
                    
                    idbidang = oid_to_idbidang.get(source_oid)
                    if idbidang is not None:
                        if idbidang not in jarak_dict:
                            jarak_dict[idbidang] = {}
                        jarak_dict[idbidang][nama_field_target] = jarak
                        
        # 11. Update data panjang rute ke layer persil
        field_to_update = ["IDBIDANG"] + daftar_nama_field
        with arcpy.da.UpdateCursor(persil_layer, field_to_update) as rows:
            for row in rows:
                data = jarak_dict.get(row[0], {})
                if not data:
                    continue # Skip jika tidak ada update jarak untuk IDBIDANG ini
                    
                for i, field_name in enumerate(daftar_nama_field, start=1):
                    val = data.get(field_name)
                    if val is not None:
                        row[i] = val
                rows.updateRow(row)

        # 12. Menampilkan output
        output_name = temp_output_name if simpan_temp else "Persil_Layer"
        self.delete_if_exists(output_name)
        arcpy.management.MakeFeatureLayer(update_fc, output_name)

        parameters[3].value = output_name
        arcpy.AddMessage("== Proses selesai ==")
        return
