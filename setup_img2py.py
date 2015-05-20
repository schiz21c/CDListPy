import sys
from wx.tools import img2py

# BeOS icons
command_lines = [
    "   -F -n Root       ico/BeOS_BeBox_grey.png res.py",
    "-a -F -n CD         ico/BeOS_Query.png      res.py",
    "-a -F -n Dir        ico/BeOS_folder.png     res.py",
    "-a -F -n DirOpen    ico/BeOS_folder.png     res.py",
    "-a -F -n File       ico/BeOS_generic.png    res.py",
    "-a -F -n CDico      ico/BeOS_BeBox_grey.ico res.py",
    ]

if __name__ == "__main__":
    for line in command_lines:
        args = line.split()
        img2py.main(args)
