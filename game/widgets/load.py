def create_item(data, manager = None):
    if data['type'] and data['type'] != 'ignore':
        return getattr(manager, "create_" + data['type'])(data)
    else:
        return []

def text_arguments(data, manager = None):
    font = getattr(manager, data['font'])
    color = eval(data['color'])
    args = [data['left'], data['top'], font, 0, data['text'], color, None, data['width'], -1, 1, 1]
    kwargs = {}
    return args, kwargs

def create_text(data, manager = None):
    args, kwargs = self.text_arguments(data, manager)
    item = ItemText(*args, **kwargs)
    return [item]

def create_text_selectable(data, manager = None):
    args, kwargs = self.text_arguments(data, manager)
    color = eval(data['color'])
    rollover_color = eval(data['rollover_color'])
    selected_color = eval(data['selected_color'])
    item = ItemTextSelectable(color, rollover_color, selected_color, *args, **kwargs)
    return [item]

def create_button(data, manager = None):
    first = image = assets.load_image(data['src'])
    item = ItemImage(data['left'], data['top'], first)
    item.image = image
    
    if 'enabled' in data:
        item.enable = data['enabled']
    
    if 'disabled_src' in data:
        first = disabled_image = assets.load_image(data['disabled_src'])
        item.disabled_image = disabled_image
    else:
        item.disabled_image = None
        
    if 'rollover_src' in data:
        item.rollover_image = assets.load_image(data['rollover_src'])
        item.set_rollover_image(item.rollover_image)
    else:
        item.rollover_image = None 
        
    if manager is not None:
        click_handler = getattr(manager, 'handle_' + data['action'])
        item.add_event_handler(ItemEvent.CLICK, click_handler)
    return [item]

def create_image(data):
    if 'image' in data:
        image = data['image']
    else:
        image = assets.load_image(data['src'])
    item = ItemImage(data['left'], data['top'], image)
    return [item]

def rectangle_arguments(data):
    if 'color' in data:
        color = eval(data['color'])
    args = [data['left'], data['top'], data['width'], data['height']]
    kwargs = {}
    if 'color' in data:
        kwargs['background'] = color
    return args, kwargs

def create_rectangle(data):
    args, kwargs = rectangle_arguments(data)
    item = ItemRect(*args, **kwargs)
    return [item]

def create_rectangle_selectable(data, manager = None):
    args, kwargs = rectangle_arguments(data)
    if 'action' in data:
        action = data['action']
    else:
        action = None
    if 'items' in data:
        items = create_items_from_yaml(data['items'], manager)
    else:
        items = []
    item = ItemRectSelectable(data['step_left'], data['step_top'], data['step_width'], data['step_height'], action, items, *args, **kwargs)
    return [item] + items

def create_option(group, data, yaml_items, manager = None):
    items = []
    for yaml_item in yaml_items:
        yaml_item.update(data)
        items += create_item(yaml_item, manager)
    OptionItems(group, data, items)
    return items

def create_option_image(group, data):
    item = OptionImage(group, data)
    return [item]