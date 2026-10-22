import sys
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

def get_credentials(credential_type = "OperatorGISInternal", use_for_tools_validity=False):
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
                    else: 
                        return result
            
            # Jika credential type tidak ditemukan
            if use_for_tools_validity:
                return False
            else:
                arcpy.AddError(f"Credential dengan tipe '{credential_type}' tidak ditemukan dalam credential.json")
                sys.exit(1)
            
    except FileNotFoundError:
        if use_for_tools_validity:
                return False
        else:
            arcpy.AddError(f"File credential.json tidak ditemukan. Pastikan ada di folder config atau set variabel lingkungan CREDENTIAL_JSON_PATH.")
            sys.exit(1)
    except json.JSONDecodeError:
        if use_for_tools_validity:
                return False
        else:
            arcpy.AddError("Gagal membaca file credential.json. Pastikan formatnya benar.")
            sys.exit(1)

