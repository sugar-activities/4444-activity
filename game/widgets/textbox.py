# -*- coding: latin-1 -*-

from framework.stage import Item, ItemEvent
from pygame.locals import *
from pygame import Surface
from collections import deque

SEPARATOR = " "
PARAGRAPH_SEPARATOR = "\n"
MAX_WORD_CACHE = 200
class Cursor():
    def __init__(self, textbox):
        self.char = 0
        self._textbox = textbox
    
    def move_left(self):
        if self.char > 0:
            self.char -= 1
    
    def move_right(self,):
        if self.char < len(self._textbox._text):
            self.char += 1
    
    def at_begining(self):
        return self.char == 0

class Line():
    def __init__(self, font, color, words, char, len):
        self._font = font
        self.rendered = False
        self._surface = None
        self._color = color
        self._line_height = 0
        self._words = words
        self._space_width = font.size(" ")[0]
        self.char = char
        self.len = len
        self.paragraph = None

    def render(self, item, target, left, top, word_cache):
        for word in self._words:
            word_obj = word_cache.get(word)
            target.blit_surface(word_obj.surface, (left, top))
            left += word_obj.surface.get_width() + self._space_width
    
    def __str__(self):
        ret = ""
        for word in self._words:
            ret = ret + word + " "
        return ret

class Paragraph():
    def __init__(self, lines):
        self._lines = lines
        for line in lines:
            line.paragraph = self

class Word():
    def __init__(self, word, font, color):
        self.font = font
        self.word = word
        self.color = color
        self.surface = font.render(word, True, color)
        current = ""
        lengths = [0]
        for l in word:
            current = current + l
            lengths.append(font.size(current)[0])
        self.lengths = lengths

class RenderCache(dict):
    
    def __init__(self, font, color):
        dict.__init__(self)
        self._font = font
        self._color = color
        self.queue = deque()
    
    def get(self, name):
        if name in self:
            return self[name]
        else:
            value = self[name] = Word(name, self._font, self._color)
            self.queue.append(name)
            if len(self.queue) > MAX_WORD_CACHE:
                word = self.queue.popleft()
                del self[word]
            return value

class TextBox(Item):
    VALID_UNICODE_CHARS = ['á','é','í','ó','ú','Á','É','Í','Ó','Ú','ñ','Ñ','ü','Ü','ç','Ç']
    def __init__(self, left, top, w, h, font, color):
        self._left = left
        self._top = top
        self._w = w
        self._h = h
        self._cursor = Cursor(self)
        self._text = ""
        self._font = font
        self._color = color
        Item.__init__(self, left, top, w, h)
        self._paragraphs = []
        self._separator_width = font.size(SEPARATOR)[0]
        self._line_height = font.size(SEPARATOR)[1]
        self._lines = []
        self.draw_function = self.render
        self._first_rendered_line = 0
        self._word_render_cache = RenderCache(self._font, self._color)
        self._cursor_surface = Surface((2, self._line_height - 2))
        self._cursor_surface.fill((0, 0, 0), (0, 0, 2, self._cursor_surface.get_height()))
        self._render_cursor = True
     
    def __begin_edit_on_click(self, *args, **kwargs):
        self.get_stage().set_focus(self)

    def begin(self):
        self.add_event_handler(ItemEvent.CLICK, self.__begin_edit_on_click) 
        self.get_stage().set_focus(self)

    def text(self, text):
        self._text = text
        self._update_text()
        self._cursor.char = 0
    
    def get_text(self):
        return self._text
    
    def _update_text(self):
        self._paragraphs = []
        self._lines = []
        for p in self._text.split("\n"):
            words = p.split(SEPARATOR)
            lines = self.get_lines(words)
            self._paragraphs.append(Paragraph(lines))

    def break_word(self, word):
        i = 0
        len_word = len(word)
        sub_words = []
        current_word = ""
        while i < len_word:
            if self._font.size(current_word + word[i])[0] > self._w:
                sub_words.append(current_word)
                current_word = ""
            else:
                current_word = current_word + word[i]
                i += 1
        return sub_words, current_word
            
    def get_lines(self, text, total_char = 0, separator = 1):
        lines = []
        line_height = 0
        current_length = 0
        current_char = 0
        words = []
        for word in text:
            word_width = self._font.size(word)[0]
            if word_width > self._w:
                if words:
                    lines.append(Line(self._font, self._color, words, total_char, current_char))
                    total_char += current_char
                    words = []
                    current_length = 0
                    current_char = 0
                broken_words, last_word = self.break_word(word)
                for broken_word in broken_words:
                    lines.append(Line(self._font, self._color, [broken_word], total_char, len(broken_word)))
                    total_char += len(broken_word)
                if last_word:
                    words = [last_word]
                    current_char = len(last_word) + separator
                    current_length = self._font.size(last_word)[0] + self._separator_width
                continue
            current_length += word_width
            if current_length > self._w:
                lines.append(Line(self._font, self._color, words, total_char, current_char))
                words = [word]
                current_length = word_width + self._separator_width
                total_char += current_char
                current_char = len(word) + separator
            else:
                words += [word]
                current_length += self._separator_width
                current_char += len(word) + separator
        if words:
            lines.append(Line(self._font, self._color, words, total_char, current_char))
            total_char += current_char
        return lines
    
    def render_cursor(self, item, target, left, top, line):
        if not self._render_cursor:
            return
        if line:
            render_cache = self._word_render_cache
            index_in_line = self._cursor.char - line.char
            i = 0
            chars = 0
            length = 0
            while index_in_line > chars + len(line._words[i]):
                length += render_cache.get(line._words[i]).surface.get_width() + self._separator_width
                chars += len(line._words[i]) + 1
                i += 1
            index_in_word = index_in_line - chars
            length += render_cache.get(line._words[i]).lengths[index_in_word] - 2
            if length < 0:
                length = 0
        else:
            length = 0
        target.blit_surface(self._cursor_surface, (left + length, top + 1))
        
        
            
    def render(self, item, target):
        cursor = self._cursor
        first_rendered_line = self._first_rendered_line
        line_height = self._line_height
        # Check if the last rendered line should be rendered now
        can_render_lines = int(self._h / line_height)
        cursor_line = self.cursor_line_index()
        if (cursor_line >= first_rendered_line + can_render_lines):
            first_rendered_line = cursor_line - can_render_lines + 1
        if (cursor_line < first_rendered_line):
            first_rendered_line = cursor_line
        line = first_rendered_line
        top = self._top
        while line - first_rendered_line < can_render_lines and line < len(self._lines):
            if (line == cursor_line):
                self.render_cursor(item, target, self._left, top, self._lines[line])
            self._lines[line].render(item, target, self._left, top, self._word_render_cache)
            line += 1
            top += self._line_height
        if len(self._lines) == 0:
            self.render_cursor(item, target, self._left, top, None)
        self._first_rendered_line = first_rendered_line
            
    def reflow(self, from_line):
        if from_line < 0:
            from_line = 0
        if from_line < len(self._lines):
            from_char = self._lines[from_line].char
        else:
            from_char = 0
        self._lines = self._lines[:from_line]
        paragraphs = self._text[from_char:].split(PARAGRAPH_SEPARATOR)
        for paragraph in paragraphs:
            words = paragraph.split(SEPARATOR)
            self._lines = self._lines + self.get_lines(words, from_char)
            from_char = self._lines[-1].len + self._lines[-1].char
            self.set_dirty()

    def _delete_char(self, position):
        self._text = self._text[:position] + self._text[position + 1:]

    def _add_char(self, position, char):
        self._text = self._text[:position] + char + self._text[position:]

    def __handle_key(self, key, unicode, data):        
        updated = False
        handled = False
                
        if key == K_RETURN:
            self.__reset_cursor_timer()
            line = self.cursor_line_index()
            self._add_char(self._cursor.char, '\n')
            self.reflow(line - 1)
            self._cursor.move_right()
        elif key == K_BACKSPACE:
            self.__reset_cursor_timer()
            if not self._cursor.at_begining():
                self._cursor.move_left()
                line = self.cursor_line_index()
                self._delete_char(self._cursor.char)
                self.reflow(line - 1)
        elif key == K_DELETE:
            self.__reset_cursor_timer()
            line = self.cursor_line_index()
            self._delete_char(self._cursor.char)
            self.reflow(line - 1)
        elif key == K_RIGHT:
            self.__reset_cursor_timer()
            self._cursor.move_right()
            self.set_dirty()
        elif key == K_LEFT:
            self.__reset_cursor_timer()
            self._cursor.move_left()
            self.set_dirty()
        elif key == K_HOME:
            self.__reset_cursor_timer()
            self._cursor.char = 0
            self.set_dirty()
            pass
        elif key == K_UP:
            self.__reset_cursor_timer()
            self.up_cursor()
            self.set_dirty()
        elif key == K_END:
            self.__reset_cursor_timer()
            self._cursor.char = len(self._text)
            self.set_dirty()
            pass
        elif key == K_DOWN:
            self.__reset_cursor_timer()
            self.down_cursor()
            self.set_dirty()
        else:
            if ((unicode != '') and
                ((ord(unicode) > 31 and ord(unicode) < 126) or \
                (ord(unicode) < 255 and unicode.encode('latin-1') in self.VALID_UNICODE_CHARS)) \
                ):
                self.__reset_cursor_timer()
                line = self.cursor_line_index()
                self._add_char(self._cursor.char, unicode.encode('latin-1'))
                self.reflow(line - 1)
                self._cursor.move_right()
        return handled
    
    def up_cursor(self):
        i = self.cursor_line_index()
        if i > 0:
            char = self._cursor.char - self._lines[i].char
            char = min(char, self._lines[i - 1].len - 1)
            self._cursor.char = self._lines[i - 1].char + char
        self.set_dirty()
    
    def down_cursor(self):
        i = self.cursor_line_index()
        if i < len(self._lines) - 1:
            char = self._cursor.char - self._lines[i].char
            char = min(char, self._lines[i + 1].len - 1)
            self._cursor.char = self._lines[i + 1].char + char
        self.set_dirty()
    
    def cursor_line_index(self):
        if not self._lines:
            return 0
        for line in self._lines:
            if self._cursor.char < line.char:
                return self._lines.index(line) - 1
        return len(self._lines) - 1
            

    def handle_event_focused(self, event, data):
        """
        This function is invoked to process events when the control is
        focused.
        - event: Event.
        - data: Data returned by the on_got_focus function.
        """
        if event.type == KEYDOWN:
            key = event.key
            unicode = event.unicode
            
            stage = self.get_stage()
            if stage != None:
                timer_key = (self, "key_repeat")        
                stage.start_timer(timer_key, 600, self.__handle_key_repeat, (key, unicode, data, True), True, False)
                
                if self.__handle_key(key, unicode, data):
                    return True

        elif event.type == KEYUP:
            timer_key = (self, "key_repeat")
            stage = self.get_stage()
            if stage != None:
                stage.stop_timer(timer_key)
    
    def __handle_key_repeat(self, key, args):
        timer_key = (self, "key_repeat")
        if args[3]:
            stage = self.get_stage()
            if stage != None:                
                stage.stop_timer(timer_key)
                stage.start_timer(timer_key, 50, self.__handle_key_repeat, (args[0], args[1], args[2], False), True, False)
                    
        self.__handle_key(args[0], args[1], args[2])
    
    def __update_cursor_timer(self, key, data):
        """
        Function that is invoked by the timer to hide/show the cursor when editing.
        """
        stage = data
        focused_item = stage.get_focus()
        if focused_item != self:            
            stage.stop_timer(key)
        else:
            self._render_cursor = not self._render_cursor
            self.set_dirty()

    def __reset_cursor_timer(self):
        stage = self.get_stage()
        if stage != None:
            cursor_key = (self, "text_cursor")
            stage.stop_timer(cursor_key)
            self._render_cursor = True
            stage.start_timer(cursor_key, 500, self.__update_cursor_timer, stage)  
        
    def on_got_focus(self, set_focus_data):
        """
        This function is invoked automatically when the text receives the
        focus.
        - set_focus_data: Data associated with the set focus.
        """ 
        stage = self.get_stage()
        if stage != None:
            key = (self, "text_cursor")            
            stage.start_timer(key, 500, self.__update_cursor_timer, stage)
            self._render_cursor = True
        index = set_focus_data
        return [index, True]

    def on_lost_focus(self, stage, data):
        """
        This function is invoked automatically when the text lost the
        focus.
        - data: Data associated with the focus.
        """        
        timer_key = (self, "key_repeat")
        stage.stop_timer(timer_key)  
        cursor_key = (self, "text_cursor")
        stage.stop_timer(cursor_key)
        self._render_cursor = False
        