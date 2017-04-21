# -*- coding: latin-1 -*-

# 2011 - Dirección General Impositiva, Uruguay.
# Todos los derechos reservados.
# All rights reserved.


from framework.stage import assets, ItemEvent, ItemImage, ItemText, Layer, Stage
from utils import DictClass
from yaml import load
import random
from framework.engine import SCREEN_HEIGHT, SCREEN_WIDTH
from gameintro import Intro
from game.stages.gamestage import GameStage

def format_time(time):
    min = str(time / 60)
    if len(min) == 1:
        min = '0' + min
    seg = str(time % 60)
    if len(seg) == 1:
        seg = '0' + seg
    return min + ':' + seg

class Asteroid():
    def __init__(self, stage, left, top, src, value):
        self.stage = stage
        image = assets.load_image(src)
        self.item = ItemImage(left, top, image)
        self.item.add_event_handler(ItemEvent.CLICK, self.handle_click)
        self.text = ItemText(left, top, stage.font, 0, str(value), width = self.item.get_width(), height = self.item.get_height(), h_align = 2, v_align = 2)
        self.value = value
    
    def set_left(self, left):
        self.item.set_left(left)
        self.text.set_left(left)
    
    def set_top(self, top):
        self.item.set_top(top)
        self.text.set_top(top)
        
    def handle_click(self, item, args):
        self.stage.select(self)
    
    def exit(self):
        self.item.exit()
        self.item = None
        self.text.exit()
        self.text = None

class AsteroidsMinigame(GameStage):
    GO_BACK_TIME = 3000
    ONE_SECOND_INTERVAL = 1000
    MARGIN = 70
    
    def __init__(self, game):
        GameStage.__init__(self, game)
        
    def initialize(self):
        GameStage.initialize(self)
        stream = file('data/fonts.yaml', 'r')
        fonts = load(stream)
        for font in fonts:
            setattr(self, font, assets.load_font(fonts[font]['file_name'], fonts[font]['size']))
            
        self.data = DictClass(load(file('data/asteroids.yaml')))
        
        self.game_over_layer = Layer()
        image = assets.load_image(self.data.game_over[self.game.datastore.datamodel.character].src)
        item = ItemImage(self.data.game_over.left, self.data.game_over.top, image)
        self.game_over_layer.add(item)
        
        self.main_layer = Layer()
        self.top_layer = Layer()
        
        self.time = self.data.time.max
        self.timer = DictClass({})
        image = assets.load_image(self.data.time.src)
        self.timer['skin'] = ItemImage(self.data.time.left, self.data.time.top, image)
        self.timer['value'] = ItemText(self.data.time.left, self.data.time.top, self.font, 0, format_time(self.time), width = image.get_width(), height = image.get_height(), h_align = 2, v_align = 2)
        self.top_layer.add(self.timer.skin)
        self.top_layer.add(self.timer.value)
        
        self.score = 0
        self.score_board = DictClass({})
        image = assets.load_image(self.data.score.src)
        self.score_board['skin'] = ItemImage(self.data.score.left, self.data.score.top, image)
        self.score_board['value'] = ItemText(self.data.score.left, self.data.score.top, self.font, 0, str(self.score), width = image.get_width(), height = image.get_height(), h_align = 2, v_align = 2)
        self.top_layer.add(self.score_board.skin)
        self.top_layer.add(self.score_board.value)
        
        self.level = self.data.start
        self.asteroids = []
        
        self.max_width = 0
        self.max_height = 0
        for a in self.data.asteroids:
            item = assets.load_image(a)
            if self.max_width < item.get_width():
                self.max_width = item.get_width()
            if self.max_height < item.get_height():
                self.max_height = item.get_height()
        self.max_col = int(SCREEN_WIDTH / self.max_width)
        self.max_row = int(SCREEN_HEIGHT / self.max_height)
        self.margin_left = (SCREEN_WIDTH % self.max_width) / 2
        self.margin_top = (SCREEN_HEIGHT % self.max_height) / 2
        
        # Load the sound
        self.click_sound = assets.load_sound('DGI_Click.ogg')
        self.item_found_sound = assets.load_sound('DGI_item_found.ogg')
        self.wrong_sound = assets.load_sound('DGI_wrong.ogg')
        self.lose_bell_sound = assets.load_sound('DGI_lose_bell.ogg')
        self.lose_music_sound = assets.load_sound('DGI_lose_music.ogg') 
    
    def prepare(self):
        self.show()
        self.add_layer(self.main_layer)
        self.add_layer(self.top_layer)
        dialog = Intro(self, self.data.intro, self.start_game)
        dialog.start()

    def start_game(self):
        self.start_timer(0, self.ONE_SECOND_INTERVAL, self.update_time)     
    
    def show(self):
        if 'selector' in self.data.levels[self.level]:
            selector = eval(self.data.levels[self.level].selector)
            aux_seq = eval(self.data.levels[self.level][selector])
        else:
            aux_seq = eval(self.data.levels[self.level].range)
        
        self.sequence = []
        for value in range(0, self.data.levels[self.level].quantity):
            value = random.choice(aux_seq)
            aux_seq.remove(value)
            self.sequence.append(value)
        
        self.sequence = sorted(self.sequence)
        self.sequence.reverse()
        
        positions = range(0, self.max_col * self.max_row)
        
        for value in self.sequence:
            src = random.choice(self.data.asteroids)
            asteroid = Asteroid(self, 0, 0, src, value)
            
            position = random.choice(positions)
            positions.remove(position)
            i = int(position / self.max_col)
            j = int(position % self.max_col) 
            left = self.margin_left + j * self.max_width + random.uniform(0, self.max_width % asteroid.item.get_width())
            top = self.margin_top + i * self.max_height + random.uniform(0, self.max_height % asteroid.item.get_height())
            
            asteroid.set_left(left)
            asteroid.set_top(top)
            self.asteroids.append(asteroid)
            self.main_layer.add(asteroid.item)
            self.main_layer.add(asteroid.text)
        
        if self.level + self.data.step <= self.data.max:
            self.level += self.data.step
    
    def select(self, asteroid):
        self.click_sound.play()
        expected = self.sequence.pop()
        if asteroid.value == expected:
            self.item_found_sound.play()
            self.score += self.data.score.points
            self.score_board.value.set_text(str(self.score))
            
            self.asteroids.remove(asteroid)
            self.main_layer.remove(asteroid.item)
            self.main_layer.remove(asteroid.text)
            asteroid.exit()
        else:
            self.wrong_sound.play()
            self.sequence.append(expected)
        if not self.asteroids:
            self.show()
    
    def update_time(self, key, data):
        self.time -= 1
        self.timer.value.set_text(format_time(self.time))
        if not self.time:
            self.game_over()
    
    def game_over(self):
        self.lose_bell_sound.play()
        self.lose_music_sound.play()
        self.stop_timer(0)
        for asteroid in self.asteroids:
            asteroid.item.remove_event_handler(ItemEvent.CLICK, asteroid.handle_click)
        self.add_layer(self.game_over_layer)
        self.start_timer("go_back_timer", self.GO_BACK_TIME, self.go_back)
    
    def go_back(self, *args, **kwargs):
        from game.stages.map import Map
        self.game.set_stage(Map(self.game))