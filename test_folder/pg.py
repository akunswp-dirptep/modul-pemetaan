import pathlib
BASE = pathlib.Path(".")
print(list(BASE.glob("*.py")))
print(BASE)