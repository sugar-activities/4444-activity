# -*- coding: latin-1 -*-

# 2011 - Dirección General Impositiva, Uruguay.
# Todos los derechos reservados.
# All rights reserved.

from framework.stage import assets, Layer, ItemEvent, ItemImage, ItemText
from yaml import load
from utils import DictClass

class Game():
    def __init__(self, stage, layer, data, footer):
        self.stage = stage
        self.layer = layer
        self.footer = footer
        self.name = data.name
        data['action'] = 'click'
        self.item = stage.create_button(data, manager=self)[0]
        if data.level <= stage.game.datastore.datamodel.unlocked_level - 1:
            index = data.clazz.rfind('.')
            if (index > 1):
                self.clazz = getattr(__import__(data.clazz[:index], globals(), locals(), data.clazz[index+1:]), data.clazz[index+1:])
            else:
                self.clazz = globals()[data.clazz]
            self.item.add_event_handler(ItemEvent.MOUSE_ENTER, self.handle_mouse_enter)
            self.item.add_event_handler(ItemEvent.MOUSE_LEAVE, self.handle_mouse_leave)
            self.item.turn_on()
        self.layer.add(self.item)

    def handle_mouse_enter(self, items, args):
        self.footer.set_text(self.name)
        self.layer.add(self.footer)
        
    def handle_mouse_leave(self, items, args):
        self.layer.remove(self.footer)
        
    def handle_click(self, items, args):
        self.stage.game.datastore.datamodel.current_map_index = self.stage.current_map_index
        self.stage.game.datastore.datamodel.map_character_left = self.stage.map_character.item.get_left()
        self.stage.game.datastore.datamodel.map_character_top = self.stage.map_character.item.get_top()
        self.stage.game.set_stage(self.clazz(self.stage.game))

class GamesViewer():
    def __init__(self, stage):
        self.layer = Layer()
        self.stage = stage
        data = DictClass(load(file('data/common/games_viewer.yaml')))
        for item in stage.create_items_from_yaml(data.other):
            self.layer.add(item)
        self.close = stage.create_button(data.close, self)[0]
        self.layer.add(self.close)
        quantity = stage.game.datastore.datamodel.unlocked_level - 1
        if quantity == 1:
            data.header['text'] = data.header.singular.pre + str(quantity) + data.header.singular.pos
        else:
            data.header['text'] = data.header.plural.pre + str(quantity) + data.header.plural.pos
        self.header = stage.create_text(data.header)[0]
        self.layer.add(self.header)
        self.footer = stage.create_text(data.footer)[0]
        for data_game in data.games:
            Game(stage, self.layer, data_game, self.footer)

    def handle_close(self, item, args):
        self.stop()

    def stop(self):
        self.stage.close_dialog(self.layer)

    def start(self):
        self.stage.show_dialog(self.layer, None)
