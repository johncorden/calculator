class ScopeRecord():
    def __init__(self):
        self.scope_array = [1]
    
    def __iadd__(self, other):
        if len(self.scope_array) == 0:
            raise Exception("Empty Record")

        self.scope_array[-1] += 1
        return self
    
    def append(self, other):
        if type(other) is not int:
            raise Exception("Cannot append non int")

        self.scope_array.append(other)
    
    def __str__(self):
        return "-".join([str(i) for i in self.scope_array])
    
class ScopesList():
    def __init__(self):
        self.scopes = dict({"for": ScopeRecord(), "while": ScopeRecord(), "if": ScopeRecord(), "else": ScopeRecord(), "dowhile": ScopeRecord()})
    
    def __getitem__(self, key: str):
        if key not in self.scopes:
            raise Exception("Loop is not recognized")

        if type(key) != str:
            raise Exception("Key type needs to be str")

        return self.scopes[key]
    
    def __setitem__(self, key: str, value: ScopeRecord):
        self.scopes[key] = value