import os
import json
import bpy
import inspect

from itertools import chain
from math import radians, degrees

def snp_locateLibrary(library_path):
    global SNP_LIBRARY_PATH
    global SNP_BASE_DATA
    SNP_LIBRARY_PATH = library_path

    # import materials and linestyles from library
    library = os.path.join(SNP_LIBRARY_PATH, "library.blend")
    freestyle_d = "\\FreestyleLineStyle\\"
    material_d = "\\Material\\"

    path = os.path.join(SNP_LIBRARY_PATH, "base_data.json")
    with open(path, mode='r') as file:
        j = file.read()

    root = json.loads(j)
    SNP_BASE_DATA = root


def snp_importLibrary():
    root = SNP_BASE_DATA
    library = os.path.join(SNP_LIBRARY_PATH, "library.blend")
    for lib, contents in root["library"].items():
        for file in contents:
            print(file)
            print(lib)
            bpy.ops.wm.append(filename=file, directory=library + "\\" + lib + "\\")

    """
    for mat in root["library"]["Materials"]:
        bpy.ops.wm.append(filename=mat, directory=library + material_d)

    for line_style in root["library"]["FreestyleLineStyles"]:
        bpy.ops.wm.append(filename=line_style, directory=library + freestyle_d)
    """

    for datablock in chain(bpy.data.materials, bpy.data.textures):
        datablock.use_fake_user = True


def snp_getBaseName(maya_node):
    return maya_node.split('|')[-1]


def snp_setLayer(layers, indices):
    for i in range(20):
        layers[i] = (i in indices)

def snp_addAreaLight(loc):
    """
    Based on https://stackoverflow.com/questions/17355617/can-you-add-a-light-source-in-blender-using-python
    """
    scene = bpy.data.scenes["Scene"]

    # Create new lamp datablock
    lamp_data = bpy.data.lamps.new(name=loc.name + "_LAMPDATA", type="AREA")
    lamp_data.shadow_method = "RAY_SHADOW"

    # Create new object with our lamp datablock
    lamp_object = bpy.data.objects.new(name=loc.name + "_LAMP", object_data=lamp_data)

    # Link lamp object to the scene so it'll appear in this scene
    scene.objects.link(lamp_object)

    # Match locator
    lamp_object.location = loc.location
    lamp_object.rotation_euler = [a + b for a, b in zip(loc.rotation_euler, (radians(90),0,0))]


def snp_createLineset(name, layer, flags, style):
    # create
    lineset = layer.freestyle_settings.linesets.new(name)
    lineset.select_by_group = True
    lineset.group = bpy.data.groups[name]
    lineset.linestyle = bpy.data.linestyles[style]

    # set flags
    all_flags = [x[0] for x in inspect.getmembers(lineset) 
                 if x[0].startswith("select_") and not "_by_" in x[0]]

    for flag in all_flags:
        short_name = flag.replace("select_", '')
        setattr(lineset, flag,
                (short_name in flags))

def snp_assignMaterials(nodes):
    root = SNP_BASE_DATA
    print(nodes)
    for node in nodes:
        if not node.type == "MESH":
            continue
        # assign SHADOW
        shad_mat = bpy.data.materials["SHADOW"]

        if node.data.materials:
            node.data.materials[0] = shad_mat
        else:
            node.data.materials.append(shad_mat)

    for mat_name, overrides in root["material_overrides"].items():
        mat = bpy.data.materials[mat_name]

        for obj in overrides:
            try:
                node = bpy.data.objects[obj]
                if not node.type == "MESH":
                    continue
            except:
                continue

            if node.data.materials:
                node.data.materials[0] = mat
            else:
                node.data.materials.append(mat)


def snp_createGroup(name, contents):
    # create group if necessary
    if name not in bpy.data.groups.keys():
        group = bpy.data.groups.new(name=name)

    for node in contents:
        try:
            group.objects.link(node)
        except:
            pass


def snp_addMayaObjsToLayer(nodes, layer_index):
    """
    Adds maya nodes to layer

    Returns list of the nodes that were valid
    """
    valid_blender_nodes = []
    for m_node in nodes:
        try:
            b_node = bpy.data.objects[snp_getBaseName(m_node)]
        except:
            continue

        snp_setLayer(b_node.layers, (0, layer_index))

        valid_blender_nodes.append(b_node)

    snp_assignMaterials(valid_blender_nodes)
    return valid_blender_nodes


def snp_setupFreestyle(render_layer, layer_nodes):
    """
    Adds freestyle line sets according to library's
    base_data.json
    """
    root = SNP_BASE_DATA

    processed_nodes = []
    for name, lineset in root["groups"].items():
        if name == "Default":
            continue

        lineset_nodes = [x for x in layer_nodes if x.name in lineset["geo"]]
        processed_nodes += lineset_nodes

        if not lineset_nodes:
            continue

        snp_createGroup(name, processed_nodes)
        snp_createLineset(name, render_layer, lineset["flags"], lineset["style"])
        #print(name + ": " + str(lineset_nodes))

    missing = [x for x in layer_nodes if x not in processed_nodes]
    snp_createGroup("DEFAULT", missing)
    snp_createLineset("DEFAULT", render_layer, root["groups"]["Default"]["flags"], lineset["style"])

    #print("TOTAL: " + str(processed_nodes))


def snp_addLineLayer(name, contents, index):
    scene = bpy.data.scenes["Scene"]
    layer = scene.render.layers.new(name)

    layer.use_solid = False
    layer.use_halo = False
    layer.use_sky = False
    layer.use_edge_enhance = False
    layer.use_strand = False

    # this is the display layer that corresponds
    # to this render layer
    snp_setLayer(layer.layers, (index, ))

    # add all items to display layers
    valid_nodes = snp_addMayaObjsToLayer(contents, index)

    # set up freestyle settings
    snp_setupFreestyle(layer, valid_nodes)


def snp_loadScene(alembic_path, json_path):
    # remove default camera and poitn light
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    # load alembic
    bpy.ops.wm.alembic_import(filepath=alembic_path, as_background_job=False)

    # load json metadata
    with open(json_path, mode='r') as file:
        j = file.read()

    root = json.loads(j)

    # set up render layers
    # (the first scene layer is not used)
    scene_layer_i = 1
    layers = root["render_layers"]
    for layer in layers.keys():
        if "__CEL" in layer:
            scene_layer_i += 1
            snp_addLineLayer(layer.replace("__CEL", "__LINE"),
                             layers[layer],
                             scene_layer_i)

    # set up scene settings
    scene = bpy.data.scenes["Scene"]

    scene.render.use_freestyle = True
    scene.render.resolution_percentage = 100
    scene.render.image_settings.compression = 0
    scene.render.filepath = root["render_output"]

    scene.render.layers[0].name = "SHADOW"
    scene.render.layers["SHADOW"].use_halo = False
    scene.render.layers["SHADOW"].use_sky = False
    scene.render.layers["SHADOW"].use_strand = False
    scene.render.layers["SHADOW"].use_freestyle = False

    # set active camera
    camera = bpy.data.objects[root["main_cam"].split('|')[-1].replace("Shape", "")]
    scene.camera = camera

    # set up lights
    for light_name in root["lights"]:
        try:
            light_loc = bpy.data.objects[light_name]
        except KeyError:
            continue

        snp_addAreaLight(light_loc)

    # finally, save out the file
    bpy.ops.wm.save_mainfile(filepath=json_path.replace(".json", ".blend"))


def snp_renderScene(*args):
    for file in args:
        # open scene
        bpy.ops.wm.open_mainfile(filepath=file)

        scene = bpy.data.scenes["Scene"]
        scene.render.use_compositing = False
        scene.render.use_sequencer = False

        orig_path = scene.render.filepath

        # turn off all layers first, then loop through them
        # one by one to render them out seperately
        for layer in scene.render.layers:
            layer.use = False

        for layer in scene.render.layers:
            layer.use = True

            # render
            scene.render.filepath = os.path.join(orig_path, layer.name, layer.name + '_')
            bpy.ops.render.render(animation=True)

            layer.use = False

    # close blender (don't save scene)
    bpy.ops.wm.quit_blender()