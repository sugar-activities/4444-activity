# -*- coding: latin-1 -*-

# 2011 - Dirección General Impositiva, Uruguay.
# Todos los derechos reservados.
# All rights reserved.

import pygame
import os
import engine
import stage
import assets
import animations
import gc
import platform
from pygame.locals import *
from framework.stage import Layer, ItemImage
import web

# Factor used to scale the images in the screen. If we are in the XO it is adjusted
# automatically to cover all the screen
SCREEN_FACTOR = 1 

SCREEN_WIDTH = 600
SCREEN_HEIGHT = 450

class Game:
    """    
    Allows to run the game using the framework
    """
        
    def __init__(self, title, default_mouse_cursor = None, loading_image = None):
        """        
        Constructor
        - title: Game's title.    
        - default_mouse_cursor: Mouse's default cursor.
        - loading_image: Name of the image used in the loading screen.
        """
        
        # Initialize psyco to improve speed
        try:
            import psyco
            psyco.full()
        except Exception, message:       
           print 'Psyco couldn''t be used to improve speed:', message           
        
        # Initialize pygame
        pygame.mixer.pre_init(22050, 0, 0, 1024)                    
        pygame.init()
        
        
        # Adjust the SCREEN_FACTOR with the smallest mode
        modes = pygame.display.list_modes()
        if modes != -1 and len(modes) > 0:
            last_mode = modes[len(modes) - 1]            
            engine.SCREEN_FACTOR = max(1, int(last_mode[0] / 600))
                
        # Create the game window
        pygame.display.init()
        self.display = pygame.display.set_mode((int(engine.SCREEN_WIDTH * engine.SCREEN_FACTOR), 
                                               int(engine.SCREEN_HEIGHT * engine.SCREEN_FACTOR)),
                                               #pygame.FULLSCREEN | pygame.HWSURFACE
                                              )   
        #self.display = pygame.display.set_mode((640, 480),
        #                                       pygame.FULLSCREEN  | pygame.HWSURFACE
        #                                      )   
        
        
        # Create a buffer to draw in it before update the window. This buffer
        # is used to scale the image using the SCREEN_FACTOR before drawing it
        # in the screen 
        self.window = pygame.Surface((600, 450), 0, self.display)
        
        if platform.system() == 'Windows':
            self.__set_icon("icon.gif")
        
        #self.window = self.display
        
        self.window_rect = self.window.get_rect()   
                
        # Set title
        pygame.display.set_caption(title)
                           
        # Set initial state        
        self.__stage = None        
        self.__design_stage = None
        self.__default_mouse_cursor = default_mouse_cursor
        self.__loading_image = loading_image
        self.loading_layer = None
        self.__show_fps = False
        self.__clock = pygame.time.Clock()
        self.__frame_delay = 0    
        self.__fps_max_width = 0
        self.__quit_game = 0        
        self.__font = assets.load_font('freesansbold.ttf', 13)
        self.__dimmed_background = None
        self.__development_mode = False                
        
        # Load default mouse cursor image
        if default_mouse_cursor == None:
            self.__default_mouse_cursor = None
        else:            
            self.__default_mouse_cursor = assets.load_image(default_mouse_cursor)        
    
        
    def run(self, initial_stage):
        """        
        Runs the game.
        - initial_stage: Stage that is shown when the game starts.
        """
    
        self.set_stage(initial_stage)
                
        # Main loop
        while not self.__quit_game:
            # Make sure game doesn't run at more than 40 frames per second. This
            # avoid that the use of CPU goes up to 100%
            self.__frame_delay = self.__clock.tick(40)
                        
            # Do operations per tick                
            self.__stage.notify_tick()
            
            # execute web events
            callback = web.get_callback()
            while callback:
                callback()
                callback = web.get_callback()
                                                
    def quit(self):
        """        
        Ends the execution of the game
        """
        # Invoke close handler
        if self.__stage != None:
            closed_handler = self.__stage.get_closed_handler()
            if closed_handler != None:
                closed_handler(self.__stage)    
        
        # Stops the main loop
        self.__quit_game = 1        
            
    def get_show_fps(self):
        """        
        Gets a value that indicates if the FPS is visible
        """
        return self.__show_fps
                
    def set_show_fps(self, value):
        """        
        Sets a value that indicates if the FPS is visible
        """        
        self.__show_fps = value
        self.__stage.redraw()        
        
    def get_default_mouse_cursor(self):
        """        
        Gets the default mouse cursor image
        """
        return self.__default_mouse_cursor
        
    def get_design_stage(self):
        """
        Gets the design stage. None if there is no design stage.                
        """
        return self.__design_stage
        
    def set_design_stage(self, design_stage):
        """
        Sets the design stage.
        - design_stage: Stage that is shown.
        
        The design stage is shown when F10 is pressed.
        """
        self.__design_stage = design_stage
    
    def __set_icon(self, iconname):        
        icon = pygame.Surface((32,32))
        icon.set_colorkey((255,0,255))
        rawicon=pygame.image.load(iconname)
        for i in range(0,32):
            for j in range(0,32):
                icon.set_at((i,j), rawicon.get_at((i,j)))
        pygame.display.set_icon(icon)
    
    def get_development_mode(self):
        """
        Gets a value that indicates if the development mode is enabled. See 
        set_development_mode for more information.
        - development_mode: True to enable the development mode, otherwise False.
        """
        return self.__development_mode
        
    def set_development_mode(self, development_mode):
        """
        Sets if the development mode is enabled. This mode is intended to
        use in development to enable shortcuts to access to the different
        parts of the game.
        - development_mode: True to enable the development mode, otherwise False.
        """
        self.__development_mode = development_mode
        
    def set_stage(self, stage, show_loading = False):
        """
        Sets the current stage.
        - stage: Stage that is assigned as the current stage.
        - show_loading: Indicate if must show the loading screen.
        """        
        # Set a dummy stage as the current stage to change the stage in 
        # the next tick. This avoids reference to current stage from the
        # function that invoke 'set_stage' that cannot allow to release all
        # the memory of the previous stage. With this approach when the
        # stage is changed generally only ChangeStageDummy has references
        # to the previous stage and can release it from the memory 
        next_stage = _ChangeStageDummy(self, self.__stage, stage)
        
        if not show_loading:
            self.__stage = next_stage
        else:
            self.__next_stage = next_stage
            self.show_loading(self.__set_next_stage)
        
    def show_loading(self, callback):
        """
        Shows a loading message while loading data in the current stage or
        a new stage is loaded.
        - callback: Function that is invoked after show the loading screen
          with the loading layer as argument.
        """
        if self.loading_layer != None:
            stage = self.loading_layer.get_stage()
            if stage != None:                
                stage.remove_layer(self.loading_layer)                
        self.loading_layer = Layer()
        image = assets.load_image(self.__loading_image)
        item = ItemImage(0, 0, image)
        self.loading_layer.add(item)        
        self.loading_layer.stage = self.__stage
        self.__stage.redraw_mouse()
                
        animations.blind_layer(self.loading_layer, animations.BlindDirection.SHOW_DOWN, None, 450, callback)        
    
    def hide_loading(self, callback = None):
        """
        Hides the loading message.
        - callback: Function that is invoked after hide the loading screen
          with the loading layer as argument. None if there is no callback function.
        """
        if self.loading_layer != None:
            self.__hide_loading_callback = callback            
            animations.blind_layer(self.loading_layer, animations.BlindDirection.HIDE_UP, None, 450, self.__blind_hide_loading_callback)

    def get_window_size(self):
        """
        Gets the window size.
        """
        return self.window.get_size()
      
    def draw_fps(self, dirty_rects):
        """        
        Draw the FPS in the screen
        - dirty_rects: List where the rect that must be redrawn is appended
        """
            
        # Render the text
        text = self.__font.render("FPS: " + str(round(self.__clock.get_fps(), 2)), True, (0, 0, 0))
        
        # Show the text in the screen
        text_rect = text.get_rect()
        text_rect.topleft = (4, 2)
        if text_rect[2] + 10 > self.__fps_max_width:
            self.__fps_max_width = text_rect[2] + 10
        border_rect = Rect(0, 0, self.__fps_max_width, text_rect.height + 4)
        self.window.set_clip(border_rect)        
        pygame.draw.rect(self.window, (250, 250, 250), border_rect)                
        pygame.draw.rect(self.window, (20, 20, 20), border_rect, 1)
        self.window.blit(text, text_rect)  
        dirty_rects.append(border_rect)
        
    def get_frame_delay(self):
        """        
        Gets the time elapsed from the previous frame.
        """
        return self.__frame_delay
    
    def update_display(self, dirty_rects):
        """
        Update the specified areas in the screen from the window buffer.
        - dirty_rects: List of the rects that must be updated.
        """
        # pygame.display.update(dirty_rects)
        # return
        if SCREEN_FACTOR == 2:            
            dirty_rects2 = []
            for r in dirty_rects:
                r = self.window_rect.clip(r)
                r2 = [x * 2 for x in r]                
                s2 = pygame.transform.scale2x(self.window.subsurface(r))
                self.display.blit(s2, r2)
                dirty_rects2.append(r2)
            pygame.display.update(dirty_rects2)
        elif SCREEN_FACTOR == 1:
            self.display.blit(self.window, (0, 0))
            pygame.display.update(dirty_rects)
        else:
            dirty_rects2 = []
            for r in dirty_rects:
                r = self.window_rect.clip(r)
                r2 = [x * SCREEN_FACTOR for x in r]                
                s2 = pygame.transform.scale(self.window.subsurface(r), r2[2:4])
                self.display.blit(s2, r2)
                dirty_rects2.append(r2)
            pygame.display.update(dirty_rects2)
            
    def __set_next_stage(self, layer):
        """
        Sets the next stage as the current stage.
        - layer: Layer of the loading screen.
        """
        self.__stage = self.__next_stage
        self.__next_stage = None

    def __blind_hide_loading_callback(self, layer):
        """
        This function is invoked after hide the loading screen.
        - layer: Layer.
        """        
        # Render the stage before remove the loading layer
        self.__stage.render()
        self.__stage.redraw_mouse()
        
        self.loading_layer = None
        
        callback = self.__hide_loading_callback
        self.__hide_loading_callback = None
        
        if callback != None:         
            callback(layer)        
        
class _ChangeStageDummy:
    """
    This class simulate an stage to perform stage changes.
    """     

    def __init__(self, game, old_stage, new_stage):
        """
        Constructor.
        """
        self.__game = game
        self.__old_stage = old_stage
        self.__new_stage = new_stage
        
    def notify_tick(self):
        """
        This function is invoked when a new clock cycle starts, and
        changes the current stage in the game.
        """        
        old_stage = self.__old_stage        
        self.__game._Game__stage = self.__new_stage   
                
        if old_stage != None:
            # Remove the focus
            old_stage.set_focus(None)
        
            # Invoke close handler
            closed_handler = old_stage.get_closed_handler()
            if closed_handler != None:
                closed_handler(old_stage)
                del closed_handler
        
        # Configure the key repeat for the stage
        key_repeat = self.__new_stage.get_key_repeat()
        if key_repeat == None:
            pygame.key.set_repeat()
        else:
            pygame.key.set_repeat(key_repeat[0], key_repeat[1])
        
        # Ensure that the mouse is not captured
        pygame.event.set_grab(False)         
        
        # Stop the music of the old stage if it is playing, and start the music 
        # associated with the new stage
        if old_stage != None:
            old_stage.stop_music()
            old_stage.stop_sounds()            
        
        # Remove the reference to the loading screen
        if self.__game.loading_layer != None:
            self.__game.loading_layer.stage = None
        
        # Run the garbage collector to release unreferenced objects. This code was added to avoid 
        # memory problems in the XO, because the garbage collector doesn't run as often as it should
        # and the application could run out of memory        
        del old_stage
        del self.__old_stage
        gc.collect()        
        
        # Initialize the stage if it was not initialized
        if not self.__new_stage.initialized:
            self.__new_stage.initialize()
            self.__new_stage.initialized = True

        # Add the reference to the loading screen
        if self.__game.loading_layer != None:
            self.__game.loading_layer.stage = self.__new_stage
                    
        self.__new_stage.play_music()        
        self.__new_stage.redraw()
        
        # Prepare the stage before show it        
        self.__new_stage.prepare()
        
        # Hide the loading screen
        if self.__game.loading_layer != None:
            self.__game.hide_loading()
        