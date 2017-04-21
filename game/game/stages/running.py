# -*- coding: latin-1 -*-

# 2011 - Dirección General Impositiva, Uruguay.
# Todos los derechos reservados.
# All rights reserved.


from pygame import KEYDOWN, KEYUP, K_UP, Rect
from framework.engine import SCREEN_HEIGHT, SCREEN_WIDTH
from framework.stage import assets, ItemEvent, ItemImage, ItemRect, ItemText, Layer, Stage
import random
from utils import DictClass
from yaml import load
from character import Character
from framework.animations import fade_out_item
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
    def __init__(self, good, src, left, right, top, points):
        self.good = good
        self.left = left
        self.right = right
        self.points = points
        self.top = top
        image = assets.load_image(src)
        item = self.item = ItemImage(0, 0, image)
        if DEBUG:
            self.debug_item = ItemRect(item.get_left() + left, item.get_top() + top, item.get_width() - left - right, 
                item.get_height() - top, border = (255, 255, 255))
    def set_left(self, left):
        self.item.set_left(left)
        if DEBUG:
            self.debug_item.set_left(left + self.left)
    
    def exit(self):
        self.good = None
        self.item.exit()
        self.item = None
        
    def set_top(self, top):
        self.item.set_top(top)
        if DEBUG:
            self.debug_item.set_top(top + self.top)
    def get_aabb(self):
        item = self.item
        return Rect(item.get_left() + self.left, item.get_top() + self.top, 
            item.get_width() - self.left - self.right, item.get_height() - self.top)
        
class RunningMinigame(GameStage):
    CREATE_INTERVAL = 1000.0
    MOVE_INTERVAL = 30.0
    DIFICULTY_INTERVAL = 2000.0
    GOOD_INDICATOR_INTERVAL = 1000
    GO_BACK_TIME = 3000
    
    def __init__(self, game):
        GameStage.__init__(self, game, Color('#333333'))
    
    def initialize(self):
        GameStage.initialize(self)
        stream = file('data/fonts.yaml', 'r')
        
        fonts = load(stream)
        for font in fonts:
            setattr(self, font, assets.load_font(fonts[font]['file_name'], fonts[font]['size']))

        self.data = DictClass(load(file('data/running.yaml')))
        self.bad_distance = self.data.start.min_distance
        self.last_bad_invader = None
        self.score_layer = Layer()
        self.game_over_layer = Layer()
        image = assets.load_image(self.data.bad[self.game.datastore.datamodel.character].src)
        item = ItemImage(self.data.bad.left, self.data.bad.top, image)
        self.game_over_layer.add(item)
        image = assets.load_image(self.data.game_over[self.game.datastore.datamodel.character].src)
        item = ItemImage(self.data.game_over.left, self.data.game_over.top, image)
        self.game_over_layer.add(item)
        
        self.main_layer = Layer()
        self.score = 0
        self.match_points = self.data.score.match_points
        self.score_board = DictClass({})
        image = assets.load_image(self.data.score.src)
        self.score_board['skin'] = ItemImage(self.data.score.left, self.data.score.top, image)
        self.score_board['value'] = ItemText(self.data.score.left, self.data.score.top, self.font, 
            0, str(self.score), width = image.get_width(), height = image.get_height(),
            h_align = 2, v_align = 2)
        self.score_layer.add(self.score_board.skin)
        self.score_layer.add(self.score_board.value) 
        
        image = assets.load_image(self.data.good[self.game.datastore.datamodel.character].src)
        self.good_indicator = ItemImage(self.data.good.left, self.data.good.top, image)
        self.good_indicator.set_visible(False)
        self.score_layer.add(self.good_indicator)
        
        self.text_indicators = []
        
        data = DictClass(load(file('data/map/common.yaml')))
        params = data.character[self.game.datastore.datamodel.character]
        params['base'] = data.character.base[self.game.datastore.datamodel.character].big
        self.character_animation = Character(**params)
        self.character = self.character_animation.item
        self.character_start_top = SCREEN_HEIGHT - self.character.get_height()
        self.character.set_top(self.character_start_top)
        self.character.set_left(25)
        self.invaders = []
        self.velocity = self.data.start.velocity
        self.jumping = False
        
        # Load the sound
        self.item_found_sound = assets.load_sound('DGI_item_found.ogg')
        self.lose_hit_sound = assets.load_sound('DGI_lose_hit.ogg')
        self.lose_music_sound = assets.load_sound('DGI_lose_music.ogg')

    def update_dificulty(self, key, data):
        self.bad_distance -= self.data.step.delta_distance
        if self.bad_distance <= 0:
            self.bad_distance = 0

    def create_invader(self, key, data):
        lst = [(True, 0.25), (False, 0.75)]
        good = w_choice(lst)
        if good:
            index = random.randint(0, len(self.data.invaders.good) - 1)
            inv = self.data.invaders.good[index]
        else:
            if self.last_bad_invader and \
                SCREEN_WIDTH - (self.last_bad_invader.item.get_left() + \
                self.last_bad_invader.item.get_width()) < self.bad_distance:
                return
            index = random.randint(0, len(self.data.invaders.bad) - 1)
            inv = self.data.invaders.bad[index]
        aabb = inv.get("aabb", {})
        invader = Invader(good, inv.src, aabb.get("left", 20), 
            aabb.get("right", 20), aabb.get("top", 20), inv.get("points", 0))
        if not good:
            if self.last_bad_invader and not (self.last_bad_invader in self.invaders):
                self.last_bad_invader.exit()
            self.last_bad_invader = invader
        left = SCREEN_WIDTH
        if "top" in inv:
            top = inv.top
        else:
            top = SCREEN_HEIGHT - invader.item.get_height()
        invader.set_left(left)
        invader.set_top(top)
        self.invaders.append(invader)
        self.main_layer.add(invader.item)
        if DEBUG:
            self.main_layer.add(invader.debug_item)
    
    def move_invaders(self, key, data):
        for item in self.text_indicators:
            item.set_top(item.get_top() - 2)
        for invader in self.invaders:
            invader.set_left(invader.item.get_left() - self.MOVE_INTERVAL * self.velocity)
            if (invader.item.get_left() + invader.item.get_width() < 0):
                self.remove_invader(invader)
            else:
                character = Rect(self.character.get_left(), self.character.get_top(), 
                    self.character.get_width(), self.character.get_height())
                item = invader.get_aabb()
                k = character.collidelist([item])
                if k != -1:
                    if invader.good:
                        self.character_animation.footsteps_concrete_sound.stop()
                        self.item_found_sound.play()
                        self.character_animation.first_walking = True
                        
                        self.score += invader.points
                        self.score_board.value.set_text(str(self.score))
                        self.good_indicator.set_visible(True)
                        item = ItemText(invader.item.get_left(), invader.item.get_top(), 
                            self.font, 0, "+" + str(invader.points), h_align = 2, v_align = 2)
                        self.text_indicators.append(item)
                        self.main_layer.add(item)
                        fade_out_item(item, True, self.GOOD_INDICATOR_INTERVAL, self.remove_indicator)
                        self.start_timer(4, self.GOOD_INDICATOR_INTERVAL, self.remove_good_indicator)
                    else:
                        self.stop_timer(1)
                        self.stop_timer(2)
                        self.stop_timer(3)
                        self.game_over()
                        return
                    self.remove_invader(invader)
    
    def remove_indicator(self, item):
        item.exit()
        self.text_indicators.remove(item)
        
    def remove_invader(self, invader):
        self.invaders.remove(invader)
        self.main_layer.remove(invader.item)
        if invader != self.last_bad_invader:
            invader.exit()
        if DEBUG:
            self.main_layer.remove(invader.debug_item)
        
    def remove_good_indicator(self, key, data):
        self.good_indicator.set_visible(False)

    def prepare(self):
        self.show_board()
        self.key = None
        dialog = Intro(self, self.data.intro, self.start_game)
        dialog.start()

    def start_game(self):
        self.start_timer(1, self.CREATE_INTERVAL, self.create_invader)
        self.start_timer(2, self.MOVE_INTERVAL, self.move_invaders)
        self.start_timer(3, self.DIFICULTY_INTERVAL, self.update_dificulty)
        self.start_timer(0, 30, self.manage_key)
        
    def show_board(self):
        self.main_layer.add(self.character)
        self.add_layer(self.main_layer)
        self.add_layer(self.score_layer)
    
    def handle_event(self, e):
        if e.type == KEYDOWN:
            self.key = e.key
        if  e.type == KEYUP:
            self.key = None
            
    def manage_key(self, key, data):
        self.gravity = self.data.jump.gravity
        max_character_y_velocity = -self.data.jump.max_impulse
        character_y_velocity_increment = self.data.jump.impulse_increment
        max_velocity_time = self.data.jump.impulse_max_time
        if not self.jumping and self.key == K_UP:
            self.velocity_increment_timer = 0
            self.jumping = True
            self.character_y_velocity = -character_y_velocity_increment
        if self.jumping:
            self.velocity_increment_timer += self.MOVE_INTERVAL
            if self.key == K_UP and self.velocity_increment_timer < max_velocity_time:
                self.character_y_velocity -= character_y_velocity_increment
                if self.character_y_velocity < max_character_y_velocity:
                    self.character_y_velocity = max_character_y_velocity
                    self.velocity_incerement_timer = max_velocity_time
            top = self.character.get_top()
            self.character_y_velocity += self.gravity * self.MOVE_INTERVAL/1000.0
            top += self.character_y_velocity * self.MOVE_INTERVAL/1000.0
            if top + self.character.get_height() >= SCREEN_HEIGHT:
                self.character_y_velocity = 0
                self.jumping = False
                top = self.character_start_top
            self.character.set_top(top)
        self.character_animation.update(self.MOVE_INTERVAL, delta_left = 1, jumping = self.jumping)
            
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
        self.add_layer(self.game_over_layer)
        self.start_timer("go_back_timer", self.GO_BACK_TIME, self.go_back)
    
    def exit(self, other):
        GameStage.exit(self, other)
        self.good_indicator.exit()
        self.good_indicator = None
        self.character_animation.exit()
        self.character_animation = None
        self.character = None
        for invader in self.invaders:
            invader.exit()
        self.data = None
        for text in self.text_indicators:
            text.exit()
        self.text_indicators = None
    
    def stop(self):
        self.character_animation.footsteps_concrete_sound.stop()

    def go_back(self, *args, **kwargs):
        from game.stages.map import Map
        self.game.set_stage(Map(self.game))