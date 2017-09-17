"""
Module for core pipeline behaviour
"""
import os
import sys
import subprocess
import time
import shutil
import maya.cmds as cmds
import maya.mel as mel

import snpPipeline.dataTypes
dty = snpPipeline.dataTypes

from send2trash import send2trash

#reload(dty)
#reload(assetManager)

def archiveFiles(files):
    pass

def openInFileManager(path):
    if sys.platform=='win32':
        os.startfile(path)

    elif sys.platform=='darwin':
        subprocess.Popen(['open', path])

    else:
        subprocess.Popen(['xdg-open', path])

def getAssets(atype):
    # get the dir where these assets are stored
    path = dty.pathOfAssetType(atype)

    # list directory
    try:
    	assets = os.listdir(path)
    except OSError:
    	cmds.warning("No assets")
    	return None

    # return list of assets
    return assets

def getOpenAssetInfo():
    # get root directory of pipeline
    from snpPipeline import ROOT_DIR
    root = ROOT_DIR

    # get opened file path
    scenepath = os.path.normpath(cmds.file(query=True, sn=True, shortName=False, withoutCopyNumber=True))
    print scenepath
    print root
    # check if we're in the project directory
    if not (root in scenepath):
        raise Exception("Current scene is not inside the pipeline folder")

    # parse the asset name
    splitdir = os.path.split(scenepath)

    scenefilename = splitdir[1]
    name = os.path.basename(splitdir[0])

    # parse the asset type
    assetcategorydir = os.path.split(os.path.split(splitdir[0])[0])[1]
    atype = dty.getAssetTypeFromDir(assetcategorydir)

    # remove the file extension
    scenefilename = os.path.splitext(scenefilename)[0]

    # parse the scene filename (TODO: make part of dataTypes.py)
    splitname = scenefilename.split('_')

    file_aname = splitname[0]
    file_atype = splitname[1]
    version = splitname[2]

    # if this is a shot, make sure we have the shot stage type
    if assetcategorydir == "Scenes":
        atype = "shot"
        shotstage = dty.shotstageFor(file_atype)
        file_atype = "shot"
    else:
        shotstage = None

    # double-check right quick to make sure the scene matches the folder
    if file_aname != name or file_atype != atype:
        raise Exception("Current scene is invalid asset: Name and Type do not match directory")

    # return asset name, version, and type
    return dty.SceneInfo(name, version, atype, shotstage)

def getOpenAsset():
    try:
        info = getOpenAssetInfo()
    except Exception, Argument:
        raise Exception(Argument)

    path = dty.pathOfAssetType(info.atype, named=info.name)

    return dty.Asset(path, info.atype)

def checkIfAlreadyOpen(asset, version=None):
    # get opened file name
    scene = cmds.file(query=True, sn=True, shortName=True, withoutCopyNumber=True)

    if version == None or version == "MASTER":
        ## We're checking if it's the same asset, no matter the version

        return scene.startswith(asset.name + "_" + asset.atype)

    else:
        ## We're checking the exact version

        # get filename of asset
        filename = asset.filenameFromVersion(version)

        # check
        return scene == filename

def renameAssetFiles(files, inDir, toName):
    # Rename all the files
    for file in files:
        splitname = file.split('_')
        splitname[0] = toName

        newname = '_'.join(splitname)

        oldpath = os.path.join(inDir, file)
        newpath = os.path.join(inDir, newname)

        os.rename(oldpath, newpath)

    # Rename directory
    splitdir = os.path.split(inDir)
    newdir = os.path.join(splitdir[0], toName)

    os.rename(inDir, newdir)

    return newdir

def renameAsset(asset, name):
    # get list of asset's files
    allfiles = asset.getAllFiles(asFullpath=False, includingPointer=True)
    assetdir = asset.getBaseDir()

    renameAssetFiles(allfiles, inDir=assetdir, toName=name)

def duplicateAsset(asset, name):
    # check if asset already exists before leaping
    existingassets = getAssets(asset.atype)

    while name in existingassets:
        name += "DUP"

    # get list of asset's files
    allfiles = asset.getAllFiles(asFullpath=False, includingPointer=True)

    # duplicate asset directory
    olddir = asset.getBaseDir()

    olddir_base = os.path.split(olddir)
    newdirname = olddir_base[1] + "_TEMP_" + time.strftime("%H%M%S")

    newdir = os.path.join(olddir_base[0], newdirname)

    shutil.copytree(olddir, newdir)

    # rename asset
    newdir = renameAssetFiles(allfiles, inDir=newdir, toName=name)

    if asset.atype == "shot":
        return dty.Shot(newdir)
    else:
        return dty.Asset(newdir, asset.atype)

def deleteAsset(asset):
    # get asset path
    path = asset.getBaseDir()

    # send to trash
    send2trash(path)

def publishAsset(asset, version):
    # delete master if exists
    if asset.masterstatus != 0:
        master = asset.fileFromVersion("MASTER")
        pointerfile = asset.getPointerFile()

        if os.path.exists(master):
            os.remove(master)

        if pointerfile:
            os.remove(pointerfile)

    # get version path
    versionfile = asset.fileFromVersion(version)

    # duplicate version into master
    splitdir = os.path.split(versionfile)
    master = os.path.join(splitdir[0], asset.filenameFromVersion("MASTER"))

    shutil.copyfile(versionfile, master)

    # make pointer file
    pointerpath = os.path.join(splitdir[0], 
        asset.filenameFromVersion("MASTER", ".pointer"))

    with open(pointerpath, mode="w") as file:
        file.write(str(version))

def exploreAsset(asset):
    if not asset:
        return

    openInFileManager(asset.getBaseDir())

def transferVersion(version, ofShot, ofStage):
    """
    Transfer a version scene file from one stage
    to another

        (LO -> Anim -> Lighting)

        Ex: "C20_1-LO_004" -> "C20_2-Anim_001_FROM-LO"
    """

    # figure out what the next version is
    if ofStage == "Layout":
        nextstage = "Animation"
        nextstage_type = "2-anim"
        desc = "FROM-LO"
    elif ofStage == "Animation":
        nextstage = "Lighting"
        nextstage_type = "3-lighting"
        desc = "FROM-ANIM"
    else:
        raise Exception("Internal Error: Invalid shot stage '" + ofStage + "'")

    # get the path+filename
    fullpath = ofShot.shotstages[ofStage].fileFromVersion(version)

    assetpath = os.path.split(fullpath)[0]
    filename = os.path.split(fullpath)[1]

    # get the latest version of the next stage
    latest = ofShot.shotstages[nextstage].latest
    latest = 000 if not latest else int(latest)

    # increment version and add _FROM-{stage}
    newver = dty._addPadding(str(latest + 1))

    newfilename = '_'.join([ofShot.name, nextstage_type, newver, desc])
    newfilename += ".ma"

    # copy file
    newfullpath = os.path.join(assetpath, newfilename)

    shutil.copyfile(fullpath, newfullpath)

def createAssetDir(name, atype):
    # make asset directory
    assetDir = dty.pathOfAssetType(atype, named=name)
    
    if(os.path.exists(assetDir)):
        cmds.warning("Asset already exists")
        return None

    os.mkdir(assetDir)

    # make subdirectories
    if atype == "shot":
        os.mkdir(os.path.join(assetDir, "LO"))
        os.mkdir(os.path.join(assetDir, "Blasts"))
    else:
        os.mkdir(os.path.join(assetDir, "Textures"))
        os.mkdir(os.path.join(assetDir, "Renders"))
        os.mkdir(os.path.join(assetDir, "Ref"))

        if atype == "rig":
            os.mkdir(os.path.join(assetDir, "Model"))

    print "Made asset directory at: " + assetDir

    return assetDir

def createAsset(name, atype):
    assetDir = createAssetDir(name, atype)

    # new scene
    cmds.file(new=True, force=True)

    atype = "1-LO" if atype == "shot" else atype

    # get naming conventions (TODO: generalize)
    filename = name + "_" + atype + "_001.ma"

    # save scene as asset
    filepath = os.path.join(assetDir, filename)

    cmds.file(rename=filepath)
    cmds.file(save=True, type="mayaAscii")

    # make asset
    return dty.Asset(assetDir, atype)

def createPipeline():
    # get root directory of pipeline
    from snpPipeline import ROOT_DIR, PROJECT_ROOT_VAR
    root = ROOT_DIR

    # make directory if non-existent
    try:
        contents = os.listdir(root)
    except OSError:
        os.makedirs(root)
        contents = os.listdir(root)

    # don't make anything if the directory is not empty
    #   (to be on the safe side)
    if contents != []:
        cmds.warning("Could not create new pipeline at " + root + " (root directory not empty)")
        return

    # create main folders
    os.mkdir(os.path.join(root, "0_Preproduction"))
    os.mkdir(os.path.join(root, "1_3DCG"))
    os.mkdir(os.path.join(root, "2_2DFX"))
    os.mkdir(os.path.join(root, "3_Comp"))
    os.mkdir(os.path.join(root, "4_Editorial"))

    # create sub-folders
    os.mkdir(os.path.join(root, "0_Preproduction", "Animatics"))
    os.mkdir(os.path.join(root, "0_Preproduction", "Concept"))
    os.mkdir(os.path.join(root, "0_Preproduction", "Reference"))

    os.mkdir(os.path.join(root, "1_3DCG", "Env"))
    os.mkdir(os.path.join(root, "1_3DCG", "Props"))
    os.mkdir(os.path.join(root, "1_3DCG", "Rigs"))
    os.mkdir(os.path.join(root, "1_3DCG", "Scenes"))

    os.mkdir(os.path.join(root, "4_Editorial", "Footage"))
    os.mkdir(os.path.join(root, "4_Editorial", "Audio"))
    os.mkdir(os.path.join(root, "4_Editorial", "Renders"))

    # create maya project
    # (use forward slashes even on Windows because MEL likes that better)
    mayaproj = os.environ[PROJECT_ROOT_VAR] + "/" + "_mayaproj"
    os.mkdir(mayaproj)

    print (mayaproj, )


    # -- from: https://fredrikaverpil.github.io/2014/08/06/set-maya-project-and-create-folder-structure/
    mel.eval('setProject \"' + mayaproj + '\"')

    for file_rule in cmds.workspace(query=True, fileRuleList=True):
        file_rule_dir = cmds.workspace(fileRuleEntry=file_rule)
        maya_file_rule_dir = os.path.join( mayaproj, file_rule_dir)
        
        if not os.path.exists( maya_file_rule_dir ):
            os.makedirs( maya_file_rule_dir )

