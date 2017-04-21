# -*- coding: latin-1 -*-

# 2011 - Dirección General Impositiva, Uruguay.
# Todos los derechos reservados.
# All rights reserved.

import pygame

class VirtualChannel():
    """    
    When we play a sound over this channel automatically find a non busy channel to play the sound, if 
    we already are playing a sound in the channel it stop it before play the new sound.
    """    
    def __init__(self, stage):
        self.__curr_channel = None
        self.__prev_channel = None
        self.__cross_fade = 0        
        self.__stage = stage
        
    def play(self, sound, loops, cross_fade = 0, offset = 0):
        """    
        Plays a sound in the channel.
        - sound: Sound to play.
        - loops: Loops (-1 to loop indefinitely)
        - cross_fade: Fade to mix the current sound and the new sound (in ms). If there is no current sound
          a fade in is performed only with the new sound, in there is a current sound a fade out
          is performed over it, and a fade in with the new sound. 
        - offset: Offset from where the sound is played (must be a percentage expressed with a number 
          between 0 and 1).
        """                        
        if offset == 0:
            sound_to_play = sound
        else:
            sample = pygame.sndarray.samples(sound)        
            sound_to_play = pygame.sndarray.make_sound(sample[int(len(sample) * float(offset)):])
        
        if cross_fade <= 0:
            if self.__cross_fade != 0:
                # Stop current sound
                if self.__prev_channel != None:
                    self.__prev_channel.stop()
                    self.__prev_channel = None
                
                # Stop the cross fade            
                self.__stage.stop_timer(self)
                self.__cross_fade = 0
                            
            # Play new sound
            if self.__curr_channel != None:
                self.__curr_channel.stop()                
            sound_len = sound_to_play.get_length()
            if sound_len == 0:            
                self.__curr_channel = None
            else:        
                self.__curr_channel = sound_to_play.play(loops)                        
        else:            
            # We must perform a cross-fade
            if self.__prev_channel != None:
                self.__prev_channel.stop()
            self.__prev_channel = self.__curr_channel
            self.__cross_fade = 50 / float(cross_fade)
            
            # Play the sound in a new channel and set its volume to 0, so we can perform the cross fade
            sound_len = sound_to_play.get_length()
            if sound_len == 0:
                self.__curr_channel = None
            else:                    
                self.__curr_channel = sound_to_play.play(loops)
                if self.__curr_channel != None:
                    self.__curr_channel.set_volume(0)                        
                                                                          
            # Start a timer to perform the cross fade
            if not self.__stage.is_timer_started(self):     
                self.__stage.start_timer(self, min(cross_fade, 50), self.__cross_fade_tick)
    
    def __cross_fade_tick(self, key, data):
        """
        Adjust the volume in channels affected with the cross-fade.
        """
        if self.__prev_channel == None:
            old_volume = 0
        else:    
            old_volume = self.__prev_channel.get_volume() - self.__cross_fade
            if old_volume <= 0:
                old_volume = 0                
                self.__prev_channel.stop()
                self.__prev_channel = None
            else:
                self.__prev_channel.set_volume(old_volume)
        if self.__curr_channel == None:
            new_volume = 1
        else:        
            new_volume = self.__curr_channel.get_volume() + self.__cross_fade         
            if new_volume > 1:
                new_volume = 1                
            self.__curr_channel.set_volume(new_volume)                                    
                
        if old_volume == 0 and new_volume == 1:            
            self.__stage.stop_timer(key)
            self.__cross_fade = 0        
        
        