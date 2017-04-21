# -*- coding: latin-1 -*-

# 2011 - Dirección General Impositiva, Uruguay.
# Todos los derechos reservados.
# All rights reserved.

import os
import subprocess

def __open_browser_any(uri, title="", description=""):
    import webbrowser
    webbrowser.open(uri)

def __save_and_show(obj):
    datastore.write(obj,
            transfer_ownership=True)
    id = obj.object_id
    activity.show_object_in_journal(id)

def __open_browser_sugar(uri, title="", description=""):
    temp_file_path = os.path.join(data_path, "tmp", "update_url.txt")
    f = open(temp_file_path,"w")
    f.write(uri)
    f.close()
    obj = datastore.create()
    obj.metadata['title'] = title
    obj.metadata['keep'] = '0'
    obj.metadata['buddies'] = ''
    obj.metadata['preview'] = ''
    obj.metadata['mime_type'] = 'text/uri-list'
    obj.metadata['activity'] = "org.laptop.WebActivitiy"
    obj.set_file_path(temp_file_path)
    __save_and_show(obj)

def __install_and_execute_sugar(path, title="", description=""):
    obj = datastore.create()
    obj.metadata['title'] = title
    obj.metadata['keep'] = '0'
    obj.metadata['buddies'] = ''
    obj.metadata['preview'] = ''
    obj.metadata['mime_type'] = 'application/vnd.olpc-sugar'
    obj.set_file_path(path)
    __save_and_show(obj)

def __check_other_activities():
    try:
        p = subprocess.Popen("ps -ef | egrep \"(rainbow|activity)\" | grep -v egrep", shell=True, stdout=subprocess.PIPE)
    except:
        return False
    ret = p.wait()
    if ret != 0:
        return False
    count = 0
    while p.stdout.readline():
        count += 1
    # Only let the current activity, the journal and the rainbow daemon to be open
    return count > 3
try:
    from sugar.activity import activity
    from sugar.datastore import datastore
    open_browser = __open_browser_sugar
    data_path = os.path.join(activity.get_activity_root(), 'data')
    execute_package = __install_and_execute_sugar
    other_activities_running = __check_other_activities
    is_sugar = True
except ImportError:
    open_browser = __open_browser_any
    data_path = ""
    execute_package = None
    other_activities_running = lambda *args, **kwargs: False
    is_sugar = False
import os

    
