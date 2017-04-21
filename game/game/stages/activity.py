# -*- coding: latin-1 -*-

# 2011 - Dirección General Impositiva, Uruguay.
# Todos los derechos reservados.
# All rights reserved.

from framework.stage import assets, Layer, ItemText, ItemEvent, ItemImage
from yaml import load
from widgets.textbox import TextBox
from utils import DictClass
from pagination import Paginator
from framework import web
from game.data.datastore import WEB_DIR_ACT, WEB_DIR_POST, WEB_DIR_NEW_POST
import pygame 

DEFAULT_NAME = ''
DEFAULT_ROOM = ''        
        
class Next:
    def __init__(self):
        self.text = None
    def set_text(self, text):
        self.text = text

def set_text(next, text, text_item):
  text_item.break_text_into(next)
  text_item.set_text(text)
  text_item.break_text_into(None)
  return text_item
        
class FocusGroup:
    
    def __init__(self):
        self.items = []
    
    def add_item(self, item):
        self.items.append(item)
    
    def next_focus(self, item):
        current = self.items.index(item)
        self.items[(current + 1) % len(self.items)].begin_edit()

class ItemTextTab(ItemText):
    
    def __init__(self, *args, **kwargs):
        ItemText.__init__(self, *args, **kwargs)
        self.focus_group = None
        self.on_enter = None
    
    def set_focus_group(self, focus_group):
        self.focus_group = focus_group
        focus_group.add_item(self)
        
    def set_on_enter(self, on_enter):
        self.on_enter = on_enter
    
    def handle_event_focused(self, event, data):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_TAB and self.focus_group:
                self.focus_group.next_focus(self)
            elif event.key == pygame.K_RETURN and self.on_enter:
                self.on_enter()
            else:
                ItemText.handle_event_focused(self, event, data)
        else:
            ItemText.handle_event_focused(self, event, data)

class CommonDialog():

    def __init__(self, stage, on_ok=None):
        self.stage = stage
        layer = self.layer = Layer()
        data = self.get_data()
        items = stage.create_items_from_yaml(data['items'], self)
        self.on_ok = on_ok
        self.items = DictClass()
        for item in items:
            layer.add(item)
        self.message = stage.create_item(data["message"])[0]
        layer.add(self.message)

    def set_message(self, message):
        self.message.set_text(message)
    
    def handle_ok(self, *args, **kwargs):
        self.stop()
        if self.on_ok:
            self.on_ok()
    
    def stop(self):
        self.stage.close_dialog(self.layer)

    def start(self):
        self.stage.show_dialog(self.layer, None)

class ErrorDialog(CommonDialog):

    def __init__(self, stage, on_ok=None):
        CommonDialog.__init__(self, stage, on_ok)
    
    def get_data(self):
        return DictClass(load(file("data/activity/error_dialog.yaml")))

def web_callback(func):
    """
    decorator created to help identify the request response we are really waiting for
    """
    def apply(self, result, id):
        if id != self.current_id:
            return
        else:
            self.stage.reset_mouse_cursor()
            self.current_id = None
            self.current_callback = None            
            ret = func(self, result)
            return ret
    return apply 

def get_web_cb(obj, method, show_clock=True):
    id = obj.current_id = object()
    if show_clock:
        obj.stage.set_mouse_cursor(obj.clock_image)
    callback = obj.current_callback = lambda result:method(result, id)
    return callback

class Activity():
    def __init__(self, stage):
        global DEFAULT_NAME, DEFAULT_ROOM        
            
        self.go_to_last = False
        self.dialog = None
        self.paginator = None
        self.background = Layer()
        self.foreground = Layer()
        self.focus_group = FocusGroup()
        self.stage = stage
        self.current_callback = None
        self.current_id = None
        data = self.data = DictClass(load(file('data/common/activity.yaml')))
        self.clock_image = ItemImage(0, 0, assets.load_image(data.clock.src))
        layers = self.layers = DictClass()
        for k, i in data.layers.items():
            layers[k] = self.create_items(i)
        self.layers.main.name_input.set_focus_group(self.focus_group)
        self.layers.main.name_input.set_on_enter(self.handle_next)
        self.layers.main.name_input.set_text(DEFAULT_NAME)
        self.layers.main.room_input.set_focus_group(self.focus_group)
        self.layers.main.room_input.set_on_enter(self.handle_next)
        self.layers.main.room_input.set_text(DEFAULT_ROOM)
        self.current_layers = [layers.main.layer]
        text_box = self.layers.post.text_box = self.create_text_box(data.text_box)
        self.layers.post.layer.add(text_box)
        
        for item in self.stage.create_items_from_yaml(data["background"], self):
            self.background.add(item)
        for item in self.stage.create_items_from_yaml(data["foreground"], self):
            self.foreground.add(item)
            
        self.stage.start_timer('msgclock', 15000, self.update_messages_tick)
            
    def create_items(self, data):
        items = DictClass()
        layer = Layer()
        self.stage._items_manager = self
        for i in data:
            item = items[i.name] = self.stage.create_item(i)[0]
            item.data = i
            layer.add(item)
        self.stage._items_manager = None
        items["layer"] = layer
        return items
    
    def change_layer(self, new_layers):
        for layer in self.current_layers:
            self.stage.remove_layer(layer)
        self.stage.remove_layer(self.foreground)
        self.current_layers = new_layers
        for layer in self.current_layers:
            self.stage.add_layer(layer)
        self.stage.add_layer(self.foreground)
            
    def handle_back(self, *args, **kwargs):
        if self.current_callback:
            return
        if self.layers.room.layer in self.current_layers:
            self.change_layer([self.layers.main.layer])
        if self.layers.post.layer in self.current_layers \
            or self.layers.view_post.layer in self.current_layers:
            self.change_layer([self.layers.room.layer] + self.paginator.get_layers() + [self.layers.logged.layer])
           
    def handle_refresh(self, item, args):
        self.refresh_messages()
        
    def update_messages_tick(self, key, data):
        if self.paginator != None:            
            self.refresh_messages(False)
        
    def refresh_messages(self, show_clock = True):
        callback = get_web_cb(self, self.refresh_cb, show_clock)
        web.query(WEB_DIR_ACT % self.layers.main.room_input.get_text(), callback=callback)
    
    @web_callback
    def refresh_cb(self, result):            
        if result.error:
           return

        data = [DictClass(item) for item in result.data["posts"]]
        
        # Check if the data change, only update the screen if changed
        if data != self.posts:            
            self.posts = data
            
            items = []
            self.load_items(self.posts, items)
            
            current = self.paginator.get_current()
            self.paginator = Paginator(self.stage, items, self.data.pager)
            self.paginator.go_to(current)
            self.change_layer([self.layers.room.layer] + self.paginator.get_layers() + [self.layers.logged.layer])             
        
    def handle_post(self, *args, **kwargs):
        if self.current_callback:
            return
        web.send_data(WEB_DIR_NEW_POST % self.layers.main.room_input.get_text(), 
                      {"post[author_name]":unicode(self.layers.main.name_input.get_text(), "latin-1").encode("utf-8"), 
                       "post[machine_id]":"id",
                       "post[text]":unicode(self.layers.post.text_box.get_text(), "latin-1").encode("utf-8")}, 
                       callback=get_web_cb(self, self.post_web_cb))
    
    @web_callback
    def post_web_cb(self, result):
        if result.error:
            self.error_try_again_later()
            return
        self.layers.post.text_box.text("")
        self.go_to_last = True
        self.go_to_room()
        
    def go_to_room(self):
        if self.current_callback:
            return
        
        global DEFAULT_NAME, DEFAULT_ROOM        
        DEFAULT_NAME = self.layers.main.name_input.get_text()
        DEFAULT_ROOM = self.layers.main.room_input.get_text()
        
        web.query(WEB_DIR_ACT % self.layers.main.room_input.get_text(), callback=get_web_cb(self, self.go_to_room_web_cb))

    @web_callback
    def go_to_room_web_cb(self, result):
        if result.error:
           if result.error == web.Error.SERVER and result.code == 404:
              self.the_room_doesnt_exist()
           else:
              self.error_try_again_later()
           return
           
        data = DictClass(result.data)
        self.title = data.title
        self.layers.room.title.set_text(self.title)
        self.layers.room.description.set_text(data.description)
        self.layers.room.code.set_text(self.layers.room.code.data.text % self.layers.main.room_input.get_text())
        self.layers.logged.login_name.set_text(self.layers.main.name_input.get_text())
        data = [DictClass(item) for item in data.posts]
        self.posts = data
        
        items = []     
        self.load_items(data, items)
        
        self.paginator = Paginator(self.stage, items, self.data.pager)
        if self.go_to_last:
            self.go_to_last = False
            self.paginator.go_to_last()
        self.change_layer([self.layers.room.layer] + self.paginator.get_layers() + [self.layers.logged.layer])     
        
    def load_items(self, data, items):
        layer = Layer()
        
        left = self.data.post_box.left
        top = self.data.post_box.top        
        cant_items = 0
        i = 0
        for item in data:
            if cant_items >= self.data.post_box.items_per_page:
                items.append(layer)
                layer = Layer()
                top = self.data.post_box.top
                cant_items = 0
            self.stage._items_manager = self
            text_item = self.stage.create_item(self.data.post_item)[0]
            text_item.data_item = item
            text_item.set_top(top)
            text_item.set_left(left)
            def set_post_text(text_item, text):
                next = Next()
                set_text(next, text, text_item)
                if next.text:
                  new_dict = dict(self.data.post_item)
                  new_dict["width"] = -1
                  ellipsis = self.stage.create_item(new_dict)[0]
                  ellipsis.set_text("...")
                  ellipsis.set_top(text_item.get_top())
                  ellipsis.set_left(text_item.get_left() + text_item.lines[0])
                  return ellipsis
                return None
                
            def on_enter(text_item, *args, **kwargs):
              item = text_item.data_item
              text_item.set_text("&#c200,0,0!%s&#c!: %s"% (item.author_name, item.text))
            def on_leave(text_item, *args, **kwargs):
              item = text_item.data_item
              text_item.set_text("&#c58,129,188!%s&#c!: %s"% (item.author_name, item.text))
            text_item.add_event_handler(ItemEvent.MOUSE_ENTER, on_enter)
            text_item.add_event_handler(ItemEvent.MOUSE_LEAVE, on_leave)
            text_item.add_event_handler(ItemEvent.CLICK, self.handle_post_click)
            text_item.post_id = item.id
            text_item.post_index = i
            self.stage._items_manager = None
            other_item = set_post_text(text_item, "&#c58,129,188!%s&#c!: %s"% (item.author_name, item.text))
            if other_item:
              layer.add(other_item)
            layer.add(text_item)
            top += self.data.post_box.inter_line
            cant_items += 1
            i += 1
        
        if len(layer.items) > 0:
            items.append(layer)        
    
    def handle_next(self, *args, **kwargs):
        if self.dialog:
            return
        self.paginator = None
        self.layers.main.name_input.set_text(self.layers.main.name_input.get_text().strip())
        self.layers.main.room_input.set_text(self.layers.main.room_input.get_text().strip())
        if not self.layers.main.name_input.get_text() or not self.layers.main.room_input.get_text():
            self.fill_inputs()
            return
        self.go_to_room()
    
    def handle_next_post(self, *args, **kwargs):
        self.current_post += 1
        self.update_post_buttons()
        web.query(WEB_DIR_POST % (self.layers.main.room_input.get_text(), self.posts[self.current_post].id), callback=get_web_cb(self, self.view_post_web_cb))
    
    def handle_previous_post(self, *args, **kwargs):
        self.current_post -= 1
        self.update_post_buttons()
        web.query(WEB_DIR_POST % (self.layers.main.room_input.get_text(), self.posts[self.current_post].id), callback=get_web_cb(self, self.view_post_web_cb))
    
    def update_post_buttons(self):
        view_post = self.layers.view_post
        if self.current_post > 0:
            view_post.previous_post.set_visible(True)
        else:
            view_post.previous_post.set_visible(False)
        if self.current_post < len(self.posts) - 1:
            view_post.next_post.set_visible(True)
        else:
            view_post.next_post.set_visible(False)
        view_post.post_count.set_text(self.data.pager.page_count.text % {"page":self.current_post + 1, "total":len(self.posts)})
    
    def handle_post_click(self, item, *args, **kwargs):
        if self.current_callback:
            return
        self.current_post = item.post_index
        self.update_post_buttons()
        web.query(WEB_DIR_POST % (self.layers.main.room_input.get_text(), item.post_id), callback=get_web_cb(self, self.view_post_web_cb))
    
    @web_callback
    def post_message_cb(self, result):
        if result.error:
            self.error_try_again_later()
            self.change_layer([self.layers.room.layer] + self.paginator.get_layers() + [self.layers.logged.layer])
            return
        self.go_to_room()
    
    @web_callback
    def view_post_web_cb(self, result):
        if result.error:
            self.error_try_again_later()
            return
        data = DictClass(result.data)
        self.layers.view_post.title.set_text(self.title)
        self.layers.view_post.author.set_text(data.author_name + ":")
        # Usamos una clase que tiene el metodo set_text para saber si hay que dividir el texto
        items = []
        next = Next()
        layer = Layer()
        def create_text(stage, next, text, data):
            text_item = stage.create_text(data)[0]
            set_text(next, text, text_item)
            return text_item
        layer.add(create_text(self.stage, next, data.text, self.layers.view_post.post.data))
        items.append(layer)
        while next.text:
            layer = Layer()
            layer.add(create_text(self.stage, next, next.text, self.layers.view_post.post.data))
            items.append(layer)
        paginator = Paginator(self.stage, items, self.data.pager_post)
        self.change_layer([self.layers.view_post.layer] +  paginator.get_layers() + [self.layers.logged.layer])

    def handle_new_post(self, *args, **kwargs):
        self.layers.post.title.set_text(self.title)
        self.change_layer([self.layers.post.layer] + [self.layers.logged.layer])
        self.layers.post.text_box.begin()
        pass

    def handle_close(self, item, args):
        self.current_id = None
        self.stage.reset_mouse_cursor()
        self.stop()
  
    def create_text_box(self, data):
        return TextBox(data.left, data.top, data.width, data.height, getattr(self.stage, data.font), eval(data.color))
    
    def stop(self):
        for layer in self.current_layers:
            self.stage.remove_layer(layer)
        self.stage.remove_layer(self.foreground)
        self.stage.close_dialog(self.background)
        self.stage.stop_timer('msgclock')

    def start(self):
        self.stage.show_dialog(self.background, None)
        for layer in self.current_layers:
            self.stage.add_layer(layer)
        self.stage.add_layer(self.foreground)
        self.layers.main.room_input.set_editable(True)
        self.layers.main.room_input.set_edit_on_click(self.layers.main.room_input)
        self.layers.main.name_input.set_editable(True)
        self.layers.main.name_input.set_edit_on_click(self.layers.main.name_input)
        self.layers.main.name_input.begin_edit()
    
    def on_exit_dialog(self):
        self.dialog = None
    
    def error_try_again_later(self):
        self.dialog = dialog = ErrorDialog(self.stage, self.on_exit_dialog)
        dialog.set_message(self.data.messages.unknown)
        dialog.start()
    
    def the_room_doesnt_exist(self):
        self.dialog = dialog = ErrorDialog(self.stage, self.on_exit_dialog)
        dialog.set_message(self.data.messages.no_activity)
        dialog.start()
    
    def fill_inputs(self):
        self.dialog = dialog = ErrorDialog(self.stage, self.on_exit_dialog)
        dialog.set_message(self.data.messages.fill_inputs)
        dialog.start()
    

