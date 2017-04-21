# -*- coding: latin-1 -*-

# 2011 - Dirección General Impositiva, Uruguay.
# Todos los derechos reservados.
# All rights reserved.

from framework import assets
from framework.stage import ItemImage
from math import floor
from utils import DictClass

class Animation():
    def __init__(self, frames):
        self.frames = frames
        self.current_time = 0
        self.current_item = 0
        self.to = frames[-1].to
    
    def update(self, interval):
        current_time = self.current_time
        current_time += interval
        current_item = self.current_item
        to = self.to
        if (current_time > self.to):
            factor = current_time/to
            current_time =  (factor - floor(factor))*to
            current_item = 0
        while self.frames[current_item].to < current_time:
            current_item += 1
        self.current_item = current_item
        self.current_time = current_time

    def reset(self):
        self.current_item = 0
        self.current_time = 0

    def get_image(self):
        return self.frames[self.current_item].image
    
    def exit(self):
        for frame in self.frames:
            frame.exit()
        self.frames = None

class Frame():
    def __init__(self, image, to):
        self.image = image
        self.to = to
    
    def exit(self):
        self.image = None
        
def load_animation(base, animation):
    total_time = 0
    frames = []
    for frame in animation:
        total_time += frame.duration*1000
        frames.append(Frame(assets.load_image(base + frame.src), total_time))
    return frames

class Character():
    class Frame():
        def __init__(self, image, to):
            self.image = image
            self.to = to

        def exit(self):
            self.image = None

    def load_animation(self, base, animation):
        total_time = 0
        frames = []
        for frame in animation:
            total_time += frame.duration*1000
            frames.append(self.Frame(assets.load_image(base + frame.src), total_time))
        return frames

    def __init__(self, left = 0, top = 0, base = None, standing = None, walking = None, jumping = None):
        self.first_jumping = True
        self.first_walking = True
            
        # Load the sound
        self.footsteps_concrete_sound = assets.load_sound('DGI_footsteps_concrete.ogg')
        self.jump_sound = assets.load_sound('DGI_jump.ogg')
        
        self.standing_still = assets.load_image(base + standing.src)
        if "wait" in standing:
            self.standing_wait = Animation(self.load_animation(base, [DictClass({'src': standing.src, 'duration': standing.duration})] + standing.wait))
        if jumping:
            self.jumping = assets.load_image(base + jumping.src)
        if walking:
            if "sideways" in walking:
                sideways = self.load_animation(base, walking.sideways)
                self.walking_sideways_left = Animation(sideways)
                self.walking_sideways_right = Animation([self.Frame(frame.image.flip_h_copy(), frame.to) for frame in sideways])
            if "front" in walking:
                self.walking_front = Animation(self.load_animation(base, walking.front))
            if "back" in walking:
                self.walking_back = Animation(self.load_animation(base, walking.back))
        self.item = ItemImage(left, top, self.standing_still)
    
    def exit(self):
        self.item.exit()
        self.standing_wait.exit()
        self.juming = None
        self.jump_sound = None
        self.footsteps_concrete_sound = None
        self.walking_sideways_left.exit()
        self.walking_sideways_left = None
        self.walking_sideways_right.exit()
        self.walking_sideways_right = None        
        self.walking_front.exit()
        self.walking_front = None
        self.walking_back.exit()
        self.walking_back = None        
    
    def update(self, delta_time, delta_left = 0, delta_top = 0, jumping = False):
        if delta_left == 0 and delta_top == 0:
            self.first_jumping = True
            self.first_walking = True
            
            self.footsteps_concrete_sound.stop()
            self.standing_wait.update(delta_time)
            self.item.set_image(self.standing_wait.get_image())
        else:
            self.standing_wait.reset()
            if jumping:
                self.first_walking = True
                if self.first_jumping:
                    self.footsteps_concrete_sound.stop()
                    self.jump_sound.play()
                    self.first_jumping = False
                self.item.set_image(self.jumping)
            else:
                self.first_jumping = True
                if self.first_walking:
                    self.footsteps_concrete_sound.play(-1)
                    self.first_walking = False
                if delta_left < 0:
                    self.walking_sideways_right.update(delta_time)
                    self.item.set_image(self.walking_sideways_right.get_image())
                    return
                if delta_left > 0:
                    self.walking_sideways_left.update(delta_time)
                    self.item.set_image(self.walking_sideways_left.get_image())
                    return
                if delta_top < 0:
                    self.walking_back.update(delta_time)
                    self.item.set_image(self.walking_back.get_image())
                    return
                self.walking_front.update(delta_time)
                self.item.set_image(self.walking_front.get_image())