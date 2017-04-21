# -*- coding: latin-1 -*-

# 2011 - Dirección General Impositiva, Uruguay.
# Todos los derechos reservados.
# All rights reserved.

class DictClass(dict):
    def __init__(self, data={}):
        def convert(value):
            if isinstance(value, dict):
                return DictClass(value)
            if isinstance(value, list):
                return [DictClass(v) if isinstance(v, dict) else v for v in value]
            return value
        res = dict(map(lambda (k, v): (k, convert(v)), data.iteritems()))
        dict.__init__(self, res)        
        
    def __getattr__(self, name):
        return self[name]
    
    def deep_update(self, other):
        for (k, v) in other.items():
            if isinstance(v, dict) and k in self:
                self[k].deep_update(v)
            else:
                self[k] = v