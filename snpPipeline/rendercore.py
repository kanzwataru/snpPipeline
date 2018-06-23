"""
Module for internal render manager related tasks
"""
import os
import platform

from snpPipeline import ROOT_DIR
from snpPipeline.backupman import BACKUP_DIR
from snpPipeline.shellinterop import *

# --
# Platform-specifics
if platform.system() == "Windows":
    nl = "\r\n"
    header = "@echo off\nset MAYA_VP2_DEVICE_OVERRIDE=VirtualDeviceDx11\n set MAYA_OGS_GPU_MEMORY_LIMIT=128\nset MAYA_NO_PARALLEL_DRAW=1\nset MAYA_NO_TBB=1\nset MAYA_NO_PARALLEL_MEMCPY=1"
    render_cmd = "\"C:\\Program Files\\Autodesk\\Maya2017\\bin\\render.exe\""
    ext = ".bat"
    last = ""
elif platform.system() == "Linux":
    nl = "\n"
    header = "#!/bin/sh"
    render_cmd = "Render"
    ext = ".sh"
    last = "read -p \"Press Return to continue...\""
elif platform.system() == "Darwin":
    nl = "\n"
    header = "#!/bin/sh"
    render_cmd = "/Applications/Autodesk/maya2017/Maya.app/Contents/bin/Render"
    ext = ".sh"
    last = "read -p \"Press Return to continue...\""
# --


def getCompDirFor(scene_name):
    return os.path.join(ROOT_DIR, "3_Comp", scene_name)


def createCompDirFor(scene_name):
    shot_dir = getCompDirFor(scene_name)
    if not os.path.exists(shot_dir):
        os.mkdir(shot_dir)
        os.mkdir(os.path.join(shot_dir, "Footage"))
        os.mkdir(os.path.join(shot_dir, "Renders"))

    return shot_dir


def formatRenderCommand(outputDir, filetype, mayaFile):
    return "{render} -rd {outputDir} -im \"<RenderLayer>/<RenderLayer>\" -of {filetype} {mayaFile}".format(
                            render=render_cmd, outputDir=outputDir, filetype=filetype, mayaFile=mayaFile)


def scenesToShellScript(scenes_versions, filetype):
    script = header + nl
    for scene, ver in scenes_versions.iteritems():
        render_dir = os.path.join(createCompDirFor(scene.name), "Footage")
        script += formatRenderCommand(render_dir, filetype, scene.fileFromVersion(ver)) + nl

    script += nl + last

    return script


def renderOut(scenes_versions, filetype):
    script = scenesToShellScript(scenes_versions, filetype)
    script_file = os.path.join(ROOT_DIR, "_temp", "render_script" + ext)

    with open(script_file, mode="w") as file:
        file.write(script)

    run(script_file, force_posix=False)
    #os.remove(script_file)
