class Union(object):
    def __init__(self, res):
        self.res = res

    def search(self, data):
        for re in self.res:
            if re.search(data): return True
        return False

    def __repr__(self):
        return "<Union \n " + "\n ".join(map(repr, self.res)) + ">"

class Inter(object):
    def __init__(self, res):
        self.res = res

    def search(self, data):
        for re in self.res:
            if not re.search(data): return False
        return True

    def __repr__(self):
        return "<Inter \n " + "\n ".join(map(repr, self.res)) + ">"

class Neg(object):
    def __init__(self, re):
        self.re = re

    def search(self, data):
        return not self.re.search(data)

    def __repr__(self):
        return "<Neg " + repr(self.re) + ">"

class Tag(object):
    def __init__(self, names, res):
        self.names = names
        self.res = res
        if not isinstance(self.res, list): self.res = [self.res]

    def search(self, data):
        for name in self.names:
            for re in self.res:
                if re.search(data.get(name, "")): return True
        return False

    def __repr__(self):
        return ("<Tag names=(" + ",".join(self.names) + ") \n " +
                "\n ".join(map(repr, self.res)) + ">")
