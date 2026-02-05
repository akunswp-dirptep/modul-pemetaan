# -*- coding: utf-8 -*-

import arcpy, os, zipfile, shutil, requests, sys
from ogisinternalutils import document
from ogisinternalutils.document import get_credentials as _get_creds_for_flag

arcpy.env.outputZFlag = "Disabled"  # Menonaktifkan output nilai Z (3D)
arcpy.env.outputMFlag = "Disabled"  # Menonaktifkan output nilai M (measure)


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "UploadZNTGabungan"
        self.alias = ""

        # List of tool classes associated with this toolbox
        self.tools = [Upload_ZNT_Gabungan]


class Upload_ZNT_Gabungan(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Upload ZNT Gabungan"
        self.description = ""
        self.canRunInBackground = False
        self.temp_folder_path = r'C:\PenilaianTanah\temp\UploadZNTGabungan'


    def getParameterInfo(self):
        """Define parameter definitions"""
        # 1. Input layer ZNT Lama
        znt_untuk_upload = arcpy.Parameter(
            displayName="Pilih SHP ZNT Gabungan",
            name="old_znt_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )

        input_link = arcpy.Parameter(
            displayName="Pilih Server Sipenta",
            name="server_link",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        input_link.filter.type = "ValueList"
        input_link.filter.list = ["Produksi", "Belajar"]

        penjelasan = arcpy.Parameter(
            displayName="Maaf, Anda tidak memiliki akses untuk menjalankan tools ini.",
            name="penjelasan",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )
        penjelasan.value = (
            "Tools ini hanya untuk Operator GIS Internal\n"
            "\n"
        )
        self.operatorGIS = bool(_get_creds_for_flag(credential_type="OperatorGISInternal", use_for_tools_validity=True))
        if self.operatorGIS:
            return [
                znt_untuk_upload,
                input_link
            ]
        else:
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
        
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        self.operatorGIS = bool(_get_creds_for_flag(credential_type="OperatorGISInternal", use_for_tools_validity=True))
        if not self.operatorGIS:
            arcpy.AddError("Anda tidak memiliki akses untuk menjalankan tools ini.")
            return
        znt_for_upload = parameters[0].valueAsText
        server_link = parameters[1].valueAsText
        use_production = True if server_link == "Produksi" else False
        data = document.get_credentials("OperatorGISInternal")
        self.nik = data['username']
        self.nomor_sk = data['password']
        self.berkas = data.get('berkas', None)
        self.token = data.get('token', None)
        self.kantor_id = data.get('kantor_id', None)
        self.coordinate_system = arcpy.Describe(znt_for_upload).spatialReference.factoryCode
        self.use_production = use_production

        zip_file = self.prepare_data_for_upload(znt_for_upload)
        if zip_file:
            self.upload_znt_gabungan(zip_file)

        return
    
    def prepare_data_for_upload(self, znt_layer):
        """
        Mempersiapkan data ZNT untuk upload dengan mengonversi ke shapefile (jika perlu) dan membuat zip.
        
        Parameter
        ---------
        znt_layer : str
            Path ke layer ZNT (bisa berupa shapefile atau feature class)
            
        Return
        ------
        str
            Path ke file zip yang siap diupload, atau None jika gagal
        """
        zipname = None
        
        try:
            # Bersihkan dan buat folder temporary
            if os.path.exists(self.temp_folder_path):
                shutil.rmtree(self.temp_folder_path)
            os.makedirs(self.temp_folder_path)
        except Exception as e:
            arcpy.AddError(f"Error creating temporary directory: {str(e)}")
            return None
        
        try:
            # Dapatkan deskripsi layer
            desc = arcpy.Describe(znt_layer)
            
            # Cek apakah ini shapefile atau feature class
            # Shapefile memiliki extension .shp di catalogPath
            is_shapefile = desc.catalogPath.lower().endswith('.shp')
            
            # Gunakan nama layer sebagai nama shapefile dan zip
            shp_base_name = desc.baseName
            
            if not is_shapefile:
                # Feature class - perlu dikonversi ke shapefile
                arcpy.AddMessage("Layer adalah feature class, mengkonversi ke shapefile...")
                
                shapefile_name = shp_base_name + ".shp"
                shapefile_path = os.path.join(self.temp_folder_path, shapefile_name)
                
                # Konversi feature class ke shapefile
                arcpy.conversion.FeatureClassToFeatureClass(
                    in_features=znt_layer,
                    out_path=self.temp_folder_path,
                    out_name=shapefile_name
                )
                arcpy.AddMessage(f"Feature class berhasil dikonversi ke: {shapefile_path}")
                
                # Set base path untuk komponen shapefile
                shapefile_base = os.path.join(self.temp_folder_path, shp_base_name)
                
            else:
                # Sudah shapefile - copy ke temp folder
                arcpy.AddMessage("Layer sudah berupa shapefile, menyalin file...")
                
                # Dapatkan path dan nama file shapefile
                shp_path = desc.catalogPath
                shp_name = desc.baseName
                shp_folder = desc.path
                
                # Copy semua komponen shapefile ke temp folder
                extensions = [".shp", ".shx", ".dbf", ".prj", ".cpg", ".shp.xml", ".sbn", ".sbx"]
                for ext in extensions:
                    src_file = os.path.join(shp_folder, shp_name + ext)
                    if os.path.exists(src_file):
                        dst_file = os.path.join(self.temp_folder_path, shp_name + ext)
                        shutil.copy2(src_file, dst_file)
                
                shapefile_base = os.path.join(self.temp_folder_path, shp_name)
            
            # Kumpulkan semua komponen shapefile
            extensions = [".shp", ".shx", ".dbf", ".prj", ".cpg", ".shp.xml", ".sbn", ".sbx"]
            shapefile_components = []
            for ext in extensions:
                file_path = shapefile_base + ext
                if os.path.exists(file_path):
                    shapefile_components.append(file_path)
            
            if not shapefile_components:
                arcpy.AddError("Komponen shapefile tidak ditemukan!")
                return None
            
            # Buat file zip dengan nama yang sama dengan shapefile
            arcpy.AddMessage("Membuat file zip...")
            zipname = os.path.join(self.temp_folder_path, shp_base_name + ".zip")
            
            with zipfile.ZipFile(zipname, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in shapefile_components:
                    file_name = os.path.basename(file_path)
                    zipf.write(file_path, file_name)
                    arcpy.AddMessage(f"  - Menambahkan: {file_name}")
            
            arcpy.AddMessage(f"File zip berhasil dibuat: {zipname}")
            return zipname
            
        except Exception as e:
            arcpy.AddError(f"Error saat mempersiapkan data: {str(e)}")
            return None
    
    def upload_znt_gabungan(self, zip_file_path):
        """
        Upload file ZNT gabungan ke server Sipenta.
        
        Parameter
        ---------
        zip_file_path : str
            Path ke file zip yang akan diupload
            
        Return
        ------
        dict
            Response dari server, atau None jika gagal
        """
        test_url = "https://belajar.atrbpn.go.id/sipenta/tatausaha/apis/uploadmerge"
        prod_url = "https://sipenta.atrbpn.go.id/tatausaha/apis/uploadmerge"

        url = prod_url if self.use_production else test_url
        
        try:
            # Siapkan headers dengan token
            headers = {
                'token': self.token
            }
            
            # Siapkan data form
            data = {
                'no_pemanfaatan': self.nomor_sk,
                'nik': self.nik,
                'epsgcode': str(self.coordinate_system)
            }
            
            # Siapkan file untuk upload
            with open(zip_file_path, 'rb') as zip_file:
                files = {
                    'file': (os.path.basename(zip_file_path), zip_file, 'application/zip')
                }

                # Kirim POST request
                response = requests.post(url, headers=headers, data=data, files=files)
                
                # Cek status response
                if response.status_code == 200:
                    result = response.json()
                    arcpy.AddMessage("Upload berhasil!")
                    return result
                else:
                    arcpy.AddError(f"Upload gagal: HTTP {response.status_code}")
                    arcpy.AddError(f"Response: {response.text}")
                    return None
                    
        except requests.exceptions.RequestException as e:
            arcpy.AddError(f"Error saat upload: {str(e)}")
            return None
        except Exception as e:
            arcpy.AddError(f"Error: {str(e)}")
            return None