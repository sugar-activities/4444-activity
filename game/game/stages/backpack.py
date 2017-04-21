# -*- coding: latin-1 -*-

# 2011 - Dirección General Impositiva, Uruguay.
# Todos los derechos reservados.
# All rights reserved.

from framework.stage import assets, Layer, ItemEvent
from gamestage import GameStage
from content import Content
from yaml import load
from utils import DictClass

class BackPack:
    ITEMS_PER_PAGE = 5
    
    def __init__(self, stage, elements):
        self.stage = stage
        self.layer = Layer()
        self.elements_layer = Layer()
        from yaml import load
        data = load(file('data/common/backpack.yaml'))
        self.elements = elements
        self.close_button = stage.create_button(data["close"], self)[0]
        self.next_button = stage.create_button(data["next"], self)[0]
        self.previous_button = stage.create_button(data["previous"], self)[0]
        self.description_text = stage.create_text(data["description"])[0]
        self.element_count_text = stage.create_text_count(data["element_count"], len(elements))[0]
        self.previous_button.set_visible(False)
        self.current_page = 0
        self.create_elements(data, elements)
        if len(elements) <= self.ITEMS_PER_PAGE:
            self.next_button.set_visible(False)
        self.set_elements()

        self.other = stage.create_items_from_yaml(data["other"])
        for other in self.other:
            self.layer.add(other)
        self.layer.add(self.close_button)
        self.layer.add(self.next_button)
        self.layer.add(self.previous_button)
        self.layer.add(self.description_text)
        self.layer.add(self.element_count_text)
        self.current_items = []

    def create_elements(self, data, elements):
        self.elements = []
        start_top = data["elements_pos"]["top"]
        inter = data["elements_pos"]["interspace"]
        element_data = DictClass(load(file('data/common/books.yaml')))
        current = 0
        for page in xrange(0, len(elements) / self.ITEMS_PER_PAGE + 1):
            start_left = 0
            for element in elements[page*self.ITEMS_PER_PAGE : (page + 1)*self.ITEMS_PER_PAGE]:
                element_data[element.type]['action'] = 'click'
                new = self.stage.create_button(element_data[element.type], manager=self)[0]
                new.set_top(start_top)
                new.set_left(start_left)
                new.add_event_handler(ItemEvent.MOUSE_ENTER, self.handle_element_enter)
                new.add_event_handler(ItemEvent.MOUSE_LEAVE, self.handle_element_leave)
                new.info = element
                start_left += new.get_width() + inter
                self.elements.append(new)
                current += 1
            start_left -= inter
            new_left = (data["elements_pos"]["width"] - start_left)/2 + data["elements_pos"]["left"]
            for element in self.elements[page*self.ITEMS_PER_PAGE : (page + 1)*self.ITEMS_PER_PAGE]:
                element.set_left(element.get_left() + new_left)
                    
    def set_elements(self):
        self.elements_layer.empty()
        fromm = self.current_page*self.ITEMS_PER_PAGE
        for element in self.elements[fromm : fromm + self.ITEMS_PER_PAGE]:
            self.elements_layer.add(element)
            
    def start(self):
        self.stage.show_dialog(self.layer, None)
        self.stage.add_layer(self.elements_layer)

    def handle_close(self, item, args):
        self.stage.remove_layer(self.elements_layer)
        self.stage.close_dialog(self.layer)
        self.layer.exit()
        self.layer = None
        self.close_button.exit()
        self.next_button.exit()
        self.previous_button.exit()
        self.description_text.exit()
        self.element_count_text.exit()
        self.previous_button.exit()
        for element in self.elements:
            element.exit()
        self.elements = None
        self.elements_layer.exit()
        self.elements_layer = None
    
    def handle_next(self, item, args):
        self.current_page += 1
        if len(self.elements) - self.current_page*self.ITEMS_PER_PAGE <= self.ITEMS_PER_PAGE:
            self.next_button.set_visible(False)
        self.previous_button.set_visible(True)
        self.set_elements()
        
    def handle_previous(self, item, args):
        self.current_page -= 1
        if not self.current_page:
            self.previous_button.set_visible(False)
        if len(self.elements) > self.ITEMS_PER_PAGE:
            self.next_button.set_visible(True)
        self.set_elements()
        
    def handle_element_enter(self, item, args):
        self.description_text.set_text(item.info.title)
    
    def handle_element_leave(self, item, args):
        self.description_text.set_text("")
        
    def handle_click(self, item, args):
        paginate = Content(self.stage, item.info.title, item.info.text)
        paginate.start()

class Element:
    def __init__(self, type, title="descr", text=" asdf asdf asdf asdf asd asdf asdfsadfkljh lhsd fjasd fljashf lasjbf lasdfh oasdhf oashf oashdfoash foashdf sadgf adfg sdfgh dsfhsdfgh sfgh sfgh sfghsfh sdfgh fgh fgh sfh s sfhsfghsfg  sfgh sgh asdfh sfh asdf asdf asdf asdf asd asdf asdfsadfkljh lhsd fjasd fljashf lasjbf lasdfh oasdhf oashf oashdfoash foashdf sadgf adfg sdfgh dsfhsdfgh sfgh sfgh sfghsfh sdfgh fgh fgh sfh s sfhsfghsfg  sfgh sgh asdfh sfh asdf asdf asdf asdf asd asdf asdfsadfkljh lhsd fjasd fljashf lasjbf lasdfh oasdhf oashf oashdfoash foashdf sadgf adfg sdfgh dsfhsdfgh sfgh sfgh sfghsfh sdfgh fgh fgh sfh s sfhsfghsfg  sfgh sgh asdfh sfh asdf asdf asdf asdf asd asdf asdfsadfkljh lhsd fjasd fljashf lasjbf lasdfh oasdhf oashf oashdfoash foashdf sadgf adfg sdfgh dsfhsdfgh sfgh sfgh sfghsfh sdfgh fgh fgh sfh s sfhsfghsfg  sfgh sgh asdfh sfh "):         
        self.type = type
        self.title = title
        self.text = text

class BackPackTest(GameStage):
    def initialize(self):
        GameStage.initialize(self)
        self.backpack = BackPack(self,[Element("blue_book","lalalalala"), Element("green_book"), Element("pink_book"), Element("pink_book"), Element("yellow_book"), Element("green_book"), Element("red_book")])
        
    def prepare_screen(self):
        self.backpack.start()
        