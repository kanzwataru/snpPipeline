"""
Various helper UIs
"""

import maya.cmds as cmds

class DialogBoxUI(object):
    """
    A simple dialog with an optional text field

    @PARAMS
        title: Window title
        message: Message to be shown
        hasField: If there should be a text field
        requireField: If it should error out with an empty field
        fieldText: The text field's default text
        yesAction: The action when the 'yes' button is pressed
        noAction: The action when the 'no' button is pressed
        yesLabel: The label for the 'yes' button
        noLabel: The label for the 'no' button
    """

    def delete(self):
        if cmds.window(self.ui["win"], exists=True):
            cmds.deleteUI(self.ui["win"])

    def _yesBtnCallback(self, *args):
        try:
            fieldText = cmds.textField(self.ui["field"], query=True, text=True)
        except:
            fieldText = ""

        if self.requireField and fieldText == "":
            cmds.warning("Please type something")
            return
        
        self.delete()

        if self.yesAction:
            self.yesAction(fieldText)



    def _noBtnCallback(self, *args):
        try:
            fieldText = cmds.textField(self.ui["field"], query=True, text=True)
        except:
            fieldText = ""

        if self.requireField and fieldText == "":
            cmds.warning("Please type something")
            return

        self.delete()

        if self.noAction:
            self.noAction(fieldText)

    def __init__(self, title, message, hasField=False, fieldText="", requireField=False,
                yesAction=None, noAction=None, yesLabel="Yes", noLabel="No"):
        # UI elements
        self.ui = {}

        # Properties
        self.requireField = requireField

        # Callbacks
        self.yesAction = yesAction
        self.noAction = noAction
        
        # create window
        winName = "fieldDialogWin"

        if cmds.window(winName, exists=True):
            cmds.deleteUI(winName)

        try:
            cmds.windowPref(winName, remove=True)
        except:
            pass

        self.ui["win"] = cmds.window(
                            winName,
                            title=title,
                            width=450,
                            height=90,
                            sizeable=True,
                            #sizeable=False,
                            maximizeButton=False,
                            minimizeButton=False)
        # create layout
        self.ui["root"] = cmds.columnLayout(adjustableColumn=True)

        # text
        cmds.separator(height=15, style="none", parent=self.ui["root"])
        self.ui["messageTxt"] = cmds.text(
                                    label=message, 
                                    parent=self.ui["root"])

        # field
        if hasField:
            cmds.separator(height=15, style="none", parent=self.ui["root"])

            self.ui["fieldRow"] = cmds.rowLayout(
                                    numberOfColumns=3, 
                                    columnWidth3=(10, 75, 10), 
                                    adjustableColumn=2, 
                                    #columnAlign=(1, 'right'), 
                                    columnAttach=[(1, 'both', 0), (2, 'both', 0), (3, 'both', 0)],
                                    parent=self.ui["root"])
            
            cmds.separator(width=2, style="none", parent=self.ui["fieldRow"])
            self.ui["field"] = cmds.textField(
                                    text=fieldText,
                                    parent=self.ui["fieldRow"])
            cmds.separator(width=2, style="none", parent=self.ui["fieldRow"])

        # buttons
        if yesAction or noAction:
            cmds.separator(height=15, style="none", parent=self.ui["root"])

            self.ui["btnRowBase"] = cmds.rowLayout(
                                        numberOfColumns=3, 
                                        columnWidth3=(10, 75, 10), 
                                        adjustableColumn=2, 
                                        #columnAlign=(1, 'right'), 
                                        columnAttach=[(1, 'both', 0), (2, 'both', 0), (3, 'both', 0)],
                                        parent=self.ui["root"])

            cmds.separator(width=5, style="none", parent=self.ui["btnRowBase"])
            self.ui["btnRow"] = cmds.rowLayout(
                                        numberOfColumns=2,
                                        parent=self.ui["btnRowBase"])
            cmds.separator(width=5, style="none", parent=self.ui["btnRowBase"])

            self.ui["yesBtn"] = cmds.button(
                                        label=yesLabel,
                                        width=60,
                                        height=30,
                                        parent=self.ui["btnRow"],
                                        command=self._yesBtnCallback)
            self.ui["noBtn"] = cmds.button(
                                        label=noLabel,
                                        width=60,
                                        height=30,
                                        parent=self.ui["btnRow"],
                                        command=self._noBtnCallback)

        cmds.separator(height=10, style="none", parent=self.ui["root"])
        # show window
        cmds.showWindow()