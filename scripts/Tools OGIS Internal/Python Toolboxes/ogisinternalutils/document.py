import sys, os
import arcpy
import json

def validate_document_type(document_id, target):
    # Ekstrak bagian pertama dari document_id (2 digit pertama)
    doc_prefix = document_id.split('/')[0]
    
    # Validasi untuk dokumen dengan awalan 01
    if doc_prefix == '01':
        if target != 'Pembuatan ZNT':
            arcpy.AddError('ERROR: Nomor berkas ini dikhususkan untuk Pembuatan ZNT')
            sys.exit(1)
        return True
    
    # Validasi untuk dokumen dengan awalan 02
    elif doc_prefix == '02':
        if target != 'Pembaruan ZNT':
            arcpy.AddError('ERROR: Nomor berkas ini dikhususkan untuk Pembaruan ZNT')
            sys.exit(1)
        return True
    
    # Validasi untuk dokumen dengan awalan 03
    elif doc_prefix == '03':
        if target != 'Pembuatan NBT':
            arcpy.AddError('ERROR: Nomor berkas ini dikhususkan untuk Pembuatan NBT')
            sys.exit(1)
        return True
    
    # Validasi untuk dokumen dengan awalan 04
    elif doc_prefix == '04':
        if target != 'Pembaruan NBT':
            arcpy.AddError('ERROR: Nomor berkas ini dikhususkan untuk Pembaruan NBT')
            sys.exit(1)
        return True
    
    # Handle nomor berkas yang tidak dikenal
    else:
        arcpy.AddError('ERROR: Nomor berkas tidak dikenal')
        arcpy.AddError('Format nomor berkas yang valid: 01/2025/0021')
        sys.exit(1)

def validate_coordinate_system(shapefile_path):
    desc = arcpy.Describe(shapefile_path)
    spatial_ref = desc.spatialReference
    if not spatial_ref.name.startswith('DGN_1995_Indonesia_TM-3_Zone'):
        arcpy.AddError( f"Proyeksi tidak sesuai: {spatial_ref.name}")
        arcpy.AddError( "Proyeksi harus DGN_1995_Indonesia_TM-3 ")
    else: arcpy.AddMessage('Proyeksi Sesuai')

def get_credentials(credential_type = "OperatorGISInternal", use_for_tools_validity=False, get_data_for_preview=False):
    """
    Membaca file credential.json untuk mendapatkan username dan password berdasarkan tipe credential.

    File credential.json diharapkan berada di direktori config dengan format:
    {
        "credentials": [{
            "type": "OperatorGISInternal",
            "username": "your_username",
            "password": "your_password",
            "token_url": "https://example.com/oauth2/token"
        }]
    }

    Parameter
    ---------
    credential_type : str, optional
        Tipe credential yang ingin diambil (default: "OperatorGISInternal").

    Return
    ------
    dict
        Mengembalikan dictionary berisi credential information:
        {
            'username': str,
            'password': str,
            'token_url': str (optional)
        }
    
    Contoh
    -------
    >>> getCredentials()
    {'username': 'user_example', 'password': 'pass_example', 'token_url': 'https://...'}
    >>> getCredentials("OperatorGISInternal")
    {'username': 'user_example', 'password': 'pass_example', 'token_url': 'https://...'}
    """

    credential_path = r'C:\PenilaianTanah\config\credential.json'

    try:
        with open(credential_path, 'r') as cred_file:
            data = json.load(cred_file)
            credentials_list = data.get('credentials', [])
            
            # Cari credential berdasarkan type
            for cred in credentials_list:
                if cred.get('type') == credential_type:
                    result = {
                        'username': cred.get('username'),
                        'password': cred.get('password'),
                        'token' : cred.get('token'),
                    }
                    # Tambahkan token jika ada
                    if 'berkas' in cred:
                        result['berkas'] = cred.get('berkas')
                    if 'kantor_id' in cred:
                        result['kantor_id'] = cred.get('kantor_id')
                    if use_for_tools_validity:
                        return True
                    elif get_data_for_preview:
                        return {
                            'username': cred.get('username'),
                            'id_penggabungan': cred.get('password'),
                            'berkas': cred.get('berkas', None),
                        }
                    else: 
                        return result
            
            # Jika credential type tidak ditemukan
            if use_for_tools_validity or get_data_for_preview:
                return False
            else:
                arcpy.AddError(f"Credential dengan tipe '{credential_type}' tidak ditemukan dalam credential.json")
                sys.exit(1)
            
    except FileNotFoundError:
        if use_for_tools_validity or get_data_for_preview:
                return False
        else:
            arcpy.AddError(f"File credential.json tidak ditemukan. Pastikan ada di folder config atau set variabel lingkungan CREDENTIAL_JSON_PATH.")
            sys.exit(1)
    except json.JSONDecodeError:
        if use_for_tools_validity or get_data_for_preview:
                return False
        else:
            arcpy.AddError("Gagal membaca file credential.json. Pastikan formatnya benar.")
            sys.exit(1)

def setup_credentials(credential_type, username, password, token, berkas=None, kantor_id=None):
    """
    Menyimpan atau memperbarui credentials dalam file credential.json.
    
    Fungsi ini akan:
    1. Membuat file credential.json jika belum ada
    2. Memperbarui credential yang sudah ada berdasarkan type
    3. Menambahkan credential baru jika type belum ada
    
    Parameter
    ---------
    credential_type : str
        Tipe credential (contoh: "OperatorGISInternal")
    username : str
        Username untuk credential
    password : str
        Password untuk credential
    token : str
        Token untuk credential
        
    Return
    ------
    bool
        True jika berhasil menyimpan/memperbarui credentials
    """

    
    credential_path = r'C:\PenilaianTanah\config\credential.json'
    # Data credential baru yang akan disimpan
    new_credential = {
        "type": credential_type,
        "username": username,
        "password": password,
        "token": token
    }
    if credential_type == "OperatorGISInternal":
        if berkas is not None:
            new_credential["berkas"] = berkas
        if kantor_id is not None:
            new_credential["kantor_id"] = kantor_id
    try:
        # Cek apakah file ada
        if os.path.exists(credential_path):
            # File ada, baca isinya
            try:
                with open(credential_path, 'r') as cred_file:
                    data = json.load(cred_file)
                    
                # Validasi format JSON
                if 'credentials' not in data or not isinstance(data['credentials'], list):
                    # Format tidak sesuai, buat struktur baru
                    data = {"credentials": []}
                    
            except json.JSONDecodeError:
                # File rusak/tidak valid, buat struktur baru
                arcpy.AddWarning("File credential.json rusak, membuat struktur baru...")
                data = {"credentials": []}
        else:
            # File belum ada, buat struktur baru
            # Pastikan direktori Menu ada
            menu_dir = os.path.dirname(credential_path)
            if not os.path.exists(menu_dir):
                os.makedirs(menu_dir)
            
            data = {"credentials": []}
        
        # Cari apakah credential type sudah ada
        credential_found = False
        for i, cred in enumerate(data['credentials']):
            if cred.get('type') == credential_type:
                # Update credential yang sudah ada
                data['credentials'][i] = new_credential
                credential_found = True
                arcpy.AddMessage(f"Credential type '{credential_type}' berhasil diperbarui")
                break
        
        # Jika belum ada, tambahkan credential baru
        if not credential_found:
            data['credentials'].append(new_credential)
            arcpy.AddMessage(f"Credential type '{credential_type}' berhasil ditambahkan")
        
        # Simpan kembali ke file
        with open(credential_path, 'w') as cred_file:
            json.dump(data, cred_file, indent=4)
        
        return True
        
    except Exception as e:
        arcpy.AddError(f"Gagal menyimpan credentials: {str(e)}")
        return False

def remove_credentials(credential_type):
    """
    Menghapus credentials dari file credential.json berdasarkan type.
    
    Parameter
    ---------
    credential_type : str
        Tipe credential yang akan dihapus (contoh: "OperatorGISInternal")
        
    Return
    ------
    bool
        True jika berhasil menghapus credentials, False jika tidak ditemukan atau error
    """    
    credential_path = r'C:\PenilaianTanah\config\credential.json'
    
    try:
        # Cek apakah file ada
        if not os.path.exists(credential_path):
            arcpy.AddWarning(f"File credential.json tidak ditemukan di {credential_path}")
            return False
        
        # Baca file credential.json
        with open(credential_path, 'r') as cred_file:
            data = json.load(cred_file)
        
        # Validasi format JSON
        if 'credentials' not in data or not isinstance(data['credentials'], list):
            arcpy.AddWarning("Format credential.json tidak sesuai")
            return False
        
        # Cari dan hapus credential berdasarkan type
        credential_found = False
        for i, cred in enumerate(data['credentials']):
            if cred.get('type') == credential_type:
                # Hapus credential
                data['credentials'].pop(i)
                credential_found = True
                break
        
        if not credential_found:
            arcpy.AddWarning(f"Credential dengan tipe '{credential_type}' tidak ditemukan")
            return False
        
        # Simpan kembali ke file setelah penghapusan
        with open(credential_path, 'w') as cred_file:
            json.dump(data, cred_file, indent=4)
        
        arcpy.AddMessage(f"Credential type '{credential_type}' berhasil dihapus")
        return True
        
    except json.JSONDecodeError:
        arcpy.AddError("Gagal membaca file credential.json. Pastikan formatnya benar.")
        return False
    except Exception as e:
        arcpy.AddError(f"Gagal menghapus credentials: {str(e)}")
        return False

