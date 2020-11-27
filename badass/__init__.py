version = "0.8"

class tree (dict) :
    def __getattr__ (self, key) :
        return self.get(key, None)
    def __setattr__ (self, key, val) :
        if isinstance(val, dict) :
            val = self.__class__(val)
        self[key] = val
