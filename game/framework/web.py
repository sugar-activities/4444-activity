# -*- coding: latin-1 -*-

# 2011 - Dirección General Impositiva, Uruguay.
# Todos los derechos reservados.
# All rights reserved.

from Queue import Queue, Empty
from threading import Lock, Thread
from weakref import ref
import urllib2, urllib
import simplejson as json
import zlib

"""
This module executes asynchronous web request in a background thread.
It starts the thread when it is first imported and then executes every web request stored in a FIFO queue
by the different methods exposed.

Every method in this module receives a key which is used to check for the result of the request.
If this key is None then no result is stored.
"""
__send_queue = Queue(0)
__results = {}
__results_lock = Lock()
__callbacks = Queue(0)

class Error:
  NO_ERROR = 0
  PARSING = 1
  CONNECTION = 2
  SERVER = 3
  UNKNOWN = 4

def __simple_task_method(func):
    def wrapper(*args, **kwargs):
        try:
            response = func(*args, **kwargs)
            print "response", response
            if response.headers.get("Content-Type","") in ('application/json', 'application/javascript'):
                data = json.loads(response.read(), strict=False)
            else:
                data = response.read()
            response.close()
            del response
            return TaskResult(data)
        except urllib2.HTTPError, e:
            return TaskResult(e, error = Error.SERVER, code = e.code)            
        except urllib2.URLError, e:
            return TaskResult(e, error = Error.CONNECTION)
        except Exception, e:
            print e
            return TaskResult(e, error = Error.UNKNOWN)
    return wrapper 

def synchronized(lock):
    """ 
    helper decorator for synchronized operations, similar to java's synchronized 
    """
    def apply(func):
        def wrapper(*args, **kwargs):
            lock.acquire()
            try:
                return func(*args, **kwargs)
            finally:
                lock.release()
        return wrapper
    return apply 

class __PendingTask:
    """ 
    It represents a pending task to execute in the web thread
    """
    def __init__(self, method, key=None, callback=None):
        self.method = method
        self.key = key
        self.callback = ref(callback)

class TaskResult:
    """ 
    It is the result of a task, which includes if it resulted in an error
    and the data obtained from the response. 
    """
    def __init__(self, data, error=False, code=0):
        self.error = error
        self.data = data
        self.code = code

def send_data(to, data, key=None, callback=None, encoding=None, compressed=False):
    """
    Post a task to execute which sends an encoded data dictionary to a recipient through a POST method
    Currently only the json encoding is implemented
    """
    @__simple_task_method
    def __send_data():
        req = urllib2.Request(str(to))
        send_data = data
        if encoding is None:
            req.add_header('Content-Type', 'application/x-www-form-urlencoded')
            send_data = urllib.urlencode(send_data)
        elif encoding == "json":
            send_data = json.dumps(send_data)
            req.add_header('Content-Type' , 'application/json')
        elif encoding == "text":
            req.add_header('Content-Type', 'text/plain')
        if compressed:
            req.add_header('Content-Encoding', 'gzip')
            send_data = zlib.compress(send_data)
        req.data = send_data
        return urllib2.urlopen(req)
            
    __send_queue.put(__PendingTask(__send_data, key, callback))

def query(to, parameters=None, key=None, callback=None):
    """
    Posts a task to execute which sends a GET request with the parameters dictionary URL-encoded at
    the end of the url address.
    """
    @__simple_task_method
    def __query():
        if parameters:
            local_to = to + '?' + urllib.urlencode(parameters)
        else:
            local_to = to
        # Convert the type to str, if it is converted to unicode
        # the the request gets stuck at a call to socket.getaddrinfo
        # because it receives a 
        return urllib2.urlopen(str(local_to))
    __send_queue.put(__PendingTask(__query, key, callback))

def download_file(to, path, parameters=None, key=None, callback=None):
    def __get_file():
        if parameters:
            local_to = to + '?' + urllib.urlencode(parameters)
        else:
            local_to = to
        try:
            return TaskResult(urllib.urlretrieve(str(local_to), path)[1])
        except IOError:
            return TaskResult(None, error=True)
    __send_queue.put(__PendingTask(__get_file, key, callback))
            
def get_callback():
    """
    Returns a callback to execute
    """
    try:
        return __callbacks.get(block=False)
    except Empty:
        return None

@synchronized(__results_lock)
def get_result_and_delete(key):
    """
    Returns the result of the request which originated by a call to a send* or query*
    method with a given key.
    """
    if key in __results:
        ret = __results[key]
        __results.pop(key)
        return ret

@synchronized(__results_lock)
def __add_result(key, data):
    __results[key] = data

def __thread_main():
    while True:
        task = __send_queue.get()
        result = task.method()
        callback = task.callback()
        if callback:
            __callbacks.put(lambda:callback(result))
        if task.key:
            __add_result(task.key, result)
        

__thread = Thread(group=None, target=__thread_main, name="web_thread")
__thread.setDaemon(True)
__thread.start()
del __thread

