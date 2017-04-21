# -*- coding: latin-1 -*-

# 2011 - Dirección General Impositiva, Uruguay.
# Todos los derechos reservados.
# All rights reserved.


from framework.stage import assets, ItemEvent, ItemImage, ItemText, Layer
from gamestage import GameStage
from framework.engine import SCREEN_WIDTH
from math import ceil

class Paginator():
    def __init__(self, stage, items, optional_data = None):
        self.layer = Layer()
        self.items_layer = Layer()
        self.items = items
        self.stage = stage
        from yaml import load
        data = load(file('data/common/pagination.yaml'))
        if optional_data is not None:
            data.update(optional_data)
        self.current = 1
        if len(self.items):
            self.current_layer = self.items[0]
        else:
            self.current_layer = Layer()
        self.min = 1
        self.max = len(self.items)
        self.count = len(self.items)
        for item in items:
            item.set_visible(False)
        self.previous = stage.create_button(data["previous"], self)[0]
        self.next = stage.create_button(data["next"], self)[0]
        self.last = None
        if "last" in data:
            self.last = stage.create_button(data["last"], self)[0]
        if "page_count" in data and data["page_count"]:
            self.page_count_text = stage.create_text(data["page_count"])[0]
            self.page_count_base_text = data["page_count"]["text"]
        else:
            self.page_count_text = None
        self.update_page_count()
        self.update_items()
        self.update_buttons()
        
        self.layer.add(self.previous)
        self.layer.add(self.next)
        if self.page_count_text:
            self.layer.add(self.page_count_text)
        if self.last:
            self.layer.add(self.last)
    
    def exit(self):
        self.layer.exit()
        self.items_layer.exit()
        for item in self.items:
            item.exit()
        self.items = None
        self.stage = None
        self.previous.exit()
        self.previous = None
        self.next.exit()
        self.next = None
        if self.last:
            self.last.exit()
            self.last = None
        if self.page_count_text:
            self.page_count_text.exit()
            self.page_count_text = None
            
    
    def update_page_count(self):
        if self.page_count_text:
            self.page_count_text.set_text(self.page_count_base_text % {"page":self.current, "total":self.max})
        
    
    def update_items(self):
        self.current_layer.set_visible(False)
        if len(self.items) > 0:
            self.current_layer = self.items[self.current - 1]
        self.current_layer.set_visible(True)
    
    def update_buttons(self):
        if self.current > self.min:
            self.previous.set_visible(True)
        else:
            self.previous.set_visible(False)
        if self.current < self.max:
            self.next.set_visible(True)
        else:
            self.next.set_visible(False)
        if self.last:
            if self.current == self.max:
                self.last.set_visible(False)
            else:
                self.last.set_visible(True)
    
    def handle_previous(self, item, args):
        if self.current > self.min:
            self.current -= 1
        self.update_buttons()
        self.update_page_count()
        self.update_items()
        
    def handle_next(self, item, args):
        if self.current < self.max:
            self.current += 1
        self.update_buttons()
        self.update_page_count()
        self.update_items()
    
    def get_current(self):
        return self.current        
    
    def go_to(self, current):
        if current < self.max:
            self.current = current
        else:
            self.current = current
        self.update_buttons()
        self.update_page_count()
        self.update_items()        

    def go_to_last(self):
        self.current = self.max
        self.update_buttons()
        self.update_page_count()
        self.update_items()
    
    def handle_go_to_last(self, item, args):
        self.go_to_last()

    def get_layers(self):
        return [self.layer] + self.items

class Pagination(GameStage):
    
    def initialize(self):
        GameStage.initialize(self)
        self.paginate = Paginate(self, "titulo",
                                      """texto largo texto largo
texto largo texto largo texto largo 
texto largo texto largo texto largo
texto largo texto largo texto largo 
texto largo texto largo texto largo 
texto largo texto largo
texto largo texto largo texto largo 
texto largotexto largo texto largo 
texto largo texto largo texto largo 
texto largo
texto largo texto largo texto largo 
texto largotexto largo texto largo 
texto largo texto largo texto largo 
texto largo p
        """)

    def prepare(self):
        self.paginate.start()
        