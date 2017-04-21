# -*- coding: latin-1 -*-

# 2011 - Dirección General Impositiva, Uruguay.
# Todos los derechos reservados.
# All rights reserved.

import assets
import engine
import gc
import sounds
import os
import pygame
import math
import sys

from pygame.locals import *

# Constant for the event that is sent when after play the music (when is configured in this way)
MUSIC_ENDSOUND_EVENT = pygame.locals.USEREVENT

# Indicate if the music is streamed of if it is loaded in memory
# Note: In test performed streaming music sometimes we heard noise in the sound
STREAM_MUSIC = False

# Sets the maximum number of milliseconds between two clicks to treat it as a double click
DBLCLICK_DELAY = 500

class Stage:
    """
    Base class to define a stage of a game.
    """

    def __init__(self, game, background=None, target_surface=None):
        """
        Constructor.
        - game: Instance of the game where the stage will be used.
        - background: Color or Image that is drawn in the background. None to use a solid black color.
        - target_surface: Surface where the stage is rendered. None if it is rendered over the screen.
        """

        self.game = game
        self.layers = []
        self.initialized = False
        self.__dialogs = []
        self.__changed_handler = None
        self.__closed_handler = None
        self.__last_click = None
        self.__last_item_stack = None
        self.__update_prerender_buffer = False
        self.__locks = 0

        # Set the target surface
        self.target_surface = target_surface

        # Load the background
        color = Color('#000000')
        if isinstance(background, type(())) or isinstance(background, color.__class__):
            self.__background = None
            self.__background_color = background
        else:
            self.__load_background(background)
        self.__background_dirty = True

        # Create the list to start timers in the stage
        self.__timers = []

        # Initialize the music
        self.__music = None
        self.__music_data = None

        # Initialize the field that marks which item is below the mouse
        self.__over_item = None

        # Initialize the field that marks which item has the focus
        self.__focused_item = None 

        # Initialize the values to define a pre-render buffer
        self.__prerender_to_layer = None
        self.__prerender_buffer = None

        # Set the layer to show an image as the mouse cursor. By default, is
        # not used
        self.__mouse_layer = None
        self.__mouse_cursor = None
        self.__mouse_snap_to_cursor = False
        self.__mouse_update = False
        self.__mouse_real_pos = None
        self.__use_mouse_layer = False
        self.__mouse_pointer = (0, 0)
        self.__leftmousedown_handlers = []

        # Set the default mouse cursor
        if target_surface != None:
            self.__default_mouse_cursor = None
        else:
            default_mouse_cursor = game.get_default_mouse_cursor()
            if default_mouse_cursor != None:
                self.__default_mouse_cursor = ItemImage(0, 0, default_mouse_cursor)
                self.set_mouse_cursor(self.__default_mouse_cursor)
            else:
                self.__default_mouse_cursor = None

        self.__previous_active = True

    def initialize(self):
        """
        This function is invoked to initialize the layer before showing it for
        first time. Its preferred to add initialization code inside this
        function instead of the constructor, because when this function is
        invoked the memory used for the previous stage is released. On the
        contrary, when the constructor is invoked the current stage is still
        loaded in memory.
        """
        pass

    def set_prerender_buffer(self, to_layer):
        """
        Defined a buffer to pre-render the items from the first layer to 'layer' before
        draw them in the screen. The buffer improve the drawing speed if the items
        of the layers that are buffered don't change very often. If the items don't change
        they are blitted directly from the buffer, when they change the buffer must be
        rendered again.
        - to_layer: Last layer that is included in the buffer.
        """
        self.__prerender_to_layer = to_layer
        if self.__prerender_buffer == None:
            if self.target_surface == None:
                window_width, window_height = self.game.get_window_size()
                self.__prerender_buffer = pygame.Surface((window_width, window_height))
            else:
                self.__prerender_buffer = pygame.Surface((self.target_surface.get_width(), self.target_surface.get_height()))
        self.__update_prerender_buffer = True

    def add_layer(self, layer, index = - 1):
        """
        Adds a layer to the stage.
        - layer: Layer.
        - index: Index where the layer in inserted in the layer list. -1
            to add the layer at the end.
        """
        layer.set_stage(self)
        if index == - 1:
            self.layers.append(layer)
        else:
            self.layers.insert(index, layer)
        layer.set_dirty()
        
        # Update the item that is below the mouse 
        self.__mouse_update = True

    def remove_layer(self, layer):
        """
        Remove a layer from the stage
        - layer: Layer
        """        
        if layer in self.layers:            
            if self.__focused_item != None and self.__focused_item[0].get_layer() == layer:
                # The layer of the focused item will be removed, remove the focus
                self.set_focus(None) 

            layer.set_stage(None)
            self.layers.remove(layer)
            self.redraw()
                        
            if self.__prerender_to_layer == layer:
                self.set_prerender_buffer(None)

            for dialog in self.__dialogs:
                if dialog[0] == layer:
                    self.__dialogs.remove(dialog)
                    break
                
            # Update the item that is below the mouse 
            self.__mouse_update = True

    def empty_layers(self):
        """
        Remove all the layers.
        """
        for l in self.layers:
            l.set_stage(None)
        del self.layers[:]
        del self.__dialogs[:]
        self.set_prerender_buffer(None)
        self.redraw()

    def contains_layer(self, layer):
        """
        Determines if the specified layer is already part of the stage.
        """
        return layer in self.layers

    def show_dialog(self, layer, event_handler, background_color=(0, 0, 0, 180), prerender_below = True):
        """
        Shows a layer as a modal dialog. The events are passed to other layers
        until the dialog is closed.
        - layer: Layer with the items of the dialog.
        - event_handler: Function to capture the events. The events are not passed
              to the stage, instead they are passed to the dialog. Use None if you don't
              want to process the events.
        - background_color: Color used to fill a solid rectangle over the layers
              below the dialog. None if you don't want to define a background.
        - prerender_below: Indicates if must prerender the layers that are below the
              dialog in a buffer, to avoid drawing it again each time the dialog
              changes.

        When invoke this function the layer of the dialog is added in the layers
        of the stage. Then you can add new layers to the dialog adding layers
        to the stage. The events (like mouse click) will be passed only to the dialog's
        layer and the layers that were added after it.

        To close the dialog you must invoke close_dialog function. When you invoke
        this function the layer of the dialog is removed from the stage and also the layers
        that were added after it.
        """
        if layer in self.layers:
            raise Exception, "The layer must be a layer of the stage if you want to use it as a dialog"

        if prerender_below:
            # Prerender the stage before the background
            previous_prerender_layer = self.__prerender_to_layer
            if len(self.layers) > 0:
                self.set_prerender_buffer(self.layers[len(self.layers) - 1])
        else:
            previous_prerender_layer = None

        if background_color == None:
            background_layer = None
        else:
            # Create a surface to show below the dialog with the background color
            window_width, window_height = self.game.get_window_size()
            background_surface = pygame.Surface((window_width / 2, window_height / 2), pygame.SRCALPHA, 32)
            background_surface.fill(background_color)
            background_image = assets.Image(background_surface)

            # Add four images to draw the background. We use four images instead of a
            # bigger image to avoid to create a bigger surface and consume 4 times
            # more memory
            background_layer = Layer()
            background_item = ItemImage(0, 0, background_image)
            background_layer.add(background_item)
            background_item = ItemImage(window_width / 2, 0, background_image)
            background_layer.add(background_item)
            background_item = ItemImage(0, window_height / 2, background_image)
            background_layer.add(background_item)
            background_item = ItemImage(window_width / 2, window_height / 2, background_image)
            background_layer.add(background_item)
            self.add_layer(background_layer)

        if pygame.event.get_grab():
            # If the mouse is grabbed, release the mouse
            pygame.event.set_grab(False)            

        # Add the layer of the dialog
        self.add_layer(layer)
        self.__dialogs.append((layer, event_handler, background_layer, previous_prerender_layer))

        # Sets the default mouse cursor for the dialog
        #self.set_mouse_cursor(None)

    def close_dialog(self, layer):
        """
        Close a dialog.
        - layer: Layer with the items of the dialog.
        """

        # Remove the dialog from the list of open dialogs
        for dialog in self.__dialogs:
            if dialog[0] == layer:
                self.__dialogs.remove(dialog)

                # Remove the layer of the dialog (and the layers that were added after it)
                k = 0
                while k < len(self.layers):
                    if self.layers[k] == layer:
                        self.remove_layer(layer)
                        while k < len(self.layers):
                            self.remove_layer(self.layers[k])
                    k += 1

                # Remove the background layer
                background_layer = dialog[2]
                if background_layer != None:
                    self.remove_layer(background_layer)
                    del background_layer

                # Restore the last prerender buffer before open the dialog
                previous_prerender_layer = dialog[3]
                if previous_prerender_layer != None:
                    if previous_prerender_layer in self.layers:
                        self.set_prerender_buffer(previous_prerender_layer)
                    else:
                        self.set_prerender_buffer(None)

        # Register a timer to run the garbage collection in the next cycle to
        # release unreferenced objects. A timer is used because the code
        # that invoke this function could hold references to the dialog.
        # This code was added to avoid memory problems in the XO, because
        # the garbage collector doesn't run as often as it should and the
        # application could run out of memory
        key = "run gc"
        self.stop_timer(key)
        self.start_timer(key, 0, self.__run_gc)

    def has_dialog_opened(self):
        """
        Returns a value that indicates if there is a dialog opened.
        """
        return len(self.__dialogs) > 0

    def blind_dialog(self, layer, direction, background = True, ignore_layers = [], callback = None):
        """
        Apply a blind effect to show or hide the specified dialog.
        - layer: Layer that define the dialog.
        - direction: A value of animations.BlindDirection that indicate the direction of the blind effect.
        - background: Indicates if the effect is applied in the background of the
            dialog (if it is defined).
        - ignore_layers: Indicates a list of layer which the blind effect is not
           applied. For example, if you define layer above the dialog's layer, you
           can use this parameter to avoid to apply the effect over one layer.
        - callback: Function to invoke with parameter layer after apply
            the effect. None if there is no callback function.
        """
        import animations
        
        layers_to_blind = []                
        for dialog in self.__dialogs:
            if dialog[0] == layer:
                duration = 450
                area = None                

                # Store the count of layers, because when the blind effect
                # is applied new dummy layers are created to lock the screen.
                # If we don't do this an infinite loop happens applying the
                # effect for the above layers
                count = len(self.layers)

                # Apply the blind in the background layer
                if dialog[2] != None and background:
                    background_layer = dialog[2]
                    layers_to_blind.append(background_layer)

                # Apply the blind in the layer that define the dialog
                if not layer in ignore_layers:
                    layers_to_blind.append(layer)                                    

                # Apply the blind in the layers above the layer that define the dialog
                if layer in self.layers:
                    k = self.layers.index(layer)
                    k += 1
                    while k < count:
                        above_layer = self.layers[k]

                        if not above_layer in ignore_layers:
                            layers_to_blind.append(above_layer)
                            
                        k += 1

                break
        
        callback_assigned = False
        for i in xrange(len(layers_to_blind)):
            if i == len(layers_to_blind) - 1:
                # Assign the callback in the last layer 
                blind_callback = callback
                callback_assigned = True
            else:
                blind_callback = None
            
            animations.blind_layer(layers_to_blind[i], direction, area, duration, blind_callback)
            
        if not callback_assigned and callback != None:
            # The blind was not applied to any layer, invoke the callback
            callback(layer)

    def lock_ui(self):
        """
        Lock the UI, no keypress and mouse events are captured. For example,
        if the UI is locked CLICK events are not raised.
        """
        self.__locks += 1
        self.__mouse_update = True

    def unlock_ui(self):
        """
        Unlock the UI.
        """
        self.__locks -= 1
        self.__mouse_update = True

    def update_mouse(self):
        """
        Update the item that is below the mouse raising the corresponding
        MOUSE_ENTER/MOUSE_LEAVE events.
        """
        self.__mouse_update = True

    def hit_test(self, x, y):
        """
        Determines if the specified coordinates are over an item. Return
        the topmost item that is below the coordinates, of None if no item found.
        """
        if self.__locks == 0:
            if len(self.__dialogs) == 0:
                i = len(self.layers) - 1
                while i >= 0:
                    layer = self.layers[i]
                    if layer.get_visible() and layer.is_inside_clip(x, y):
                        for item in reversed(layer.items):
                            if item.get_visible() and item.is_over(x, y):
                                return item
                    i -= 1
            else:
                # There is a modal dialog opened. Only consider the layer
                # of the dialog and the layers that were added after it
                dialog_layer = self.__dialogs[len(self.__dialogs) - 1][0]
                i = len(self.layers) - 1
                while i >= 0:
                    layer = self.layers[i]
                    if layer.get_visible() and layer.is_inside_clip(x, y):
                        for item in reversed(layer.items):
                            if item.get_visible() and item.is_over(x, y):
                                return item
                    if layer == dialog_layer:
                        break
                    else:
                        i -= 1

        return None

    def hit_test_stack(self, x, y):
        """
        Determines if the specified coordinates are over one or more items. Return
        the stack of items that are below the coordinates, of an empty list if no item found.
        """
        stack = []
        l = len(self.layers)
        if not l:
            return stack
        if self.__locks > 0:
            i = l
        elif len(self.__dialogs) == 0:
            i = 0
        else:
            dialog_layer = self.__dialogs[len(self.__dialogs) - 1][0]
            i = l - 1
            while i > 0:
                layer = self.layers[i]
                if layer == dialog_layer:
                    break
                else:
                    i -= 1

        while i < l:
            layer = self.layers[i]
            if layer.get_visible() and layer.is_inside_clip(x, y):
                for item in layer.items:
                    if item.get_visible() and item.is_over(x, y):
                        stack.append(item)
            i += 1

        return stack

    def set_music(self, intro, loop):
        """
        Sets the music for the stage.
        - intro: Name of the file with the intro music. None if there is no intro music.
        - loop: Name of the file with the music that is repeated after the intro.

        The music is played automatically when the stage is assigned as the current stage.
        """        
        self.__music = (intro, loop)

    def get_music(self):
        """
        Gets the music defined for the stage (intro, loop).
        """
        return self.__music

    def play_music(self):
        """
        Plays the music associated with the stage.

        This function must not be invoked directly. When you assign a stage
        as the current stage, its music is played automatically.
        """
        if self.__music != None:            
            self.stop_music()                        
            
            intro = self.__music[0]
            loop = self.__music[1]                        

            if STREAM_MUSIC:
                if intro != None:
                    pygame.mixer.music.load('sounds/' + intro)
                    pygame.mixer.music.queue('sounds/' + loop)

                    # Define an event to define the loop
                    pygame.mixer.music.set_endevent(MUSIC_ENDSOUND_EVENT)
                    
                    pygame.mixer.music.play()                                
                else:
                    pygame.mixer.music.load('sounds/' + loop)
                    pygame.mixer.music.play(-1)
                    
                self.__music_data = True
            else:
                # Load the music in memory
                if intro != None:
                    intro_data = assets.load_sound(intro)
                else:
                    intro_data = None
                loop_data = assets.load_sound(loop)
                self.__music_data = (intro_data, loop_data)

                # Reserve the first channel to play the music
                pygame.mixer.set_reserved(1)

                # Play the music
                music_channel = pygame.mixer.Channel(0)
                if intro_data != None:
                    music_channel.set_endevent(MUSIC_ENDSOUND_EVENT)                    
                    music_channel.play(intro_data, 0, 0, 400)
                else:                    
                    music_channel.play(loop_data, -1)

    def stop_music(self):
        """
        Stops the music of the stage if it is playing.
        """
        if self.__music_data != None:            
            self.__music_data = None            

            if STREAM_MUSIC:                
                pygame.mixer.music.fadeout(200)                
            else:                
                music_channel = pygame.mixer.Channel(0)                
                music_channel.fadeout(200)     
                
            # Clear the event, because we don't want to play
            # the next sound after the music
            pygame.event.clear(MUSIC_ENDSOUND_EVENT)           

    def stop_sounds(self):
        """
        Stop all sounds.
        """
        # Stop all channels
        pygame.mixer.stop()

    def get_mouse_cursor(self):
        """
        Gets the item that is used as the mouse's cursor. Returns None if
        there is no item assigned to the mouse.
        """
        return self.__mouse_cursor

    def set_mouse_cursor(self, cursor, pointer=(0, 0), use_mouse_layer=True, update_item_pos=True,
                         move_area=None):
        """
        Sets an item as the mouse cursor.
        - cursor: An item that is used as the mouse cursor. None to use
             the default cursor.
        - pointer: Position where the mouse is located inside the cursor's item.
             This position determines the selection coordinates that are passed to mouse events.
             Use (0, 0) to locate the pointer in the upper-left corner of the image.
        - use_mouse_layer: Indicates if the item is added to the mouse layer
             (which is shown over all other layers)
        - update_item_pos: Indicates if the item is moved to current mouse position.
        - move_area: An instance of Rect that defines the area where the mouse cursor
             could be moved. Also, you can pass a function that is invoked
             to adjust the position, it an (x, y) pair with position of the
             mouse and must return the final position. Use None if you don't
             want to restrict the area where the mouse can be moved.
        """
        if self.__mouse_cursor != cursor:
            # Prepare the to show the mouse cursor (if necessary)
            if use_mouse_layer:
                if self.__mouse_layer == None:
                    self.__mouse_layer = Layer()
                    self.__mouse_layer.set_stage(self)

                # Set the image in the mouser layer (or remove it)
                if cursor == None:
                    self.__mouse_layer.empty()
                elif not (self.__mouse_layer.contains(cursor)):
                    self.__mouse_layer.empty()
                    self.__mouse_layer.add(cursor)
            else:
                if self.__mouse_layer != None:
                    self.__mouse_layer.empty()

            if update_item_pos and cursor != None:
                # Move the cursor item to the mouse's cursor position
                if self.__mouse_snap_to_cursor:
                    if self.__mouse_cursor != None:
                        x = self.__mouse_cursor.get_left() + self.__mouse_pointer[0]
                        y = self.__mouse_cursor.get_top() + self.__mouse_pointer[1]
                        cursor.set_lefttop(x - pointer[0], y - pointer[1])
                else:
                    x, y = pygame.mouse.get_pos()
                    x = int(x / engine.SCREEN_FACTOR)
                    y = int(y / engine.SCREEN_FACTOR)
                    cursor.set_lefttop(x - pointer[0], y - pointer[1])

            self.__mouse_cursor = cursor
            self.__use_mouse_layer = use_mouse_layer
            self.__mouse_move_area = move_area
            self.__mouse_pointer = pointer
            self.__mouse_update = True

            # Mark that the mouse must be repositioned to match the cursor position.
            # The position is updated later because mouse.set_pos doesn't work
            # if this function is called when processing a mouse event.
            if cursor != None and not update_item_pos:
                self.__mouse_snap_to_cursor = True

            # Hide or show the standard cursor
            if cursor == None:
                if self.__default_mouse_cursor != None:
                    self.set_mouse_cursor(self.__default_mouse_cursor)
                    pygame.mouse.set_visible(False)
                    self.__mouse_snap_to_cursor = False
                else:
                    pygame.mouse.set_visible(True)
            else:
                pygame.mouse.set_visible(False)

    def set_mouse_pos(self, x, y):
        """
        Sets the mouse position to the specified (x, y).
        - x: X coordinate.
        - y: Y coordinate.
        """
        # Mark that the mouse must be repositioned to match the cursor position.
        # The position is updated later because mouse.set_pos doesn't work
        # if this function is called when processing a mouse event.
        if self.__mouse_cursor != None:
            self.__mouse_cursor.set_lefttop(x - self.__mouse_pointer[0], y - self.__mouse_pointer[1])
            self.__mouse_snap_to_cursor = True
    
    def redraw_mouse(self):
        """
        Redraw the layer used to display an item as the mouse cursor.
        """  
        if self.__mouse_layer != None:
            self.__mouse_layer.set_dirty()

    def capture_leftmousedown(self, item, handler):
        """
        Indicate a function that must receive all mouse move events while
        the left mouse button is pressed.
        - item: Item associated with the mouse capture. The MOUSE_ENTER/MOUSE_LEAVE
          are only raised in this item while the left mouse button is not
          released.
        - handler: Function to invoke. The function is invoked each time the mouse
        is moved or when the left mouse button is released. It is invoked with
        an instance of ItemEventArgsMouse, and a boolean argument, the last argument
        is a boolean that indicates if the mouse was released.

        If the left mouse button is not pressed when this function is invoked
        it invokes the handler with true in the last argument.
        """
        button1 = pygame.mouse.get_pressed()[0]
        if not button1:
            # The button is not pressed. Check if is pressed with the keys
            # that control the mouse
            key = "mouse_button_keys"
            if self.is_timer_started(key):
                data = self.get_timer_data(key)
                if data != None and data[0]:
                    button1 = True
        
        if not button1:
            # The left button is not pressed
            x, y = pygame.mouse.get_pos()
            x = int(x / engine.SCREEN_FACTOR)
            y = int(y / engine.SCREEN_FACTOR)
            args = ItemEventArgsMouse(x, y)
            handler(args, True)
        else:
            handler_defined = False
            for handler_data in self.__leftmousedown_handlers:
                if handler_data[0] == item and handler_data[1] == handler:
                    handler_defined = True
                    break

            if not handler_defined:
                self.__leftmousedown_handlers.append((item, handler))

    def start_timer(self, key, milliseconds, func, data=None, drop_ticks=False, render_first = False):
        """
        Starts a timer. The specified function is invoked every given number
        of milliseconds.
        - key: Key that is associated with the timer. It could be any type of object.
        - milliseconds: Number of milliseconds between each call. The first
              invoke is not performed until the amount of time has passed.
        - func: Function that is invoked with this parameters (key, data).
        - data: Data to include in the arguments of the function.
        - drop_ticks: Indicate if must ignore invocations if the elapsed time is
          greater than two times the number of milliseconds. For example, if you set
          a timer for 100ms, and a heavy process is executed and the time between ticks
          is 300ms. If you set False in this parameter, the func is invoked three times
          to recover the lost time, if you set True, only one invocation is performed and
          other ones are "dropped".
        - render_first: If True is indicated in this parameter a full render is performed
          before invoke the timer for first time.

        If there is a timer started with the same key stop the timer.
        """
        # If the timer is already defined throw an exception
        i = 0
        while i < len(self.__timers):
            if self.__timers[i].key == key:
                # The timer is already defined. Stop the timer
                self.stop_timer(key)                
                break                
            i += 1

        # Add the timer
        milliseconds = max(1, milliseconds)
        self.__timers.append(Stage.TimerData(key, milliseconds, func, data, drop_ticks, render_first))

    def stop_timer(self, key):
        """
        Stops a timer.
        - key: Key of the timer.

        Return the timer data, or None if the timer is not active.
        """
        i = 0
        while i < len(self.__timers):
            if self.__timers[i].key == key:
                # Delete the timer
                data = self.__timers[i].data
                del self.__timers[i]
                return data
            i += 1

        return None

    def stop_timers(self):
        """
        Stops all the timers defined in the stage.
        """
        while len(self.__timers) > 0:
            del self.__timers[len(self.__timers) - 1]

    def is_timer_started(self, key):
        """
        Determines if a timer is enabled.
        - key: Key of the timer.
        """
        i = 0
        while i < len(self.__timers):
            if self.__timers[i].key == key:
                return True
            i += 1

        return False

    def get_timer_data(self, key):
        """
        Get the data associated with the timer with the specified key.
        - key: Key.
        """
        i = 0
        while i < len(self.__timers):
            if self.__timers[i].key == key:
                return self.__timers[i].data
            i += 1

        return None

    def get_key_repeat(self):
        """
        Gets the key repeat configuration for the stage. Returns (delay, interval) or
        None if key repeat is disabled for the stage. The delay is the number of milliseconds
        before the first repeated pygame.KEYDOWN will be sent. After that another
        pygame.KEYDOWN will be sent every interval milliseconds.
        """
        return None

    def get_changed_handler(self):
        """
        Gets the function that is invoked when the items of the stage changed. Return
        None is no function is defined.
        """
        return self.__changed_handler

    def set_changed_handler(self, changed_handler):
        """
        Sets the function that is invoked when the items of the stage changed.
        - changed_handler: Function with parameter (stage). None if there is no
              function associated with changed event.
        """
        self.__changed_handler = changed_handler

    def get_closed_handler(self):
        """
        Gets the function that is invoked when the stage is closed. Return None
        is no function is defined.
        """
        return self.__closed_handler

    def set_closed_handler(self, closed_handler):
        """
        Sets a function that is invoked when the stage is closed to show another
        stage or because the application will be closed.
        - close_handler: Function with parameter (stage). None if there is no
              function associated with close event.
        """
        self.__closed_handler = closed_handler

    def set_focus(self, item, set_focus_data = None):
        """
        Sets the focus in the specified item.
        - item: Item where the focus is set. None to remove the focus.
        - set_focus_data: Data associated with the set focus.
        """
        old_focused_item = self.__focused_item
        if old_focused_item != None:
            old_item = old_focused_item[0]                        
            old_data = old_focused_item[1]
        else:
            old_item = None
            
        if old_item != item:        
            self.__focused_item = None
            
            if old_item != None:
                old_item.on_lost_focus(self, old_data)            
                old_item.fire_event(ItemEvent.LOST_FOCUS, ItemEventArgs())            
            
            if item == None:
                self.__focused_item = None               
            else:
                data = item.on_got_focus(set_focus_data)
                self.__focused_item = (item, data)            
                item.fire_event(ItemEvent.GOT_FOCUS, ItemEventArgs())

    def get_focus(self):
        """
        Gets the item that has the focus.
        """
        if self.__focused_item == None:
            return None
        else:
            return self.__focused_item[0]

    def get_focus_data(self):
        """
        Gets the data associated with the focused item.
        """
        if self.__focused_item == None:
            return None
        else:
            return self.__focused_item[1]
        
    def get_over_item(self):
        """
        Gets the item that is below the mouse (only items that capture
        MOUSE_ENTER/MOUSE_LEAVE events are considered)
        """
        return self.__over_item

    def notify_tick(self):
        """
        This function is invoked to notify a new CPU cycle. It must process
        the events (keyboard, mouse), draw the stage, play sounds, etc. You
        should not invoke this function directly.
        """

        # Determine the with function will process the events
        if self.__locks > 0:
            event_handler = None
        elif len(self.__dialogs) == 0:
            event_handler = self.handle_event
        else:
            event_handler = self.__dialogs[len(self.__dialogs) - 1][1]

        # Handle input events
        for event in pygame.event.get():
            processed = False
            
            if event.type == MOUSEMOTION:
                self.__on_mouse_move(event.pos[0], event.pos[1], event.buttons, event.rel[0], event.rel[1])
            elif event.type == QUIT:
                if self.handle_quit():
                    self.game.quit()
                processed = True
            elif event.type == KEYDOWN:
                if event.key == K_f and event.mod & (KMOD_CTRL | KMOD_ALT):
                    self.game.set_show_fps(not self.game.get_show_fps())
                    processed = True
                elif event.key == K_F10 or \
                    (event.mod == pygame.KMOD_LSHIFT and event.key == pygame.K_0):
                    design_stage = self.game.get_design_stage()
                    if design_stage != None and self.game.get_development_mode():
                        self.game.set_stage(design_stage)
                        processed = True
            elif event.type == MOUSEBUTTONDOWN:
                self.__on_mouse_button_down(event.pos[0], event.pos[1], event.button)
            elif event.type == MOUSEBUTTONUP:
                self.__on_mouse_button_up(event.pos[0], event.pos[1], event.button)                
            elif event.type == ACTIVEEVENT:
                if event.gain:
                    if not self.__previous_active:
                        if self.__use_mouse_layer:
                            if (self.__mouse_layer != None) and (not self.__mouse_layer.contains(self.__mouse_cursor)):
                                self.__mouse_layer.add(self.__mouse_cursor)

                        self.__previous_active = True
                else:
                    if self.__previous_active:
                        if self.__mouse_layer != None:
                            self.__mouse_layer.empty()

                        self.__previous_active = False
            elif event.type == MUSIC_ENDSOUND_EVENT:                
                if self.__music_data != None:
                    if self.__music != None:
                        if STREAM_MUSIC:
                            # Play the loop
                            pygame.mixer.music.load('sounds/' + self.__music[1])
                            pygame.mixer.music.play(-1)                            
                        else:
                            music_channel = pygame.mixer.Channel(0)
                            music_channel.play(self.__music_data[1], - 1)                            
                    if STREAM_MUSIC:
                        pygame.mixer.music.set_endevent()

            if not processed and self.__focused_item != None:
                if self.__focused_item[0].handle_event_focused(event, self.__focused_item[1]):
                    processed = True                            

            if not processed and event_handler != None:
                event_handler(event)
                
            if not processed:
                self.__process_mouse_keys(event)                                

        # Render the stage in the target surface
        self.render()
    
    def handle_quit(self):
        return True
    
    def __on_mouse_move(self, x, y, buttons, rel_x, rel_y):
        """
        This method is invoked to process a event indicating that
        the mouse was moved.
        """
        
        # If the mouse is being controled with the keys, take the
        # button pressed        
        data = self.get_timer_data("mouse_button_keys")
        if data != None:
            buttons = data[0]            
        
        # The mouse was moved inside the stage. If the default cursor
        # is used verifies that cursor is in the mouse layer
        # (see ACTIVEEVENT). This is defensive programming practice,
        # sometimes a ACTIVEEVENT with gain = 0 is raised but then
        # the ACTIVEEVENT with gain = 1 is not raised
        if self.__use_mouse_layer:
            if ((self.__mouse_layer != None) and (not self.__mouse_layer.contains(self.__mouse_cursor))):
                self.__mouse_layer.add(self.__mouse_cursor)
        self.__previous_active = True

        # Check if the mouse is over an object to fire MOUSE_ENTER and MOUSE_LEAVE
        # event
        event = pygame.event.Event(MOUSEMOTION,
                            {'pos' : (int(x / engine.SCREEN_FACTOR), int(y / engine.SCREEN_FACTOR)),
                             'rel' : (int(rel_x / engine.SCREEN_FACTOR), int(rel_y / engine.SCREEN_FACTOR)),
                             'buttons' : buttons})

        x, y = event.pos
        item_stack = self.__update_over_item(x, y)

        # Fire MOUSE_MOVE event in the first item that handle it
        self.__fire_routed_event(item_stack, ItemEvent.MOUSE_MOVE, ItemEventArgsMouse(x, y))

        # If there are handlers capturing the left mouse down invoke
        # the handlers
        if event.buttons[0] == 1 and len(self.__leftmousedown_handlers) > 0:
            x = event.pos[0]
            y = event.pos[1]
            args = ItemEventArgsMouse(x, y)
            for handler_data in self.__leftmousedown_handlers:
                handler_data[1](args, False)
    
    def __on_mouse_button_down(self, x, y, button):
        """
        This method is invoked to process a event indicating that
        a mouse button was pressed.
        """
        event = pygame.event.Event(MOUSEBUTTONDOWN,
                                    {'pos': (int(x / engine.SCREEN_FACTOR), int(y / engine.SCREEN_FACTOR)),
                                     'button': button})

        if event.button == 1:
            # Check if the click was performed over an item
            item_stack = None
            if self.__mouse_cursor != None:
                x = self.__mouse_cursor.get_left() + self.__mouse_pointer[0]
                y = self.__mouse_cursor.get_top() + self.__mouse_pointer[1]
                if pygame.event.get_grab():
                    # The mouse cursor capture all the mouse events
                    item_stack = [self.__mouse_cursor]
            else:
                x = event.pos[0]
                y = event.pos[1]
            if item_stack == None:
                item_stack = self.hit_test_stack(x, y)
                
            if self.__focused_item != None:
                if not self.__focused_item[0] in item_stack:
                    self.set_focus(None) 

            # Check if there was a double click
            dblclick = False
            if self.__last_click != None:
                if pygame.time.get_ticks() - self.__last_click < DBLCLICK_DELAY:
                    dblclick = True
            if dblclick:
                self.__last_click = None
            else:
                self.__last_click = pygame.time.get_ticks()

            if item_stack != None and len(item_stack) > 0:
                ## Fire the CLICK event in the item
                #self.__fire_routed_event(item_stack, ItemEvent.CLICK, ItemEventArgsMouse(x, y))
                self.__fire_routed_event(item_stack, ItemEvent.PRESS, ItemEventArgsMouse(x, y))
                self.__last_item_stack = item_stack

                if dblclick:
                    # Fire the DBLCLICK event in item
                    self.__fire_routed_event(item_stack, ItemEvent.DBLCLICK, ItemEventArgsMouse(x, y))

    def __on_mouse_button_up(self, x, y, button):
        """
        This method is invoked to process a event indicating that
        a mouse button was released.
        """
        event = pygame.event.Event(MOUSEBUTTONUP,
                            {'pos': (int(x / engine.SCREEN_FACTOR), int(y / engine.SCREEN_FACTOR)),
                             'button': button})
        
        item_stack = None
        if self.__mouse_cursor != None:
            x = self.__mouse_cursor.get_left() + self.__mouse_pointer[0]
            y = self.__mouse_cursor.get_top() + self.__mouse_pointer[1]
            if pygame.event.get_grab():
                # The mouse cursor capture all the mouse events
                item_stack = [self.__mouse_cursor]
        else:
            x = event.pos[0]
            y = event.pos[1]
        if item_stack == None:
            item_stack = self.hit_test_stack(x, y)
        
        if item_stack == self.__last_item_stack:
            # Fire the CLICK event in the item
            self.__fire_routed_event(item_stack, ItemEvent.CLICK, ItemEventArgsMouse(x, y))
            
        if event.button == 1 and len(self.__leftmousedown_handlers) > 0:
            x = event.pos[0]
            y = event.pos[1]
            args = ItemEventArgsMouse(x, y)
            for handler_data in self.__leftmousedown_handlers:
                handler_data[1](args, True)
            self.__leftmousedown_handlers = []
    
            # Update the item over the mouse, because when the mouse
            # is captured the MOUSE_ENTER/MOUSE_LEAVE events are
            # not raised in the items the are not associated with
            # the mouse capture
            self.__update_over_item(x, y)
            
    def __process_mouse_keys(self, event):
        """
        Process the keys that control the mouse.
        """
        if event.type == KEYDOWN:
            if event.key == K_KP4 or \
              event.key == K_KP6 or \
              event.key == K_KP2 or \
              event.key == K_KP8:
                key = 'mouse_pos_keys'
                
                data = self.get_timer_data(key)
                if data == None:
                    data = [1]
                                                
                self.start_timer(key, 30, self.__update_mouse_position_keys, data)                
                self.__update_mouse_position_keys(key, data)
            elif event.key == K_KP7 or \
              event.key == K_KP9 or \
              event.key == K_KP1 or \
              event.key == K_KP3:
                key = 'mouse_button_keys'
                
                data = self.get_timer_data(key)
                if data == None:
                    data = [[False, False, False]]
                     
                self.start_timer(key, 30, self.__update_mouse_button_keys, data)                
                self.__update_mouse_button_keys(key, data)
                                        
                
    def __update_mouse_position_keys(self, key, data):
        """
        This method is invoked to update the mouse position with the key
        pressed.
        """
        increment = data[0]
        if increment < 30:
            data[0] += 1
        increment *= engine.SCREEN_FACTOR
        
        pressed = pygame.key.get_pressed()
        x, y = pygame.mouse.get_pos()        
        
        processed = False
        if pressed[K_KP4]:
            x -= increment
            processed = True
        if pressed[K_KP6]:
            x += increment
            processed = True
        if pressed[K_KP8]:
            y -= increment
            processed = True
        if pressed[K_KP2]:
            y += increment
            processed = True
        
        if not processed:
            self.stop_timer(key)
        else:
            if x < 0:
                x = 0
            if y < 0:
                y = 0
                
            screen_width = engine.SCREEN_WIDTH * engine.SCREEN_FACTOR
            screen_height = engine.SCREEN_HEIGHT * engine.SCREEN_FACTOR
            if x >= screen_width:
                x = screen_width - 1
            if y >= screen_height:
                y = screen_height - 1
                
            pygame.mouse.set_pos(x, y)                    
                              
    def __update_mouse_button_keys(self, key, data):
        """
        This method is invoked to update the mouse button with the key
        pressed.
        """
        old_state = data[0]
        new_state = [False, False, False]
        data[0] = new_state
        
        pressed = pygame.key.get_pressed()        
        processed = False
        if pressed[K_KP3]:
            new_state[0] = True
            processed = True
        
        for i in xrange(len(old_state)):
            if old_state[i] != new_state[i]:
                x, y = pygame.mouse.get_pos()
                if new_state[i]:                    
                    self.__on_mouse_button_down(x, y, i + 1)
                else:                    
                    self.__on_mouse_button_up(x, y, i + 1)
        
        if not processed:
            self.stop_timer(key)                
            
    def __run_gc(self, key, data):
        """
        Runs the Garbage Collector
        - key: Timer key.
        - data: Timer data.
        """
        self.stop_timer(key)
        gc.collect()

    def __fire_routed_event(self, item_stack, click_type, args):
        """
        Fires a routed event.
        - item_stack: Item stack below the mouse position.
        - click_type: Click type.
        - args: Event args.
        """
        # Fire the event in the first element that handle it
        k = len(item_stack) - 1
        while k >= 0:
            if item_stack[k].fire_event(click_type, args):
                # The event was handled
                break

            k -= 1

    def __draw_background(self, surface, dirty_rects):
        """
        Draw the background over the dirty rects.
        - surface: Target surface
        - dirty_rects: Dirty rects where the background must be draw
        """
        surface.set_clip(Rect(0, 0, 9999, 9999)) # We use a big rect instead None because the None value doesn't work with Pysco in the X0
        if self.__background == None:
            bgd_color = self.__background_color
            for dirty_rect in dirty_rects:
                surface.fill(bgd_color, dirty_rect)
        else:
            surface_blit = surface.blit
            bgd_surface = self.__background.surface
            for dirty_rect in dirty_rects:
                surface_blit(bgd_surface, dirty_rect, dirty_rect)

    def __update_over_item_callback(self, key, data):
        """
        Update the item that is below the mouse. This function is
        invoked from a timer.
        - key: Timer key.
        - data: Timer data.
        """
        self.stop_timer(key)
        x, y = pygame.mouse.get_pos()
        self.__update_over_item(int(x / engine.SCREEN_FACTOR), int(y / engine.SCREEN_FACTOR))

    def __update_over_item(self, x, y):
        """
        Update the item that is below the mouse.
        - x: X coordinate of the mouse in the stage.
        - y: Y coordinate of the mouse in the stage.
        """
        item_stack = self.hit_test_stack(x, y)

        # Set the first item that define a mouse enter/leave
        if self.__mouse_cursor != None and not self.__use_mouse_layer:
            # The mouse is used to move an item, mark this item as the item that is below the mouse.
            # This code ensure that MOUSEENTER/MOUSELEAVE are not fired over other items while
            # an item is moved with the mouse
            new_over_item = self.__mouse_cursor
        else:
            k = len(item_stack) - 1
            new_over_item = None
            while k >= 0:
                item = item_stack[k]
                if item.has_event_handler(ItemEvent.MOUSE_ENTER) or item.has_event_handler(ItemEvent.MOUSE_LEAVE):
                    new_over_item = item
                    break

                k -= 1

        if self.__over_item != new_over_item:
            if len(self.__leftmousedown_handlers) > 0:
                # There are handlers defined to capture the mouse. The
                # MOUSE_ENTER/MOUSE_LEAVE are only raised in items associated
                # with mouse capture
                over_captured_item = False
                for handler_data in self.__leftmousedown_handlers:
                    if handler_data[0] == new_over_item:
                        over_captured_item = True
                if not over_captured_item:
                    new_over_item = None

            old_over_item = self.__over_item 
            self.__over_item = new_over_item
            
            if old_over_item != None:
                old_over_item.fire_event(ItemEvent.MOUSE_LEAVE, ItemEventArgsMouse(x, y))
            if self.__over_item != None:
                self.__over_item.fire_event(ItemEvent.MOUSE_ENTER, ItemEventArgsMouse(x, y))

        return item_stack

    def prepare(self):
        """
        This function after the stage is selected as the current stage, and before show it.
        """
        pass

    def render(self):
        """
        Render the stage in the target surface. This function redraw
        the items that has changed in the stage since previous render.
        """
        # Update the mouse (if necessary)
        pos = pygame.mouse.get_pos()
        if pos != self.__mouse_real_pos or self.__mouse_update:
            self.__mouse_real_pos = pos
            self.__mouse_update = False

            x = int(pos[0] / engine.SCREEN_FACTOR)
            y = int(pos[1] / engine.SCREEN_FACTOR)

            self.__update_over_item(x, y)
            if self.__mouse_cursor != None:
                self.__update_mouse_cursor_position(x, y)

        # Invoke the functions associated with the timers
        timers = self.__timers
        if len(timers) > 0:
            ticks = pygame.time.get_ticks()
            i = 0
            while i < len(timers):
                timer = timers[i]                

                if timer.render_first:
                    # The timer is invoked after perform this full render
                    timer.render_first = False
                else:                    
                    while ticks >= timer.tick:                                                            
                        # Invoke the function associated with the timer                        
                        timer.func(timer.key, timer.data)

                        # Check if the timer is still defined because it could
                        # be stopped during previous invocation
                        if not timer in timers:
                            i -= 1
                            break

                        if timer.drop_ticks:
                            while ticks >= timer.tick:
                                timer.tick += timer.milliseconds
                            break;
                        else:
                            # Increment the timer
                            timer.tick += timer.milliseconds

                i += 1

        # Get the target surface where the stage is rendered
        target_surface = self.target_surface
        if target_surface == None:
            target_surface = self.game.window

        # Get the time elapsed from the previous frame
        frame_delay = self.game.get_frame_delay()

        # Update the items and calculate the rects that must by
        # updated (the dirty rects)
        dirty_rects = []
        prerender_dirty_rects = []
        prerender = (self.__prerender_to_layer != None)
        for l in self.layers:
            if prerender:
                l.update(prerender_dirty_rects, frame_delay)
                prerender = (self.__prerender_to_layer != l)

                if len(prerender_dirty_rects) > 6:
                    self.__compact_dirty_rects(prerender_dirty_rects)
            else:
                l.update(dirty_rects, frame_delay)
                if len(prerender_dirty_rects) > 6:
                    self.__compact_dirty_rects(dirty_rects)
        if self.target_surface != None:
            loading_layer = None
        else:
            loading_layer = self.game.loading_layer
            if loading_layer != None:             
                loading_layer.update(dirty_rects, frame_delay)                                
        if self.__mouse_layer != None:
            self.__mouse_layer.update(dirty_rects, frame_delay)

        # Check if must update the background
        if self.__background_dirty:
            if self.__prerender_to_layer != None:
                prerender_dirty_rects = [target_surface.get_rect()]
                dirty_rects = []
            else:
                dirty_rects = [target_surface.get_rect()]
            self.__background_dirty = False

        # Check if some layers are prerendered
        prerender = (self.__prerender_to_layer != None)
        if prerender:
            if self.__update_prerender_buffer:
                # Should draw all the prebuffer
                self.__update_prerender_buffer = False;
                prerender_rects = [target_surface.get_rect()]
            else:
                prerender_rects = prerender_dirty_rects

        # Draw the background (if it is needed)
        if self.__prerender_to_layer != None:
            self.__draw_background(self.__prerender_buffer, prerender_rects)
        else:
            self.__draw_background(target_surface, dirty_rects)

        # Draw the layers
        for l in self.layers:
            # Draw the layer. Only draw the dirty rects (these are the
            # areas of the stage that were modified)
            if prerender:
                if l.get_visible():
                    l.draw(self.__prerender_buffer, prerender_rects)
                if self.__prerender_to_layer == l:
                    for prerender_dirty_rect in prerender_dirty_rects:
                        k = prerender_dirty_rect.collidelist(dirty_rects)
                        while k != - 1:
                            prerender_dirty_rect.union_ip(dirty_rects[k])
                            del dirty_rects[k]
                            k = prerender_dirty_rect.collidelist(dirty_rects)
                        dirty_rects.append(prerender_dirty_rect)
                    if len(dirty_rects) > 0:
                        self.__draw_prerender_buffer(target_surface, dirty_rects)
                    prerender = False
            else:
                if l.get_visible():
                    l.draw(target_surface, dirty_rects)
        if loading_layer != None:
            loading_layer.draw(target_surface, dirty_rects)
        elif self.__mouse_layer != None:
            self.__mouse_layer.draw(target_surface, dirty_rects)

        # Update the stage in the display if the target it the screen
        if self.target_surface == None:
            # Show FPS (if necessary)
            if self.game.get_show_fps():
                self.game.draw_fps(dirty_rects)

            # Update the screen
            self.game.update_display(dirty_rects)

    def __compact_dirty_rects(self, dirty_rects):
        """
        Reduce the list of dirty rects, to avoid to have a large list
        that could affect the performance in drawing partial items.
        - dirty_rects: Dirty rects.
        """
        while len(dirty_rects) > 6:
            dirty_rect = dirty_rects[0]
            dirty_rect.union_ip(dirty_rects[1])
            del dirty_rects[0:1]
            k = dirty_rect.collidelist(dirty_rects)
            while k != - 1:
                dirty_rect.union_ip(dirty_rects[k])
                del dirty_rects[k]
                k = dirty_rect.collidelist(dirty_rects)
            dirty_rects.append(dirty_rect)

    def __draw_prerender_buffer(self, target_surface, dirty_rects):
        """
        Draw the pre-render buffer in the target surface.
        - target_surface: Target surface.
        - dirty_rect: Dirty rects.
        """
        for dirty_rect in dirty_rects:
            target_surface.set_clip(dirty_rect)
            target_surface.blit(self.__prerender_buffer, dirty_rect, dirty_rect)


    def __load_background(self, image):
        """
        Load the background
        - image: Image that is drawn in the background.
        """

        if image == None:
            self.__background = None
            self.__background_color = Color("#000000")
        else:
            rect = image.get_real_rect()
            if self.target_surface == None:
                stage_width, stage_height = self.game.get_window_size()
            else:
                stage_width, stage_height = self.target_surface.get_size()

            if (rect.width >= stage_width) and (rect.height >= stage_height):
                # The image occupies the entire stage
                self.__background = image
            else:
                # The image is smaller than the stage's area. It is repeated to
                # cover all the stage
                surface = pygame.Surface((stage_width, stage_height))
                y = 0
                while (y < stage_height):
                    x = 0
                    while (x < stage_width):
                        surface.blit(image.surface, (x, y), rect)
                        x += rect.width
                    y += rect.height
                self.__background = assets.Image(surface)


    def __update_mouse_cursor_position(self, x, y):
        """
        Updates the mouse cursor position.
        - x: X coordinate of the mouse.
        - y: Y coordinate of the mouse.
        """
        if self.__mouse_snap_to_cursor:
            # Move the mouse to the upper left corner of the cursor
            pygame.mouse.set_pos(int((self.__mouse_cursor.get_left() + self.__mouse_pointer[0]) * engine.SCREEN_FACTOR),
                                 int((self.__mouse_cursor.get_top() + self.__mouse_pointer[1]) * engine.SCREEN_FACTOR))
            self.__mouse_snap_to_cursor = False
        else:
            if self.__mouse_move_area != None:
                if callable(self.__mouse_move_area):
                    x, y = self.__mouse_move_area(x, y)
                else:
                    # Check if the mouse is outside the move area and adjust it
                    cursor_width = self.__mouse_cursor.get_width()
                    cursor_height = self.__mouse_cursor.get_height()
                    if x < self.__mouse_move_area.left:
                        x = self.__mouse_move_area.left
                    elif x + cursor_width > self.__mouse_move_area.right:
                        x = self.__mouse_move_area.right - cursor_width
                    if y < self.__mouse_move_area.top:
                        y = self.__mouse_move_area.top
                    elif y + cursor_height > self.__mouse_move_area.bottom:
                        y = self.__mouse_move_area.bottom - cursor_height

                if x != None and y != None:
                    pygame.mouse.set_pos(int(x * engine.SCREEN_FACTOR),
                      int(y * engine.SCREEN_FACTOR))

            if x != None and y != None:
                # Set the mouse position to the mouse cursor's item
                self.__mouse_cursor.set_lefttop(x - self.__mouse_pointer[0], y - self.__mouse_pointer[1])


    def handle_event(self, e):
        """
        Handle an event in the stage.
        - e: Event.
        """

        # This function must be overriden
        return 0

    def redraw(self):
        """
        Redraws the entire stage
        """
        self.__background_dirty = True
        if self.__changed_handler != None:
            self.__changed_handler(self)

        # Update the item below the mouse before show the stage
        self.__mouse_update = True

    class TimerData:
        """
        Contains the data of a timer
        """

        def __init__(self, key, milliseconds, func, data, drop_ticks, render_first):
            """
            Constructor
            - key: Key associated with the timer.
            - milliseconds: Milliseconds of the timer.
            - func: Function to invoke for each tick of the timer.
            - data: Data associated with the timer.
            - drop_ticks: Indicate if must ignore invocations if the elapsed time is
              greater than two times the number of milliseconds.
            - render_first: Indicates if a full render is performed before
              invoke the timer.
            """
            self.key = key
            self.tick = pygame.time.get_ticks() + milliseconds
            self.milliseconds = milliseconds
            self.func = func
            self.data = data
            self.drop_ticks = drop_ticks
            self.render_first = render_first

class StageIso(Stage):
    """
    Stage with helper functions to show items in a isometric perspective.
    """

    def __init__(self, game, tags, background_image=None, target_surface=None):
        """
        Constructor
        - game: Instance of the game where the stage will be used.
        - tags: List with possible tags. First tags define lower z-indexes to the items associated with them.
        - background_image: Image that is drawn in the background. None to use a solid black color.
        - target_surface: Surface where the stage is rendered. None if it is rendered over the screen.
        """
        Stage.__init__(self, game, background_image, target_surface)

        self.__origin = (300, 200)
        self.__cell_width = 80
        self.__cell_height = 40
        self.__multiplier = 1
        self.__item_definitions = {}
        self.__item_images_cache = {}
        self.__item_masks_cache = {}
        self.__set_name = ""
        self.__image_suffix = ""
        self.__tags = tags
        self.__adjust_positions = None


    def add_layer(self, layer, index= - 1):
        """
        Adds a layer to the stage
        - layer: Layer
        - index: Index where the layer in inserted in the layer list. -1
            to add the layer at the end.
        """
        Stage.add_layer(self, layer, index)
        self.mark_update_positions(layer, None)

    def get_rowcol(self, x, y):
        """
        Gets the (row, columns) associated with the specified coordinates.
        - X: X coordinate.
        - Y: Y coordinate.
        """
        x -= (self.__origin[0] * self.__multiplier)
        y -= (self.__origin[1] * self.__multiplier)

        m = float(-self.__cell_height) / self.__cell_width
        t1 = y / (2 * m)
        t2 = x / 2
        t3 = (self.__cell_width * self.__multiplier) / 2

        row = int(math.floor((-t1 - t2) / t3))
        col = int(math.floor((-t1 + t2) / t3))

        return row, col

    def get_xy(self, row, col):
        """
        Gets the (x, y) coordinates of the center of the specified cell.
        - row: Cell's row.
        - col: Cell's column.
        """
        x = self.__origin[0] * self.__multiplier + \
            (self.__cell_width / 2) * self.__multiplier * (col - row)
        y = self.__origin[1] * self.__multiplier + \
            (self.__cell_height / 2) * self.__multiplier * (row + col + 1)

        return int(x), int(y)

    def get_items_over(self, item):
        """
        Returns a list with the items that are over 'item' (of type ItemCell) in
        the same layer.
        - item: Item.
        """
        # If there are pending updated perform the updates before search the items
        self.__update_positions()

        # Add the items over the specified item
        items_over = []
        layer = item.get_layer()
        if layer != None:
            row_from, col_from = item.get_position()
            size = item.get_definition().size
            row_to = row_from + size[0] - 1
            col_to = col_from + size[1] - 1
            items = layer.items
            k = layer.items.index(item)
            l = len(items)
            k += 1
            while k < l:
                citem = items[k]
                crow_from, ccol_from = citem.get_position()
                csize = citem.get_definition().size
                crow_to = crow_from + csize[0] - 1
                ccol_to = ccol_from + csize[1] - 1
                if crow_to >= row_from and crow_from <= row_to and ccol_to >= col_from and ccol_from <= col_to:
                    items_over.append(citem)
                else:
                    break
                k += 1


        return items_over

    def hit_test(self, x, y):
        """
        Determines if the specified coordinates are over an item. Return
        the item that is below the coordinates, of None if no item found.
        """
        # If there are pending updated perform the updates before do the hit test
        self.__update_positions()

        return Stage.hit_test(self, x, y)

    def hit_test_stack(self, x, y):
        """
        Determines if the specified coordinates are over one or more items. Return
        the stack of items that are below the coordinates, of an empty list if no item found.
        """
        # If there are pending updated perform the updates before do the hit test
        self.__update_positions()

        return Stage.hit_test_stack(self, x, y)

    def get_grid_origin(self):
        """
        Gets the origin of the grid.
        """
        return self.__origin

    def get_grid_cell_size(self):
        """
        Gets the cell size of the grid.
        """
        return self.__cell_width, self.__cell_height

    def get_grid_multiplier(self):
        """
        Gets the multiplier used to adjust all the positions in the grid.
        """
        return self.__multiplier

    def get_grid_definition(self):
        """
        Gets the definition of the grid.
        """
        return self.__origin, self.__cell_width, self.__cell_height, self.__multiplier

    def set_grid_definition(self, origin, cell_width, cell_height, multiplier):
        """
        Sets the definition of the grid.
        - origin: Position of the origin in the isometric grid where the items are drawn.
        - cell_width: Length of the cell's horizontal diagonal.
        - cell_height: Length of the cell's vertical diagonal.
        - multiplier: Multiplier used to adjust all the positions in the grid
             (including the origin, the cell size and the items data)
        """
        self.__origin = origin
        self.__cell_width = cell_width
        self.__cell_height = cell_height
        self.__multiplier = multiplier

    def get_tags(self):
        """
        Gets the list with possible tags.
        """
        return self.__tags

    def set_tags(self, tags):
        """
        Sets the list with possible tags.
        - tags: List of tags.
        """
        self.__tags = tags

    def get_set_name(self):
        """
        Gets the set name that is used in the stage.
        """
        return self.__set_name

    def set_items(self, set_name, image_suffix="", item_definitions=None):
        """
        Sets the set of items that is used in the stage.
        - set_name: Name of the set. "" to remove the current set.
        - image_suffix: Suffix that is added to load the item images
        - item_definitions: A dictionary with the items definitions (instances of IsoDefinition). None if it must be load from a file.
        """
        self.__set_name = set_name
        self.__image_suffix = image_suffix
        self.__item_images_cache = {}
        self.__item_masks_cache = {}

        # Loads the items data of the set
        if item_definitions != None:
            self.__item_definitions = item_definitions
        elif set_name != "":
            full_name = os.path.join('data', self.__set_name + '.tcs')
            try:
                self.__item_definitions = {}
                file = open(full_name, 'r')
                line = file.readline()
                line = line.rstrip('\n').rstrip('\r')
                while line != "":
                    fields = line.split(';')
                    if len(fields) > 0:
                        type = fields[0]
                        try:
                            # Store the item data
                            center = (int(fields[1]), int(fields[2]))
                            size = (int(fields[3]), int(fields[4]))
                            l = fields[5].split('|')
                            place_holders = []
                            for place_holder in l:
                                if len(place_holder) >= 3:
                                    place_holder = place_holder.split(',')
                                    place_holders.append(IsoPlaceHolder(place_holder[0], int(place_holder[1]), int(place_holder[2]), int(place_holder[3])))
                            tag = fields[6].strip()
                            l = fields[7].split('|')
                            states = []
                            for state in l:
                                state = state.split(',')
                                if len(state) >= 3:
                                    if len(state) >= 4:
                                        clip = (state[3].strip() == '1')
                                    else:
                                        clip = False
                                    states.append(IsoDefState(state[0], (int(state[1]), int(state[2])), clip))
                            self.__item_definitions[type] = IsoDefinition(center, size, place_holders, tag, states)
                        except Exception:
                            print 'Invalid format for item \'' + type + '\' in file \'' + full_name + '\''
                            raise

                    line = file.readline()
                file.close()
            except Exception:
                print 'Cannot load items data:', full_name
                raise

    def get_item_definition(self, item_type, flipped_h=False):
        """
        Get the definition of the specified item (an instance of IsoDefinition).
        - item_type: Item's type.
        """

        # Get the item definition
        try:
            definition = self.__item_definitions[item_type]
        except Exception:
            print 'Missing definition for item \'' + item_type + '\'.'
            raise

        return definition

    def get_item_definitions(self):
        """
        Gets a dictionary with the item definitions (instances of IsoDefinition).
        """
        return self.__item_definitions

    def get_item_types_with_tag(self, tag):
        """
        Gets a list with the item types that in its definition have the specified tag.
        - tag: Tag to check.
        """
        item_types = []
        for item_type, definition in self.__item_definitions.iteritems():
            if definition.tag == tag:
                item_types.append(item_type)

        return item_types

    def load_item_image(self, type, state, flip_h=False, suffix=None):
        """
        Loads the image of the specified item.
        - type: Item's type.
        - state: Item's state.
        - flip_h: Indicates flip the image horizontally.
        - suffix: Suffix that is added to the file name.
        """

        key = type
        if state.suffix != "":
            state_suffix = "_" + state.suffix
            key += state_suffix
        else:
            state_suffix = ""
        if suffix != None:
            key += suffix
            state_suffix += suffix
        if flip_h:
            key += "?H"

        # Check if the image was previously loaded
        if self.__item_images_cache.has_key(key):
            image = self.__item_images_cache[key]
        else:
            image = None

            # If the image must be flipped gets the source image
            if flip_h:
                image = self.load_item_image(type, state, False, suffix)

            if image == None:
                # Load the image
                file_name = self.__set_name + type + self.__image_suffix + state_suffix + ".png"
                image = assets.load_image(file_name)

            # Flip the image if it is necessary
            if flip_h:
                image = assets.Image(pygame.transform.flip(image.surface, True, False))

            # Add the image in the cache
            self.__item_images_cache[key] = image

        return image

    def load_item_mask(self, type, state, flip_h, mask_suffix):
        """
        Loads the specified mask of the item.
        - type: Item's type.
        - state: Item's state.
        - flip_h: Indicates flip the image horizontally.
        - mask_suffix: Suffix that identifies the mask's file.
        """

        key = type
        if state.suffix != "":
            suffix = "_" + state.suffix
            key += suffix
        else:
            suffix = ""
        suffix += "$" + mask_suffix
        if flip_h:
            key += "?H"

        # Check if the mask was previously loaded
        if self.__item_masks_cache.has_key(key):
            mask = self.__item_masks_cache[key]
        else:
            mask = None

            # If the mask must be flipped gets the source mask
            if flip_h:
                mask = self.load_item_mask(type, state, False, mask_suffix)

            if mask == None:
                # Load the mask
                file_name = self.__set_name + type + self.__image_suffix + suffix + ".gif"
                mask = assets.load_mask(file_name)

            # Flip the mask if it is necessary
            if flip_h:
                mask = pygame.transform.flip(mask, True, False)

            # Add the mask in the cache
            self.__item_masks_cache[key] = mask

        return mask


    def load_level(self, level_name, layer, states, prepare_item=None):
        """
        Load the items of the specified level (from a file).
        - level_name: Level's name.
        - layer: Layer where the items are loaded.
        - states: List with possible states (instances of IsoState)
        - prepare_item: Function that is invoked with item for each item that will be added to the layer
             This function could be used to add event handlers to the item. None if no function is specified.
        """
        full_name = os.path.join('data', self.__set_name + level_name + '.tcl')
        try:
            file = open(full_name, 'r')
            line = file.readline()
            line = line.rstrip('\n').rstrip('\r')
            while line != "":
                fields = line.split(';')
                if len(fields) > 0:
                    type = fields[0]
                    if type.endswith('?H'):
                        type = type[:len(type) - 2]
                        flip_h = True
                    else:
                        flip_h = False

                    try:
                        row = float(fields[1])
                        col = float(fields[2])
                        state_suffix = fields[3].strip()
                    except Exception:
                        print 'Invalid format for item \'' + type + '\' in file \'' + full_name + '\''
                        raise

                    item_state = None
                    for state in states:
                        if state.suffix == state_suffix:
                            item_state = state
                            break
                    if item_state == None:
                        raise Exception, "State suffix '" + state_suffix + "' is not defined, and item '" + type + "' has this state."

                    item = ItemCell(self, type, item_state, flip_h, row, col)

                    if prepare_item != None:
                        prepare_item(item)

                    layer.add(item)

                line = file.readline()
            file.close()
        except Exception:
            print 'Cannot load level items:', full_name
            raise

    def save_level(self, level_name, layer):
        """
        Save the items of the specified layer in a level file.
        - level_name: Level's name.
        - layer: Layer with the items of the level.
        """
        full_name = os.path.join('data', self.__set_name + level_name + '.tcl')
        try:
            file = open(full_name, 'w')
            items_to_write = layer.items[:]

            # Check if there are duplicate items
            i = 0
            while i < len(items_to_write):
                item = items_to_write[i]

                duplicate = False
                j = i + 1
                while j < len(items_to_write):
                    item2 = items_to_write[j]
                    item_position = item.get_position()
                    if (item_position != None) and \
                       (item.get_type() == item2.get_type()) and \
                       (item_position == item2.get_position()) and \
                       (item.get_flip_h() == item2.get_flip_h()):
                        duplicate = True
                        break
                    else:
                        j += 1
                if duplicate:
                    del items_to_write[i]
                else:
                    i += 1

            for item in items_to_write:
                file.write(item.get_type())
                if item.get_flip_h():
                    file.write('?H')
                row, col = item.get_position()
                file.write(';')
                if row % 1 < 0.001:
                    row = int(row)
                file.write(str(row))
                file.write(';')
                if col % 1 < 0.001:
                    col = int(col)
                file.write(str(col))
                file.write(';')
                file.write(item.get_state().suffix)
                file.write("\r\n")
            file.close()
        except Exception:
            print 'Cannot save items data:', full_name
            raise

    def load_place_holders(self, layer, list):
        """
        Load a list with (item, place_holders) with all the place holders in the
        specified layer.
        - layer: Layer.
        - list: List where the place holders are loaded.
        """
        for item in layer.items:
            if isinstance(item, ItemCell):
                definition = item.get_definition()
                for place_holder in definition.place_holders:
                    list.append((item, place_holder))

    def find_item(self, layer, position, type):
        """
        Find an item that is located in the specified position with the specified
        type.
        - layer: Layer where the item is search.
        - position: Position.
        - type: type.
        """
        for item in layer.items:
            if isinstance(item, ItemCell):
                if (item.get_type() == type) and (item.get_position() == position):
                    return item

        return None

    def render(self):
        """
        Render the stage in the target surface. This function redraw
        the items that has changed in the stage since previous render.
        """
        if self.__adjust_positions != None:
            self.__update_positions()

        Stage.render(self)

    def mark_update_positions(self, layer, item=None):
        """
        Add the item in a list of pending update, to update its position
        to be shown correctly in the stage according to its row and columns.
        If item is None all items of the layer are adjusted.
        - layer: Layer of the item.
        - item: Item that changed. None to update all items.
        """
        if self.__adjust_positions == None:
            self.__adjust_positions = []
        add_item = True
        l = len(self.__adjust_positions)

        if item == None:
            # If there is already an item of the layer marked to update remove the
            # item because all the items must be updates
            k = l - 1
            while k >= 0:
                adj_pos = self.__adjust_positions[k]
                if adj_pos[0] == layer:
                    if adj_pos[1] == None:
                        add_item = False
                    else:
                        del self.__adjust_positions[k]
                k -= 1
        else:
            if not isinstance(item, ItemCell):
                add_item = False
            else:
                # Check if the item is already defined to update, or the layer
                # is marked to update all items in it
                k = 0
                while k < l:
                    adj_pos = self.__adjust_positions[k]
                    if adj_pos[0] == layer:
                        if adj_pos[1] == None:
                            add_item = False
                        elif adj_pos[1] == item:
                            add_item = False
                        else:
                            # There is already other item of the layer,
                            # mark to update all the items, because if
                            # too much items are marked to update the
                            # algorithm is very slow
                            del self.__adjust_positions[k]
                            self.__adjust_positions.append((layer, None))
                            add_item = False
                        break
                    k += 1
        if add_item:
            self.__adjust_positions.append((layer, item))

    def __update_positions(self):
        """
        Update the items positions that are marked to update.
        """
        if self.__adjust_positions != None:
            compare_func = self.__compare

            for adj_pos in self.__adjust_positions:
                layer = adj_pos[0]
                item = adj_pos[1]

                items = layer.items
                self.__several_rows_items = layer._Layer__several_rows_items
                self.__compare_items = items[:]
                if item != None:
                    if item in items:
                        items.remove(item)
                        self.__add_item_in_order(items, item)
                else:
                    items.sort(compare_func)

            # Clear the list of pending adjusts
            self.__adjust_positions = None
            self.__several_rows_items = None
            self.__compare_items = None

    def __add_item_in_order(self, items, item):
        """
        Add the specified item in order in the correct position according with its row and column.
        - items: List of items.
        - item: Item.
        """
        k = 0
        l = len(items)
        added = False
        while k < l:
            itemk = items[k]
            if isinstance(itemk, ItemCell) and self.__compare(item, items[k]) < 0:
                items.insert(k, item)
                added = True
                break
            else:
                k += 1
        if not added:
            items.append(item)

    def __compare(self, item1, item2):
        """
        Determines if item1 must be placed before item2.
        - item1: Item 1.
        - item2: item 2.

        Returns a negative number if item1 < item2, 0 if item1 == item2 or
        a positive number if item1 > item2
        """
        if not isinstance(item1, ItemCell):
            if not isinstance(item2, ItemCell):
                return self.__compare_items.index(item1) - self.__compare_items.index(item2)
            else:
                return -1
        if not isinstance(item2, ItemCell):
            return 1

        row1, col1 = item1.get_position()
        row2, col2 = item2.get_position()

        # Check if there is an item with more than one row in the middle of the two items
        for big_item in self.__several_rows_items:
            b_row_from = big_item[1]
            b_row_to = big_item[2]
            b_col_from = big_item[3]
            if b_row_from <= row1 and row1 <= b_row_to and \
               b_row_from <= row2 and row2 <= b_row_to:
                if col1 < b_col_from and col2 >= b_col_from:
                    return -1
                elif col2 < b_col_from and col1 >= b_col_from:
                    return 1

        size1 = item1.get_definition().size
        if row1 + size1[0] - 1 < row2:
            return -1
        size2 = item2.get_definition().size
        if row1 > row2 + size2[0] - 1:
            return 1
        else:
            if col1 + size1[1] - 1 < col2:
                return -1
            if col1 > col2 + size2[1] - 1:
                return 1

        # The items are overlapped
        return item1.get_z_index() - item2.get_z_index()

class IsoDefinition:
    """
    Contains the definition of an item to be shown in an isometric stage.
    """

    def __init__(self, center, size, place_holders, tag, states):
        """
        Constructor.
        - center: Position of the center of top most cell of the item.
        - size: Size of the item. A pair with (rows, columns).
        - place_holders: List of place holders where objects can be located. Each place
            holder is an instance of IsoPlaceHolder
        - tag: Tag associated with the item.
        - states: List with valid states for the item (instances of IsoDefState). It doesn't
            include the default state (the state with suffix "")
        """
        self.center = center
        self.size = size
        self.place_holders = place_holders
        self.tag = tag
        self.states = states
        self.__flip_h = None

    def has_state(self, state):
        """
        Determines if the item has the specified state in the definition.
        - state: State (an instance of IsoState).
        """
        for def_state in self.states:
            if def_state.name == state.name:
                return True

        return False


    def flip_h(self, item):
        """
        Get a definition for the item after flip it horizontally.
        - item: Item which the definition bellows.
        """
        if self.__flip_h == None:
            flipped_place_holders = []
            for placeholder in self.place_holders:
                flipped_place_holders.append(IsoPlaceHolder(placeholder.tag, - placeholder.x, placeholder.y, placeholder.height))

            flipped_states = []
            for state in self.states:
                # The center is flipped in the load_center function
                flipped_states.append(IsoDefState(state.name, state.center, state.clip))

            # The center is flipped in the load_center function
            self.__flip_h = IsoDefinition(self.center, (self.size[1], self.size[0]), flipped_place_holders, self.tag, flipped_states)
            self.__flip_h.__flip_h = self

        return self.__flip_h

class IsoDefState:
    """
    Contains the definition of a valid state for an item.
    """

    def __init__(self, name, center, clip):
        """
        Constructor.
        - name: Name of the state.
        - center: Position of the center of top most cell of the item in the state's image.
        - clip: Indicates if the state has a clipping mask.
        """
        self.name = name
        self.center = center
        self.clip = clip

class IsoPlaceHolder:
    """
    Contains a definition of a position where an object could be located over an item
    in an isometric stage.
    """

    def __init__(self, tag, x, y, height):
        """
        Constructor.
        - tag: Tag of the place holder.
        - x: X coordinate of the place holder in the image of the item.
        - y: Y coordinate of the place holder in the image of the item.
        - height: Height of the place holder.
        """
        self.tag = tag
        self.x = x
        self.y = y
        self.height = height

    def get_z_index(self, container_item):
        """
        Gets the z-index value that will be assigned to an item if it
        is located in the place_holder.

        The z-index of the items is modified to ensure that if there are several
        items in the same row, col associated with different place holders they are
        drawn in the correct order.
        - container_item: Item where the place holder is defined.
        - place_holder: Place holder (an instance of IsoPlaceHolder)
        """
        center_x, center_y = container_item.get_center()
        return math.floor(container_item.get_z_index()) + float((center_y + self.y) * 2048 + (center_x + self.x)) / 4194304

class IsoState:
    """
    Represents a possible state of an ItemCell.

    The states could be used to open or close a door.
    """

    def __init__(self, name, suffix):
        """
        Constructor.
        - name: Name of the state.
        - suffix: Suffix used to indicate the image of the state. Use "" to indicate the default state.
        """
        self.name = name
        self.suffix = suffix


class Item:
    """
    Represents an item that is shown in the stage
    """

    def __init__(self, left, top, width, height):
        """
        Constructor
        - left: X coordinate of the upper-left corner of the item.
        - top: Y coordinate of the upper-left corner of the item.
        - width: Width of the item.
        - height: Height of the item.
        """

        # Set the initial position
        self.__layer = None
        self.__left = left
        self.__top = top
        self.__width = width
        self.__height = height
        self.__alpha = 255
        self.visible = True
        self.rect = Rect(left, top, width, height)

        self.image = None
        self.draw_function = None
        self.__events = {}
        self.__rollover = None
        
    def exit(self):
        self.__rollover = None
        self.__events = {}
        self.image = None
        self.draw_function = None 
        self.__layer = None
        
    def get_visible(self):
        """
        Gets a value that indicates if the item is visible in the stage.
        """
        return self.visible

    def set_visible(self, visible):
        """
        Sets a value that indicates if the item is visible in the stage.
        - visible: True if the item is visible, false otherwise.
        """
        if self.visible != visible:
            self.visible = visible
            self.set_dirty()


    def get_left(self):
        """
        Gets the X coordinate of the upper-left corner of the item.
        """
        return self.__left

    def set_left(self, value):
        """
        Sets the X coordinate of the upper-left corner of the item.
        - value: New value.
        """
        if self.__left != value:
            self.__left = value
            self.set_dirty()

    def get_top(self):
        """
        Gets the Y coordinate of the upper-left corner of the item.
        """
        return self.__top

    def set_top(self, value):
        """
        Sets the Y coordinate of the upper-left corner of the item.
        - value: New value.
        """
        if self.__top != value:
            self.__top = value
            self.set_dirty()

    def set_lefttop(self, left, top):
        """
        Sets the (left, top) coordinates.
        - left: X coordinate of the upper-left corner of the item.
        - top: Y coordinate of the upper-left corner of the item.
        """
        if self.__left != left or self.__top != top:
            self.__left = left
            self.__top = top
            self.set_dirty()

    def get_width(self):
        """
        Gets the width of the item.
        """
        return self.__width

    def set_width(self, value):
        """
        Sets the width of the item.
        - value: New value.
        """
        if self.__width != value:
            self.__width = value
            self.set_dirty()

    def get_height(self):
        """
        Gets the height of the item.
        """
        return self.__height

    def set_height(self, value):
        """
        Sets the height of the item.
        - value: New value.
        """
        if self.__height != value:
            self.__height = value
            self.set_dirty()

    def get_bounds(self):
        """
        Gets the bounds of the item.
        """
        return Rect(self.__left, self.__top, self.__width, self.__height)

    def get_size(self):
        """
        Gets the size of the item.
        """
        return self.__width, self.__height

    def set_dirty(self):
        """
        Sets the item as dirty. Only the dirty items are redrawn in
        the screen in each refresh cycle. So, this function marks that
        the item must be redraw.
        """
        if self.__layer != None:
            self.__layer.add_dirty_item(self)

        if self.__rollover != None:
            self.__update_rollover_position()

    def get_layer(self):
        """
        Gets the layer of the item.
        """
        return self.__layer

    def set_layer(self, layer):
        """
        Sets the layer of the item.
        - layer: Layer if the item was added to the layer. None
              the item was removed from a layer
        """
        if layer == None:
            self.__layer = None
        else:
            if self.__layer != None:
                raise Exception, "The item is already part of a layer"
            else:
                self.__layer = layer
                
    def get_stage(self):
        """
        Gets the stage of the item.
        """
        if self.__layer == None:
            return None
        else:
            return self.__layer.get_stage()

    def update(self, frame_delay):
        """
        Updates the item before draw it in the stage. Returns the
        rectangle that must be updated.
        - frame_delay: Milliseconds elapsed from the previous frame.
        """

        real_left = self.__left
        real_top = self.__top
        if self.visible:
            real_width = self.__width
            real_height = self.__height
        else:
            real_width = 0
            real_height = 0

        # Move the drawing rectangle to the new position
        old_rect = self.rect
        self.rect = Rect(real_left, real_top, real_width, real_height)

        # Marks the rectangle that must be redrawn
        if old_rect == None:
            return self.rect
        else:
            return self.rect.union(old_rect)

    def is_over(self, x, y):
        """
        Determines if the specified point is contained in a rectangle with
        bounds of the item.
        - x: X coordinate.
        - y: Y coordinate.
        """
        return ((self.__left <= x) and (x < self.__left + self.__width) and
           (self.__top <= y) and (y < self.__top + self.__height))

    def add_event_handler(self, event, handler):
        """
        Adds a function to be invoked when the specified event is performed
        over this item.
        - event: The event. It should be a member of ItemEvent.
        - handler: Function to be invoked with (item, args)
        """
        if self.__events.has_key(event):
            self.__events[event].append(handler)
        else:
            self.__events[event] = [handler]

    def remove_event_handler(self, event, handler):
        """
        Removes a function from be invoked when the specified event
        is performed over this item.
        - event: The event. It should be a member of ItemEvent.
        - handler: Function to remove.
        """
        if self.__events.has_key(event):
            if handler in self.__events[event]:
                handlers = self.__events[event]
                handlers.remove(handler)
                if len(handlers) == 0:                    
                    del self.__events[event]

    def fire_event(self, event, args):
        """
        Fires an event over this item.
        - event: Event.
        - args: Arguments.

        Return a boolean value that indicates if the event has handled. If it returns true the event
        should be propagated to items that are below this item.
        """
        if self.__events.has_key(event):
            handlers = self.__events[event]
            handled = False
            for handler in handlers:
                ret = handler(self, args)

                # If the handler returns True or None the event is handled
                if ret or ret == None:
                    handled = True
            return handled
        else:
            return False

    def has_event_handler(self, event):
        """
        Determines if the item has at least one function that handles the specified event.
        - event: Event to check.
        """
        return self.__events.has_key(event) and len(self.__events[event]) > 0 

    def set_rollover(self, image, x=None, y=None):
        """
        Configure the item to show the specified image below the item when the mouse is moved over it.
        - image: Image that is shown below the item. None to remove the rollover.
        - x: X coordinate of the rollover relative to the item. 0 means the same position of the item,
             negative values to move the rollover to the left, positive values to move the rollover to
             the right. Use None to center the rollover in the item.
        - y: Y coordinate of the rollover relative to the item. 0 means the same position of the item,
             negative values to move the rollover up, positive values to move the rollover down.
             Use None to center the rollover in the item.
        """
        if image == None:
            self.__rollover = None

            # Remove the event handlers
            self.remove_event_handler(ItemEvent.MOUSE_ENTER, self.__rollover_mouse_enter)
            self.remove_event_handler(ItemEvent.MOUSE_LEAVE, self.__rollover_mouse_leave)
        else:
            item_image = ItemImage(0, 0, image)
            self.__rollover = (item_image, x, y)

            # Add the event handlers
            self.add_event_handler(ItemEvent.MOUSE_ENTER, self.__rollover_mouse_enter)
            self.add_event_handler(ItemEvent.MOUSE_LEAVE, self.__rollover_mouse_leave)

    def show_rollover(self):
        """
        Show the rollover if there is a rollover defined.
        """
        if self.__rollover != None:
            layer = self.get_layer()
            if layer != None:
                # Only show the rollover if there isn't a fade over the item
                stage = layer.get_stage()
                if stage != None and not stage.is_timer_started((self, "fade")):
                    item_image = self.__update_rollover_position()
                    layer.add(item_image, layer.index_of(self))

    def hide_rollover(self):
        """
        Hide the rollover if it is visible
        """
        if self.__rollover != None:
            image = self.__rollover[0]
            layer = image.get_layer()
            if layer != None:
                layer.remove(image)

    def __rollover_mouse_enter(self, item, args):
        """
        Function that is invoked when the mouse enters in an item with rollover.
        """
        self.show_rollover()

    def __rollover_mouse_leave(self, item, args):
        """
        Function that is invoked when the mouse leaves in an item with rollover.
        """
        self.hide_rollover()

    def __update_rollover_position(self):
        """
        Updates the position of the rollover image according to current
        position.
        """
        item_image = self.__rollover[0]
        x = self.__rollover[1]
        y = self.__rollover[2]

        if x == None:
            dx = (self.get_width() - item_image.get_width()) / 2
        else:
            dx = x
        if y == None:
            dy = (self.get_height() - item_image.get_height()) / 2
        else:
            dy = y

        item_image.set_left(self.__left + dx)
        item_image.set_top(self.__top + dy)

        return item_image


class ItemEvent:
    """
    Enumeration that specifies the events that can be fired in an item.
    """

    """
    The mouse left button was clicked over the item.
    Arguments:
    - x: X coordinate of the mouse.
    - y: Y coordinate of the mouse.

    The event is fired first in the topmost item below the mouse, then in the item that
    is below, and so on until one item handle it. To handle the event, the at least one function associated
    with the event must return None (default value if no return is defined) or True. If the handler
    returns False the event is fired in the item that is below.

    If an item doesn't have a handled defined for the item, is equivalent to define a handler that
    returns False.
    """
    CLICK = 0

    """
    The mouse left button was clicked two times over the item in a short period of time.
    Arguments:
    - x: X coordinate of the mouse.
    - y: Y coordinate of the mouse.

    The event is fired in the same fashion as with CLICK event.
    """
    DBLCLICK = 1

    """
    The mouse's cursor enter in the item.
    Arguments:
    - x: X coordinate of the mouse.
    - y: Y coordinate of the mouse.

    The MOUSE_ENTER is fired when the mouse is moved inside the item and it is
    defined as the current item.

    The current item is the first item that is below the mouse that handle
    a MOUSE_ENTER/MOUSE_LEAVE event.
    """
    MOUSE_ENTER = 2

    """
    The mouse's cursor leave the item.
    Arguments:
    - x: X coordinate of the mouse.
    - y: Y coordinate of the mouse.

    The MOUSE_LEAVE is fired when the mouse is moved outside the item, and the item
    is not longer the current item (see MOUSE_ENTER to read how the current item is defined).
    """
    MOUSE_LEAVE = 3

    """
    The mouse's cursor was move over the item.
    Arguments:
    - x: X coordinate of the mouse.
    - y: Y coordinate of the mouse.

    The event is fired in the same fashion as with CLICK event.
    """
    MOUSE_MOVE = 4

    """
    An item got the focus.
    """
    GOT_FOCUS = 5

    """
    An item lost the focus.
    """
    LOST_FOCUS = 6

    """
    The state of an ItemCell item changed.
    - previous_state: Previous state.
    """
    STATE_CHANGED = 7
    
    """
    The mouse left button was pressed over the item.
    Arguments:
    - x: X coordinate of the mouse.
    - y: Y coordinate of the mouse.

    The event is fired first in the topmost item below the mouse, then in the item that
    is below, and so on until one item handle it. To handle the event, the at least one function associated
    with the event must return None (default value if no return is defined) or True. If the handler
    returns False the event is fired in the item that is below.

    If an item doesn't have a handled defined for the item, is equivalent to define a handler that
    returns False.
    """
    PRESS = 8

class ItemEventArgs:
    """
    Contains the arguments of an event
    """

    def __init__(self):
        """
        Constructor.
        """
        pass

class ItemEventArgsMouse(ItemEventArgs):
    """
    Contains the arguments of a mouse event
    """

    def __init__(self, x, y):
        """
        Constructor.
        - x: X coordinate.
        - y: Y coordinate.
        """
        self.x = x
        self.y = y

class ItemEventArgsStateChanged(ItemEventArgs):
    """
    Contains the arguments of a state changed event
    """

    def __init__(self, previous_state):
        """
        Constructor.
        - previous_state: Previous state.
        """
        self.previous_state = previous_state


class ItemImage(Item):
    """
    Represents an item that is shown with an image.
    """

    def __init__(self, left, top, image, area=None, hit_over_transparent=False):
        """
        Constructor.
        - left: X coordinate of the upper-left corner of the item.
        - top: Y coordinate of the upper-left corner of the item.
        - image: Image that is used to draw the item. It must be an instance of assets.Image class.
        - area: Area of the image to be shown (a Rect). None to show the whole image.
        - hit_over_transparent: Indicate if transparent zones of the images are consider part of the image
          in mouse events. For example, if you indicate True and click on a transparent pixel of the
          image the CLICK event is fired, if you indicate False the click is not fired. The same
          happens with other mouse events.
        """

        # Initialize base class
        Item.__init__(self, left, top, 0, 0)

        # Set the image
        self.__alpha = 255
        self.__hit_over_transparent = hit_over_transparent
        self.set_image(image, area)
        
    def exit(self):
        Item.exit(self)
        self.__image = None
        if hasattr(self, "_ItemImage__rollover"):
            self.__rollover = None
        if hasattr(self, "_ItemImage__pressed"):
            self.__pressed = None
        self.__source_surface = None
        self.__surface_noclip = None
        self.surface = None
        
    def get_alpha(self):
        """
        Gets the alpha value associated with the item. If alpha value is 0 the item
        is invisible, if it is 255 the item is visible, and intermediate values
        sets a semi-transparent item.
        """
        return self.__alpha

    def set_alpha(self, alpha):
        """
        Sets the alpha value associated with the item.
        - alpha: Alpha value.
        """
        self.__alpha = alpha
        self.surface = set_surface_alpha(self.__source_surface, alpha)
        self.set_dirty()

    def is_over(self, x, y):
        """
        Determines if the specified point is contained in the item.
        - x: X coordinate
        - y: Y coordinate
        """
        bounds = self.get_bounds()
        if (bounds.collidepoint(x, y)):
            if self.__hit_over_transparent:
                return True

            # The coordinate is over the image rectangle, check if it is not
            # over a transparent pixel. Get the pixel RGBA
            try:
                c = self.surface.get_at((int(x - self.get_left()), int(y - self.get_top())))
            except Exception:
                return False

            # Check the value of the alpha component
            if c[3] > 40:
                return True;
        return False;

    def get_image(self):
        """
        Gets the image associated with the ItemImage
        """
        return self.__image

    def set_image(self, image, area=None):
        """
        Sets the image of the item.
        - image: Image that is used to draw the item in the screen. It must be an instance of assets.Image class.
        - area: Area of the image to be shown (a Rect). None to show the whole image.
        """
        if hasattr(self, "_ItemImage__rollover") and self.__rollover != None and self.__rollover[1] != None:
            # There is a rollover defined and the mouse is over the image. Update the image in the rollover
            self.__rollover[1] = image
        elif hasattr(self, "_ItemImage__pressed") and self.__pressed != None and self.__pressed[1] != None:
            # There is a pressed image defined and the mouse has press the image. Update the image in the pressed data
            self.__pressed[1] = image
        else:
            self.__set_image_internal(image, area)

    def set_clip_mask(self, image_mask, image_pos):
        """
        Exclude a part of the image using the alpha channel of the specified image mask.
        - image_mask: Image mask. None to remove the mask.
        - image_pos: Image position in the stage (left, top). The position is used to calculate
          the intersection between the two images, and apply the alpha channel of the intersection
          in this image.
        """

        if image_mask == None:
            self.__source_surface = self.__surface_noclip
            if self.surface != self.__surface_noclip:
                self.surface = self.__surface_noclip
                self.set_dirty()
        else:
            # Calculate the area that define the alpha channel that must be copied
            left = self.get_left()
            top = self.get_top()
            if image_pos[0] < left:
                x = 0
                area_x = (left - image_pos[0])
            else:
                x = (image_pos[0] - left)
                area_x = 0
            if image_pos[1] < top:
                y = 0
                area_y = (top - image_pos[1])
            else:
                y = image_pos[1] - top
                area_y = 0
            area_width = min(image_mask.get_width() - area_x, self.get_width())
            area_height = min(image_mask.get_height() - area_y, self.get_height())

            # Copy the alpha channel of 'image_mask' in this image
            self.surface = self.__source_surface.copy()
            alpha_matrix = pygame.surfarray.pixels_alpha(self.surface)
            alpha_matrix_mask = pygame.surfarray.pixels_alpha(image_mask.surface)
            for i in xrange(area_width):
                alpha_matrix[x + i][y:y + area_height] &= alpha_matrix_mask[area_x + i][area_y : area_y + area_height]

            # Copy the surface to the source surface, because when alpha is
            # modified the source surface is used to calculate the final surface with the alpha value
            self.__source_surface = self.surface

            self.set_dirty()

    def set_rollover_image(self, image):
        """
        Configure the item to replace the image with the specified image when the
        mouse is moved over the item.
        - image: Image that is shown when the mouse is over the item. None to remove the rollover.
        """
        if hasattr(self, "_ItemImage__rollover") and self.__rollover != None:
            # If there is a rollover image set in the item remove it
            old_image = self.__rollover[1]
            self.__rollover = None
            if old_image != None:
                self.set_image(old_image)

            # Remove the event handlers
            self.remove_event_handler(ItemEvent.MOUSE_ENTER, self.__rollover_mouse_enter)
            self.remove_event_handler(ItemEvent.MOUSE_LEAVE, self.__rollover_mouse_leave)

        if image != None:
            self.__rollover = [image, None]

            # Add the event handlers
            self.add_event_handler(ItemEvent.MOUSE_ENTER, self.__rollover_mouse_enter)
            self.add_event_handler(ItemEvent.MOUSE_LEAVE, self.__rollover_mouse_leave)

    def set_pressed_image(self, image):
        """
        Configure the item to replace the image with the specified image when the
        mouse press the item.
        - image: Image that is shown when the mouse press the item. None to remove the press image.
        """
        if hasattr(self, "_ItemImage__pressed") and self.__pressed != None:
            # If there is a pressed image set in the item remove it
            old_image = self.__pressed[1]
            self.__pressed = None
            if old_image != None:
                self.set_image(old_image)

            # Remove the event handlers
            self.remove_event_handler(ItemEvent.PRESS, self.__pressed_click)

        if image != None:
            self.__pressed = [image, None]

            # Add the event handlers
            self.add_event_handler(ItemEvent.PRESS, self.__pressed_click)

    def __set_image_internal(self, image, area=None):
        """
        Sets the image of the item.
        - image: Image that is used to draw the item in the screen. It must be an instance of assets.Image class.
        - area: Area of the image to be shown (a Rect). None to show the whole image.
        """
        self.__image = image
        if image == None:
            self.area = (0, 0, 0, 0)
            self.surface = pygame.Surface((0, 0), pygame.SRCALPHA, 32)
            self.__source_surface = self.surface
            self.__surface_noclip = self.surface
            self.set_width(0)
            self.set_height(0)
        else:
            self.set_width(image.get_width())
            self.set_height(image.get_height())

            self.surface = image.surface
            self.__source_surface = self.surface
            self.__surface_noclip = self.surface
            self.area = area

            if self.__alpha != 255:
                self.surface = set_surface_alpha(self.__source_surface, self.__alpha)

            self.set_dirty()

    def __rollover_mouse_enter(self, item, args):
        """
        Function that is invoked when the mouse enters in an item with rollover.
        """
        if self.__rollover != None:
            if hasattr(self, "_ItemImage__pressed") and self.__pressed != None and self.__pressed[1] != None:
                # There is a pressed image defined and the mouse is pressing the image
                # Set the rollover in the pressed image data
                self.__rollover[1] = self.__pressed[1]
                self.__pressed[1] = self.__rollover[0]
            else:
                # Set the rollover normally
                current_image = self.get_image()
                self.__set_image_internal(self.__rollover[0])
                self.__rollover[1] = current_image

    def __rollover_mouse_leave(self, item, args):
        """
        Function that is invoked when the mouse leaves in an item with rollover.
        """
        if self.__rollover != None:
            if hasattr(self, "_ItemImage__pressed") and self.__pressed != None and self.__pressed[1] != None:
                # There is a pressed image defined and the mouse is pressing the image
                # Remove the rollover from the pressed image data
                self.__pressed[1] = self.__rollover[1]
                self.__rollover[1] = None
            else:
                # Remove the rollover normally
                old_image = self.__rollover[1]
                if old_image != None:
                    self.__rollover[1] = None
                    item.__set_image_internal(old_image)

    def __pressed_click(self, item, args):
        """
        Function that is invoked when the mouse click the an item with a pressed image.
        """
        if self.__pressed != None:
            stage = self.get_stage()
            if stage != None:
                current_image = self.get_image()
                self.__set_image_internal(self.__pressed[0])
                self.__pressed[1] = current_image

                # Capture the mouse to detect when the mouse is released
                stage.capture_leftmousedown(self, self.__pressed_mousecapture)

    def __pressed_mousecapture(self, mouse_args, released):
        """
        Function that is invoked the the image is pressed and the mouse
        is moved or the left mouse button is released.
        - mouse_args: Mouse arguments.
        - released: Boolean value that indicates if the left mouse button was released.
        """
        if released:
            if self.__pressed != None:
                old_image = self.__pressed[1]
                if old_image != None:
                    self.__pressed[1] = None
                    self.__set_image_internal(old_image)

class ItemCustomDraw(Item):
    """
    Represents an item that drawn invoking a custom function.
    """

    def __init__(self, left, top, width, height, draw_function, mask=None):
        """
        Constructor
        - left: X coordinate of the upper-left corner of the item.
        - top: Y coordinate of the upper-left corner of the item.
        - width: Width of the item.
        - height: Height of the item.
        - draw_function: Function to draw the item with parameters (item, target),
                where 'item' is the item to be drawn, and target is an instance of
                CustomDraw and it must be used to draw the item.
        - mask: Mask to check if a pair of coordinates is over the item. mask could
                be a Surface or a function with parameters (item, x, y). Use None to define
                a mask with a rectangle using the bounds of the item.
        """
        Item.__init__(self, left, top, width, height)

        self.draw_function = draw_function
        self.mask = mask

    def is_over(self, x, y):
        """
        Determines if the specified point is contained in the item.
        - x: X coordinate
        - y: Y coordinate
        """
        bounds = self.get_bounds()
        if (bounds.collidepoint(x, y)):
            if self.mask == None:
                return True
            elif callable(self.mask):
                return self.mask(self, x, y)
            else:
                # Check if the coordinate is in an non-white pixel of the mask
                try:
                    c = self.mask.get_at((x - self.get_left(), y - self.get_top()))
                    if (c[0] != 255) or (c[1] != 255) or (c[2] != 255):
                        return True
                except Exception:
                    return False

        return False;


class ItemCell(ItemImage):
    """
    Represents an item that is shown in a cell of a isometric stage
    specifying its row and column
    """

    def __init__(self, stage, type, state, flip_h = False, row = - 999, col= - 999):
        """
        Constructor
        - stage: Stage where the item is shown (must be an instance of StageIso).
        - type: Item's type (the type must be present in the stage items' data).
        - state: Initial state for the item (an instance of IsoState).
        - flip_h: Indicates if the item is flipped horizontaly.
        - row: Row where the item is located. -999 if the position must be defined later.
        - col: Column where the item is located. -999 if the position must be defined later.
        """
        self.__stage = stage

        # Initialize base class
        ItemImage.__init__(self, 0, 0, None)

        # Sets the item
        self.__state = state
        self.__center = None
        self.__flip_h = flip_h
        self.__type = None
        self.__definition = None
        self.__z_index = 0
        self.set_type(type)
        self.__position = (0, 0)
        if row != - 999:
            self.set_position(row, col)

    def clone(self, stage):
        """
        Create a new item with the same values of this item for the specified stage.
        - Stage: Target stage.
        """
        row, col = self.get_position()
        new_item = ItemCell(stage, self.__type, self.__state, self.__flip_h, - 999, - 999)
        new_item.__z_index = self.__z_index
        new_item.__center = self.__center
        new_item.set_position(row, col)
        new_item.set_visible(self.get_visible())

        if hasattr(self, "_ItemCell__visible_in_states") and self.__visible_in_states != None:
            new_item.__visible_in_states = self.__visible_in_states

        return new_item

    def get_type(self):
        """
        Gets the type of the item
        """
        return self.__type

    def set_type(self, type):
        """
        Sets a new item for this instance.
        - type: Item's type.
        """
        if self.__type != type:
            # Get current row an column
            if self.__type == None:
                position = None
            else:
                position = self.get_position()

            self.__type = type

            # Load the item image
            self.__image = self.__stage.load_item_image(type, self.__state, self.__flip_h)
            self.set_image(self.__image, None)

            # Get the item definition
            if self.__definition != None:
                old_rows = self.__definition.size[0]
            else:
                old_rows = - 1
            self.__definition = self.__stage.get_item_definition(type)
            if self.__definition == None:
                raise Exception, "There is no definition for item '" + type + "'"
            if self.__flip_h:
                self.__definition = self.__definition.flip_h(self)
            self.__load_center()

            # Update the z-index
            tags = self.__stage.get_tags()
            if tags != None and self.__definition.tag in tags:
                self.__z_index = tags.index(self.__definition.tag)
            else:
                self.__z_index = 999

            # Update the left, top coordinates
            if position != None:
                self.set_position(position[0], position[1], old_rows)

    def get_state(self):
        """
        Gets the state of the item (an instance of IsoState).
        """
        return self.__state

    def set_state(self, state):
        """
        Sets a new state for the item.
        - state: State (an instance of IsoState).
        """
        if self.__state != state:
            # Get current row an column
            position = self.get_position()

            previous_state = self.__state
            self.__state = state
            self.__image = self.__stage.load_item_image(self.__type, self.__state, self.__flip_h)
            self.set_image(self.__image, None)
            self.__load_center()

            # Update the left, top coordinates
            self.set_position(position[0], position[1])

            # Update the items over it
            items_over = self.__stage.get_items_over(self)
            for item_over in items_over:
                # Check if the item is visible in this state
                if hasattr(item_over, "_ItemCell__visible_in_states"):
                    visible_in_states = item_over.__visible_in_states
                    if visible_in_states != None:
                        # We don't check that this is container because in Ceibal Detective the items
                        # are cloned, and in the large stage the instance are not the same, so the
                        # check would fail. Instead of check object reference we check the names
                        if visible_in_states[0].get_type() == self.__type:
                            clip_mask = None
                            if state in visible_in_states[1]:
                                # Show the item
                                item_over.set_visible(True)

                                # Set the clip mask if there is a mask in the state. The clip mask allow
                                # to erase part of the items, for example if we open a door the items
                                # that are inside could not be completely visible and the clip mask could
                                # remove the parts that are not visible
                                clip = False
                                for def_state in self.__definition.states:
                                    if def_state.name == state.name:
                                        if def_state.clip:
                                            clip = True
                                        break
                                if clip:
                                    if clip_mask == None:
                                        # Load the clip mask
                                        clip_mask = self.__stage.load_item_image(self.__type, self.__state, self.__flip_h, "$x")
                                        clip_pos = (self.get_left(), self.get_top())

                                    item_over.set_clip_mask(clip_mask, clip_pos)
                                else:
                                    item_over.set_clip_mask(None, None)
                            else:
                                # False the item
                                item_over.set_visible(False)

            # Fire STATE_CHANGE event
            self.fire_event(ItemEvent.STATE_CHANGED, ItemEventArgsStateChanged(previous_state))

    def get_position(self):
        """
        Gets the position (row, col) of the item in the grid of the isometric stage.
        """
        return self.__position

    def set_position(self, row, col, old_rows= - 1, z_index= - 1):
        """
        Set the position of the item in the grid of the isometric stage.
        - row: Row.
        - col: Column.
        - old_rows: Old number of rows for the item if it could changed. This parameter
          is used internally. -1 if it didn't change.
        - z_index: Z-index. -1 to keep current z-index.
        """
        # Get the grid position of the specified row and column
        left, top = self.__from_grid_position(row, col)
        self.set_lefttop(left, top)
        self.__position = (row, col)
        layer = self.get_layer()
        if z_index != - 1:
            self.__z_index = z_index
        if layer != None:
            stage = layer.get_stage()
            if old_rows > 1:
                layer = self.get_layer()
                if layer != None:
                    layer._Layer__remove_serveral_rows_item(self)
            if self.__definition.size[0] <= 1:
                if stage != None:
                    stage.mark_update_positions(layer, self)
            else:
                layer._Layer__update_serveral_rows_item(self, self.__definition)
                if stage != None:
                    stage.mark_update_positions(layer, None)

    def get_mask(self, mask_suffix):
        """
        Loads the specified mask of the item (an instance of Surface)
        - mask_suffix: Suffix that identifies the mask's file.
        """
        return self.__stage.load_item_mask(self.__type, self.__state, self.__flip_h, mask_suffix)

    def get_at_mask(self, x, y, mask_suffix):
        """
        Gets the color of the corresponding pixel of the mask in the specified
        stage position.
        - x: X coordinate in the stage.
        - y: Y coordinate in the stage.
        - mask_suffix: Suffix that identifies the mask's file.
        """

        # Load the mask without flipping it to avoid load the unflipped image of the
        # mask in memory because we can modify the coordinates to simulate the flipped
        # mask
        mask = self.__stage.load_item_mask(self.__type, self.__state, False, mask_suffix)
        if mask == None:
            return (255, 255, 255, 255)
        else:
            if self.__flip_h:
                mask_x = self.get_width() - (x - self.get_left())
            else:
                mask_x = x - self.get_left()
            mask_y = y - self.get_top()
            if mask_x < 0 or mask_y < 0 or mask_x >= mask.get_width() or mask_y >= mask.get_height():
                return (255, 255, 255, 255)
            else:
                return mask.get_at((mask_x, mask_y))

    def get_center(self):
        """
        Gets the (x, y) coordinates inside the item of the center.
        """
        return self.__center

    def set_to_place_holder(self, container_item, place_holder, below=False, only_visible_in_states=None):
        """
        Locate the item centered in the specified place holder.
        - container_item: Item where the place holder is defined.
        - place_holder: Place holder (an instance of IsoPlaceHolder)
        - below: True to locate item below the 'container_item'
        - only_visible_in_states: List with the states of 'container_item' in which this item must be visible,
          Use None to don't affect the visibility of this item.
        """

        # Get the row and column of the placeholder
        row, col = container_item.get_position()
        ph_row, ph_col = container_item.get_place_holder_rowcol(place_holder)
        drow = ph_row - row
        dcol = ph_col - col

        # Redefine the center to draw the item over the place holder
        self.__load_center()
        cell_width, cell_height = self.__stage.get_grid_cell_size()
        self.__center = (self.__center[0] - place_holder.x + (dcol - drow) * cell_width / 2,
                         self.__center[1] - (place_holder.y - place_holder.height) + (dcol + drow) * cell_height / 2)

        # Locate the item in the same position that the container item
        z_index = place_holder.get_z_index(container_item)
        if below:
            z_index -= 1
        self.set_position(ph_row, ph_col, - 1, z_index)

        if only_visible_in_states != None:
            # Monitor the state change event in the container to update the visibility
            self.__visible_in_states = (container_item, only_visible_in_states)
            self.set_visible(self.get_state() in only_visible_in_states)
        else:
            if hasattr(self, "_ItemCell__visible_in_states"):
                self.__visible_in_states = None

    def get_place_holder_rowcol(self, place_holder):
        """
        Gets the (row, column) where the specified place holder is located.
        - place_holder: Place holder (an instance of IsoPlaceHolder).
        """
        multiplier = self.__stage.get_grid_multiplier()
        return self.__stage.get_rowcol(self.get_left() + (self.__center[0] + place_holder.x) * multiplier,
            self.get_top() + (self.__center[1] + place_holder.y) * multiplier)

    def get_place_holder_xy(self, place_holder):
        """
        Gets the (x, y) coordinates of the specified place holder (of this item).
        - place_holder: Place holder (an instance of IsoPlaceHolder).
        """
        multiplier = self.__stage.get_grid_multiplier()
        return (self.get_left() + (self.__center[0] + place_holder.x) * multiplier,
                self.get_top() + (self.__center[1] + place_holder.y - place_holder.height) * multiplier)

    def get_flip_h(self):
        """
        Gets a value indicating if the item is flipped horizontal.
        """
        return self.__flip_h

    def set_flip_h(self, value):
        """
        Sets a value indicating if the item is flipped horizontal.
        - value: True if the item is flipped horizontal, otherwise False
        """
        if self.__flip_h != value:
            position = self.get_position()
            self.__image = self.__stage.load_item_image(self.__type, self.__state, value)
            self.set_image(self.__image, None)
            old_rows = self.__definition.size[0]
            self.__definition = self.__definition.flip_h(self)
            self.__flip_h = value
            self.__load_center()
            if position != None:
                # Update the left, top coordinates
                self.set_position(position[0], position[1], old_rows)

    def get_definition(self):
        """
        Gets the definition of the item (an instance of IsoDefinition).
        """
        return self.__definition

    def reload_definition(self):
        """
        Reload the definition of the item from the stage.
        """
        # Set a type that is not used, so when we set the type again it will be different
        # from current type and the definition will be loaded again.
        type = self.__type
        self.__type = '???'
        self.set_type(type)

    def get_z_index(self):
        """
        Gets the z-index of the item. The z index is used to order items that are
        in the same row, col. Items with lower z-index are shown before.
        """
        return self.__z_index

    def collision_test(self, row, col, only_item_layer):
        """
        Tests if the item will collide with another ItemCell item if the specified
        position is assigned to this item. Returns None if there is no collision,
        if there is a collision returns the first item which collide with.
        - row: Row to test.
        - col: Column to test:
        - only_item_layer: True if only evaluate a collision with the items of the
          same layer of this element. False if considers all the items.
        """
        layer = self.get_layer()
        if layer != None:
            if only_item_layer:
                return self.__collide_test_layer(row, col, layer)
            else:
                stage = layer.get_stage()
                if stage != None:
                    for layer in stage.layers:
                        item = self.__collide_test_layer(row, col, self.__layer)
                        if item != None:
                            return item

        return None

    def __load_center(self):
        if self.__state.suffix == "":
            # Default state is assigned
            self.__center = self.__definition.center
        else:
            # Find the definition of the state
            state_center = None
            for state in self.__definition.states:
                if state.name == self.__state.name:
                    state_center = state.center

            if state_center == None:
                raise Exception, "State '" + self.__state.name + "' is not defined for item '" + self.__type + "'"
            else:
                self.__center = state_center
        if self.__flip_h:
            self.__center = (self.get_width() / self.__stage.get_grid_multiplier() - self.__center[0], self.__center[1])

    def __collide_test_layer(self, row, col, layer):
        """
        Tests if the item will collide with another ItemCell item if the specified
        position is assigned to this item. Returns None if there is no collision,
        if there is a collision returns the first item which collide with.
        - row: Row to test.
        - col: Column to test:
        - layer: Layer where the collision is tested.
        """
        size = self.__definition.size
        for item in layer.items:
            if isinstance(item, ItemCell) and (item != self):
                item_pos = item.get_position()
                if item_pos != None:
                    if (item_pos[0] < row + size[0]) and \
                        (item_pos[1] < col + size[1]):
                        item_def = item.get_definition()
                        item_size = item_def.size
                        if (item_pos[0] + item_size[0] > row) and \
                            (item_pos[1] + item_size[1] > col):
                            # There is a collision!!
                            return item

        # There isn't a collision
        return None

    def __from_grid_position(self, row, col):
        """
        Gets the position in the screen associated with the specified row
        and column.
        - row: Row.
        - column: Column.
        """
        if self.__definition == None:
            return row, col
        else:
            stage = self.__stage
            origin, cell_width, cell_height, multiplier = stage.get_grid_definition()
            center = self.__center
            left = int((origin[0] + (col - row) * cell_width / 2 - center[0]) * multiplier)
            top = int((origin[1] + (col + row) * cell_height / 2 - center[1] + cell_height / 2) * multiplier)

            return left, top

    def __to_grid_position(self, left, top):
        """
        Gets the position in the grid from a position in the screen.
        - left: X coordinate of the upper-left corner.
        - top: Y coordinate of the upper-left corner.
        """
        stage = self.__stage
        origin, cell_width, cell_height, multiplier = stage.get_grid_definition()
        center = self.__center

        # Calculate (col - row)
        d1 = (left / multiplier - origin[0] + center[0]) / (cell_width / 2)

        # Calculate (col + row)
        d2 = (top / multiplier - origin[1] + center[1] - cell_height / 2) / (cell_height / 2)

        # Calculate the col and row
        col = (d1 + d2) / 2
        row = col - d1

        return row, col

class ItemMask(Item):
    """
    Defines an item that doesn't have graphic representation but can be used
    as a mask to detect clicks on an specific region of the screen, or detect
    mouse over and mouse leave events.
    """

    def __init__(self, left, top, mask):
        """
        Constructor
        - left: X coordinate of the upper-left corner of the item.
        - top: Y coordinate of the upper-left corner of the item.
        - mask: Mask to check if a pair of coordinates is over the item. mask should
                could a Surface, and Image (loaded with assets.load_image) or a
                pair (width, height) to use a solid rectangle.
        """
        if isinstance(mask, pygame.Surface):
            width = mask.get_width()
            height = mask.get_height()
        elif isinstance(mask, assets.Image):
            width = mask.get_width()
            height = mask.get_height()
        else:
            width = mask[0]
            height = mask[1]
            mask = None

        Item.__init__(self, left, top, width, height)

        self.mask = mask
        self.draw_function = self.__draw_item

    def is_over(self, x, y):
        """
        Determines if the specified point is contained in the item.
        - x: X coordinate
        - y: Y coordinate
        """
        bounds = self.get_bounds()
        if (bounds.collidepoint(x, y)):
            if self.mask == None:
                return True
            else:
                # Check if the coordinate is in an non-white pixel of the mask
                try:
                    c = self.mask.get_at((x - self.get_left(), y - self.get_top()))
                    if (c[0] != 255) or (c[1] != 255) or (c[2] != 255):
                        return True
                except Exception:
                    return False

        return False;

    def update(self, frame_delay):
        """
        Updates the item before draw it in the stage. Returns the
        rectangle that must be updated.
        - frame_delay: Milliseconds elapsed from the previous frame.
        """

        # The item is not drawn in the stage, so do nothing
        return None

    def get_at(self, x, y):
        """
        Get the value of the pixel at the specified position.
        - x: X coordinate
        - y: Y coordinate
        """
        return self.mask.get_at((x, y))

    def __draw_item(self, item, target):
        """
        Draws the item.
        - item: Item to be drawn.
        - target: An instance of CustomDraw to draw the item.
        """

        # The item is not drawn
        pass


class ItemText(Item):
    """
    Defines an item that shows a text
    """

    VALID_UNICODE_CHARS = ['á','é','í','ó','ú','Á','É','Í','Ó','Ú','ñ','Ñ','ü','Ü','ç','Ç']

    def __init__(self, left, top, font, line_height, text, color= (255, 255, 255), background = None, width = -1, height = - 1, h_align = 1, v_align = 1, additional_fonts = []):
        """
        Constructor
        - left: X coordinate of the upper-left corner of the item.
        - top: Y coordinate of the upper-left corner of the item.
        - font: Font used to render the text.
        - line_height: Line height. 0 to use default height.
        - text: Default text.
        - color: Text's color. It could be an (R, G, B) tuple.
        - background: Background's color.
        - width: Width for the text box. -1 if it is determined automatically.
        - height: Height for the text box. -1 if it is determined automatically.
        - h_align: Horizontal alignment (1 = left, 2 = center, 3 = right).
        - v_align: Vertical alignment (1 = top, 2 = center, 3 = bottom).
        - additional_fonts: Dictionary with the additional fonts that can be
          referenced in the text using &#f:font_name! or &#f! to use the
          default font. It must be indexed by the name of the font. And the
          values of the dictionary must a pair with (font, line_height),
          use 0 in the line_height to use the default line height of
          the font.
        """
        self.__width = width
        self.__height = height
        self.__h_align = h_align
        self.__v_align = v_align
        self.__font = font
        self.__additional_fonts = additional_fonts
        if line_height == 0:
            self.__line_height = max(1, font.get_linesize())
        else:
            self.__line_height = line_height
        self.__color = color
        self.__background = background
        self.__alpha = 255
        self.__break_text_into = None
        self.__rollover_color = None
        self.__edit_mode = None
        self.__max_chars = -1
        
        # Initialize base class
        Item.__init__(self, left, top, 0, 0)

        # Set the text
        self.__text = text
        self.area = None
        self.__update_text()

        # Set the item size
        if self.__width != - 1:
            self.set_width(self.__width)
        else:
            self.__dx = 0
        if self.__height != - 1:
            self.set_height(self.__height)
        else:
            self.__dy = 0

        # Set the function to draw the text
        self.draw_function = self.__draw_item
        
    def set_editable(self, editable):
        """
        Sets a value that indicates if the text item is editable.
        - editable: True if it is editable; otherwise, false.        
        """
        if editable:
            if self.__edit_mode == None:
                self.__edit_mode = False
                self.__update_text()
        else:
            self.__edit_mode = None        

    def get_alpha(self):
        """
        Gets the alpha value associated with the item. If alpha value is 0 the item
        is invisible, if it is 255 the item is visible, and intermediate values
        sets a semi-transparent item.
        """
        return self.__alpha

    def set_alpha(self, alpha):
        """
        Sets the alpha value associated with the item.
        - alpha: Alpha value.
        """
        self.__alpha = alpha
        self.__text_surface = set_surface_alpha(self.__source_surface, alpha)
        self.set_dirty()

    def get_color(self):
        """
        Gets the color of the text.
        """
        return self.__color

    def set_color(self, color):
        """
        Sets the color of the text.
        - color: Color.
        """
        if self.__rollover_color != None and self.__rollover_color[1] != None:
            # There is a rollover color defined and the mouse is over the text. Update the color in the rollover
            self.__rollover_color[1] = color
        else:
            if self.__color != color:
                self.__color = color

                # Marks the text to update later because the width/height
                # doesn't change after render it so delay the update because
                # other changes could be performed before update the text
                # in the screen
                self.__mark_text_to_update()

    def set_rollover_color(self, rollover_color):
        """
        Sets the color of the text when the mouse is over it.
        - rollover_color: Color when the mouse is over the text. None to remove the rollover color
        """
        if self.__rollover_color != None:
            # If there is a rollover color setted in the item remove it
            old_color = self.__rollover_color[1]
            self.__rollover_color = None
            if old_color != None:
                self.__color = old_color
                self.__mark_text_to_update()

            # Remove the event handlers
            self.remove_event_handler(ItemEvent.MOUSE_ENTER, self.__rollover_color_mouse_enter)
            self.remove_event_handler(ItemEvent.MOUSE_LEAVE, self.__rollover_color_mouse_leave)

        if rollover_color != None:
            self.__rollover_color = [rollover_color, None]

            # Add the event handlers
            self.add_event_handler(ItemEvent.MOUSE_ENTER, self.__rollover_color_mouse_enter)
            self.add_event_handler(ItemEvent.MOUSE_LEAVE, self.__rollover_color_mouse_leave)

    def get_background(self):
        """
        Gets the background of the text.
        """
        return self.__background

    def set_background(self, background):
        """
        Sets the background of the text.
        - color: Color.
        """
        if self.__background != background:
            self.__background = background

            # Marks the text to update later because the width/height
            # doesn't change after render it so delay the update because
            # other changes could be performed before update the text
            # in the screen
            self.__mark_text_to_update()

    def set_dimensions(self, width, height):
        """
        Sets a new dimensions for the item.
        - width: Width for the text box. -1 if it is determined automatically.
        - height: Height for the text box. -1 if it is determined automatically.
        """
        self.__width = width
        self.__height = height

        # Set the item size
        if self.__width != - 1:
            self.set_width(self.__width)
        else:
            self.__dx = 0
        if self.__height != - 1:
            self.set_height(self.__height)
        else:
            self.__dy = 0

        self.__update_text()

    def get_text(self):
        """
        Gets the text of the item.
        """
        return self.__text

    def set_text(self, text):
        """
        Sets the text of the item.
        - text: Text.
        """
        if self.__text != text:
            self.__text = text
            self.__update_text()

    def break_text_into(self, item_text):
        """
        Sets an ItemText to set the text that doesn't fit inside this ItemText. After invoke this
        function, when you assign a text into the ItemText if the text can't be shown completely inside
        this ItemText the remaining text is assigned to the specified ItemText.
        - item_text: ItemText to assign the text that doesn't fit into this ItemText.
        """
        self.__break_text_into = item_text

    def update(self, frame_delay):
        """
        Updates the item before draw it in the stage. Returns the
        rectangle that must be updated.
        - frame_delay: Milliseconds elapsed from the previous frame.
        """
        if self.__text_surface == None:
            self.__render_text()

        return Item.update(self, frame_delay)

    def hit_test(self, x, y):
        """
        Return the index of the character of the text that is below
        the specified X, Y coordinates.
        - x: X coordinate.
        - y: Y coordinate.
        """
        # Add some pixels of the X coordinate to select the next
        # char if the coordinate is near of its border
        adjust = self.__font.get_linesize() / 4
        editable = (self.__edit_mode != None)
        return hittest_text(self.__text, x - self.get_left() + adjust, y - self.get_top(), 
                            self.__font, self.__additional_fonts, self.__line_height,
                            self.__width, self.__height, True, self.__h_align, editable,
                            self.__break_text_into)        

    def set_edit_on_click(self, item):
        """
        Configure the specified item to begin edit this text when the 
        item is clicked.
        - item: Item.        
        """
        item.add_event_handler(ItemEvent.CLICK, self.__begin_edit_on_click)            
            
    def set_max_chars(self, max_chars):
        """
        Sets the maximum number of characters allowed to enter in the ItemText,
        when it is in edit mode.
        - max_char: Maximum number of characters.
        """
        self.__max_chars = max_chars

    def begin_edit(self, x = 1000, y = 1000):
        """
        Starts the editing mode in this text item.
        - x: X coordinate where the screen was clicked to begin the editing mode.
        - Y: Y coordinate where the screen was clicked to begin the editing mode.
        """        
        if self.__edit_mode == None:
            raise Exception, "The ItemText is not editable."
            
        index = self.hit_test(x, y)
        stage = self.get_stage()
        if stage != None:
            if stage.get_focus() == self:
                stage.get_focus_data()[0] = index
                stage.get_focus_data()[1] = True                
                self.__start_cursor_timer()            
            else:                
                stage.set_focus(self, (index))
            self.__update_text()                                                    

    def end_edit(self):
        """
        Ends the editing mode in this text item.
        """        
        stage = self.get_stage()
        if stage != None:
            if stage.get_focus() == self:
                stage.set_focus(None)                    
                self.__update_text()
                                
    def on_got_focus(self, set_focus_data):
        """
        This function is invoked automatically when the text receives the
        focus.
        - set_focus_data: Data associated with the set focus.
        """ 
        self.__edit_mode = True        
        self.__start_cursor_timer()                           
        index = set_focus_data
        return [index, True]

    def on_lost_focus(self, stage, data):
        """
        This function is invoked automatically when the text lost the
        focus.
        - data: Data associated with the focus.
        """        
        timer_key = (self, "key_repeat")
        stage.stop_timer(timer_key)        
        self.__edit_mode = False
        self.__update_text()
    
    def handle_event_focused(self, event, data):
        """
        This function is invoked to process events when the control is
        focused.
        - event: Event.
        - data: Data returned by the on_got_focus function.
        """
        if event.type == KEYDOWN:
            key = event.key
            unicode = event.unicode
            
            stage = self.get_stage()
            if stage != None:
                timer_key = (self, "key_repeat")
                if self.__can_repeat(unicode):            
                    stage.start_timer(timer_key, 600, self.__handle_key_repeat, (key, unicode, data, True), True, False)
                    
                if self.__handle_key(key, unicode, data):
                    return True
        elif event.type == KEYUP:
            timer_key = (self, "key_repeat")
            stage = self.get_stage()
            if stage != None:
                stage.stop_timer(timer_key)
            
        return False
    
    def __can_repeat(self, unicode):
        if unicode != '' and \
          ord(unicode) < 255 and \
          unicode.encode('latin-1') in ['á','é','í','ó','ú','Á','É','Í','Ó','Ú']:
            # In the XO the KEY_UP is not raised when one of this letters
            # are written, so disable the repeat because it cannot be detected 
            # whwn the repeat should end            
            return False
        else:            
            return True
            
    def __handle_key_repeat(self, key, args):
        timer_key = (self, "key_repeat")
        if args[3]:
            stage = self.get_stage()
            if stage != None:                
                stage.stop_timer(timer_key)
                stage.start_timer(timer_key, 50, self.__handle_key_repeat, (args[0], args[1], args[2], False), True, False)
                    
        self.__handle_key(args[0], args[1], args[2])
            
    def __handle_key(self, key, unicode, data):        
        updated = False
        handled = False
        old_cursor = data[0]
        old_text = self.__text
                
        if key == K_RETURN:
            # End the editing mode                
            self.end_edit()
            handled = True             
        elif key == K_BACKSPACE:
            if data[0] > 0:
                self.__text = self.__text[:data[0] - 1] + self.__text[data[0]:]
                data[0] -= 1                    
                updated = True
            handled = True
        elif key == K_DELETE:
            if data[0] < len(self.__text):
                self.__text = self.__text[:data[0]] + self.__text[data[0] + 1:]                    
                updated = True
            handled = True
        elif key == K_RIGHT:
            if data[0] < len(self.__text):
                data[0] += 1                    
                updated = True
            handled = True
        elif key == K_LEFT:
            if data[0] > 0:
                data[0] -= 1                    
                updated = True
            handled = True
        elif key == K_HOME or key == K_UP:
            if data[0] > 0:
                data[0] = 0                    
                updated = True
            handled = True
        elif key == K_END  or key == K_DOWN:
            if data[0] < len(self.__text):
                data[0] = len(self.__text)      
                updated = True
            handled = True
        else:         
            if ((unicode != '') and
                ((ord(unicode) > 31 and ord(unicode) < 126) or \
                (ord(unicode) < 255 and unicode.encode('latin-1') in self.VALID_UNICODE_CHARS)) and \
                ((len(self.__text) < self.__max_chars) or (self.__max_chars == -1))):                
                self.__text = self.__text[:data[0]]  + unicode.encode('latin-1') + self.__text[data[0]:]
                data[0] += 1
                updated = True
                handled = True

        if updated:
            # Restart the timer
            data[1] = True
            if not self.__update_text():
                # After change the text, part of the text is now outside
                # of the box, undo the change
                self.__text = old_text
                data[0] = old_cursor
                self.__update_text()
            else:
                self.__start_cursor_timer()
        
        return handled
        
    def __start_cursor_timer(self):
        stage = self.get_stage()
        if stage != None:            
            key = (self, "text_cursor")            
            stage.start_timer(key, 500, self.__update_cursor_timer, stage)

    def __begin_edit_on_click(self, item, args):
        """
        Start the editing mode in this text.
        """
        stage = item.get_stage()
        if stage != None:
            focused_item = stage.get_focus()
        else:
            focused_item = None
            
        if focused_item == self:
            self.begin_edit(args.x, args.y)    
        else:
            self.begin_edit()
            
    def __update_text(self):
        """
        Updates the text.
        """
        text_fit_in_box = self.__render_text()
        self.set_dirty()
        
        return text_fit_in_box

    def __render_text(self):
        """
        Render the text's surface.
        """
        
        # If it is in edit mode, get the index where the cursor should be paint
        cursor_index = -1
        editable = False
        if self.__edit_mode != None:
            editable = True            
            stage = self.get_stage()
            if stage != None:                
                if self.__edit_mode:
                    focus_data = stage.get_focus_data()
                    if focus_data[1]:
                        cursor_index = focus_data[0]                                        
                
        text_surface, text_fit, lines = render_text(self.__text, self.__font, self.__additional_fonts, self.__line_height,
                                   self.__width, self.__height, True, self.__color, self.__background,
                                   self.__h_align, self.__break_text_into, cursor_index, editable)
        self.lines = lines
        self.__text_surface = text_surface
        self.__source_surface = text_surface

        text_width = text_surface.get_width()
        text_height = text_surface.get_height()

        if self.__width == - 1:
            self.set_width(text_width)
        else:
            if self.__h_align == 1:
                # Align the text to the left (horizontally)
                self.__dx = 0
            elif self.__h_align == 2:
                # Align the text to the center (horizontally)
                self.__dx = (self.__width - text_width) / 2
            elif self.__h_align == 3:
                # Align the text to the right
                self.__dx = self.__width - text_width

        if self.__height == - 1:
            self.set_height(text_height)
        else:
            if self.__v_align == 1:
                # Align the text to the top
                self.__dy = 0
            elif self.__v_align == 2:
                # Align the text to the center (vertically)
                self.__dy = (self.__height - text_height) / 2
            elif self.__v_align == 3:
                # Align the text to the bottom
                self.__dy = self.__height - text_height
        if self.__alpha != 255:
            self.__text_surface = set_surface_alpha(self.__source_surface, self.__alpha)
                    
        return text_fit

    def __mark_text_to_update(self):
        """
        Marks the text to update.
        """
        self.__text_surface = None
        self.set_dirty()

    def __draw_item(self, item, target):
        """
        Draws the item.
        - item: Item to be drawn.
        - target: An instance of CustomDraw to draw the item.
        """
        target.blit_surface(self.__text_surface, (self.get_left() + self.__dx, self.get_top() + self.__dy))

    def __rollover_color_mouse_enter(self, item, args):
        """
        Function that is invoked when the mouse enters in an item with rollover in the color.
        """
        if self.__rollover_color != None:
            self.__rollover_color[1] = self.__color
            self.__color = self.__rollover_color[0]
            self.__mark_text_to_update()

    def __rollover_color_mouse_leave(self, item, args):
        """
        Function that is invoked when the mouse leaves in an item with rollover in the color.
        """
        if self.__rollover_color != None:
            old_color = self.__rollover_color[1]
            if old_color != None:
                self.__color = old_color
                self.__mark_text_to_update()
                self.__rollover_color[1] = None
                
    def __update_cursor_timer(self, key, data):
        """
        Function that is invoked by the timer to hide/show the cursor when editing.
        """
        stage = data
        focused_item = stage.get_focus()
        if focused_item != self:            
            stage.stop_timer(key)
        else:
            focus_data = stage.get_focus_data()
            focus_data[1] = not focus_data[1]
            self.__update_text()            

class ItemRect(Item):
    """
    Defines an item that shows a rectangle
    """

    def __init__(self, left, top, width, height, font = None, line_height = 0, text = "", color = (0, 0, 0), background = (0, 0, 0), border = None, text_h_align = 1, additional_fonts = []):
        """
        Constructor
        - left: X coordinate of the upper-left corner of the item.
        - top: Y coordinate of the upper-left corner of the item.
        - width: Width of the rectangle.
        - height: Height of the rectangle.
        - font: Font used to render the text. None if there is no text.
        - line_height: Line height. 0 to use default height.
        - text: Default text. "" if there is no text.
        - color: Text's color. It could be an (R, G, B) tuple.
        - background: Background color. None if the background is transparent.
        - border: Border color. None if there is no border.
        - text_h_align: Text horizontal alignment (1 = left, 2 = center, 3 = right).
        - additional_fonts: Dictionary with the additional fonts that can be
          referenced in the text using &#f:font_name! or &#f! to use the
          default font. It must be indexed by the name of the font. And the
          values of the dictionary must a pair with (font, line_height),
          use 0 in the line_height to use the default line height of
          the font.
        """

        self.__font = font
        self.__additional_fonts = additional_fonts
        if line_height == 0 and font != None:
            self.__line_height = font.get_linesize()
        else:
            self.__line_height = line_height
        self.__color = color
        self.__background = background
        self.__border = border
        self.__text_h_align = text_h_align

        # Initialize base class
        Item.__init__(self, left, top, width, height)

        # Set the text
        self.__text = text
        self.__update_text()

        # Set the function to draw the item
        self.draw_function = self.__draw_item

    def get_color(self):
        """
        Gets the color of the text.
        """
        return self.__color

    def set_color(self, color):
        """
        Sets the color of the text.
        - color: Color.
        """
        if self.__color != color:
            self.__color = color

            # Marks the text to update later because the width/height
            # doesn't change after render it so delay the update because
            # other changes could be performed before update the text
            # in the screen
            self.__mark_text_to_update()

    def get_background(self):
        """
        Gets the background of the rectangle.
        """
        return self.__background

    def set_background(self, background):
        """
        Sets the background of the rectangle.
        - color: Color.
        """
        if self.__background != background:
            self.__background = background

            # Marks the text to update later because the width/height
            # doesn't change after render it so delay the update because
            # other changes could be performed before update the text
            # in the screen
            self.__mark_text_to_update()

    def get_font(self):
        """
        Gets the font used to draw the text.
        """
        return self.__font

    def set_font(self, font):
        """
        Sets the font used to draw the text.
        - font: Font.
        """
        if self.__font != font:
            self.__font = font
            self.__update_text()

    def get_text(self):
        """
        Gets the text of the item.
        """
        return self.__text

    def set_text(self, text):
        """
        Sets the text of the item.
        - text: Text.
        """
        if self.__text != text:
            self.__text = text
            self.__update_text()

    def update(self, frame_delay):
        """
        Updates the item before draw it in the stage. Returns the
        rectangle that must be updated.
        - frame_delay: Milliseconds elapsed from the previous frame.
        """
        if self.__text_surface == None and self.__text != "":
            self.__render_text()

        return Item.update(self, frame_delay)

    def __update_text(self):
        """
        Updates the text.
        """
        self.__render_text()
        self.set_dirty()

    def is_over(self, x, y):
        """
        Determines if the specified point is contained in a rectangle with
        bounds of the item.
        - x: X coordinate.
        - y: Y coordinate.
        """
        bounds = self.get_bounds()
        if self.__background != None:
            return ((bounds[0] <= x) and (x < bounds[0] + bounds[2]) and
                    (bounds[1] <= y) and (y < bounds[1] + bounds[3]))
        else:
            return ((bounds[0] == x) or (x == bounds[0] + bounds[2] - 1) and
                    (bounds[1] == y) or (y == bounds[1] + bounds[3] - 1))

    def __render_text(self):
        """
        Render the text's surface.
        """
        width = self.get_width()
        height = self.get_height()

        if self.__text == "":
            self.__text_surface = None
            self.__text_width = width
            self.__text_height = height
            text_fit = True
        else:
            if self.__background == None or ((len(self.__background) >= 4) and (self.__background[3] != 255)):
                # Text background cannot have transparency
                text_background = None
            else:
                text_background = self.__background
            self.__text_surface, text_fit = render_text(self.__text, self.__font, self.__additional_fonts, self.__line_height,
                                                              width, height, True, self.__color, text_background,
                                                              self.__text_h_align, None)
            self.__text_width = width
            self.__text_height = height
        self.set_dirty()
        
        return text_fit

    def __draw_item(self, item, target):
        """
        Draws the item.
        - item: Item to be drawn.
        - target: An instance of CustomDraw to draw the item.
        """
        draw_rect = item.get_bounds()
        width = draw_rect[2]
        height = draw_rect[3]

        # Check if the size of the item changed and the rendered text
        # must be updated
        if (self.__text_width != width) or (self.__text_height != height):
            self.__update_text()

        # Draw rectangle's background
        if self.__background != None:
            target.fill(self.__background, draw_rect)

        # Draw the text
        if self.__text_surface != None:
            text_x = draw_rect.left + (draw_rect.width - self.__text_surface.get_width()) / 2
            text_y = draw_rect.top + (draw_rect.height - self.__text_surface.get_height()) / 2
            target.blit_surface(self.__text_surface, (text_x, text_y))

        # Draw the border
        if self.__border != None:
            target.draw_rect(self.__border, draw_rect)

    def __mark_text_to_update(self):
        """
        Marks the text to update.
        """
        self.__text_surface = None
        self.set_dirty()

class ItemObject(ItemImage):
    """
    Represents an object that we can apply movement animations.
    """
    def __init__(self, left, top, image, test_collision, normal_deceleration=None, area=None):
        """
        Constructor.
        - left: X coordinate of the upper-left corner of the item.
        - top: Y coordinate of the upper-left corner of the item.
        - image: Image that is used to draw the object. It must be an instance of assets.Image class.
        - test_collision: Function used to test if the item collide with another item when it is moved.
          The function receives (item, new_left, new_top) and must return True if there is a collision.
          None if there is no function to test the collision.
        - normal_deceleration: Deceleration that is applied when we stop to move the object (we
          invoke function stop_move). None if there is no normal deceleration.
        - area: Area of the image to be shown (a Rect). None to show the whole image.

        The normal deceleration is expressed in pixels per second squared.
        """

        # Initialize base class
        ItemImage.__init__(self, left, top, image, area)

        self.__prev_velocity = (0.0, 0.0)
        self.__normal_deceleration = normal_deceleration
        self.__test_collision = test_collision
        self.__nokey_move = None
        self.__key_moves = []

    def start_move_vel(self, vel_x, vel_y, key_event=None):
        """
        Starts to move the object with a fixed velocity.
        - vel_x: Horizontal velocity. Positive values move the object to the right, negative values
          move the object to the left.
        - vel_y: Vertical velocity. Positive values move to object down, negative values move the
          object up.
        - key_event: Key event associated with the movement. Use this parameter if this movement was started
          when a key was pressed (a KEY_DOWN event). Then you can stop the movement when the key is released
          (KEY_UP event) invoking stop_move with the key event.

        The velocity is expressed in pixels per second.
        """
        self.__start_move((0, vel_x, vel_y), key_event)

    def start_move_accel(self, accel_x, accel_y, max_vel_x=9999, max_vel_y=9999, key_event=None):
        """
        Starts to move the object with a fixed acceleration.
        - accel_x: Horizontal acceleration. Positive values increase the horizontal velocity (until 'max_vel_x),
          negative values decrease the horizontal velocity (until 0).
        - accel_y: Vertical acceleration. Positive values increase the vertical velocity (until 'max_vel_y),
          negative values decrease the vertical velocity (until 0).
        - max_vel_x: Maximum horizontal velocity, the acceleration is applied until the velocity reach this
          value.
        - max_vel_y: Maximum vertical velocity, the acceleration is applied until the velocity reach this
          value.
        - key_event: Key event associated with the movement. Use this parameter if this movement was started
          when a key was pressed (a KEY_DOWN event). Then you can stop the movement when the key is released
          (KEY_UP event) invoking stop_move with the key event.

        The acceleration is expressed in pixels per second squared.

        The velocity is expressed in pixels per second.
        """
        self.__start_move((1, accel_x, accel_y, max_vel_x, max_vel_y), key_event)

    def start_move_dynvel(self, vel_func, key_event=None):
        """
        Starts to move the object with a dynamic velocity.
        - vel_func: Function that returns the velocity for a given frame. The function is invoked
          with (item, frame_delay) and must return a tuple with (velocity x, velocity y).
        - key_event: Key event associated with the movement. Use this parameter if this movement was started
          when a key was pressed (a KEY_DOWN event). Then you can stop the movement when the key is released
          (KEY_UP event) invoking stop_move with the key event.

        The velocity is expressed in pixels per second.
        """
        self.__start_move((2, vel_func), key_event)

    def stop_move(self, key_event=None):
        """
        Stop a movement in the object.
        - key_event: Key event if the movement was produced from a key event.
        """
        if key_event == None:
            self.__nokey_move = None
        else:
            # If there is a move vector associated with the key we remove it
            k = 0
            while k < len(self.__key_moves):
                if self.__key_moves[k][0] == key_event.key:
                    del self.__key_moves[k]
                else:
                    k += 1

        self.set_dirty()

    def update(self, frame_delay):
        """
        Updates the item before draw it in the stage. Returns the
        rectangle that must be updated.
        - frame_delay: Milliseconds elapsed from the previous frame.
        """

        # Calculate the velocity of current defined movements
        vel_x = 0
        vel_y = 0
        n = 0
        if self.__nokey_move != None:
            vel_x, vel_y = self.__do_move(self.__nokey_move, frame_delay)
            n += 1
        for key_move in self.__key_moves:
            move_vel_x, move_vel_y = self.__do_move(key_move[1], frame_delay)
            vel_x += move_vel_x
            vel_y += move_vel_y
            n += 1
        if n == 0:
            # There is no movement. Apply the normal deceleration
            if self.__normal_deceleration != None:
                if self.__prev_velocity[0] >= 0:
                    vel_x = max(0, self.__prev_velocity[0] + float(self.__normal_deceleration[0] * frame_delay) / 1000)
                else:
                    vel_x = min(0, self.__prev_velocity[0] - float(self.__normal_deceleration[0] * frame_delay) / 1000)
                if self.__prev_velocity[1] >= 0:
                    vel_y = max(0, self.__prev_velocity[1] + float(self.__normal_deceleration[1] * frame_delay) / 1000)
                else:
                    vel_y = min(0, self.__prev_velocity[1] - float(self.__normal_deceleration[1] * frame_delay) / 1000)
        else:
            # Calculate the average velocity
            vel_x /= n
            vel_y /= n

        # Calculate the new position according to the velocity
        new_left = self.get_left() + vel_x * frame_delay
        new_top = self.get_top() + vel_y * frame_delay

        # Check if the new position produce a collision with another item
        if self.__test_collision == None or not self.__test_collision(self, new_left, new_top):
            self.set_lefttop(new_left, new_top)
        else:
            # There is a collision. Stop the movement
            vel_x = 0
            vel_y = 0
            self.__nokey_move = None
            self.__key_moves = []

        # Update the item
        rect = ItemImage.update(self, frame_delay)

        # Mark the item as dirty if we the velocity is not zero or we have movements
        if vel_x != 0 or vel_y != 0 or self.__nokey_move != None or len(self.__key_moves) > 0:
            self.set_dirty()

        # Store the last velocity used
        self.__prev_velocity = (vel_x, vel_y)

        return rect

    def __start_move(self, move_tuple, key_event):
        """
        Starts a move.
        - move_tuple: Move tuple data.
        - key_event: Key event associated with the movement, or None if there is no key event.
        """
        if key_event == None:
            self.__nokey_move = move_tuple
        else:
            for key_move in self.__key_moves:
                if key_move[0] == key_event.key:
                    self.__key_moves.remove(key_move)
            self.__key_moves.append((key_event.key, move_tuple))

        self.set_dirty()

    def __do_move(self, move_data, frame_delay):
        """
        Calculate the velocity vector of the specified movement.
        - move_data: Move data.
        - frame_delay: Milliseconds elapsed from the previous frame.
        """
        if move_data[0] == 0:
            return (move_data[1], move_data[2])
        elif move_data[0] == 1:
            vel_x = self.__prev_velocity[0] + float(move_data[1] * frame_delay) / 1000
            vel_y = self.__prev_velocity[1] + float(move_data[2] * frame_delay) / 1000

            # Check the velocity limits
            if move_data[1] >= 0:
                if vel_x > move_data[3]:
                    vel_x = move_data[3]
            else:
                if vel_x < move_data[3]:
                    vel_x = move_data[3]
            if move_data[2] >= 0:
                if vel_y > move_data[4]:
                    vel_y = move_data[4]
            else:
                if vel_y < move_data[4]:
                    vel_y = move_data[4]

            return vel_x, vel_y
        else:
            return move_data[1](frame_delay)

def render_text(text, font, additional_fonts, line_height, max_width, max_height, 
                antialias, color, background, h_align, break_text_into, cursor_index = -1,
                editable = False):
    """
    Render the text and returns a surface with the result.
    - text: Text.
    - font: Font used to render the text.
    - additional_fonts: Dictionary with the additional fonts that can be
      referenced in the text using &#f:font_name! or &#f! to use the
      default font. It must be indexed by the name of the font. And the
      values of the dictionary must a pair with (font, line_height, y_adjust),
      use 0 in the line_height to use the default line height of
      the font. If y_adjust has a positive value the text is moved down. 
    - line_height: Line height.
    - max_width: Maximum width of the text. -1 if there is no maximum width.
    - max_height: Maximum height of the text. -1 if there is no maximum height.
    - antialias: Indicates if the text is rendered with using antialiasing.
    - color: Color used to render the text.
    - background: Background of the text.
    - h_align: Horizontal alignment (1 = left, 2 = center, 3 = right).
    - break_text_into: Item to assign the text that doesn't fit in this surface.
    - cursor_index: Index where the cursor must be drawn. -1 to doesn't draw the cursor.
    - editable: Indicates if the text is editable.
    """
    # Split the text in lines        
    if max_width == -1:
        max_line_width = sys.maxint
    else:
        max_line_width = max_width
        if editable:
            # Reserve some space to add the cursor at the end of the text
            max_line_width -= 2            
    
    # Wrap the text in lines    
    lines, remaining_lines, break_color, break_font = wrap_text_in_lines(text, 
        False, color, font, line_height, additional_fonts, max_line_width, max_height,
        break_text_into)        
        
    # Render the lines
    line_surfs = []
    width = 0
    if background == None or ((len(background) >= 4) and (background[3] != 255)):
        # Text background cannot have transparency
        text_background = None
    else:
        text_background = background
    height = 0
    line_count = len(lines)
    for i in xrange(line_count):        
        line = lines[i]
        part_surfs = []
        line_surfs_width = 0
        line_surfs_height = 0
        for line_part in line:            
            part_font_data = line_part[1]
            if text_background == None:
                part_surf = part_font_data[0].render(line_part[2], antialias, line_part[0])
            else:
                # If more efficient to draw the text with a background if available
                part_surf = part_font_data[0].render(line_part[2], antialias, line_part[0], text_background)
            line_surfs_width += part_surf.get_width()
            part_surfs.append((part_surf, part_font_data))

            # Update the height for the line
            if i < line_count - 1:
                part_height = part_font_data[1]
            else:
                # It is the line line, ensures that all the line is drawn
                # and it is not cut
                part_height = max(font.get_linesize(), part_font_data[1])

            if part_height > line_surfs_height:
                line_surfs_height = part_height
        line_surfs.append((line_surfs_width, line_surfs_height, part_surfs))
        if line_surfs_width > width:
            width = line_surfs_width
        height += line_surfs_height
        
    # Draw the cursor
    if cursor_index != -1:
        if height == 0:
            height = line_height            

        # Wrap the text in lines (for hit_test to avoid extra characters 
        # like "..." or "-")
        cursor_text_data = wrap_text_in_lines(text, True, color, font, line_height, additional_fonts, max_line_width, max_height, break_text_into)        
        
        # Draw the cursor
        draw_cursor(cursor_index, text, cursor_text_data[0], line_surfs, width, line_height, font)
        
        # Add an extra width to draw the cursor at the end of the text if necessary
        extra_width = 2
    else:
        extra_width = 0
        
    # Join the lines in one surface
    surface = pygame.Surface((width + extra_width, height), pygame.SRCALPHA, 32)
    if background == None:
        surface.fill((0, 0, 0, 0))
    else:
        surface.fill(background)
    line_y = 0
    for i in xrange(len(line_surfs)):
        if h_align == 1:
            line_x = 0
        elif h_align == 2:
            line_x = (width - line_surfs[i][0]) / 2
        elif h_align == 3:
            line_x = (width - line_surfs[i][0])

        parts_height = line_surfs[i][1]
        line_part_surfs = line_surfs[i][2]
        max_ascent = -1
        for part_surf_data in line_part_surfs:
            part_surf = part_surf_data[0]
            part_height = part_surf_data[1][1]
            y_adjust = part_surf_data[1][2]
            if part_height >= parts_height:
                surface.blit(part_surf, (line_x, line_y + y_adjust))                
            else:
                # The height of the part is lower than the height of the
                # line. Align the part to share the same base line with all
                # the parts of the line
                if max_ascent == -1:
                    for part_surf_data2 in line_part_surfs:
                        ascent = part_surf_data2[1][0].get_ascent()
                        if ascent > max_ascent:
                            max_ascent = ascent
                margin = max_ascent - part_surf_data[1][0].get_ascent()
                surface.blit(part_surf, (line_x, line_y + margin + y_adjust))
            line_x += part_surf.get_width()
        line_y += parts_height

    # Set the text that doesn't fit in the specified item    
    if break_text_into != None:
        # Remove empty lines at the beginning of the text
        k = 0
        while k < len(remaining_lines):
            line = remaining_lines[k]

            # Test if has only spaces
            only_spaces = True
            for c in line:
                if c != ' ' and c != '\r' and c != '\t':
                    only_spaces = False
                    break
            if only_spaces:
                k += 1
            else:
                break
        if k > 0:
            remaining_lines = remaining_lines[k:]

        remaining_text = "\n".join(remaining_lines)

        # If the color selected when the text was break is not the default 
        # color add a control character to indicate the color
        if break_font[0] != font and break_font[1] != None:
            remaining_text = "&#f:" + break_font[1] + '!' + remaining_text        
        if break_color != color:
            remaining_text = "&#c" + ','.join(map(str, break_color)) + '!' + remaining_text
        break_text_into.set_text(remaining_text)

    return surface, len(remaining_lines) == 0, [surf[0] for surf in line_surfs]

def draw_cursor(cursor_index, text, lines, line_surfs, width, line_height, font):
    """
    Draw the cursor in the line surfaces.
    - cursor_index: Index where the cursor is drawn.
    - text: Text.
    - lines: Lines data.
    - line_surf: Surfaces rendered for the lines.
    - width: Width of the surface to draw the text.
    - line_height: Line's height.
    - font: Font.
    """
    line_index = 0
    text_index = 0    
    while line_index < len(lines):
        line = lines[line_index]
        part_index = 0
        while part_index < len(line):
            part = line[part_index]
            part_text = part[2]
            
            if cursor_index >= text_index and cursor_index < text_index + len(part_text):
                # Found where the cursor should be drawn. Draw it
                part_surf = line_surfs[line_index][2][part_index][0]                
                char_index = cursor_index - text_index
                part_font = part[1][0] 
                x = part_font.size(part_text[0:char_index])[0]
                draw_cursor_in_surface(part_surf, x)
                
                return                                        
            else:
                text_index += len(part_text)
            
            part_index += 1
            
        line_index += 1        
    
    # Didn't found the character where the cursor should be drawn. Draw
    # the cursor at the end of the text
    line_index = len(lines) - 1
    if line_index < 0:        
        # There is no lines. Add a new one
        new_surf = pygame.Surface((2, line_height), pygame.SRCALPHA, 32)
        draw_cursor_in_surface(new_surf, 0)    
        line_part_surfs = [(new_surf, (font, line_height, 0))]        
        line_surfs.append((2, line_height, line_part_surfs))
    else:
        line = lines[line_index]
        part_index = len(line) - 1
        if part_index >= 0:
            part = line[part_index]
            line_surfs_data = line_surfs[line_index]
            line_part_surfs = line_surfs_data[2] 
            part_surf_data = line_part_surfs[part_index] 
            part_surf = part_surf_data[0]
            
            # Create a new surface to add space to draw the cursor
            width, height = part_surf.get_size()
            new_surf = pygame.Surface((width + 2, height), pygame.SRCALPHA, 32)
            new_surf.blit(part_surf, (0, 0))
                            
            if len(part_surf_data) != 2:
                raise Exception, "Invalid surface part data, excepted data with length 2. Fix the code below to copy all the data if the size changed."                                
            line_part_surfs[part_index] = (new_surf, part_surf_data[1])
            
            # Draw the cursor
            draw_cursor_in_surface(new_surf, width)                    
            
def draw_cursor_in_surface(surf, x):
    """
    Draw a cursor in the specified position.
    - surf: Surface where the cursor is drawn.
    - x: X coordinate where the cursor is drawn.
    """
    surf.fill((0, 0, 0), (x, 1, 2, surf.get_height() - 2))

def hittest_text(text, x, y, font, additional_fonts, line_height, max_width, max_height, 
                 antialias, h_align, editable = False, break_text_into = None):
    """
    Determines the index of the char below the specified coordinates in 
    the text.
    - text: Text.
    - x: X coordinate of where the hit test is done. The text starts in 0.
    - y: Y coordinate of where the hit test is done. The text starts in 0.
    - font: Font used to render the text.
    - additional_fonts: Dictionary with the additional fonts that can be
      referenced in the text using &#f:font_name! or &#f! to use the
      default font. It must be indexed by the name of the font. And the
      values of the dictionary must a pair with (font, line_height, y_adjust),
      use 0 in the line_height to use the default line height of
      the font. If y_adjust has a positive value the text is moved down. 
    - line_height: Line height.
    - max_width: Maximum width of the text. -1 if there is no maximum width.
    - max_height: Maximum height of the text. -1 if there is no maximum height.
    - antialias: Indicates if the text is rendered with using antialiasing.
    - h_align: Horizontal alignment (1 = left, 2 = center, 3 = right).
    - editable: Indicates if the text is editable.
    - break_text_into: Item to assign the text that doesn't fit in this surface.
    """
    # Split the text in lines    
    if max_width == - 1:
        max_line_width = sys.maxint
    else:
        max_line_width = max_width
        if editable:
            # Reserve some space to add the cursor at the end of the text
            max_line_width -= 2
                        
    # Wrap the text in lines    
    result = wrap_text_in_lines(text, 
        False, color, font, line_height, additional_fonts, max_line_width, max_height,
        break_text_into)    
    lines = result[0]    
                            
    # Calculate the line index that is below the specified coordinates
    line_y = 0
    line_index = 0
    index = 0
    while line_index < len(lines) - 1 and line_y + line_height < y:        
        for line_part in lines[line_index]:
            index += len(line_part[2])
        if index < len(text) and text[index] == '\n':
            index += 1
                
        line_y += line_height 
        line_index += 1
       
    if line_index < len(lines):        
        part_index = 0        
        line_x = 0
        line = lines[line_index]
        found = False
        while part_index < len(line) and not found:
            part = line[part_index]
            char_index = 0
            part_font = part[1][0] 
            part_text = part[2]
            char_width = 0
            while char_index < len(part_text):
                char_index += 1
                char_width = part_font.size(part_text[0:char_index])[0]                                
                                
                if line_x + char_width < x:                    
                    index += 1
                else:
                    found = True
                    break
            
            line_x += char_width
            part_index += 1
        
        if not found and index > 0 and line_index + 1 < len(lines):
            # Perform and adjustment in the index to select the last char
            index -= 1
            
    return index
    
def wrap_text_in_lines(text, hit_test, color, font, line_height, additional_fonts, max_line_width, max_height,
                       break_text_into):
    """
    Wrap the text in lines.
    - text: Text to wrap.
    - hit_test: Indicates if wrap the text for hit test.
    - color: Color used to render the text.
    - font: Font used to render the text.
    - line_height: Line height for the font.
    - additional_fonts: Dictionary with the additional fonts that can be
      referenced in the text.
    - max_line_width: Maximum line width.
    - max_height: Maximum height.
    - break_text_into: Item to assign the text that doesn't fit in this surface.
    """     
    lines = []
    remaining_lines = []
    current_height = [0]
    current_color = [color]
    current_font = [font, line_height, 0, None]    
    for line in text.splitlines():
        wrap_line(line, hit_test, font, line_height, additional_fonts, lines, current_height, 
                  max_line_width, max_height, remaining_lines, color, current_color, 
                  current_font, False, break_text_into)
        
    return lines, remaining_lines, current_color[0], (current_font[0], current_font[1]) 
    
def wrap_line(line, hit_test, font, line_height, additional_fonts, lines, current_height, max_width, max_height, 
              remaining_lines, default_color, current_color, current_font, 
              add_ellipsis, break_text_into):
    """
    If the line is too long, split the line in multiple lines.
    - line: Line to wrap.
    - hit_test: Indicates if wrap the text for hit test.
    - font: Font used to render the text.
    - line_height: Line height for the font.
    - additional_fonts: Dictionary with the additional fonts that can be
      referenced in the text.
    - lines: List where the result is added.
    - current_height: Current height of the text.
    - max_width: Maximum width for a line.
    - max_height: Maximum height for the text.
    - max_line_count: Maximum line count. -1 if there is no limit.
    - remaining_lines: List to add the lines that cannot be written because the text is too long.
    - default_color: Default text color.
    - current_color: Array to store current line color.
    - current_font: Array to store the current font with its line height.
    - add_ellipsis: Indicates if must add '...' if a word is too long.
    - break_text_into: Item to assign the text that doesn't fit in this surface. 
    """
    if max_height != - 1 and current_height[0] + line_height > max_height:
        remaining_lines.append(line)
    else:
        # Calculate the width of the line
        line_width = current_font[0].size(line)[0]

        # Check if the line is too long (and doesn't have control characters)
        if line_width <= max_width and line.find("&#") == - 1:
            lines.append([(current_color[0], current_font[:], line)])
            current_height[0] += current_font[1]
        else:
            # The line contains control characters or is too long. Split the line in pats to
            # analyze the control chars, and then in words to shorten the line
            start = 0
            new_line = ''
            empty_line = True
            line_width = 0
            space_width = current_font[0].size(' ')[0]
            line_parts = []
            line_parts_height = 0
            while start < len(line):
                next_control = line.find("&#", start)
                if next_control == - 1:
                    line_part = line[start:]
                    next_word = ''
                else:
                    line_part = line[start:next_control]
                    next_control_end = line.find('!', next_control)
                    if next_control_end == - 1:
                        next_control_end = len(line)

                    k = line.find(' ', next_control_end + 1)
                    if k == -1:
                        next_word = line[next_control_end + 1:]
                    else:
                        next_word = line[next_control_end + 1:k]

                if line_part != '':
                    # Split the part in word to determine the maximum number of words for the line
                    words = line_part.split(' ')
                    i = 0
                    new_line = ''
                    for i in xrange(len(words)):
                        add_word = words[i]      
                        add_space = True                  
                        while add_word != None:
                            word = add_word                            
                            add_word = None                         
                            word_width = current_font[0].size(word)[0]
    
                            if i == len(words) - 1:
                                extra_width = current_font[0].size(next_word)[0]
                            else:
                                extra_width = 0
    
                            if word_width > max_width:                                                                
                                if add_ellipsis:
                                    # The word is too long truncate it
                                    end_width = current_font[0].size('...')[0]
                                    if end_width > max_width:
                                        word = ''
                                        word_width = 0
                                    else:
                                        k = len(word)
                                        while k >= 0 and word_width + end_width > max_width:
                                            k -= 1
                                            word_width = current_font[0].size(word[0:k])[0]
                                        if hit_test:                                        
                                            word = word[:k]
                                        else:
                                            word = word[:k] + '...'
                                        word_width += end_width
                                else:
                                    is_last_line = current_height[0] + current_font[1] * 2 >= max_height
                                    if not is_last_line or break_text_into != None:
                                        # There are more lines. Add a '-' to separate the word                                                                         
                                        end_width = current_font[0].size('-')[0]
                                        if end_width > max_width:
                                            word = ''
                                            word_width = 0
                                        else:
                                            k = len(word)
                                            while k >= 0 and word_width + end_width > max_width:
                                                k -= 1
                                                word_width = current_font[0].size(word[0:k])[0]
                                            add_word = word[k:]
                                            if hit_test:                                        
                                                word = word[:k]
                                            else:
                                                word = word[:k] + '-'
                                            word_width += end_width
                                    else:
                                        # Is the last line. Truncate the word
                                        k = len(word)
                                        while k >= 0 and word_width > max_width:
                                            k -= 1
                                            word_width = current_font[0].size(word[0:k])[0]
                                        word = word[:k]                                    
                            
                            if (empty_line) and (line_width + word_width + extra_width <= max_width):                                
                                new_line = word
                                line_width += word_width
                                empty_line = False
                            elif (line_width + word_width + space_width + extra_width <= max_width):                                
                                new_line += ' ' + word
                                line_width += word_width + space_width
                            else:                                
                                # The end of the line was found. Add it in the result
                                if new_line != '':
                                    if word != '' and add_space:
                                        new_line += ' '
                                    line_parts.append((current_color[0], current_font[:], new_line))
                                    line_parts_height = max(line_parts_height, current_font[1])
                                if len(line_parts) > 0:
                                    lines.append(line_parts)
                                    current_height[0] += line_parts_height
    
                                # Start a new line
                                line_parts = []
                                line_parts_height = 0
                                if word == '':
                                    new_line = ''
                                    line_width = 0
                                    empty_line = True
                                else:
                                    new_line = word
                                    line_width = word_width
    
                                # Check if the maximum height was reached
                                if max_height != - 1 and current_height[0] + line_height >= max_height:
                                    text = ' '.join(words[i:])
                                    if next_control != -1:
                                        text += line[next_control:]
                                    remaining_lines.append(text)
                                    return

                            # Avoid to add an ending space while processing the same word
                            add_space = False
                        i += 1

                # Process the control char
                if next_control == - 1:
                    start = len(line)
                else:
                    if next_control_end >= next_control + 3:
                        c = line[next_control + 2]
                        if c == 'c' or c == 'f':
                            # A control character was used to define a new color or a new font.
                            # Add the line written until now with the current color before change
                            # the color
                            if new_line != '':
                                line_parts.append((current_color[0], current_font[:], new_line))
                                line_parts_height = max(line_parts_height, current_font[1])
                                new_line = ''
                                empty_line = True

                            if next_control + 3 == next_control_end:
                                # No color or font was defined, use default color or font
                                if c == 'c':
                                    current_color[0] = default_color
                                elif c == 'f':
                                    current_font[0] = font
                                    current_font[1] = line_height
                                    current_font[2] = 0
                                    current_font[3] = None
                            elif c == 'c':
                                rgb = line[next_control + 3:next_control_end].split(",")
                                current_color[0] = (int(rgb[0]), int(rgb[1]), int(rgb[2]))
                            elif c == 'f':
                                font_name = line[next_control + 4:next_control_end]
                                font_selected = additional_fonts[font_name]
                                if len(font_selected) >= 3:                                                            
                                    current_font[:] = [font_selected[0], font_selected[1], font_selected[2], font_name]
                                else:
                                    current_font[:] = [font_selected[0], font_selected[1], 0, font_name, None]
                                if current_font[1] == 0:
                                    current_font[1] = current_font[0].get_linesize()

                    start = next_control_end + 1

            # Add the last line
            if new_line != '':
                line_parts.append((current_color[0], current_font[:], new_line))
                line_parts_height = max(line_parts_height, current_font[1])
            if len(line_parts) > 0:
                lines.append(line_parts)
                current_height[0] += line_parts_height

def set_surface_alpha(surface, alpha):
    """
    Sets the alpha value of a surface.
    - surface: Surface.
    - alpha: Alpha value.
    """
    surface = surface.copy()
    if surface.get_bitsize() < 32:
        surface.set_alpha(alpha)
    elif surface.get_width() != 0:
        alpha_matrix = pygame.surfarray.pixels_alpha(surface)
        mult_alpha = alpha_matrix * (float(alpha) / 255)
        alpha_matrix[:] = mult_alpha.astype('b')

    return surface

class Layer:
    """
    Represents a layer.

    The standard RenderUpdates redraw all the sprites, this class is optimized
    to detect which sprite is modified and the update area. It assumes that
    all the item in the layer are Item  instances
    """

    def __init__(self):
        """
        Constructor
        """
        self.items = []
        self.stage = None
        self.__visible = True
        self.__changed_handler = None
        self.custom_draw = CustomDraw()
        self.__several_rows_items = []
        self.__alpha = 255
        self.__alpha_buffer = None
        self.__alpha_blit = None
        self.__clip = None
        self.__drawn = False

        # Initialize dirty items
        self.dirty_rects = []
        self.dirty_items = []
        self.dirty_layer = False

    def exit(self):
        self.stage = None
        for item in self.items:
            item.exit()
        self.items = []
        self.custom_draw = None
        self.__changed_handler = None

    def contains(self, item):
        """
        Determines if the layer contains the specified object
        """
        return item in self.items

    def empty(self):
        """
        Remove all the items from the layer
        """
        while len(self.items) > 0:
            self.remove(self.items[0])

    def add(self, item, index= - 1):
        """
        Adds the item in the layer.
        - item: Item.
        - index: Index where the layer in inserted in the layer list. -1
            to add the item at the end.
        """
        layer = item.get_layer()
        if layer != None:
            # There item is already part of a layer remove it before add it to this layer
            # (this is defensive programming to avoid runtime errors because the item is already part of a layer)
            layer.remove(item)

        # Add the item in the layer
        item.set_layer(self)
        if index == - 1:
            index = len(self.items)
            self.items.append(item)
        else:
            self.items.insert(index, item)

        # If the item is an ItemCell mark that the index must be adjusted to show
        # it in the correct place according with its row an column
        if isinstance(item, ItemCell) and self.stage != None:
            definition = item.get_definition()
            if definition.size[0] > 1:
                self.__add_serveral_rows_item(item, definition)
                self.stage.mark_update_positions(self)
            else:
                self.stage.mark_update_positions(self, item)

        # Set the item as dirty to recalculate if area and draw it
        # in the screen
        item.set_dirty()
        
        if self.stage != None:
            # Update the item that is below the mouse         
            self.stage.update_mouse()

    def remove(self, item):
        """
        Remove the item from the layer.
        - item: Item.
        """
        if self.stage != None:
            focused_item = self.stage.get_focus()
        else:
            focused_item = None
        
        if item in self.items:
            if focused_item == item:
                # The item has the focus, remove the focus first
                self.stage.set_focus(None)
            
            self.items.remove(item)
            item.set_layer(None)

            # Append the item's rectangle to force a redraw in this area
            if not item.rect in self.dirty_rects and item.rect.width != 0 and item.rect.height != 0:
                self.dirty_rects.append(item.rect)

                if self.__changed_handler != None:
                    self.__changed_handler(self.stage)

            # If it is a ItemCell we must adjust other item indexes to ensure that
            # they are correctly drawn
            if isinstance(item, ItemCell):
                definition = item.get_definition()
                if definition.size[0] > 1:
                    self.__remove_serveral_rows_item(item)
                    self.stage.mark_update_positions(self)

        if self.stage != None:
            # Update the item that is below the mouse         
            self.stage.update_mouse()

    def index_of(self, item):
        """
        Search the item in the layer and returns the index of the item in the layer.
        """
        return self.items.index(item)

    def get_count(self):
        """
        Get the number of items added in the layer.
        """
        return len(self.items)

    def get_visible(self):
        """
        Gets a value that indicates if the layer items of the layer must be shown
        in the stage.
        """
        return self.__visible

    def set_visible(self, visible):
        """
        Sets a value that indicates if the layer items of the layer must be shown
        in the stage.
        - visible: Value that indicates if the layer is visible.
        """
        if self.__visible != visible:
            self.__visible = visible
            if self.stage != None:
                self.dirty_layer = True

    def update(self, dirty_rects, frame_delay):
        """
        Updates the items before draw it in the stage.
        - dirty_rects: List where the parts of the stage that must be updated
              are added.
        - frame_delay: Milliseconds elapsed from the previous frame.
        """
        # Get a copy of the list of dirty items and rects, and then clear it. In the update
        # we use the lists read so we can set new dirty items (in the lists associated with the layer)
        # to update in the next frame
        dirty_rects_list = self.dirty_rects
        self.dirty_rects = []
        dirty_items_list = self.dirty_items
        self.dirty_items = []

        for rect in dirty_rects_list:
            # If the rect intersects with another, join them. If we don't do this
            # and a part of an item with alpha mid levels is drawn more than once and the
            # resulting painting will not be as expected
            k = rect.collidelist(dirty_rects)
            while k != - 1:
                rect.union_ip(dirty_rects[k])
                del dirty_rects[k]
                k = rect.collidelist(dirty_rects)

            dirty_rects.append(rect)

        # If the layer is marked as dirty add a rect that cover all the items of the layer
        if self.dirty_layer:
            self.dirty_layer = False

            for item in self.items:
                dirty_rect = item.update(frame_delay)
                if self.__clip != None and dirty_rect != None:
                    dirty_rect = dirty_rect.clip(self.__clip)
                if dirty_rect != None and dirty_rect.width != 0 and dirty_rect.height != 0:
                    k = dirty_rect.collidelist(dirty_rects)
                    while k != - 1:
                        dirty_rect.union_ip(dirty_rects[k])
                        del dirty_rects[k]
                        k = dirty_rect.collidelist(dirty_rects)
                    dirty_rects.append(dirty_rect)
        else:
            # Update the dirty items
            for item in dirty_items_list:
                dirty_rect = item.update(frame_delay)
                if self.__clip != None:
                    dirty_rect = dirty_rect.clip(self.__clip)
                    if dirty_rect.width == 0 or dirty_rect.height == 0:
                        dirty_rect = None

                if dirty_rect != None:
                    # If the rect intersects with another, join them
                    k = dirty_rect.collidelist(dirty_rects)
                    while k != - 1:
                        dirty_rect.union_ip(dirty_rects[k])
                        del dirty_rects[k]
                        k = dirty_rect.collidelist(dirty_rects)

                    dirty_rects.append(dirty_rect)

        # If the items of the layer changed and there is an alpha value, updates the alpha buffer
        if self.__alpha != 255:
            if (len(dirty_rects_list) != 0 or len(dirty_items_list) != 0 or \
                (self.dirty_layer and self.__alpha_buffer == None)):
                # Render the layer into a surface
                self.__alpha_buffer, self.__alpha_bounds = self.render_into_surface()

                # Calculate the surface with the alpha value
                self.__alpha_blit = set_surface_alpha(self.__alpha_buffer, self.__alpha)

    def draw(self, surface, dirty_rects):
        """
        Draws the items if the layer.
        - surface: Target surface.
        - dirty_rects: Areas of the stage that must be redraw
        """
        if self.__clip != None and (self.__clip.width == 0 or self.__clip.height == 0):
            # There is nothing to draw
            return

        if len(dirty_rects) > 0:
            surface_blit = surface.blit

            if self.__clip == None:
                set_clip = surface.set_clip
            else:
                self.__set_clip_surface = surface
                set_clip = self.__set_clip

            if self.__alpha_blit != None:
                alpha_bounds = self.__alpha_bounds
                set_clip(alpha_bounds)
                for dirty_rect in dirty_rects:
                    dirty_rect_clipped = dirty_rect.clip(alpha_bounds)
                    dirty_rect_adj = dirty_rect_clipped.move(-alpha_bounds.left, - alpha_bounds.top)
                    surface_blit(self.__alpha_blit, dirty_rect_clipped, dirty_rect_adj)
            else:
                self.custom_draw.surface = surface
                for dirty_rect in dirty_rects:
                    set_clip(dirty_rect)
                    for item in self.items:
                        # Check if the item intersects with one of the rect that must
                        # be redraw
                        rect = item.rect
                        if not rect.colliderect(dirty_rect) or not item.visible:
                            # It is not necessary to draw the item, continues with
                            # the next item  (this control optimize the drawing performance)
                            continue

                        # Draw the item
                        draw_function = item.draw_function
                        if draw_function == None:
                            # The item is an image, draw the image
                            if item.area == None:
                                surface_blit(item.surface, rect)
                            else:
                                surface_blit(item.surface, rect, item.area)
                        else:
                            # It has a custom drawing function, invoke the function
                            draw_function(item, self.custom_draw)

            self.__set_clip_surface = None

        # Mark that the layaer was drawn
        if not self.__drawn:
            if len(self.items) > 0:
                self.__drawn = True

    def add_dirty_item(self, item):
        """
        Add an item as dirty in the layer to redraw it
        """
        if not item in self.dirty_items:
            self.dirty_items.append(item)
        if self.__changed_handler != None:
            self.__changed_handler(self.stage)

    def get_alpha(self):
        """
        Gets the alpha value associated with the layer. If alpha value is 0 the layer
        is invisible, if it is 255 the layer is visible, and intermediate values
        sets a semi-transparent layer.
        """
        return self.__alpha

    def set_alpha(self, alpha):
        """
        Sets the alpha value associated with the layer.
        - alpha: Alpha value.
        """
        if self.__alpha != alpha:
            self.__alpha = alpha

            if self.__alpha == 255:
                self.__alpha_buffer = None
                self.__alpha_blit = None
            else:
                if self.__alpha_buffer != None:
                    self.__alpha_blit = set_surface_alpha(self.__alpha_buffer, self.__alpha)

            self.set_dirty()

    def get_stage(self):
        """
        Gets the stage of the layer
        """
        return self.stage

    def set_stage(self, stage):
        """
        Sets the stage of the layer
        - stage: Stage where the layer is used.
        """
        if stage == None:
            self.stage = None
            self.__changed_handler = None
        else:
            if self.stage != None:
                raise Exception, "The layer is already part of a stage"
            else:
                self.stage = stage
                self.__changed_handler = stage.get_changed_handler()

    def get_bounds(self):
        """
        Calculate a rectangle that includes all the visible items of the layer.
        """
        layer_bounds = None
        for item in self.items:
            if item.get_visible():
                item_bounds = item.get_bounds()
                if layer_bounds == None:
                    layer_bounds = item_bounds
                else:
                    layer_bounds.union_ip(item_bounds)

        if layer_bounds == None:
            return Rect(0, 0, 0, 0)
        else:
            return layer_bounds

    def set_dirty(self):
        """
        Set all the items of the layer as dirty to draw them again.
        """
        self.dirty_layer = True    

    def get_clip(self):
        """
        Gets the clips rectangle. None if there is no clip rectangle.
        """
        return self.__clip

    def set_clip(self, clip):
        """
        Sets a rectangle to clip the content of the layer. Only the content
        inside the rect is shown for the layer.
        - clip: Clip rect. None to remove the clip rect.
        """
        if len(self.items) == 0 or not self.__drawn:
            # Make sure that the layer is marked as dirty to draw it
            # in the next cycle (if it has items)
            self.dirty_layer = True
        else:
            if self.__clip != clip and self.stage != None:
                window_width, window_height = self.stage.game.get_window_size()

                if clip == None:
                    new_clip = Rect(0, 0, window_width, window_height)
                else:
                    new_clip = clip

                if self.__clip == None:
                    old_clip = Rect(0, 0, window_width, window_height)
                else:
                    old_clip = self.__clip                                                                        

                # Mark only the minimum area of dirty rect
                total_dirty_rect = old_clip.union(new_clip)

                if total_dirty_rect.width != 0 and total_dirty_rect.height != 0:
                    if old_clip.left > total_dirty_rect.left:                        
                        dirty_rect = Rect(total_dirty_rect.left, total_dirty_rect.top, old_clip.left - total_dirty_rect.left, total_dirty_rect.height)
                        self.dirty_rects.append(dirty_rect)
                    elif new_clip.left > total_dirty_rect.left:
                        dirty_rect = Rect(total_dirty_rect.left, total_dirty_rect.top, new_clip.left - total_dirty_rect.left, total_dirty_rect.height)
                        self.dirty_rects.append(dirty_rect)

                    if old_clip.right < total_dirty_rect.right:
                        dirty_rect = Rect(old_clip.right, total_dirty_rect.top, total_dirty_rect.right - old_clip.right, total_dirty_rect.height)
                        self.dirty_rects.append(dirty_rect)
                    elif new_clip.right < total_dirty_rect.right:
                        dirty_rect = Rect(new_clip.right, total_dirty_rect.top, total_dirty_rect.right - new_clip.right, total_dirty_rect.height)
                        self.dirty_rects.append(dirty_rect)

                    if old_clip.top > total_dirty_rect.top:
                        dirty_rect = Rect(old_clip.left, total_dirty_rect.top, old_clip.width, old_clip.top - total_dirty_rect.top)
                        self.dirty_rects.append(dirty_rect)
                    elif new_clip.top > total_dirty_rect.top:
                        dirty_rect = Rect(new_clip.left, total_dirty_rect.top, new_clip.width, new_clip.top - total_dirty_rect.top)
                        self.dirty_rects.append(dirty_rect)

                    if old_clip.bottom < total_dirty_rect.bottom:
                        dirty_rect = Rect(old_clip.left, old_clip.bottom, old_clip.width, total_dirty_rect.bottom - old_clip.bottom)
                        self.dirty_rects.append(dirty_rect)
                    elif new_clip.bottom < total_dirty_rect.bottom:
                        dirty_rect = Rect(new_clip.left, new_clip.bottom, new_clip.width, total_dirty_rect.bottom - new_clip.bottom)
                        self.dirty_rects.append(dirty_rect)

        self.__clip = clip

    def is_inside_clip(self, x, y):
        """
        Determines if the specified coordinates are inside the clip rectangle.
        """
        if self.__clip == None:
            return True
        else:
            return self.__clip.collidepoint(x, y)

    def render_into_surface(self):
        """
        Draw the layer in a surface. Returns the surface and the bounds
        of the surface in screen coordinates (applying the screen factor)
        """
        # Calculate a rectangle that includes all the items
        bounds = self.get_bounds()

        # Draw the items in a surface to calculate the alpha over the surface
        buffer = pygame.Surface(bounds.size, pygame.SRCALPHA, 32)
        surface_blit = buffer.blit
        custom_draw = CustomDrawDelta(buffer, - bounds.left, - bounds.top)
        custom_draw.surface = buffer
        for item in self.items:
            # Draw the item
            draw_function = item.draw_function
            if draw_function == None:
                # The item is an image, draw the image
                if item.area == None:
                    surface_blit(item.surface, item.rect.move(-bounds.left, - bounds.top))
                else:
                    surface_blit(item.surface, item.rect.move(-bounds.left, - bounds.top), item.area)
            else:
                # It has a custom drawing function, invoke the function
                draw_function(item, custom_draw)

        return buffer, bounds

    def __set_clip(self, rect):
        """
        Set the clip in the set_clip_surface using the clip region of the
        layer.
        - rect: Rect to clip.
        """
        if self.__clip != None:
            rect = rect.clip(self.__clip)

        self.__set_clip_surface.set_clip(rect)

    def __add_serveral_rows_item(self, item, definition):
        """
        Adds the specified item in the list of items with several rows.
        - item: Item.
        - definition: Item's definition.
        """
        row, col = item.get_position()
        self.__several_rows_items.append((item, row, row + definition.size[0] - 1, col))

    def __remove_serveral_rows_item(self, item):
        """
        Remove the specified item from the list of items with several rows.
        - item: Item.
        """
        for big_item in self.__several_rows_items:
            if big_item[0] == item:
                self.__several_rows_items.remove(big_item)

    def __update_serveral_rows_item(self, item, definition):
        """
        Update the specified item from the list of items with several rows.
        - item: Item.
        - definition: Definition.
        """
        found = False
        row, col = item.get_position()
        t = (item, row, row + definition.size[0] - 1, col)
        k = 0
        l = len(self.__several_rows_items)
        while k < l:
            if self.__several_rows_items[k][0] == item:
                self.__several_rows_items[k] = t
                found = True
                break
            k += 1
        if not found:
            self.__several_rows_items.append(t)

# Maximum speed
MAX_SPEED = 90

class LayerRace(Layer):
    """
    Layer to implement races (like car races).
    """

    def __init__(self, stage, vehicle):
        """
        Constructor.
        - stage: Stage.
        - vehicle: Vehicle that is used in the race.
        """
        Layer.__init__(self)

        self.__speed = 0.0
        self.__speed_mark = 0.0
        self.__acceleration = 0
        self.__accelerating = False
        self.__distance_traveled = 0
        self.__braking = False

        # Initialize the sound properties
        self.__speed_item = None
        self.__distance_traveled_item = None
        self.__sound_acceleration = None
        self.__sound_deceleration = None
        self.__sound_braked = None
        self.__sound_max_speed = None
        self.__sound_engine_on = None
        self.__engine_channel = sounds.VirtualChannel(stage)

        # Initialize the acceleration constants at zero (they are defined based on the sounds later)
        self.__const_acceleration = 0
        self.__const_normal_deceleration = 0
        self.__const_break_deceleration = 0

        # Add the vehicle that is used during the race in the layer
        self.add(vehicle)

        # Test objects
        self.car = assets.load_image("alien.gif")
        self.car_pos2 = (300, 0)
        self.car_speed2 = 10
        self.images = [assets.load_image("p2s01i005.png"), assets.load_image("p2s01i005_o.png")]
        self.positions1 = [(0, 0), (90, 0), (0, 150), (90, 150), (0, 300)]
        self.image_index1 = 0
        self.positions2 = [(500, 0), (410, 0), (500, 150), (410, 150), (500, 300)]
        self.image_index2 = 0
        self.image_step = 0

    def get_speed(self):
        """
        Gets current speed of the vehicle.
        """
        return self.__speed

    def get_distance_traveled(self):
        """
        Gets current distance traveled.
        """
        return self.__distance_traveled

    def set_engine_sounds(self, acceleration, deceleration, braked, max_speed, engine_on):
        """
        Set the arrays of sounds used to play according with the speed.
        - acceleration: Acceleration from 0 to maximum speed.
        - deceleration: Deceleration sound.
        - braked: Breaked from maximum speed to 0.
        - max_speed: Max speed loop.
        - engine_on: Speed 0 loop (with the engine running).
        """
        self.__sound_acceleration = acceleration
        self.__sound_deceleration = deceleration
        self.__sound_braked = braked
        self.__sound_max_speed = max_speed
        self.__sound_engine_on = engine_on

        # Set the acceleration speed based on sound lengths
        self.__const_acceleration = MAX_SPEED / (float(acceleration.get_length()) * 1000)
        self.__const_normal_deceleration = - MAX_SPEED / (float(deceleration.get_length()) * 1000)
        self.__const_break_deceleration = - MAX_SPEED / (float(braked.get_length()) * 1000)

    def set_speed_item(self, item):
        """
        Set an ItemText to set the speed when it changes.
        - item: Item.
        """
        self.__speed_item = item

    def set_distance_traveled_item(self, item):
        """
        Set an ItemText to set the distance traveled when it changes.
        - item: Item.
        """
        self.__distance_traveled_item = item

    def play_engine_on(self):
        """
        Plays the engine on loop.
        """
        self.__engine_channel.play(self.__sound_engine_on, - 1, 1000, 0)

    def start_accelerate(self):
        """
        Invoke this function when the accelerator is pushed.
        """
        if self.__speed < MAX_SPEED:
            self.__acceleration = self.__const_acceleration
            self.__accelerating = True
            self.__braking = False

            # Calculate a speed when we have to start playing the max speed loop because we are near max speed
            speed_mark = MAX_SPEED - self.__acceleration * 1000
            if self.__speed > speed_mark:
                # We are near maximum speed, play the max speed loop
                self.__engine_channel.play(self.__sound_max_speed, - 1, 500, 0)
                self.__speed_mark = MAX_SPEED
            else:
                # Play the engine accelerating
                offset = float(self.__speed) / MAX_SPEED
                self.__engine_channel.play(self.__sound_acceleration, 0, 500, offset)
                self.__speed_mark = speed_mark


    def stop_accelerate(self):
        """
        Invoke this function when the accelerator is realeased.
        """
        if self.__accelerating:
            self.__acceleration = self.__const_normal_deceleration
            self.__accelerating = False

            # Calculate a speed when we have to start playing the engine on loop because we are near speed 0
            speed_mark = - self.__acceleration * 500
            if self.__speed < speed_mark:
                # We are near speed 0, play the engine on speed loop
                self.__engine_channel.play(self.__sound_engine_on, - 1, 100, 0)
                self.__speed_mark = 0
            else:
                # Play the engine decelerating
                offset = 1 - float(self.__speed) / MAX_SPEED
                self.__engine_channel.play(self.__sound_deceleration, 0, 500, offset)
                self.__speed_mark = speed_mark

    def start_break(self):
        """
        Invoke this function when the accelerator is pushed.
        """
        if self.__speed > 0:
            self.__acceleration = self.__const_break_deceleration
            self.__accelerating = False
            self.__braking = True

            # Calculate a speed when we have to start playing the engine on loop because we are near speed 0
            speed_mark = - self.__acceleration * 100
            if self.__speed < speed_mark:
                # We are near speed 0, play the engine on speed loop
                self.__engine_channel.play(self.__sound_engine_on, - 1, 100, 0)
                self.__speed_mark = 0
            else:
                # Play the engine decelerating
                offset = 1 - float(self.__speed) / MAX_SPEED
                self.__engine_channel.play(self.__sound_braked, 0, 50, offset)
                self.__speed_mark = speed_mark


    def stop_break(self):
        """
        Invoke this function when the accelerator is realeased.
        """
        if self.__braking:
            self.__acceleration = self.__const_normal_deceleration
            self.__braking = False

            # Calculate a speed when we have to start playing the engine on loop because we are near speed 0
            speed_mark = - self.__acceleration * 500
            if self.__speed < speed_mark:
                # We are near speed 0, play the engine on speed loop
                self.__engine_channel.play(self.__sound_engine_on, - 1, 100, 0)
                self.__speed_mark = 0
            else:
                # Play the engine decelerating
                offset = 1 - float(self.__speed) / MAX_SPEED
                self.__engine_channel.play(self.__sound_deceleration, 0, 250, offset)
                self.__speed_mark = speed_mark

    def update(self, dirty_rects, frame_delay):
        """
        Updates the items before draw it in the stage.
        - dirty_rects: List where the parts of the stage that must be updated
              are added.
        - frame_delay: Milliseconds elapsed from the previous frame.
        """

        # Update the speed of the car
        if self.__acceleration > 0:
            self.__speed += self.__acceleration * frame_delay
            if self.__speed >= MAX_SPEED:
                self.__speed = MAX_SPEED
                self.__acceleration = 0

            if self.__speed > self.__speed_mark:
                # We are near maximum speed, play the engine loop at maximum speed with a cross fade
                if self.__acceleration == 0:
                    cross_fade = 0
                else:
                    cross_fade = int((MAX_SPEED - self.__speed) / self.__acceleration)
                self.__engine_channel.play(self.__sound_max_speed, - 1, cross_fade, 0)
                self.__speed_mark = MAX_SPEED
        elif self.__acceleration < 0:
            self.__speed += self.__acceleration * frame_delay
            if self.__speed <= 0:
                self.__speed = 0
                self.__acceleration = 0

            if self.__speed < self.__speed_mark:
                # We are near 0 speed, play the engine on (without acceleration) with a cross fade
                if self.__acceleration == 0:
                    cross_fade = 0
                else:
                    cross_fade = int(self.__speed / - self.__acceleration)
                self.__engine_channel.play(self.__sound_engine_on, - 1, cross_fade, 0)
                self.__speed_mark = 0

        # Set the speed text
        if self.__speed_item != None:
            self.__speed_item.set_text(str(int(self.__speed)))

        # Update the distance traveled
        self.__distance_traveled += self.__speed * (float(frame_delay) / 360)
        if self.__distance_traveled_item != None:
            self.__distance_traveled_item.set_text(str(int(self.__distance_traveled)))

        # Update other items in the layer
        Layer.update(self, dirty_rects, frame_delay)

        # Update test objects
        if self.car_speed2 > 0:
            dirty_rects.append(Rect(self.car_pos2[0], self.car_pos2[1], self.car.get_width(), (self.car.get_height() + self.car_speed2)))
        else:
            dirty_rects.append(Rect(self.car_pos2[0], (self.car_pos2[1] + self.car_speed2), self.car.get_width(), (self.car.get_height() - self.car_speed2)))
        if self.car_speed2 > 0:
            dirty_rects.append(Rect(self.car_pos2[0] - 100, self.car_pos2[1], self.car.get_width(), (self.car.get_height() + self.car_speed2)))
        else:
            dirty_rects.append(Rect(self.car_pos2[0] - 100, (self.car_pos2[1] + self.car_speed2), self.car.get_width(), (self.car.get_height() - self.car_speed2)))
        if self.image_step == 0:
            for pos in self.positions1:
                dirty_rects.append(Rect(pos[0], pos[1], self.images[self.image_index1].get_width(), self.images[self.image_index1].get_height()))
        elif self.image_step == 1:
            for pos in self.positions2:
                dirty_rects.append(Rect(pos[0], pos[1], self.images[self.image_index2].get_width(), self.images[self.image_index2].get_height()))

    def draw(self, surface, dirty_rects):
        """
        Draws the items if the layer.
        - surface: Target surface.
        - dirty_rects: Areas of the stage that must be redraw
        """

        # Draw test objects
        if self.image_step == 0:
            for pos in self.positions1:
                surface.blit(self.images[self.image_index1].surface, (pos[0], pos[1]))
            self.image_index1 += 1
            if self.image_index1 >= len(self.images):
                self.image_index1 = 0
        elif self.image_step == 1:
            for pos in self.positions2:
                surface.blit(self.images[self.image_index2].surface, (pos[0], pos[1]))
            self.image_index2 += 1
            if self.image_index2 >= len(self.images):
                self.image_index2 = 0
        self.image_step += 1
        if self.image_step > 1:
            self.image_step = 0
        self.car_pos2 = (self.car_pos2[0], self.car_pos2[1] + self.car_speed2)
        surface.blit(self.car.surface, (self.car_pos2[0], self.car_pos2[1]))
        surface.blit(self.car.surface, (self.car_pos2[0] - 100, self.car_pos2[1]))
        if self.car_speed2 > 0:
            if self.car_pos2[1] > 300:
                self.car_speed2 = - self.car_speed2
        else:
            if self.car_pos2[1] < 30:
                self.car_speed2 = - self.car_speed2


        # Draw other items in the layer
        Layer.draw(self, surface, dirty_rects)


class LayerBuffered(Layer):
    """
    Represents a layer with a buffer to pre-render the items.
    """

    def __init__(self, width, height, use_alpha=False):
        """
        Constructor
        - width: Width of the layer.
        - height: Height of the layer.
        - use_alpha: Indicates if the buffer is defined with an alpha channel.
        """
        Layer.__init__(self)

        # Create the buffer
        if use_alpha:
            self.__buffer = pygame.Surface((width, height), pygame.SRCALPHA, 32)
        else:
            self.__buffer = pygame.Surface((width, height))

    def update(self, dirty_rects, frame_delay):
        """
        Updates the items before draw it in the stage.
        - dirty_rects: List where the parts of the stage that must be updated
              are added.
        - frame_delay: Milliseconds elapsed from the previous frame.
        """

        # Get a copy of the list of dirty items and rects, and then clear it. In the update
        # we use the lists read so we can set new dirty items (in the lists associated with the layer)
        # to update in the next frame
        dirty_rects_list = self.dirty_rects
        self.dirty_rects = []
        dirty_items_list = self.dirty_items
        self.dirty_items = []

        # Updates the items
        for item in dirty_items_list:
            dirty_rect = item.update(frame_delay)
            if dirty_rect != None:
                dirty_rects_list.append(dirty_rect)

        if len(dirty_rects_list) > 0:
            buffer = self.__buffer

            # Draw the items
            buffer.set_clip(Rect(0, 0, 9999, 9999)) # We use a big rect instead None because the None value doesn't work with Pysco in the X0

            # Clear the dirty areas buffer
            for rect in dirty_rects_list:
                buffer.fill((0, 0, 0, 0), rect)

            # Draw the items
            Layer.draw(self, buffer, dirty_rects_list)

            # Append the dirty rects to the global list
            for rect in dirty_rects_list:
                # If the rect intersects with another, join them
                k = rect.collidelist(dirty_rects)
                while k != - 1:
                    rect.union_ip(dirty_rects[k])
                    del dirty_rects[k]
                    k = rect.collidelist(dirty_rects)

                dirty_rects.append(rect)


    def draw(self, surface, dirty_rects):
        """
        Draws the items if the layer.
        - surface: Target surface.
        - dirty_rects: Areas of the stage that must be redraw
        """
        surface_blit = surface.blit
        buffer = self.__buffer
        surface.set_clip(Rect(0, 0, 9999, 9999)) # We use a big rect instead None because the None value doesn't work with Pysco in the X0
        for dirty_rect in dirty_rects:
            surface_blit(buffer, dirty_rect, dirty_rect)


class CustomDraw:
    """
    Provides the functions to draw over a surface.
    """

    def __init__(self, width=0, height=0):
        """
        Constructor.
        - width: Width of the surface to be created.
        - height: Height of the surface to be created.
        """
        if width == 0:
            self.surface = None
        else:
            self.surface = pygame.Surface((width, height), pygame.SRCALPHA, 32)

    def blit_surface(self, surface, pos, area=None):
        """
        Draws a Surface.
        - surface: Surface to draw.
        - pos: A pair of coordinates representing the position where the stage is drawn.
             A Rect can also be passed as a destination (x,y), the size of the
             rectangle is ignored.
        - area: Represents the portion of the surface to draw.
        """
        if area != None:
            self.surface.blit(surface, pos, area)
        else:
            self.surface.blit(surface, pos)

    def blit_image(self, image, pos, area=None):
        """
        Draws an Image.
        - image: Image to draw.
        - pos: A pair of coordinates representing the position where the stage is drawn.
             A Rect can also be passed as a destination (x,y), the size of the
             rectangle is ignored.
        - area: Represents the portion of the surface to draw.
        """
        if area != None:
            self.surface.blit(image.surface, pos, area)
        else:
            self.surface.blit(image.surface, pos)

    def blit_stage(self, stage, pos, area=None):
        """
        Draw the content of a stage.
        - stage: Stage to draw.
        - pos: A pair of coordinates representing the position where the stage is drawn.
             A Rect can also be passed as a destination (x,y), the size of the
             rectangle is ignored.
        - area: Represents the portion of the stage to draw.
        """
        surface = stage.target_surface
        if surface == None:
            surface = stage.game.window

        if area != None:
            self.surface.blit(surface, pos, area)
        else:
            self.surface.blit(surface, pos)

    def clear(self, color):
        """
        Clear the target surface with the specified color.
        - color
        """
        self.surface.fill(color)

    def fill(self, color, rect):
        """
        Fill a rectangle with a solid color
        - color: Color of the rectangle.
        - rect: Bounds of the rectangle.
        """
        self.surface.fill(color, rect)

    def draw_line(self, color, start_pos, end_pos, width=1):
        """
        Draws a line from 'start_pos' to 'end_pos'.
        - color: Color of the line.
        - start_pos: Position where the line starts.
        - end_pos: Position where the line ends.
        - width: Width of the line.
        """
        pygame.draw.line(self.surface, color, start_pos, \
                         end_pos, \
                         width)

    def draw_rect(self, color, rect, width=1):
        """
        Draw a rectangle.
        - color: Color of the rectangle.
        - rect: Bounds of the rectangle.
        - width: Width of the border.
        """
        pygame.draw.rect(self.surface, color, rect, width)


class CustomDrawDelta:
    """
    Provides the functions to draw over a surface with a displacement.
    """

    def __init__(self, surface, dx, dy):
        """
        Constructor.
        - surface: Target surface.
        - dx: Value that is added to the coordinates in the X axis.
        - dy: Value that is added to the coordinates in the Y axis.
        """
        self.surface = surface
        self.dx = dx
        self.dy = dy

    def blit_surface(self, surface, pos, area=None):
        """
        Draws a Surface.
        - surface: Surface to draw.
        - pos: A pair of coordinates representing the position where the stage is drawn.
             A Rect can also be passed as a destination (x,y), the size of the
             rectangle is ignored.
        - area: Represents the portion of the surface to draw.
        """
        if area != None:
            self.surface.blit(surface, pos, area)
        else:
            self.surface.blit(surface, pos)

    def blit_image(self, image, pos, area=None):
        """
        Draws an Image.
        - image: Image to draw.
        - pos: A pair of coordinates representing the position where the stage is drawn.
             A Rect can also be passed as a destination (x,y), the size of the
             rectangle is ignored.
        - area: Represents the portion of the surface to draw.
        """
        if area != None:
            self.surface.blit(image.surface, pos, area)
        else:
            self.surface.blit(image.surface, pos)

    def blit_stage(self, stage, pos, area=None):
        """
        Draw the content of a stage.
        - stage: Stage to draw.
        - pos: A pair of coordinates representing the position where the stage is drawn.
             A Rect can also be passed as a destination (x,y), the size of the
             rectangle is ignored.
        - area: Represents the portion of the stage to draw.
        """
        surface = stage.target_surface
        if surface == None:
            surface = stage.game.window

        if area != None:
            self.surface.blit(surface, pos, area)
        else:
            self.surface.blit(surface, pos)

    def clear(self, color):
        """
        Clear the target surface with the specified color.
        - color
        """
        self.surface.fill(color)

    def fill(self, color, rect):
        """
        Fill a rectangle with a solid color
        - color: Color of the rectangle.
        - rect: Bounds of the rectangle.
        """
        self.surface.fill(color, rect)

    def draw_line(self, color, start_pos, end_pos, width=1):
        """
        Draws a line from 'start_pos' to 'end_pos'.
        - color: Color of the line.
        - start_pos: Position where the line starts.
        - end_pos: Position where the line ends.
        - width: Width of the line.
        """
        pygame.draw.line(self.surface, color, (start_pos[0] + self.dx, start_pos[1] + self.dy), \
                         (end_pos[0] + self.dx, end_pos[1] + self.dy), \
                         width)

    def draw_rect(self, color, rect, width=1):
        """
        Draw a rectangle.
        - color: Color of the rectangle.
        - rect: Bounds of the rectangle.
        - width: Width of the border.
        """
        rect = Rect(rect[0] + self.dx,
                rect[1] + self.dy,
                rect[2],
                rect[3])
        pygame.draw.rect(self.surface, color, rect, width)
