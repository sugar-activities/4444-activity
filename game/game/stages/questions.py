# -*- coding: latin-1 -*-

# 2011 - Dirección General Impositiva, Uruguay.
# Todos los derechos reservados.
# All rights reserved.

from framework.stage import assets, Layer, ItemCustomDraw, Item
import itertools
from yaml import load
from utils import DictClass
from gamestage import GameStage
from widgets.option import OptionGroup, CheckBox
from pagination import Paginator
from math import sqrt, acos, pi
    

class Win():
    def __init__(self, stage):
        self.stage = stage
        layer = self.layer = Layer()
        data = DictClass(load(file('data/common/next_level.yaml')))
        items = stage.create_items_from_yaml(data.other, self)
        for item in items:
            layer.add(item)
        text = stage.create_text(data.text)[0]
        text.set_text(data.text.texts[self.stage.game.datastore.datamodel.level])
        layer.add(text)
        
        # Load the sound
        item_found_sound = assets.load_sound('DGI_item_found.ogg')
        item_found_sound.play()
    
    def handle_next(self, item, args):
        if self.stage.game.datastore.datamodel.level + 1 > self.stage.game.datastore.datamodel.unlocked_level:
            self.stage.game.datastore.datamodel.unlocked_level =  self.stage.game.datastore.datamodel.level + 1
        self.stop()
        self.stage.handle_level_change()
        
        # Save data
        self.stage.game.datastore.changed_data = True
        # self.stage.game.datastore.save()
    
    def stop(self):
        self.stage.close_dialog(self.layer)
        self.layer.exit()

    def start(self):
        self.stage.show_dialog(self.layer, None)

class Fail():
    def __init__(self, stage, amount):
        self.stage = stage
        layer = self.layer = Layer()
        self.amount = amount
        data = DictClass(load(file('data/common/fail_tests.yaml')))
        text = stage.create_text(data.text)[0]
        if amount == 1:
            text.set_text(data.text.singular)
        else:
            text.set_text(data.text.plural % dict(amount = amount))
        items = stage.create_items_from_yaml(data.other, self)
        for item in items:
            layer.add(item)
        layer.add(text)
        
        # Load the sound
        wrong_sound = assets.load_sound('DGI_wrong.ogg')
        wrong_sound.play()

    def handle_next(self, item, args):
        self.stop()
    
    def stop(self):
        self.stage.close_dialog(self.layer)
        self.layer.exit()

    def start(self):
        self.stage.show_dialog(self.layer, None)

class Question():
    def __init__(self, stage, title, description, data):
        self.stage = stage
        layer = self.layer = Layer()
        if title:
            title_item = stage.create_text(data.title)[0]
            title.set_top(data.top_container.top)
            title_item.set_text(title)
            layer.add(title_item)
        else:
            title_item = Item(0,data.top_container.top, 0, 0)
        if description:
            description_item = self.description = stage.create_text(data.description)[0]
            extra = 0
            if title:
                extra = data.top_container.after_title
            description_item.set_top(title_item.get_top() + title_item.get_height() + extra)
            description_item.set_text(description)
            layer.add(description_item)
        else:
            self.description = Item(0,title_item.get_top() + title_item.get_height(),0,0)
    
    def exit(self):
        self.layer.exit()
        self.description = None
        self.stage = None
    
    def get_layer(self):
        return self.layer

class TestsViewer():
    def __init__(self, stage, tests):
        self.layer = Layer()
        self.stage = stage
        self.tests = tests
        data = DictClass(load(file('data/common/tests_viewer.yaml')))
        layers = [test.get_layer() for test in tests]
        self.paginator = Paginator(self.stage, layers, data.get("pagination", None))
        for item in self.stage.create_items_from_yaml(data.other, self):
            self.layer.add(item)

    def handle_confirm(self, item, args):
        failed = 0
        for test in self.tests:
            if not test.check():
                failed += 1
        if failed:
            fail_dialog = Fail(self.stage, failed)
            fail_dialog.start()
        else:
            self.stop()
            win = Win(self.stage)
            win.start()
            
    def handle_close(self, item, args):
        self.stop()

    def exit(self):
        self.paginator.exit()
        self.paginator = None
        self.stage = None
        self.layer.exit()
        self.layer = None
        for test in self.tests:
            test.exit()
        self.tests = None
        
    def stop(self):
        for layer in self.paginator.get_layers():
            self.stage.remove_layer(layer)
        self.stage.close_dialog(self.layer)

    def start(self):
        self.stage.show_dialog(self.layer, None)
        for layer in self.paginator.get_layers():
            self.stage.add_layer(layer)

class MultipleChoice(Question):
    def __init__(self, stage, title, description, options, right_answers):
        data = DictClass(load(file('data/common/multiple_choice.yaml')))
        Question.__init__(self, stage, title, description, data)
        self.options = options
        self.right_answers = set(right_answers)
        if len(self.right_answers) > 1:
            self.option_group = None
        else:
            self.option_group = OptionGroup()
        self.__load_items(data)
    
    def __load_items(self, data):

        description = self.description
        top = description.get_top() + description.get_height() + data.test_box.interline
        height = data.test_box.bottom - top
        interline = data.test_box.interline
        max_width = 0
        text_data = dict(data.texts)
        text_data["width"] = -1
        items = []
        self.option_items = []
        option_width = 0
        items_height = 0
        for option in self.options:
            if isinstance(option, int):
                option = str(option)
            text_data["text"] = option
            text_item = self.stage.create_text(text_data)[0]
            max_width = max(max_width, text_item.get_width())
            self.layer.add(text_item)
            option_item = CheckBox(self.stage, data.check_box, self.option_group)
            option_width = option_item.get_width()
            self.option_items.append(option_item)
            for item in option_item.get_items():
                self.layer.add(item)
            items.append((text_item, option_item))
            items_height += text_item.get_height() + interline
        items_height -= interline
        
        top = (height - items_height)/2 + top
        if max_width > data.texts.width:
            text_width = data.texts.width
        else:
            text_width = max_width
        for text, option in items:
            text.set_dimensions(text_width, -1)
            text.set_top(top)
            option.set_top(top)
            top += text.get_height() + interline

        width = text_width + option_width
        left_text = (data.test_box.width - width)/2 + data.test_box.left
        left_item = left_text + text_width + data.test_box.after_text
        for text, option in items:
            text.set_left(left_text)
            option.set_left(left_item)
            
    def check(self):
        answers = []
        for i in xrange(0,len(self.option_items)):
            if self.option_items[i].selected:
                answers.append(i)
        return self.right_answers == set(answers)
    
    def exit(self):
        Question.exit(self)
        self.result_handler = None
        self.stage = None
        for item in self.option_items:
            item.exit()
        self.option_items = None
        self.options = None
        self.right_answers = None
        if self.option_group:
            self.option_group.exit()
        self.option_group = None
        
    def stop(self):
        self.stage.close_dialog(self.layer)

    def start(self, result_handler = None):
        self.stage.show_dialog(self.layer, None)
        self.result_handler = result_handler

class Joining(Question):
    class ArrowItem(ItemCustomDraw):
        def __init__(self, left_item, right_item, color, line_width):
            self.__color = color
            self.__line_width = line_width
            self.__left_item = left_item
            self.__right_item = right_item
            self.left_x = self.__left_item.get_left() + self.__left_item.get_width()/2
            self.left_y = self.__left_item.get_top() + self.__left_item.get_height()/2
            self.right_x = self.__right_item.get_left() + self.__right_item.get_width()/2
            self.right_y = self.__right_item.get_top() + self.__right_item.get_height()/2
            self.__left = left = min(self.left_x, self.right_x) - self.__line_width/2
            width = max(self.left_x, self.right_x) - min(self.left_x, self.right_x) + self.__line_width
            self.__top = top = min(self.left_y, self.right_y) - self.__line_width/2
            height = max(self.left_y, self.right_y) - min(self.left_y, self.right_y) + self.__line_width
            # Pygame primitives for line drawing don't work as expected, so we scale and rotate a rectangle
            import pygame
            from pygame.draw import aaline, line
            from pygame import transform
            surface = pygame.Surface((1, line_width))
            length = sqrt((self.left_x - self.right_x)**2  + (self.left_y - self.right_y)**2)
            surface.fill(color)
            surface = self.surface = surface.convert_alpha()
            surface = transform.scale(surface, (int(length), int(line_width)))
            surface = transform.rotate(surface, acos((self.left_x - self.right_x)/length)*180.0/pi)
            if (self.left_y > self.right_y):
                surface = transform.flip(surface, False, True)
            self.surface = surface
            
            """line_hack = 4
            if self.right_y > self.left_y:
                for i in xrange(-line_hack, line_hack):
                    for j in xrange(-line_hack, line_hack):
                        line(surface, color, (self.__line_width/2 + i, self.__line_width/2 + i), 
                             (width - self.__line_width/2 + j, height - self.__line_width/2 + j), 1)
            else:
                for i in xrange(-line_hack, line_hack):
                    for j in xrange(-line_hack, line_hack):
                        line(surface, color, (self.__line_width/2 + i, height - self.__line_width/2 + i), 
                             (width - self.__line_width/2 + j, self.__line_width/2 + j), 1)"""
            ItemCustomDraw.__init__(self, left, top, width, height, self.draw_function)
        
        def exit(self):
            self.__left_item.exit()
            self.__right_item.exit()
            self.surface = None
        
        def draw_function(self, item, target):
            from pygame.draw import aaline, line
            target.blit_surface(self.surface, (self.__left, self.__top))
            
    class Options():
        def __init__(self, select_callback):
            self.select_callback = select_callback
            self.option_group = OptionGroup(self.__option_group_callback)
            self.selectables = []
            self.selectables_selected = []
            self.text_items = []
            self.options = []
            self.others = []
            self.selections = []
        
        def __option_group_callback(self, optn, item):
            index = self.options.index(item)
            return self.select_callback(self, index)
        
        def selected_index(self):
            return self.options.index(self.option_group.selected)
        
        def selected_item(self):
            return self.option_group.selected is not None
        
        def unselect(self):
            self.option_group.unselect()
        
        def select(self, index, joined):
            if joined:
                self.selections[index] += 1
            else:
                if self.selections[index] > 0:
                    self.selections[index] -= 1
            if self.selections[index] == 1 and joined or not joined and self.selections[index] == 0: 
                self.options[index].set_visible(False)
                self.others[index].set_visible(True)
                swap = self.options[index]
                self.options[index] = self.others[index]
                self.others[index] = swap
        
        def load_items(self, elements, data, stage, top, height, width = None):    
            total_height = 0
            text_width = data.text.width
            max_text_width = 0
            text_data = dict(data.text)
            text_data["width"] = -1
            lines = []
            for element in elements:
                self.selections.append(0)
                text = stage.create_text(text_data)[0]
                if isinstance(element, int):
                    element = str(element)
                text.set_text(element)
                if text.get_width() > max_text_width:
                    max_text_width = text.get_width()
                selectable = stage.create_option_image(self.option_group, data.box.joined)[0]
                selectable_selected = stage.create_option_image(self.option_group, data.box.not_joined)[0]
                selectable_selected.set_visible(False)
                self.options.append(selectable)
                self.others.append(selectable_selected)
                self.text_items.append(text)
                self.selectables.append(selectable)
                self.selectables_selected.append(selectable_selected)
                lines.append((selectable, selectable_selected, text))
            
            if max_text_width < text_width:
                text_width = max_text_width
            
            total_height = 0
            total_width = 0
            for selectable, selectable_selected, text_item in lines:               
                text_item.set_dimensions(text_width, -1)
                if "after_text" in data.container_box:
                    total_width = text_width + data.container_box.after_text + selectable.get_width()
                    selectable.set_left(text_width + data.container_box.after_text)
                    selectable_selected.set_left(selectable.get_left())
                else:
                    total_width = text_width + data.container_box.after_box + selectable.get_width()
                    text_item.set_left(selectable.get_width() + data.container_box.after_box)
                text_item.set_top(total_height)
                selectable.set_top(total_height)
                selectable_selected.set_top(total_height)
                total_height += data.container_box.interline + text_item.get_height()

            total_height -= data.container_box.interline
            new_top = (height - total_height)/2 + top
            for item in self.get_items():
                item.set_top(item.get_top() + new_top)
            return total_width
        
        def exit(self):
            self.select_callback = None
            self.option_group.exit()
            for item in self.selectables:
                item.exit()
            self.selectables = None
            for item in self.selectables_selected:
                item.exit()
            self.selectables_selected = None
            for item in self.options:
                item.exit()
            self.options = None
            for item in self.others:
                item.exit()
            self.others = None
            for item in self.text_items:
                item.exit()
            self.text_items = None
        
        def set_left(self, left):
            for item in self.get_items():
                item.set_left(item.get_left() + left)
            
        def get_items(self):
            return self.text_items + self.selectables + self.selectables_selected
            
    def __init__(self, stage, title, description, fromm, to, correct_pairs, visualization = None):
        data = DictClass(load(file('data/common/joining.yaml')))
        if visualization:
            data.deep_update(visualization)
        Question.__init__(self, stage, title, description, data)
        self.fromm = fromm
        self.to = to
        self.correct_pairs = set(correct_pairs)
        self.__load_items(data)
    
    def exit(self):
        Question.exit(self)
        self.fromm = None
        self.to = None
        self.correct_pairs = None
        self.left.exit()
        self.right.exit()
        self.left = None
        self.right = None
        self.selected_pairs = None
    
    def on_selected_left(self, options, index):
        if self.right.selected_item():
            joined = self.join(index, self.right.selected_index())
            self.left.select(index, joined)
            self.right.select(self.right.selected_index(), joined)
            self.right.unselect()
            return False
        return True 

    def on_selected_right(self, options, index):
        if self.left.selected_item():
            joined = self.join(self.left.selected_index(), index)
            self.right.select(index, joined)
            self.left.select(self.left.selected_index(), joined)
            self.left.unselect()
            return False
        return True

    def join(self, left_index, right_index):
        if not self.selected_pairs[left_index][right_index]:
            self.selected_pairs[left_index][right_index] = self.ArrowItem(self.left.selectables[left_index], self.right.selectables[right_index], self.arrow_color, self.arrow_width)
            self.layer.add(self.selected_pairs[left_index][right_index])
            return True
        else:
            self.layer.remove(self.selected_pairs[left_index][right_index])
            self.selected_pairs[left_index][right_index] = None
            return False
    
    def __load_items(self, data):
        self.left = self.Options(self.on_selected_left)
        self.right = self.Options(self.on_selected_right)
        self.selected_pairs = [list(itertools.repeat(None, len(self.to))) for x in self.fromm]
        self.arrow_color = eval(data.arrow.color)
        self.arrow_width = data.arrow.width
        
        top = self.description.get_top() + self.description.get_height()
        left_width = self.left.load_items(self.fromm, data.left, self.stage, top, data.test_box.bottom - top)
        right_width = self.right.load_items(self.to, data.right, self.stage, top,  data.test_box.bottom - top, data.test_box.width + data.test_box.after_left_container - left_width )
        total_width = left_width + right_width + data.test_box.after_left_container
        left_left = (data.test_box.width - total_width)/2 + data.test_box.left
        right_left = left_left + left_width + data.test_box.after_left_container
        self.left.set_left(left_left)
        self.right.set_left(right_left)
        
        for item in self.left.get_items() + self.right.get_items():
            self.layer.add(item)
    
    def check(self):
        selected_pairs = []
        for i in xrange(0, len(self.selected_pairs)):
            for j in xrange(0, len(self.selected_pairs[i])):
                if self.selected_pairs[i][j] is not None:
                    selected_pairs.append((i, j))
        return self.correct_pairs == set(selected_pairs)
 
    def start(self):
        self.stage.show_dialog(self.layer, None)
    
    def stop(self):
        self.stage.close_dialog(self.layer)
    
    def show_current_page(self):
        return self.layer

class TrueFalse(Question):
    def __init__(self, stage, title, description, statements, answers):
        data = DictClass(load(file('data/common/true_false.yaml')))
        Question.__init__(self, stage, title, description, data)
        self.statements = statements
        self.answers = answers
        self.__load_items(data)
    
    def exit(self):
        Question.exit(self)
        self.statements = None
        self.answers = None
        for option in self.options:
            option.exit()
        self.options = None
        self.option_items = None
    
    def __load_items(self, data):
        self.option_items = []
        self.options = []
        top = self.description.get_top() + self.description.get_height() + data.test_box.interline
        height = data.test_box.bottom - top
        text_data = dict(data.text)
        lines = []
        text_width = data.text.width
        max_text_width = 0
        text_data["width"] = -1
        false_width = 0
        true_width = 0
        for statement in self.statements:
            option_group = OptionGroup()
            self.options.append(option_group)
            text_item = self.stage.create_text(text_data)[0]
            text_item.set_text(statement)
            if text_item.get_width() > max_text_width:
                max_text_width = text_item.get_width()
            
            self.layer.add(text_item)
            
            false_item = CheckBox(self.stage, data.false_box, option_group)
            false_width = false_item.get_width()
            for item in false_item.get_items():
                self.layer.add(item)
            
            true_item = CheckBox(self.stage, data.true_box, option_group)
            true_width = true_item.get_width()
            for item in true_item.get_items():
                self.layer.add(item)

            self.option_items.append((false_item, true_item))
            lines.append((text_item, false_item, true_item))
            

        if max_text_width < text_width:
            text_width = max_text_width
        
        left_false = text_width + data.test_box.after_text
        left_true = left_false + data.test_box.after_false + false_width
        total_width = left_true + true_width

        start_left = (data.test_box.width - total_width)/2 + data.test_box.left
        left_false += start_left
        left_true += start_left
        items_height = 0
        for text_item, true_item, false_item in lines:
            text_item.set_dimensions(text_width, -1)
            text_item.set_left(start_left)
            true_item.set_left(left_true)
            false_item.set_left(left_false)
            items_height += text_item.get_height() + data.test_box.interline
        items_height -= data.test_box.interline
        
        top = (height - items_height)/2 + top
        for text_item, true_item, false_item in lines:
            text_item.set_top(top)
            true_item.set_top(top)
            false_item.set_top(top)
            top += text_item.get_height() + data.test_box.interline
                
    def check(self):
        all_selected = True
        for option in self.option_items:
            if not (option[0].selected or option[1].selected):
                return False
        return self.answers == [option[1].selected for option in self.option_items]

    def start(self):
        self.stage.show_dialog(self.layer, None)
    
    def get_layer(self):
        return self.layer
    
    def stop(self):
        self.stage.close_dialog(self.layer)

class Multiple(GameStage):

    
    def initialize(self):
        GameStage.initialize(self)
        self.viewer = TestsViewer(self, [MultipleChoice(self, ["sdfsdf", "asdfasdfsdf", "asdfasdfasdf"], 1),
            TrueFalse(self, ["adfgvadfv","dfvdfv","adfvadfvadfvadfvadfdfvdfv", 
                "asdfasdfasdfsd adsfga asdfg adfg adgf adfg adgf adfg adfg adfg sdfhfdshdfhfdgh  dfh  fdgh dfgjdfj "],
                "Sdf"),
            Joining(self, ["lalallalala", "lalalalalala", "lalalala", 
                "dfgsdfg sdfg sdfh sdfh sdfhgsdfgsd"], ["sdfsdf", "fdsfsdf"], [])])

    def prepare(self):
        self.viewer.start()
        
        
            
