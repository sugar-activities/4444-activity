# -*- coding: latin-1 -*-

# 2011 - Dirección General Impositiva, Uruguay.
# Todos los derechos reservados.
# All rights reserved.


from framework.stage import assets, ItemEvent, ItemImage, ItemText, Layer, Stage
import random
from math import ceil, sqrt
from utils import DictClass
from yaml import load
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

class Card():
    def __init__(self, stage, key, image, image_back):
        self.stage = stage
        self.key = key
        self.image = image
        self.image_back = image_back
        self.item = ItemImage(0, 0, image_back)
        self.item.add_event_handler(ItemEvent.CLICK, self.handle_click)
        
    def handle_click(self, item, args):
        self.stage.select(self)
        
    def select(self):
        self.item.set_image(self.image)
    
    def unselect(self):
        self.item.set_image(self.image_back)
    
    def exit(self):
        self.stage = None
        self.image = None
        self.image_back = None
        self.item.exit()
        self.item = None

class MemoryMinigame(GameStage):
    GO_BACK_TIME = 3000
    ONE_SECOND_INTERVAL = 1000
    
    def __init__(self, game):
        GameStage.__init__(self, game)
        
    def initialize(self):
        GameStage.initialize(self)
        stream = file('data/fonts.yaml', 'r')
        fonts = load(stream)
        for font in fonts:
            setattr(self, font, assets.load_font(fonts[font]['file_name'], fonts[font]['size']))
            
        self.data = DictClass(load(file('data/memory.yaml')))
        
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
        self.timer['value'] = ItemText(self.data.time.left, self.data.time.top, self.font, 0, 
        format_time(self.time), width = image.get_width(), height = image.get_height(), h_align = 2, v_align = 2)
        self.top_layer.add(self.timer.skin)
        self.top_layer.add(self.timer.value)
        
        self.score = 0
        self.score_board = DictClass({})
        image = assets.load_image(self.data.score.src)
        self.score_board['skin'] = ItemImage(self.data.score.left, self.data.score.top, image)
        self.score_board['value'] = ItemText(self.data.score.left, self.data.score.top, self.font, 0, 
        str(self.score), width = image.get_width(), height = image.get_height(), h_align = 2, v_align = 2)
        self.top_layer.add(self.score_board.skin)
        self.top_layer.add(self.score_board.value)
        
        self.deck = []
        image_back = assets.load_image(self.data.board.card_back)
        for k in range(0, len(self.data.board.cards)):
            image = assets.load_image(self.data.board.cards[k])
            self.deck.append([Card(self, k, image, image_back), Card(self, k, image, image_back)])
            
        self.range = self.data.start
        self.cards = []
        self.deal()
        
        # Load the sound
        self.card_flip_sound = assets.load_sound('DGI_card_flip.ogg')
        self.item_found_sound = assets.load_sound('DGI_item_found.ogg')
        self.wrong_sound = assets.load_sound('DGI_wrong.ogg')
        self.lose_bell_sound = assets.load_sound('DGI_lose_bell.ogg')
        self.lose_music_sound = assets.load_sound('DGI_lose_music.ogg')

    def deal(self):
        self.first = None
        self.second = None
        
        for k in range(0, self.range):
            self.cards.append(self.deck[k][0])
            self.cards.append(self.deck[k][1])
        random.shuffle(self.cards)
        
        d = ceil(sqrt(2 * self.range))
        for i, card in zip(range(2 * self.range), self.cards):
            card.item.set_left(self.data.board.left + card.item.get_width() * (i % d))
            card.item.set_top(self.data.board.top + card.item.get_height() * int(i / d))
            self.main_layer.add(card.item)
    
    def select(self, card):
        self.card_flip_sound.play()
        if not self.second:
            if self.first:
                if self.first != card:
                    self.second = card
                    card.select()
                    self.start_timer(1, 500, self.check_match)
            else:
                self.first = card
                card.select()
    
    def check_match(self, key, data):
        self.stop_timer(1)
        if self.first.key == self.second.key:
            self.item_found_sound.play()
            self.cards.remove(self.first)
            self.cards.remove(self.second)
            self.main_layer.remove(self.first.item)
            self.main_layer.remove(self.second.item)
            self.score += self.data.score.points
            self.score_board.value.set_text(str(self.score))
        else:
            self.wrong_sound.play()
        self.first.unselect()
        self.second.unselect()
        self.first = self.second = None
        if len(self.cards) == 2:
            self.first = self.cards[0]
            self.second = self.cards[1]
            self.first.select()
            self.second.select()
            self.start_timer(1, 500, self.check_match)
        elif not self.cards:
            if self.range + self.data.step <= len(self.deck):
                self.range += self.data.step
            self.deal()
    
    def prepare(self):
        self.show_board()
        dialog = Intro(self, self.data.intro, self.start_game)
        dialog.start()
    
    def start_game(self):
        self.start_timer(0, self.ONE_SECOND_INTERVAL, self.update_time)
    
    def update_time(self, key, data):
        self.time -= 1
        self.timer.value.set_text(format_time(self.time))
        if not self.time:
            self.game_over()
    
    def show_board(self):
        self.add_layer(self.main_layer)
        self.add_layer(self.top_layer)
        
    def game_over(self):
        self.lose_bell_sound.play()
        self.lose_music_sound.play()
        self.stop_timer(0)
        for card in self.cards:
            card.item.remove_event_handler(ItemEvent.CLICK, card.handle_click)
        self.add_layer(self.game_over_layer)
        self.start_timer("go_back_timer", self.GO_BACK_TIME, self.go_back)
    
    def exit(self, other_item):
        GameStage.exit(self, other_item)
        for card1, card2 in self.deck:
            card1.exit()
            card2.exit()
        self.deck = None
        self.cards = None
    
    def go_back(self, *args, **kwargs):
        from game.stages.map import Map
        self.game.set_stage(Map(self.game))
