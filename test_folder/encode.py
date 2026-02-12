import marshal
import zlib
from cryptography.fernet import Fernet
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
cipher = Fernet(key)

with open("hitung.py", "r", encoding="utf-8") as f:
    source = f.read()

code_obj = compile(source, "mylib", "exec")
bytecode = marshal.dumps(code_obj)

compressed = zlib.compress(bytecode)
encrypted = cipher.encrypt(compressed)

with open("encode_lib/mylib.enc", "wb") as f:
    f.write(encrypted)

print("KEY:", key.decode())
