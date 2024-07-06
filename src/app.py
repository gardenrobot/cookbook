from flask import Flask, send_from_directory, redirect
from cooklang import Recipe
import os
from jinja2 import Environment, FileSystemLoader
import urllib

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
RECIPE_DIR = os.path.join(BASE_DIR, 'recipes')
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

EXCLUDE_DIRS = ['config']

app = Flask(
    __name__,
    static_url_path='/static',
    static_folder=STATIC_DIR,
)

jinja_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

def get_parent_folders(rel_path):
    """
        Take a user supplied path and return a list of tuples.
        First item of the tuple is a part of the path.
        Second items is the relative path up until that point.
        Ex: 'a/b/c' => [('a', 'a'), ('b', 'a/b'), ('c', 'a/b/c')]
    """
    all_paths = []
    while (split_path := os.path.split(rel_path))[0] != '':
        if (path := split_path[1]) != '':
            all_paths.append(path)
        rel_path = split_path[0]
    all_paths.append(split_path[1])
    all_paths.reverse()

    final = []
    last_path = ''
    for part in all_paths:
        last_path = os.path.join(last_path, part)
        final.append((part, urllib.parse.quote(last_path)))
    return final


def render_folder(rel_path, full_path):
    _, sub_folders, files = next(os.walk(full_path))
    recipes = [f[:-5] for f in files if f.endswith('.cook')]
    parent_folders = get_parent_folders(rel_path)

    sub_folders = [x for x in sub_folders if x not in EXCLUDE_DIRS]

    tmp = jinja_env.get_template("folder.html").render(
        parent_folders=parent_folders,
        sub_folders=sub_folders,
        recipes=recipes,
    )
    return tmp

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

def get_image_name(path, name):
    base = path[:-5]
    for img_ext in ['jpg', 'png']:
        if os.path.isfile(base+'.'+img_ext):
            return name+'.'+img_ext
    return None

def get_image(rel_path):
    path = os.path.join(RECIPE_DIR, rel_path)
    with open(path, 'rb') as f:
        return f.read()


def render_recipe(rel_path, full_path):
    parent_folders = get_parent_folders(rel_path)
    name = parent_folders[-1][0]
    with open(full_path) as f:
        recipe = Recipe.parse(f.read())
    image = get_image_name(full_path, name)

    highlighted_steps = highlight_steps(recipe.ingredients, recipe.steps)


    return jinja_env.get_template('recipe.html').render(
        parent_folders=parent_folders,
        ingredients=recipe.ingredients,
        steps=highlighted_steps,
        metadata=recipe.metadata,
        name=name,
        image=image,
    )

@app.get('/')
def index():
    return redirect('/cookbook/')

@app.get('/cookbook/')
def cookbook():
    return render_folder('', RECIPE_DIR)

@app.get('/cookbook/<path:path>')
def all_routes(path):

    # check file exists and is not doing dir traversal attack
    joined_path = os.path.join(RECIPE_DIR, path)
    if not os.path.exists(joined_path) and not os.path.exists(joined_path+'.cook'):
        return "Invalid path", 404
    if not is_witin_recipes(joined_path):
        return "Restricted path", 403

    # folder
    if os.path.isdir(joined_path):
        if not path.endswith('/') and path != '':
            return redirect('/cookbook/'+path+'/')
        return render_folder(path, joined_path)

    # image file
    if path.endswith('.jpg') or path.endswith('.png'):
        return get_image(path)

    # recipe file
    recipe_path = joined_path + '.cook'
    if os.path.isfile(recipe_path):
        return render_recipe(path, recipe_path)

    return "Unknown error", 500
