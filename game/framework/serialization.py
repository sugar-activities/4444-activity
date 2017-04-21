# -*- coding: latin-1 -*-

# 2011 - Dirección General Impositiva, Uruguay.
# Todos los derechos reservados.
# All rights reserved.


def read_objects(file_name, type):
    """    
    Reads a list of objects from a file.
    - file_name: File name.
    - type: Type of the objects to be readed.
    """

    # Open the file
    file = open(file_name, 'rb')
    
    # Read the file line per line
    reader = Reader()
    line = file.readline()
    objs = []
    while line != "":
        # Create a new instance of an object and read its data
        obj = type()
        reader.set_data(line)
        obj.read(reader)
        
        # Append the object in the list
        objs.append(obj)
        
        # Read the next line
        line = file.readline()
        
    # Close the file        
    file.close()
    
    return objs

def read_objects_dict(file_name, type, key):
    """    
    Reads a dictionary of objects from a file.
    - file_name: File name.
    - type: Type of the objects to be readed.
    - key: Function to get the key of the object to be added in the dictionary
    """    

    # Open the file
    file = open(file_name, 'rb')
    
    # Read the file line per line
    reader = Reader()
    line = file.readline()
    objs = {}
    while line != "":
        # Create a new instance of an object and read its data
        obj = type()
        reader.set_data(line)
        obj.read(reader)
        
        # Add the object in the dictionary
        objs[key(obj)] = obj
        
        # Read the next line
        line = file.readline()
        
    # Close the file        
    file.close()
    
    return objs
    
def write_objects(file_name, objs):
    """
    Writes a list of objects in a file
    - file_name: File name.
    - objs: List of objects to be written.
    """

    # Open the file
    file = open(file_name, 'wb')
    
    # Write the objects in the file
    writer = Writer(file)
    for o in objs:
        # Write the object in the file
        o.write(writer)
    
        # Marks that the end of current object data
        writer.write_end_of_object() 
        
    # Close the file        
    file.close()


class Reader:
    """
    Class used to read object's data from a file
    """
        
    def __init__(self):
        """        
        Constructor.
        """
        self.__fields = []
        self.__index = 0
        
    def set_data(self, data):
        """
        Sets the data to be readed.
        - data: Text of a line to be readed.
        """    
        self.__fields = data.split(';')
        self.__index = 0
            
    def read_str(self):
        """
        Reads a field that has a value of type string.
        """
        s = self.__fields[self.__index]
        self.__index += 1
        return s.decode('string_escape').replace('\s', ';')
        
    def read_int(self):
        """
        Reads a field that has a value of type int.
        """
        s = self.__fields[self.__index]
        self.__index += 1
        return int(s)
        
    def get_field_count(self):
        """
        Gets the number of fields of the object.
        """
        return len(self.__fields)
    
class Writer:
    """
    Class used to write object's data in a file
    """
    
    def __init__(self, file):
        """
        Constructor.    
        - file: File where the objects are written.
        """
    
        self.__file = file
        self.__first_field = True
        
    def write_str(self, value):
        """
        Writes a field that has a value of type string.
        - value: Value of the field.
        """
        if self.__first_field:
            self.__file.write(';')   
            self.__first_field = False
        self.__file.write(value.encode('string_escape').replace(';', '\s'))
        
    def write_end_of_object(self):
        """        
        Writes the end of an object
        """
        self.__file.writeline()
        self.__first_field = True
    