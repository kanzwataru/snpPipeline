"""
Pipeline for final film
"""
import os

import core
reload(core)
import dataTypes
reload(dataTypes)
import backupman
reload(backupman)

import gui
reload(gui)

PROJECT_ROOT_VAR="FINAL_FILM_ROOT"
ROOT_DIR = os.path.normpath(os.environ[PROJECT_ROOT_VAR])

def createAssetManager(atype):
    # Make Manager
    manager = gui.assetManager.AssetManager(atype)

    return manager

def createShotManager():
    # Make Manager
    manager = gui.assetManager.ShotManager()

    return manager

def backupProject():
    backupman.backupProject(ROOT_DIR)

def syncToUSB():
    gui.misc.DialogBoxUI("Sync TO flash drive?",
                         message="Sync TO the flash drive? (PC -> USB)",
                         hasField=False,
                         requireField=False,
                         yesLabel="TO",
                         noLabel="Cancel",
                         yesAction=lambda x: backupman.syncToUSB(ROOT_DIR))

def syncFromUSB():
    def callback(*args):
        gui.misc.DialogBoxUI("Are you sure?",
                     message="Have you backed everything up?",
                     hasField=False,
                     requireField=False,
                     yesLabel="Yes I have",
                     noLabel="No",
                     yesAction=lambda x: backupman.syncFromUSB(ROOT_DIR))

    gui.misc.DialogBoxUI("Sync FROM flash drive?",
                         message="Sync FROM the flash drive? (USB -> PC)",
                         hasField=False,
                         requireField=False,
                         yesLabel="FROM",
                         noLabel="Cancel",
                         yesAction=callback)

"""
def saveAsVersion():
    gui.misc.DialogBoxUI("Save As New Version",
                    message="Version Description (optional):",
                    hasField=True,
                    requireField=False,
                    yesLabel="Save",
                    noLabel="Cancel",
                    yesAction=core.saveNewVersion)
"""

# tests
def testShotClass():
    path = "C:\\_testing\\pipelineTest\\1_3DCG\\Scenes\\C20"

    shot = dataTypes.Shot(path)

    assets = shot.assets

    for asset in assets:
        print "name: " + str(asset.name)
        print "atype: " + str(asset.atype)
        print "versions: " + str(asset.versions)
        print "latest: " + str(asset.latest)
        print "master status: " + str(asset.masterstatus)
        print "--"