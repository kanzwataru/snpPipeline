"""
Backup manager
"""
import os
import platform
import subprocess
import inspect

import core

BACKUP_DIR_VAR = "BACKUP_DIR"
BACKUP_DIR = os.path.normpath(os.environ[BACKUP_DIR_VAR])

SHELL_SCRIPT_PATH = os.path.join(os.path.dirname(inspect.getfile(core)), "shellscripts")

# Commands for opening terminal on different OSes
TERMINALS = {
    "Linux" : "x-terminal-emulator -e /bin/bash ",
    "Windows" : "D:\\_applications\\cygwin64\\bin\\mintty.exe /bin/bash ",
    "Mac" : ''
}

TERM = TERMINALS[platform.system()]

# D:\_applications\cygwin64\bin

def getUSBDir():
    return os.path.normpath(os.environ["USB_DIR"])

def cygwinizePath(path):
    splitpath = os.path.normpath(path).split('\\')
    driveletter = splitpath[0].lower().replace(':', '')

    del splitpath[0]

    return "/cygdrive/" + ('/'.join([driveletter] + splitpath))

def run(cmd):
    if platform.system() == "Windows": 
        subprocess.call("path D:\\_applications\\cygwin64\\bin;%PATH% && " + cmd, shell=True)
    else:
        subprocess.call(cmd, shell=True)

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

# Cygwinize the path to the shell scripts directory on Windows
if platform.system() == "Windows": SHELL_SCRIPT_PATH = cygwinizePath(SHELL_SCRIPT_PATH)