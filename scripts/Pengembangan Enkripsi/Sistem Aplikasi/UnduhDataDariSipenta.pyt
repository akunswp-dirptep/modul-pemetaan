import arcpy
import os
import requests
import sys
from datetime import datetime

script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from zntutils.system_utils import renew_user_data, get_all_config, get_user_data, clear_user_data, get_all_berkas_id, renew_multiple_user_data
from zntutils.constant import PREFERRED_BERKAS_ID, TIPE_USER_PIHAK_KETIGA, TIPE_USER_SSO, AUTH_KEY, PREFERRED_SERVER_KEY, YEAR_KEY, SSO_DATA_KEY, CREDENTIAL_KEY
from zntutils.upload_utils import upload_shapefile_to_sipenta, upload_feature_layer_to_sipenta

class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Unduh_Data_Dari_Sipenta, Upload_Revisi_Ke_Sipenta, GenerateISOMetadata]


class Unduh_Data_Dari_Sipenta(object):
    def __init__(self):
        self.label = "Unduh Data Dari Sipenta"
        self.description = "Tool untuk mengunduh data pemetaan berdasarkan nomor berkas."
        self.canRunInBackground = False

        self.param_mapping = {
            # Berkas 01: Pembuatan ZNT
            "01": {
                "Peta Rencana Area Kerja": "pembuatan_znt_peta_rencana_area_kerja",
                "Peta Area Kerja yang Disepakati": "pembuatan_znt_peta_area_kerja_disepakati",
                "Peta Area Kerja (AOI)": "pembuatan_znt_peta_area_kerja_aoi",
                "Delineasi Zona Awal Nilai Tanah": "pembuatan_znt_delineasi_zona_awal",
                "Survei Batas Zona Awal Nilai Tanah": "pembuatan_znt_survei_batas_zona_awal",
                "Peta Sebaran Sampel": "pembuatan_znt_peta_shp_sebaran_sampel",
                "Peta Standar Deviasi": "pembuatan_znt_peta_shp_standar_deviasi",
                "Peta Zona Nilai Tanah": "pembuatan_znt_laporan_pendahuluan",        
            },
            
            # Berkas 02: Pembaruan ZNT
            "02": {
                "Peta Rencana Area Kerja": "pembaruan_znt_peta_rencana_area_kerja",
                "Peta Area Kerja yang Disepakati": "pembaruan_znt_peta_area_kerja_yang_disepakati",
                "Delineasi Perubahan Batas Zona Baru": "pembaruan_znt_delineasi_perubahan_batas_zona_baru",
                "Peta Hasil Survei Batas Zona Nilai Tanah Yang Diperbarui": "pembaruan_znt_peta_hasil_survei_batas_zona_shp",
                "Titik Zona": "pembaruan_znt_data_shp_titik_zona",
                "Titik Sampel": "pembaruan_znt_data_shp_titik_sampel",
                "Zona Nilai Tanah": "pembaruan_znt_data_shp_zona_nilai_tanah",
                # Lanjutkan untuk pembaruan ZNT lainnya...
            },
            
            # Berkas 03: Pembuatan NBT
            "03": {
                "Peta Rencana Lokasi Kegiatan (AOI)": "pembuatan_nbt_peta_rencana_lokasi_kegiatan",
                "Peta Lokasi Kegiatan (AOI) yang Disepakati": "pembuatan_nbt_peta_lokasi_kegiatan_yang_disepakati",
                "Peta Area Kerja (AOI)": "pembuatan_nbt_peta_area_kerja",
                "Basis Data Penilaian Bidang Tanah": "pembuatan_nbt_basis_data_penilaian_bidang_tanah",
                "Peta Sebaran Sampel Nilai Tanah": "pembuatan_nbt_peta_sebaran_sampel_nilai_tanah",
                "Nilai Bidang Tanah": "pembuatan_nbt_nilai_bidang_tanah"
            },
            
            # Berkas 04: Pembaruan NBT
            "04": {
                "Peta Rencana Lokasi Kegiatan (AOI)": "pembaruan_nbt_peta_rencana_lokasi_kegiatan",
                "Peta Lokasi Kegiatan (AOI) yang Disepakati": "pembaruan_nbt_peta_lokasi_kegiatan_yang_disepakati",
                "Basis Data Penilaian Bidang Tanah": "pembaruan_nbt_basis_data_penilaian_bidang_tanah",
                "Peta Sebaran Sampel Nilai Tanah": "pembaruan_nbt_peta_sebaran_sampel_nilai_tanah",
                "Nilai Bidang Tanah": "pembaruan_nbt_nilai_bidang_tanah"

            }
        }

    def getParameterInfo(self):
        # 1. Parameter Berkas
        berkas_list = get_all_berkas_id() # Tarik seluruh berkas yang ada
        berkas_show = []
        can_show = 0
        if berkas_list is not None:
            for berkas in berkas_list:
                berkas_show.append(f"{berkas[0]}")
                can_show += 1
        if can_show == 0:
            berkas_show = ['Tidak ada berkas yang dapat dipilih']

        berkas = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="berkas",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        berkas.filter.type = "ValueList"
        berkas.filter.list = berkas_show

        # 2. Parameter Jenis Data (Dropdown Label)
        jenis_data = arcpy.Parameter(
            displayName="Jenis Data",
            name="jenis_data",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        jenis_data.filter.type = "ValueList"
        jenis_data.filter.list = [] 

        # 3. Parameter Output Folder
        output_folder = arcpy.Parameter(
            displayName="Folder Penyimpanan",
            name="output_folder",
            datatype="DEFolder",
            parameterType="Required",
            direction="Input")
        
        default_downloads = os.path.join(os.path.expanduser('~'), 'Downloads')
        output_folder.value = default_downloads

        # 4. Parameter Penjelasan
        penjelasan = arcpy.Parameter(
            displayName="Informasi Tools",
            name="petunjuk",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        penjelasan.value = (
            "Login terlebih dahulu untuk mengakses fitur ini.\n\n"
            "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
            "Kementerian ATR/BPN.\n"
            "Tahun: {}\n".format(datetime.now().year))
            
        params = [berkas, jenis_data, output_folder, penjelasan]
        return params

    def updateMessages(self, parameters):
        return

    def updateParameters(self, parameters):
        berkas = parameters[0]
        jenis_data = parameters[1]
        output_folder = parameters[2]
        penjelasan = parameters[3]

        is_login = get_user_data(CREDENTIAL_KEY)

        if is_login is None:
            berkas.enabled = False
            jenis_data.enabled = False
            output_folder.enabled = False
            penjelasan.enabled = True
        else:
            berkas.enabled = True
            jenis_data.enabled = True
            output_folder.enabled = True
            penjelasan.enabled = False

        # Filter List Jenis Data berdasarkan nomor berkas (01/02/03/04)
        if berkas.valueAsText and berkas.valueAsText != 'Tidak ada berkas yang dapat dipilih':
            prefix = berkas.valueAsText[:2] 
            if prefix in self.param_mapping:
                labels = list(self.param_mapping[prefix].keys())
                jenis_data.filter.list = labels
                
                if jenis_data.valueAsText not in labels:
                    jenis_data.value = labels[0] if labels else None
            else:
                jenis_data.filter.list = []
                jenis_data.value = None
        return

    def execute(self, parameters, messages):
        user_data = get_user_data(CREDENTIAL_KEY)
        if not user_data:
            arcpy.AddError("Anda belum login. Silakan login terlebih dahulu.")
            return

        nomor_berkas = parameters[0].valueAsText
        label_data = parameters[1].valueAsText
        output_folder = parameters[2].valueAsText

        server = get_user_data(PREFERRED_SERVER_KEY)
        use_production = True if server == "Produksi" or server is None else False
        token = user_data.get(AUTH_KEY, None)

        # Cari param berdasarkan label yang dipilih user
        prefix = nomor_berkas[:2]
        param_id = self.param_mapping.get(prefix, {}).get(label_data)

        if not param_id:
            arcpy.AddError("Parameter ID tidak ditemukan. Periksa kembali konfigurasi data Anda.")
            return

        self.download_from_sipenta(nomor_berkas, token, param_id, output_folder, use_production)
        return

    def download_from_sipenta(self, nomor_berkas, token, param, output_folder, use_production=True):
        arcpy.AddMessage(f"Mempersiapkan unduhan untuk berkas {nomor_berkas}...")

        test_url = "https://belajar.atrbpn.go.id/sipenta/tatausaha-2/api/pemetaan/download"
        prod_url = "https://sipenta.atrbpn.go.id/tatausaha/api/pemetaan/download"
        base_url = prod_url if use_production else test_url
        
        api_url = f"{base_url}?no_berkas={nomor_berkas}&param={param}"
        headers = {"Authorization": f"Bearer {token}"}

        try:
            arcpy.AddMessage("Menghubungi server untuk riwayat file...")
            response = requests.get(api_url, headers=headers)
            response.raise_for_status()
            
            json_data = response.json()

            if not json_data.get("success"):
                raise Exception(json_data.get("message", "Gagal mendapatkan histori file dari server."))

            file_info = json_data.get("data", {})
            file_url = file_info.get("file_path")
            file_name = file_info.get("file_name")

            if not file_url or not file_name:
                raise Exception("URL atau nama file tidak ditemukan dalam respons.")

            arcpy.AddMessage(f"Mengunduh {file_name}...")
            
            # Request file asli 
            # Note: Jika download file statis dari server membutuhkan token juga, 
            # tambahkan param `headers=headers` pada method get di bawah ini.
            file_response = requests.get(file_url, stream=True)
            file_response.raise_for_status()

            output_path = os.path.join(output_folder, file_name)
            with open(output_path, 'wb') as f:
                for chunk in file_response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            arcpy.AddMessage(f"Berhasil! File diunduh dan disimpan di: {output_path}")

        except requests.exceptions.HTTPError as e:
            response = e.response
            message = ""
            try:
                error_json = response.json()
                message = error_json.get("message", "")
            except Exception:
                pass

            if response.status_code == 403 and "expired" in message.lower():
                clear_user_data()
                arcpy.AddError("Token Anda kadaluarsa, silakan login ulang.")
            elif response.status_code == 403:
                arcpy.AddError("Akses ditolak (403). Periksa hak akses atau token.")
            elif response.status_code == 404:
                arcpy.AddError("File tidak ditemukan (404) di server.")
            else:
                arcpy.AddError(f"HTTP Error {response.status_code}: {message or str(e)}")

        except Exception as e:
            arcpy.AddError(f"Terjadi kesalahan saat proses unduh: {str(e)}")

class Upload_Revisi_Ke_Sipenta(object):

    def __init__(self):
        self.label = "Upload Revisi ke Sipenta"
        self.description = "Tool untuk mengupload revisi peemtaan berdasarkan nomor berkas."
        self.canRunInBackground = False

        self.param_mapping = {
            # Berkas 01: Pembuatan ZNT
            "01": {
                "Fase Persiapan": "pembuatan_znt_usulan_rev_shp_persiapan",
                "Fase Pembuatan Zona Awal": "pembuatan_znt_usulan_rev_shp_pembuatan_zona_awal",
                "Fase Survey Zona Awal": "pembuatan_znt_usulan_rev_shp_survei_zona_awal",
                "Fase Pengumpulan Sampel": "pembuatan_znt_usulan_rev_shp_pengumpulan_sampel",
                "Fase Analisis Pengolahan": "pembuatan_znt_usulan_rev_shp_analisis_pengolahan",
                "Fase Penyajian Peta": "pembuatan_znt_usulan_rev_shp_penyajian_peta",
                "Fase Pelaporan": "pembuatan_znt_usulan_rev_shp_pelaporan",        
            },
            
            # Berkas 02: Pembaruan ZNT
            "02": {
                "Fase Persiapan": "pembaruan_znt_usulan_rev_shp_persiapan",
                "Fase Delineasi Zona": "pembaruan_znt_usulan_rev_shp_analis_delineasi_zona",
                "Fase Survey Batas Zona": "pembaruan_znt_usulan_rev_shp_survei_batas_zona",
                "Fase Pengumpulan Sampel": "pembaruan_znt_usulan_rev_shp_pengumpulan_sampel",
                "Fase Analisis Pengolahan": "pembaruan_znt_usulan_rev_shp_analisis_pengolahan",
                "Fase Penyajian Peta": "pembaruan_znt_usulan_rev_shp_penyajian_peta",
                "Fase Pelaporan": "pembaruan_znt_usulan_rev_shp_pelaporan",        
            },
            
            # Berkas 03: Pembuatan NBT
            "03": {
                "Fase Persiapan": "pembuatan_nbt_usulan_rev_shp_persiapan",
                "Fase Survey Fisik dan Lingkungan Bidang Tanah": "pembuatan_nbt_usulan_rev_shp_survei_fisik_dan_lbt",
                "Fase Pembaruan Basis Data": "pembuatan_nbt_usulan_rev_shp_pembaruan_basis_data",
                "Fase Pengumpulan Sampel": "pembuatan_nbt_usulan_rev_shp_pengumpulan_sampel",
                "Fase Analisis Data": "pembuatan_nbt_usulan_rev_shp_analisis_data",
                "Fase Penyajian Peta": "pembuatan_nbt_usulan_rev_shp_penyajian_peta",
                "Fase Pelaporan": "pembuatan_nbt_usulan_rev_shp_pelaporan",        
            },
            
            # Berkas 04: Pembaruan NBT
            "04": {
                "Fase Persiapan": "pembaruan_nbt_usulan_rev_shp_persiapan",
                "Fase Identifikasi Perubahan Fisik dan Lingkungan Bidang Tanah": "pembaruan_nbt_usulan_rev_shp_identifikasi_lbt",
                "Fase Survey Fisik dan Lingkungan Bidang Tanah": "pembaruan_nbt_usulan_rev_shp_survei_fisik_dan_lbt",
                "Fase Pembaruan Basis Data": "pembaruan_nbt_usulan_rev_shp_pembaruan_basis_data",
                "Fase Pengumpulan Sampel": "pembuatan_nbt_usulan_rev_shp_pengumpulan_sampel",
                "Fase Analisis Data": "pembuatan_nbt_usulan_rev_shp_analisis_data",
                "Fase Penyajian Peta": "pembaruan_nbt_usulan_rev_shp_penyajian_peta",
                "Fase Pelaporan": "pembaruan_nbt_usulan_rev_shp_pelaporan",        
            },
        }

    def getParameterInfo(self):
        # 1. Parameter Berkas
        berkas_list = get_all_berkas_id(show_can_qc=True) # Tarik seluruh berkas yang ada
        berkas_show = []
        can_show = 0
        if berkas_list is not None:
            for berkas in berkas_list:
                if berkas[1] == True:
                    berkas_show.append(f"{berkas[0]}")
                    can_show += 1
        if can_show == 0:
            berkas_show = ['Tidak ada berkas yang dapat dipilih']

        param_in_feature = arcpy.Parameter(
            name="in_feature",
            displayName="Input Layer (Persil)",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        
        berkas = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="berkas",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        berkas.filter.type = "ValueList"
        berkas.filter.list = berkas_show

        # 2. Parameter Jenis Data (Dropdown Label)
        jenis_data = arcpy.Parameter(
            displayName="Pilih Tahapan",
            name="jenis_data",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        jenis_data.filter.type = "ValueList"
        jenis_data.filter.list = [] 



        # 4. Parameter Penjelasan
        penjelasan = arcpy.Parameter(
            displayName="Informasi Tools",
            name="petunjuk",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        penjelasan.value = (
            "Login terlebih dahulu untuk mengakses fitur ini.\n\n"
            "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
            "Kementerian ATR/BPN.\n"
            "Tahun: {}\n".format(datetime.now().year))
            
        params = [param_in_feature, berkas, jenis_data, penjelasan]
        return params

    def updateMessages(self, parameters):
        return

    def updateParameters(self, parameters):
        feature_layer = parameters[0]
        berkas = parameters[1]
        jenis_data = parameters[2]
        penjelasan = parameters[3]

        is_login = get_user_data(CREDENTIAL_KEY)

        if is_login is None:
            berkas.enabled = False
            jenis_data.enabled = False
            feature_layer.enabled = False
            penjelasan.enabled = True
        else:
            berkas.enabled = True
            jenis_data.enabled = True
            feature_layer.enabled = True
            penjelasan.enabled = False

        # Filter List Jenis Data berdasarkan nomor berkas (01/02/03/04)
        if berkas.valueAsText and berkas.valueAsText != 'Tidak ada berkas yang dapat dipilih':
            prefix = berkas.valueAsText[:2] 
            if prefix in self.param_mapping:
                labels = list(self.param_mapping[prefix].keys())
                jenis_data.filter.list = labels
                
                if jenis_data.valueAsText not in labels:
                    jenis_data.value = labels[0] if labels else None
            else:
                jenis_data.filter.list = []
                jenis_data.value = None
        return

    def execute(self, parameters, messages):
        user_data = get_user_data(CREDENTIAL_KEY)
        if not user_data:
            arcpy.AddError("Anda belum login. Silakan login terlebih dahulu.")
            return

        feature_layer = parameters[0].valueAsText
        berkas_value = parameters[1].valueAsText
        jenis_data = parameters[2].valueAsText

        server = get_user_data(PREFERRED_SERVER_KEY)
        use_production = True if server == "Produksi" or server == None else False
        token = user_data.get(AUTH_KEY, None)

        # Cari param berdasarkan label yang dipilih user
        prefix = berkas_value[:2]
        param_id = self.param_mapping.get(prefix, {}).get(jenis_data)

        if not param_id:
            arcpy.AddError("Parameter ID tidak ditemukan. Periksa kembali konfigurasi data Anda.")
            return

        upload_feature_layer_to_sipenta(
            nomor_berkas=berkas_value,
            token=token,
            param=param_id,
            in_feature="Zona_Layer",
            feature_layer=feature_layer,
            use_production=use_production)
        return

class GenerateISOMetadata(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Create ISO 19115-3 Metadata"
        self.description = "Membuat file metadata XML berformat ISO 19115-3 untuk suatu Feature Layer."
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        in_feature = arcpy.Parameter(
            displayName="Input Feature Layer",
            name="in_feature_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        out_xml = arcpy.Parameter(
            displayName="Output XML File",
            name="out_xml_file",
            datatype="DEFile",
            parameterType="Required",
            direction="Output")
        out_xml.filter.list = ["xml"]

        return [in_feature, out_xml]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        in_feature = parameters[0].valueAsText
        out_xml = parameters[1].valueAsText

        arcpy.AddMessage(f"Membaca informasi dari: {in_feature}")

        # Dapatkan Deskripsi dari Feature Layer untuk dinamisasi metadata
        desc = arcpy.Describe(in_feature)
        
        # 1. Nama Dataset
        dataset_name = desc.baseName

        # 2. Extent / Bounding Box
        extent = desc.extent
        xmin = extent.XMin
        xmax = extent.XMax
        ymin = extent.YMin
        ymax = extent.YMax

        # 3. Spatial Reference (EPSG Code)
        sr = desc.spatialReference
        epsg_code = sr.factoryCode if sr.factoryCode else "4326"

        # 4. Tanggal Pembuatan Metadata (Waktu saat ini)
        now_date = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

        # Struktur XML Format ISO 19115-3
        # Menggunakan .format() agar kompatibel dengan kurung kurawal XML (jika ada)
        xml_template = """<mdb:MD_Metadata xmlns:mac="http://standards.iso.org/iso/19115/-3/mac/2.0"
                 xmlns:mrc="http://standards.iso.org/iso/19115/-3/mrc/2.0"
                 xmlns:mdq="http://standards.iso.org/iso/19157/-2/mdq/1.0"
                 xmlns:srv="http://standards.iso.org/iso/19115/-3/srv/2.1"
                 xmlns:mrd="http://standards.iso.org/iso/19115/-3/mrd/1.0"
                 xmlns:mrl="http://standards.iso.org/iso/19115/-3/mrl/2.0"
                 xmlns:mri="http://standards.iso.org/iso/19115/-3/mri/1.0"
                 xmlns:mrs="http://standards.iso.org/iso/19115/-3/mrs/1.0"
                 xmlns:cit="http://standards.iso.org/iso/19115/-3/cit/2.0"
                 xmlns:mcc="http://standards.iso.org/iso/19115/-3/mcc/1.0"
                 xmlns:mas="http://standards.iso.org/iso/19115/-3/mas/1.0"
                 xmlns:gex="http://standards.iso.org/iso/19115/-3/gex/1.0"
                 xmlns:lan="http://standards.iso.org/iso/19115/-3/lan/1.0"
                 xmlns:mda="http://standards.iso.org/iso/19115/-3/mda/1.0"
                 xmlns:mco="http://standards.iso.org/iso/19115/-3/mco/1.0"
                 xmlns:gco="http://standards.iso.org/iso/19115/-3/gco/1.0"
                 xmlns:mds="http://standards.iso.org/iso/19115/-3/mds/2.0"
                 xmlns:mdb="http://standards.iso.org/iso/19115/-3/mdb/2.0"
                 xmlns:cat="http://standards.iso.org/iso/19115/-3/cat/1.0"
                 xmlns:mex="http://standards.iso.org/iso/19115/-3/mex/1.0"
                 xmlns:msr="http://standards.iso.org/iso/19115/-3/msr/2.0"
                 xmlns:mdt="http://standards.iso.org/iso/19115/-3/mdt/2.0"
                 xmlns:mmi="http://standards.iso.org/iso/19115/-3/mmi/1.0"
                 xmlns:gcx="http://standards.iso.org/iso/19115/-3/gcx/1.0"
                 xmlns:mpc="http://standards.iso.org/iso/19115/-3/mpc/1.0"
                 xmlns:gfc="http://standards.iso.org/iso/19110/gfc/1.1"
                 xmlns:gml="http://www.opengis.net/gml/3.2"
                 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                 xmlns:xlink="http://www.w3.org/1999/xlink"
                 xsi:schemaLocation="http://standards.iso.org/iso/19115/-3/mdb/2.0 https://schemas.isotc211.org/19115/-3/mdt/2.0/mdt.xsd ">
<mdb:metadataIdentifier>
<mcc:MD_Identifier>
<mcc:code>
<gco:CharacterString>{dataset_name}</gco:CharacterString>
</mcc:code>
</mcc:MD_Identifier>
</mdb:metadataIdentifier>
<mdb:defaultLocale>
<lan:PT_Locale>
<lan:language>
<lan:LanguageCode codeList="http://www.loc.gov/standards/iso639-2/php/code_list.php" codeListValue="ind">ind</lan:LanguageCode>
</lan:language>
<lan:country>
<lan:CountryCode codeList="http://www.iso.org/iso/country_codes/iso_3166_code_lists.htm" codeListValue="ID">ID</lan:CountryCode>
</lan:country>
<lan:characterEncoding>
<lan:MD_CharacterSetCode codeList="https://schemas.isotc211.org/19115/-3/lan/2.0/codelists.xml#MD_CharacterSetCode" codeListValue="utf8">utf8</lan:MD_CharacterSetCode>
</lan:characterEncoding>
</lan:PT_Locale>
</mdb:defaultLocale>
<mdb:parentMetadata uuidref="RBI5KINDONESIA2015">
</mdb:parentMetadata>
<mdb:metadataScope>
<mdb:MD_MetadataScope>
<mdb:resourceScope>
<mcc:MD_ScopeCode codeList="standards.iso.org/19115/-3/lan/1.0/codelists.xml#MD_ScopeCode" codeListValue="dataset">dataset</mcc:MD_ScopeCode>
</mdb:resourceScope>
<mdb:name>
<gco:CharacterString>Dataset</gco:CharacterString>
</mdb:name>
</mdb:MD_MetadataScope>
</mdb:metadataScope>
<mdb:contact>
<cit:CI_Responsibility>
<cit:role>
<cit:CI_RoleCode codeList="standards.iso.org/19115/-3/lan/1.0/codelists.xml#CI_RoleCode" codeListValue="owner">owner</cit:CI_RoleCode>
</cit:role>
<cit:party>
<cit:CI_Organisation>
<cit:name>
<gco:CharacterString>Pusat Pemetaan Rupabumi dan Toponimi</gco:CharacterString>
</cit:name>
<cit:contactInfo>
<cit:CI_Contact>
<cit:phone>
<cit:CI_Telephone>
<cit:number>
<gco:CharacterString>021-8753155</gco:CharacterString>
</cit:number>
<cit:numberType>
<cit:CI_TelephoneTypeCode codeList="standards.iso.org/19115/-3/lan/1.0/codelists.xml#CI_TelephoneTypeCode" codeListValue="voice">voice</cit:CI_TelephoneTypeCode>
</cit:numberType>
</cit:CI_Telephone>
</cit:phone>
<cit:address>
<cit:CI_Address>
<cit:deliveryPoint>
<gco:CharacterString>Jl Raya Jakarta Bogor KM.46</gco:CharacterString>
</cit:deliveryPoint>
<cit:city>
<gco:CharacterString>Bogor</gco:CharacterString>
</cit:city>
<cit:administrativeArea>
<gco:CharacterString>Jawa Barat</gco:CharacterString>
</cit:administrativeArea>
<cit:postalCode>
<gco:CharacterString>16912</gco:CharacterString>
</cit:postalCode>
<cit:country>
<lan:CountryCode codeList="http://www.iso.org/iso/country_codes/iso_3166_code_lists.htm" codeListValue="ID">ID</lan:CountryCode>
</cit:country>
<cit:electronicMailAddress>
<gco:CharacterString>info@big.go.id</gco:CharacterString>
</cit:electronicMailAddress>
</cit:CI_Address>
</cit:address>
<cit:hoursOfService>
<gco:CharacterString>08.00-16.00</gco:CharacterString>
</cit:hoursOfService>
<cit:contactInstructions>
<gco:CharacterString>hari kerja senin - jumat</gco:CharacterString>
</cit:contactInstructions>
</cit:CI_Contact>
</cit:contactInfo>
<cit:individual>
<cit:CI_Individual>
<cit:name>
<gco:CharacterString>Ade Komara</gco:CharacterString>
</cit:name>
<cit:positionName>
<gco:CharacterString>Kepala Pusat Pemetaan Rupabumi dan Toponimi</gco:CharacterString>
</cit:positionName>
</cit:CI_Individual>
</cit:individual>
</cit:CI_Organisation>
</cit:party>
</cit:CI_Responsibility>
</mdb:contact>
<mdb:dateInfo>
<cit:CI_Date>
<cit:date>
<gco:DateTime>{now_date}</gco:DateTime>
</cit:date>
<cit:dateType>
<cit:CI_DateTypeCode codeList="standards.iso.org/19115/-3/lan/1.0/codelists.xml#CI_DateTypeCode" codeListValue="revision">revision</cit:CI_DateTypeCode>
</cit:dateType>
</cit:CI_Date>
</mdb:dateInfo>
<mdb:metadataStandard>
<cit:CI_Citation>
<cit:title>
<gco:CharacterString>ISO 19115-3 Geographic Information - Metadata - Part 1: Fundamentals</gco:CharacterString>
</cit:title>
<cit:edition>
<gco:CharacterString>2014</gco:CharacterString>
</cit:edition>
</cit:CI_Citation>
</mdb:metadataStandard>
<mdb:otherLocale>
<lan:PT_Locale>
<lan:language>
<lan:LanguageCode codeList="http://www.loc.gov/standards/iso639-2/php/code_list.php" codeListValue="ind">ind</lan:LanguageCode>
</lan:language>
<lan:country>
<lan:CountryCode codeList="http://www.iso.org/iso/country_codes/iso_3166_code_lists.htm" codeListValue="ID">ID</lan:CountryCode>
</lan:country>
<lan:characterEncoding>
<lan:MD_CharacterSetCode codeList="standards.iso.org/19115/-3/lan/1.0/codelists.xml#MD_CharacterSetCode" codeListValue="utf8">utf8</lan:MD_CharacterSetCode>
</lan:characterEncoding>
</lan:PT_Locale>
</mdb:otherLocale>
<mdb:spatialRepresentationInfo>
<msr:MD_VectorSpatialRepresentation>
<msr:topologyLevel>
<msr:MD_TopologyLevelCode codeList="standards.iso.org/19115/-3/lan/1.0/codelists.xml#MD_TopologyLevelCode" codeListValue="geometryOnly">geometryOnly</msr:MD_TopologyLevelCode>
</msr:topologyLevel>
<msr:geometricObjects>
<msr:MD_GeometricObjects>
<msr:geometricObjectType>
<msr:MD_GeometricObjectTypeCode codeList="standards.iso.org/19115/-3/lan/1.0/codelists.xml#MD_GeometricObjectTypeCode" codeListValue="composite">composite</msr:MD_GeometricObjectTypeCode>
</msr:geometricObjectType>
</msr:MD_GeometricObjects>
</msr:geometricObjects>
</msr:MD_VectorSpatialRepresentation>
</mdb:spatialRepresentationInfo>
<mdb:referenceSystemInfo>
<mrs:MD_ReferenceSystem>
<mrs:referenceSystemIdentifier>
<mcc:MD_Identifier>
<mcc:code>
<gco:CharacterString>{epsg_code}</gco:CharacterString>
</mcc:code>
<mcc:codeSpace>
<gco:CharacterString>EPSG</gco:CharacterString>
</mcc:codeSpace>
</mcc:MD_Identifier>
</mrs:referenceSystemIdentifier>
</mrs:MD_ReferenceSystem>
</mdb:referenceSystemInfo>
<mdb:identificationInfo>
<mri:MD_DataIdentification>
<mri:citation>
<cit:CI_Citation>
<cit:title>
<gco:CharacterString>{dataset_name}</gco:CharacterString>
</cit:title>
<cit:alternateTitle>
<gco:CharacterString>Peta RBI skala 1:5.000 wilayah kota bogor tahun 2015</gco:CharacterString>
</cit:alternateTitle>
<cit:date>
<cit:CI_Date>
<cit:date>
<gco:DateTime>{now_date}</gco:DateTime>
</cit:date>
<cit:dateType>
<cit:CI_DateTypeCode codeList="standards.iso.org/19115/-3/lan/1.0/codelists.xml#CI_DateTypeCode" codeListValue="creation">creation</cit:CI_DateTypeCode>
</cit:dateType>
</cit:CI_Date>
</cit:date>
<cit:identifier>
<mcc:MD_Identifier>
<mcc:code>
<gco:CharacterString>https://geoservices.big.go.id/rbi/rest/services/BATASWILAYAH/Administrasi_AR_KelDesa_10K/MapServer</gco:CharacterString>
</mcc:code>
</mcc:MD_Identifier>
</cit:identifier>
<cit:presentationForm>
<cit:CI_PresentationFormCode codeList="standards.iso.org/19115/-3/lan/1.0/codelists.xml#CI_PresentationFormCode" codeListValue="imageDigital">imageDigital</cit:CI_PresentationFormCode>
</cit:presentationForm>
</cit:CI_Citation>
</mri:citation>
<mri:abstract>
<gco:CharacterString>RBI kota Bogor tahun 2015 disusun menggunakan sumber data foto udara LIDAR. tahapan pekerjaan pada pembuatan peta RBI ini adalah :1. Stereoploting2. Topologi dan Poligon3. DTM4. Kontur dan Spotheight5. Persiapan Survei6. Survei Kelengkapan Lapangan7. Penyelarasan Data8. Metadata9. Penyajian Hasil Pekerjaan</gco:CharacterString>
</mri:abstract>
<mri:purpose>
<gco:CharacterString>pemenuhan peta dasar RBI Indonesia skala 1:5.000</gco:CharacterString>
</mri:purpose>
<mri:credit>
<gco:CharacterString>Badan Informasi Geospasial</gco:CharacterString>
</mri:credit>
<mri:status>
<mcc:MD_ProgressCode codeList="standards.iso.org/19115/-3/lan/1.0/codelists.xml#MD_ProgressCode" codeListValue="completed">completed</mcc:MD_ProgressCode>
</mri:status>
<mri:spatialRepresentationType>
<mcc:MD_SpatialRepresentationTypeCode codeList="standards.iso.org/19115/-3/lan/1.0/codelists.xml#MD_SpatialRepresentationTypeCode" codeListValue="vector">vector</mcc:MD_SpatialRepresentationTypeCode>
</mri:spatialRepresentationType>
<mri:spatialResolution>
<mri:MD_Resolution>
<mri:equivalentScale>
<mri:MD_RepresentativeFraction>
<mri:denominator>
<gco:Integer>5000</gco:Integer>
</mri:denominator>
</mri:MD_RepresentativeFraction>
</mri:equivalentScale>
</mri:MD_Resolution>
</mri:spatialResolution>
<mri:topicCategory>
<mri:MD_TopicCategoryCode>imageryBaseMapsEarthCover</mri:MD_TopicCategoryCode>
</mri:topicCategory>
<mri:topicCategory>
<mri:MD_TopicCategoryCode>transportation</mri:MD_TopicCategoryCode>
</mri:topicCategory>
<mri:extent>
<gex:EX_Extent>
<gex:description>
<gco:CharacterString>cakupan area dataset</gco:CharacterString>
</gex:description>
<gex:geographicElement>
<gex:EX_GeographicBoundingBox>
<gex:westBoundLongitude>
<gco:Decimal>{xmin}</gco:Decimal>
</gex:westBoundLongitude>
<gex:eastBoundLongitude>
<gco:Decimal>{xmax}</gco:Decimal>
</gex:eastBoundLongitude>
<gex:southBoundLatitude>
<gco:Decimal>{ymin}</gco:Decimal>
</gex:southBoundLatitude>
<gex:northBoundLatitude>
<gco:Decimal>{ymax}</gco:Decimal>
</gex:northBoundLatitude>
</gex:EX_GeographicBoundingBox>
</gex:geographicElement>
</gex:EX_Extent>
</mri:extent>
<mri:resourceMaintenance>
<mmi:MD_MaintenanceInformation>
<mmi:maintenanceAndUpdateFrequency>
<mmi:MD_MaintenanceFrequencyCode codeList="standards.iso.org/19115/-3/lan/1.0/codelists.xml#MD_MaintenanceFrequencyCode" codeListValue="asNeeded">asNeeded</mmi:MD_MaintenanceFrequencyCode>
</mmi:maintenanceAndUpdateFrequency>
</mmi:MD_MaintenanceInformation>
</mri:resourceMaintenance>
<mri:resourceFormat>
<mrd:MD_Format>
<mrd:formatSpecificationCitation>
<cit:CI_Citation>
<cit:title>
<gco:CharacterString>WMS</gco:CharacterString>
</cit:title>
<cit:alternateTitle>
<gco:CharacterString>OGC Web Map Service (WMS) Implementation Specification, OGC 06-042</gco:CharacterString>
</cit:alternateTitle>
<cit:edition>
<gco:CharacterString>1.3</gco:CharacterString>
</cit:edition>
</cit:CI_Citation>
</mrd:formatSpecificationCitation>
</mrd:MD_Format>
</mri:resourceFormat>
<mri:descriptiveKeywords>
<mri:MD_Keywords>
<mri:keyword>
<gco:CharacterString>Rbi</gco:CharacterString>
</mri:keyword>
<mri:type>
<mri:MD_KeywordTypeCode codeList="standards.iso.org/19115/-3/lan/1.0/codelists.xml#napMD_KeywordTypeCode" codeListValue="theme">theme</mri:MD_KeywordTypeCode>
</mri:type>
</mri:MD_Keywords>
</mri:descriptiveKeywords>
<mri:resourceConstraints>
<mco:MD_SecurityConstraints>
<mco:classification>
<mco:MD_ClassificationCode codeList="standards.iso.org/19115/-3/lan/1.0/codelists.xml#MD_ClassificationCode" codeListValue="unclassified">unclassified</mco:MD_ClassificationCode>
</mco:classification>
<mco:userNote>
<gco:CharacterString>permintaan akses untuk skala lebih detail</gco:CharacterString>
</mco:userNote>
<mco:classificationSystem>
<gco:CharacterString>credential need</gco:CharacterString>
</mco:classificationSystem>
</mco:MD_SecurityConstraints>
</mri:resourceConstraints>
<mri:defaultLocale>
<lan:PT_Locale>
<lan:language>
<lan:LanguageCode codeList="http://www.loc.gov/standards/iso639-2/php/code_list.php" codeListValue="ind">ind</lan:LanguageCode>
</lan:language>
<lan:country>
<lan:CountryCode codeList="http://www.iso.org/iso/country_codes/iso_3166_code_lists.htm" codeListValue="ID">ID</lan:CountryCode>
</lan:country>
<lan:characterEncoding>
<lan:MD_CharacterSetCode codeList="standards.iso.org/19115/-3/lan/1.0/codelists.xml#MD_CharacterSetCode" codeListValue="utf8">utf8</lan:MD_CharacterSetCode>
</lan:characterEncoding>
</lan:PT_Locale>
</mri:defaultLocale>
<mri:environmentDescription>
<gco:CharacterString>Microsoft Windows 10 Version 10.0 (Build 19045) ; Esri ArcGIS 12.9.0.32739</gco:CharacterString>
</mri:environmentDescription>
</mri:MD_DataIdentification>
</mdb:identificationInfo>
</mdb:MD_Metadata>"""

        # Melakukan proses inject variable dari feature class ke format template XML
        formatted_xml = xml_template.format(
            dataset_name=dataset_name,
            now_date=now_date,
            epsg_code=epsg_code,
            xmin=xmin,
            xmax=xmax,
            ymin=ymin,
            ymax=ymax
        )

        # Menyimpan output string XML ke dalam path/lokasi parameter target
        with open(out_xml, 'w', encoding='utf-8') as f:
            f.write(formatted_xml)

        arcpy.AddMessage(f"Berhasil! Metadata XML berformat ISO 19115-3 telah tersimpan di {out_xml}")
        return