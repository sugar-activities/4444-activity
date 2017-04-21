# -*- coding: latin-1 -*-

# 2011 - Dirección General Impositiva, Uruguay.
# Todos los derechos reservados.
# All rights reserved.

class Datamodel:

    def __init__(self):
        self.current_map_index = None
        self.map_character_left = None
        self.map_character_top = None
        self.character = "male"
        self.level = 1
        self.unlocked_level = 1
        self.backpack = [set() for x in range(0, 4)]
        