"""
Module for rendering with Render Sequence
"""
import os
import shutil
import maya.cmds as cmds
import maya.mel as mel

from snpPipeline import ROOT_DIR
from snpPipeline.rendercore import getCompDirFor, createCompDirFor

PROJ = os.path.join(ROOT_DIR, '_mayaproj')
IMAGES = os.path.join(PROJ, 'images')
IMAGES_TMP = os.path.join(IMAGES, 'tmp')

def _setCorrectProject():
    """
    Set project to current snpPipeline project
    """
    print(PROJ)
    mel.eval('setProject "' + PROJ.replace('\\', '/') + '"')


def _emptyImages():
    """
    Empty out the images folder
    """
    if os.path.exists(IMAGES):
        for filename in os.listdir(IMAGES):
            filepath = os.path.join(IMAGES, filename)

            try:
                shutil.rmtree(filepath)
            except OSError:
                os.remove(filepath)


def _getRenderLayers():
    all_layers = cmds.ls(type="renderLayer")
    return [x for x in all_layers if (':' not in x and x != 'defaultRenderLayer')]


def _switchLayer(layer):
    cmds.editRenderLayerGlobals(crl=layer)


def _renderSeq():
    cmds.optionVar(intValue=("renderSequenceAllCameras", True))
    cmds.optionVar(intValue=("renderSequenceAllLayers", False))

    mel.eval("RenderSequence")


def _getRenderedFramesFolder(layer_name):
    files = os.listdir(IMAGES_TMP)
    print(files)
    if not files:
        raise Exception("No files in rendered folder: " + IMAGES)

    if layer_name in files:
        return os.path.join(IMAGES_TMP, layer_name)
    elif layer_name in os.listdir(os.path.join(IMAGES_TMP, files[0])):
        return os.path.join(IMAGES_TMP, files[0], layer_name)
    else:
        raise Exception("Could not locate the rendered frames for layer: " + layer_name)


def renderSeq(shot_name, filetype):
    """
    Renders with Render Sequence then copies
    to appropriate folder
    """
    # sanity checks
    _setCorrectProject()
    _emptyImages()

    # get render layers
    layers = _getRenderLayers()

    for layer in layers:
        # switch render layer and set the folder structure
        _switchLayer(layer)

        cmds.setAttr("defaultRenderGlobals.imageFilePrefix",
                     layer + '/' + layer,
                     type="string")

        # render
        _renderSeq()

        # move folder
        layer_dir = _getRenderedFramesFolder(layer)
        footage_dir = createCompDirFor(shot_name)
        dest_dir = os.path.join(footage_dir, 'footage', layer)
        
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir)

        shutil.copytree(layer_dir, dest_dir)
