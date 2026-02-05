import arcpy, os, requests, sys
from ogisinternalutils.document import get_credentials, setup_credentials, remove_credentials


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Login OGIS Internal"
        self.alias = ""

        # List of tool classes associated with this toolbox
        self.tools = [Login_OGIS_Internal, Logout_OGIS_Internal]


class Login_OGIS_Internal(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Login OGIS Internal"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        input_nik = arcpy.Parameter(
            displayName="Nomor Induk Kependudukan (NIK)",
            name="username",
            datatype="GPString",
            parameterType="Required",
            direction="Input")

        input_kata_sandi = arcpy.Parameter(
            displayName="Kata Sandi",
            name="password",
            datatype="GPStringHidden",
            parameterType="Required",
            direction="Input")
        
        input_link = arcpy.Parameter(
            displayName="Pilih Server Sipenta",
            name="server_link",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        input_link.filter.type = "ValueList"
        input_link.filter.list = ["Produksi", "Belajar"]
        

        return [
                input_nik,
                input_kata_sandi,
                input_link
            ]

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
        # Validasi NIK harus 16 angka
        if len(parameters) > 1:
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
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        # Trim semua spasi dari NIK sebelum digunakan
        self.operatorGIS = bool(get_credentials(credential_type="OperatorGISInternal", use_for_tools_validity=True))
        if not self.operatorGIS:
            nik = parameters[0].valueAsText.replace(" ", "") if parameters[0].valueAsText else None
            kata_sandi = parameters[1].valueAsText
            server_link = parameters[2].valueAsText

            arcpy.AddMessage("Memproses login...")

            use_production = True if server_link == "Produksi" else False
            self.nik = nik
            self.nomor_sk = kata_sandi
            self.use_production = use_production

            arcpy.AddMessage(f"Server yang dipilih: {'Produksi' if use_production else 'Belajar'}")

            self.login_user()
            succes_login = setup_credentials("OperatorGISInternal", self.nik, self.nomor_sk, self.token, self.berkas, self.kantor_id)
            # Reload all Python toolboxes after successful login
            all_toolboxes_folder_need_reload = [
                r"C:\PenilaianTanah\scripts\Zona Nilai Tanah\Python Toolboxes",
                r"C:\PenilaianTanah\scripts\Tools OGIS Internal\Python Toolboxes"
            ]

            try:
                if succes_login:
                    for folder in all_toolboxes_folder_need_reload:
                        self.reload_all_toolboxes_in_folder(folder)
                else:
                    arcpy.AddWarning("Gagal login. Silakan coba lagi.")
            except Exception as e:
                arcpy.AddWarning(f"Gagal memuat ulang toolbox: {str(e)}")
        else:

            arcpy.AddWarning(f"Anda sudah login sebagai OGIS Internal")
 

        return

    def login_user(self):

        test_url = "https://belajar.atrbpn.go.id/sipenta/tatausaha/apis/loginogis"
        prod_url = "https://sipenta.atrbpn.go.id/tatausaha/apis/loginogis"

        url = prod_url if self.use_production else test_url

        # Siapkan data untuk body request
        data = {
            "username": self.nik,
            "password": self.nomor_sk
        }
        
        try:
            # Kirim POST request dengan JSON body
            response = requests.post(url, json=data, headers={'Content-Type': 'application/json'})
            
            # Cek status code
            if response.status_code == 200:
                result = response.json()              
                self.token = result['token']
                self.berkas = result['data']
                self.kantor_id = result['kantor_id']
                return result
             
            else:
                arcpy.AddError(f"Login gagal: HTTP {response.status_code} - {response.text}")
                sys.exit(1)
                    
        except requests.exceptions.RequestException as e:
            arcpy.AddError(f"Error saat melakukan request: {str(e)}")
            sys.exit(1)
        except Exception as e:
            arcpy.AddError(f"Error: {str(e)}")
            sys.exit(1)

    def reload_all_toolboxes_in_folder(self, toolbox_folder):
        """Refresh dan reload semua Python toolboxes (.pyt) dari folder ke dalam ArcGIS Pro project."""
        
        if not os.path.exists(toolbox_folder):
            arcpy.AddError(f"Folder toolbox tidak ditemukan: {toolbox_folder}")
            return
        
        # Cari semua file .pyt di folder
        pyt_files = [f for f in os.listdir(toolbox_folder) if f.endswith('.pyt')]
        
        if not pyt_files:
            arcpy.AddWarning(f"Tidak ada file .pyt ditemukan di {toolbox_folder}")
            return
        
        # Refresh katalog
        try:
            arcpy.management.RefreshCatalog(toolbox_folder)
        except Exception:
            try:
                arcpy.RefreshCatalog(toolbox_folder)
            except Exception:
                pass
        
        # Load toolbox di proyek saat ini
        try:
            # Hapus dan reload menggunakan ImportToolbox (lebih reliable)
            for pyt_file in pyt_files:
                pyt_path = os.path.join(toolbox_folder, pyt_file)
                try:
                    arcpy.ImportToolbox(pyt_path)
                    arcpy.AddMessage(f"✓ Berhasil memuat: {pyt_file}")
                except Exception as e:
                    arcpy.AddWarning(f"✗ Gagal memuat {pyt_file}: {str(e)}")
            
            arcpy.AddMessage(f"Selesai: semua toolbox telah di-reload")
            
        except Exception as e:
            arcpy.AddWarning(f"Error saat reload toolbox: {str(e)}")

class Logout_OGIS_Internal(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Logout OGIS Internal"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        self.login_data = get_credentials(credential_type="OperatorGISInternal", get_data_for_preview=True)        
        penjelasan = arcpy.Parameter(
            displayName="Anda sudah login",
            name="penjelasan",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )
        if self.login_data:
            berkas_list = ""
            for data in self.login_data['berkas']:
                berkas_list += f"- {data['no_berkas']}\n"

            penjelasan.value = (
                f"Anda saat ini masuk sebagai pengguna internal OGIS\n"
                "dengan hak akses terhadap:\n"
                f"{self.login_data['id_penggabungan']}\n"
                "Anda memiliki akses ke berkas-berkas berikut:\n"
                f"{berkas_list}\n"
                "Gunakan tools ini untuk logout"
                "\n----------------------------------------------\n"
                "Dikembangkan oleh:\n"
                "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
                "Kementerian ATR/BPN.\n"
            )
        else:       
            penjelasan.value = (
                "Anda belum login sebagai OGIS Internal.\n"
                "Tools ini hanya untuk logout"
                "\n----------------------------------------------\n"
                "Dikembangkan oleh:\n"
                "Direktorat Penilaian Tanah dan Ekonomi Pertanahan,\n"
                "Kementerian ATR/BPN.\n"
            )
        

        return [penjelasan]


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
        # Validasi NIK harus 16 angka

        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        # Trim semua spasi dari NIK sebelum digunakan
        self.operatorGIS = bool(get_credentials(credential_type="OperatorGISInternal", use_for_tools_validity=True))
        if self.operatorGIS:
            success_logout = remove_credentials("OperatorGISInternal")
            # Reload all Python toolboxes after successful login
            all_toolboxes_folder_need_reload = [
                r"C:\PenilaianTanah\scripts\Zona Nilai Tanah\Python Toolboxes",
                r"C:\PenilaianTanah\scripts\Tools OGIS Internal\Python Toolboxes"
            ]
            try:
                if success_logout:
                    for folder in all_toolboxes_folder_need_reload:
                        self.reload_all_toolboxes_in_folder(folder)
                else: 
                    arcpy.AddWarning("Gagal logout. Silakan coba lagi.")
            except Exception as e:
                arcpy.AddWarning(f"Gagal memuat ulang toolbox: {str(e)}")
        else:
            arcpy.AddWarning(f"Anda belum login sebagai OGIS Internal")
 

        return

    def reload_all_toolboxes_in_folder(self, toolbox_folder):
        """Refresh dan reload semua Python toolboxes (.pyt) dari folder ke dalam ArcGIS Pro project."""
        
        if not os.path.exists(toolbox_folder):
            arcpy.AddError(f"Folder toolbox tidak ditemukan: {toolbox_folder}")
            return
        
        # Cari semua file .pyt di folder
        pyt_files = [f for f in os.listdir(toolbox_folder) if f.endswith('.pyt')]
        
        if not pyt_files:
            arcpy.AddWarning(f"Tidak ada file .pyt ditemukan di {toolbox_folder}")
            return
        
        # Refresh katalog
        try:
            arcpy.management.RefreshCatalog(toolbox_folder)
        except Exception:
            try:
                arcpy.RefreshCatalog(toolbox_folder)
            except Exception:
                pass
        
        # Load toolbox di proyek saat ini
        try:
            # Hapus dan reload menggunakan ImportToolbox (lebih reliable)
            for pyt_file in pyt_files:
                pyt_path = os.path.join(toolbox_folder, pyt_file)
                try:
                    arcpy.ImportToolbox(pyt_path)
                    arcpy.AddMessage(f"✓ Berhasil memuat: {pyt_file}")
                except Exception as e:
                    arcpy.AddWarning(f"✗ Gagal memuat {pyt_file}: {str(e)}")
            
            arcpy.AddMessage(f"Selesai: semua toolbox telah di-reload")
            
        except Exception as e:
            arcpy.AddWarning(f"Error saat reload toolbox: {str(e)}")
