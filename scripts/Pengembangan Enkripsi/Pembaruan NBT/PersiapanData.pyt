from datetime import datetime
import sys
import arcpy, os

arcpy.env.outputZFlag = "Disabled"
arcpy.env.outputMFlag = "Disabled"

# Tambahkan parent directory ke sys.path
script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from zntutils.constant import NAMA_PROVINSI, KAB_KOTA
from zntutils.document import validate_document_type, get_credentials
from zntutils.upload_utils import main_upload_shapefile, main_upload
from zntutils.system_utils import get_user_data, renew_user_data
from zntutils import zona_layer

#Helper Functions
def is_internal():
    try:
        return bool(get_credentials(credential_type="OperatorGISInternal", use_for_tools_validity=True))
        # return True
    except Exception:
        return False

def current_year():
    try:
        return int(datetime.now().year)
    except Exception:
        return None

class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [Upload_Peta_Rencana_Lokasi_Kegiatan_AOI,
                      Upload_Peta_Lokasi_Kegiatan_Disepakati_AOI,
                      Upload_Peta_Peta_Area_Kerja_AOI]

class Upload_Peta_Rencana_Lokasi_Kegiatan_AOI(object):
    def __init__(self):
        self.label = "Upload Peta Rencana Lokasi Kegiatan (AOI)"
        self.description = ""
        self.canRunInBackground = False


    def getParameterInfo(self):
        self.is_gis_internal = is_internal()
        preferred_server = get_user_data('preferred_server')
        nik = get_user_data('nik')
        berkas = get_user_data('berkas')
        self.current_year = current_year()

        param0 = arcpy.Parameter(
            displayName="Nomor Induk Kependudukan (NIK)",
            name="username",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        if nik:
            param0.value = nik
        param1 = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="project_id",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        if berkas:
            param1.value = berkas
        param2 = arcpy.Parameter(
            displayName="Tahun",
            name="tahun",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")

        param3 = arcpy.Parameter(
            displayName="Shapefile Peta Rencana Lokasi Kegiatan (.shp)",
            name="shapefile_path",
            datatype="DEFile",  
            parameterType="Required",
            direction="Input")
        
        param4 = arcpy.Parameter(
            displayName="Server Sipenta",
            name="link",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
               
        if self.current_year:
            param2.value = self.current_year

        if preferred_server:
            param4.value = preferred_server

        param4.filter.type = "ValueList"
        param4.filter.list = ["Produksi", "Belajar"]
        
        params = [param0, param1, param2, param3]
        # Periksa ulang status saat membuka parameter agar mengikuti login terbaru
        self.is_gis_internal = is_internal()
        if self.is_gis_internal:
            params.append(param4)
            return params
        else:
            return params
        
    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        input_nik = parameters[0]
        if input_nik.value:
            # Trim semua spasi (leading, trailing, dan di tengah)
            nik_str = str(input_nik.value).replace(" ", "")
            # sinkronkan nilai parameter yang ditampilkan
            input_nik.value = nik_str
            
            # Cek apakah hanya berisi angka
            if not nik_str.isdigit():
                input_nik.setErrorMessage("NIK harus berisi angka saja")
            # Cek apakah panjangnya tepat 16
            elif len(nik_str) != 16:
                input_nik.setErrorMessage(f"NIK harus tepat 16 digit (saat ini: {len(nik_str)} digit)")
            else:
                input_nik.clearMessage()

        # Validasi format Nomor Berkas (project_id): harus seperti 01/2025/0020
        input_project = parameters[1]
        if input_project.value:
            pj_str = str(input_project.value).strip()
            input_project.value = pj_str

            # Pola: 2 digit / 4 digit (tahun) / 4 digit
            import re
            pattern = r"^\d{2}/\d{4}/\d{4}$"
            if not re.match(pattern, pj_str):
                input_project.setErrorMessage("Nomor Berkas harus berbentuk NN/YYYY/NNNN, contoh: 01/2025/0020")
            else:
                input_project.clearMessage()
        return   
    
    def execute(self, parameters, messages):
        username = str(parameters[0].valueAsText).replace(" ", "")
        project_id = str(parameters[1].valueAsText).replace(" ", "")
        tahun = parameters[2].valueAsText
        shapefile_path = parameters[3].valueAsText
        server = parameters[4].valueAsText if len(parameters) > 4 else None
        use_production = True if server == "Produksi" or server == None else False


        validate_document_type(project_id, target='Pembaruan NBT')
        main_upload_shapefile(project_id, username, "pembaruan_nbt_peta_rencana_lokasi_kegiatan", "Persiapan", "Zona_Layer", tahun, "NBT", shapefile_path, use_production)
        
        preferred_server = get_user_data('preferred_server')
        nik = get_user_data('nik')
        berkas = get_user_data('berkas')
        if nik != username:
            renew_user_data('nik', username)
        if berkas != project_id:
            renew_user_data('berkas', project_id)
        if len(parameters) > 4 and server != preferred_server:
            renew_user_data('preferred_server', server)

        return

class Upload_Peta_Lokasi_Kegiatan_Disepakati_AOI(object):
    def __init__(self):
        self.label = "Upload Peta Lokasi Kegiatan Disepakati (AOI)"
        self.description = ""
        self.canRunInBackground = False


    def getParameterInfo(self):
        self.is_gis_internal = is_internal()
        preferred_server = get_user_data('preferred_server')
        nik = get_user_data('nik')
        berkas = get_user_data('berkas')
        self.current_year = current_year()

        param0 = arcpy.Parameter(
            displayName="Nomor Induk Kependudukan (NIK)",
            name="username",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        if nik:
            param0.value = nik
        param1 = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="project_id",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        if berkas:
            param1.value = berkas
        param2 = arcpy.Parameter(
            displayName="Tahun",
            name="tahun",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")

        param3 = arcpy.Parameter(
            displayName="Shapefile Peta Lokasi Kegiatan Disepakati (.shp)",
            name="shapefile_path",
            datatype="DEFile",  
            parameterType="Required",
            direction="Input")
        
        param4 = arcpy.Parameter(
            displayName="Server Sipenta",
            name="link",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
               
        if self.current_year:
            param2.value = self.current_year

        if preferred_server:
            param4.value = preferred_server

        param4.filter.type = "ValueList"
        param4.filter.list = ["Produksi", "Belajar"]
        
        params = [param0, param1, param2, param3]
        # Periksa ulang status saat membuka parameter agar mengikuti login terbaru
        self.is_gis_internal = is_internal()
        if self.is_gis_internal:
            params.append(param4)
            return params
        else:
            return params
        
    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        input_nik = parameters[0]
        if input_nik.value:
            # Trim semua spasi (leading, trailing, dan di tengah)
            nik_str = str(input_nik.value).replace(" ", "")
            # sinkronkan nilai parameter yang ditampilkan
            input_nik.value = nik_str
            
            # Cek apakah hanya berisi angka
            if not nik_str.isdigit():
                input_nik.setErrorMessage("NIK harus berisi angka saja")
            # Cek apakah panjangnya tepat 16
            elif len(nik_str) != 16:
                input_nik.setErrorMessage(f"NIK harus tepat 16 digit (saat ini: {len(nik_str)} digit)")
            else:
                input_nik.clearMessage()

        # Validasi format Nomor Berkas (project_id): harus seperti 01/2025/0020
        input_project = parameters[1]
        if input_project.value:
            pj_str = str(input_project.value).strip()
            input_project.value = pj_str

            # Pola: 2 digit / 4 digit (tahun) / 4 digit
            import re
            pattern = r"^\d{2}/\d{4}/\d{4}$"
            if not re.match(pattern, pj_str):
                input_project.setErrorMessage("Nomor Berkas harus berbentuk NN/YYYY/NNNN, contoh: 01/2025/0020")
            else:
                input_project.clearMessage()
        return   
    
    def execute(self, parameters, messages):
        username = str(parameters[0].valueAsText).replace(" ", "")
        project_id = str(parameters[1].valueAsText).replace(" ", "")
        tahun = parameters[2].valueAsText
        shapefile_path = parameters[3].valueAsText
        server = parameters[4].valueAsText if len(parameters) > 4 else None
        use_production = True if server == "Produksi" or server == None else False


        validate_document_type(project_id, target='Pembaruan NBT')
        main_upload_shapefile(project_id, username, "pembaruan_nbt_peta_lokasi_kegiatan_yang_disepakati", "Persiapan", "Zona_Layer", tahun, "NBT", shapefile_path, use_production)
        
        preferred_server = get_user_data('preferred_server')
        nik = get_user_data('nik')
        berkas = get_user_data('berkas')
        if nik != username:
            renew_user_data('nik', username)
        if berkas != project_id:
            renew_user_data('berkas', project_id)
        if len(parameters) > 4 and server != preferred_server:
            renew_user_data('preferred_server', server)

        return

class Upload_Peta_Peta_Area_Kerja_AOI(object):
    def __init__(self):
        self.label = "Upload Peta Area Kerja (AOI)"
        self.description = ""
        self.canRunInBackground = False


    def getParameterInfo(self):
        self.is_gis_internal = is_internal()
        preferred_server = get_user_data('preferred_server')
        nik = get_user_data('nik')
        berkas = get_user_data('berkas')
        self.current_year = current_year()

        param0 = arcpy.Parameter(
            displayName="Nomor Induk Kependudukan (NIK)",
            name="username",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        if nik:
            param0.value = nik
        param1 = arcpy.Parameter(
            displayName="Nomor Berkas",
            name="project_id",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        if berkas:
            param1.value = berkas
        param2 = arcpy.Parameter(
            displayName="Tahun",
            name="tahun",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")

        param3 = arcpy.Parameter(
            displayName="Shapefile Peta Area Kerja (.shp)",
            name="shapefile_path",
            datatype="DEFile",  
            parameterType="Required",
            direction="Input")
        
        param4 = arcpy.Parameter(
            displayName="Server Sipenta",
            name="link",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
               
        if self.current_year:
            param2.value = self.current_year

        if preferred_server:
            param4.value = preferred_server

        param4.filter.type = "ValueList"
        param4.filter.list = ["Produksi", "Belajar"]
        
        params = [param0, param1, param2, param3]
        # Periksa ulang status saat membuka parameter agar mengikuti login terbaru
        self.is_gis_internal = is_internal()
        if self.is_gis_internal:
            params.append(param4)
            return params
        else:
            return params
        
    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        input_nik = parameters[0]
        if input_nik.value:
            # Trim semua spasi (leading, trailing, dan di tengah)
            nik_str = str(input_nik.value).replace(" ", "")
            # sinkronkan nilai parameter yang ditampilkan
            input_nik.value = nik_str
            
            # Cek apakah hanya berisi angka
            if not nik_str.isdigit():
                input_nik.setErrorMessage("NIK harus berisi angka saja")
            # Cek apakah panjangnya tepat 16
            elif len(nik_str) != 16:
                input_nik.setErrorMessage(f"NIK harus tepat 16 digit (saat ini: {len(nik_str)} digit)")
            else:
                input_nik.clearMessage()

        # Validasi format Nomor Berkas (project_id): harus seperti 01/2025/0020
        input_project = parameters[1]
        if input_project.value:
            pj_str = str(input_project.value).strip()
            input_project.value = pj_str

            # Pola: 2 digit / 4 digit (tahun) / 4 digit
            import re
            pattern = r"^\d{2}/\d{4}/\d{4}$"
            if not re.match(pattern, pj_str):
                input_project.setErrorMessage("Nomor Berkas harus berbentuk NN/YYYY/NNNN, contoh: 01/2025/0020")
            else:
                input_project.clearMessage()
        return   
    
    def execute(self, parameters, messages):
        username = str(parameters[0].valueAsText).replace(" ", "")
        project_id = str(parameters[1].valueAsText).replace(" ", "")
        tahun = parameters[2].valueAsText
        shapefile_path = parameters[3].valueAsText
        server = parameters[4].valueAsText if len(parameters) > 4 else None
        use_production = True if server == "Produksi" or server == None else False


        validate_document_type(project_id, target='Pembaruan NBT')
        main_upload_shapefile(project_id, username, "pembaruan_nbt_peta_area_kerja", "Persiapan", "Zona_Layer", tahun, "NBT", shapefile_path, use_production)
        
        preferred_server = get_user_data('preferred_server')
        nik = get_user_data('nik')
        berkas = get_user_data('berkas')
        if nik != username:
            renew_user_data('nik', username)
        if berkas != project_id:
            renew_user_data('berkas', project_id)
        if len(parameters) > 4 and server != preferred_server:
            renew_user_data('preferred_server', server)

        return

class Buat_Workspace_Pembaruan_NBT(object):
    def __init__(self):
        self.label = "Buat Workspace"
        self.description = ""
        self.canRunInBackground = False


    def getParameterInfo(self):
        self.is_gis_internal = is_internal()
        preferred_server = get_user_data('preferred_server')
        nik = get_user_data('nik')
        berkas = get_user_data('berkas')
        self.current_year = current_year()

        folder_path = arcpy.Parameter(
            displayName='Pilih Folder untuk Menyimpan Workspace Pembaruan NBT',
            name = 'folder_path',
            datatype='DEFolder',
            parameterType='Required',
            direction='Input'
        )
        file_persil = arcpy.Parameter(
            displayName="Shapefile Peta Area Kerja (.shp)",
            name="shapefile_path",
            datatype="DEFile",  
            parameterType="Required",
            direction="Input")
        
        return [folder_path, file_persil]
        
    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return   
    
    def execute(self, parameters, messages):
        folder_path = parameters[0].valueAsText
        persil_path = parameters[1].valueAsText

        project_config = os.path.join(folder_path, "project_config.json")
        gdbname = "NilaiBidangTanah.gdb"
        dataset = "nbt_ds"
        dataset_fasilitas = "fasilitas"
        dataset_resiko = "resiko"
        gdbtemplate = "ds_nbt_template"
        gdbtemplate_path = os.path.join(folder_path, "template.gdb", gdbtemplate)
        tbl = "template_var"
        tbltemplate_path = os.path.join(folder_path, "template.gdb", tbl)
        temporary = "temporary.gdb"
        temporary_path = os.path.join(folder_path, temporary)

        sisijalan = "SisiJalan"
        jaringanjalan = "Jaringan_Jalan"
        midpoint_jaringanjalan = "MidpointJaringanJalan"
        simbologi_lebarjalan = "SimbologiLebarJalan"
        simbologi_kelasjalan = "SimbologiKelasJalan"
        kelas_jalan = "kelasjalan,Lokal Setapak;1:Lokal Sekunder;2:Lokal Primer;3:Kolektor Sekunder;4:Kolektor Primer;5:Arteri Sekunder;6:Arteri Primer;7"
        topologi_sisijalan = "TopologiSisiJalan"
        topologi_jaringanjalan = "TopologiJaringanJalan"
        nd = "JaringanJalan_ND"
        jaringanjalannd = "JaringanJalanForND"

        persil = "Persil"
        persil_line = "PersilLine"
        persil_split = "PersilSplit"
        persil_centroid = "PersilCentroid"
        persil_split_midpoint = "PersilMidpoint"
        persil_zonasi = "zonasi,Pertanian;1:Industri;2:Perkampungan;3:Perumahan Sederhana;4:Perumahan Menengah;5:Perumahan Mewah;6:Komersil;7"
        persil_bentuk = "bentuk,Segi Banyak Tidak Beraturan;1:Segitiga;2:Segi Empat Tidak Beraturan;3:Segi Empat Beraturan;4"
        persil_letak = "letak,Lain-lain;1:Normal;2:Tusuk sate;3:Hook;4"

        gdb_path = os.path.join(folder_path, gdbname)
        dataset_path = os.path.join(gdb_path, dataset)
        dataset_fasilitas_path = os.path.join(gdb_path, dataset_fasilitas)
        dataset_resiko_path = os.path.join(gdb_path, dataset_resiko)
        sisijalan_path = os.path.join(dataset_path, sisijalan)
        jaringanjalan_path = os.path.join(dataset_path, jaringanjalan)
        midpoint_jaringanjalan_path = os.path.join(dataset_path, midpoint_jaringanjalan)
        # simbologi_lebarjalan_path = os.path.join(appdata, simbologi_lebarjalan + ".lyr")
        # simbologi_kelasjalan_path = os.path.join(appdata, simbologi_kelasjalan + ".lyr")
        topologi_sisijalan_path = os.path.join(dataset_path, topologi_sisijalan)
        topologi_jaringanjalan_path = os.path.join(dataset_path, topologi_jaringanjalan)
        nd_path = os.path.join(gdb_path, gdbtemplate, nd)
        jaringanjalannd_path = os.path.join(gdb_path, gdbtemplate, jaringanjalannd)

        persil_path = os.path.join(dataset_path, persil)
        persil_line_path = os.path.join(dataset_path, persil_line)
        persil_split_path = os.path.join(dataset_path, persil_split)
        persil_centroid_path = os.path.join(dataset_path, persil_centroid)
        persil_split_midpoint_path = os.path.join(dataset_path, persil_split_midpoint)
        

        return
