import marshal
import zlib
import pathlib
import types
from cryptography.fernet import Fernet

_KEY = b"YzSeNEwOM3ZmZas-KKp0YCfXyT4pAqI8V49bwO1UAq4="
_BASE = pathlib.Path(__file__).parent

def _load_loader():
    path = _BASE / "loader.enc"
    cipher = Fernet(_KEY)

    decrypted = cipher.decrypt(path.read_bytes())
    code = marshal.loads(zlib.decompress(decrypted))

    module = types.ModuleType("_loader")
    exec(code, module.__dict__)
    return module

_loader = _load_loader()

_modules = {}

for enc_file in _BASE.glob("*.enc"):

    if enc_file.name == "loader.enc":
        continue

    module = _loader.load_lib(_KEY, enc_file)
    _modules[enc_file.stem] = module

def __getattr__(name):

    if name in _modules:
        return _modules[name]

    for module in _modules.values():
        if hasattr(module, name):
            return getattr(module, name)

    raise AttributeError(name)
