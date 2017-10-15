"""
Module for internal render manager related tasks
"""
import os
import platform

from snpPipeline import ROOT_DIR
from snpPipeline.backupman import BACKUP_DIR
from snpPipeline.shellinterop import *


def createCompDirFor(shot):
    pass


def formatRenderCommand(outputDir, fileType, mayaFile):
    return "Render -rd {outputDir} -im \"<RenderLayer>/<RenderLayer>\" -of {fileType} {mayaFile}".format(outputDir=outputDir, fileType=fileType, mayaFile=mayaFile)

class RenderList(object):
    def __init__(self, scenes, fileType):
        self.scenes = []

    def toShellScript(self):
        pass


def renderOut(renderList):
    pass
