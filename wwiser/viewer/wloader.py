import pkgutil

class _Loader(object):
    def __init__(self):
        pass

    def get_resource_text(self, path):
        try:
            return pkgutil.get_data(__name__, path).decode()
        except (FileNotFoundError, OSError): # as e
            return None

    def get_resource(self, path):
        try:
            return pkgutil.get_data(__name__, path)
        except (FileNotFoundError, OSError): # as e
            return None

Loader = _Loader()
