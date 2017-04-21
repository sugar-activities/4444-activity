# -*- coding: latin-1 -*-

# 2011 - Dirección General Impositiva, Uruguay.
# Todos los derechos reservados.
# All rights reserved.

import pygame
import os
import engine
import codecs
from pygame.locals import *


def load_data(file_name, field_sep = ";"):
    """ 
    Loads a data file as a matrix.
      - file_name: File name to load.
      - field_sep: Field separator 
    """
    
    full_name = os.path.join('data', file_name)
    try:
        file = open(full_name, 'r') 
        line = file.readline()
        data = []
        while line != "":
            line = line.rstrip('\n').rstrip('\r')
            fields = line.split(field_sep)            
            data.append(fields)            
            line = file.readline()
        file.close()
    except Exception, message:
        print 'Cannot load data file:', full_name
        raise SystemExit, message

    return data

def save_data(file_name, data, field_sep = ";"):
    """ 
    Saves a data file from a matrix.
      - file_name: File name to save.
      - data: Data to save. 
      - field_sep: Field separator 
    """    
    full_name = os.path.join('data', file_name)
    try:
        file = open(full_name, 'w')
        first_line = True            
        for line in data:
            if first_line:
                first_line = False
            else:
                file.write('\n')
            file.write(field_sep.join(line))
        file.close()
    except Exception, message:
        print 'Cannot save data file:', full_name
        raise SystemExit, message
    

def file_to_save_data(file_name):
    """ 
    Loads a data file to write on
    """
    full_name = os.path.join('data', file_name)
    try:
        file = open(full_name, 'w')
    except Exception, message:
        print 'Cannot load data file:', full_name
        raise SystemExit, message

    return file

def load_sound(file_name):
    """    
    Loads the specified sound .
    - file_name: File name   
    """ 
    full_name = os.path.join('sounds', file_name)
    try:
        sound = pygame.mixer.Sound(full_name)
    except pygame.error, message:
        print 'Cannot load sound:', full_name
        raise SystemExit, message
    
    return sound

def load_image(file_name):
    """    
    Loads the specified image.
    - file_name: File name   
    
    The loaded image is optimized to be shown in the screen.
    """ 

    # Load the surface
    surface = load_surface(file_name)
            
    return Image(surface)                

def load_image_alpha(file_name_rgb, file_name_alpha):
    """    
    Loads the specified image with a separated alpha mask.
    - file_name_rgb: File name (with RGB colors)   
    - file_name_alpha: File name (with alpha channel). None to create a solid alpha channel.
    
    The loaded image is optimized to be shown in the screen.
    """    

    # Load the surface
    surface = load_surface_alpha(file_name_rgb, file_name_alpha)
        
    return Image(surface)   

def load_surface(file_name):
    """    
    Loads the specified image in a surface.
    - file_name: File name
    """   

    full_name = os.path.join('images', file_name)
    try:
        image = pygame.image.load(full_name)
    except pygame.error, message:
        print 'Cannot load image:', full_name
        raise SystemExit, message

    # Convert the image to the same pixel format as the screen.
    # This is the fastest format to blitting        
    if image.get_bitsize() == 32:            
        image = image.convert_alpha()
    else:
        image = image.convert()
        
    return image                

def load_surface_alpha(file_name_rgb, file_name_alpha):
    """    
    Loads the specified image with a separated alpha mask in a surface.
    - file_name_rgb: File name (with RGB colors)   
    - file_name_alpha: File name (with alpha channel). None to create a solid alpha channel.
    """

    full_name = os.path.join('images', file_name_rgb)
    try:
        image_rgb = pygame.image.load(full_name)            
    except pygame.error, message:
        print 'Cannot load image:', full_name
        raise SystemExit, message

    if file_name_alpha == None:
        image = image_rgb.convert_alpha()
    else:
        full_name = os.path.join('images', file_name_alpha)
        try:
            image_alpha = pygame.image.load(full_name)            
        except pygame.error, message:
            print 'Cannot load image:', full_name
            raise SystemExit, message
        
        # Merge image RGB with alpha channel
        image = image_rgb.convert_alpha()
        alpha = pygame.surfarray.pixels_alpha(image);                
        for x in range(image.get_width()):
            for y in range(image.get_height()):                                
                alpha[x][y] = image_alpha.get_at((x, y))[0]        

    return image   

def load_mask(file_name):
    """    
    Loads the specified image to be used as a mask in a surface.
    - file_name: File name   
    
    The loaded image is optimized to consume less memory.
    """ 

    full_name = os.path.join('images', file_name)
    try:
        image = pygame.image.load(full_name)
    except pygame.error, message:
        print 'Cannot load image:', full_name
        raise SystemExit, message

    # The image probably has a palette, the convert function
    # is not invoked because the image will no be shown in the
    # screen and the representation with a palette consume less
    # memory
    
    return image                

def load_font(file_name, size):
    """    
    Loads a font.
    - file_name: File name.
    - size: Size.
    """

    full_name = os.path.join('fonts', file_name)
    return pygame.font.Font(full_name, size)

class Image(object):
    """    
    Represents an image
    """
    
    def __init__(self, surface):
        """        
        Constructor.
        - surface: Surface that represents the image. None to create a new surface based on the width and height.
        """    
    
        self.surface = surface        
            
    def get_width(self):
        """        
        Gets the width of the image.
        """        
        return self.surface.get_width()
    
    def get_height(self):
        """        
        Gets the height of the image.
        """        
        return self.surface.get_height()
    
    def get_size(self):
        """
        Gets the size of the image.
        """
        return (self.get_width(), self.get_height())
    
    def get_at(self, x, y):
        """        
        Get the value of the pixel at the specified position.
        - x: X coordinate
        - y: Y coordinate
        """    
        return self.surface.get_at(x, y)
     
    def flip_h(self):
        """
        Flips the image horizontally.
        """
        self.surface = pygame.transform.flip(self.surface, True, False)
    
    def flip_h_copy(self):
        """
        Flips the image horizontally and return it in a new instance.
        """
        return Image(pygame.transform.flip(self.surface, True, False))
    
    def flip_v(self):
        """
        Flips the image vertically.
        """
        self.surface = pygame.transform.flip(self.surface, False, True)
    
    def flip_v_copy(self):
        """
        Flips the image vertically and return it in a new instance.
        """
        return Image(pygame.transform.flip(self.surface, False, True))
    
    def flip_hv(self):
        """
        Flips the image horizontally and vertically.
        """
        self.surface = pygame.transform.flip(self.surface, True, True)
    
    def flip_hv_copy(self):
        """
        Flips the image horizontally and vertically and return it in a new instance.
        """
        return Image(pygame.transform.flip(self.surface, True, True))
        
    def get_real_rect(self):
        """        
        Gets the image rect.
        """        
        return self.surface.get_rect()

    def blit_over(self, target_surface, pos, area = None):
        """        
        Draw the image on the target surface.
        - target_surface: Surface where the image is drawn.    
        - pos: A pair of coordinates representing the position of the image. A Rect 
             can also be passed as de destination (x,y), the size of the rectangle is ignored.
        - area: Represents the portion of the image to draw.
        """      
                
        if area != None:
            target_surface.blit(self.surface, pos, area)
        else:
            target_surface.blit(self.surface, pos)
            