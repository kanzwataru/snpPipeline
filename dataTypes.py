"""
Final film pipeline,
data type classes

BaseData -> Asset (Env, Prop, Rig)
         -> Shot
"""
import os
from collections import OrderedDict
from collections import namedtuple

import maya.cmds as cmds
import maya.mel as mel

# (third-party) https://github.com/abstractfactory/maya-capture
#from capture import capture

ASSET_TYPES={
    "rig" : "Rigs",
    "prop" : "Props",
    "env" : "Environments",
    "shot" : "Scenes",
    "1-LO" : "Scenes",
    "2-anim" : "Scenes",
    "3-lighting" : "Scenes"
}

SceneInfo = namedtuple('SceneInfo', ['name',
                                    'version',
                                    'atype',
                                    'shotstage'])

SHOT_STAGE_TYPES={
    "1-LO" : "Layout",
    "2-anim" : "Animation",
    "3-lighting" : "Lighting"
}

def shotstageFor(atype):
    return SHOT_STAGE_TYPES[atype]

def atypeFor(shotstage):
    # Get the reverse of the type name
    atype = None
    for key, value in SHOT_STAGE_TYPES.iteritems():
            if value == shotstage:
                atype = key

    return atype

def getAssetTypeFromDir(directory):
    # Get the reverse of the type name
    atype = None
    for key, value in ASSET_TYPES.iteritems():
            if value == directory:
                atype = key

    return atype

def compareDate(master, compared, path):
    """
    Compare which file is newer

    @RETURNS
        True : master is the same or newer
        False : master is older
    """

    mastertime = os.path.getmtime(os.path.join(path, master))
    comparedtime = os.path.getmtime(os.path.join(path, compared))

    return mastertime >= comparedtime

def pathOfAssetType(atype, named=None, isRelative=False):
    """
    Returns the folder where assets of type 'atype' are
    stored. If 'named' is provided, also adds the name of 
    a specific asset. If relative is True, adds Maya env
    variable for the root of the pipeline
    """
    from snpPipeline import ROOT_DIR, PROJECT_ROOT_VAR

    if isRelative:
        root = "$" + PROJECT_ROOT_VAR
    else:
        root = ROOT_DIR

    # directory for this type of attribute
    path = os.path.join(root, "1_3DCG", ASSET_TYPES[atype])

    if named:
        path = os.path.join(path, named)

    return path


def _addPadding(string):
        while len(string) < 3:
            string = "0" + string

        return string

class DummyAsset(object):
    def __init__(self, name):
        self.name = name

    def masterStatus(self):
        return 2

class Asset(object):
    def __init__(self, path, atype):
        # Data name
        self.name = ""

        # "Version" : Identifier
        # "MASTER" : (pointer version if matches)
        self.versions = OrderedDict()

        # Latest version by number
        #   003, 004, *005*
        self.latest = ""

        # Type of asset
        self.atype = atype

        # Status of master
        self._masterstatus = None

        # Assign name from path
        self.name = os.path.basename(path)

        # list scene files
        files = os.listdir(path)

        # add corresponding files to list
        scenes = []

        for file in files:
            if file.startswith(self.name) and file.endswith(".ma"):
                scenes.append(file)

        # split name into variables
        for scene in scenes:
            # remove the file extension
            filename = os.path.splitext(scene)[0]

            # split into vars
            attrs = filename.split('_')

            # skip if not right type
            if attrs[1] != self.atype:
                continue

            if len(attrs) == 2:
                # MASTER scene
                self.versions["MASTER"] = ""
            elif len(attrs) == 3:
                # Scene with no description
                self.versions[attrs[2]] = ""
            elif len(attrs) == 4:
                # Scene with description
                self.versions[attrs[2]] = attrs[3]

        self._setLatest()


    def getVerNumbers(self):
        """
        Returns list of version numbers (in order),
        not including MASTER
        """

        verstrings = self.versions.keys()
        vernums = []

        for verstring in verstrings:
            if verstring != "MASTER":
                vernums.append(int(verstring))

        vernums.sort()

        return vernums

    def _setLatest(self):
        vers = self.getVerNumbers()

        if len(vers) > 1:
            last = vers[-1]
        elif len(vers) == 1:
            last = vers[0]
        elif len(vers) == 0:
            return

        self.latest = _addPadding(str(last))

    def getPointerFile(self):
        # read pointer file
        pointerfile = self.filenameFromVersion("MASTER", ".pointer")
        path = self.getBaseDir()
        pointerpath = os.path.join(path, pointerfile)
        if not os.path.exists(pointerpath):
            print "'" + self.name + "'" + " is missing a .pointer file"
            return None

        return pointerpath

    def getPointedVersion(self):
        pointerpath = self.getPointerFile()

        if not pointerpath:
            return

        with open(pointerpath, mode="r") as file:
            pointedver = file.read()

        return pointedver

    def getMasterStatus(self):
        """
        Checks the status of the master scene

        @Returns:
            0 : No master file (or invalid)
            1 : Master file exists but not latest
            2 : Master file exists and is latest
        """

        # check if master exists
        if not "MASTER" in self.versions.keys():
            print "'" + self.name + "'" + " does not have a master"
            return 0

        path = pathOfAssetType(self.atype, named=self.name)
        pointedver = self.getPointedVersion()

        # check if exists in version array
        if not pointedver in self.versions.keys():
            # master points to a non-existing file
            print "'" + self.name + "'" + " does not point to an existing version"
            return 0

        # check if master time is older
        masterfile = self.filenameFromVersion("MASTER")
        pointedfile = self.filenameFromVersion(pointedver)

        if not compareDate(masterfile, pointedfile, path):
            # master is older than the pointed file
            return 1

        # check if pointed version is the latest file
        if pointedver == self.latest:
            return 2
        else:
            return 1

    def fileFromVersion(self, version, isRelative=False):
        # checks
        if not version:
            cmds.error("Internal error: no version specified for " + str(self))
        elif not (version in self.versions.keys()):
            cmds.error("Internal error: version does not exist")

        # put together the file name
        filename = self.filenameFromVersion(version)

        # put together the full path
        path = os.path.join(self.getBaseDir(isRelative), filename)

        return path

    def filenameFromVersion(self, version, ext=".ma", descriptor="/"):
        """
        Reconstructs the filename from the version
        """
        if version == "MASTER":
            filename = self.name + "_" + self.atype + ext
        else:
            """
            # Check if we have that version
            if not version in self.versions.keys():
                return None
            """
            if descriptor == "/":
                descriptor = self.versions[version]

            # Check if we have a descriptor    
            if descriptor != "":
                filename = self.name + "_" + self.atype + "_" + version + "_" + descriptor + ext
            else:
                filename = self.name + "_" + self.atype + "_" + version + ext

        return filename

    def getBaseDir(self, isRelative=False):
        return os.path.join(pathOfAssetType(self.atype, named=self.name, isRelative=isRelative))

    def getAllFiles(self, asFullpath=False, includingPointer=False):
        files = []
        for ver in self.versions.keys():
            if asFullpath:
                files.append(self.fileFromVersion(ver))
            elif not asFullpath:
                files.append(self.filenameFromVersion(ver))

        if includingPointer:
            try:
                pointerfilepath = self.getPointerFile()
                pointer = os.path.basename(pointerfilepath)
                files.append(pointer)
            except:
                pass

        return files               

    def openVersion(self, version):
        path = self.fileFromVersion(version)
        # let's open
        cmds.file(new=True, force=True)
        cmds.file(path, open=True)

    def importVersion(self, version, toNamespace=None, asReference=False):
        path = self.fileFromVersion(version, isRelative=True)

        if not toNamespace:
            toNamespace = self.name

        # let's import
        if asReference:
            cmds.file(path, r=True, namespace=toNamespace)
        else:
            cmds.file(path, i=True, namespace=toNamespace)            

    def saveNewVersion(self, descriptor):
        # get file name
        newver = _addPadding(str(int(self.latest) + 1))
        filename = self.filenameFromVersion(newver, descriptor=descriptor.upper())

        # get asset base path
        filepath = pathOfAssetType(self.atype)

        # splice
        path = os.path.join(filepath, self.name, filename)

        # save as
        cmds.file(rename=path)
        cmds.file(save=True, type="mayaAscii")

    @property
    def masterstatus(self):
        if self._masterstatus:
            return self._masterstatus
        else:
            self._masterstatus = self.getMasterStatus()
            return self._masterstatus


class Shot(object):
    def __init__(self, path):
        # Assign name from path
        self.name = os.path.basename(path)

        # This is always shot, since it is a container
        self.atype = "shot"

        # All assets
        self.shotstages = {}

        # Create Asset objects for each process of a shot
        self.shotstages["Layout"] = Asset(path, "1-LO")
        self.shotstages["Animation"] = Asset(path, "2-anim")
        self.shotstages["Lighting"] = Asset(path, "3-lighting")

        # Bind the method from a shotstage so as to be DRY
        self.getBaseDir = self.shotstages["Layout"].getBaseDir

    def getAllFiles(self, asFullpath, includingPointer):
        files = []
        for _, asset in self.shotstages.iteritems():
            files += asset.getAllFiles(asFullpath, includingPointer)

        return files

    def renderVersion(self, version, ofStage):
        raise NotImplementedError

    def playblastVersion(self, version, ofStage):
        # Get full file path of version
        versionfile = self.shotstages[ofStage].fileFromVersion(version)

        # Blasts directory
        blastdir = os.path.join(os.path.split(versionfile)[0], "Blasts")

        # Name of playblast file
        blastname = '_'.join([self.name, ofStage, version, "PLAYBLAST"])
        file = os.path.join(blastdir, blastname)
        
        # Avoid overwriting existing playblasts
        count = 0
        while os.path.exists(file + ".mov") or os.path.exists(file + ".avi") or os.path.exists(file + ".mp4"):
            count += 1

            blastname = '_'.join([self.name, ofStage, version, "PLAYBLAST", str(count)])
            file = os.path.join(blastdir, blastname)

        # Playblast
        cmds.playblast(width=1280, height=720, percent=100, filename=file)

        mel.eval("print \"Playblast: " + file + "\"")