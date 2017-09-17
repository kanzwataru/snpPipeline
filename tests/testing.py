class BaseData(object):
	def __init__(self):
		self.name = "foo"
		self.type = ""
		self.version = ""
		self.descriptor = ""

	def load_name(self):
		self.name = "Brilliant"

class Asset(BaseData):
	def load_name(self):
		self.name = "SpacePilot"
		self.type = "rig"
		self.version = "101"
		self.descriptor = "SLEEVESNEW"


myBase = BaseData()
myBase.load_name()
print myBase.name

myRig = Asset()
print myRig.name
myRig.load_name()
print myRig.name