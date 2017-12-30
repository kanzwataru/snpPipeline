import maya.cmds as cmds
import snpPipeline as p
reload(p)

#p.createAssetDir("Bar", "env")
#p.createAssetDir("Hoge", "prop")

#p.createAssetDir("C20", "shot")

#p.testClasses()

#p.makeManyFiles()
#p.makeManyAssets()

#manui = p.createAssetManager("env")

'''
cmds.textScrollList(manui.ui["versionList"],
                    edit=True,
                    lineFont=(3, "boldLabelFont"))
'''



def yact(message):
    print message
    
def nact(message):
    print "Cancelling " + message

def dialogTest():
    dialog = p.ui.DialogBoxUI("Rename", 
                                message="Rename to:",
                                hasField=True,
                                yesLabel="Rename",
                                noLabel="Cancel",
                                yesAction=yact,
                                noAction=nact )


#myasset = p.dty.Asset("C:\\_testing\\pipelineTest\\1_3DCG\\Rigs\\Foo", "rig")
#print myasset.masterstatus

#print p.getAssets("rig")

# Unit Tests
def makeManyAssets():
    myAsset = dty.Asset("C:\\_testing\\pipelineTest\\1_3DCG\\Environments\\Bar", "env")

    for i in xrange(0, 50):
        duplicateAsset(myAsset, "FooBar" + str(i))

def testClasses():
    myAsset = dty.Asset("C:\\_testing\\pipelineTest\\1_3DCG\\Props\\Hoge", "prop")

    print "name: " + str(myAsset.name)
    print "atype: " + str(myAsset.atype)
    print "versions: " + str(myAsset.versions)
    print "latest: " + str(myAsset.latest)
    print "master status: " + str(myAsset.masterstatus)

def makeManyFiles():
    path = "C:\\_testing\\pipelineTest\\1_3DCG\\Props\\Hoge"

    for i in xrange(1,120):
        name = "Hoge_prop_" + dty.addPadding(str(i)) + ".ma"

        pathname = os.path.join(path, name)

        with open(pathname, mode="w") as file:
            file.write("hoge")

def assetManagerUITest(atype):
    # get list of assets

    # make ui with those assets
    amanUI = gui.assetManager.AssetManagerUI(atype)

    #TEST
    for i in xrange(0,60):
        #asset = dty.Asset("C:\\_testing\\pipelineTest\\1_3DCG\\Rigs\\Foo", "rig")

        asset = dty.DummyAsset("Fuga" + str(i))

        amanUI.addAsset(asset)