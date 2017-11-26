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
    newline = "\r\n"
    render_cmd = "C:\\Program Files\\Autodesk\\Maya2017\\bin\\render.exe"
    ext = "bat"
elif platform.system() == "Linux":
    newline = "\n"
    render_cmd = "Render"
    ext = "sh"
elif platform.system() == "Darwin":
    newline = "\n"
    render_cmd = "/Applications/Autodesk/maya2017/Maya.app/Contents/bin/Render"
    ext = "sh"
# --


def createCompDirFor(scene):
    shot_dir = os.path.join(ROOT_DIR, "3_Comp", scene.name)
    if not os.path.exists(shot_dir):
        os.mkdir(shot_dir)
        os.mkdir(os.path.join(shot_dir, "Footage"))
        os.mkdir(os.path.join(shot_dir, "Renders"))

    return shot_dir


def formatRenderCommand(outputDir, fileType, mayaFile):
    return "{render} -rd {outputDir} -im \"<RenderLayer>/<RenderLayer>\" -of {fileType} {mayaFile}".format(
                            render=render_cmd, outputDir=outputDir, fileType=fileType, mayaFile=mayaFile)


def scenesToShellScript(scenes_versions, fileType):
    script = ""
    for scene, ver in scenes_versions.iteritems():
        render_dir = os.path.join(createCompDirFor(scene), "Footage")
        script += formatRenderCommand(render_dir, fileType, scene.fileFromVersion(ver)) + newline

    script += "read -p \"Press Return to continue...\""

    return script


def renderOut(scenes_versions, fileType):
    script = scenesToShellScript(scenes_versions, fileType)
    script_file = os.path.join(ROOT_DIR, "render_script" + ext)

    with open(script_file, mode="w") as file:
        file.write(script)

    run(script_file)
    os.remove(script_file)
