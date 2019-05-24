from __future__ import division
from __future__ import print_function
from cctbx.eltbx.development.format_gaussian_fits import read_pickled_fits
from cctbx.eltbx import xray_scattering
import cctbx.eltbx.gaussian_fit
import scitbx.math.gaussian_fit
import hashlib
import time
import sys

def write_module_info(f, module_object):
  file_name = module_object.__file__
  if (file_name.endswith(".pyc")):
    file_name = file_name[:-1]
  assert file_name.endswith(".py")
  file_content = open(file_name, "rb").read()
  m = hashlib.md5()
  m.update(file_content)
  print("// Module:", module_object.__name__, file=f)
  print("//   size:", len(file_content), file=f)
  print("//   MD5 hexdigest:", m.hexdigest(), file=f)
  print(file=f)

def write_header(f):
  print("""\
#include <cctbx/eltbx/xray_scattering/n_gaussian_raw.h>
#include <cstring>

namespace {

#undef D
#define D static const double
""", file=f)

def identifier(label):
  return (label.lower()
    .replace("'", "prime")
    .replace("+", "plus")
    .replace("-", "minus"))

def write_fit_group(f, label, group):
  if (label == "h_sds"): # retro-fitted
    group = list(reversed(group))
  id = identifier(label)
  s = "D %s_s[] = {" % id
  for fit in group:
    s += " " + str(fit.stol) + ","
  s = s[:-1] + " };"
  print(s, file=f)
  print("D %s_e[] = {" % id, file=f)
  if (label == "h_sds"): # retro-fitted
    from cctbx.eltbx.development.hydrogen_plots import fit_input
    from scitbx.array_family import flex
    fi = fit_input()
  for fit in group:
    sel = fi.stols <= fit.stol + 1.e-6
    if (label == "h_sds"): # retro-fitted
      gaussian_fit = scitbx.math.gaussian.fit(
        fi.stols.select(sel),
        fi.data.select(sel),
        fi.sigmas.select(sel),
        fit)
      s = str(flex.max(gaussian_fit.significant_relative_errors()))
    else:
      s = str(fit.max_error)
    if (fit is not group[-1]): s += ","
    print(s, file=f)
  print("};", file=f)
  labels = []
  for fit_unsorted in group:
    fit = fit_unsorted.sort()
    lbl = "%s_%d" % (id, fit.n_terms())
    if (fit.use_c()): lbl += "c"
    print("D %s[] = {" % lbl, file=f)
    labels.append(lbl)
    buf = []
    for a,b in zip(fit.array_of_a(), fit.array_of_b()):
      buf.append("%s, %s," % (str(a), str(b)))
    if (fit.use_c()):
      buf.append(str(fit.c()))
    else:
      buf[-1] = buf[-1][:-1]
    for s in buf: print(s, file=f)
    print("};", file=f)
  print("D* %s_c[] = { %s };" % (id, ", ".join(labels)), file=f)
  print(file=f)
  return
  print("""\
""", file=f)

def write_labels(f, labels):
  print("""\
static const char*
labels[] = {""", file=f)
  last_label = labels[-1]
  for label in labels:
    assert not '"' in label
    c = ","
    if (label == last_label): c = ""
    print('"%s"%s' % (label, c), file=f)
  print("};", file=f)

def write_table(f, labels):
  print("""\
static const cctbx::eltbx::xray_scattering::n_gaussian::raw::entry
table[] = {""", file=f)
  last_label = labels[-1]
  for label in labels:
    id = identifier(label)
    c = ","
    if (label == last_label): c = ""
    print('%s_s, %s_e, %s_c%s' % (id, id, id, c), file=f)
  print("};", file=f)

def write_tail(f, localtime, table_size):
  print("""\
} // namespace <anonymous>

namespace cctbx { namespace eltbx { namespace xray_scattering {
namespace n_gaussian { namespace raw {

  const char*
  get_tag() { return "%s"; }

  const char**
  get_labels() { return labels; }

  unsigned int
  get_table_size() { return %dU; }

  const entry*
  get_table() { return table; }

}}}}} // namespace cctbx::eltbx::xray_scattering::n_gaussian::raw""" % (
  "%04d_%02d_%02d_%02d%02d" % localtime[:5], table_size), file=f)

def run(gaussian_fit_pickle_file_names):
  localtime = time.localtime()
  fits = read_pickled_fits(gaussian_fit_pickle_file_names)
  f = sys.stdout
  if (gaussian_fit_pickle_file_names[0].find("sds") >= 0): # retro-fitted
    write_fit_group(f, "h_sds", fits.all["SDS"])
    return
  print("// This is an automatically generated file. DO NOT EDIT!", file=f)
  print(file=f)
  print("// Time %04d/%02d/%02d %02d:%02d:%02d" % localtime[:6], file=f)
  print("// Time zone:", time.tzname, file=f)
  print(file=f)
  write_module_info(f, cctbx.eltbx.gaussian_fit)
  write_module_info(f, scitbx.math.gaussian_fit)
  print("// Parameters:", file=f)
  for k,v in fits.parameters.items():
    print("//   %s:" % k, v, file=f)
  print(file=f)
  present = []
  missing = []
  for wk in xray_scattering.wk1995_iterator():
    try:
      fit_group = fits.all[wk.label()]
    except Exception:
      missing.append(wk.label())
    else:
      present.append(wk.label())
  if (len(missing) > 0):
    print("// Warning: Missing scattering labels:", file=f)
    for label in missing:
      print("// ", label, file=f)
    print(file=f)
  write_header(f)
  for label in present:
    write_fit_group(f, label, fits.all[label])
  write_labels(f, present)
  write_table(f, present)
  write_tail(f, localtime, len(present))

if (__name__ == "__main__"):
  run(sys.argv[1:])
