from cctbx.xray import ext
from cctbx.eltbx import caasf
from cctbx import adptbx
from scitbx.boost_python_utils import injector
import sys

class scatterer(ext.scatterer):

  def __init__(self, label="",
                     site=(0,0,0),
                     u=None,
                     occupancy=1,
                     scattering_type=None,
                     fp=0,
                     fdp=0,
                     b=None):
    assert u is None or b is None
    if   (b is not None): u = adptbx.b_as_u(b)
    elif (u is None): u = 0
    if (scattering_type is None):
      scattering_type = caasf.wk1995(label, 0).label()
    ext.scatterer.__init__(
      self, label, site, u, occupancy, scattering_type, fp, fdp)

class _scatterer(injector, ext.scatterer):

  def copy(self, label=None,
                 site=None,
                 u=None,
                 b=None,
                 occupancy=None,
                 scattering_type=None,
                 fp=None,
                 fdp=None):
    assert u is None or b is None
    if (b is not None): u = adptbx.b_as_u(b)
    if (label is None): label = self.label
    if (site is None): site = self.site
    if (u is None):
      if (self.anisotropic_flag): u = self.u_star
      else: u = self.u_iso
    if (occupancy is None): occupancy = self.occupancy
    if (scattering_type is None): scattering_type = self.scattering_type
    if (fp is None): fp = self.fp
    if (fdp is None): fdp = self.fdp
    return scatterer(
      label=label,
      site=site,
      u=u,
      occupancy=occupancy,
      scattering_type=scattering_type,
      fp=fp,
      fdp=fdp)

  def show(self, f=None, unit_cell=None):
    if (f is None): f = sys.stdout
    print >> f, "%-4s" % self.label,
    print >> f, "%3d" % self.multiplicity(),
    print >> f, "%7.4f %7.4f %7.4f" % self.site,
    print >> f, "%4.2f" % self.occupancy,
    if (not self.anisotropic_flag):
      print >> f, "%6.4f" % self.u_iso,
    else:
      assert unit_cell is not None
      print >> f, ("%6.3f " * 5 + "%6.3f") % adptbx.u_star_as_u_cart(
        unit_cell, self.u_star),
    print >> f
    if (self.fp != 0 or self.fdp != 0):
      print >> f, "     fp,fdp = %6.4f,%6.4f" % (
        self.fp,
        self.fdp)
