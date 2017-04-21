# -*- coding: latin-1 -*-

# 2011 - Dirección General Impositiva, Uruguay.
# Todos los derechos reservados.
# All rights reserved.

from game.stages.gamestage import GameStage        

class Phase(GameStage):
    def initialize(self):
        GameStage.initialize(self)
    
    def set_up_background(self):
        return

    def show_next_item(self):
        GameStage.show_next_item(self)

    def handle_previous(self, item, args):
        if self.actual_screen == 0:
            from presentation import Presentation
            presentation = Presentation(self.game, 3)
            self.game.set_stage(presentation)
        else:
            self.show_previous_screen()
        
    def handle_next(self, item, args):
        if self.actual_screen == 3:
            from map import Map
            self.game.set_stage(Map(self.game))
        else:
            self.show_next_screen()

class Phase1(Phase):
    pass
class Phase2(Phase):
    pass
class Phase3(Phase):
    pass
class Phase4(Phase):
    pass