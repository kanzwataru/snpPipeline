import maya.cmds as cmds


def padNum(num):
    num_str = str(int(num))
    while(len(num_str) < 4):
        num_str = "0" + num_str
        
    return num_str


def fixShadMapPath():
	pass


def getCompatibleEnogu():
	pass


def initShadMap(shot):
	# find where the shadow map would be

	# try to apply it to all Enogu materials

	# add hook for refreshing