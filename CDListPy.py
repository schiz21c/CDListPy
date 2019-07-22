#!/usr/bin/env python

import os
import sqlite3
import wx

# Deprecated
#import win32file
#import win32api

import yaml
import res

__version__ = '1.1.0 (2019-07-21)'


class MainApp(wx.App):

    def OnInit(self):
        frame = MainFrame()
        frame.Show()
        self.SetTopWindow(frame)
        return True


class MainFrame(wx.Frame):

    def __init__(self):
        self.loadSetting()

        wx.Frame.__init__(self, None, -1, 'CDListPy', self.setting['mainPos'], self.setting['mainSize'])

        # Menu
        menuFile = wx.Menu()
        menuFile.Append(1, '&Reload', 'Reload all data')
        menuFile.Append(2, '&Find',   'Find the specified file')
        menuFile.Append(3, '&Scan',   'Scan new CD info')
        menuFile.AppendSeparator()
        menuFile.Append(4, 'E&xit',   'Exit the program')

        menuHelp = wx.Menu()
        menuHelp.Append(5, '&About',  'About the program')

        menuBar = wx.MenuBar()
        menuBar.Append(menuFile, '&File')
        menuBar.Append(menuHelp, '&Help')

        self.SetMenuBar(menuBar)
        self.CreateStatusBar()

        self.Bind(wx.EVT_MENU, self.OnReload, id=1)
        self.Bind(wx.EVT_MENU, self.OnFind,   id=2)
        self.Bind(wx.EVT_MENU, self.OnScan,   id=3)
        self.Bind(wx.EVT_MENU, self.OnQuit,   id=4)
        self.Bind(wx.EVT_MENU, self.OnAbout,  id=5)

        self.SetIcon(res.CDico.GetIcon())

        # Image list
        self.il = wx.ImageList(16, 16)
        self.IMG_ROOT    = self.il.Add(res.Root.GetBitmap())
        self.IMG_CD      = self.il.Add(res.CD.GetBitmap())
        self.IMG_DIR     = self.il.Add(res.Dir.GetBitmap())
        self.IMG_DIROPEN = self.il.Add(res.DirOpen.GetBitmap())
        self.IMG_FILE    = self.il.Add(res.File.GetBitmap())

        # Create the tree
        self.tree = wx.TreeCtrl(self)
        self.tree.SetImageList(self.il)

        self.Bind(wx.EVT_TREE_ITEM_EXPANDING, self.OnExpandItem)
        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnSelectItem)
        self.Bind(wx.EVT_CLOSE, self.OnClose)

        self.scanDialog = None
        self.findDialog = None

        self.Show(True) # Show first and load

        self.loadDirdata()

    def loadSetting(self):
        self.settingfn = '.' + os.path.sep + 'CDListPy.conf'
        if os.path.exists(self.settingfn):
            f = open(self.settingfn)
            self.setting = yaml.load(f.read())
        else:
            self.setting = {'mainPos':  (-1, -1),
                            'mainSize': (640, 480),
                            'findPos':  (-1, -1),
                            'findSize': (640, 480),
                            'findColumnPath': 297,
                            'findColumnFile': 297,
                            'scanPos':  (-1, -1)}

    def saveSetting(self):
        self.setting['mainPos']  = self.GetPositionTuple()
        self.setting['mainSize'] = self.GetSizeTuple()
        if self.findDialog:
            self.setting['findPos']  = self.findDialog.GetPositionTuple()
            self.setting['findSize'] = self.findDialog.GetSizeTuple()
            self.setting['findColumnPath'] = self.findDialog.resultList.GetColumnWidth(0)
            self.setting['findColumnFile'] = self.findDialog.resultList.GetColumnWidth(1)
        if self.scanDialog:
            self.setting['scanPos']  = self.scanDialog.GetPositionTuple()

        dumped = yaml.dump(self.setting)
        f = open(self.settingfn, 'w')
        f.write(dumped)

    def OnQuit(self, event):
        self.Close()

    def OnClose(self, event):
        self.saveSetting()
        db.close()
        self.Destroy()

    def OnAbout(self, event):
        wx.MessageBox("CDListPy " + __version__ + "     ", "About", wx.OK | wx.ICON_INFORMATION, self)

    def OnReload(self, event):
        self.loadDirdata()

    def OnFind(self, event):
        if self.scanDialog:
            self.scanDialog.Close()
            self.scanDialog = None

        if not self.findDialog:
            self.findDialog = FindDialog(self, 1, 'Find')
            self.findDialog.expandFunc = self.expandNode

        self.findDialog.Show()
        self.findDialog.Raise()
        pass

    def OnScan(self, event):
        if self.findDialog:
            self.findDialog.Close()
            self.findDialog = None

        if not self.scanDialog:
            self.scanDialog = ScanDialog(self, 1, 'Scan')
            self.scanDialog.reloadFunc = self.OnReload

        self.scanDialog.Show()
        self.scanDialog.Raise()

    def OnExpandItem(self, event):
        node = event.GetItem()
        pyData = self.tree.GetPyData(node)

        if pyData:
            filedata = db.getFiledata(pyData)

            for i in filedata:
                filenode = self.tree.AppendItem(node, i[0])
                self.tree.SetItemImage(filenode, self.IMG_FILE)

        self.tree.SetPyData(node, None)

    def OnSelectItem(self, event):
        path = []
        node = event.GetItem()
        while node:
            path.insert(0, self.tree.GetItemText(node))
            node = self.tree.GetItemParent(node)

        self.SetStatusText('/'.join(path))

    def loadDirdata(self):
        wx.BeginBusyCursor()
        self.tree.DeleteAllItems()

        # Add a root node
        self.root = self.tree.AddRoot("Root")
        self.tree.SetItemImage(self.root, self.IMG_ROOT)

        dirdata = db.getDirdata()
        self.nodeDic = {}

        for i in dirdata:
            path = i[1].strip()

            # Trim trailing '/'
            while len(path) > 0 and path[0] == '/':
                path = path[1:]
            while len(path) > 0 and path[len(path) - 1] == '/':
                path = path[:-1]
            if len(path) == 0:
                continue

            node = self.getNode(path)
            self.tree.SetItemHasChildren(node, True)
            self.tree.SetPyData(node, i[0]) # Set dir id

        self.SetStatusText('Ready')
        self.tree.Expand(self.root)
        wx.EndBusyCursor()

    def getNode(self, path):
        if self.nodeDic.has_key(path):
            return self.nodeDic[path]
        else:
            idx = path.rfind('/')
            if idx != -1:
                parent = self.getNode(path[:idx]) # parent node
                node   = self.tree.AppendItem(parent, path[idx + 1:])
                self.tree.SetItemImage(node, self.IMG_DIR,     wx.TreeItemIcon_Normal)
                self.tree.SetItemImage(node, self.IMG_DIROPEN, wx.TreeItemIcon_Expanded)
            else:
                parent = self.root
                node   = self.tree.AppendItem(parent, path)
                self.tree.SetItemImage(node, self.IMG_CD)
            self.nodeDic[path] = node
            return node

    def expandNode(self, path):
        if self.nodeDic.has_key(path):
            node = self.nodeDic[path]
            self.tree.SelectItem(node, True)
            self.tree.Expand(node)


class FindDialog(wx.Dialog):

    def __init__(self, parent, id, title):
        wx.Dialog.__init__(self, parent, id, title, parent.setting['findPos'], style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)

        self.expandFunc = None

        self.findText   = wx.TextCtrl(self, -1, '', size=(50, 22), style=wx.TE_PROCESS_ENTER)
        self.findButton = wx.Button(self, 1, 'Find', size=(50, 22))
        self.resultList = wx.ListCtrl(self, -1, size=(100, 38), style=wx.LC_REPORT)

        self.il = wx.ImageList(16, 16)
        self.IMG_DIR  = self.il.Add(res.Dir.GetBitmap())
        self.IMG_FILE = self.il.Add(res.File.GetBitmap())

        self.resultList.SetImageList(self.il, wx.IMAGE_LIST_SMALL)

        self.Bind(wx.EVT_BUTTON, self.OnFind, id=1)
        self.findText.Bind(wx.EVT_CHAR, self.EvtChar, self.findText)
        self.resultList.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItem)

        self.resultList.InsertColumn(0, 'Path', width=parent.setting['findColumnPath'])
        self.resultList.InsertColumn(1, 'File', width=parent.setting['findColumnFile'])

        dialogSizer = wx.BoxSizer(wx.VERTICAL)
        searchSizer = wx.BoxSizer(wx.HORIZONTAL)
        searchSizer.Add(self.findText,   1, wx.EXPAND|wx.ALL, 4)
        searchSizer.Add(self.findButton, 0, wx.EXPAND|wx.TOP|wx.RIGHT|wx.BOTTOM, 4)
        dialogSizer.Add(searchSizer,     0, wx.EXPAND|wx.ALL, 0)
        dialogSizer.Add(self.resultList, 1, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, 4)
        self.SetSizerAndFit(dialogSizer)

        self.SetSize(parent.setting['findSize'])

    def OnFind(self, event):
        self.resultList.DeleteAllItems()

        result = db.findDirdata(self.findText.GetValue())
        for d in result:
            idx = self.resultList.InsertImageStringItem(self.resultList.GetItemCount(), d[0], self.IMG_DIR)
            self.resultList.SetStringItem(idx, 1, '/')

        result = db.findFiledata(self.findText.GetValue())
        for d in result:
            idx = self.resultList.InsertImageStringItem(self.resultList.GetItemCount(), d[0], self.IMG_FILE)
            self.resultList.SetStringItem(idx, 1, d[1])

    def OnItem(self, event):
        path = event.GetItem().GetText()
        self.expandFunc(path)

    def EvtChar(self, event):
        if event.GetKeyCode() == wx.WXK_RETURN:
            self.OnFind(None)
        else:
            event.Skip()


class ScanDialog(wx.Dialog):

    def __init__(self, parent, id, title):
        wx.Dialog.__init__(self, parent, id, title, parent.setting['scanPos'], (220, 140))

        self.reloadFunc = None

        self.driveLabel = wx.StaticText(self, -1, 'Dir:', (10, 13))
        self.driveText  = wx.TextCtrl(self, -1, '', (60, 10), (140, 22))
        self.nameLabel  = wx.StaticText(self, -1, 'Name:', (10, 43))
        self.nameText   = wx.TextCtrl(self, -1, '', (60, 40), (140, 22))
        self.scanButton = wx.Button(self, 1, 'Scan', (70, 80))

        self.Bind(wx.EVT_BUTTON, self.OnScan, id=1)

        '''
        # Get CD-Rom drive
        for d in win32api.GetLogicalDriveStrings().split('\x00'):
            dt = win32file.GetDriveType(d)
            if dt == win32file.DRIVE_CDROM:
                self.driveCombo.Append(d)

        #self.driveCombo.Append('E:\\') # FOR SCAN TEST

        # Select first drive
        if self.driveCombo.GetCount() > 0:
            self.driveCombo.SetSelection(0)
        else:
            self.driveCombo.Disable()
            self.scanButton.Disable()
        '''

    def OnScan(self, event):
        if self.driveText.GetValue()[-1] != '/':
            self.driveText.SetValue(self.driveText.GetValue() + '/')
        if len(self.nameText.GetValue()) == 0:
            wx.MessageBox("Name is empty     ", "Error", wx.OK | wx.ICON_ERROR, self)
            return

        # Scan
        for (dirpath, dirnames, filenames) in os.walk(self.driveText.GetValue()):
            dirdata = dirpath.replace(self.driveText.GetValue(), self.nameText.GetValue() + '/')

            if dirdata[len(dirdata) - 1] == '/':
                dirdata = dirdata[:-1]

            dirid = db.insertDirdata(dirdata)
            for filename in sorted(filenames):
                db.insertFiledata(dirid, filename)
        db.commit()

        self.Close()
        self.reloadFunc(None) # Call parent


class DB:

    def __init__(self, filename='CDListPy.db'):
        initTable = False
        if not os.path.exists(filename):
            initTable = True

        self.conn = sqlite3.connect(filename)
        #self.conn.text_factory = str

        self.c = self.conn.cursor()

        if initTable:
            self.c.execute("create table dirdata  (id integer primary key autoincrement, dirname text)")
            self.c.execute("create table filedata (id integer primary key autoincrement, dirid integer, filename text)")
            self.c.execute("create index id_idx    on dirdata  ( id )")
            self.c.execute("create index dirid_idx on filedata ( dirid )")
            self.conn.commit()

    def test(self):
        # test
        self.c.execute("insert into dirdata (dirname) values ('test/123')")
        self.c.execute("insert into dirdata (dirname) values ('test/456')")
        self.c.execute("insert into filedata (dirid, filename) values (1, 'a111')")
        self.c.execute("insert into filedata (dirid, filename) values (2, 'b111')")
        self.conn.commit()

        self.c.execute("select * from dirdata")
        for row in self.c:
            print row

        self.close()

    def getDirdata(self):
        self.c.execute("select id, dirname from dirdata")
        return self.c.fetchall()

    def getFiledata(self, dirid):
        self.c.execute("select filename from filedata where dirid = ?", [dirid])
        return self.c.fetchall()

    def insertDirdata(self, dirname):
        dirname = dirname.replace(os.path.sep, '/')
        self.c.execute("select id from dirdata where dirname = ?", [dirname])
        for row in self.c:
            return row[0]

        self.c.execute("insert into dirdata (dirname) values (?)", [dirname])

        self.c.execute("select id from dirdata where dirname = ?", [dirname])
        for row in self.c:
            return row[0]

    def insertFiledata(self, dirid, filename):
        self.c.execute("insert into filedata (dirid, filename) values (?, ?)", [dirid, filename])

    def findDirdata(self, name):
        self.c.execute("select dirname from dirdata where dirname like ?", ['%' + name + '%'])
        return self.c.fetchall()

    def findFiledata(self, name):
        self.c.execute("select dirdata.dirname, filedata.filename from dirdata, filedata where dirdata.id = filedata.dirid and filedata.filename like ?", ['%' + name + '%'])
        return self.c.fetchall()

    def importData(self):
        fd = open('dirdata.txt')
        ff = open('filedata.txt')

        l = fd.readline().strip()
        while l:
            id, dirname = l.split('\t')
            dirname = dirname.decode('euc-kr') # To unicode
            print '/', id
            self.c.execute("insert into dirdata (dirname) values (?)", [dirname])

            l = fd.readline().strip()

        l = ff.readline().strip()
        while l:
            id, dirid, filename = l.split('\t')
            filename = filename.decode('euc-kr') # To unicode
            print id
            self.c.execute("insert into filedata (dirid, filename) values (?, ?)", [dirid, filename])

            l = ff.readline().strip()

        self.commit()
        self.close()

    def commit(self):
        self.conn.commit()

    def close(self):
        self.c.close()
        self.conn.close()


db = DB()

if __name__ == '__main__':
    app = MainApp(False)
    app.MainLoop()

    # TEST
    #db.test()
    #db.importData()
