import maya.cmds as cmds

def saveFile():
	cmds.file(save=True, type="mayaAscii")

def newFile():
    cmds.file(new=True, force=True)

def getRenderCams():
    cameras = cmds.ls(type=('camera'), l=True)
    return [cam for cam in cameras if cmds.getAttr(cam + ".renderable")]

def to_unicode(text):
	try:
		text_u = unicode(text.decode("utf8"))
	except:
		try:
			text_u = unicode(text.decode("shift_jis"))
		except:
			try:
				text_u = unicode(text.decode("utf16"))
			except Exception as e:
				raise e

	return text_u