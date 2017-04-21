# -*- coding: latin-1 -*-

# 2011 - Dirección General Impositiva, Uruguay.
# Todos los derechos reservados.
# All rights reserved.

from framework import assets
from game.stages.gamestage import GameStage
from utils import DictClass
from yaml import load
from content import Content
from framework.stage import ItemMask, ItemEvent, ItemImage
from character import Animation, load_animation

NULLEVENT = lambda *args, **kwargs: None

class Square(GameStage):
    DIALOG_INTERVAL = 6000
    ANIMATION_INTERVAL = 16
    
    def initialize(self):
        GameStage.initialize(self)
        
        # Load the sound
        self.item_found_sound = assets.load_sound('DGI_item_found.ogg')
    
    def set_up_background(self):
        return

    def show_next_item(self):
        self.item_data = DictClass(load(file('data/common/books.yaml')))
        GameStage.show_next_item(self)
        self.item_data = None

    def handle_after_blind(self, *args):
        self.dialog_mask.add_event_handler(ItemEvent.CLICK, self.dialog_mask_click)
        self.start_timer("dialog_timer", self.DIALOG_INTERVAL, self.dialog_mask_click)
        self.start_timer("dialog_animation_timer", self.ANIMATION_INTERVAL, self.handle_animation)
    
    def handle_animation(self, *args, **kwargs):
        dialog = self.dialog_items[self.current_dialog_frame]
        animation = self.dialog_animations[dialog.animation_name]
        animation.update(self.ANIMATION_INTERVAL)
        animation.item.set_image(animation.get_image())

    def dialog_mask_click(self, item, args):
        self.stop_timer("dialog_timer")
        dialog = self.dialog_items[self.current_dialog_frame]
        animation = self.dialog_animations[dialog.animation_name]
        self.named_layers.dialog.remove(dialog)
        animation.reset()
        animation.item.set_image(animation.get_image())
        self.current_dialog_frame += 1
        if self.current_dialog_frame >= len(self.dialog_items):
            self.stop_timer("dialog_animation_timer")
            self.named_layers.dialog.remove(self.dialog_mask)
            return
        self.named_layers.dialog.add(self.dialog_items[self.current_dialog_frame])
        self.start_timer("dialog_timer", self.DIALOG_INTERVAL, self.dialog_mask_click)
        
    def create_initial_dialog(self, data):
        data = DictClass(data)
        self.dialog_items = []
        self.dialog_animations = {}
        self.dialog_animation_items = []
        for (name, animation_data) in data["animations"].items():
            if "both" in animation_data:
                animation_data = animation_data["both"]
            else:
                animation_data = animation_data[self.game.datastore.datamodel.character] 
            self.dialog_animations[name] = animation = Animation(load_animation("", animation_data["animation"]))
            animation_item = ItemImage(animation_data["left"], animation_data["top"], animation.get_image())
            self.dialog_animation_items.append(animation_item)
            animation.item = animation_item
        for dialog_data in data["items"]:
            dialog = self.create_image(dialog_data["dialog"])[0]
            dialog.animation_name = dialog_data["animation"]
            self.dialog_items.append(dialog)            
            self.dialog_animation_items.append(animation_item)
        self.dialog_mask = ItemMask(0, 0, (600, 450))
        self.dialog_mask.add_event_handler(ItemEvent.CLICK, lambda *args, **kwargs: None)
        self.dialog_mask.add_event_handler(ItemEvent.MOUSE_ENTER, lambda *args, **kwargs: None)
        self.current_dialog_frame = 0
        return self.dialog_items[:1] + [self.dialog_mask] + self.dialog_animation_items

    def create_contents(self, data):
        data = DictClass(data)
        items = []
        icons = []
        contents = self.game.datastore.contents
        left = data.left
        width = data.width
        top = data.top
        inter = data.inter
        
        for content in data.contents:
            item = self.create_button(content.item)[0]
            if content.name in self.game.datastore.datamodel.backpack[self.game.datastore.datamodel.level - 1]:
                item.remove_event_handler(ItemEvent.CLICK, self.handle_select_item)
                item.set_rollover_image(None)
            item.content = content.name
            other_dict = dict(self.item_data[contents[item.content].type])
            other_dict.update({"action":"item_click"})
            hidden = self.create_image(dict(src = other_dict["hidden_src"]))[0]
            hidden.set_top(top)
            icon = self.create_button(other_dict)[0]
            icon.set_top(top)
            icon.content = item.content
            items.append(item)
            item.icon_item = icon 
            icons.append((icon, hidden))

        start = left + width
        icons_list = []
        for icon, hidden in icons:
            width = icon.get_width()
            hidden.set_left(start - width)
            icon.set_visible(icon.content in self.game.datastore.datamodel.backpack[self.game.datastore.datamodel.level - 1])
            icon.set_left(start - width)
            start -= width + inter
            icons_list += [hidden, icon]

        return items + icons_list

    def handle_item_click(self, item, args):
        content_data = self.game.datastore.contents[item.content]
        content = Content(self, content_data.title, content_data.text)
        content.start()
        
        
    def handle_select_item(self, item, args):
        content_data = self.game.datastore.contents[item.content]
        item.set_rollover_image(None)
        item.remove_event_handler(ItemEvent.CLICK, self.handle_select_item)
        content = Content(self, content_data.title, content_data.text)
        self.game.datastore.datamodel.backpack[self.game.datastore.datamodel.level - 1].add(item.content)
        item.icon_item.set_visible(True)
        content.start()
        self.render()
        self.item_found_sound.play()
        
        # Save data
        self.game.datastore.changed_data = True
        
    def handle_back(self, item, args):
        from map import Map
        self.game.set_stage(Map(self.game))
        