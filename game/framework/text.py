# -*- coding: latin-1 -*-

# 2011 - Dirección General Impositiva, Uruguay.
# Todos los derechos reservados.
# All rights reserved.

def to_upper(text):
    """    
    Convert a text to uppercase.
    
    The standard upper() function provided by python doesn't deal well the
    accents, so, its recommended to use this function.
    """
    return text.decode('latin-1').upper().encode('latin-1')
    
def to_lower(text):
    """
    Convert a text to lowecase.
    
    The standard lower() function provided by python doesn't deal well the
    accents, so, its recommended to use this function.
    """  
    return text.decode('latin-1').lower().encode('latin-1')

def format_number(number):
    """    
    Converts the specified number to a text and adds thousand separators.
    - number: Number.
    """
    text = str(number)
        
    decimal_separator = text.find(',')
    if decimal_separator == -1:
        decimal_separator = text.find('.')
    if decimal_separator == -1:
        text_len = len(text)
    else:
        text_len = decimal_separator
    
    k = 3
    while k < text_len:
        i = text_len - k
        if i == 1 and text[0] == '-':
            break        
        text = text[0:i] + '.' + text[i:]
        k += 4
        
    return text
    