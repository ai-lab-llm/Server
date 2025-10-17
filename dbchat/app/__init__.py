import sys, importlib
sys.modules.setdefault("app", importlib.import_module("dbchat.app"))