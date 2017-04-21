# -*- coding: latin-1 -*-

# 2011 - Dirección General Impositiva, Uruguay.
# Todos los derechos reservados.
# All rights reserved.

from pygame import KEYDOWN, KEYUP, K_DOWN, K_LEFT, K_RIGHT, K_UP, QUIT
from game.stages.gamestage import GameStage
from backpack import BackPack
from questions import TestsViewer, MultipleChoice, TrueFalse, Joining
from games import GamesViewer
from activity import Activity, ItemTextTab
from math import sin, cos, fabs
from utils import DictClass
from framework.stage import assets, ItemImage, Layer
from yaml import load
from character import Character 
from math import sqrt


class ExitDialog():

    def __init__(self, stage, on_no):
        self.stage = stage
        layer = self.layer = Layer()
        data = load(file('data/map/exit_dialog.yaml'))
        items = stage.create_items_from_yaml(data['items'], self)
        self.on_no = on_no
        for item in items:
            layer.add(item)
    
    def handle_ok(self, item, args):
        from presentation import Presentation
        presentation = Presentation(self.stage.game, 3)
        self.stage.game.set_stage(presentation)
    
    def handle_cancel(self, *args, **kwargs):
        self.on_no()
        self.stop()
    
    def stop(self):
        self.stage.close_dialog(self.layer)
        self.layer.exit()
        self.on_no = None
        self.stage = None

    def start(self):
        self.stage.show_dialog(self.layer, None)
     

class MapManager():
    
    def __init__(self, stage, character, layer):
        self.character = character
        self.elements = list(layer.items)
        self.sort_elements()
        self.layer = layer
        layer.empty()
        [layer.add(element) for element in self.elements]
        self.stage = stage
        for element in self.elements:
            self.layer.add(element)
    
    def sort_elements(self):
        self.elements.sort(lambda x, y: cmp(x.get_top() + x.get_height(), y.get_top() + y.get_height()))

    def update(self):
        last_index = self.elements.index(self.character)
        self.sort_elements()
        new_index = self.elements.index(self.character)
        if last_index != new_index:
            self.layer.remove(self.character)
            self.layer.add(self.character, new_index)
    
    def exit(self):
        self.character = None
        self.elements = None
        self.layer = None
        self.stage = None
        

COLLISION_COLOR = (0, 0, 0, 255)
ENTRANCE_COLOR = (0, 0, 255, 255)
class Map(GameStage):
    def __init__(self, game):
        GameStage.__init__(self, game)
            
    INTERVAL = 30
    def initialize(self):
        GameStage.initialize(self)

        self.tests = None 
        self.h_key = None
        self.v_key = None
        self.map_character = None
        self.named_layers = None
        self.collisions = None
        self.map_manager = None
        
        if self.game.datastore.datamodel.current_map_index:
            self.current_map_index = self.game.datastore.datamodel.current_map_index
            self.game.datastore.datamodel.current_map_index = None
        else:
            self.current_map_index = 4
        
        # Load the sound
        self.street_ambience_sound = assets.load_sound('DGI_street_ambience.ogg')
        self.street_ambience_sound.play(-1)
    
    def set_up_background(self):
        return

    def load_quadrant(self):
        # remove the character before it gets destroyed
        if self.named_layers and hasattr(self.named_layers, "character"):
            self.named_layers.character.remove(self.map_character.item)
        if self.layers:
            self.remove_layer(self.gui)
        for layer in self.layers:
            layer.exit()
        self.empty_layers()
        data = DictClass(load(file('data/map/quadrant_%d.yaml' % self.current_map_index)))
        self.named_layers, layers = self.create_layers(data["layers"])
        self.named_layers.character.add(self.map_character.item)
        
        if self.game.datastore.datamodel.map_character_left:
            self.map_character.item.set_left(self.game.datastore.datamodel.map_character_left)
            self.game.datastore.datamodel.map_character_left = None
        if self.game.datastore.datamodel.map_character_top:
            self.map_character.item.set_top(self.game.datastore.datamodel.map_character_top)
            self.game.datastore.datamodel.map_character_top = None
            
        class Collision():
            def __init__(self, collision_map, trans_x = 0, trans_y = 0):
                self.collision_map = collision_map
                self.trans_x = trans_x
                self.trans_y = trans_y
            
            def get_at(self, pos):
                return self.collision_map.get_at((pos[0] + self.trans_x, pos[1] + self.trans_y))
            
            def bottom(self):
                return self.collision_map.get_height() - self.trans_y
            
            def left(self):
                return -self.trans_x
            
            def right(self):
                return self.collision_map.get_width() - self.trans_x
            
            def top(self):
                return -self.trans_y 
             
            def exit(self):
                self.collision_map = None
                
        if "collision" in data:
            if self.collisions:
                for col in self.collisions:
                    col.exit()
            self.collisions = []
            base_data = data.collision.base
            self.collisions.append(Collision(assets.load_mask(base_data.src), base_data.get("trans_x", 0), base_data.get("trans_y", 0)))
            if self.game.datastore.datamodel.unlocked_level >= 3:
                self.collisions.append(Collision(assets.load_mask(data.collision.trash.src)))
            if self.game.datastore.datamodel.unlocked_level >= 4:
                self.collisions.append(Collision(assets.load_mask(data.collision.lights.src)))
            if self.game.datastore.datamodel.unlocked_level >= 5  and "vegetation" in data.collision:
                self.collisions.append(Collision(assets.load_mask(data.collision.vegetation.src)))
        else:
            self.collisions = []
        if "entrance" in data:
            self.entrance = assets.load_mask(data.entrance.src)
            to = data.entrance.to
            index = to.rfind(".")
            if (index > 1):
                self.entrance_class = getattr(__import__(to[:index], globals(), locals(), to[index+1:]), to[index+1:])
            else:
                self.entrance_class = globals()[to]
        else:
            self.entrance = None
        if self.map_manager:
            self.map_manager.exit()
        self.map_manager = MapManager(self, self.map_character.item, self.named_layers.character)
        for layer in layers:
            self.add_layer(layer)
        self.add_layer(self.gui)
        
        # Start processing events after everything is loaded
        self.start_timer(0, self.INTERVAL, self.manage_key)

    def prepare(self):
        data = DictClass(load(file('data/map/common.yaml')))
        self.gui = Layer()
        for item in self.create_items_from_yaml(data.gui):
            self.gui.add(item)
        self.create_selected_map_character(data.character)
        self.load_quadrant()
        self.tests_counter = self.create_text(data.counters.tests)[0]
        self.backpack_counter = self.create_text(data.counters.backpack)[0]
        self.games_counter = self.create_text(data.counters.games)[0]
        self.gui.add(self.tests_counter)
        self.gui.add(self.backpack_counter)
        self.gui.add(self.games_counter)
        self.backpack_counter.set_text(str(len(self.game.datastore.datamodel.backpack[self.game.datastore.datamodel.level - 1])))
        self.tests_counter.set_text(str(len(self.game.datastore.levels[self.game.datastore.datamodel.level].tests)))
        self.games_counter.set_text(str(self.game.datastore.datamodel.unlocked_level - 1))

    def create_selected_map_character(self, data):
        if not self.map_character:
            character = self.game.datastore.datamodel.character
            params = data[character]
            params['base'] = data.base[character].small
            params["jumping"] = None
            self.map_character = Character(**params)
        return [self.map_character.item]

    def create_buildings(self, data):
        return self.create_items_from_yaml(data["items"])
    
    def create_background(self, data):
        if self.game.datastore.datamodel.unlocked_level <= 1:
            return self.create_image(data["dirty"])
        else:
            return self.create_image(data["clean"])
            
    def create_text_tab(self, data):
        args, kwargs = self.text_arguments(data)
        return [ItemTextTab(*args, **kwargs)]
        
    def create_trash(self, data):
        if self.game.datastore.datamodel.unlocked_level <= 2:
            return self.create_items_from_yaml(data["before"])
        else:
            return self.create_items_from_yaml(data["after"])
    
    def create_lights(self, data):
        if self.game.datastore.datamodel.unlocked_level <= 3:
            return []
        else:
            return self.create_items_from_yaml(data["items"])
    
    def create_level_counter(self, data):
        data["src"] = data["src"][self.game.datastore.datamodel.level]
        return self.create_image(data)
    
    def create_vegetation(self, data):
        if self.game.datastore.datamodel.unlocked_level <= 4:
            return []
        else:
            return self.create_items_from_yaml(data["items"])

    def handle_backpack(self, items, args):
        backpack = BackPack(self, [self.game.datastore.contents[content_id] for content_id in self.game.datastore.datamodel.backpack[self.game.datastore.datamodel.level - 1]])
        backpack.start()
    
    def handle_exercises(self, item, args):
        if not self.tests:
            tests = []
            for test in self.game.datastore.levels[self.game.datastore.datamodel.level].tests:
                test = self.game.datastore.tests[test]
                if test.type == "multiple":
                    tests.append(MultipleChoice(self, test.title, test.description, test.options, test.answer))
                elif test.type == "true_false":
                    tests.append(TrueFalse(self, test.title, test.description, test.options, test.answer))
                elif test.type == "joining":
                    tests.append(Joining(self, test.title, test.description, test.left_options, test.right_options, map(tuple, test.answer), test.get("visualization", None)))        
            self.tests = TestsViewer(self, tests)
        self.tests.start()
    
    def handle_games(self, item, args):
        games = GamesViewer(self)
        games.start()
    
    def handle_activity(self, item, args):
        activity = Activity(self)
        activity.start()
        
    def handle_previous(self, item, args):
        if self.actual_screen == 0:
            from presentation import Presentation
            presentation = Presentation(self.game, 2)
            self.game.set_stage(presentation)
        else:
            self.show_previous_screen()
    
    def exit(self, other_self):
        GameStage.exit(self, other_self)
        self.gui.exit()
        self.gui = None
        if self.tests:
            self.tests.exit()
        self.tests = None
        self.map_character.exit()
        self.map_character = None
        if self.collisions:
            for col in self.collisions:
                col.exit()
        self.collisions = None
        self.named_layers = None
        self.entrance = None
        if self.map_manager:
            self.map_manager.exit()
            self.map_manager = None
    
    def handle_back(self, *args, **kwargs):
        dialog = ExitDialog(self, self.on_exit_no)
        self.stop_timer(0)
        dialog.start()
        
    def on_exit_no(self):
        self.start_timer(0, self.INTERVAL, self.manage_key)

    def handle_next(self, item, args):
        self.show_next_screen()

    def handle_event(self, e):
        if e.type == KEYDOWN:
            if (e.key == K_LEFT or e.key == K_RIGHT):
                self.h_key = e.key
            elif (e.key == K_UP or e.key == K_DOWN):
                self.v_key = e.key
        if e.type == KEYUP:
            if self.h_key == e.key:
                self.h_key = None
            elif self.v_key == e.key:
                self.v_key = None
  
    def manage_key(self, key, data):
        if self.map_character:
            if not self.h_key and self.v_key == K_UP:
                x = 0
                y = -1
            elif not self.h_key and self.v_key == K_DOWN:
                x = 0
                y = 1
            elif self.h_key == K_LEFT and not self.v_key:
                x = -1
                y = 0
            elif self.h_key == K_RIGHT and not self.v_key:
                x = 1
                y = 0
            elif self.h_key == K_LEFT and self.v_key == K_UP:
                x = -cos(1)
                y = -sin(1)
            elif self.h_key == K_LEFT and self.v_key == K_DOWN:
                x = -cos(1)
                y = sin(1)
            elif self.h_key == K_RIGHT and self.v_key == K_UP:
                x = cos(1)
                y = -sin(1)
            elif self.h_key == K_RIGHT and self.v_key == K_DOWN:
                x = cos(1)
                y = sin(1)
            else:
                x = 0
                y = 0
            r = 4
            x *= r
            y *= r
            self.move_character(x, y)
    
    def move_character(self, delta_left, delta_top):
        current_map_index = self.current_map_index
        window_width, window_height = self.game.get_window_size()
        
        character = self.map_character.item
        height = character.get_height()
        width = character.get_width()
        left = character.get_left()
        top = character.get_top()
        new_left = left + delta_left
        new_top = top + delta_top
        
        if (self.check_entrance(new_left + width / 2, new_top + height)):
            self.game.datastore.datamodel.current_map_index = self.current_map_index
            self.game.datastore.datamodel.map_character_left = self.map_character.item.get_left()
            self.game.datastore.datamodel.map_character_top = self.map_character.item.get_top()
            self.game.set_stage(self.entrance_class(self.game))
            return
        if delta_left or delta_top:
            new_left, new_top = self.check_collition(left + width / 2, top + height, new_left + width / 2, new_top + height)
            new_left -= width / 2
            new_top -= height

        self.map_manager.update()
        if self.current_map_index == 1:
            if new_left < 0:
                new_left = 0
            elif new_left > window_width - width / 2:
                new_left = - width / 2
                self.current_map_index = 2
            
            if new_top < 0:
                new_top = 0
            elif new_top > window_height - height / 2:
                new_top = - height / 2
                self.current_map_index = 4    
        
        elif self.current_map_index == 2:
            if new_left < - width / 2:
                new_left = window_width - width / 2
                self.current_map_index = 1
            elif new_left > window_width - width:
                new_left = window_width - width
            
            if new_top < 0:
                new_top = 0
            elif new_top > window_height - height / 2:
                new_top = - height / 2
                self.current_map_index = 3
                
        elif self.current_map_index == 3:
            if new_left < - width / 2:
                new_left = window_width - width / 2
                self.current_map_index = 4
            elif new_left > window_width - width:
                new_left = window_width - width
            
            if new_top < - height / 2:
                new_top = window_height - height / 2
                self.current_map_index = 2
            elif new_top > window_height - height:
                new_top = window_height - height
        
        elif self.current_map_index == 4:
            if new_left < 0:
                new_left = 0
            elif new_left > window_width - width / 2:
                new_left = - width / 2
                self.current_map_index = 3
            if new_top < - height / 2:
                new_top = window_height - height / 2
                self.current_map_index = 1
            elif new_top > window_height - height:
                new_top = window_height - height
        
        if (left != new_left or top != new_top):
            character.set_left(new_left)
            character.set_top(new_top)
        self.map_character.update(self.INTERVAL, delta_left, delta_top)
          
        if self.current_map_index != current_map_index:
            self.load_quadrant()
    
    def check_entrance(self, left, top):
        if self.game.datastore.levels[self.game.datastore.datamodel.level].place_quadrant != self.current_map_index - 1:
            return False
        entrance = self.entrance
        if not entrance: return False
        c_width = entrance.get_width()
        c_height = entrance.get_height()
        return left >= 0 and top >= 0 and left < c_width and top < c_height \
            and entrance.get_at((int(left), int(top))) == ENTRANCE_COLOR

    def handle_level_change(self):
        if self.game.datastore.datamodel.level < 4:
            from presentation import Presentation
            presentation = Presentation(self.game, 3)
            self.game.datastore.changed_data = True
            self.game.set_stage(presentation)
        else:
            self.game.set_stage(Map(self.game))

    def check_collition_color(self, left, top):
        exists = False
        for collision in self.collisions:
            if left < collision.right() and left >= collision.left() and top < collision.bottom()\
                and top >= collision.top():
                if collision.get_at((left, top)) == COLLISION_COLOR:
                    return True
                exists = True
        return not exists
            
    def check_collition(self, left, top, new_left, new_top):
        if self.check_collition_color(int(new_left), int(new_top)):
            Dx = float(new_left - left)
            Dy = float(new_top - top)
            left = float(left)
            top = float(top)
            dx = Dx/4.0
            dy = Dy/4.0
            n_dx = dy
            n_dy = -dx
            Dx = fabs(Dx)
            Dy = fabs(Dy)
            fdy = fabs(dy)
            fdx = fabs(dx)
            total = sqrt(Dx*Dx + Dy*Dy)
            while total > 0:
                left = left + dx
                top = top + dy
                found = True
                if self.check_collition_color(int(left), int(top)):
                    slide_total = total
                    slide_left = left + n_dx
                    slide_top = top + n_dy
                    found = False
                    while slide_total > 0:
                        if self.check_collition_color(int(slide_left), int(slide_top)):
                            slide_left = slide_left + n_dx
                            slide_top = slide_top + n_dy
                            slide_total -= sqrt(n_dx**2 + n_dy**2)
                        else:
                            total = slide_total - sqrt(fdx**2 + fdy**2)
                            left = slide_left
                            top = slide_top
                            found = True
                            break
                    if not found:
                        slide_total = total
                        slide_left = left - n_dx
                        slide_top = top - n_dy
                        while slide_total > 0:
                            if self.check_collition_color(int(slide_left), int(slide_top)):
                                slide_left = slide_left - n_dx
                                slide_top = slide_top - n_dy
                                slide_total -= sqrt(n_dx**2 + n_dy**2)
                            else:
                                total = slide_total - sqrt(fdx**2 + fdy**2)
                                left = slide_left
                                top = slide_top
                                found = True
                                break
                    if not found:
                        return left - dx, top - dy
                else:
                    Dx -= fdx
                    Dy -= fdy
                    total -= sqrt(fdx**2 + fdy**2)
            return left, top
        return new_left, new_top
                    
def limit(val, fromm, to):
    val = val if val >= fromm else fromm
    val = val if val <= to else to
    return val