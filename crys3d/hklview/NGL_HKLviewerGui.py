from __future__ import absolute_import, division, print_function

#-------------------------------------------------------------------------------
# Name:        module1
# Purpose:
#
# Author:      oeffner
#
# Created:     09/05/2019
# Copyright:   (c) oeffner 2019
# Licence:     <your licence>
#-------------------------------------------------------------------------------

from PySide2.QtCore import Qt, QUrl, QTimer
from PySide2.QtWidgets import ( QApplication, QCheckBox, QComboBox,
        QDial, QFileDialog, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
        QProgressBar, QPushButton, QRadioButton, QScrollBar, QSizePolicy,
        QSlider, QDoubleSpinBox, QSpinBox, QStyleFactory, QTableWidget,
        QTableWidgetItem, QTabWidget, QTextEdit, QVBoxLayout, QWidget )

from PySide2.QtWebEngineWidgets import QWebEngineView


import sys, zmq, subprocess, time, traceback

class NGL_HKLViewer(QWidget):
  def __init__(self, parent=None):
    super(NGL_HKLViewer, self).__init__(parent)
    self.context = None

    self.originalPalette = QApplication.palette()

    self.openFileNameButton = QPushButton("Load reflection file")
    self.openFileNameButton.setDefault(True)
    self.openFileNameButton.clicked.connect(self.OpenReflectionsFile)

    self.debugbutton = QPushButton("Debug Button")
    self.debugbutton.clicked.connect(self.DebugInteractively)

    self.mousemoveslider = QSlider(Qt.Horizontal)
    self.mousemoveslider.setMinimum(0)
    self.mousemoveslider.setMaximum(400)
    self.mousemoveslider.setValue(0)
    self.mousemoveslider.sliderReleased.connect(self.onFinalMouseSensitivity)
    self.mousemoveslider.valueChanged.connect(self.onMouseSensitivity)

    self.mousesensitxtbox = QLineEdit('')
    self.mousesensitxtbox.setReadOnly(True)

    self.MillerComboBox = QComboBox()
    self.MillerComboBox.activated.connect(self.MillerComboSelchange)
    #self.MillerComboBox.setSizeAdjustPolicy(QComboBox.AdjustToContents)

    self.MillerLabel = QLabel()
    self.MillerLabel.setText("Selected Miller Array")

    self.SpaceGroupComboBox = QComboBox()
    self.SpaceGroupComboBox.activated.connect(self.SpacegroupSelchange)

    self.SpacegroupLabel = QLabel()
    self.SpacegroupLabel.setText("Space Subgroups")

    self.mergecheckbox = QCheckBox()
    self.mergecheckbox.setText("Merge data")
    #self.mergecheckbox.setTristate (True)
    self.mergecheckbox.clicked.connect(self.MergeData)

    self.expandP1checkbox = QCheckBox()
    self.expandP1checkbox.setText("Expand to P1")
    self.expandP1checkbox.clicked.connect(self.ExpandToP1)

    self.expandAnomalouscheckbox = QCheckBox()
    self.expandAnomalouscheckbox.setText("Show Friedel pairs")
    self.expandAnomalouscheckbox.clicked.connect(self.ExpandAnomalous)

    self.sysabsentcheckbox = QCheckBox()
    self.sysabsentcheckbox.setText("Show Systematic Absences")
    self.sysabsentcheckbox.clicked.connect(self.showSysAbsent)

    self.missingcheckbox = QCheckBox()
    self.missingcheckbox.setText("Show Missing")
    self.missingcheckbox.clicked.connect(self.showMissing)

    self.onlymissingcheckbox = QCheckBox()
    self.onlymissingcheckbox.setText("Only Show Missing")
    self.onlymissingcheckbox.clicked.connect(self.showOnlyMissing)

    self.showslicecheckbox = QCheckBox()
    self.showslicecheckbox.setText("Show Slice")
    self.showslicecheckbox.clicked.connect(self.showSlice)

    self.sliceindexspinBox = QDoubleSpinBox()
    self.sliceindex = 0
    self.sliceindexspinBox.setValue(self.sliceindex)
    self.sliceindexspinBox.setDecimals(0)
    self.sliceindexspinBox.setSingleStep(1)
    self.sliceindexspinBox.setRange(0, 20)
    self.sliceindexspinBox.valueChanged.connect(self.onSliceIndexChanged)

    self.SliceLabelComboBox = QComboBox()
    self.SliceLabelComboBox.activated.connect(self.onSliceComboSelchange)
    self.sliceaxis = [ "h", "k", "l" ]
    self.SliceLabelComboBox.addItems( self.sliceaxis )

    self.HKLnameedit = QLineEdit('')
    self.HKLnameedit.setReadOnly(True)
    self.textInfo = QTextEdit()
    self.textInfo.setReadOnly(True)

    self.RadiiScaleGroupBox = QGroupBox("Radii Size of HKL Spheres")
    #self.PowerScaleGroupBox = QGroupBox("Manual Power Scaling of Sphere Radii")

    self.ManualPowerScalecheckbox = QCheckBox()
    self.ManualPowerScalecheckbox.setText("Manual Power Scaling of Sphere Radii")
    self.ManualPowerScalecheckbox.clicked.connect(self.onManualPowerScale)

    self.power_scale_spinBox = QDoubleSpinBox(self.RadiiScaleGroupBox)
    self.nth_power_scale = 0.5
    self.power_scale_spinBox.setValue(self.nth_power_scale)
    self.power_scale_spinBox.setDecimals(2)
    self.power_scale_spinBox.setSingleStep(0.05)
    self.power_scale_spinBox.setRange(0.0, 1.0)
    self.power_scale_spinBox.valueChanged.connect(self.onPowerScaleChanged)
    self.powerscaleLabel = QLabel()
    self.powerscaleLabel.setText("Power scale Factor")

    self.radii_scale_spinBox = QDoubleSpinBox(self.RadiiScaleGroupBox)
    self.radii_scale = 1.0
    self.radii_scale_spinBox.setValue(self.radii_scale)
    self.radii_scale_spinBox.setDecimals(1)
    self.radii_scale_spinBox.setSingleStep(0.1)
    self.radii_scale_spinBox.setRange(0.2, 2.0)
    self.radii_scale_spinBox.valueChanged.connect(self.onRadiiScaleChanged)
    self.radiiscaleLabel = QLabel()
    self.radiiscaleLabel.setText("Linear Scale Factor")

    self.millertable = QTableWidget(0, 8)
    labels = ["label", "type", "no. of HKLs", "span of HKLs",
       "min max data", "min max sigmas", "d_min, d_max", "symmetry unique"]
    self.millertable.setHorizontalHeaderLabels(labels)
    # don't allow editing the miller array info
    self.millertable.setEditTriggers(QTableWidget.NoEditTriggers)

    self.createGroupBox1()
    self.createGroupBox2()
    self.CreateSliceGroupBox()
    self.createBottomLeftTabWidget()
    self.createRadiiScaleGroupBox()

    self.BrowserBox = QWebEngineView()

    mainLayout = QGridLayout()
    mainLayout.addWidget(self.GroupBox2,           0, 0)
    mainLayout.addWidget(self.HKLnameedit,         1, 0, 1, 1)
    mainLayout.addWidget(self.topLeftGroupBox,     2, 0)
    mainLayout.addWidget(self.sliceTabWidget,      3, 0)
    mainLayout.addWidget(self.RadiiScaleGroupBox,  4, 0)
    mainLayout.addWidget(self.bottomLeftGroupBox,  5, 0)
    mainLayout.addWidget(self.BrowserBox,          0, 1, 6, 3)

    #self.BrowserBox.load(QUrl("https://cctbx.github.io/"))
    self.BrowserBox.setUrl("https://cctbx.github.io/")
    self.BrowserBox.loadFinished.connect(self.onLoadFinished)
    self.BrowserBox.renderProcessTerminated.connect(self.onRenderProcessTerminated)

    mainLayout.setRowStretch(0, 0)
    mainLayout.setRowStretch(1, 0)
    mainLayout.setRowStretch(2, 0)
    mainLayout.setRowStretch(3, 0)
    mainLayout.setRowStretch(4, 1)
    #mainLayout.setColumnStretch(0, 1)
    mainLayout.setColumnStretch(2, 1)
    self.setLayout(mainLayout)

    self.verbose = 0
    for e in sys.argv:
      if "verbose" in e:
        self.verbose = e.split("verbose=")[1]

    self.setWindowTitle("NGL-HKL-viewer")
    self.cctbxproc = None
    self.LaunchCCTBXPython()
    self.out = None
    self.err = None
    self.hklscenes_arrays = []
    self.array_infotpls = []
    self.matching_arrays = []
    self.bin_info = None
    self.html_url = ""
    self.spacegroups = []
    self.info = []
    self.infostr = ""
    self.fileisvalid = False
    self.NewFileLoaded = False

    self.show()


  def update(self):
    #while 1:
    #  time.sleep(1)
    if self.cctbxproc:
      if self.cctbxproc.stdout:
        print(self.cctbxproc.stdout.read().decode("utf-8"))
      if self.cctbxproc.stderr:
        print(self.cctbxproc.stderr.read().decode("utf-8"))
    if self.out:
      print(self.out.decode("utf-8"))
    if self.err:
      print(self.err.decode("utf-8"))
    #print("in update\n")
    if self.context:
      try:
        msg = self.socket.recv(flags=zmq.NOBLOCK) #To empty the socket from previous messages
        #msg = self.socket.recv()
        msgstr = msg.decode()
#        print(msgstr)
        self.infodict = eval(msgstr)
        #print("received from cctbx: " + str(self.info))
        if self.infodict:

          if self.infodict.get("hklscenes_arrays"):
            self.hklscenes_arrays = self.infodict.get("hklscenes_arrays", [])

          if self.infodict.get("array_infotpls"):
            self.array_infotpls = self.infodict.get("array_infotpls",[])

          if self.infodict.get("bin_info"):
            self.bin_info = self.infodict["bin_info"]

          if self.infodict.get("html_url"):
            self.html_url = self.infodict["html_url"]
            self.BrowserBox.setUrl(self.html_url)

          if self.infodict.get("spacegroups"):
            self.spacegroups = self.infodict.get("spacegroups",[])

          if self.infodict.get("merge_data"):
            self.mergedata = self.infodict["merge_data"]

          if self.infodict.get("info"):
            self.infostr = self.infodict.get("info",[])

          if self.infodict.get("NewFileLoaded"):
            self.NewFileLoaded = self.infodict.get("NewFileLoaded",False)

          self.fileisvalid = True
          #print("ngl_hkl_infodict: " + str(ngl_hkl_infodict))

          if self.infostr:
            print(self.infostr)
            self.textInfo.setPlainText(self.infostr)
            #self.mergecheckbox.setEnabled(True)
          else:
            self.textInfo.setPlainText("")
            #self.mergecheckbox.setEnabled(False)
          if self.NewFileLoaded:
            #if self.mergedata == True : val = Qt.CheckState.Checked
            #if self.mergedata == None : val = Qt.CheckState.PartiallyChecked
            #if self.mergedata == False : val = Qt.CheckState.Unchecked
            #self.mergecheckbox.setCheckState(val )
            #print("got hklscenes: " + str(self.hklscenes_arrays))

            self.MillerComboBox.clear()
            self.MillerComboBox.addItems( [ (str(e[0]) + " (" + str(e[1]) +")" )
                                             for e in self.hklscenes_arrays ] )
            self.SpaceGroupComboBox.clear()
            self.SpaceGroupComboBox.addItems( self.spacegroups )

            self.millertable.setRowCount(len(self.hklscenes_arrays))
            #self.millertable.setColumnCount(8)
            for n,millarr in enumerate(self.array_infotpls):
              for m,elm in enumerate(millarr):
                self.millertable.setItem(n, m, QTableWidgetItem(str(elm)))

      except Exception as e:
        errmsg = str(e)
        if "Resource temporarily unavailable" not in errmsg:
          print( errmsg  +  traceback.format_exc(limit=10) )
        pass


  def onFinalMouseSensitivity(self):
    val = self.mousemoveslider.value()/100.0
    self.NGL_HKL_command('NGL_HKLviewer.mouse_sensitivity = %f' %val)


  def onMouseSensitivity(self):
    val = self.mousemoveslider.value()/100.0
    self.mousesensitxtbox.setText("%2.2f" %val )


  def MergeData(self):
    if self.mergecheckbox.checkState()== Qt.CheckState.Checked:
      self.NGL_HKL_command('NGL_HKLviewer.mergedata = True')
    if self.mergecheckbox.checkState()== Qt.CheckState.PartiallyChecked:
      self.NGL_HKL_command('NGL_HKLviewer.mergedata = None')
    if self.mergecheckbox.checkState()== Qt.CheckState.Unchecked:
      self.NGL_HKL_command('NGL_HKLviewer.mergedata = False')


  def ExpandToP1(self):
    if self.expandP1checkbox.isChecked():
      self.NGL_HKL_command('NGL_HKLviewer.viewer.expand_to_p1 = True')
    else:
      self.NGL_HKL_command('NGL_HKLviewer.viewer.expand_to_p1 = False')


  def ExpandAnomalous(self):
    if self.expandAnomalouscheckbox.isChecked():
      self.NGL_HKL_command('NGL_HKLviewer.viewer.expand_anomalous = True')
    else:
      self.NGL_HKL_command('NGL_HKLviewer.viewer.expand_anomalous = False')


  def showSysAbsent(self):
    if self.sysabsentcheckbox.isChecked():
      self.NGL_HKL_command('NGL_HKLviewer.viewer.show_systematic_absences = True')
    else:
      self.NGL_HKL_command('NGL_HKLviewer.viewer.show_systematic_absences = False')


  def showMissing(self):
    if self.missingcheckbox.isChecked():
      self.NGL_HKL_command('NGL_HKLviewer.viewer.show_missing = True')
    else:
      self.NGL_HKL_command('NGL_HKLviewer.viewer.show_missing = False')


  def showOnlyMissing(self):
    if self.onlymissingcheckbox.isChecked():
      self.NGL_HKL_command('NGL_HKLviewer.viewer.show_only_missing = True')
    else:
      self.NGL_HKL_command('NGL_HKLviewer.viewer.show_only_missing = False')


  def showSlice(self):
    if self.showslicecheckbox.isChecked():
      self.NGL_HKL_command('NGL_HKLviewer.viewer.slice_mode = True')
    else:
      self.NGL_HKL_command('NGL_HKLviewer.viewer.slice_mode = False')


  def onSliceComboSelchange(self,i):
    rmin = self.hklscenes_arrays[self.MillerComboBox.currentIndex()][3][0][i]
    rmax = self.hklscenes_arrays[self.MillerComboBox.currentIndex()][3][1][i]
    self.sliceindexspinBox.setRange(rmin, rmax)
    self.NGL_HKL_command("NGL_HKLviewer.viewer.slice_axis = %s" % self.sliceaxis[i] )


  def onSliceIndexChanged(self, val):
    self.sliceindex = val
    self.NGL_HKL_command("NGL_HKLviewer.viewer.slice_index = %d" %self.sliceindex)


  def onRadiiScaleChanged(self, val):
    self.radii_scale = val
    self.NGL_HKL_command("""
      NGL_HKLviewer.viewer {
        nth_power_scale_radii = %f
        scale = %f
      }
      """ %(self.nth_power_scale, self.radii_scale)
    )


  def onPowerScaleChanged(self, val):
    self.nth_power_scale = val
    self.NGL_HKL_command("""
      NGL_HKLviewer.viewer {
        nth_power_scale_radii = %f
        scale = %f
      }
      """ %(self.nth_power_scale, self.radii_scale)
    )

  def onLoadFinished(self, val):
    print("web page finished loading now")


  def onRenderProcessTerminated(self, termstatus, exitcode):
    print("Rendering terminated with status: %s and exitcode: %s" %(str(termstatus), str(exitcode)))


  def onManualPowerScale(self):
    if self.ManualPowerScalecheckbox.isChecked():
      self.NGL_HKL_command('NGL_HKLviewer.viewer.nth_power_scale_radii = %f' %self.nth_power_scale)
      self.power_scale_spinBox.setEnabled(True)
    else:
      self.NGL_HKL_command('NGL_HKLviewer.viewer.nth_power_scale_radii = -1.0')
      self.power_scale_spinBox.setEnabled(False)


  def OpenReflectionsFile(self):
    options = QFileDialog.Options()
    fileName, filtr = QFileDialog.getOpenFileName(self,
            "Load reflections file",
            "",
            "All Files (*);;MTZ Files (*.mtz);;CIF (*.cif)", "", options)
    if fileName:
      self.HKLnameedit.setText(fileName)
      self.fileisvalid = False
      self.NGL_HKL_command('NGL_HKLviewer.filename = "%s"' %fileName )
      self.MillerComboBox.clear()


  def createGroupBox1(self):
    self.topLeftGroupBox = QGroupBox("Group 1")
    layout = QGridLayout()
    layout.addWidget(self.MillerComboBox,            1, 1, 1, 1)
    layout.addWidget(self.MillerLabel,               1, 0, 1, 1)
    layout.addWidget(self.SpaceGroupComboBox,        2, 1, 1, 1)
    layout.addWidget(self.SpacegroupLabel,           2, 0, 1, 1)
    layout.addWidget(self.mergecheckbox,             3, 0, 1, 1)
    layout.addWidget(self.expandP1checkbox,          3, 1, 1, 1)
    layout.addWidget(self.expandAnomalouscheckbox,   4, 0, 1, 1)
    layout.addWidget(self.sysabsentcheckbox,         4, 1, 1, 1)
    layout.addWidget(self.missingcheckbox,           5, 0, 1, 1)
    layout.addWidget(self.onlymissingcheckbox,       5, 1, 1, 1)
    #layout.addStretch(1)
    self.topLeftGroupBox.setLayout(layout)


  def CreateSliceGroupBox(self):
    self.sliceTabWidget = QTabWidget()
    tab1 = QWidget()
    layout1 = QGridLayout()
    layout1.addWidget(self.showslicecheckbox,         0, 0, 1, 1)
    layout1.addWidget(self.SliceLabelComboBox,        0, 1, 1, 1)
    layout1.addWidget(self.sliceindexspinBox,         0, 2, 1, 1)
    tab1.setLayout(layout1)

    tab2 = QWidget()
    layout2 = QGridLayout()

    self.hvec_spinBox = QDoubleSpinBox(self.sliceTabWidget)
    self.hvecval = 0.0
    self.hvec_spinBox.setValue(self.nth_power_scale)
    self.hvec_spinBox.setDecimals(2)
    self.hvec_spinBox.setSingleStep(0.5)
    self.hvec_spinBox.setRange(-100.0, 10.0)
    self.hvec_spinBox.valueChanged.connect(self.onHvecChanged)
    self.hvec_Label = QLabel()
    self.hvec_Label.setText("H")
    layout2.addWidget(self.hvec_Label,      0, 0, 1, 1)
    layout2.addWidget(self.hvec_spinBox,    0, 1, 1, 1)

    self.kvec_spinBox = QDoubleSpinBox(self.sliceTabWidget)
    self.kvecval = 0.0
    self.kvec_spinBox.setValue(self.nth_power_scale)
    self.kvec_spinBox.setDecimals(2)
    self.kvec_spinBox.setSingleStep(0.5)
    self.kvec_spinBox.setRange(-100.0, 10.0)
    self.kvec_spinBox.valueChanged.connect(self.onLvecChanged)
    self.kvec_Label = QLabel()
    self.kvec_Label.setText("K")
    layout2.addWidget(self.kvec_Label,      1, 0, 1, 1)
    layout2.addWidget(self.kvec_spinBox,    1, 1, 1, 1)

    self.lvec_spinBox = QDoubleSpinBox(self.sliceTabWidget)
    self.lvecval = 0.0
    self.lvec_spinBox.setValue(self.nth_power_scale)
    self.lvec_spinBox.setDecimals(2)
    self.lvec_spinBox.setSingleStep(0.5)
    self.lvec_spinBox.setRange(-100.0, 10.0)
    self.lvec_spinBox.valueChanged.connect(self.onKvecChanged)
    self.lvec_Label = QLabel()
    self.lvec_Label.setText("L")
    layout2.addWidget(self.lvec_Label,      2, 0, 1, 1)
    layout2.addWidget(self.lvec_spinBox,    2, 1, 1, 1)

    self.fixedorientcheckbox = QCheckBox(self.sliceTabWidget)
    self.fixedorientcheckbox.setText("Allow mouse zoom and translation but no rotation")
    self.fixedorientcheckbox.clicked.connect(self.onFixedorient)
    layout2.addWidget(self.fixedorientcheckbox,   3, 0, 1, 1)

    self.hkldist_spinBox = QDoubleSpinBox(self.sliceTabWidget)
    self.hkldistval = 0.0
    self.hkldist_spinBox.setValue(self.nth_power_scale)
    self.hkldist_spinBox.setDecimals(2)
    self.hkldist_spinBox.setSingleStep(0.5)
    self.hkldist_spinBox.setRange(-100.0, 10.0)
    self.hkldist_spinBox.valueChanged.connect(self.onHKLdistChanged)
    self.hkldist_Label = QLabel()
    self.hkldist_Label.setText("Distance from Origin")
    layout2.addWidget(self.hkldist_Label,      4, 0, 1, 1)
    layout2.addWidget(self.hkldist_spinBox,    4, 1, 1, 1)

    self.clipwidth_spinBox = QDoubleSpinBox(self.sliceTabWidget)
    self.clipwidthval = 0.0
    self.clipwidth_spinBox.setValue(self.nth_power_scale)
    self.clipwidth_spinBox.setDecimals(2)
    self.clipwidth_spinBox.setSingleStep(0.5)
    self.clipwidth_spinBox.setRange(-100.0, 10.0)
    self.clipwidth_spinBox.valueChanged.connect(self.onClipwidthChanged)
    self.clipwidth_Label = QLabel()
    self.clipwidth_Label.setText("Clip Plane Width")
    layout2.addWidget(self.clipwidth_Label,      5, 0, 1, 1)
    layout2.addWidget(self.clipwidth_spinBox,    5, 1, 1, 1)

    tab2.setLayout(layout2)
    self.sliceTabWidget.addTab(tab1, "Explicit Slicing")
    self.sliceTabWidget.addTab(tab2, "Clip Plane Slicing")


  def onClipwidthChanged(self, val):
    self.clipwidthval = val
    self.NGL_HKL_command("NGL_HKLviewer.normal_clip_plane.clipwidth = %f" %self.clipwidthval)


  def onHKLdistChanged(self, val):
    self.hkldist = val
    self.NGL_HKL_command("NGL_HKLviewer.normal_clip_plane.hkldist = %f" %self.hkldist)


  def onHvecChanged(self, val):
    self.hvecval = val
    self.NGL_HKL_command("NGL_HKLviewer.normal_clip_plane.h = %f" %self.hvecval)


  def onKvecChanged(self, val):
    self.kvecval = val
    self.NGL_HKL_command("NGL_HKLviewer.normal_clip_plane.k = %f" %self.kvecval)


  def onLvecChanged(self, val):
    self.lvecval = val
    self.NGL_HKL_command("NGL_HKLviewer.normal_clip_plane.l = %f" %self.lvecval)


  def onFixedorient(self):
    if self.fixedorientcheckbox.isChecked():
      self.NGL_HKL_command('NGL_HKLviewer.normal_clip_plane.fixorientation = True')
    else:
      self.NGL_HKL_command('NGL_HKLviewer.normal_clip_plane.fixorientation = False')


  def createGroupBox2(self):
    self.GroupBox2 = QGroupBox("Group 2")
    layout = QGridLayout()
    layout.addWidget(self.openFileNameButton,  0, 0, 1, 1)
    layout.addWidget(self.debugbutton, 0, 3, 1, 3)
    layout.addWidget(self.mousemoveslider,  1, 0, 1, 1)
    layout.addWidget(self.mousesensitxtbox,  1, 3, 1, 3)
    #layout.setColumnStretch(1, 2)
    self.GroupBox2.setLayout(layout)


  def createRadiiScaleGroupBox(self):
    self.RadiiScaleGroupBox = QGroupBox("Radii Size of HKL Spheres")
    #self.PowerScaleGroupBox = QGroupBox("Manual Power Scaling of Sphere Radii")

    self.ManualPowerScalecheckbox = QCheckBox()
    self.ManualPowerScalecheckbox.setText("Manual Power Scaling of Sphere Radii")
    self.ManualPowerScalecheckbox.clicked.connect(self.onManualPowerScale)

    self.power_scale_spinBox = QDoubleSpinBox(self.RadiiScaleGroupBox)
    self.nth_power_scale = 0.5
    self.power_scale_spinBox.setValue(self.nth_power_scale)
    self.power_scale_spinBox.setDecimals(2)
    self.power_scale_spinBox.setSingleStep(0.05)
    self.power_scale_spinBox.setRange(0.0, 1.0)
    self.power_scale_spinBox.valueChanged.connect(self.onPowerScaleChanged)
    self.powerscaleLabel = QLabel()
    self.powerscaleLabel.setText("Power scale Factor")

    self.radii_scale_spinBox = QDoubleSpinBox(self.RadiiScaleGroupBox)
    self.radii_scale = 1.0
    self.radii_scale_spinBox.setValue(self.radii_scale)
    self.radii_scale_spinBox.setDecimals(1)
    self.radii_scale_spinBox.setSingleStep(0.1)
    self.radii_scale_spinBox.setRange(0.2, 2.0)
    self.radii_scale_spinBox.valueChanged.connect(self.onRadiiScaleChanged)
    self.radiiscaleLabel = QLabel()
    self.radiiscaleLabel.setText("Linear Scale Factor")

    layout = QGridLayout()
    layout.addWidget(self.ManualPowerScalecheckbox, 1, 0, 1, 2)
    layout.addWidget(self.powerscaleLabel,          2, 0, 1, 2)
    layout.addWidget(self.power_scale_spinBox,      2, 1, 1, 2)
    layout.addWidget(self.radiiscaleLabel,          3, 0, 1, 2)
    layout.addWidget(self.radii_scale_spinBox,      3, 1, 1, 2)
    layout.setColumnStretch (0, 1)
    layout.setColumnStretch (1 ,0)
    self.RadiiScaleGroupBox.setLayout(layout)


  def DebugInteractively(self):
    import code, traceback; code.interact(local=locals(), banner="".join( traceback.format_stack(limit=10) ) )


  def createBottomLeftTabWidget(self):
    self.bottomLeftGroupBox = QGroupBox("Group 3")
    layout = QGridLayout()

    """
    self.bottomLeftTabWidget = QTabWidget()
    self.bottomLeftTabWidget.setSizePolicy(QSizePolicy.Preferred,  QSizePolicy.Ignored)
    tab1 = QWidget()
    tab1hbox = QHBoxLayout()
    tab1hbox.setContentsMargins(5, 5, 5, 5)
    tab1hbox.addWidget(self.millertable)
    tab1.setLayout(tab1hbox)
    tab2 = QWidget()

    tab2hbox = QHBoxLayout()
    tab2hbox.setContentsMargins(5, 5, 5, 5)
    tab2hbox.addWidget(self.textInfo)
    tab2.setLayout(tab2hbox)
    self.bottomLeftTabWidget.addTab(tab1, "&Miller Arrays")
    self.bottomLeftTabWidget.addTab(tab2, "Information")
    """

    layout.addWidget(self.millertable,            0, 0, 1, 1)
    layout.addWidget(self.textInfo,               1, 0, 1, 1)
    layout.setRowStretch (0, 1)
    layout.setRowStretch (1 ,0)
    self.bottomLeftGroupBox.setLayout(layout)


  def MillerComboSelchange(self,i):
    self.NGL_HKL_command("NGL_HKLviewer.scene_id = %d" %i)
    self.SpaceGroupComboBox.clear()
    self.SpaceGroupComboBox.addItems( self.spacegroups )
    # need to supply issymunique flag in infotuple
    #if self.hklscenes_arrays[ i ][6] == 0:
    #  self.mergecheckbox.setEnabled(True)
    #else:
    #  self.mergecheckbox.setEnabled(False)



  def SpacegroupSelchange(self,i):
    self.NGL_HKL_command("NGL_HKLviewer.spacegroupchoice = %d" %i)


  def find_free_port(self):
    import socket
    s = socket.socket()
    s.bind(('', 0))      # Bind to a free port provided by the host.
    port = s.getsockname()[1]
    s.close()
    return port


  def LaunchCCTBXPython(self):
    self.sockport = self.find_free_port()
    self.context = zmq.Context()
    self.socket = self.context.socket(zmq.PAIR)
    self.socket.bind("tcp://127.0.0.1:%s" %self.sockport)
    try: msg = self.socket.recv(flags=zmq.NOBLOCK) #To empty the socket from previous messages
    except Exception as e: pass
    #cmdargs = 'cctbx.python.bat -i -c "from crys3d.hklview import cmdlineframes; myHKLview = cmdlineframes.HKLViewFrame(useSocket=True, high_quality=False, verbose=0)"\n'
    cmdargs = 'cctbx.python.bat -i -c "from crys3d.hklview import cmdlineframes;' \
     + ' myHKLview = cmdlineframes.HKLViewFrame(useGuiSocket=%s, high_quality=True,' %self.sockport \
     + ' verbose=%s, UseOSBrowser= False)"\n' %self.verbose
    #self.cctbxproc = subprocess.Popen( cmdargs, shell=True, stdout=sys.stdout, stderr=sys.stderr)
    self.cctbxproc = subprocess.Popen( cmdargs, shell=True, stdin=subprocess.PIPE, stdout=sys.stdout, stderr=sys.stderr)
    #self.cctbxproc = subprocess.Popen( cmdargs, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    #import code, traceback; code.interact(local=locals(), banner="".join( traceback.format_stack(limit=10) ) )
    time.sleep(1)


  def NGL_HKL_command(self, cmdstr):
    print("sending:\n" + cmdstr)
    self.socket.send(bytes(cmdstr,"utf-8"))
    print("stuff sent")



if __name__ == '__main__':
  try:
    app = QApplication(sys.argv)
    guiobj = NGL_HKLViewer()

    timer = QTimer()
    timer.setInterval(0.1)
    timer.timeout.connect(guiobj.update)
    timer.start(500)

    if guiobj.cctbxproc:
      guiobj.cctbxproc.terminate()
    sys.exit(app.exec_())
  except Exception as e:
    errmsg = str(e)
    print( errmsg  +  traceback.format_exc(limit=10) )
