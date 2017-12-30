import os
import subprocess
import maya.cmds as cmds

import snpPipeline.utilities as utilities
import snpPipeline.shellinterop as shinterop
from snpPipeline import ROOT_DIR, BLENDER_DIR, BLENDER_SCRIPTS_DIR

STARTUP_SCRIPTS = ("snpRenderSystem.py",)
PARALLELNESS = 3

def chunk(xs,n):
    return [xs[index::n] for index in range(n)]

def parallel_render(scenes):
    chunked_scenes = chunk(scenes, PARALLELNESS)

    for scenes in chunked_scenes:
        if len(scenes) == 0:
            continue

        cmd = "snp_renderScene("
        for file in scenes:
            cmd += '\"' + file + '\"'
            if not file == scenes[-1]:
                cmd += ', '

        cmd += ')'

        run((cmd, ), background=True, shell=True, parallel=True)


def run(commands, background=False, shell=False, parallel=True, blend_file=''):
    script = ""
    bg_flag = "--background --factory-startup " if background else ""

    # compose script file
    for start_script in STARTUP_SCRIPTS:
        filename = os.path.join(BLENDER_SCRIPTS_DIR, start_script)
        script += "exec(compile(open(\"" + filename + "\").read(), \"" + filename + "\", 'exec'))\n"

    script += "snp_locateLibrary(\"" + BLENDER_SCRIPTS_DIR + "\")\n"

    for cmd in commands:
        script += cmd + '\n'

    # export script
    script = utilities.to_unicode(script).replace('\\', '/')
    path = os.path.join(ROOT_DIR, "_temp", "__maya_to_blender_interop__.py")

    if parallel:
        new_path = path
        index = 1
        while(os.path.exists(new_path)):
            new_path = path.replace(".py", str(index) + ".py")
            index += 1

        path = new_path


    with open(path, mode="w") as file:
        file.write(script.encode("utf8"))

    bl = os.path.normpath(os.path.join(BLENDER_DIR, "blender"))
    cmd = '"' + bl + '" ' + bg_flag + "--python " + path + ' ' + blend_file
    
    if shell:
        shinterop.run(cmd, force_posix=False)
    else:
        subprocess.Popen(cmd, shell=False)
