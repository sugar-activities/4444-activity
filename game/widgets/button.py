from framework.stage import assets, ItemEvent, ItemImage, ItemMask, ItemRect, ItemText, Layer, Stage

class Button(ItemImage):
    def __init__(self, data):
        image = assets.load_image(data['src'])
        ItemImage.__init__(self, data.get('left', 0), data.get('top', 0), image)
        self.image = image
        
        if 'rollover_src' in data:
            self.rollover_image = assets.load_image(data['rollover_src'])
        else:
            self.rollover_image = None
            
        if 'pressed_src' in data:
            self.pressed_image = assets.load_image(data['pressed_src'])
        else:
            self.pressed_image = None
             
        if 'click_handler' in data:
            self.click_handler = data['click_handler']
        else:
            self.click_handler = None
        
        # Sounds
        if 'sound_click_handler' in data:
            self.sound_click_handler = data['sound_click_handler']
        else:
            self.sound_click_handler = None
            
        if 'sound_mouse_enter_handler' in data:
            self.sound_mouse_enter_handler = data['sound_mouse_enter_handler']
        else:
            self.sound_mouse_enter_handler = None
            
        if 'disabled_src' in data:
            self.disabled_image = assets.load_image(data['disabled_src'])
            self.on = True
            self.turn_off()
        else:
            self.disabled_image = None
            self.on = False
            self.turn_on()
    
    def exit(self):
        ItemImage.exit(self)
        self.click_handler = None
        self.sound_click_handler = None
        self.sound_mouse_enter_handler = None
        self.presed_image = None
        self.rollover_image = None
        self.image = None
        self.disabled_image = None
    
    def turn_on(self):
        if self.on: return
        self.on = True
        self.set_image(self.image)
        if self.rollover_image:
            self.set_rollover_image(self.rollover_image)
        if self.pressed_image:
            self.set_pressed_image(self.pressed_image)
        if self.click_handler:
            self.add_event_handler(ItemEvent.CLICK, self.sound_click_handler)
            self.add_event_handler(ItemEvent.CLICK, self.click_handler)
        if self.sound_mouse_enter_handler:
            self.add_event_handler(ItemEvent.MOUSE_ENTER, self.sound_mouse_enter_handler)
    
    def turn_off(self):
        if not self.on: return
        self.on = False
        self.set_image(self.disabled_image)
        self.set_rollover_image(None)
        self.set_pressed_image(None)
        self.remove_event_handler(ItemEvent.CLICK, self.click_handler)
        self.remove_event_handler(ItemEvent.CLICK, self.sound_click_handler)
        self.remove_event_handler(ItemEvent.MOUSE_ENTER, self.sound_mouse_enter_handler)
        
