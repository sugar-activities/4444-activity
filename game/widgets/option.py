from framework.stage import assets, ItemEvent, ItemImage, ItemMask, ItemRect, ItemText, Layer, Stage

class OptionGroup():
    def __init__(self, on_select_callback=None):
        self.selected = None
        self.buttons = []
        self.on_select_callback = on_select_callback
    
    def select(self, option):
        if self.selected != option:
            if self.on_select_callback and not self.on_select_callback(self, option):
                return
            for button in self.buttons:
                button.turn_on()
                button.set_image(button.image)
                button.set_rollover_image(button.rollover_image)
            if self.selected:
                self.selected.unselect()
            self.selected = option
            self.selected.select()

    def exit(self):
        self.selected = None
        self.buttons = []
        self.on_select_callback = None
        
    def unselect(self):
        if self.selected:
            self.selected.unselect()
            self.selected = None

class OptionImage(ItemImage):
    def __init__(self, group, data):
        image = assets.load_image(data['src'])
        ItemImage.__init__(self, data.get('left', 0), data.get('top', 0), image)
        self.image = image
        
        if 'rollover_src' in data:
            self.rollover_image = assets.load_image(data['rollover_src'])
            self.set_rollover_image(self.rollover_image)
        else:
            self.rollover_image = None
        
        if 'selected_src' in data:
            self.selected_image = assets.load_image(data['selected_src'])
        else:
            self.selected_image = None
        
        if 'value' in data:
            self.value = data['value']
        
        def handle_select(item, args):
            group.select(self)
        self.add_event_handler(ItemEvent.CLICK, handle_select)
        
        # Sounds
        if 'sound_click_handler' in data:
            self.add_event_handler(ItemEvent.CLICK, data['sound_click_handler'])
                       
        if 'sound_mouse_enter_handler' in data:
            self.add_event_handler(ItemEvent.MOUSE_ENTER, data['sound_mouse_enter_handler'])
    
    def exit(self):
        ItemImage.exit(self)
        self.selected_image = None
        self.rollover_image = None
        self.group = None
        self.rollover_image = None
    
    def select(self):
        if self.selected_image:
            self.set_image(self.selected_image)
            self.set_rollover_image(None)
    
    def unselect(self):
        self.set_image(self.image)
        if self.rollover_image:
            self.set_rollover_image(self.rollover_image)

class OptionItems():
    def __init__(self, group, data, items):
        self.group = group
        self.group.selected = None
        self.items = items
        
        def handle_select(item, args):
            group.select(self)
            
        for item in items:
            item.add_event_handler(ItemEvent.MOUSE_ENTER, self.handle_mouse_enter)
            item.add_event_handler(ItemEvent.MOUSE_LEAVE, self.handle_mouse_leave)
            item.add_event_handler(ItemEvent.CLICK, handle_select)
    
    def select(self):
        self.group.selected = self
        for item in self.items:
            if getattr(item, 'select', None):
                item.select()
            item.remove_event_handler(ItemEvent.MOUSE_ENTER, self.handle_mouse_enter)
            item.remove_event_handler(ItemEvent.MOUSE_LEAVE, self.handle_mouse_leave)
    
    def unselect(self):
        self.group.selected = None
        for item in self.items:
            if getattr(item, 'unselect', None):
                item.unselect()
            item.add_event_handler(ItemEvent.MOUSE_ENTER, self.handle_mouse_enter)
            item.add_event_handler(ItemEvent.MOUSE_LEAVE, self.handle_mouse_leave)
    
    def handle_mouse_enter(self, item, args):
        for item in self.items:
            if getattr(item, 'mouse_enter', None):
                item.mouse_enter(item, args)
    
    def handle_mouse_leave(self, item, args):
        for item in self.items:
            if getattr(item, 'mouse_leave', None):
                item.mouse_leave(item, args)

"""
--------------------------------------------------------------------------------
"""

class ItemTextSelectable(ItemText):
    def __init__(self, color, rollover_color, *args, **kwargs):
        ItemText.__init__(self, *args, **kwargs)
        self.color = color
        self.rollover_color = rollover_color
        self.add_event_handler(ItemEvent.MOUSE_ENTER, self.handle_mouse_enter)
        self.add_event_handler(ItemEvent.MOUSE_LEAVE, self.handle_mouse_leave)
    
    def handle_mouse_enter(self, item, args):
        item.set_color(self.rollover_color)
    
    def handle_mouse_leave(self, item, args):
        item.set_color(self.color)

class ItemRectSelectable(ItemRect):
    def __init__(self, dif_left, dif_top, dif_width, dif_height, action, items, *args, **kwargs):
        ItemRect.__init__(self, *args, **kwargs)
        self.dif_left = dif_left
        self.dif_top = dif_top
        self.dif_width = dif_width
        self.dif_height = dif_height
        self.action = action
        self.items = items
        for item in self.items:
            item.set_visible(False)
    
    def select(self):
        self.set_left(self.get_left() + self.dif_left)
        self.set_top(self.get_top() + self.dif_top)
        self.set_width(self.get_width() + self.dif_width)
        self.set_height(self.get_height() + self.dif_height)
        if self.action:
            for item in self.items:
                item.set_visible(True)
    
    def unselect(self):
        self.set_left(self.get_left() - self.dif_left)
        self.set_top(self.get_top() - self.dif_top)
        self.set_width(self.get_width() - self.dif_width)
        self.set_height(self.get_height() - self.dif_height)
        if self.action:
            for item in self.items:
                item.set_visible(False)

class CheckBox():
    def __init__(self, stage, data, group = None):
        self.group = group     
        self.selected = False
        self.selected_items = []
        for item in data.selected:
            new_item = stage.create_item(item)[0]
            self.selected_items.append(new_item)
            new_item.CheckBox_relative_position = (new_item.get_left(), new_item.get_top())
        self.unselected_items = []
        for item in data.unselected:
            new_item = stage.create_item(item)[0]
            self.unselected_items.append(new_item)
            new_item.CheckBox_relative_position = (new_item.get_left(), new_item.get_top())
        for item in self.unselected_items:
            item.set_visible(True)
            item.add_event_handler(ItemEvent.CLICK, self.handle_select)
        for item in self.selected_items:
            item.set_visible(False)
            item.add_event_handler(ItemEvent.CLICK, self.handle_unselect)
    
    def exit(self):
        for item in self.selected_items:
            item.exit()
        for item in self.unselected_items:
            item.exit()
        self.unselected_items = None
        self.slected_items = None
        self.group = None
    
    def handle_unselect(self, item, args):
        self.group.unselect() if self.group else self.unselect() 

    def handle_select(self, item, args):
        self.group.select(self) if self.group else self.select()
        
    def select(self):
        if self.selected: return
        self.selected = True
        for item in self.selected_items:
            item.set_visible(True)
        for item in self.unselected_items:
            item.set_visible(False)
    
    def unselect(self):
        if not self.selected: return
        self.selected = False
        for item in self.selected_items:
            item.set_visible(False)
        for item in self.unselected_items:
            item.set_visible(True)
    
    def get_width(self):
        return self.unselected_items[0].get_width()
    
    def get_height(self):
        return self.unselected_items[0].get_height()
    
    def set_left(self, left):
        for item in self.selected_items + self.unselected_items:
            item.set_left(left + item.CheckBox_relative_position[0])
    
    def set_top(self, top):
        for item in self.get_items():
            item.set_top(top + item.CheckBox_relative_position[1])
            
    def get_items(self):
        return self.selected_items + self.unselected_items
    
    

        
