# -*- coding: utf-8 -*-
from __future__ import division, print_function

from libtbx.program_template import ProgramTemplate

from mmtbx.validation import comparama
from mmtbx.validation.ramalyze import res_type_labels, find_region_max_value

import numpy as np
from collections import Counter
from libtbx.test_utils import approx_equal
from matplotlib.backends.backend_pdf import PdfPages

# =============================================================================

class Program(ProgramTemplate):

  description = '''
phenix.comparama: tool for compare Ramachandran plots, e.g. before-after
  refinement.

Usage examples:
  phenix.comparama model1.pdb model2.pdb
  phenix.comparama model1.cif model2.cif
  '''

  datatypes = ['model', 'phil']

  master_phil_str = """\
    include scope mmtbx.validation.comparama.master_phil_str
    output
    {
      individual_residues = True
        .type = bool
      sorted_individual_residues = False
        .type = bool
      counts = True
        .type = bool
      prefix = kleywegt
        .type = str
      plots = False
        .type = bool
        .help = output Kleywegt plots - arrows on Rama plot showing where \
          residues moved.
      pdf = True
        .type = bool
        .help = save the same plots as one pdf file
    }
"""

  # ---------------------------------------------------------------------------
  def validate(self):
    print('Validating inputs', file=self.logger)
    self.data_manager.has_models(expected_n=2, exact_count=True, raise_sorry=True)
    model_1, model_2 = self._get_models()
    assert model_1.get_hierarchy().is_similar_hierarchy(model_2.get_hierarchy())
    for m in [model_1, model_2]:
      assert m.get_hierarchy().models_size() == 1

  # ---------------------------------------------------------------------------
  def run(self):
    # I'm guessing self.data_manager, self.params and self.logger
    # are already defined here...
    # print('Using model: %s' % self.data_manager.get_default_model_name(), file=self.logger)

    # this must be mmtbx.model.manager?
    model_1, model_2 = self._get_models()

    self.rama_comp = comparama.rcompare(
        model1 = model_1,
        model2 = model_2,
        params = self.params.comparama,
        log = self.logger)

    # outputting results
    results = self.rama_comp.get_results()
    res_columns = zip(*results)
    if self.params.output.individual_residues:
      for r in results:
        self.show_single_result(r)
      print("="*80, file=self.logger)
    if self.params.output.sorted_individual_residues:
      sorted_res = sorted(results, key=lambda tup: tup[1])
      for r in sorted_res:
        self.show_single_result(r)
      print("="*80, file=self.logger)
    print ("mean: %.3f std: %.3f" % (np.mean(res_columns[1]), np.std(res_columns[1])),
        file=self.logger)
    print("Sum of rama scores: %.3f -> %.3f" % \
        (np.sum(res_columns[-2]), np.sum(res_columns[-1])) , file=self.logger)
    print("Sum of rama scores/n_residues: %.4f -> %.4f (%d residues)" % \
        (np.mean(res_columns[-2]), np.mean(res_columns[-1]), len(res_columns[-1])), file=self.logger)
    # printing scaled vals
    # rescale both
    v1, v2 = rama_rescale(results)
    print("Sum of rama scores scaled: %.3f -> %.3f" % \
        (np.sum(v1), np.sum(v2)) , file=self.logger)
    print("Sum of rama scores/n_residues scaled: %.4f -> %.4f (%d residues)" % \
        (np.mean(v1), np.mean(v2), len(v1)), file=self.logger)
    if self.params.output.counts:
      cntr = Counter(res_columns[-4])
      for k, v in cntr.iteritems():
        print("%-20s: %d" % (k,v), file=self.logger)

    if self.params.output.plots or self.params.output.pdf:
      base_fname = "%s--%s" % (self.data_manager.get_model_names()[0].split('.')[0],
          self.data_manager.get_model_names()[1].split('.')[0])
      rama1, rama2 = self.rama_comp.get_ramalyze_objects()
      plots = rama2.get_plots(
          show_labels=True,
          point_style='bo',
          markersize=3,
          markeredgecolor="black",
          dpi=300,
          markerfacecolor="white")
      pdf_fname = "%s_%s.pdf" % (base_fname, self.params.output.prefix)
      if self.params.output.pdf:
        pdfp = PdfPages(pdf_fname)
      for pos, plot in plots.iteritems():
        # prepare data
        got_outliers = [x for x in results if (x[-3]==pos and x[-4].find("-> OUTLIER") > 0)]#.sort(key=lambda x:x[1], reverse=True)
        got_outliers.sort(key=lambda x:x[1], reverse=True)
        print("got_outliers:", len(got_outliers))
        for o in got_outliers:
          self.show_single_result(o)
        got_not_outliers = [x for x in results if (x[-3]==pos and x[-4] == "OUTLIER -> Favored")]#.sort(key=lambda x:x[1], reverse=True)
        got_not_outliers.sort(key=lambda x:x[1], reverse=True)
        print("got_not_outliers:", len(got_not_outliers))
        for o in got_not_outliers:
          self.show_single_result(o)

        for data, color in [(got_outliers, "red"), (got_not_outliers, "lime")]:
          # print (len(data))
          if data and len(data) < 0: continue
          ad = [((x[2], x[3]),(x[4], x[5])) for x in data]
          add_arrows_on_plot(
              plot,
              ad,
              color=color)
        file_label = res_type_labels[pos].replace("/", "_")
        plot_file_name = "%s_%s_%s_plot.png" % (
            base_fname, self.params.output.prefix, file_label)
        if self.params.output.plots:
          print("saving: '%s'" % plot_file_name)
          plot.save_image(plot_file_name, dpi=300)
        if self.params.output.pdf:
          pdfp.savefig(plot.figure)
      if self.params.output.pdf:
        print("saving: '%s'" % pdf_fname)
        pdfp.close()

  def show_single_result(self, r):
    print("%s %.2f, (%.1f:%.1f), (%.1f:%.1f), %s, Score: %.4f -> %.4f" % \
        (r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[8], r[9]),
        file=self.logger)

  # ---------------------------------------------------------------------------
  def get_results(self):
    return self.rama_comp.get_results()

  def _get_models(self):
    m_names = self.data_manager.get_model_names()
    model_1 = self.data_manager.get_model(filename=m_names[0])
    model_2 = self.data_manager.get_model(filename=m_names[1])
    return model_1, model_2

def breake_arrow_if_needed(abeg, aend, plot_ranges):
  eps = 1e-3
  tp = comparama.two_rama_points(abeg, aend)
  actual_len = tp.length(abeg, aend)
  min_len = tp.min_length()
  best_xy_multipliers = tp.get_xy_multipliers()
  result = []
  if best_xy_multipliers == [0,0]:
    return [(abeg,aend)]
  # Now we figure out how to brake it.
  result = [ [abeg, (0,0)], [(0,0), aend] ]
  ix = 0 if best_xy_multipliers[0] == -1 else 1
  iy = 0 if best_xy_multipliers[1] == -1 else 1
  if approx_equal(abeg[0], aend[0], eps, out=None):
    # case where x1 == x2
    result[0][1] = (abeg[0], plot_ranges[0][iy])
    result[1][0] = (abeg[0], plot_ranges[0][1-iy])
  elif best_xy_multipliers.count(0) == 1:
    # general case, 1 border crossing
    # y = ax + b
    n_aend = (aend[0]+360*best_xy_multipliers[0], aend[1]+360*best_xy_multipliers[1])
    a = (n_aend[1]-abeg[1]) / (n_aend[0] - abeg[0])
    b = n_aend[1] - a*n_aend[0]
    if best_xy_multipliers[0] != 0:
      # x wrapping, calculating y
      y = a*(plot_ranges[0][ix]) + b
      y = comparama.get_distance(y, 0)
      result[0][1] = (plot_ranges[0][ix],   y)
      result[1][0] = (plot_ranges[0][1-ix], y)
    else:
      # y wrapping, calculating x
      x = (plot_ranges[1][iy] - b) / a
      x = comparama.get_distance(x, 0)
      result[0][1] = (x, plot_ranges[1][iy])
      result[1][0] = (x, plot_ranges[1][1-iy])
  else:
    # both sides cutting. just go to the corner to make things simple
    result[0][1] = (plot_ranges[0][ix], plot_ranges[1][iy])
    result[1][0] = (plot_ranges[0][1-ix], plot_ranges[1][1-iy])
  return result


def add_arrows_on_plot(
    p,
    arrows_data,
    color='green',
    wrap_arrows=True,
    plot_ranges=[(-180, 180), (-180, 180)]):
  """
  p - pyplot
  arrows_data - [((x,y beginning), (x,y end)), ... ((xy),(xy))]
  wrap_arrows - draw shortest possible arrow - wrap around plot edges
  ranges - ranges of the plot
  """
  import matplotlib.patches as patches
  import matplotlib.lines as lines

  style="Simple,head_length=10,head_width=5,tail_width=1"
  for arrow in arrows_data:
    if wrap_arrows:
      r = breake_arrow_if_needed(arrow[0], arrow[1], plot_ranges)
      for l_coors in r[:-1]:
        l = lines.Line2D(
            xdata = [l_coors[0][0], l_coors[1][0]],
            ydata = [l_coors[0][1], l_coors[1][1]],
            linewidth=1.7, color=color)
        p.plot.add_line(l)
    p.plot.add_patch(patches.FancyArrowPatch(
        r[-1][0],
        r[-1][1],
        arrowstyle=style,
        color = color,
        linewidth=0.5,
        zorder=10,
        ))

def rama_rescale(results):
  res1 = []
  res2 = []
  for r1_id_str, diff2, r1_phi, r1_psi, r2_phi, r2_psi, v, r2_res_type, r1_score, r2_score in results:
    max_value1 = find_region_max_value(r2_res_type, r1_phi, r1_psi)
    if max_value1 is None:
      res1.append(r1_score)
    else:
      # if max_value1[1] < 1:
      #   print("rescaling: %.4f -> %.4f" % (r1_score, r1_score/max_value1[1]))
      res1.append(r1_score/max_value1[1])
    max_value2 = find_region_max_value(r2_res_type, r2_phi, r2_psi)
    if max_value2 is None:
      res2.append(r2_score)
    else:
      res2.append(r2_score/max_value2[1])
  return res1, res2