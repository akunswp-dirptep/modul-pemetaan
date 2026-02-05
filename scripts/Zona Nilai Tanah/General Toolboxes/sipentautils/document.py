import sys
import arcpy

def validateDocumentType(document_id, target):
    """
    Memvalidasi kecocokan antara nomor berkas (document_id) dengan jenis target pekerjaan (target).
    
    Fungsi ini memastikan bahwa setiap nomor berkas yang digunakan sesuai dengan 
    jenis kegiatan yang diizinkan berdasarkan dua digit pertama dari kode dokumen.
    
    Parameter
    ----------
    document_id : str
        Nomor berkas dokumen, dengan format seperti '01/2025/0021'.
        Dua digit pertama menunjukkan jenis kegiatan:
        - 01 → Pembuatan ZNT
        - 02 → Pembaruan ZNT
        - 03 → Pembuatan NBT
        - 04 → Pembaruan NBT

    target : str
        Jenis pekerjaan atau kegiatan yang sedang diproses, seperti:
        'Pembuatan ZNT', 'Pembaruan ZNT', 'Pembuatan NBT', atau 'Pembaruan NBT'.

    Return
    ------
    bool
        Mengembalikan True jika validasi berhasil (jenis dokumen sesuai dengan target).
        Jika tidak sesuai, fungsi akan menampilkan pesan error di ArcGIS (melalui arcpy.AddError)
        dan menghentikan eksekusi program menggunakan sys.exit(1).
    
    Contoh
    -------
    >>> validateDocumentType('01/2025/0021', 'Pembuatan ZNT')
    True
    >>> validateDocumentType('02/2025/0045', 'Pembuatan ZNT')
    # Akan menampilkan pesan error dan menghentikan program.
    """

    # Ekstrak bagian pertama (prefix) dari document_id, yaitu 2 digit pertama sebelum tanda '/'
    doc_prefix = document_id.split('/')[0]

    # Validasi untuk dokumen dengan awalan 01 → hanya valid untuk Pembuatan ZNT
    if doc_prefix == '01':
        if target != 'Pembuatan ZNT':
            arcpy.AddError('ERROR: Nomor berkas ini dikhususkan untuk Pembuatan ZNT')
            sys.exit(1)
        return True

    # Validasi untuk dokumen dengan awalan 02 → hanya valid untuk Pembaruan ZNT
    elif doc_prefix == '02':
        if target != 'Pembaruan ZNT':
            arcpy.AddError('ERROR: Nomor berkas ini dikhususkan untuk Pembaruan ZNT')
            sys.exit(1)
        return True

    # Validasi untuk dokumen dengan awalan 03 → hanya valid untuk Pembuatan NBT
    elif doc_prefix == '03':
        if target != 'Pembuatan NBT':
            arcpy.AddError('ERROR: Nomor berkas ini dikhususkan untuk Pembuatan NBT')
            sys.exit(1)
        return True

    # Validasi untuk dokumen dengan awalan 04 → hanya valid untuk Pembaruan NBT
    elif doc_prefix == '04':
        if target != 'Pembaruan NBT':
            arcpy.AddError('ERROR: Nomor berkas ini dikhususkan untuk Pembaruan NBT')
            sys.exit(1)
        return True

    # Jika nomor berkas tidak diawali dengan 01, 02, 03, atau 04 → anggap tidak valid
    else:
        arcpy.AddError('ERROR: Nomor berkas tidak dikenal')
        arcpy.AddError('Format nomor berkas yang valid: 01/2025/0021')
        sys.exit(1)

def get_credentials(credential_type):
    """
    Membaca file credential.json untuk mendapatkan username dan password berdasarkan tipe credential.

    File credential.json diharapkan berada di direktori Menu dengan format:
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
    import json
    import os

    script_dir = os.path.dirname(os.path.abspath(__file__))
    credential_path = os.path.join(os.path.join(os.path.dirname(os.path.dirname(script_dir)), 'Menu'), 'credential.json')

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
                    
                    return result
            
            # Jika credential type tidak ditemukan
            arcpy.AddError(f"Credential dengan type '{credential_type}' tidak ditemukan dalam credential.json")
            sys.exit(1)
            
    except FileNotFoundError:
        arcpy.AddError(f"File credential.json tidak ditemukan di {credential_path}")
        sys.exit(1)
    except json.JSONDecodeError:
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
    import json
    import os
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    credential_path = os.path.join(os.path.join(os.path.dirname(os.path.dirname(script_dir)), 'Menu'), 'credential.json')
    
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

