import sys
import arcpy

def validateDocumentType(document_id, target):
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