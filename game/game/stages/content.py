# -*- coding: latin-1 -*-

# 2011 - Dirección General Impositiva, Uruguay.
# Todos los derechos reservados.
# All rights reserved.


from framework.stage import  Layer
from gamestage import GameStage
from pagination import Paginator
from yaml import load
from utils import DictClass

class Content():
    def __init__(self, stage, title, text):
        self.layer = Layer()
        self.stage = stage
        data = DictClass(load(file('data/common/content_viewer.yaml')))
        title_item = self.title_text = stage.create_text(data.title)[0]
        title_item.set_top(data.container.top)
        self.title_text.set_text(title)
        text_top = title_item.get_top() + title_item.get_height() + 10
        text_height = data.container.height - (text_top - data.container.top) 
        self.close = stage.create_button(data.close, self)[0]
        self.__load_items(text, data, text_top, text_height)
        self.paginator = Paginator(self.stage, self.items, data.get("pagination", None))
        for item in self.stage.create_items_from_yaml(data.other):
            self.layer.add(item)
        self.layer.add(self.title_text)
        self.layer.add(self.close)

    def __load_items(self, text, data, top, height):
        self.items = []
        def create_text(stage, next, text, top, height):
            text_item = stage.create_text(data.text)[0]
            text_item.break_text_into(next)
            text_item.set_text(text)
            text_item.set_top(top)
            text_item.set_dimensions(data.text.width, height)
            text_item.break_text_into(None)
            return text_item
        # Usamos una clase que tiene el metodo set_text para saber si hay que dividir el texto
        class Next:
            def __init__(self):
                self.text = None
            def set_text(self, text):
                self.text = text
        next = Next()
        layer = Layer()
        layer.add(create_text(self.stage, next, text, top, height))
        self.items.append(layer)
        while next.text:
            layer = Layer()
            layer.add(create_text(self.stage, next, next.text, top, height))
            self.items.append(layer)

    def handle_close(self, item, args):
        self.stop()

    def stop(self):
        for layer in self.paginator.get_layers():
            self.stage.remove_layer(layer)
        self.stage.close_dialog(self.layer)

    def start(self):
        self.stage.show_dialog(self.layer, None)
        for layer in self.paginator.get_layers():
            self.stage.add_layer(layer)

class TestContent(GameStage):
    
    def initialize(self):
        GameStage.initialize(self)
        self.paginate = Content(self, "titulo", 
        """Sed ut perspiciatis unde 
omnis iste natus error sit voluptatem accusantium doloremque laudantium,
totam rem aperiam, eaque ipsa quae ab illo inventore veritatis et quasi
architecto beatae vitae dicta sunt explicabo.
Nemo enim ipsam voluptatem quia voluptas sit aspernatur aut odit aut fugit,
sed quia consequuntur magni dolores eos qui ratione voluptatem sequi
nesciunt. Neque porro quisquam est, qui dolorem ipsum quia dolor sit amet,
consectetur, adipisci velit, sed quia non numquam eius modi tempora
incidunt ut labore et dolore magnam aliquam quaerat voluptatem. Ut enim
ad minima veniam, quis nostrum exercitationem ullam corporis suscipit
laboriosam, nisi ut aliquid ex ea commodi consequatur? Quis autem vel eum
iure reprehenderit qui in ea voluptate velit esse quam nihil molestiae
consequatur, vel illum qui dolorem eum fugiat quo voluptas nulla
pariatur?""")

    def prepare(self):
        self.paginate.start()
        