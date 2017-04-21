# -*- coding: latin-1 -*-

# 2011 - Dirección General Impositiva, Uruguay.
# Todos los derechos reservados.
# All rights reserved.

from pygame import KEYDOWN, K_SPACE
from framework.stage import assets, ItemEvent, ItemImage, ItemMask, ItemRect, ItemText, Layer, Stage
from framework import animations
from yaml import load
from widgets.option import OptionGroup, OptionImage, OptionItems, ItemTextSelectable, ItemRectSelectable
from widgets.button import Button
from pygame.locals import Color

class QuitDialog():

    def __init__(self, stage, on_no=None):
        self.stage = stage
        layer = self.layer = Layer()
        data = load(file('data/common/quit_dialog.yaml'))
        items = stage.create_items_from_yaml(data['items'], self)
        self.on_no = on_no
        for item in items:
            layer.add(item)
    
    def handle_ok(self, item, args):
        self.stage.game.datastore.save()
        self.stage.game.quit()
    
    def handle_cancel(self, *args, **kwargs):
        if self.on_no:
            self.on_no()
        self.stage.game.quit()
    
    def stop(self):
        self.stage.close_dialog(self.layer)
        self.layer.exit()

    def start(self):
        self.stage.show_dialog(self.layer, None)

class GameStage(Stage):
    """
    Defines dialogs for winning or losing case
    """    
    def __init__(self, game, background=None):
        """
        Constructorselect_handler.
        - game: Game.
        """
        Stage.__init__(self, game, background)
        self.actual_screen = -1

    def initialize(self):
        """
        Initialize the stage.

        Its preferred to add initialization code in the function instead of
        the constructor, because this function is invoked before show stage
        for first time and after release the memory of the previous stage.
        """
        self.set_closed_handler(self.exit)
        self.__mouser_cursor_item = ItemImage(0, 0, assets.load_image('cursor.png'))
        self.__mouse_pointer = (6, 0)
        self.reset_mouse_cursor()        
        
        stream = file('data/fonts.yaml', 'r')
        fonts = load(stream)
        self.named_items = {}
        self.named_fonts = {}
        
        for font in fonts:
            loaded_font = assets.load_font(fonts[font]['file_name'], fonts[font]['size'])
            setattr(self, font, loaded_font)
            self.named_fonts[font] = loaded_font
        
        # Load the sound
        self.click_sound = assets.load_sound('DGI_Click.ogg')
        self.mouse_enter_sound = assets.load_sound('DGI_Roll_Over.ogg')
        self.turn_page_sound = assets.load_sound('DGI_page_turn.ogg')
        
        self.data_sounds = {
                            'sound_click_handler': getattr(self, 'handle_sound_click'),
                            'sound_mouse_enter_handler': getattr(self, 'handle_sound_mouse_enter')
                            }
    
    def prepare(self):
        """
        This function after the stage is selected as the current stage, and before show it.
        """
        self.show_next_screen()
    
    def reset_mouse_cursor(self):
        self.set_mouse_cursor(self.__mouser_cursor_item , pointer=self.__mouse_pointer)
        
    def prepare_screen(self):
        self.set_up_background()
        self.show_next_item()
        
    def show_next_screen(self):
        self.actual_screen += 1
        self.prepare_screen()

    def show_previous_screen(self):
        self.actual_screen -= 1
        self.prepare_screen()

    def create_layers(self, data):
        class ExtraLayers:
            pass
        layers = ExtraLayers()
        layer_list = []
        for layer in data:
            new_layer = Layer()
            layer_list.append(new_layer)
            if "name" in layer:
                setattr(layers, layer["name"], new_layer)
            items = self.create_items_from_yaml(layer["items"])
            if items:
                for item in items:
                    new_layer.add(item)
        return layers, layer_list
            
    def show_next_item(self):
        for layer in self.layers:
            layer.exit()
        self.empty_layers()
        stream = file('data/' + self.__class__.__name__.lower() + '/screen.' + str(self.actual_screen) + '.yaml', 'r')
        data = load(stream)
        self.named_items = {}
        items = self.create_items_from_yaml(data.get('items', None))
        self.show_items(items)
        layers, layer_list = self.create_layers(data.get("layers", []))
        self.named_layers = layers
        for layer in layer_list:
            self.add_layer(layer)
        if "start_effect" in data:
            start_effect = data["start_effect"]
            # TODO: do it dinamically for more effects
            if start_effect["type"] == "blind":
                callback = None
                if "callback" in start_effect:
                    callback = getattr(self, "handle_" + start_effect["callback"])
                for layer in layer_list:
                    animations.blind_layer(layer, animations.BlindDirection.SHOW_DOWN, None, start_effect.get("time", 450), callback, False)
                    callback = None
    
    def show_items(self, items):
        if items:
            if hasattr(self, "actual_layer") and self.actual_layer:
                self.actual_layer.exit()
            self.actual_layer = Layer()
            layer = self.actual_layer
            for item in items:
                layer.add(item)
            self.add_layer(layer)
    
    def create_items_from_yaml(self, yaml_items, manager = None):
        items = []
        self._items_manager = manager
        if yaml_items:
            for yaml_item in yaml_items:
                items += self.create_item(yaml_item)
        self._items_manager = None
        return items
    
    def create_item(self, data):
        if data['type'] and data['type'] != 'ignore':
            items = getattr(self, "create_" + data['type'])(data)
            if 'name' in data:
                self.named_items[data['name']] = items
            return items
        else:
            return []
    
    def text_arguments(self, data):
        font = getattr(self, data['font'])
        color = eval(data['color'])
        args = [data.get('left', 0), data.get('top', 0), font, data.get('line_height', 0), data.get('text', ""), 
            color, None, data.get('width', -1), data.get('height', -1), data.get('h_align', 1), data.get('v_align', 1)]
        kwargs = {"additional_fonts": dict(zip(self.named_fonts.keys(), [(x, 0) for x in self.named_fonts.values()]))}
        return args, kwargs
    
    def create_text(self, data):
        args, kwargs = self.text_arguments(data)
        item = ItemText(*args, **kwargs)
        if "max_chars" in data:
            item.set_max_chars(data["max_chars"])
        return [item]
    
    def create_text_count(self, data, count):
        item = self.create_text(data)[0]
        if count > 1:
            item.set_text(data["text_plural"] % count)
        elif count == 1:
            item.set_text(data["text_singular"])
        else:
            item.set_text(data["text_none"])
        return [item]        
    
    def create_text_selectable(self, data, manager=None):
        args, kwargs = self.text_arguments(data)
        color = eval(data['color'])
        rollover_color = eval(data['rollover_color'])
        item = ItemTextSelectable(color, rollover_color, *args, **kwargs)
        if manager is None:
            click_handler = getattr(self, 'handle_' + data['action'])
        else:
            click_handler = getattr(manager, 'handle_' + data['action'])
        item.add_event_handler(ItemEvent.CLICK, click_handler)
        return [item]

    def create_button(self, data, manager=None, sounds=True):
        if 'action' in data:
            if manager:
                data['click_handler'] = getattr(manager, 'handle_' + data['action'])
            elif self._items_manager:
                data['click_handler'] = getattr(self._items_manager, 'handle_' + data['action'])
            else:
                data['click_handler'] = getattr(self, 'handle_' + data['action'])
        if sounds:
            data_sounds = {}
            data_sounds.update(self.data_sounds)
            if 'action_sound' in data:
                data_sounds['sound_click_handler'] = getattr(self, 'handle_sound_' + data['action_sound'])
            data.update(data_sounds)
        item = Button(data)
        return [item]
    
    def create_image(self, data):
        if 'image' in data:
            image = data['image']
        else:
            image = assets.load_image(data['src'])
        item = ItemImage(data.get('left', 0), data.get('top', 0), image, hit_over_transparent = data.get("hit_over_transparent", False))
        if 'rollover_src' in data:
            item.rollover_image = assets.load_image(data['rollover_src'])
            item.set_rollover_image(item.rollover_image)
        else:
            item.rollover_image = None 
        return [item]
    
    def rectangle_arguments(self, data):
        if 'color' in data:
            color = eval(data['color'])
        args = [data['left'], data['top'], data['width'], data['height']]
        kwargs = {}
        if 'color' in data:
            kwargs['background'] = color
        return args, kwargs
    
    def create_rectangle(self, data):
        args, kwargs = self.rectangle_arguments(data)
        item = ItemRect(*args, **kwargs)
        return [item]
    
    def create_rectangle_selectable(self, data):
        args, kwargs = self.rectangle_arguments(data)
        if 'action' in data:
            action = data['action']
        else:
            action = None
        if 'items' in data:
            items = self.create_items_from_yaml(data['items'])
        else:
            items = []
        item = ItemRectSelectable(data['step_left'], data['step_top'], data['step_width'], data['step_height'], action, items, *args, **kwargs)
        return [item] + items
    
    def create_option(self, group, data, yaml_items):
        items = []
        for yaml_item in yaml_items:
            yaml_item.update(data)
            items += self.create_item(yaml_item)
        OptionItems(group, data, items)
        return items
    
    def create_option_image(self, group, data):
        item = OptionImage(group, data)
        return [item]

    def create_selected_character(self, data):
        character = self.create_image(data[self.game.datastore.datamodel.character])[0]
        return [character]
    
    def set_screen(self, screen):
        self.actual_screen = screen - 1

    def handle_quit(self, item, args):
        self.game.quit()
    
    def handle_event(self, e):
        if e.type == KEYDOWN:
            if e.key == K_SPACE:
                return
    
    # Sounds
    def handle_sound_click(self, item, args):
        self.click_sound.play()
    
    def handle_sound_turn_page(self, item, args):
        self.turn_page_sound.play()
      
    def handle_sound_mouse_enter(self, item, args):
        self.mouse_enter_sound.play()
        
    def handle_quit(self):
        if not self.game.datastore.changed_data: return True
        self.stop()
        self.stop_timers()
        quit = QuitDialog(self)
        quit.start()
        return False
    
    def exit(self, other_self):
        for layer in self.layers:
            layer.exit()
        self.layers = []
        self.named_items = None
        self.named_layers = None
        self.named_fonts = None
        
    def stop(self):
        pass
