# -*- coding: latin-1 -*-

# 2011 - Dirección General Impositiva, Uruguay.
# Todos los derechos reservados.
# All rights reserved.


from pygame import KEYDOWN, KEYUP, K_LEFT, K_RIGHT, Rect
from framework.engine import SCREEN_HEIGHT, SCREEN_WIDTH
from framework.stage import assets, ItemEvent, ItemImage, ItemRect, ItemText, Layer, Stage
from framework.animations import fade_out_item
import random
from utils import DictClass
from yaml import load
from character import Character
from framework.engine import SCREEN_WIDTH
from gameintro import Intro
from game.stages.gamestage import GameStage
from pygame import Color

def w_choice(lst):
    n = random.uniform(0, 1)
    for item, weight in lst:
        if n < weight:
            break
        n = n - weight
    return item

DEBUG = False

class Invader():
    def __init__(self, left, top, min, max, velocity, good, src, points, collision):
        self.left = left
        self.top = top
        self.min = min
        self.max = max
        self.velocity = velocity
        self.good = good
        image = assets.load_image(src)
        self.item = ItemImage(0, 0, image)
        self.points = points
        self.collision = collision
        if max:
            self.delta = random.choice([-1, 1])
            self.delta = random.choice([-1.5, -1, 1, 1.5])
        else:
            self.delta = 0
        if DEBUG:
            self.debug_item = ItemRect(self.get_left(), self.get_top(), self.get_width(), self.get_height(), border = (255, 255, 255))
    
    def set_left(self, left):
        self.min -= left / 2
        self.max += left / 2
        self.item.set_left(left)
        if DEBUG:
            self.debug_item.set_left(left + self.collision.left)
    
    def exit(self):
        self.item.exit()
        self.item = None
        self.collision = None
    
    def get_left(self):
        return self.item.get_left() + self.collision.left
    
    def get_top(self):
        return self.item.get_top() + self.collision.top
    
    def get_width(self):
        return self.item.get_width() - self.collision.left - self.collision.right
    
    def get_height(self):
        return self.item.get_height() - self.collision.top - self.collision.bottom
    
    def move(self, time, velocity):
        if self.delta:
            left = self.item.get_left()
            if left + self.delta > self.max or left + self.delta + self.item.get_width() > SCREEN_WIDTH:
                self.delta = -1
                self.delta = random.choice([-1.5, -1])
            elif left + self.delta < self.min or left + self.delta < 0:
                self.delta = 1
                self.delta = random.choice([1, 1.5])
            left += self.delta * time * velocity * self.velocity
            self.item.set_left(left)
            if DEBUG:
                self.debug_item.set_left(left + self.collision.left)
        top = self.item.get_top() + time * velocity * self.velocity
        self.item.set_top(top)
        if DEBUG:
            self.debug_item.set_top(top + self.collision.top)
        
class InvadersMinigame(GameStage):
    MOVE_INTERVAL = 30
    GOOD_INDICATOR_INTERVAL = 1000
    DIFFICULTY_INTERVAL = 10000
    GO_BACK_TIME = 3000
    
    def __init__(self, game):
        GameStage.__init__(self, game, Color('#333333'))
    
    def initialize(self):
        GameStage.initialize(self)
        stream = file('data/fonts.yaml', 'r')
        
        fonts = load(stream)
        for font in fonts:
            setattr(self, font, assets.load_font(fonts[font]['file_name'], fonts[font]['size']))
                    
        self.data = DictClass(load(file('data/invaders.yaml')))
        
        self.good = self.data.start.good
        self.velocity = self.data.start.velocity
        self.interval = self.data.start.interval
        
        self.game_over_layer = Layer()
        image = assets.load_image(self.data.bad[self.game.datastore.datamodel.character].src)
        item = ItemImage(self.data.bad.left, self.data.bad.top, image)
        self.game_over_layer.add(item)
        image = assets.load_image(self.data.game_over[self.game.datastore.datamodel.character].src)
        item = ItemImage(self.data.game_over.left, self.data.game_over.top, image)
        self.game_over_layer.add(item)
        
        image = assets.load_image(self.data.good[self.game.datastore.datamodel.character].src)
        self.good_indicator = ItemImage(self.data.good.left, self.data.good.top, image)
        
        self.text_indicators = []
        
        self.main_layer = Layer()
        self.top_layer = Layer()
        
        self.score = 0
        self.score_board = DictClass({})
        image = assets.load_image(self.data.score.src)
        self.score_board['skin'] = ItemImage(self.data.score.left, self.data.score.top, image)
        self.score_board['value'] = ItemText(self.data.score.left, self.data.score.top, self.font, 0, str(self.score), width = image.get_width(), height = image.get_height(), h_align = 2, v_align = 2)
        self.top_layer.add(self.score_board.skin)
        self.top_layer.add(self.score_board.value)
        
        data = DictClass(load(file('data/map/common.yaml')))
        params = data.character[self.game.datastore.datamodel.character]
        params['base'] = data.character.base[self.game.datastore.datamodel.character].big
        self.character_animation = Character(**params)
        self.character = self.character_animation.item
        self.character.set_left((SCREEN_WIDTH - self.character.get_width()) / 2)
        self.character.set_top(SCREEN_HEIGHT - self.character.get_height())
        left = self.character.get_left() + self.data.collision.left
        top = self.character.get_top() + self.data.collision.top
        width = self.character.get_width() - self.data.collision.left - self.data.collision.right
        height = self.character.get_height() - self.data.collision.top - self.data.collision.bottom
        if DEBUG:
            self.debug_character = ItemRect(left, top, width, height, border = (255, 255, 255))
        self.invaders = []

        
        # Load the sound
        self.item_found_sound = assets.load_sound('DGI_item_found.ogg')
        self.lose_hit_sound = assets.load_sound('DGI_lose_hit.ogg')
        self.lose_music_sound = assets.load_sound('DGI_lose_music.ogg')

    def increase_difficulty(self, key, data):
        if self.good + self.data.step.good >= self.data.min.good:
            self.good += self.data.step.good
        if  self.velocity + self.data.step.velocity <= self.data.max.velocity:
            self.velocity += self.data.step.velocity
        if  self.interval + self.data.step.interval >= self.data.min.interval:
            self.interval += self.data.step.interval
            self.stop_timer(1)
            self.start_timer(1, self.interval, self.create_invader)
        
    def create_invader(self, key, data):
        lst = [(True, self.good), (False, 1 - self.good)]
        good = w_choice(lst)
        if good:
            index = random.randint(0, len(self.data.invaders.good) - 1)
            invader = self.data.invaders.good[index]
        else:
            index = random.randint(0, len(self.data.invaders.bad) - 1)
            invader = self.data.invaders.bad[index]
        src = invader.src
        points = invader.points
        collision = invader.collision
        min = invader.min
        max = invader.max
        velocity = invader.velocity
        invader = Invader(0, 0, min, max, velocity, good, src, points, collision)
        left = random.randint(0, SCREEN_WIDTH - invader.item.get_image().get_width())
        invader.set_left(left)
        top = -invader.item.get_image().get_height()
        invader.item.set_top(top)
        self.invaders.append(invader)
        
        self.main_layer.add(invader.item)
        if DEBUG:
            self.main_layer.add(invader.debug_item)
    
    def move_invaders(self, key, data):
        for item in self.text_indicators:
            item.set_top(item.get_top() - 2)
            
        for invader in self.invaders:
            invader.move(self.MOVE_INTERVAL, self.velocity)
            if (invader.item.get_top() > SCREEN_HEIGHT):
                self.remove_invader(invader)
            else:
                left = self.character.get_left() + self.data.collision.left
                top = self.character.get_top() + self.data.collision.top
                width = self.character.get_width() - self.data.collision.left - self.data.collision.right
                height = self.character.get_height() - self.data.collision.top - self.data.collision.bottom
                character = Rect(left, top, width, height)
                item = Rect(invader.get_left(), invader.get_top(), invader.get_width(), invader.get_height())
                k = character.collidelist([item])
                if k != -1:
                    if invader.good:
                        self.character_animation.footsteps_concrete_sound.stop()
                        self.item_found_sound.play()
                        self.character_animation.first_walking = True
                        
                        self.score += invader.points
                        self.score_board.value.set_text(str(self.score))
                        self.top_layer.add(self.good_indicator)
                        item = ItemText(invader.get_left(), invader.get_top(), self.font, 0, "+" + str(invader.points), h_align = 2, v_align = 2)
                        self.text_indicators.append(item)
                        self.top_layer.add(item)
                        fade_out_item(item, True, self.GOOD_INDICATOR_INTERVAL)
                        self.start_timer(3, self.GOOD_INDICATOR_INTERVAL, self.remove_good_indicator)
                    else:
                        self.stop_timer(1)
                        self.stop_timer(2)
                        self.game_over()
                        return
                    self.remove_invader(invader)
    
    def remove_invader(self, invader):
        self.invaders.remove(invader)
        self.main_layer.remove(invader.item)
        invader.exit()
        if DEBUG:
            self.main_layer.remove(invader.debug_item)
    
    def remove_good_indicator(self, key, data):
        self.stop_timer(3)
        self.top_layer.remove(self.good_indicator)
    
    def prepare(self):
        self.show_board()
        self.key = None
        dialog = Intro(self, self.data.intro, self.start_game)
        dialog.start()
    
    def start_game(self):
        self.start_timer(1, self.interval, self.create_invader)
        self.start_timer(2, self.MOVE_INTERVAL, self.move_invaders)
        self.start_timer(4, self.DIFFICULTY_INTERVAL, self.increase_difficulty)
        self.start_timer(0, 30, self.manage_key)
        
    def show_board(self):
        self.main_layer.add(self.character)
        if DEBUG:
            self.main_layer.add(self.debug_character)
        self.add_layer(self.main_layer)
        self.add_layer(self.top_layer)
    
    def handle_event(self, e):
        if e.type == KEYDOWN:
            self.key = e.key
        if  e.type == KEYUP:
            self.key = None
            
    def manage_key(self, key, data):
        delta = 0
        if self.key == K_LEFT:
            delta = -8
        if self.key == K_RIGHT:
            delta = 8
        left = self.character.get_left() + delta
        if 0 <= left and left <= SCREEN_WIDTH - self.character.get_width():
            self.character.set_left(left)
            if DEBUG:
                self.debug_character.set_left(left + self.data.collision.left)
            self.character_animation.update(self.MOVE_INTERVAL, delta_left = delta)
            
    def game_over(self):
        self.good_indicator.set_visible(False)
        self.character_animation.footsteps_concrete_sound.stop()
        self.lose_hit_sound.play()
        self.lose_music_sound.play()
        
        self.stop_timer(0)
        self.stop_timer(1)
        self.stop_timer(2)
        self.stop_timer(3)
        self.stop_timer(4)
        self.top_layer.remove(self.good_indicator)
        self.add_layer(self.game_over_layer)
        self.start_timer("go_back_timer", self.GO_BACK_TIME, self.go_back)
    
    def exit(self, other_stage):
        GameStage.exit(self, other_stage)
        self.good_indicator.exit()
        self.good_indicator = None
        self.character_animation.exit()
        self.character_animation = None
        for invader in self.invaders:
            invader.exit()
        self.invaders = None
    
    def go_back(self, *args, **kwargs):
        from game.stages.map import Map
        self.game.set_stage(Map(self.game))