# -*- coding: latin-1 -*-

# 2011 - Dirección General Impositiva, Uruguay.
# Todos los derechos reservados.
# All rights reserved.

import assets
import os
import traceback
from datetime import *

__start_date = date.today()
__data = None
__pending_save = False
__active_events = {}

def start_time_event(code):
    if __data == None:
        __load_data()
        
    if not code in __active_events:
        __active_events[code] = datetime.now()
                
        
def end_time_event(code):
    if __data == None:
        __load_data()

    if code in __active_events:
        elapsed_time = (datetime.now() - __active_events[code]).seconds
        
        if code in __data:
            __data[code] = elapsed_time
        else:
            __data[code] += elapsed_time
        
        del __active_events[code]        
        __pending_save = True
   
    
def increment_count_event(code):
    if __data == None:
        __load_data()   
        
    if code in __data:
        __data[code] += 1
    else:
        __data[code] = 1
        
    __pending_save = True
   
   
def save_if_pending():
    if __pending_save:
        data_to_save = [[str(__start_date.toordinal()), str(date.today().toordinal())]]
        for key, value in __data:
            data_to_save.append([str(key), str(value)])
        assets.save_data("game.data", data_to_save)
        
        __pending_save = False
        
def report_error(type, value, tb):
    full_name = os.path.join('data', "game_err.dat")
    file = open(full_name, 'a')
    file.write("[")
    file.write(str(datetime.now().strftime('%d/%m/%Y %H:%M:%S')))
    file.write("] ")
    file.write("%s: %s\n" % (type.__name__, str(value)))
    traceback.print_tb(tb, None, file)                
    file.close()

def __load_data():    
    lines = assets.load_data("game.dat")    
    __data = {}
    if len(lines) >= 1:
        first_line = lines[0]
        if len(first_line) >= 2:
            __start_date = date.fromordinal(first_line[0])
            for line in lines[1:]:
                if len(line) >= 2:
                    __data[int(line[0])] = int(line[1])
            
    
    
    
