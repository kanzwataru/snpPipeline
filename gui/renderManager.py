import os
import json
from sets import Set

import maya.cmds as cmds

import snpPipeline.core as p
import snpPipeline.rendercore as rc
import snpPipeline.blenderinterop as blender
import enoguRefreshShad as ers
import snpPipeline.utilities as utilities
from snpPipeline import PROJECT_ROOT_VAR, ROOT_DIR, BLENDER_DIR
from assetManager import initAssets, p, LATEST_BGC, OLD_BGC, NEUTRAL_BGC

IMAGES_FOLDER_STRUCTURE = "<RenderLayer>/<RenderLayer>"
IMAGE_FORMAT = "png"
BG_COL = (0.17, 0.17, 0.17)
WIDTH = 600
HEIGHT = 700


def getBlastDir(shot):
    path = os.path.join(ROOT_DIR, "4_Editorial", "Footage", "Blasts")
    if not os.path.exists(path):
        os.makedirs(path)

    return path


def getBlenderPath(shot):
    return os.path.join(shot.getBaseDir(), "Blender")


def getBlenderStatus(shot):
    path = getBlenderPath(shot)
    asset = shot.shotstages["Lighting"]
    has = False
    old = False

    if os.path.exists(path):
        files = os.listdir(path)
        has = bool([x for x in files if ".blend" in x])
        
        alembic = os.path.join(path, shot.name)
        if os.path.exists(alembic) and asset.latest:
            latest = asset.fileFromVersion(asset.latest)
            if os.path.exists(latest):
                old = os.path.getmtime(alembic) < os.path.getmtime(latest)

    return has, old


def getRenderStatus(shot):
    path = os.path.join(rc.getCompDirFor(shot), "Footage")
    asset = shot.shotstages["Lighting"]
    has = False
    old = False

    if os.path.exists(path):
        contents = [os.path.join(path, x) for x in os.listdir(path) if x]
        has = bool(contents)
        if has and asset.latest:
            latest = asset.fileFromVersion(asset.latest)
            old = (os.path.getmtime(max(contents, key=os.path.getmtime))
                   < os.path.getmtime(latest))

    return has, old

def initShadMap(shot):
    # find where the shadow map would be
    shad_map = os.path.join(ROOT_DIR, "3_Comp", shot.name, "Footage", "SHADOW", "SHADOW_0008.png")
    shad_map_rel = os.path.join("$" + PROJECT_ROOT_VAR, "3_Comp", shot.name, "Footage", "SHADOW", "SHADOW_0008.png")

    if not os.path.exists(shad_map):
        print(shot.name + " has no valid shadow map, skipping")
        return

    # try to apply it to all Enogu materials
    enogu_materials = ers.getEnoguShaders()
    for mat in enogu_materials:
        try:
            cmds.setAttr(mat + ".shadowMapTex", shad_map_rel, type="string")
            cmds.setAttr(mat + ".useShadowMapTex", True)
        except Exception, e:
            print(e)

    # add hook for refreshing
    cmd = "python(\"import enoguRefreshShad; enoguRefreshShad.updateAll()\");"
    cmds.setAttr("defaultRenderGlobals.preRenderMel", cmd, type="string")
    cmds.setAttr("defaultRenderGlobals.preRenderLayerMel", cmd, type="string")


def fixRenderSettings():
    cmds.setAttr("defaultRenderGlobals.imageFilePrefix",
                     IMAGES_FOLDER_STRUCTURE,
                     type="string")


def sendToBlender(shot, update=False):
    # shot info
    asset = shot.shotstages["Lighting"]
    if not asset.latest:
        cmds.warning("This shot has nothing in the lighting stage")
        return

    path = os.path.join(asset.getBaseDir(), "Blender")
    if not os.path.exists(path):
        os.makedirs(path)

    try:
        asset.openVersion(asset.latest)
    except:
        pass

    # get render cam
    cameras = utilities.getRenderCams()
    if len(cameras) > 1:
        cmds.warning("CAMERA ERROR: Too many cooks!")
        return
    elif len(cameras) == 0:
        cmds.warning("CAMERA ERROR: Not enough cooks!")
        return
    else:
        camera = cameras[0]

    # get meshes from all render layers
    layer_data = {}
    layers = cmds.ls(type="renderLayer")
    for layer in layers:
        if len(layers) > 1 and layer == "defaultRenderLayer":
            continue
        elif ':' in layer:
            continue

        geos = cmds.editRenderLayerMembers(layer, q=True, fullNames=True)

        # (make sure that we have all the children of everything selected as well
        #  since Alembic does NOT traverse hierearchies without using the
        #  super-buggy '-root [thing]' flag)
        geos = geos + cmds.listRelatives(geos, c=True, ad=True, fullPath=True)

        layer_data[layer] = geos
        cmds.select(geos, add=True)
    
    cmds.select(utilities.getRenderCams(), add=True)

    # export alembic file
    start = cmds.playbackOptions(minTime=True, q=True)
    end = cmds.playbackOptions(maxTime=True, q=True)
    abc_path = os.path.join(path, shot.name + ".abc")
    args = "-frameRange " + str(start) + ' ' + str(end) + " -sl -file " + abc_path
    cmds.AbcExport(j=args)



    if update:
        utilities.newFile()
        return

    # export render layer metadata
    try:
        lights = cmds.sets("BL_EXPORT_LIGHTS", q=True)
    except:
        lights = cmds.listRelatives(cmds.ls(type="light"), p=True)

    root = {
        "render_layers": layer_data, 
        "render_output": rc.getCompDirFor(shot),
        "main_cam": camera,
        "lights": lights
    }

    j = json.dumps(root, indent=4, separators=(',',':'))
    j_path = os.path.join(path, shot.name + ".json")

    with open(j_path, mode='w') as file:
        file.write(j)

    # run blender with command
    blender.run(("snp_importLibrary()",
                 "snp_loadScene(\"" + abc_path + '\", \"' + j_path + "\")"))

    utilities.newFile()


def renderBlender(shots):
    blender_files = []
    for shot in shots:
        shot_asset = shot.shotstages["Lighting"]
        bl_dir = getBlenderPath(shot_asset)
        path = os.path.join(bl_dir, shot.name + ".blend")

        blender_files.append(path)

    """
    cmd = "snp_renderScene("
    for file in blender_files:
        cmd += '\"' + file + '\"'
        if not file == blender_files[-1]:
            cmd += ', '

    cmd += ')'
    """

    blender.parallel_render(blender_files)



def render(shots):
    scenes_versions = {}
    for shot in shots:
        shot_asset = shot.shotstages["Lighting"]
        ver = shot_asset.latest

        if not ver:
            continue

        shot_asset.openVersion(ver)

        # set stuff up
        initShadMap(shot)

        fixRenderSettings()

        # add to dict of stuff that gets rendered
        scenes_versions[shot_asset] = ver

        utilities.saveFile()

    utilities.newFile()

    rc.renderOut(scenes_versions, IMAGE_FORMAT)

    cmds.quit()


class RenderManagerUI(object):
    def __init__(self):
        self.ui = {}
        self.root = ""
        self.lastWasDark = True
        self.scenes = {}
        self.b_scenes = {}

        self.createUI()
        self.refresh()

    def getCheckedShots(self):
        shots = []
        for checkbox, shot in self.scenes.iteritems():
            if cmds.iconTextCheckBox(checkbox, q=True, value=True):
                shots.append(shot)

        return shots

    def refresh(self):
        assets = initAssets("shot")

        for asset in assets:
            has_blender, update_blender = getBlenderStatus(asset)
            has_render, update_render = getRenderStatus(asset)
            self.createAssetBtn(asset, has_blender, update_blender, has_render, update_render)

    def getShotStatus(self, shot):
        padlen = 16 - len(shot.name)
        pad = " " * padlen

        sep = " | "
        blank = "   "

        name = shot.name

        if shot.shotstages["Layout"].masterstatus == 2:
            layoutver = "MASTER"
        else:
            layoutver = shot.shotstages["Layout"].latest
            layoutver = blank if not layoutver else layoutver

        if shot.shotstages["Animation"].masterstatus == 2:
            animationver = "MASTER"
        else:
            animationver = shot.shotstages["Animation"].latest
            animationver = blank if not animationver else animationver

        if shot.shotstages["Lighting"].masterstatus == 2:
            lightingver = "MASTER"
        else:
            lightingver = shot.shotstages["Lighting"].latest
            lightingver = blank if not lightingver else lightingver

        assetstatus = pad + "LO: " + layoutver + sep + "Anim: " + animationver + sep + "Light: " + lightingver
        return assetstatus

    def createAssetBtn(self, shot, has_blender, update_blender, has_render, update_render):
        # checkbox
        name = shot.name
        assetstatus = self.getShotStatus(shot)
        color = (0.23, 0.23, 0.23) if self.lastWasDark else (0.3, 0.3, 0.3)
        self.lastWasDark = not self.lastWasDark
        cb = cmds.iconTextCheckBox(
                name,
                width=3 * (WIDTH / 4),
                height=30,
                style='iconAndTextHorizontal',
                image1="render.png",
                label=name + assetstatus,
                bgc=color,
                font="fixedWidthFont",
                parent=self.ui["scrollViewLeft"])

        # status icon
        if has_render:
            if update_render:
                status_col = OLD_BGC
            else:
                status_col = LATEST_BGC
        else:
            status_col = BG_COL

        icn = cmds.button(l=" ",
                          w=(WIDTH / 4 / 4),
                          h=30,
                          bgc=status_col,
                          p=self.ui["scrollViewMid"])

        # blender button
        if has_blender:
            label = "Update"
            callback = lambda _, x=shot: sendToBlender(shot, update=True)
            if update_blender:
                b_col = OLD_BGC
            else:
                b_col = LATEST_BGC
        else:
            label = "Create"
            callback = lambda _, x=shot: sendToBlender(shot, update=False)
            b_col = color
        if not shot.shotstages["Lighting"].latest:
            b_col = BG_COL

        btn = cmds.button(l=label,
                          w=(WIDTH / 4 / 2),
                          h=30,
                          bgc=b_col,
                          p=self.ui["scrollViewRight"],
                          c=callback)

        self.scenes[cb] = shot
        self.b_scenes[btn] = shot


    def createUI(self):
        winName = "renderManagerUI"
        if cmds.window(winName, exists=True):
            cmds.deleteUI(winName)

        try:
            cmds.windowPref(winName, remove=True)
        except:
            pass

        self.ui["win"] = cmds.window(
                                winName,
                                title="RenderManager",
                                width=WIDTH,
                                height=HEIGHT,
                                #sizeable=True,
                                sizeable=False,
                                maximizeButton=False,
                                menuBar=True)

        # create root layout
        self.root = cmds.columnLayout()

        # top toolbar
        self.ui["toolbar"] = cmds.rowLayout(numberOfColumns=6, p=self.root)

        def selAllCallback(*args):
            for checkbox, _ in self.scenes.iteritems():
                cmds.iconTextCheckBox(checkbox, e=True, value=True)
        self.ui["selAllBtn"] = cmds.button(label="Select All",
                                           width=73,
                                           height=30,
                                           p=self.ui["toolbar"],
                                           command=selAllCallback)

        def selNoneCallback(*args):
            for checkbox, _ in self.scenes.iteritems():
                cmds.iconTextCheckBox(checkbox, e=True, value=False)
        self.ui["selNoneBtn"] = cmds.button(label="Select None",
                                           width=73,
                                           height=30,
                                           p=self.ui["toolbar"],
                                           command=selNoneCallback)

        def selInvertCallback(*args):
            for checkbox, _ in self.scenes.iteritems():
                val = cmds.iconTextCheckBox(checkbox, query=True, value=True)
                cmds.iconTextCheckBox(checkbox, e=True, value=not val)
        self.ui["selInvertBtn"] = cmds.button(label="Invert Sel",
                                           width=73,
                                           height=30,
                                           p=self.ui["toolbar"],
                                           command=selInvertCallback)

        cmds.separator(style='none', w=250)

        def exploreCompCallback(*args):
            p.openInFileManager(os.path.join(ROOT_DIR, "3_Comp"))

        self.ui["selInvertBtn"] = cmds.button(label="Comp...",
                                           width=60,
                                           height=30,
                                           p=self.ui["toolbar"],
                                           command=exploreCompCallback)

        def exploreShotCallback(*args):
            p.openInFileManager(os.path.join(ROOT_DIR, "1_3DCG", "Scenes"))

        self.ui["selInvertBtn"] = cmds.button(label="Shots...",
                                           width=60,
                                           height=30,
                                           p=self.ui["toolbar"],
                                           command=exploreShotCallback)

        # create scroll view
        self.ui["scrollView"] = cmds.scrollLayout(
                                    bgc=BG_COL,
                                    w=WIDTH,
                                    h=HEIGHT - 50,
                                    p=self.root)
        self.ui["scrollViewRow"] = cmds.rowLayout(numberOfColumns=3, p=self.ui["scrollView"])

        self.ui["scrollViewLeft"] = cmds.columnLayout(p=self.ui["scrollViewRow"])
        cmds.text(l="Shots")
        self.ui["scrollViewMid"] = cmds.columnLayout(p=self.ui["scrollViewRow"])
        cmds.text(l="Stat")
        self.ui["scrollViewRight"] = cmds.columnLayout(p=self.ui["scrollViewRow"])
        cmds.text(l="Blender")

        # btm toolbar
        self.ui["btmToolbar"] = cmds.rowLayout(numberOfColumns=4, p=self.root)

        def blastCallback(*args):
            for checkbox, shot in self.scenes.iteritems():
                if cmds.iconTextCheckBox(checkbox, q=True, value=True):
                    ss = shot.getLatestShotstage()
                    shot.playblastVersion(shot.shotstages[ss].latest, 
                                          ss, 
                                          toPath=getBlastDir(shot),
                                          resolutionMult=1.0,
                                          terseName=True)

        self.ui["blastBtn"] = cmds.button(label="Playblast",
                                           width=73,
                                           height=50,
                                           p=self.ui["btmToolbar"],
                                           command=blastCallback)


        cmds.separator(style='none', w=220)

        def renderBlenderCallback(*args):
            shots = self.getCheckedShots()
            if not shots:
                cmds.warning("No shots selected")
                return
            renderBlender(shots)

        self.ui["renderBtn"] = cmds.button(label="Render Blender",
                                           width=150,
                                           height=50,
                                           p=self.ui["btmToolbar"],
                                           command=renderBlenderCallback)

        def renderCallback(*args):
            shots = self.getCheckedShots()
            if not shots:
                cmds.warning("No shots selected")
                return
            render(shots)

        self.ui["renderBtn"] = cmds.button(label="Render Maya",
                                           width=150,
                                           height=50,
                                           p=self.ui["btmToolbar"],
                                           command=renderCallback)

        cmds.showWindow()
