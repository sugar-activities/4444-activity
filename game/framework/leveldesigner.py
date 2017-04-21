# -*- coding: latin-1 -*-

# 2011 - Dirección General Impositiva, Uruguay.
# Todos los derechos reservados.
# All rights reserved.

from stage import *
import leveldesigner

# Clipboard to implement copy/paste
clipboard_layer = None
clipboard_item = None

class SetItemsStage(StageIso):
    """        
    Stage that is used to set how is located each item in the cells of the stage.
    """                        
    
    def __init__(self, game, origin, cell_width, cell_height, grid_size, tags, place_holder_tags, states, set_prefix):
        """        
        Constructor.
        - game: Game.
        - origin: Origin.
        - cell_width: Cell's width.
        - cell_height: Cell's height.
        - grid_size: A (rows, columns) pair with the size of the grid.
        - tags: List with possible tags.
        - place_holder_tags: List with possible tags that can be assigned to a place holder.
        - states: List with information of the possible states for the items (instance of IsoState).
        - set_prefix: Prefix of the used set.
        """    
        StageIso.__init__(self, game, tags)
        window_width, window_height = game.get_window_size()
        
        # Restore previous state (if it was saved)
        full_name = self.get_state_file_name()
        state_loaded = False
        if os.path.isfile(full_name):                    
            try:                            
                file = open(full_name, 'r')
                state_set_prefix = file.readline().strip()
                set_number = int(file.readline().strip())
                item_index = int(file.readline().strip())
                zoom = int(file.readline().strip())
                place_holders_visible = (int(file.readline().strip()) == 1)
                default_state_name = file.readline().strip()
                file.close()
                state_loaded = True
            except Exception, message:
                print 'Cannot read set designer state:', full_name
                raise SystemExit, message
        if not state_loaded or state_set_prefix != set_prefix:
            # Set default options
            set_number = 1
            item_index = 0
            zoom = 2
            place_holders_visible = True    
            default_state_name = ""    
        
        # Store the tags, place holder names and states
        self.tags = tags
        self.place_holder_tags = place_holder_tags
        self.states = states
        
        # Prepare the grid
        self.zoom = zoom        
        self.origin = origin
        self.set_grid_definition(self.get_adjusted_origin(), cell_width, cell_height, self.zoom)
        self.grid_size = grid_size
        
        # Prepare auto save
        self.pending_save = False
        self.set_closed_handler(self.on_closed)
        
        # Create the layer for the items
        self.items_layer = Layer()
        self.add_layer(self.items_layer)

        # Add a layer to draw the grid
        self.grid_layer = Layer()
        self.add_layer(self.grid_layer)
        self.grid = None
        
        # Create the layer for the place holders
        self.current_place_holder = 0
        self.place_holders_layer = LayerBuffered(window_width, window_height, True)
        self.place_holders_layer.set_visible(place_holders_visible)
        self.add_layer(self.place_holders_layer)
        
        # Show the options
        self.font = assets.load_font("freesansbold.ttf", 12)
        window_width, window_height = game.get_window_size()
        text_color = (0, 0, 10)
        text_background = (215, 232, 237, 150)
        name_width = 95        
        self.item_type_item = ItemRect(5, window_height - 23 - 18 - 5, name_width, 18, self.font, 0, "", text_color, (241, 242, 201, 150))
        self.stage_name_item = ItemRect(5, window_height - 23, name_width, 18, self.font, 0, "", text_color, text_background)        
        self.tag_name_item = ItemRect(window_width - name_width - 5, 5, name_width, 18, self.font, 0, "", text_color, text_background)
        self.zindex_item = ItemRect(window_width - name_width * 2 - 10, 5, name_width, 18, self.font, 0, "Z-index:", (255, 255, 255), None)
        self.move_placeholder_item = ItemRect(5 + name_width + 5, window_height - 23 * 2, window_width - name_width - 15, 18, self.font, 0, "xxxxx", (255, 255, 255), None)
        self.state_items = []
        self.options_item = ItemRect(5 + name_width + 5, window_height - 23, window_width - name_width - 15, 18, self.font, 0, "", text_color, text_background)        
        self.options_layer = LayerBuffered(window_width, window_height, True)
        self.options_layer.add(self.item_type_item)
        self.options_layer.add(self.zindex_item)
        self.options_layer.add(self.stage_name_item)                
        self.options_layer.add(self.tag_name_item)            
        self.options_layer.add(self.move_placeholder_item)
        self.options_layer.add(self.options_item)
        self.add_layer(self.options_layer)
        self.current_options_mod = None        
        self.start_timer("update_options", 50, self.update_options_text)                                        
                
        # Load the default set        
        self.current_item = None
        self.items = []
        self.item_states = {}
        self.set_prefix = set_prefix                        
        self.load_set(set_number)        
        self.item_index = item_index
        self.current_item = None        
        self.move_placeholder_mode = False
        self.show_current_item(default_state_name)
        self.update_move_placeholder_text()
        self.update_options_text(None, None)

    def select_item_type(self, type):
        """
        Select the specified item type as the specified item.
        - type: Item type to select. 
        """                
        for index in xrange(len(self.items)):
            item = self.items[index]            
            if item.get_type() == type:                
                self.item_index = index
                self.current_place_holder = 0                        
                self.show_current_item()
                break                                                                
    
    def update_grid(self):
        """
        Update the draw of the grid in the stage. If it was not created, this function
        create it.
        """
        if self.grid != None:
            self.grid_layer.remove(self.grid)
        
        if self.current_item == None:
            mark_size = None
        else:
            mark_size = self.current_item.get_definition().size
        
        place_holder_cell = None
        if self.current_item != None and self.move_placeholder_mode:
            definition = self.current_item.get_definition()            
            if self.current_place_holder < len(definition.place_holders):
                selected_place_holder = definition.place_holders[self.current_place_holder]
                place_holder_cell = self.current_item.get_place_holder_rowcol(selected_place_holder)
                if place_holder_cell[0] < 0 or place_holder_cell[1] < 0:
                    place_holder_cell = None 
                            
        self.grid = create_grid(self, self.grid_size, True, mark_size, place_holder_cell)
        self.grid_layer.add(self.grid)           

    def update_options_text(self, key, data):
        """
        Update the text of the options.
        - key: Key used in the timer.
        - data: Data.        
        """
        mod = get_common_modifiers(pygame.key.get_mods())
        if mod == pygame.KMOD_NONE:
            text = "Arrows = Move"
            if not self.move_placeholder_mode:
                text += " | Q/A = Change type" 
            else:
                text += " | Q/A = Height"
            text += " | S = State | T = Tag | Z = "
            if self.zoom == 2:
                text += "Zoom out"
            else:
                text += "Zoom in"            
            self.options_item.set_text(text)
        elif (mod == pygame.KMOD_LCTRL) or (mod == pygame.KMOD_RCTRL):
            text = "Arrows = Resize"
            if not self.move_placeholder_mode:
                text += " | Page Up/Down = Change set"
            self.options_item.set_text(text)
        elif (mod == pygame.KMOD_LALT) or (mod == pygame.KMOD_RALT):
            if self.place_holders_layer.get_visible():
                hide_text = "Hide"
            else:
                hide_text = "Show"
                
            self.options_item.set_text("N = New | M = Move | S = Select | T = Tag | Del = Delete | H = " + hide_text)
        else:
            self.options_item.set_text("")
        self.current_options_mod = mod

    def get_set_file_name(self):
        return os.path.join('data', self.set_name + '.tcs')

    def get_state_file_name(self):
        return os.path.join('data', 'setdesigner.sta')

    def get_key_repeat(self):
        """
        Gets the key repeat configuration for the stage. Returns (delay, interval) or
        None if key repeat is disabled for the stage. The delay is the number of milliseconds 
        before the first repeated pygame.KEYDOWN will be sent. After that another
        pygame.KEYDOWN will be sent every interval milliseconds.
        """  
        return (200, 10)
    
    def load_set(self, set_number):
        """
        Load the items of the specified set.
        - set_number: Number of the set of items.
        """        
        set_name = self.set_prefix + "s" + str(set_number).zfill(2)
        self.set_number = set_number
        self.set_name = set_name
        self.stage_name_item.set_text(set_name)
        
        # Load the current definition of the items (if exists)
        if os.path.isfile(self.get_set_file_name()):            
            item_definitions = None
        else:
            item_definitions = {}
        self.set_items(self.set_name, "", item_definitions)
        item_definitions = self.get_item_definitions()
        original_item_definitions = item_definitions.copy()
        
        # Get the default state
        default_state = None
        for state in self.states:
            if state.suffix == "":
                default_state = state
                break
        if default_state == None:
            raise Exception, "There is no default state defined"
        
        # Detect the items that are defined reading the images for the set
        self.items = []
        self.item_states = {}                 
        multiplier = self.get_grid_multiplier()
        for name in os.listdir('images'):                    
            if name.startswith(self.set_name):
                # Get the item's type
                item_type = name[len(self.set_name):]
                
                # Remove the extension
                k = item_type.rfind('.')
                if k != -1:
                    item_type = item_type[:k]                                
                
                # Check that the item type doesn't has '$'
                if item_type.rfind('$') == -1:                
                    # Check that the item's last char is a digit 
                    type_len = len(item_type)                           
                    if type_len > 0 and item_type[type_len - 1].isdigit():                    
                        if multiplier != 1:                        
                            # Scale the image (we can do these because the image is stored in a cache that then is read) 
                            image = self.load_item_image(item_type, default_state, False)
                            width, height = image.surface.get_size()
                            image.surface = pygame.transform.scale(image.surface, (width * multiplier, height * multiplier))                                                     
                                                                
                        if not item_definitions.has_key(item_type):                        
                            definition = IsoDefinition((0, 0), (1, 1), [], self.tags[0], [])
                            new_definition = True                        
                        else:                        
                            definition = item_definitions[item_type]
                            new_definition = False
                            
                            # Create a new definition to remove the states
                            definition = IsoDefinition(definition.center, definition.size, definition.place_holders, definition.tag, [])
                        
                        item_definitions[item_type] = definition                        
                            
                        # Create the item
                        item = ItemCell(self, item_type, default_state, False, 0, 0)
                                                  
                        if new_definition:          
                            # Set the default position for the item in the grid
                            center_x = (item.get_width() / multiplier) / 2
                            center_y = (item.get_height() / multiplier) / 2
                            definition.center = (center_x, center_y)                                                 
                            item.reload_definition()
                            
                        self.items.append(item)
                    else:
                        # Check if the image belongs to an item state
                        full_item_type = item_type
                        k = item_type.rfind('_')
                        if k != -1:
                            state_suffix = item_type[k + 1:]
                            item_type = item_type[:k]
                        
                            state_name = None
                            for state in self.states:
                                if state.suffix == state_suffix:
                                    item_state = state
                                    state_name = state.name
                                    break
                                
                            if state_name != None:
                                type_len = len(item_type)                            
                                if type_len > 0 and item_type[type_len - 1].isdigit():
                                    if multiplier != 1:
                                        # Scale the image (we can do these because the image is stored in a cache that then is read) 
                                        image = self.load_item_image(item_type, item_state, False)
                                        width, height = image.surface.get_size()
                                        image.surface = pygame.transform.scale(image.surface, (width * multiplier, height * multiplier))                                                     
                                    
                                    if item_type in self.item_states:
                                        states = self.item_states[item_type]
                                    else:
                                        states = []
                                        self.item_states[item_type] = states
                                        
                                    # Check if the center of the state is already defined
                                    state_center = None
                                    if original_item_definitions.has_key(item_type):
                                        definition = original_item_definitions[item_type]
                                        for state in definition.states:
                                            if state.name == state_name:
                                                state_center = state.center
                                                break
                                    if state_center == None:
                                        center_x = (item.get_width() / multiplier) / 2
                                        center_y = (item.get_height() / multiplier) / 2
                                        state_center = (center_x, center_y)
                                    
                                    # Check if there is a mask to erase part of the items
                                    # that are shown over this item and they are visible 
                                    # in this state but not in the default state            
                                    clip = os.path.exists('images/' + self.set_name + full_item_type + '$x.png')                                                            
                                    
                                    # Append the read state
                                    states.append(IsoDefState(state_name, state_center, clip))                                                                                                     
                    
        # Assign the states to the items
        for item in self.items:
            item_type = item.get_type()
            if self.item_states.has_key(item_type):
                item.get_definition().states = self.item_states[item_type]
                
        self.items.sort(None, key = ItemCell.get_type)                
                    
    def notify_set_changed(self):
        """
        This function is invoked when the items of the set changed.
        """
        self.pending_save = True
        
        # Start a timer to save the items if not changed is performed in the next 5 seconds
        self.stop_timer("auto_save")
        self.start_timer("auto_save", 5000, self.save_set, None)        
        
    def on_closed(self, stage):
        self.save_set(None, None)
        
        # Save the current state to restore it when the stage is open
        # again 
        full_name = self.get_state_file_name()
        try:                            
            file = open(full_name, 'w')
            file.write(self.set_prefix)
            file.write("\r\n")
            file.write(str(self.set_number))
            file.write("\r\n")
            file.write(str(self.item_index))
            file.write("\r\n")
            file.write(str(self.zoom))
            file.write("\r\n")
            if self.place_holders_layer.get_visible():
                file.write("1")
            else:
                file.write("0")
            file.write("\r\n")
            if self.current_item == None:
                file.write("")
            else:
                file.write(self.current_item.get_state().name)            
            file.close()
        except Exception, message:
            print 'Cannot save set designer state:', full_name
            raise SystemExit, message
                                                        
    def save_set(self, key, data):
        """
        Save the current set.
        - key: Key used in the timer to save the data.
        - data: Data.
        """        
        self.stop_timer("auto_save")
        if self.pending_save:
            self.pending_save = False
            full_name = self.get_set_file_name()
            try:                            
                file = open(full_name, 'w')
                for item in self.items:
                    file.write(item.get_type())
                    definition = item.get_definition()
                    file.write(';')
                    file.write(str(definition.center[0]))
                    file.write(';')
                    file.write(str(definition.center[1]))
                    file.write(';')
                    file.write(str(definition.size[0]))
                    file.write(';')
                    file.write(str(definition.size[1]))
                    file.write(';')                    
                    
                    first = True
                    for place_holder in definition.place_holders:
                        if first:
                            first = False
                        else:
                            file.write('|')
                        file.write(place_holder.tag)
                        file.write(',')
                        file.write(str(place_holder.x))
                        file.write(',')
                        file.write(str(place_holder.y))
                        file.write(',')
                        file.write(str(place_holder.height))
                            
                    file.write(';')
                    file.write(definition.tag)
                    file.write(';')
                    
                    first = True
                    for state in definition.states:
                        if first:
                            first = False
                        else:
                            file.write('|')
                        file.write(state.name)
                        file.write(',')
                        file.write(str(state.center[0]))
                        file.write(',')
                        file.write(str(state.center[1]))
                        file.write(',')
                        if state.clip:                  
                            file.write('1')
                        else:
                            file.write('0')
                    file.write("\r\n")
                file.close()
            except Exception, message:
                print 'Cannot save items data:', full_name
                raise SystemExit, message            
                
    def show_current_item(self, default_state_name = None):
        """        
        Show current item in the stage
        - default_state_name: Default state.
        """
        if self.current_item != None:
            self.items_layer.remove(self.current_item)
            self.current_item = None
        if len(self.items) > 0:
            self.current_item = self.items[self.item_index]                        
            self.items_layer.add(self.current_item)
            self.item_type_item.set_text(self.current_item.get_type())
            
            if default_state_name != None:    
                type = self.current_item.get_type()
                if self.item_states.has_key(type):
                    item_states = self.item_states[type]
                    valid_state = False
                    for state in item_states:
                        if state.name == default_state_name:
                            valid_state = True                                                    
                            break
                    if valid_state:          
                        default_state = None 
                        for state in self.states:
                            if state.name == default_state_name:
                                default_state = state
                                break
                        if default_state != None:
                            self.current_item.set_state(default_state)                                
        else:
            self.item_type_item.set_text("")
        self.update_place_holders()            
        self.update_item_tag()        
        self.update_grid()
        self.show_item_states()
        self.update_current_state()
    
    def show_item_states(self):
        """
        Show the valid states of the current item.
        """
        
        # Remove previous states 
        for state_item in self.state_items:
            self.options_layer.remove(state_item[1])
        
        self.state_items = []    
        if self.current_item != None:        
            text_color = (0, 0, 10)
            text_background = (241, 242, 201, 150)
            left = self.tag_name_item.get_left()
            top = self.tag_name_item.get_top() + self.tag_name_item.get_height() + 5
            width = self.tag_name_item.get_width()
            height = self.tag_name_item.get_height()
            font = self.tag_name_item.get_font()
            
            # Add default state
            default_state = None
            for state in self.states:
                if state.suffix == "":
                    default_state = state
                    break        
            if default_state != None:
                state_item = ItemRect(left, top, width, height, font, 0, default_state.name, text_color, text_background)
                self.options_layer.add(state_item)
                self.state_items.append((default_state.name, state_item))
                top += height + 5
                
            # Add the defined states for the item
            definition = self.current_item.get_definition()
            for state in definition.states:
                state_item = ItemRect(left, top, width, height, font, 0, state.name, text_color, text_background)
                self.options_layer.add(state_item)
                self.state_items.append((state.name, state_item))
                top += height + 5

    def update_current_state(self):
        """
        Update the state that is currently selected.
        """
        normal_background = (241, 242, 201, 150)
        selected_background = (248, 237, 120, 150)
        if self.current_item == None:
            current_state = None
        else:
            current_state = self.current_item.get_state()
        for state_item in self.state_items:            
            if current_state == None or state_item[0] != current_state.name:
                state_item[1].set_background(normal_background)
            else:
                state_item[1].set_background(selected_background)

    def update_item_tag(self):
        """
        Update the text that shows the tag of the current item.
        """
        if self.current_item == None:
            self.tag_name_item.set_text("")
        else:
            definition = self.current_item.get_definition()
            self.tag_name_item.set_text(definition.tag)
            
            if definition.tag in self.tags:
                index = self.tags.index(definition.tag)
                self.zindex_item.set_text("Z-index: " + str(index))
            else:
                self.zindex_item.set_text("Z-index: ")

    def get_adjusted_origin(self):
        """
        Gets the origin adjusted to shown in a better position to edit a set of items.
        """
        return (self.origin[0] / self.zoom, self.origin[1] / self.zoom)

    def handle_event(self, e):        
        if e.type == MOUSEBUTTONDOWN:
            item = self.hit_test(e.pos[0], e.pos[1])
            if item != None:
                if item.get_layer() == self.place_holders_layer:
                    if hasattr(item, "place_holder_index"):
                        self.current_place_holder = item.place_holder_index                        
                        self.move_placeholder_mode = True
                        self.update_move_placeholder_text()
                        self.update_place_holders()
                        self.update_grid()
                elif item == self.tag_name_item:
                    self.set_next_tag()
                else:
                    k = 0
                    for state_item in self.state_items:
                        if state_item[1] == item:                            
                            # Set the new state                            
                            for state in self.states:
                                if state.name == state_item[0]:
                                    new_state = state
                            self.current_item.set_state(new_state)
                            self.update_current_state()
                            self.update_place_holders()  
                            self.update_grid()                          
                            break
                        k += 1
        elif e.type == KEYDOWN:
            # Filter mod with accepted modes 
            mod = get_common_modifiers(e.mod)                                        
            if mod == pygame.KMOD_NONE:                
                if e.key == K_RETURN:
                    if self.move_placeholder_mode:
                        self.move_placeholder_mode = False
                        self.update_move_placeholder_text()
                        self.update_place_holders()
                        self.update_grid()
                if e.key == K_LEFT:                                                    
                    if self.current_item != None:
                        if self.move_placeholder_mode:                            
                            if self.place_holders_layer.get_visible():
                                definition = self.current_item.get_definition()
                                if self.current_place_holder < len(definition.place_holders):
                                    place_holder = definition.place_holders[self.current_place_holder]
                                    place_holder.x -= 1 
                                    self.update_place_holders()
                                    self.update_grid()
                                    self.notify_set_changed()
                        else:  
                            definition = self.current_item.get_definition()                        
                            current_state = self.current_item.get_state()
                            
                            if current_state.suffix == "":
                                center = definition.center
                                definition.center = (center[0] + 1, center[1])
                            else:
                                for state in definition.states:
                                    if state.name == current_state.name:
                                        center = state.center
                                        state.center = (center[0] + 1, center[1])
                                        break
                                
                            self.current_item.reload_definition()
                            self.update_place_holders()  
                            self.update_grid()                      
                            self.notify_set_changed()                            
                elif e.key == K_RIGHT:
                    if self.current_item != None:
                        if self.move_placeholder_mode:
                            if self.place_holders_layer.get_visible():
                                definition = self.current_item.get_definition()
                                if self.current_place_holder < len(definition.place_holders):
                                    place_holder = definition.place_holders[self.current_place_holder]
                                    place_holder.x += 1 
                                    self.update_place_holders()
                                    self.update_grid()
                                    self.notify_set_changed()      
                        else:
                            definition = self.current_item.get_definition()                        
                            current_state = self.current_item.get_state()
                            
                            if current_state.suffix == "":
                                center = definition.center
                                definition.center = (center[0] - 1, center[1])
                            else:
                                for state in definition.states:
                                    if state.name == current_state.name:
                                        center = state.center
                                        state.center = (center[0] - 1, center[1])
                                        break
                            
                            self.current_item.reload_definition()                        
                            self.update_place_holders()      
                            self.update_grid()                  
                            self.notify_set_changed()
                elif e.key == K_UP:
                    if self.current_item != None:
                        if self.move_placeholder_mode:
                            if self.place_holders_layer.get_visible():
                                definition = self.current_item.get_definition()
                                if self.current_place_holder < len(definition.place_holders):
                                    place_holder = definition.place_holders[self.current_place_holder]
                                    place_holder.y -= 1 
                                    self.update_place_holders()
                                    self.update_grid()
                                    self.notify_set_changed()  
                        else:
                            definition = self.current_item.get_definition()
                            current_state = self.current_item.get_state()
                            
                            if current_state.suffix == "":
                                center = definition.center
                                definition.center = (center[0], center[1] + 1)
                            else:
                                for state in definition.states:
                                    if state.name == current_state.name:
                                        center = state.center
                                        state.center = (center[0], center[1] + 1)
                                        break
                            
                            self.current_item.reload_definition()                        
                            self.update_place_holders()  
                            self.update_grid()                      
                            self.notify_set_changed()                            
                elif e.key == K_DOWN:
                    if self.current_item != None:
                        if self.move_placeholder_mode:
                            if self.place_holders_layer.get_visible():
                                definition = self.current_item.get_definition()
                                if self.current_place_holder < len(definition.place_holders):
                                    place_holder = definition.place_holders[self.current_place_holder]
                                    place_holder.y += 1 
                                    self.update_place_holders()
                                    self.update_grid()
                                    self.notify_set_changed()  
                        else:
                            definition = self.current_item.get_definition()
                            current_state = self.current_item.get_state()
                            
                            if current_state.suffix == "":
                                center = definition.center
                                definition.center = (center[0], center[1] - 1)
                            else:
                                for state in definition.states:
                                    if state.name == current_state.name:
                                        center = state.center
                                        state.center = (center[0], center[1] - 1)
                                        break
    
                            self.current_item.reload_definition()                                                
                            self.update_place_holders()
                            self.update_grid()                        
                            self.notify_set_changed()                    
                elif e.key == K_q:
                    if self.move_placeholder_mode:
                        if self.place_holders_layer.get_visible():
                            definition = self.current_item.get_definition()
                            if self.current_place_holder < len(definition.place_holders):
                                place_holder = definition.place_holders[self.current_place_holder]
                                place_holder.height += 1 
                                self.update_place_holders()
                                self.update_grid()
                                self.notify_set_changed()
                    else:
                        if self.item_index < len(self.items) - 1:
                            self.item_index += 1
                            self.current_place_holder = 0                        
                            self.show_current_item()                                                                
                elif e.key == K_a:
                    if self.move_placeholder_mode:
                        if self.place_holders_layer.get_visible():
                            definition = self.current_item.get_definition()
                            if self.current_place_holder < len(definition.place_holders):
                                place_holder = definition.place_holders[self.current_place_holder]
                                if place_holder.height > 0:
                                    place_holder.height -= 1 
                                    self.update_place_holders()
                                    self.update_grid()
                                    self.notify_set_changed()
                    else:                    
                        if self.item_index > 0:
                            self.item_index -= 1
                            self.current_place_holder = 0
                            self.show_current_item()
                elif e.key == K_t:
                    if self.move_placeholder_mode:
                        if self.place_holders_layer.get_visible():
                            self.change_place_holder_tag()
                    else:
                        self.set_next_tag()                    
                elif e.key == K_s:
                    if self.current_item.get_type() in self.item_states:
                        # Get current state 
                        current_state = self.current_item.get_state()                                        
                        item_states = self.item_states[self.current_item.get_type()]
                        k = 0  
                        state_index = -1
                        for state in item_states:
                            if state.name == current_state.name:
                                state_index = k                                                    
                                break
                            k += 1                    
                        
                        # Set the new state
                        new_state_index = state_index + 1
                        if new_state_index < len(item_states):
                            new_state_name = item_states[new_state_index].name
                            for state in self.states:
                                if state.name == new_state_name:
                                    new_state = state
                        else:
                            # Set the default state                        
                            for state in self.states:
                                if state.suffix == "":
                                    new_state = state                    
                        self.current_item.set_state(new_state)
                        self.update_current_state()
                        self.update_place_holders()   
                        self.update_grid()                             
                elif e.key == K_z:
                    if self.zoom == 2:
                        self.zoom = 1
                    else:
                        self.zoom = 2                                            
                    
                    # Update grid definition
                    definition = self.get_grid_definition()
                    cell_width = definition[1]
                    cell_height = definition[2] 
                    self.set_grid_definition(self.get_adjusted_origin(), cell_width, cell_height, self.zoom)
                    
                    # Update grid drawing
                    self.update_grid()
                    
                    # Update current set and item
                    self.save_set(None, None)
                    state = self.current_item.get_state()
                    self.load_set(self.set_number)                                          
                    self.show_current_item()            
                    self.current_item.set_state(state)
                    self.update_current_state()                        
            elif (mod == pygame.KMOD_LCTRL) or (mod == pygame.KMOD_RCTRL):
                if e.key == K_LEFT:
                    if self.current_item != None:
                        definition = self.current_item.get_definition()
                        if definition.size[1] > 1:
                            definition.size = (definition.size[0], definition.size[1] - 1)
                            self.notify_set_changed()
                            self.update_grid()
                            self.update_place_holders()
                elif e.key == K_RIGHT:
                    if self.current_item != None:
                        definition = self.current_item.get_definition()
                        definition.size = (definition.size[0], definition.size[1] + 1)
                        self.notify_set_changed()
                        self.update_grid()
                        self.update_place_holders()
                elif e.key == K_UP:
                    if self.current_item != None:
                        definition = self.current_item.get_definition()
                        if definition.size[0] > 1:
                            definition.size = (definition.size[0] - 1, definition.size[1])
                            self.notify_set_changed()
                            self.update_grid()
                            self.update_place_holders()                            
                elif e.key == K_DOWN:
                    if self.current_item != None:
                        definition = self.current_item.get_definition()
                        definition.size = (definition.size[0] + 1, definition.size[1])
                        self.notify_set_changed()
                        self.update_grid()         
                        self.update_place_holders()                       
                elif (e.key == K_PAGEUP) or (e.key == K_PAGEDOWN):
                    if not self.move_placeholder_mode:
                        # If there are pending saves perform it
                        self.save_set(None, None)
                        
                        update_set = False
                        if e.key == K_PAGEDOWN:
                            if self.set_number < 99:
                                set_number = self.set_number + 1
                                update_set = True
                        elif e.key == K_PAGEUP:
                            if self.set_number > 1:
                                set_number = self.set_number - 1
                                update_set = True                    
                        if update_set:
                            self.load_set(set_number)
                            self.item_index = 0
                            self.current_place_holder = 0                                        
                            self.show_current_item()                            
            elif (mod == pygame.KMOD_LALT) or (mod == pygame.KMOD_RALT):
                if e.key == K_n:
                    if self.current_item != None:                        
                        if self.place_holders_layer.get_visible() and \
                            len(self.place_holder_tags) > 0:
                            definition = self.current_item.get_definition()
                            definition.place_holders.append(IsoPlaceHolder(self.place_holder_tags[0], 0, 0, 0))                                                                      
                            self.current_place_holder = len(definition.place_holders) - 1                                 
                            self.move_placeholder_mode = True
                            self.update_move_placeholder_text()
                            self.update_place_holders()
                            self.update_grid()
                            self.notify_set_changed()
                elif e.key == K_m:
                    self.move_placeholder_mode = not self.move_placeholder_mode
                    self.update_move_placeholder_text()
                    self.update_place_holders()
                    self.update_grid()
                elif e.key == K_t:
                    if self.current_item != None:
                        if self.place_holders_layer.get_visible():
                            self.change_place_holder_tag()                            
                elif e.key == K_s:
                    if self.current_item != None:
                        if self.place_holders_layer.get_visible():
                            definition = self.current_item.get_definition()
                            if self.current_place_holder + 1 < len(definition.place_holders):
                                self.current_place_holder += 1
                            else:
                                self.current_place_holder = 0
                            self.update_place_holders() 
                            self.update_grid()                               
                elif e.key == K_DELETE:
                    if self.current_item != None:
                        if self.place_holders_layer.get_visible():
                            definition = self.current_item.get_definition()
                            if self.current_place_holder < len(definition.place_holders):
                                del definition.place_holders[self.current_place_holder]
                                if self.current_place_holder >= len(definition.place_holders) and self.current_place_holder > 0:
                                    self.current_place_holder -= 1                            
                                if len(definition.place_holders) == 0:                             
                                    self.move_placeholder_mode = False                                
                                    self.update_move_placeholder_text()
                                self.update_place_holders()
                                self.update_grid()
                                self.notify_set_changed()                                        
                elif e.key == K_h:
                    self.place_holders_layer.set_visible(not self.place_holders_layer.get_visible())
                                
    def change_place_holder_tag(self):
        """
        Change the tag associated with the current place holder.
        """
        definition = self.current_item.get_definition()
        if (len(self.place_holder_tags) > 0) and (self.current_place_holder < len(definition.place_holders)):
            place_holder = definition.place_holders[self.current_place_holder]
            if place_holder.tag in self.place_holder_tags:
                k = self.place_holder_tags.index(place_holder.tag)
            else:
                k = -1;
            k += 1
            if k >= len(self.place_holder_tags):
                k = 0
            place_holder.tag = self.place_holder_tags[k]  
            self.update_place_holders()
            self.notify_set_changed()
                    
    def update_move_placeholder_text(self):
        """
        Update the text that indicates if we are in "Move place holder state"
        """
        if self.move_placeholder_mode:
            self.move_placeholder_item.set_text("Move Placeholder Mode (Press Enter to exit)")
            self.move_placeholder_item.set_visible(True)                    
        else:
            self.move_placeholder_item.set_visible(False)                
    
    def set_next_tag(self):
        """
        Sets the next tag for the current item.
        """
        if len(self.tags) > 0:
            definition = self.current_item.get_definition()                        
            if definition.tag in self.tags:                         
                k = self.tags.index(definition.tag)
            else:
                k = -1
            k += 1                        
            if k >= len(self.tags):
                k = 0
            definition.tag = self.tags[k]
            self.update_item_tag()
            self.notify_set_changed()

    def update_place_holders(self):
        """
        Update the items corresponding to place holders of the current item.
        """
        self.place_holders_layer.empty()
        if self.current_item != None:
            definition = self.current_item.get_definition()
            
            if self.current_place_holder < len(definition.place_holders):
                selected_place_holder = definition.place_holders[self.current_place_holder]
            else:
                selected_place_holder = None
            
            height_index = self.place_holders_layer.get_count()
            
            index = 0
            for place_holder in definition.place_holders:
                size = 6
                
                if place_holder == selected_place_holder:
                    if not self.move_placeholder_mode:
                        text_color = (255, 255, 255)
                        height_color = (255, 255, 255, 100)
                    else:
                        text_color = (55, 255, 55)
                        height_color = (55, 255, 55, 100)
                else:
                    text_color = (140, 140, 140)
                    height_color = (255, 255, 255, 50)
                                            
                place_holder_cell = self.current_item.get_place_holder_rowcol(place_holder)                
                if place_holder_cell[0] < 0 or place_holder_cell[0] >= definition.size[0] or place_holder_cell[1] < 0 or place_holder_cell[1] >= definition.size[1]:
                    name = "[Out of Bounds]"
                else:                        
                    name = place_holder.tag                
                    
                center = self.current_item.get_center()                
                text = ItemText(self.current_item.get_left() + center[0] * self.zoom + place_holder.x * self.zoom - 3 * self.zoom, \
                    self.current_item.get_top() + center[1] * self.zoom + (place_holder.y - place_holder.height) * self.zoom - 9 - 4 * self.zoom,
                    self.font, 0, name, text_color)
                text.set_left(text.get_left() - text.get_width())
                text.place_holder_index = index
                self.place_holders_layer.add(text)
                
                mark_x = self.current_item.get_left() + center[0] * self.zoom + place_holder.x * self.zoom
                mark_y = self.current_item.get_top() + center[1] * self.zoom + (place_holder.y - place_holder.height) * self.zoom                              
                
                if place_holder.height != 0:
                    item = ItemCustomDraw(mark_x - self.zoom / 2, mark_y, self.zoom, place_holder.height * self.zoom, self.draw_place_holder_height)
                    item.place_holder_index = index
                    item.place_holder_color = height_color
                    self.place_holders_layer.add(item, height_index)                
        
                item = ItemCustomDraw(mark_x - size * self.zoom / 2, mark_y - size * self.zoom / 2, size * self.zoom, size * self.zoom, self.draw_place_holder)
                item.place_holder_index = index
                item.place_holder_color = text_color
                self.place_holders_layer.add(item)                
                
                index += 1                
                                
            
    def draw_place_holder(self, item, target):
        bounds = item.get_bounds()
        color = item.place_holder_color
        target.fill(color, Rect(bounds.left + bounds.width / 2 - 5 * self.zoom / 2, bounds.top + bounds.height / 2 - self.zoom / 2, 5 * self.zoom, self.zoom))
        target.fill(color, Rect(bounds.left + bounds.width / 2 - self.zoom / 2, bounds.top + bounds.height / 2 - 5 * self.zoom / 2, self.zoom, 5 * self.zoom))        
               
    def draw_place_holder_height(self, item, target):
        bounds = item.get_bounds()
        color = item.place_holder_color
        target.draw_line(color, (bounds[0], bounds[1]), (bounds[0], bounds[1] + bounds[3] - 1), bounds[2])
            
                                                         
class LevelDesignerStage(StageIso):
    def __init__(self, game, origin, cell_width, cell_height, grid_size, tags, place_holder_tags, states, set_prefix):
        """        
        Constructor.
        - game: Game.
        - origin: Origin.
        - cell_width: Cell's width.
        - cell_height: Cell's height.        
        - grid_size: A (rows, columns) pair with the size of the grid.
        - tags: List with possible tags.
        - place_holder_tags: List with possible tags that can be assigned to a place holder.
        - states: List with information of the possible states for the items (instance of IsoState).
        - set_prefix: Prefix of the used set.
        """    
        StageIso.__init__(self, game, tags)        

        # Prepare the grid
        self.set_grid_definition(origin, cell_width, cell_height, 1)        
        self.grid_size = grid_size        
        self.place_holder_tags = place_holder_tags
        
        # Prepare auto save
        self.pending_save = []
        self.set_closed_handler(self.on_closed)            
        
        # Add a layer to draw the grid        
        self.grid_layer = Layer()
        self.add_layer(self.grid_layer)        
        grid = create_grid(self, self.grid_size, False, None, None)                
        self.grid_layer.add(grid)                
        
        # Create options layer
        font = assets.load_font("freesansbold.ttf", 12)
        window_width, window_height = game.get_window_size()
        text_color = (0, 0, 10)
        text_background = (215, 232, 237, 150)
        name_width = 95
        self.level_name_item = ItemRect(5, window_height - 23, name_width, 18, font, 0, "", text_color, text_background)
        self.options_item = ItemRect(5 + name_width + 5, window_height - 23, window_width - name_width - 15, 18, font, 0, "", text_color, text_background)        
        self.options_layer = LayerBuffered(window_width, window_height, True)
        self.options_layer.add(self.level_name_item)
        self.options_layer.add(self.options_item)
                        
        # Restore previous state (it it was saved)
        full_name = self.get_state_file_name()
        state_loaded = False        
        if os.path.isfile(full_name):                            
            try:                            
                file = open(full_name, 'r')
                state_set_prefix = file.readline().strip()
                set_number = int(file.readline().strip())
                current_layers = file.readline().strip().split(';')
                select_layer = int(file.readline().strip())
                current_item_index = int(file.readline().strip())
                file.close()
                state_loaded = True
            except Exception, message:
                print 'Cannot read set designer state:', full_name
                raise SystemExit, message
        if not state_loaded or state_set_prefix != set_prefix:        
            # Set default options
            set_prefix = "p2"
            set_number = 1
            current_layers = []
            select_layer = 0
            current_item_index = 0
            
        # Save states
        self.states = states
        self.default_state = None
        for state in self.states:
            if state.suffix == "":
                self.default_state = state
                break
        if self.default_state == None:
            raise Exception, "There is no default state defined"
                    
        # Load the set        
        self.items = []
        self.set_prefix = set_prefix                
        self.current_item = None        
        self.load_set(set_number)
        
        # Create a layer to mark selected item
        self.selection_layer = Layer()
        self.selection_item = ItemRect(0, 0, 0, 0, None, 0, "", None, None, (200, 0, 0))
        self.selection_layer.add(self.selection_item)                
        
        # Create the item layers        
        self.item_layers = []
        self.layer_current_item = []
        self.current_layer = -1 
        for i in xrange(4):
            layer = Layer()            
            letter = chr(ord('a') + i)
            
            # Get initial selected layer
            if i < len(current_layers):
                number = int(current_layers[i * 2])
                if current_layers[i * 2 + 1] == 'H':
                    layer.set_visible(False)
            else:
                number = 1
            
            # Build level name
            name = "l" + str(number).zfill(3) + letter
        
            text_color = (0, 0, 10)
            text_background = (241, 242, 201, 150)        
            text_item = ItemRect(5, self.level_name_item.get_top() - (18 + 5) * (i + 1), name_width, 18, font, 0, "", text_color, text_background)
            self.options_layer.add(text_item)
            
            layer_tuple = self.build_layer(letter, layer, name, text_item, number)
            self.item_layers.append(layer_tuple)
            self.set_layer_text(layer_tuple)
            self.layer_current_item.append(None)
            self.add_layer(layer)            

            # Load the level items
            self.load_level(name, layer)
        
        # Add a layer to mark selected item
        self.add_layer(self.selection_layer)    

        # Select a layer                    
        self.select_layer(select_layer, current_item_index)
                
        # Show options
        self.add_layer(self.options_layer)
        self.current_options_mod = None
        self.update_options_text(None, None)
        self.start_timer("update_options", 50, self.update_options_text)                        
                                            
    def select_layer(self, layer, default_select_item = 0):
        """
        Select the specified layer.
        - layer: New selected layer number.
        - default_select_item = Index of the item to select if there weren't a previous selection.
        """
        if self.current_layer != layer:            
            # Unmark the previous selected layer
            if self.current_layer != -1:                
                self.item_layers[self.current_layer][3].set_background((241, 242, 201, 150))
                self.layer_current_item[self.current_layer] = self.current_item
        
            # Mark the new layer selected
            self.current_layer = layer    
            self.item_layers[self.current_layer][3].set_background((248, 237, 120, 150))
                            
            # Update the text with the name of the level and the current item
            self.update_current_layer(default_select_item)
            
    def set_layer_text(self, layer_tuple):
        s = "Layer " + layer_tuple[0].upper()
        if not layer_tuple[1].get_visible():
            s += " (H)"
        else:
            s += " (" + str(layer_tuple[4]) + ")"
        layer_tuple[3].set_text(s)
        
    def update_current_layer(self, default_select_item = 0):
        """
        Update the text with the name of the level and the current item.
        - default_select_item = Index of the item to select if there weren't a previous selection.
        """        
        self.level_name_item.set_text(self.set_name + self.item_layers[self.current_layer][2])
            
        # Update current item
        self.current_item = self.layer_current_item[self.current_layer]
        layer = self.item_layers[self.current_layer][1]
        if (self.current_item == None) or (not self.current_item in layer.items):            
            l = len(layer.items)
            if l > 0:
                if default_select_item < l:
                    self.current_item = layer.items[default_select_item]
                else:
                    self.current_item = layer.items[0]
            else:                   
                self.current_item = None
        self.update_current_item_selection()
    
    def update_current_item_selection(self):
        """
        Update the bounds of the rectangle that marks the current selection.
        """
        if self.current_item == None:            
            visible = False
        else:
            if self.current_layer == -1:
                visible = False
            else:
                layer_tuple = self.item_layers[self.current_layer]
                layer = layer_tuple[1]
                visible = layer.get_visible()
        if not visible:            
            self.selection_item.set_visible(False)
        else:            
            self.selection_item.set_left(self.current_item.get_left() - 2)
            self.selection_item.set_top(self.current_item.get_top() - 2)
            self.selection_item.set_width(self.current_item.get_width() + 4)
            self.selection_item.set_height(self.current_item.get_height() + 4)
            self.selection_item.set_visible(True)
    
    def build_layer(self, letter, layer, name, text_item, number):
        """
        Builds a layer tuple.
        - letter: Letter associated with the layer.
        - layer: Instance of Layer class.
        - name: Name of the layer.
        - text_item: Text item to show layer name in the stage.
        - number: Number of the selected level.
        """
        return (letter, layer, name, text_item, number)
        
    def update_options_text(self, key, data):
        """
        Update the text of the options.
        - key: Key used in the timer.
        - data: Data.        
        """
        mod = get_common_modifiers(pygame.key.get_mods())
        if mod == pygame.KMOD_NONE:
            self.options_item.set_text("N = New | Tab = Select | Q/A = Change | F - Flip | S - State | Del - Delete")
        elif (mod == pygame.KMOD_LCTRL) or (mod == pygame.KMOD_RCTRL):
            self.options_item.set_text("C/V = Copy/Paste | Up/Down = Send back/forward | Page Up/Down = Change set")
        elif (mod == pygame.KMOD_LALT) or (mod == pygame.KMOD_RALT):                              
            layer = self.item_layers[self.current_layer][1]
            if layer.get_visible():
                h_text = "Hide layer"
            else:
                h_text = "Show layer"
            self.options_item.set_text("C/V/H = Copy/Paste/" + h_text + " | Up/Down = Layer | Left/Right = Level")
        else:
            self.options_item.set_text("")
        self.current_options_mod = mod                
        
    def load_set(self, set_number):
        """
        Loads the items of the specified set.
        - set_number: Number of the set of items.
        """   
        set_name = self.set_prefix + "s" + str(set_number).zfill(2)             
        self.set_number = set_number
        self.set_name = set_name        
        
        # Load the definition of the items
        if os.path.isfile(self.get_set_file_name()):            
            item_definitions = None
        else:
            item_definitions = {}        
        self.set_items(self.set_name, "", item_definitions)
        
        # Load the list of item types        
        self.item_types = self.get_item_definitions().keys()        
        self.item_types.sort()

    def get_key_repeat(self):
        """
        Gets the key repeat configuration for the stage. Returns (delay, interval) or
        None if key repeat is disabled for the stage. The delay is the number of milliseconds 
        before the first repeated pygame.KEYDOWN will be sent. After that another
        pygame.KEYDOWN will be sent every interval milliseconds.
        """  
        return (200, 50)
        
    def get_set_file_name(self):
        return os.path.join('data', self.set_name + '.tcs')

    def get_level_file_name(self, level_name):
        return os.path.join('data', self.set_name + level_name + '.tcl')

    def get_state_file_name(self):
        return os.path.join('data', 'leveldesigner.sta')

    def load_level(self, level_name, layer):
        """
        Loads the level.
        - level_name: Level's name.
        - layer: Layer where the level is loaded.
        """
        # Load the level in the stage
        if os.path.isfile(self.get_level_file_name(level_name)):
            StageIso.load_level(self, level_name, layer, self.states, self.add_item_event_handlers)
            
            # Select last item
            l = len(layer.items)
            if l == 0:
                self.current_item = None
            else:
                self.current_item = layer.items[l - 1]
            self.update_current_item_selection()
        
    def notify_level_changed(self):
        """
        This function is invoked when the items of the set changed.
        """
        level = self.item_layers[self.current_layer]
        if not level in self.pending_save:
            self.pending_save.append(level)        
        
        # Start a timer to save the items if not changed is performed in the next 5 seconds
        self.stop_timer("auto_save")
        self.start_timer("auto_save", 5000, self.save_current_levels, None)        
        
    def on_closed(self, stage):
        self.save_current_levels(None, None)
        
        # Save the current state to restore it when the stage is open
        # again 
        full_name = self.get_state_file_name()
        try:                            
            file = open(full_name, 'w')
            file.write(self.set_prefix)
            file.write("\r\n")
            file.write(str(self.set_number))
            file.write("\r\n")
            first = True
            for layer in self.item_layers:
                if first:
                    first = False
                else:
                    file.write(';')
                file.write(str(layer[4]))
                file.write(';')
                if layer[1].get_visible():
                    file.write('V')
                else:
                    file.write('H')                
            file.write("\r\n")
            file.write(str(self.current_layer))
            file.write("\r\n")            
            if self.current_item == None:
                selected_item_index = 0
            else:
                items_layer = self.item_layers[self.current_layer][1]
                selected_item_index = items_layer.items.index(self.current_item)
                if selected_item_index == -1:
                    selected_item_index = 0
            file.write(str(selected_item_index))
            file.close()
        except Exception, message:
            print 'Cannot save set designer state:', full_name
            raise SystemExit, message
    
    def save_current_levels(self, key, data):
        """
        Save the current level.
        - key: Key used in the timer.
        - data: Data.
        """
        self.stop_timer("auto_save")          
        if len(self.pending_save) > 0:                                        
            for layer in self.pending_save:
                if len(layer[1].items) == 0:
                    # There is no items. Delete the file if exists
                    file_name = self.get_level_file_name(layer[2])                
                    if os.path.isfile(file_name):                    
                        os.remove(file_name)
                else:             
                    StageIso.save_level(self, layer[2], layer[1])
            self.pending_save = []                
    
    def handle_event(self, e):
        if e.type == MOUSEBUTTONDOWN:
            item = self.hit_test(e.pos[0], e.pos[1])
            if item != None:
                k = 0
                for layer in self.item_layers:
                    if layer[3] == item:
                        self.select_layer(k)
                    k += 1
        elif e.type == KEYDOWN:
            mod = get_common_modifiers(e.mod) 
            if mod == pygame.KMOD_NONE:
                items_layer = self.item_layers[self.current_layer][1]
                if items_layer.get_visible():
                    if e.key == K_n:
                        if len(self.item_types) > 0:                                                                        
                            new_item = self.create_item(self.item_types[0], self.default_state, False, 0, 0)                            
                            if self.current_item != None:
                                new_item.set_type(self.current_item.get_type())
                                row, col = self.current_item.get_position()
                                size = new_item.get_definition().size                                
                                if col + size[1] + 1 <= self.grid_size[1]:
                                    col += 1
                                elif row + size[0] + 1 <= self.grid_size[0]:
                                    col = 0
                                    row += 1
                                new_item.set_position(row, col)
                            items_layer = self.item_layers[self.current_layer][1]
                            items_layer.add(new_item)                        
                            self.current_item = new_item
                            self.update_current_item_selection()
                            self.notify_level_changed()                                    
                    elif e.key == K_LEFT:
                        if self.current_item != None:
                            row, col = self.current_item.get_position()                            
                            new_col = col - 1
                            if new_col >= 0:                        
                                self.current_item.set_position(row, new_col)
                                self.notify_level_changed()
                                self.update_current_item_selection()                                                                                
                    elif e.key == K_RIGHT:
                        if self.current_item != None:
                            row, col = self.current_item.get_position()
                            size = self.current_item.get_definition().size
                            new_col = col + 1                            
                            if new_col + size[1] <= self.grid_size[1]:
                                self.current_item.set_position(row, new_col)
                                self.notify_level_changed()
                                self.update_current_item_selection()
                    elif e.key == K_UP:
                        if self.current_item != None:
                            row, col = self.current_item.get_position()
                            new_row = row - 1
                            if new_row >= 0:
                                self.current_item.set_position(new_row, col)
                                self.notify_level_changed()
                                self.update_current_item_selection()                                                            
                    elif e.key == K_DOWN:
                        if self.current_item != None:
                            row, col = self.current_item.get_position()
                            size = self.current_item.get_definition().size   
                            new_row = row + 1
                            if new_row + size[0] <= self.grid_size[0]:
                                self.current_item.set_position(new_row, col)
                                self.notify_level_changed()
                                self.update_current_item_selection()
                    elif e.key == K_q:
                        if self.current_item != None:
                            k = self.item_types.index(self.current_item.get_type())
                            if (k != -1) and (k + 1 < len(self.item_types)):
                                self.current_item.set_type(self.item_types[k + 1])
                                self.notify_level_changed()
                                self.update_current_item_selection()
                    elif e.key == K_a:
                        if self.current_item != None:
                            k = self.item_types.index(self.current_item.get_type())
                            if (k != -1) and (k > 0):
                                self.current_item.set_type(self.item_types[k - 1])
                                self.notify_level_changed()
                                self.update_current_item_selection()
                    elif e.key == K_TAB:
                        if self.current_item != None:
                            items_layer = self.item_layers[self.current_layer][1]
                            k = items_layer.items.index(self.current_item)
                            l = len(items_layer.items)
                            if k + 1 < l:
                                k += 1
                            else:
                                k = 0                    
                            self.current_item = items_layer.items[k]
                            self.update_current_item_selection()
                    elif e.key == K_f:                                  
                        if self.current_item != None:
                            self.current_item.set_flip_h(not self.current_item.get_flip_h())
                            self.notify_level_changed()
                            self.update_current_item_selection()
                    elif e.key == K_s:               
                        if self.current_item != None:
                            current_state = self.current_item.get_state()
                            state_index = -1
                            states = self.current_item.get_definition().states
                            k = 0
                            for state in states:
                                if state.name == current_state.name:
                                    state_index = k
                                    break
                                k += 1
                            state_index += 1
                            if state_index >= len(states):
                                self.current_item.set_state(self.default_state)
                            else:
                                for state in self.states:
                                    if state.name == states[state_index].name:
                                        self.current_item.set_state(state)
                                        break
                                               
                    elif e.key == K_DELETE:
                        if self.current_item != None:
                            items_layer = self.item_layers[self.current_layer][1]                    
                            k = items_layer.items.index(self.current_item)                    
                            items_layer.remove(self.current_item)
                            l = len(items_layer.items)
                            if k >= l:
                                k = l - 1                    
                            if k < 0:
                                self.current_item = None
                            else:
                                self.current_item = items_layer.items[k]                                            
                            self.notify_level_changed()
                            self.update_current_item_selection()
            elif (mod == pygame.KMOD_LCTRL) or (mod == pygame.KMOD_RCTRL):
                if e.key == K_c:
                    row, col = self.current_item.get_position()
                    leveldesigner.clipboard_item = (self.current_item.get_type(), row, col, self.current_item.get_flip_h(), self.current_item.get_state())
                elif e.key == K_v:
                    if leveldesigner.clipboard_item != None:                        
                        new_item = self.create_item(leveldesigner.clipboard_item[0], leveldesigner.clipboard_item[4], leveldesigner.clipboard_item[3], leveldesigner.clipboard_item[1], leveldesigner.clipboard_item[2])
                        items_layer = self.item_layers[self.current_layer][1]
                        items_layer.add(new_item, False)
                        self.current_item = new_item
                        self.update_current_item_selection()
                        self.notify_level_changed()
                elif e.key == K_UP:
                    if self.current_item != None:
                        items_layer = self.item_layers[self.current_layer][1]
                        k = items_layer.items.index(self.current_item)
                        if k >= 1:                            
                            items_layer.remove(self.current_item)                                     
                            items_layer.add(self.current_item, k - 1)
                            self.notify_level_changed()
                            self.update_current_item_selection()                
                
                elif e.key == K_DOWN:
                    if self.current_item != None:
                        items_layer = self.item_layers[self.current_layer][1]
                        k = items_layer.items.index(self.current_item)
                        l = len(items_layer.items)                        
                        if k + 1 < l:                            
                            items_layer.remove(self.current_item)                                     
                            items_layer.add(self.current_item, k + 1)
                            self.notify_level_changed()
                            self.update_current_item_selection()
                elif (e.key == K_PAGEUP) or (e.key == K_PAGEDOWN):                    
                    # If there are pending saves perform it
                    self.save_current_levels(None, None)
                    
                    update_set = False
                    if e.key == K_PAGEDOWN:
                        if self.set_number < 99:
                            set_number = self.set_number + 1
                            update_set = True
                    elif e.key == K_PAGEUP:
                        if self.set_number > 1:
                            set_number = self.set_number - 1
                            update_set = True                    
                    if update_set:                        
                        self.load_set(set_number)
                        for layer in self.item_layers:
                            layer[1].empty()
                            self.load_level(layer[2], layer[1])
                        self.item_index = 0     
                        layer = self.item_layers[self.current_layer][1]
                        l = len(layer.items)
                        if l > 0:
                            self.current_item = layer.items[0]
                        else:
                            self.current_item = None                                                                        
                        self.update_current_layer()                        
                        self.update_current_item_selection()
                        
            elif (mod == pygame.KMOD_LALT) or (mod == pygame.KMOD_RALT):
                if e.key == K_c:
                    layer = self.item_layers[self.current_layer][1]
                    leveldesigner.clipboard_layer = []
                    for item in layer.items:
                        row, col = item.get_position()                     
                        leveldesigner.clipboard_layer.append((item.get_type(), row, col, item.get_flip_h(), item.get_state()))                                            
                elif e.key == K_v:
                    if leveldesigner.clipboard_layer != None:
                        # Add the items that are in the layer clipboard
                        items_layer = self.item_layers[self.current_layer][1]
                        for item in leveldesigner.clipboard_layer:
                            # Check if there is already an item with the same data
                            exists = False
                            for current_item in items_layer.items:
                                row, col = current_item.get_position()
                                if (current_item.get_type() == item[0]) and (row == item[1]) and (row == item[1]):
                                    exists = True       
                            
                            if not exists:
                                new_item = self.create_item(item[0], item[4], item[3], item[1], item[2])
                                items_layer.add(new_item)
                                self.current_item = new_item
                        self.update_current_item_selection()
                        self.notify_level_changed()     
                elif e.key == K_h:
                    layer_tuple = self.item_layers[self.current_layer]
                    layer = layer_tuple[1]
                    layer.set_visible(not layer.get_visible())
                    self.set_layer_text(layer_tuple)
                    self.update_current_item_selection()        
                elif e.key == K_UP:
                    if self.current_layer + 1 < len(self.item_layers):
                        self.select_layer(self.current_layer + 1)                        
                elif e.key == K_DOWN:
                    if self.current_layer > 0:
                        self.select_layer(self.current_layer - 1)                        
                elif (e.key == K_LEFT) or (e.key == K_RIGHT):
                    layer = self.item_layers[self.current_layer]
                    number = layer[4]
                    
                    update_layer = False
                    if e.key == K_LEFT:
                        if number > 1:                        
                            number -= 1
                            update_layer = True
                    else:
                        if number < 999:
                            number += 1
                            update_layer = True
                    
                    if update_layer:
                        # If there are pending saves perform it
                        self.save_current_levels(None, None)
                    
                        # Update layer data
                        name = "l" + str(number).zfill(3) + layer[0]                        
                        layer = self.build_layer(layer[0], layer[1], name, layer[3], number)                        
                        self.item_layers[self.current_layer] = layer
                        
                        # Load layer items
                        layer[1].empty()                        
                        self.load_level(name, layer[1])                        
                        
                        # Update current layer
                        self.update_current_layer()             
                        self.update_current_item_selection()     
                        self.set_layer_text(layer)                          

    def create_item(self, type, state, flip_h = False, row = -999, col = -999):
        """
        Creates a new item.
        - stage: Stage where the item is shown (must be an instance of StageIso).
        - type: Item's type (the type must be present in the stage items' data). 
        - state: Initial state for the item (an instance of IsoState).
        - flip_h: Indicates if the item is flipped horizontaly.
        - row: Row where the item is located. -999 if the position must be defined later.
        - col: Column where the item is located. -999 if the position must be defined later.        
        """
        item = ItemCell(self, type, state, flip_h, row, col)    
        self.add_item_event_handlers(item)
        
        return item
    
    def add_item_event_handlers(self, item):
        """
        Add the event handlers for the item.
        """
        item.add_event_handler(ItemEvent.CLICK, self.item_click)
        item.add_event_handler(ItemEvent.DBLCLICK, self.item_dblclick)    
    
    def item_click(self, item, args):
        """        
        This function is invoked when user clicks in an item.
        """   
        item_layer = item.get_layer()
        item_layer_index = -1
        k = 0
        for layer in self.item_layers:
            if layer[1] == item_layer:
                item_layer_index = k
            k += 1
        if item_layer_index != -1:
            self.select_layer(item_layer_index)                    
            self.current_item = item
            self.notify_level_changed()
            self.update_current_item_selection()
            
    def item_dblclick(self, item, args):
        """        
        This function is invoked when user clicks in an item.
        """           
        # Go to the set designer with the item type selected
        definition = self.get_grid_definition()
        origin = definition[0]
        cell_width = definition[1]
        cell_height = definition[2] 
        setitems_stage = leveldesigner.SetItemsStage(self.game, origin, cell_width, cell_height, self.grid_size, self.get_tags(), self.place_holder_tags, self.states, self.set_prefix)                                                   
        setitems_stage.select_item_type(item.get_type()) 
        self.game.set_stage(setitems_stage)        
        
def get_common_modifiers(mod):
    """
    Applied a filter to the specified modifier and return only the standards modifier that
    are active.
    - mod: Modifiers 
    """
    return mod & (pygame.KMOD_LCTRL | pygame.KMOD_RCTRL | pygame.KMOD_LALT | pygame.KMOD_RALT | pygame.KMOD_LSHIFT | pygame.KMOD_RSHIFT)    
                            
def create_grid(stage, grid_size, mark_center, mark_size, mark_cell):
    """
    Create an image with the grid.
    - grid_size: A (rows, columns) pair with the size of the grid.
    - mark_center: Indicates if the center of the cell (0, 0) should be marked.
    - mark_size: Indicates if must draw a rectangle to mark the size in the set designer.
        Specify a (rows, columns) pair to mark the size, use None otherwise.
    - mark_cell: Indicate if must draw a rectangle to mark the specified cell, use None otherwise. 
    """
    definition = stage.get_grid_definition()
    origin = definition[0]
    multiplier = definition[3] 
    grid = ItemImage(0, origin[1] * multiplier, draw_grid(stage, grid_size, mark_center, mark_size, mark_cell))
    
    return grid
            
def draw_grid(stage, grid_size, mark_center, mark_size, mark_cell):
    """    
    Draws the grid of the isometric stage over an image and returns it.
    - grid_size: A (rows, columns) pair with the size of the grid.
    - mark_center: Indicates if the center of the cell (0, 0) should be marked.
    - mark_size: Indicates if must draw a rectangle to mark the size in the set designer.
        Specify a (rows, columns) pair to mark the size, use None otherwise.
    - mark_cell: Indicate if must draw a rectangle to mark the specified cell, use None otherwise.     
    """
    
    width, height = stage.game.get_window_size()
    origin, cell_width, cell_height, multiplier = stage.get_grid_definition()
    grid_definition = (origin, cell_width, cell_height, multiplier)
    
    grid_height = height - origin[1] * multiplier
    target = CustomDraw(width, grid_height)
    target.clear((0, 0, 0, 0))
    
    # Draw the grid lines    
    grid_color = (255, 255, 255, 50)    
    start_pos = get_grid_pos(0, 0, grid_definition)
    end_pos = get_grid_pos(grid_size[0], 0, grid_definition)
    col = 0        
    while col <= grid_size[1]:              
        target.draw_line(grid_color, start_pos, end_pos)
        col += 1
        start_pos = get_grid_pos(0, col, grid_definition)
        end_pos = get_grid_pos(grid_size[0], col, grid_definition)        
    
    start_pos = get_grid_pos(0, 0, grid_definition)
    end_pos = get_grid_pos(0, grid_size[1], grid_definition)    
    row = 0        
    while row <= grid_size[0]:              
        target.draw_line(grid_color, start_pos, end_pos)
        row += 1
        start_pos = get_grid_pos(row, 0, grid_definition)
        end_pos = get_grid_pos(row, grid_size[1], grid_definition)        
             
    if mark_center:
        # Mark the origin cell center
        mark_color = (255, 0, 0, 200)
        target.fill(mark_color, (origin[0] * multiplier - 5 * multiplier / 2, cell_height * multiplier / 2 - multiplier / 2, 5 * multiplier, multiplier))
        target.fill(mark_color, (origin[0] * multiplier - multiplier / 2, cell_height * multiplier / 2 - 5 * multiplier / 2, multiplier, 5 * multiplier))
        
    if mark_size != None:
        # Draw a rectangle to mark the size of an item        
        size_color = (255, 255, 0, 150)
        start_pos = get_grid_pos(0, 0, grid_definition)    
        end_pos = get_grid_pos(mark_size[0], 0, grid_definition)
        target.draw_line(size_color, start_pos, end_pos)
        start_pos = get_grid_pos(0, mark_size[1], grid_definition)    
        end_pos = get_grid_pos(mark_size[0], mark_size[1], grid_definition)
        target.draw_line(size_color, start_pos, end_pos)        
        start_pos = get_grid_pos(0, 0, grid_definition)    
        end_pos = get_grid_pos(0, mark_size[1], grid_definition)
        target.draw_line(size_color, start_pos, end_pos)
        start_pos = get_grid_pos(mark_size[0], 0, grid_definition)    
        end_pos = get_grid_pos(mark_size[0], mark_size[1], grid_definition)
        target.draw_line(size_color, start_pos, end_pos)
    
    if mark_cell != None:
        # Draw a rectangle to mark the size of an item        
        cell_color = (255, 0, 0, 150)
        start_pos = get_grid_pos(mark_cell[0], mark_cell[1], grid_definition)    
        end_pos = get_grid_pos(mark_cell[0] + 1, mark_cell[1], grid_definition)
        target.draw_line(cell_color, start_pos, end_pos, 3)
        start_pos = get_grid_pos(mark_cell[0], mark_cell[1] + 1, grid_definition)    
        end_pos = get_grid_pos(mark_cell[0] + 1, mark_cell[1] + 1, grid_definition)
        target.draw_line(cell_color, start_pos, end_pos, 3)        
        start_pos = get_grid_pos(mark_cell[0], mark_cell[1], grid_definition)    
        end_pos = get_grid_pos(mark_cell[0], mark_cell[1] + 1, grid_definition)
        target.draw_line(cell_color, start_pos, end_pos, 3)
        start_pos = get_grid_pos(mark_cell[0] + 1, mark_cell[1], grid_definition)    
        end_pos = get_grid_pos(mark_cell[0] + 1, mark_cell[1] + 1, grid_definition)
        target.draw_line(cell_color, start_pos, end_pos, 3)
                            
    return assets.Image(target.surface)

def get_grid_pos(row, col, grid_definition):
    """    
    Calculates the position of a vertex in the grid.
    - row: Row.
    - col: Column.
    """
    origin = grid_definition[0]
    cell_width = grid_definition[1]
    cell_height = grid_definition[2]
    multiplier = grid_definition[3]
    
    x = origin[0] * multiplier + ((col - row) * cell_width * multiplier) / 2
    y = 1 + ((row + col) * cell_height * multiplier) / 2
    
    return x, y
    