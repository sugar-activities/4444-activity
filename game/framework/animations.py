# -*- coding: latin-1 -*-

# 2011 - Dirección General Impositiva, Uruguay.
# Todos los derechos reservados.
# All rights reserved.

import stage, assets
from stage import ItemImage
import math
import pygame
import sys
import animations

WAIT_ORDINAL = 1

def fade_in_item(item, duration = 500, callback = None, to_alpha = 255):
    """    
    Perform a fade in animation to show an item.
    - item: Item.
    - duration: Duration in milliseconds of the fade in animation.
    - callback: Function that is invoked with parameter item when the animation is completed. None
      there is no callback function. 
    - to_alpha: Final alpha value for the fade. 
    """
    stage = __get_item_stage(item)
    
    key = (item, "fade")
    milliseconds = 20
    
    if item.get_alpha() == 255:
        item.set_alpha(0)
    
    # If a fade timer was already started for the item, stop it
    stage.stop_timer(key)
    
    # Start the timer        
    data = [pygame.time.get_ticks(), None, duration, to_alpha, callback, stage]
    stage.start_timer(key, milliseconds, __timer_fade_in_item, data, True, True)

def fade_out_item(item, remove, duration = 500, callback = None):
    """    
    Perform a fade out animation to hide an item.
    - item: Item.
    - remove: True if the item will be removed at the end of the fade-out. False otherwise.
    - duration: Duration in milliseconds of the fade in animation.
    - callback: Function that is invoked with parameter item when the animation is completed. None
      there is no callback function.     
    """
    stage = __get_item_stage(item)
    
    key = (item, "fade")
    milliseconds = 20
    
    # If a fade timer was already started for the item, stop it
    stage.stop_timer(key)
    
    # Hide the rollover if there is a rollover over the item
    item.hide_rollover()
    
    # Start the timer
    data = [pygame.time.get_ticks(), None, duration, remove, callback, stage]
    stage.start_timer(key, milliseconds, __timer_fade_out_item, data, True, True)

def fade_in_layer(layer, duration = 500, callback = None):
    """    
    Perform a fade in animation to show the items of a layer.
    - layer: Layer.
    - duration: Duration in milliseconds of the fade in animation.
    - callback: Function that is invoked with parameter layer when the animation is completed. None
      there is no callback function. 
    """
    stage = __get_layer_stage(layer)
    
    if layer.get_alpha() == 255:
        layer.set_alpha(0)
    
    key = (layer, "fade")
    milliseconds = 20
    
    # If a fade timer was already started for the item, stop it
    stage.stop_timer(key)
    
    # Start the timer    
    data = [pygame.time.get_ticks(), None, duration, callback, stage]
    stage.start_timer(key, milliseconds, __timer_fade_in_layer, data, True, True)

def fade_out_layer(layer, duration = 500, callback = None):
    """    
    Perform a fade out animation to hide the items of a layer.
    - layer: Layer.    
    - duration: Duration in milliseconds of the fade in animation.
    - callback: Function that is invoked with parameter layer when the animation is completed. None
      there is no callback function.     
    """
    stage = __get_layer_stage(layer)
    
    key = (layer, "fade")
    milliseconds = 20
    
    # If a fade timer was already started for the item, stop it
    stage.stop_timer(key)
    
    # Start the timer
    data = [pygame.time.get_ticks(), None, duration, callback, stage]
    stage.start_timer(key, milliseconds, __timer_fade_out_layer, data, True, True)
    
def start_image_sequence(item_image, images, fps, loops = 0, callback = None):
    """
    Starts an animation showing a sequence of images through an ItemImage.
    - item_image: An instance of ItemImage, the images are assigned to this item.
    - images: Images (must be instances of assets.Image)
    - fps: Frames per seconds. Define the speed of the animation.
    - loops: Number of times that the sequence is repeated (0 to show the sequence only once). -1
      to repeat the image sequences indefinitely.
    - callback: Function that is invoked with parameter item_image when the animation is completed. None
      there is no callback function.     
      
    If there is already an image sequence started over the item it is stopped before start this animation. 
    """
    stage = __get_item_stage(item_image)        
    
    # If a image sequence timer was already started for the item, stop it
    key = (item_image, "image_sequence")
    stage.stop_timer(key)
    
    # Start the timer
    milliseconds = 1000 / fps
    stage.start_timer(key, milliseconds, __timer_image_sequence, [0, images, loops, callback, stage])
        
def stop_image_sequence(item_image):
    """
    Stops an image sequence animation started over the specified item.
    - item_image: Item.
    
    Return current image in the sequence.
    """
    stage = __get_item_stage(item_image)    
    item_data = stage.stop_timer((item_image, "image_sequence"))
    if item_data == None:
        return 0
    else:
        return item_data[0]

def start_move(item, left, top, duration, acceleration = None, move_marks = None, callback = None):
    """
    Starts an animation that moves the specified item in a straight line to 
    the specified position.
    - item: Item.
    - left: Target left.
    - top: Target top.
    - duration: Duration in milliseconds of the move animation.
    - acceleration: Acceleration. It use a sinusoidal function to calculate
          the displacement as time pass. A pair with (maxvel_t, maxvel_dist, tension)
          should be passed in this parameter to control the movement, where:       
          * maxvel_t: Value between 0 and 1 that indicate the percentage of the
              time of the point with the higher velocity. If you indicate 
              0.5 the maximum velocity will be reached in the middle of the
              movement.
          * maxvel_dist: Value between 0 and 1 that indicate the percentage of the
             distance that is traveled at maxvel_t. 
          * tension: Indicate how curved is the movement, it is power that is 
              applied to the sine function. If it is 1 the movement is a 
              sinusoidal function. Values less than 1 indicate a movement more
              closer to an uniform movement, and values greater that 1 indicates
              a more accelerated displacement.
              
        Use None to generate a uniform move.
    - move_marks: An instance of MoveMarks. Define an image that is repeated to mark the path traveled.
      None to don't print move marks.
    - callback: Function that is invoked with parameter item when the animation is completed. None
      there is no callback function.     
    """ 
    stage = __get_item_stage(item)        
    
    # If a move timer is already started for the item, stop it
    key = (item, "move")
    milliseconds = 20
    stage.stop_timer(key)    
    
    item_left = item.get_left()
    item_top = item.get_top()    
    
    # Initialize the move marks data    
    if move_marks == None:    
        move_marks_data = None
    else:
        angle = math.atan2(top - item_top, left - item_left)
        dx_per_mark = math.cos(angle) * move_marks.separation
        dy_per_mark = math.sin(angle) * move_marks.separation
        if abs(dx_per_mark) < 1 and abs(dy_per_mark) < 1:
            move_marks_data = None
        else:
            mark_image_dx = item.get_width() / 2 - move_marks.mark_image.get_width() / 2
            mark_image_dy = item.get_height() / 2 - move_marks.mark_image.get_height() / 2
            move_marks_data = [item_left - dx_per_mark, item_top - dy_per_mark, dx_per_mark, dy_per_mark, mark_image_dx, mark_image_dy]
                    
    # Start the timer
    data = [None, duration, item_left, item_top, left, top, acceleration, move_marks, move_marks_data, callback, stage]        
    stage.start_timer(key, milliseconds, __timer_move, data, True, True)

def remove_move_marks(item):
    """
    Remove the move marks printed for the specified items with move animations.
    - item: Item.
    """
    layer = item.get_layer()
    if layer != None:
        items_to_remove = []        
        for i in layer.items:
            if isinstance(i, ItemImage):
                if hasattr(i, "move_mark_item"):
                    if i.move_mark_item == item:
                        # The image is a move mark associated with 'item'. Add to remove it (we cannot
                        # remove it here because is will unsycn the iterator)                        
                        items_to_remove.append(i)
                        
        # Remove the marks
        for i in items_to_remove:
            layer.remove(i)     
    
def stop_move(item):
    """
    Stops a move animation started over the specified item.
    - item_image: Item.
    """
    stage = __get_item_stage(item)    
    stage.stop_timer((item, "move"))

def start_resize(item_image, image, from_size, to_size, duration, origin_type = 1, callback = None):
    """
    Start a resize animation on the specified ItemImage.
    - item: ItemImage to resize.
    - image: Image that is resized an assigned to the ItemImage.
    - from_size: Initial size specified as (width, height).
    - to_size: Final size specified as (width, height).
    - origin_type: Origin. Possible values:
        0 - Left X, Left Y.
        1 - Center X, Center Y.
    - callback: Function that is invoked with parameter item when the animation is completed. None
      there is no callback function.     
    """
    stage = __get_item_stage(item_image)        
    
    # If a move timer is already started for the item, stop it
    key = (item_image, "resize")
    milliseconds = 20
    stage.stop_timer(key)    
    
    # Set the initial size
    resized_image = assets.Image(pygame.transform.smoothscale(image.surface, (int(from_size[0]), int(from_size[1]))))
    item_image.set_image(resized_image) 
    
    if origin_type == 1:
        orgin_pos = (item_image.get_left() + item_image.get_width() / 2, item_image.get_top() + item_image.get_height() / 2)
    else:
        orgin_pos = None
    
    # Start the timer    
    data = [None, image, duration, origin_type, orgin_pos, from_size, to_size, callback, stage]        
    stage.start_timer(key, milliseconds, __timer_resize, data, True, True)    

def stop_resize(item_image):
    """
    Stops a resize animation started over the specified item.
    - item_image: Item.
    """
    stage = __get_item_stage(item_image)    
    stage.stop_timer((item_image, "resize"))

def wait(stage, milliseconds, callback):
    """
    Waits the specified time and invoke the callback.
    - stage: Stage.
    - milliseconds: Number of milliseconds to wait.
    - callback: Function to invoke (without parameters).
    
    Return the wait's timer key. It can be used to cancel the wait using the
    cancel_wait function.    
    """    
    key = ("wait", animations.WAIT_ORDINAL)
    stage.start_timer(key, milliseconds, __timer_wait, (stage, callback))
    animations.WAIT_ORDINAL += 1
    if animations.WAIT_ORDINAL == 99999:
        animations.WAIT_ORDINAL = 1
        
    return key

def wait_locked(stage, milliseconds, callback):
    """
    Waits the specified time and invoke the callback. While the game waits
    for the specified time the interface is locked and cannot receive mouse
    or other events.
    - stage: Stage.
    - milliseconds: Number of milliseconds to wait.
    - callback: Function to invoke (without parameters).
    
    Return the wait's timer key. It can be used to cancel the wait using the
    cancel_wait function.
    """
    stage.lock_ui()
    key = ("wait_locked", animations.WAIT_ORDINAL)
    stage.start_timer(key, milliseconds, __timer_wait_locked, (stage, callback))
    animations.WAIT_ORDINAL += 1
    if animations.WAIT_ORDINAL == 99999:
        animations.WAIT_ORDINAL = 1
        
    return key
    
def cancel_wait(stage, key):
    """
    Cancel a wait to avoid invoke the wait's function.
    - stage: Stage.
    - key: Key returned by the wait operation that must be canceled.
    """
    stage.stop_timer(key)
    
def stop_blind_layer(layer):
    """
    If there is a blind effect being applied over the specified layer, stop the
    effect and set the final state in the layer.
    - layer: Layer.
    """
    stage = __get_layer_stage(layer)
    
    key = (layer, "blind")
    data = stage.stop_timer(key)
    if data != None:
        if data[9]:
            # There was an effect that was locking the UI, unlock it 
            stage.unlock_ui()

        direction = data[1]    
        if direction == BlindDirection.SHOW_UP or direction == BlindDirection.SHOW_DOWN:
            layer.set_clip(None)                
        elif direction == BlindDirection.HIDE_UP or direction == BlindDirection.HIDE_DOWN:
            clip = pygame.Rect(0, data[5], data[3], data[6])    
            layer.set_clip(clip)
        
                
def blind_layer(layer, direction, area, duration = 450, callback = None, lock_ui = True):
    """
    Apply a blind effect to show or hide the specified layer.
    - layer: Layer.
    - direction: A value of BlindDirection that indicate the direction of the blind effect.
    - area: Area where the blind effect is applied. None to cross the entire screen. A smaller
      rectangle indicate the the blind only must cross the zone defined in the rectangle.
    - duration: Duration in milliseconds of the blind effect to cross the full screen.
      If you specify an area the duration could be smaller, because it could
      not cross the full screen. This behavior is defined to give consistency
      with the default time if you apply the effect over areas with different
      sizes. 
    - callback: Function to invoke with parameter Layer when the blind effect ends.
        None if there is no callback function.
    - lock_ui: Indicates if must lock the UI while performing the effect
    """
    stage = __get_layer_stage(layer)
    
    key = (layer, "blind")
    milliseconds = 20
    
    # Create the effect data, if there is a blind effect in progress stop
    # the effect and apply this effect from the previous position    
    data = stage.stop_timer(key)        
    window_width, window_height = stage.game.get_window_size()    
    dy_factor = float(window_height) / duration

    if data != None and data[9]:
        # There was an effect that was locking the UI, unlock it 
        stage.unlock_ui()
    
    if data != None and data[1] == direction and data[0] != None:
        # There is already an effect applied over the layer with
        # the same direction. Replace the callback and continue 
        # with the effect            
        data[7] = callback        
    else:
        if direction == BlindDirection.SHOW_UP or \
          direction == BlindDirection.SHOW_DOWN:        
            if direction == BlindDirection.SHOW_DOWN:
                if area == None:
                    current_top = 0
                else:
                    current_top = area.top
            else:
                if area == None:
                    current_top = window_height
                else:
                    current_top = area.top + area.height
            current_height = 0            
            layer.set_clip(pygame.Rect(0, current_top, window_width, 0))        
        elif direction == BlindDirection.HIDE_UP or \
          direction == BlindDirection.HIDE_DOWN:
            hidden = False
            if not layer.get_visible():
                hidden = True
            else:
                clip = layer.get_clip()
                if clip != None and (clip.width == 0 or clip.height == 0):
                    hidden = True
                          
            if hidden:
                # It is already hidden, don't apply the effect
                if callback != None:
                    callback(layer)
                return
            else:
                if area == None:
                    current_top = 0                        
                    current_height = window_height
                else:
                    current_top = area.top         
                    current_height = area.height                    
                layer.set_clip(None)            
                    
        data = [None, direction, dy_factor, window_width, window_height, current_top, current_height, callback, stage, lock_ui]
        
    if lock_ui:
        # Lock the UI while performing the effect
        stage.lock_ui()
    
    # Start the timer            
    stage.start_timer(key, milliseconds, __timer_blind_layer, data, True, True)    

def cancel_blind_layer(stage, layer, show):
    """
    Cancel a blind effect over the specified layer.
    - stage: Stage.
    - layer: Layer.
    - show: True to show the full layer, False to hide the layer.
    """
    key = (layer, "blind")        
    stage.stop_timer(key)
    
    if show:
        layer.set_clip(None)
    else:
        layer.set_clip(pygame.Rect(0, 0, 0, 0))        
    
def is_applying_blind(stage, layer):
    """
    Determines if is a blind effect is being applied over the specified layer.
    - stage: Stage of the layer.
    - layer: Layer which the effect is being applied.
    """
    key = (layer, "blind")
    return stage.is_timer_started(key)
    
class BlindDirection:
    """
    Direction in which a blind direction can be applied.
    """
    SHOW_UP = 0
    SHOW_DOWN = 1        
    HIDE_UP = 2
    HIDE_DOWN = 3   
       
            
class MoveMarks:
    """
    Allows to define an image that is repeated in a move animation to mark the path traveled.
    """
    def __init__(self, mark_image, separation):
        """
        Constructor.
        - mark_image: Image that is repeated in the path (an instance of assets.Image)
        - separation: Separation per mark.
        """
        self.mark_image = mark_image
        self.separation = separation
    
def __get_item_stage(item):
    """
    Returns the stage of the specified item.
    - item: Item.
    """
    layer = item.get_layer()
    if layer == None:
        raise Exception, "The item must be part of a layer"        
    stage = layer.get_stage()
    if stage == None:
        raise Exception, "The item's layer must be part of a stage"            
    
    return stage

def __get_layer_stage(layer):
    """
    Returns the stage of the specified layer.
    - layer: Layer.
    """
    stage = layer.get_stage()
    if stage == None:
        raise Exception, "The layer must be part of a stage"            
    
    return stage
    
def __timer_fade_in_item(key, data):
    """    
    This function is invoked by a timer to perform an step of a fade in animation over an item.
    - key: Timer's key.
    - data: Timer's data.    
    """
    item = key[0]
    
    # Calculate the increment based on the elapsed time
    now = pygame.time.get_ticks()
    if data[1] == None:        
        elapsed_time = min(0, now - data[0])
    else:    
        elapsed_time = now - data[1]
    data[1] = now    
    to_alpha = data[3]
    increment = to_alpha * (float(elapsed_time) / data[2]) 
    
    # Apply the increment
    alpha = item.get_alpha()
    alpha += increment
    if alpha < to_alpha:
        item.set_alpha(alpha)
    else:
        item.set_alpha(to_alpha)                
        stage = data[5]
        stage.stop_timer(key)
        
        callback = data[4]
        if callback != None:             
            callback(item)    
    
def __timer_fade_out_item(key, data):
    """    
    This function is invoked by a timer to perform an step of a fade out animation over an item.
    - key: Timer's key.
    - data: Timer's data.    
    """    
    item = key[0]
    
    # Calculate the decrement based on the elapsed time
    now = pygame.time.get_ticks()
    if data[1] == None:
        elapsed_time = min(0, now - data[0])
    else:    
        elapsed_time = now - data[1]
    data[1] = now                
    decrement = 255 * (float(elapsed_time) / data[2])    
    
    # Apply the decrement
    alpha = item.get_alpha()
    alpha -= decrement
    if alpha >= 0:
        item.set_alpha(alpha)
    else:
        item.set_alpha(0)                
        layer = item.get_layer()
        if data[3] and layer != None:
            layer.remove(item)
        stage = data[5] 
        stage.stop_timer(key)
        
        callback = data[4]
        if callback != None:
            callback(item)        

def __timer_fade_in_layer(key, data):
    """    
    This function is invoked by a timer to perform an step of a fade in animation over a layer.
    - key: Timer's key.
    - data: Timer's data.    
    """
    layer = key[0]
    
    # Calculate the increment based on the elapsed time
    now = pygame.time.get_ticks()
    if data[1] == None:        
        elapsed_time = min(0, now - data[0])
    else:    
        elapsed_time = now - data[1]
    data[1] = now    
    increment = 255 * (float(elapsed_time) / data[2]) 
    
    # Apply the increment
    alpha = layer.get_alpha()
    alpha += increment
    if alpha < 255:
        layer.set_alpha(alpha)
    else:
        layer.set_alpha(255)
        stage = data[4]                
        stage.stop_timer(key)
        
        callback = data[3]
        if callback != None:
            callback(layer)    
    
def __timer_fade_out_layer(key, data):
    """    
    This function is invoked by a timer to perform an step of a fade out animation over a layer.
    - key: Timer's key.
    - data: Timer's data.    
    """    
    layer = key[0]
    
    # Calculate the decrement based on the elapsed time
    now = pygame.time.get_ticks()
    if data[1] == None:
        elapsed_time = min(0, now - data[0])
    else:    
        elapsed_time = now - data[1]
    data[1] = now                
    decrement = 255 * (float(elapsed_time) / data[2])    
    
    # Apply the decrement
    alpha = layer.get_alpha()    
    alpha -= decrement
    if alpha >= 0:       
        layer.set_alpha(alpha)
    else:
        layer.set_alpha(0)
        stage = data[4]         
        stage.stop_timer(key)
        
        callback = data[3]
        if callback != None:
            callback(layer)        
    
def __timer_image_sequence(key, data):
    """    
    This function is invoked by a timer to perform an step of a image sequence animation.
    - key: Timer's key.
    - data: Timer's data.    
    """    
    item = key[0]    
    images = data[1]

    # Set the new image in the item
    if len(images) > 0:
        item.set_image(images[data[0]])        
    
    # Update the index
    data[0] += 1
    if data[0] >= len(images):        
        data[0] = 0
                   
        # Update the loops                 
        if data[2] != -1:
            data[2] -= 1
            if data[2] < 0:
                # There are no more loops left, the animation must be stopped
                stage = data[4]
                stage.stop_timer(key)
                        
                callback = data[3]
                if callback != None:
                    callback(item)

def __timer_move(key, data):
    """    
    This function is invoked by a timer to perform an step of a move animation.
    - key: Timer's key.
    - data: Timer's data.    
    """
    item = key[0]
            
    # Calculate the the elapsed time
    now = pygame.time.get_ticks()
    if data[0] == None:
        elapsed_time = 0
        data[0] = now
    else:    
        elapsed_time = now - data[0]    
    
    # Get the move data
    duration = data[1]
    left_from = data[2]
    top_from = data[3]
    left_to = data[4]
    top_to = data[5]
    acceleration = data[6]
            
    # Calculate the displacement
    percentage = min(1, (float(elapsed_time) / duration))    
    if acceleration == None:
        dx = (left_to - left_from) * percentage
        dy = (top_to - top_from) * percentage
    else:
        # Apply the acceleration if it was indicated
        maxvel_t, maxvel_dist, tension = acceleration
        if percentage <= maxvel_t:
            factor = (math.cos(percentage / maxvel_t * math.pi / 2 - math.pi) + 1)
            factor = math.pow(factor, tension) * maxvel_dist
        else:
            factor = (math.cos((percentage - maxvel_t) / (1 - maxvel_t) * math.pi / 2 - math.pi / 2) + 1) - 1
            factor = math.pow(factor, tension) * (1 - maxvel_dist) + maxvel_dist
        dx = (left_to - left_from) * factor
        dy = (top_to - top_from) * factor        
                
    # Calculate the new position      
    new_left = left_from + dx
    new_top = top_from + dy
    
    # Update the position in the item
    item.set_left(new_left)
    item.set_top(new_top)
    
    # Check if must define move marks
    move_marks = data[7]
    if move_marks != None:        
        marks_data = data[8]
        
        last_mark_left = marks_data[0]
        last_mark_top = marks_data[1]
        dx_per_mark = marks_data[2]
        dy_per_mark = marks_data[3]
        
        # Check if must define a new mark        
        while ((((dx_per_mark > 0) and (last_mark_left + dx_per_mark < new_left)) or \
               ((dx_per_mark < 0) and (last_mark_left + dx_per_mark > new_left))) and \
              (((dy_per_mark > 0) and (last_mark_top + dy_per_mark < new_top)) or \
               ((dy_per_mark < 0) and (last_mark_top + dy_per_mark > new_top)))):
    
            # Create the new mark                        
            mark_x = last_mark_left + dx_per_mark
            mark_y = last_mark_top + dy_per_mark
            mark = ItemImage(mark_x + marks_data[4], mark_y + marks_data[5], move_marks.mark_image)
            mark.move_mark_item = item            
            
            # Add the mark
            layer = item.get_layer()
            if layer != None:
                index = layer.items.index(item)
                layer.add(mark, index)
                
            # Store the data of the last mark
            last_mark_left = mark_x
            last_mark_top = mark_y
            marks_data[0] = last_mark_left
            marks_data[1] = last_mark_top
            
    if percentage >= 1:
        # The item reaches the target location, the animation should be stopped
        
        stage = data[10]
        stage.stop_timer(key)
                
        callback = data[9]
        if callback != None:
            callback(item)

def __timer_resize(key, data):
    """    
    This function is invoked by a timer to perform an step of a resize animation.
    - key: Timer's key.
    - data: Timer's data.    
    """
    item_image = key[0]
            
    # Calculate the the elapsed time
    now = pygame.time.get_ticks()
    if data[0] == None:
        elapsed_time = 0
        data[0] = now
    else:    
        elapsed_time = now - data[0]    
    
    # Get the resize data
    image = data[1]
    duration = data[2]
    origin_type = data[3]
    origin_pos = data[4]
    from_size = data[5]    
    to_size = data[6]            
            
    # Calculate the new size
    percentage = min(1, (float(elapsed_time) / duration))
    new_size = (int(from_size[0] + (to_size[0] - from_size[0]) * percentage), int(from_size[1] + (to_size[1] - from_size[1]) * percentage))
    
    # Calculate the new position
    if origin_type == 1:      
        new_left = origin_pos[0] - new_size[0] / 2
        new_top = origin_pos[1] - new_size[1] / 2
    else:
        new_left = item_image.get_left()
        new_top = item_image.get_top()
    
    # Set the new size
    resized_image = assets.Image(pygame.transform.smoothscale(image.surface, new_size))
    item_image.set_image(resized_image) 
           
    # Update the image and the position in the item
    item_image.set_image(resized_image)
    item_image.set_left(new_left)
    item_image.set_top(new_top)
                
    if percentage >= 1:
        # The item reaches the target location, the animation should be stopped
        
        stage = data[8]
        stage.stop_timer(key)
                
        callback = data[7]
        if callback != None:
            callback(item_image)
            
def __timer_wait(key, data):
    """    
    This function is invoked by a timer to invoke a callback after a wait.
    - key: Timer's key.
    - data: Timer's data.    
    """    
    stage = data[0]
    callback = data[1]
    stage.stop_timer(key)
    callback()
    
def __timer_wait_locked(key, data):
    """    
    This function is invoked by a timer to invoke a callback after a locked wait.
    - key: Timer's key.
    - data: Timer's data.    
    """    
    stage = data[0]
    callback = data[1]
    stage.stop_timer(key)
    stage.unlock_ui()
    if callback != None:    
        callback()
    
def __timer_blind_layer(key, data):
    """    
    This function is invoked by a timer to perform an step of a layer blind animation.
    - key: Timer's key.
    - data: Timer's data.    
    """    
    layer = key[0]
            
    # Calculate the elapsed time
    now = pygame.time.get_ticks()
    if data[0] == None:
        elapsed_time = 0
    else:
        elapsed_time = now - data[0]
    data[0] = now
    
    # Calculate the displacement
    dy_factor = data[2]
    dy = elapsed_time * dy_factor  
    
    # Apply the displacement
    end_of_blind = False
    direction = data[1] 
    if direction == BlindDirection.SHOW_UP:
        show = True
        if data[6] >= data[4]:
            # Only mark the end of the blind and invoke the callback after
            # that is rendered the full screen, because otherwise a rough
            # effect is see in the screen if the callback takes too long
            end_of_blind = True
        else:
            if data[6] + dy >= data[4]:
                data[5] = 0                
                data[6] = data[4]
            else:
                data[5] -= dy
                data[6] += dy            
    elif direction == BlindDirection.SHOW_DOWN:
        show = True
        if data[6] >= data[4]:
            end_of_blind = True
        else:                                    
            if data[6] + dy >= data[4]:
                data[6] = data[4]
            else:
                data[6] += dy
                                            
    elif direction == BlindDirection.HIDE_UP:
        show = False
        if data[6] <= 0:            
            end_of_blind = True
        else:            
            if data[6] - dy <= 0:
                data[6] = 0
                end_of_blind = True
            else:
                data[6] -= dy
    elif direction == BlindDirection.HIDE_DOWN:
        show = False 
        if data[6] <= 0:            
            end_of_blind = True
        else:
            if data[6] - dy <= 0:
                data[5] = 0
                data[6] = 0
                end_of_blind = True
            else:
                data[5] += dy
                data[6] -= dy            
    
    # Apply the clip
    if end_of_blind and show:
        layer.set_clip(None)
    else:
        clip = pygame.Rect(0, data[5], data[3], data[6])    
        layer.set_clip(clip)
        
    if end_of_blind:
        # The blind effect reach the end                 
        stage = data[8]
        lock_ui = data[9]            
        stage.stop_timer(key)
        stage.update_mouse()
        
        if lock_ui:
            stage.unlock_ui()
        
        callback = data[7]
        if callback != None:
            # Render the stage before call the callback, to avoid
            # long processing before update the last step
            stage.render()            
            callback(layer)
            