# -*- coding: latin-1 -*-

# 2011 - Dirección General Impositiva, Uruguay.
# Todos los derechos reservados.
# All rights reserved.

from framework.stage import Layer
class Intro:
    def __init__(self, stage, data, next_cb):
        self.next_cb = next_cb
        self.layer = Layer()
        self.stage = stage
        self.layer.add(stage.create_image(data.intro)[0])
        self.layer.add(stage.create_button(data.next, self)[0])

    def stop(self):
        self.stage.close_dialog(self.layer)

    def start(self):
        self.stage.show_dialog(self.layer, None)

    def handle_next(self, *args, **kwargs):
        self.stop()
        self.next_cb()
        self.next_cb = None
        self.layer.exit()
        self.stage = None
    