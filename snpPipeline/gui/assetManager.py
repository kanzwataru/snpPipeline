"""
UI Classes for Asset Manager (and Shot Manager)
"""
import os
import maya.cmds as cmds
from collections import namedtuple

import snpUtilities as su

import misc
import snpPipeline.core
import snpPipeline.dataTypes

p = snpPipeline.core
dty = snpPipeline.dataTypes

reload(misc)

# Status icons
PROP_ICON = "polyCube.png"
RIG_ICON = "kinJoint.png"
ENV_ICON = "render_envSky.png"
SHOT_ICON = "render.png"

LATEST_BGC = (0.188, 0.394, 0.188)
OLD_BGC = (0.49, 0.482, 0.25)
INVALID_BGC = (0.394, 0.188, 0.188)
NEUTRAL_BGC = (0.23, 0.23, 0.23)

def initAssets(atype):
    # Get asset names from filesystem
    assetNames = p.getAssets(atype)

    # Make Asset objects for each asset
    assets = []
    if assetNames != None:
        for name in assetNames:
            if "_TEMP_" in name or name.startswith("_") or name.startswith("."):
                continue

            path = dty.pathOfAssetType(atype, named=name)

            if not os.path.isdir(path):
                # Don't try to make an asset based on a file
                continue

            if atype == "shot":
                assets.append(dty.Shot(path))
            else:
                assets.append(dty.Asset(path, atype))

    return assets

class Manager(object):
    """
    Base manager root class

    Can manage assets (or shots)
    but does not do version-specific/shot stage-specific stuff
    to alow for code reuse
    """

    def __init__(self, atype):
        # Asset type to browse
        self.atype = atype

        # Selected Asset (or Shot) obj
        self.selectedAsset = None

        # SceneInfo of opened scene
        self.sceneInfo = None

        # Assets dict
        #   name : object
        self.assets = {}

        # Add callbacks
        self.addCallbacks()

        # Add stuff to UI
        self.ui.createUI()
        self.loadUIWith(initAssets(self.atype))

    def addCallbacks(self):
        self.ui.C_deleteAsset = self.deleteAsset
        self.ui.C_newAsset = self.newAsset
        self.ui.C_duplicateAsset = self.duplicateAsset
        self.ui.C_renameAsset = self.renameAsset
        self.ui.C_exploreAsset = self.exploreAsset
        self.ui.C_refreshUI = self.refreshUI
        self.ui.C_switchToAssetNamed = self.switchToAssetNamed

    def addAsset(self, asset):
        """
        Add Assets to the list

        @PARAMS
            asset: Asset object to add
        """
        raise NotImplementedError

    def loadUIWith(self, assets):
        """
        Populate assets
        """
        if assets:
            # Add assets
            for asset in assets:
                self.addAsset(asset)

        # select an asset if it's currently open
        self.switchToOpenAssetIn(assets)

    def switchToOpenAssetIn(self, assets):
        try:
            info = p.getOpenAssetInfo()
        except:
            return

        for asset in assets:
            if info.name == asset.name and info.atype == self.atype:
                self.switchToAssetNamed(info.name, atVersion=info.version)
                self.sceneInfo = info


    def refreshUI(self, atype=None):
        if not atype:
            atype = self.atype

        self.atype = atype

        self.assets = {}
        self.selectedAsset = None
        self.sceneInfo = None
        self.selectedVersion = None

        self.ui.atype = atype
        self.ui.createUI()

        self.loadUIWith(initAssets(self.atype))

    def duplicateAsset(self):
        """
        Physically duplicate the asset,
        including folders and files and everythin'
        """
        def callback(text):
            asset = p.duplicateAsset(self.selectedAsset, text)
            self.addAsset(asset)

        self.ui.CloneDialog(callback)

    def deleteAsset(self):
        """
        Physically send the asset folder to the trash
        """
        if not self.selectedAsset:
            return

        def callback(text):
            p.deleteAsset(self.selectedAsset)
            self.refreshUI()

        self.ui.DeleteDialog(callback, name=self.selectedAsset.name)

    def renameAsset(self):
        """
        Physically rename the asset folder and scene files
        """
        if not self.selectedAsset:
            return

        def callback(text):
            p.renameAsset(self.selectedAsset, text)
            self.refreshUI()

        self.ui.RenameDialog(callback)

    def newAsset(self):
        """
        Physically create a new asset of self.atype
        """
        def callback(text):
            p.createAsset(text, self.atype)
            self.refreshUI()

        self.ui.NewDialog(callback)

    def exploreAsset(self):
        p.exploreAsset(self.selectedAsset)


class AssetManager(Manager):
    """
    Manages assets
    """

    #OVERRIDE
    def __init__(self, atype):
        # GUI
        self.ui = AssetManagerUI(atype)

        # Current asset's selected version
        self.selectedVersion = None

        super(AssetManager, self).__init__(atype)

    #OVERRIDE
    def addCallbacks(self):
        super(AssetManager, self).addCallbacks()

        self.ui.C_importAsset = self.importAsset
        self.ui.C_publishSelectedVersion = self.publishSelectedVersion
        self.ui.C_saveNewVersion = self.saveNewVersion
        self.ui.C_openSelectedVersion = self.openSelectedVersion
        self.ui.C_switchManagerToAssetType = self.switchManagerToAssetType
        self.ui.C_versionListChanged = self.versionListChanged

    #OVERRIDE
    def addAsset(self, asset):
        """
        Add Assets to the list

        @PARAMS
            asset: Asset object to add
        """
        self.assets[asset.name] = asset

        self.ui.addAssetInfo(asset.name,
                            asset.masterstatus,
                            asset.getPointedVersion(),
                            asset.latest)

    def switchManagerToAssetType(self, nicename):
        """
        Switch to displaying a different
        type of asset
        """

        # Get the internal name from nice name
        #   ex: "Environments" -> "env"
        atype = dty.getAssetTypeFromDir(nicename)

        # Rebuild the UI
        self.refreshUI(atype)

    #OVERRIDE
    def switchToAssetNamed(self, assetName, atVersion=None):
        """
        Switch to an asset
        """
        # deselect the previous asset checkbox
        if self.selectedAsset:
            self.ui.deselectAssetListItem(self.selectedAsset.name)

        # select the asset checkbox just in case
        self.ui.selectAssetListItem(assetName)

        self.selectedAsset = self.assets[assetName]

        # Clear!
        self.ui.clearVersionsList()

        # if we haven't been specified a version, select
        # the one that's currently open if applicable
        if self.sceneInfo:
            if self.sceneInfo.name == assetName:
                version = self.sceneInfo.name

        # list the versions
        asset = self.assets[assetName]
        versions = asset.versions

        if not versions:
            return

        # make entry for each version
        pointedver = asset.getPointedVersion()

        self.selectedVersion = None

        if atVersion:
            self.selectedVersion = atVersion
        else:
            self.selectedVersion = str(asset.latest)

        # add to gui
        self.ui.addVersionsInfo(versions, pointedver, atVersion, self.selectedVersion)

    def versionListChanged(self, version):
        self.selectedVersion = version

    def importAsset(self, asRef):
        """
        Imports/References the MASTER of the current asset
        """
        if not self.selectedAsset:
            cmds.warning("Please select an asset")
            return

        if p.checkIfAlreadyOpen(self.selectedAsset, "MASTER"):
            cmds.warning("The same file is already open")
            return

        if self.selectedAsset.masterstatus == 1:
            cmds.warning("MASTER file is not up-to-date")
        elif self.selectedAsset.masterstatus == 0:
            cmds.warning("No MASTER file, please publish")
            return

        # Import (or reference)
        self.selectedAsset.importVersion("MASTER", asReference=asRef)

    def openSelectedVersion(self):
        """
        Opens the selected version (if any)
        """
        if self.selectedVersion and self.selectedAsset:
            self.selectedAsset.openVersion(self.selectedVersion)
            self.refreshUI()
        else:
            cmds.warning("Please select an asset and a version")

    def publishSelectedVersion(self):
        """
        Publishes the selected version for the selected asset
        """
        if self.selectedVersion and self.selectedAsset:
            p.publishAsset(self.selectedAsset, self.selectedVersion)
            self.refreshUI()

    def saveNewVersion(self):
        """
        Save new version of asset from current scene
        """

        # Get the scene info and check if it's the right asset
        try:
            info = p.getOpenAssetInfo()
        except Exception, Argument:
            cmds.warning(str(Argument))
            return

        if info.name != self.selectedAsset.name or info.atype != self.atype:
            cmds.warning("Wrong Asset")
            return

        def callback(text):
            self.selectedAsset.saveNewVersion(text)
            self.refreshUI()

        # Dialog box time!
        self.ui.SaveDialog(callback)

class ShotManager(Manager):
    """
    Manages shots
    """
    def __init__(self):
        # GUI
        self.ui = ShotManagerUI("shot")

        # Selected version for each stage type
        self.selectedVersions = {
            "Layout" : None,
            "Animation" : None,
            "Lighting" : None
        }


        super(ShotManager, self).__init__(atype="shot")

    def addCallbacks(self):
        super(ShotManager, self).addCallbacks()

        self.ui.C_switchToAssetNamed = self.switchToAssetNamed

        self.ui.C_openSelectedVersion = self.openSelectedVersion
        self.ui.C_versionListChanged = self.versionListChanged
        self.ui.C_saveNewVersion = self.saveNewVersion
        self.ui.C_publishSelectedVersion = self.publishSelectedVersion

        self.ui.C_transferVersion = self.transferVersion
        self.ui.C_playblastSelectedVersion = self.playblastSelectedVersion
        self.ui.C_renderSelectedVersion = self.renderSelectedVersion

    #OVERRIDE
    def versionListChanged(self, version, shotstage):
        self.selectedVersions[shotstage] = version

    def addAsset(self, asset):
        """
        Add Assets to the list

        @PARAMS
            asset: Asset object to add
        """
        self.assets[asset.name] = asset

        self.ui.addShotInfoFor(asset)

    def publishSelectedVersion(self, shotstage):
        """
        Publishes the selected version for the selected asset
        """
        if self.selectedVersions[shotstage] and self.selectedAsset:
            p.publishAsset(self.selectedAsset.shotstages[shotstage],
                            self.selectedVersions[shotstage])
            self.refreshUI()

    def saveNewVersion(self, shotstage):
        """
        Save new version of asset from current scene
        """

        # Get the scene info and check if it's the right asset
        try:
            info = p.getOpenAssetInfo()
        except Exception, Argument:
            cmds.warning(str(Argument))
            return

        if info.name != self.selectedAsset.name or info.atype != self.atype:
            cmds.warning("Wrong Asset")
            return

        if info.shotstage != shotstage:
            cmds.warning("Wrong shot stage")
            return

        def callback(text):
            self.selectedAsset.shotstages[shotstage].saveNewVersion(text)
            self.refreshUI()

        # Dialog box time!
        self.ui.SaveDialog(callback)

    def transferVersion(self, shotstage):
        """
        Transfer to next step of shot

            (ex: LO -> Anim -> Lighting)
        """
        if self.selectedVersions[shotstage] and self.selectedAsset:
            p.transferVersion(version=self.selectedVersions[shotstage],
                                ofShot=self.selectedAsset,
                                ofStage=shotstage)

        self.refreshUI()

    def publishSelectedVersion(self, shotstage):
        """
        Publishes the selected version for the selected asset
        """
        if self.selectedVersions[shotstage] and self.selectedAsset:
            p.publishAsset(self.selectedAsset.shotstages[shotstage],
                            self.selectedVersions[shotstage])

            self.refreshUI()

    def addVersionsFor(self, shotstage, atVersion=None, currentStage=None):
        """
        Add versions to list for a specific shotstage
        """
        asset = self.selectedAsset.shotstages[shotstage]

        # TODO: DRY

        # if we haven't been specified a version, select
        # the one that's currently open if applicable
        if self.sceneInfo:
            if self.sceneInfo.name == asset.name:
                atVersion = self.sceneInfo.version
                currentStage = self.sceneInfo.shotstage

        # list the versions
        versions = asset.versions

        if not versions:
            return

        # make entry for each version
        pointedver = asset.getPointedVersion()

        self.selectedVersions[shotstage] = None

        if atVersion and shotstage == currentStage:
            self.selectedVersions[shotstage] = atVersion
        else:
            self.selectedVersions[shotstage] = str(asset.latest)

        # add to gui
        self.ui.addVersionsInfo(versions, pointedver, atVersion, currentStage, self.selectedVersions, shotstage)


    def switchToOpenAssetIn(self, assets):
        try:
            info = p.getOpenAssetInfo()
        except:
            return

        for asset in assets:
            if info.name == asset.name and info.atype == self.atype:
                self.switchToAssetNamed(info.name, atVersion=info.version, ofStage=info.shotstage)
                self.sceneInfo = info

    def switchToAssetNamed(self, assetName, atVersion=None, ofStage=None):
        """
        Switch to an asset
        """
        # deselect the previous asset checkbox
        if self.selectedAsset:
            self.ui.deselectAssetListItem(self.selectedAsset.name)

        # select the asset checkbox just in case
        self.ui.selectAssetListItem(assetName)

        self.selectedAsset = self.assets[assetName]

        # Clear!
        self.ui.clearVersionsList()


        # Add versions for each shot stage
        self.addVersionsFor("Layout", atVersion, currentStage=ofStage)
        self.addVersionsFor("Animation", atVersion, currentStage=ofStage)
        self.addVersionsFor("Lighting", atVersion, currentStage=ofStage)


    def openSelectedVersion(self, shotstage):
        """
        Opens the selected version (if any)
        """
        if self.selectedVersions[shotstage] and self.selectedAsset:
            self.selectedAsset.shotstages[shotstage].openVersion(self.selectedVersions[shotstage])
            self.refreshUI()
        else:
            cmds.warning("Please select an asset and a version")

    def playblastSelectedVersion(self, shotstage):
        """
        Playblasts the selected version (if any)
        """
        if self.selectedVersions[shotstage] and self.selectedAsset:
            self.selectedAsset.playblastVersion(self.selectedVersions[shotstage], shotstage)
        else:
            cmds.warning("Please select an asset and a version")

    def renderSelectedVersion(self, shotstage):
        """
        Playblasts the selected version (if any)
        """
        if self.selectedVersions[shotstage] and self.selectedAsset:
            self.selectedAsset.renderVersion(self.selectedVersions[shotstage], shotstage)
        else:
            cmds.warning("Please select an asset and a version")


class ManagerUI(object):
    """
    Base class for AssetManagerUI and ShotManagerUI
    """
    def __init__(self, atype):
        # UI elements
        self.ui = {}

        # Whether the last item in the list was dark or not
        self.lastwasdark = False

        # Asset type
        self.atype = atype

        # Title of window
        self.windowTitle = "Manager"


    def selectAssetListItem(self, item):
        cmds.iconTextCheckBox(item, e=True, value=1)

    def deselectAssetListItem(self, item):
        if item:
            cmds.iconTextCheckBox(item, e=True, value=0)

    def clearVersionsList(self):
        cmds.textScrollList(self.ui["versionList"], edit=True, removeAll=True)

    # Dialogs
    def CloneDialog(self, action):
        misc.DialogBoxUI("Clone",
                    message="Name:",
                    hasField=True,
                    requireField=True,
                    yesLabel="Clone",
                    noLabel="Cancel",
                    yesAction=action)

    def RenameDialog(self, action):
        misc.DialogBoxUI("Rename",
                    message="Name:",
                    hasField=True,
                    requireField=True,
                    yesLabel="Rename",
                    noLabel="Cancel",
                    yesAction=action)

    def DeleteDialog(self, action, name):
        misc.DialogBoxUI("Delete?",
                    message="Are you sure you want to delete '" + name + "'?",
                    hasField=False,
                    yesLabel="Delete",
                    noLabel="Cancel",
                    yesAction=action)

    def NewDialog(self, action):
        misc.DialogBoxUI("Create new " + self.atype,
                    message="Name:",
                    hasField=True,
                    yesLabel="New",
                    noLabel="Cancel",
                    yesAction=action)

    def SaveDialog(self, action):
        misc.DialogBoxUI("Save As New Version",
                    message="Version Description (optional):",
                    hasField=True,
                    requireField=False,
                    yesLabel="Save",
                    noLabel="Cancel",
                    yesAction=action)

    def createMenubar(self):
        # create menus
        self.ui["toolsMenu"] = cmds.menu(label="Tools")
        cmds.menuItem(label="Batch Publish...")
        cmds.menuItem(label="Export File List...")
        cmds.menuItem(label="Archive Old Versions...")
        self.ui["settingsMenu"] = cmds.menu(label="Settings")
        cmds.menuItem(label="Settings Manager...")

    def createAssetsList(self):
        # "Assets"
        # toolbar
        self.ui["assetsToolbarRow"] = cmds.rowLayout(
                                        numberOfColumns=2,
                                        parent=self.ui["rootCol"])
        self.ui["refreshBtn"] = cmds.symbolButton(
                                        image="refresh.png",
                                        parent=self.ui["assetsToolbarRow"],
                                        command=lambda _: self.C_refreshUI())
        self.ui["exploreBtn"] = cmds.symbolButton(
                                        image="search.png",
                                        parent=self.ui["assetsToolbarRow"],
                                        command=lambda _: self.C_exploreAsset())

        # asset list
        self.ui["assetList"] = cmds.scrollLayout(
                                        backgroundColor=(0.17,0.17,0.17),
                                        width=500,
                                        height=200,
                                        parent=self.ui["rootCol"])
    def createAssetsListLeftButtons(self):
        self.ui["importBtn"] = cmds.button(
                            label="Import",
                            width=73,
                            height=30,
                            parent=self.ui["buttonRow"],
                            command=lambda _: self.C_importAsset(asRef=False))
        self.ui["refBtn"] = cmds.button(
                            label="Ref",
                            width=73,
                            height=30,
                            parent=self.ui["buttonRow"],
                            command=lambda _: self.C_importAsset(asRef=True))
        cmds.separator(width=175, style="none", parent=self.ui["buttonRow"])

    def createAssetsListRightButtons(self):
        self.ui["renameBtn"] = cmds.button(
                            label="Rename",
                            width=60,
                            height=30,
                            parent=self.ui["buttonRow"],
                            command=lambda _: self.C_renameAsset())
        self.ui["cloneBtn"] = cmds.button(
                            label="Clone",
                            width=45,
                            height=30,
                            parent=self.ui["buttonRow"],
                            command=lambda _: self.C_duplicateAsset())
        self.ui["newBtn"] = cmds.button(
                            label="+",
                            width=30,
                            height=30,
                            #backgroundColor=(0.2,0.4,0.2),
                            parent=self.ui["buttonRow"],
                            command=lambda _: self.C_newAsset())
        self.ui["delBtn"] = cmds.button(
                            label="-",
                            width=30,
                            height=30,
                            #backgroundColor=(0.2,0.4,0.2),
                            parent=self.ui["buttonRow"],
                            command=lambda _: self.C_deleteAsset())
        cmds.separator(height=10, style="none", parent=self.ui["rootCol"])

    def createAssetsListButtons(self):
        # button row
        self.ui["buttonRow"] = cmds.rowLayout(
                                        numberOfColumns=7,
                                        parent=self.ui["rootCol"])
        self.createAssetsListLeftButtons()
        self.createAssetsListRightButtons()

    def createUITop(self):
        """
        Create the top of the UI
        """
        self.createMenubar()
        self.createAssetsList()
        self.createAssetsListButtons()

    def createUIBtm(self):
        """
        Create the bottom of the UI
        """

        return

    # Main UI
    def createUI(self):
        """
        Creates the (empty) Asset Manager UI
        """

        # create window
        winName = type(self).__name__ + "Win"

        if cmds.window(winName, exists=True):
            cmds.deleteUI(winName)

        """
        try:
            cmds.windowPref(winName, remove=True)
        except:
            pass
        """


        self.ui["win"] = cmds.window(
                                winName,
                                title=self.windowTitle,
                                width=500,
                                height=600,
                                #sizeable=True,
                                sizeable=False,
                                maximizeButton=False,
                                menuBar=True)

        # create root layout
        self.ui["rootCol"] = cmds.columnLayout()

        # create widgets
        # (separated into different methods to allow for
        #   inheritence customization)
        self.createUITop()

        self.createUIBtm()

        # show window
        cmds.showWindow()

class AssetManagerUI(ManagerUI):
    """
    GUI for AssetManager
    """
    def __init__(self, atype):
        super(AssetManagerUI, self).__init__(atype)

        # Title of window
        self.windowTitle = "Asset Manager"

    def addAssetInfo(self, name, status, pointedver, latest):
        """
        Add checkbox/list item for asset
        """

        padlen = 30 - len(name)
        pad = " " * padlen

        if self.atype == "rig":
            icon = RIG_ICON
        elif self.atype == "prop":
            icon = PROP_ICON
        elif self.atype == "env":
            icon = ENV_ICON
        else:
            icon = SHOT_ICON

        if status == 2:
            color = LATEST_BGC
            assetstatus = pad + "@MASTER -> " + pointedver
        elif status == 1:
            color = OLD_BGC
            assetstatus = pad + "@MASTER -> " + pointedver + " (" + latest + ")"
        elif status == 0:
            color = INVALID_BGC
            assetstatus = pad + "(" + latest + ")"
        else:
            cmds.error("Invalid status")


        #color = su.multvec(color, (1.0,1.0,1.0))
        """
        if self.lastwasdark:
            color = su.multvec(color, (0.8,0.8,0.0))

        self.lastwasdark = not self.lastwasdark
        """

        # FooBar    @MASTER -> 003 (007)

        cmds.iconTextCheckBox(
                name,
                width=490,
                height=30,
                style='iconAndTextHorizontal',
                image1=icon,
                label=name + assetstatus,
                parent=self.ui["assetList"],
                bgc=color,
                font="fixedWidthFont",
                onCommand=lambda _, x=name: self.C_switchToAssetNamed(x),
                offCommand=lambda _, x=name: self.selectAssetListItem(x))

    def addVersionsInfo(self, versions, pointedVer, sceneVersion, selectedVersion):
        """
        Add items to versions scroll list
        """
        for v, desc in versions.iteritems():
            if v != "MASTER":

                pointed = ""
                if v == pointedVer:
                    pointed = "@ "

                opened = ""
                if v == sceneVersion:
                    opened = "   <-----"

                cmds.textScrollList(self.ui["versionList"],
                                    edit=True,
                                    append=pointed + v + ": " + desc.lower() + opened,
                                    uniqueTag=v)

        cmds.textScrollList(self.ui["versionList"],
                    edit=True,
                    selectUniqueTagItem=selectedVersion)

    # OVERRIDEN
    def createAssetTypeDropdown(self):
        # asset type dropdown
        self.ui["typeDropdown"] = cmds.optionMenu(
                                        parent=self.ui["rootCol"],
                                        changeCommand=lambda x: self.C_switchManagerToAssetType(x),
                                        width=500,
                                        height=30)
        cmds.menuItem("env", label="Environments")
        cmds.menuItem("prop", label="Props")
        cmds.menuItem("rig", label="Rigs")

        cmds.optionMenu(self.ui["typeDropdown"], e=True, value=dty.ASSET_TYPES[self.atype])

    # OVERRIDDEN
    def createUITop(self):
        """
        Create the top of the UI
        """
        self.createMenubar()

        self.createAssetTypeDropdown()
        self.createAssetsList()
        self.createAssetsListButtons()

    def versionListCallback(self, *args):
        ver = cmds.textScrollList(self.ui["versionList"],
                                    query=True,
                                    selectUniqueTagItem=True)

        self.C_versionListChanged(ver[0])

    def createUIBtm(self):
        """
        Create the bottom of the UI
        """

        # version list
        self.ui["versionFrame"] = cmds.frameLayout(
                                        label="Versions",
                                        labelAlign="top",
                                        collapsable=False,
                                        parent=self.ui["rootCol"])
        self.ui["versionFrameCol"] = cmds.columnLayout(
                                        adjustableColumn=True,
                                        parent=self.ui["versionFrame"])



        self.ui["versionList"] = cmds.textScrollList(
                                        #backgroundColor=(0.21,0.21,0.21),
                                        width=500,
                                        height=200,
                                        parent=self.ui["versionFrameCol"],
                                        selectCommand=self.versionListCallback)

        # buttons
        self.ui["verBtnRow"] = cmds.rowLayout(
                                        numberOfColumns=7,
                                        parent=self.ui["versionFrameCol"])
        btncol = (0.5,0.5,0.5)
        self.ui["openBtn"] = cmds.button(
                            label="Open",
                            width=100,
                            height=40,
                            #backgroundColor=btncol,
                            parent=self.ui["verBtnRow"],
                            command=lambda _: self.C_openSelectedVersion())
        self.ui["saveBtn"] = cmds.button(
                            label="+",
                            width=30,
                            height=40,
                            #backgroundColor=btncol,
                            parent=self.ui["verBtnRow"],
                            command=lambda _: self.C_saveNewVersion())

        cmds.separator(width=285, style="none", parent=self.ui["verBtnRow"])

        self.ui["publishBtn"] = cmds.button(
                                        label="Publish",
                                        width=80,
                                        height=40,
                                        #backgroundColor=(0.2,0.2,0.2),
                                        parent=self.ui["verBtnRow"],
                                        command=lambda _: self.C_publishSelectedVersion())




class ShotManagerUI(ManagerUI):
    """
    GUI for ShotManager
    """
    def __init__(self, atype):
        super(ShotManagerUI, self).__init__(atype)

        # Title of the window
        self.windowTitle = "Shot Manager"

        self.createUI()

    def addShotInfoFor(self, shot):
        padlen = 16 - len(shot.name)
        pad = " " * padlen

        sep = " | "
        blank = "   "

        image = SHOT_ICON
        color = NEUTRAL_BGC
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

        if self.lastwasdark:
            color = su.multvec(color, (1.3,1.3,1.3))

        self.lastwasdark = not self.lastwasdark

        # C20    LO: MASTER | Anim: 004 | Light: 007

        assetstatus = pad + "LO: " + layoutver + sep + "Anim: " + animationver + sep + "Light: " + lightingver

        cmds.iconTextCheckBox(
                name,
                width=490,
                height=30,
                style='iconAndTextHorizontal',
                image1=image,
                label=name + assetstatus,
                parent=self.ui["assetList"],
                bgc=color,
                font="fixedWidthFont",
                onCommand=lambda _, x=name: self.C_switchToAssetNamed(x),
                offCommand=lambda _, x=name: self.selectAssetListItem(x))


    def clearVersionsList(self):
        cmds.textScrollList(self.ui["verList" + "Layout"], edit=True, removeAll=True)
        cmds.textScrollList(self.ui["verList" + "Animation"], edit=True, removeAll=True)
        cmds.textScrollList(self.ui["verList" + "Lighting"], edit=True, removeAll=True)

    def addVersionsInfo(self, versions, pointedver, sceneVersion, sceneShotstage, selectedVersions, shotstage):
        """
        Add items to versions scroll list for the type of shot stage
        """

        # TODO: DRY
        for v, desc in versions.iteritems():
            if v != "MASTER":

                pointed = ""
                if v == pointedver:
                    pointed = "@"

                opened = ""
                if v == sceneVersion and shotstage == sceneShotstage:
                    opened = "   <-----"

                cmds.textScrollList(self.ui["verList" + shotstage],
                                    edit=True,
                                    append=pointed + v + ": " + desc.lower() + opened,
                                    uniqueTag=v)

        cmds.textScrollList(self.ui["verList" + shotstage],
                            edit=True,
                            selectUniqueTagItem=selectedVersions[shotstage])


    #OVERRIDE
    def createAssetsListLeftButtons(self):
        cmds.separator(width=321, style="none", parent=self.ui["buttonRow"])

    #OVERRIDE
    def versionListCallback(self, shotstage):
        ver = cmds.textScrollList(self.ui["verList" + shotstage],
                                    query=True,
                                    selectUniqueTagItem=True)

        self.C_versionListChanged(ver[0], shotstage)

    def createVersionListFor(self, shotstage, width):
        # frame layout
        self.ui["verListFrame" + shotstage] = cmds.frameLayout(label=shotstage,
                                            labelAlign="top",
                                            collapsable=False,
                                            parent=self.ui["verLists"])

        # - column
        self.ui["verListCol" + shotstage] = cmds.columnLayout(
                                            adjustableColumn=True,
                                            parent=self.ui["verListFrame" + shotstage])

        # -- list
        self.ui["verList" + shotstage] = cmds.textScrollList(
                                            width=width,
                                            height=200,
                                            parent=self.ui["verListCol" + shotstage],
                                            selectCommand=lambda x = shotstage: self.versionListCallback(x)
                                            )

        # -- row
        self.ui["verBtnRowUp" + shotstage] = cmds.rowLayout(
                                            numberOfColumns=4,
                                            parent=self.ui["verListCol" + shotstage])
        # --- buttons
        self.ui["openBtn" + shotstage] = cmds.button(
                                            label="Open",
                                            width=55,
                                            height=40,
                                            parent=self.ui["verBtnRowUp" + shotstage],
                                            command=lambda _, x = shotstage: self.C_openSelectedVersion(shotstage=x)
                                            )
        self.ui["saveBtn" + shotstage] = cmds.button(
                                            label="+",
                                            width=20,
                                            height=40,
                                            parent=self.ui["verBtnRowUp" + shotstage],
                                            command=lambda _, x = shotstage: self.C_saveNewVersion(x))

        width = 80 if shotstage == "Lighting" else 59
        self.ui["publishBtn" + shotstage] = cmds.button(
                                            label="Publish",
                                            width=width,
                                            height=40,
                                            parent=self.ui["verBtnRowUp" + shotstage],
                                            command=lambda _, x = shotstage: self.C_publishSelectedVersion(x))

        if shotstage != "Lighting":
            self.ui["transferBtn" + shotstage] = cmds.button(
                                                label="->",
                                                width=20,
                                                height=40,
                                                parent=self.ui["verBtnRowUp" + shotstage],
                                                command=lambda _, x = shotstage: self.C_transferVersion(x))

        cmds.separator(height=10, style="none", parent=self.ui["verListCol" + shotstage])

        # -- row
        self.ui["verBtnRowDown" + shotstage] = cmds.rowLayout(
                                            numberOfColumns=4,
                                            parent=self.ui["verListCol" + shotstage])
        # --- buttons
        cmds.separator(width=10, style="none", parent=self.ui["verBtnRowDown" + shotstage])

        self.ui["playblastBtn" + shotstage] = cmds.button(
                                            label="Playblast",
                                            width=60,
                                            height=30,
                                            parent=self.ui["verBtnRowDown" + shotstage],
                                            command=lambda _, x = shotstage: self.C_playblastSelectedVersion(x))

        cmds.separator(width=10, style="none", parent=self.ui["verBtnRowDown" + shotstage])

        self.ui["renderBtn" + shotstage] = cmds.button(
                                            label="Render",
                                            width=60,
                                            height=30,
                                            parent=self.ui["verBtnRowDown" + shotstage],
                                            command=lambda _, x = shotstage: self.C_renderSelectedVersion(x))

        cmds.separator(height=10, style="none", parent=self.ui["verListCol" + shotstage])


    # OVERRIDEN
    def createUIBtm(self):
        self.ui["verLists"] = cmds.rowLayout(
                                numberOfColumns=3,
                                parent=self.ui["rootCol"])

        for _, shotstage in dty.SHOT_STAGE_TYPES.iteritems():
            self.createVersionListFor(shotstage, 470 / 3)
