class DummyPin:
    IN = OUT = PULL_UP = 0
    def __init__(self, *a, **k): self._v = 0
    def value(self, v=None):
        if v is None: return self._v
        self._v = v

class DummyADC:
    ATTN_11DB = 0
    def __init__(self, *a): self._val = 2048
    def atten(self, *_): pass
    def read(self): return self._val

class DummyHX711:
    def __init__(self, *a): pass
    def read(self): return 355.0     # fixed g for tests
