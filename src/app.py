from flask import Flask, send_from_directory, redirect, Response, request
from cooklang import Recipe
import os
from jinja2 import Environment, FileSystemLoader
import urllib

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')
RECIPE_DIR = os.getenv('RECIPE_DIR', os.path.join(BASE_DIR, 'recipes'))

EXCLUDE_DIRS = ['config']

app = Flask(
    __name__,
    static_url_path='/static',
    static_folder=STATIC_DIR,
)

jinja_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))


def split_path(path):
    parts = []
    headtail = (path, 0)
    while (headtail := os.path.split(headtail[0]))[0] not in ['', '/']:
        parts.insert(0, headtail[1])
    parts.insert(0, headtail[1])
    if (head := headtail[0]) == '/':
        parts.insert(0, head)
    return parts

def join_paths(parts):
    joined = ''
    for part in parts:
        joined = os.path.join(joined, part)
    return joined

def find_matching_child(folder, tail):
    _, folders, files = next(os.walk(os.path.join(RECIPE_DIR, folder)))
    replaced_tail = tail.replace('_', ' ')
    for group in [folders, files]:
        for t in [tail, replaced_tail]:
            if t in group:
                return t
    return None

def find_matching_path(unjoined_path):
    """Take an unjoined_path and return the file it matches."""
    parts = split_path(unjoined_path)
    matching_parts = []
    for part_count, part in enumerate(parts):
        current_folder = join_paths(matching_parts[:part_count]) or '.'
        match = find_matching_child(current_folder, part)
        if match == None:
            return None
        matching_parts.append(match)
    return join_paths(matching_parts)

def highlight_steps(ingredients, steps):
    # find indexes to insert highlighting
    indexes = []
    for ingr in ingredients:
        for step_index, step in enumerate(steps):
            if (start_index := step.find(ingr.name)) > -1:
                end_index = start_index + len(ingr.name)
                indexes.append((end_index, ingr, step_index))

    # sort the index high to low
    indexes.sort(key=lambda x: -x[0])

    # insert highlighting
    hl_steps = steps
    for index, ingr, step_index in indexes:
        step = hl_steps[step_index]

        hl = ''
        if ingr.quantity != None:
            hl += '<span class=ingr-quantity-inline>(' + str(ingr.quantity.amount)
            if ingr.quantity.unit:
                hl += ' ' + ingr.quantity.unit
            hl += ')</span>'

        step = step[:index] + hl + step[index:]
        hl_steps[step_index] = step

    return hl_steps

def get_image_name(rel_path):
    recipe_path = rel_path[:-5]
    parts = split_path(recipe_path)
    for ext in ['jpg', 'png']:
        if os.path.isfile(os.path.join(RECIPE_DIR, recipe_path+'.'+ext)):
            return recipe_path+'.'+ext
    return None

def get_image(rel_path):
    path = os.path.join(RECIPE_DIR, rel_path)
    with open(path, 'rb') as f:
        return f.read()

def render_folder(rel_path):
    full_path = os.path.join(RECIPE_DIR, rel_path)
    _, sub_folders, files = next(os.walk(full_path))
    parent_folders = split_path(rel_path)

    sub_folders = sorted([x for x in sub_folders if x not in EXCLUDE_DIRS])
    recipes = sorted([f[:-5] for f in files if f.endswith('.cook')])

    return jinja_env.get_template("folder.html").render(
        parent_folders=parent_folders,
        sub_folders=sub_folders,
        recipes=recipes,
    )

def render_recipe(rel_path, is_printable, color):
    full_path = os.path.join(RECIPE_DIR, rel_path)

    parent_folders = split_path(rel_path)
    parent_folders[-1] = parent_folders[-1][:-5]

    title = parent_folders[-1]
    with open(full_path) as f:
        recipe = Recipe.parse(f.read())
    image = get_image_name(rel_path)

    highlighted_steps = highlight_steps(recipe.ingredients, recipe.steps)

    cooklang_link = '/cookbook/' + rel_path
    printable_link = '/printable/' + rel_path[:-5]


    return jinja_env.get_template('recipe.html').render(
        parent_folders=parent_folders,
        ingredients=recipe.ingredients,
        steps=highlighted_steps,
        metadata=recipe.metadata,
        title=title,
        image=image,
        cooklang_link=cooklang_link,
        printable_link=printable_link,
        is_printable=is_printable,
        color=color,
    )

@app.get('/')
def index():
    return redirect('/cookbook/')

@app.get('/cookbook/')
def cookbook():
    return render_folder('')

@app.get('/cookbook/<path:path>.png')
def png(path):
    return get_image(path+'.png')

@app.get('/cookbook/<path:path>.jpg')
def jpg(path):
    return get_image(path+'.jpg')

@app.get('/cookbook/<path:path>.cook')
def cook(path):
    path += '.cook'
    matching_path = find_matching_path(path)

    if matching_path == None:
        return 'Cook file not found', 404

    joined_path = os.path.join(RECIPE_DIR, matching_path)
    with open(joined_path) as f:
        response = Response(f.read(), mimetype='text/plain')
    response.headers['Content-Disposition'] = 'attachment; filename=' + urllib.parse.quote(os.path.split(path)[1])
    return response

@app.get('/cookbook/<path:path>/')
def recipe_and_folder(path):
    matching_path = find_matching_path(path)
    if matching_path != None:
        joined_path = os.path.join(RECIPE_DIR, matching_path)
        if os.path.isdir(joined_path):
            return render_folder(matching_path)

    matching_path = find_matching_path(path + '.cook')
    if matching_path != None:
        joined_path = os.path.join(RECIPE_DIR, matching_path)
        if os.path.isfile(joined_path):
            color = request.args.get('color')
            if color:
                color = color.split(',')
            return render_recipe(matching_path, False, color)

    return 'Recipe/Folder not found', 404

@app.get('/printable/<path:path>/')
def printable(path):
    matching_path = find_matching_path(path + '.cook')
    if matching_path != None:
        joined_path = os.path.join(RECIPE_DIR, matching_path)
        if os.path.isfile(joined_path):
            return render_recipe(matching_path, True, None)

    return 'Recipe not found', 404
