# -*- coding: latin-1 -*-

# 2011 - Dirección General Impositiva, Uruguay.
# Todos los derechos reservados.
# All rights reserved.

from game.data import datamodel
from yaml import load, dump
from utils import DictClass
import os.path
import zlib
from framework.external import data_path
 
DATA_PATH = os.path.join(data_path, "data")
if not os.path.exists(DATA_PATH):
    os.mkdir(DATA_PATH)

DATA_FILE_PATH = os.path.join(DATA_PATH, "datamodel.yaml")

WEB_DIR = "http://cblog.dgi.gub.uy/api/"
WEB_DIR_ACT = WEB_DIR + "activity/%s"
WEB_DIR_NEW_POST = WEB_DIR + "activity/%s/posts"
WEB_DIR_POST = WEB_DIR + "activity/%s/posts/%s"

class Datastore:
    """
    Allows to set up useful data for the game
    """
    def __init__(self):
        """
        Constructor
        """
        self.changed_data = False
        self.loaded_data = False
        self.set_up_data()
        self.save()
    
    def save(self):
        file = open(DATA_FILE_PATH, "wb")
        file.write(zlib.compress(dump(self.datamodel)))
        file.close()
    
    def reset_character(self):
        self.datamodel = datamodel.Datamodel()
    
    def load(self):
        if os.path.exists(DATA_FILE_PATH):
            file = open(DATA_FILE_PATH, "rb")
            try:
                self.datamodel.__dict__.update(load(zlib.decompress(file.read())).__dict__)
                self.loaded_data = True
            except:
                pass
            file.close()

    def set_up_data(self):
        """
        Set types
        """
        self.contents = DictClass(load(file('data/common/contents.yaml')))
        self.tests = DictClass(load(file('data/common/tests.yaml')))
        self.levels = DictClass(load(file('data/common/level_contents.yaml')))
        self.datamodel = datamodel.Datamodel()
        
        self.load()
        