import marshal
import zlib
from cryptography.fernet import Fernet
import pathlib
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64


password = 'bpnri-jakarta'
salt = b'static_salt_12345'  # Untuk production, gunakan salt yang unik

# Derive proper key dari password
kdf = PBKDF2HMAC(
    algorithm=hashes.SHA256(),
    length=32,
    salt=salt,
    iterations=100000,
)
key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
BASE = pathlib.Path(".")

cipher = Fernet(key)

print("\nSIMPAN KEY INI:\n")
print(key.decode())
print("\n=============================\n")

# =====================================
# Encrypt semua *_plain.py
# =====================================

for plain_file in BASE.glob("*_plain.py"):

    module_name = plain_file.stem.replace("_plain", "")
    enc_name = f"{module_name}.enc"

    print(f"Encrypting {plain_file.name} → {enc_name}")

    source = plain_file.read_text(encoding="utf-8")

    code_obj = compile(source, module_name, "exec")
    bytecode = marshal.dumps(code_obj)

    encrypted = cipher.encrypt(zlib.compress(bytecode))

    out_path = BASE / "encode_lib" / enc_name
    out_path.write_bytes(encrypted)

# =====================================
# Loader Plain (GENERIC)
# =====================================

loader_code = """
import marshal, zlib, types
from cryptography.fernet import Fernet

def load_lib(key, path):
    cipher = Fernet(key)

    data = cipher.decrypt(path.read_bytes())
    code = marshal.loads(zlib.decompress(data))

    module = types.ModuleType(path.stem)
    exec(code, module.__dict__)
    return module
"""

print("\nEncrypting loader → loader.enc")

code_obj = compile(loader_code, "loader", "exec")
bytecode = marshal.dumps(code_obj)

encrypted_loader = cipher.encrypt(zlib.compress(bytecode))

(BASE / "encode_lib" / "loader.enc").write_bytes(encrypted_loader)

print("\nDONE 🔥")
