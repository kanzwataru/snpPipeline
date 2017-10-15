"""
Backup manager
"""
import os
import platform

from snpPipeline.shellinterop import *

BACKUP_DIR_VAR = "BACKUP_DIR"
BACKUP_DIR = os.path.normpath(os.environ[BACKUP_DIR_VAR])


def backupProject(root):
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)

    if platform.system() == "Windows":
        root = cygwinizePath(root)
        backupdir = cygwinizePath(BACKUP_DIR)
    else:
        backupdir = BACKUP_DIR

    script = '/'.join([SHELL_SCRIPT_PATH, "archive-nix.sh"])

    cmd = TERM + script + ' ' + root + ' ' + backupdir

    run(cmd)


def syncToUSB(root):
    usbdir = getUSBDir()

    if platform.system() == "Windows":
        root = cygwinizePath(root)
        usbdir = cygwinizePath(usbdir)

    script = os.path.join(SHELL_SCRIPT_PATH, "syncfromto.sh")

    cmd = TERM + script + ' ' + root + '/ ' + usbdir

    run(cmd)


def syncFromUSB(root):
    usbdir = getUSBDir()

    if platform.system() == "Windows":
        root = cygwinizePath(root)
        usbdir = cygwinizePath(usbdir)

    script = os.path.join(SHELL_SCRIPT_PATH, "syncfromto.sh")

    cmd = TERM + script + ' ' + usbdir + '/ ' + root

    run(cmd)
