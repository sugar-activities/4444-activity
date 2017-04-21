# -*- coding: latin-1 -*-

# 2011 - Dirección General Impositiva, Uruguay.
# Todos los derechos reservados.
# All rights reserved.

from framework.stage import assets
from game.stages.gamestage import GameStage
from phase import Phase1, Phase2, Phase3, Phase4
from widgets.option import OptionGroup, OptionImage

class Presentation(GameStage):

    def __init__(self, game, screen=None):
        GameStage.__init__(self, game)
        self._start_screen = screen

    def initialize(self):
        GameStage.initialize(self)
        self.character = None
        self.character_group = OptionGroup()
        self.level_group = OptionGroup()
        self.continued = False
    
    def prepare(self):
        if self._start_screen:
            self.set_screen(self._start_screen)
        elif not self.game.datastore.loaded_data:
            self.actual_screen = 0    
        GameStage.prepare(self)
        
    def set_up_background(self):
        return
    
    def create_characters(self, data):
        characters = []
        for gender in ['male', 'female']:
            data[gender].update(self.data_sounds)
            characters += self.create_option_image(self.character_group, data[gender])
        self.character_group.buttons = self.create_button(data['button'])
        
        return characters + self.character_group.buttons
    
    def create_levels(self, data):
        levels = []
        max_level = self.game.datastore.datamodel.unlocked_level + 1
        if max_level > 5:
            max_level = 5
        for i in range(1, max_level):
            data['level' + str(i)]['enabled'].update(self.data_sounds)
            levels += self.create_option_image(self.level_group, data['level' + str(i)]['enabled'])
        for i in range(max_level, 5):
            levels += self.create_image(data['level' + str(i)]['disabled'])
        self.level_group.buttons = self.create_button(data['button'])
        if 'selected_character' in data:
            self.level_group.buttons += self.create_button(data['selected_character'][self.game.datastore.datamodel.character], 
            sounds = False)
        return levels + self.level_group.buttons
    
    def handle_previous(self, item, args):
        self.show_previous_screen()
    
    def handle_start(self, item, args):
        self.continued = False
        self.game.datastore.reset_character()
        self.show_next_screen()
    
    def handle_continue(self, item, args):
        self.continued = True
        self.actual_screen = 2
        self.show_next_screen()

    def handle_next(self, item, args):
        if self.actual_screen == 2:
            if self.character_group.selected.value:
                self.game.datastore.datamodel.character = self.character_group.selected.value
                self.show_next_screen()
        elif self.actual_screen == 3:
            if self.level_group.selected.value:
                if self.level_group.selected.value == 'level1':
                    self.game.datastore.datamodel.level = 1
                    phase = Phase1(self.game)
                if self.level_group.selected.value == 'level2':
                    self.game.datastore.datamodel.level = 2
                    phase = Phase2(self.game)
                if self.level_group.selected.value == 'level3':
                    self.game.datastore.datamodel.level = 3
                    phase = Phase3(self.game)
                if self.level_group.selected.value == 'level4':
                    self.game.datastore.datamodel.level = 4
                    phase = Phase4(self.game)
                self.game.set_stage(phase)
        else:
            self.show_next_screen()
