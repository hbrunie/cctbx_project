# -*- mode: python; coding: utf-8; indent-tabs-mode: nil; python-indent: 2 -*-
#
# LIBTBX_SET_DISPATCHER_NAME cxi.xmerge
#
# $Id$

from __future__ import division

import iotbx.phil
from cctbx.array_family import flex
from cctbx.crystal import symmetry
from cctbx import uctbx
from iotbx import mtz
from libtbx.utils import Usage, multi_out
from libtbx import easy_pickle
import math
import os
import time
import sys

from xfel.command_line.cxi_merge import master_phil,scaling_manager
from xfel.command_line.cxi_merge import unit_cell_distribution,show_overall_observations
from xfel.command_line.cxi_merge import scaling_result
from cctbx.crystal_orientation import crystal_orientation
from xfel import column_parser
from xfel.cxi.util import is_odd_numbered

#-----------------------------------------------------------------------
class xscaling_manager (scaling_manager) :
  def __init__ (self, miller_set, i_model, params, log=None) :
    scaling_manager.__init__(self,miller_set,i_model,params,log)

  def scale_all (self) :
    t1 = time.time()

    self.read_all_mysql()
    self.millers = self.millers_mysql
    self.frames = self.frames_mysql
    self._frames = self._frames_mysql
    self.observations = self.observations_mysql
    self._observations = self._observations_mysql
    if self.params.model is None:
      self.n_accepted = len(self.frames["cc"])
      self.n_low_corr = 0
    else:
      self.n_accepted = (self.frames["cc"]>self.params.min_corr).count(True)
      self.n_low_corr = (self.frames["cc"]>self.params.min_corr).count(False)
      statsy = flex.mean_and_variance(self.frames["cc"])
      print >> self.log, "%5d images, individual image correlation coefficients are %6.3f +/- %5.3f"%(
               len(self.frames["cc"]),
               statsy.mean(),  statsy.unweighted_sample_standard_deviation(),
               )

    t2 = time.time()
    print >> self.log, ""
    print >> self.log, "#" * 80
    print >> self.log, "FINISHED MERGING"
    print >> self.log, "  Elapsed time: %.1fs" % (t2 - t1)
    print >> self.log, "  %d integration files were accepted" % (
      self.n_accepted)
    print >> self.log, "  %d rejected due to poor correlation" % \
      self.n_low_corr

  def read_all_mysql(self):
    print "reading observations from MySQL database"

    if self.params.backend == 'MySQL':
      from xfel.cxi.merging_database import manager
    elif self.params.backend == 'SQLite':
      from xfel.cxi.merging_database_sqlite3 import manager
    else:
      from xfel.cxi.merging_database_fs import manager

    CART = manager(self.params)
    self.millers_mysql = CART.read_indices()
    self.millers = self.millers_mysql

    self.observations_mysql = CART.read_observations()
    parser = column_parser()
    parser.set_int("hkl_id",self.observations_mysql["hkl_id"])
    parser.set_double("i",self.observations_mysql["i"])
    parser.set_double("sigi",self.observations_mysql["sigi"])
    parser.set_int("frame_id",self.observations_mysql["frame_id"])
    parser.set_int("H",self.observations_mysql["original_h"])
    parser.set_int("K",self.observations_mysql["original_k"])
    parser.set_int("L",self.observations_mysql["original_l"])
    self._observations_mysql = parser
    self.observations = dict(hkl_id=parser.get_int("hkl_id"),
                             i=parser.get_double("i"),
                             sigi=parser.get_double("sigi"),
                             frame_id=parser.get_int("frame_id"),
                             H=parser.get_int("H"),
                             K=parser.get_int("K"),
                             L=parser.get_int("L"),
                             )

    self.frames_mysql = CART.read_frames()
    parser = column_parser()
    parser.set_int("frame_id",self.frames_mysql["frame_id"])
    parser.set_double("wavelength",self.frames_mysql["wavelength"])
    parser.set_double("cc",self.frames_mysql["cc"])
    parser.set_double("slope",self.frames_mysql["slope"])
    parser.set_double("offset",self.frames_mysql["offset"])
    self._frames_mysql = parser

    CART.join()

  def read_all(self):
    # XXX Should not be used any more--migrate C++ into
    # cxi/merging_database_fs.py?
    print "reading observations from flat-file database"
    self.frames = dict( frame_id=flex.int(),
                        wavelength=flex.double(),
                        cc=flex.double(),
                        slope=flex.double(),
                        offset=flex.double(),
                        odd_numbered=flex.bool(),
                        orientation=[],
                        unit_cell=[])
    self.millers = dict(merged_asu_hkl=flex.miller_index())
    G = open(self.params.output.prefix+"_miller.db","r")
    for line in G.xreadlines():
      tokens = line.strip().split()
      self.millers["merged_asu_hkl"].append((int(tokens[1]),int(tokens[2]),int(tokens[3])))

# --- start C++ read
    parser = column_parser()
    parser.set_int("hkl_id",0)
    parser.set_double("i",1)
    parser.set_double("sigi",2)
    parser.set_int("frame_id",5)
    parser.set_int("H",7)
    parser.set_int("K",8)
    parser.set_int("L",9)

    G = open(self.params.output.prefix+"_observation.db","r")
    for line in G.xreadlines():
      parser.parse_from_line(line)
    self.observations = dict(hkl_id=parser.get_int("hkl_id"),
                             i=parser.get_double("i"),
                             sigi=parser.get_double("sigi"),
                             frame_id=parser.get_int("frame_id"),
                             H=parser.get_int("H"),
                             K=parser.get_int("K"),
                             L=parser.get_int("L"),
                             )
    self._observations = parser
    G.close()
# --- done with C++ read

    G = open(self.params.output.prefix+"_frame.db","r")
    for line in G.xreadlines():
      tokens = line.strip().split()
      self.frames["frame_id"].append(int(tokens[0]))
      self.frames["wavelength"].append(float(tokens[1]))
      self.frames["cc"].append(float(tokens[5]))
      self.frames["slope"].append(float(tokens[6]))
      self.frames["offset"].append(float(tokens[7]))
      self.frames["odd_numbered"].append( is_odd_numbered(tokens[17]) )
      # components of orientation direct matrix
      odm = (float(tokens[8]), float(tokens[9]), float(tokens[10]),
             float(tokens[11]), float(tokens[12]), float(tokens[13]),
             float(tokens[14]), float(tokens[15]), float(tokens[16]),)
      CO = crystal_orientation(odm, False)
      self.frames["orientation"].append(CO)
      self.frames["unit_cell"].append(CO.unit_cell())
    G.close()
    parser = column_parser()
    parser.set_int("frame_id",0)
    parser.set_double("wavelength",1)
    parser.set_double("cc",5)
    parser.set_double("slope",6)
    parser.set_double("offset",7)
    G = open(self.params.output.prefix+"_frame.db","r")
    for line in G.xreadlines():
      parser.parse_from_line(line)
    self._frames = parser

#-----------------------------------------------------------------------
def run(args):
  phil = iotbx.phil.process_command_line(args=args, master_string=master_phil).show()
  work_params = phil.work.extract()
  if ("--help" in args) :
    libtbx.phil.parse(master_phil.show())
    return

  if ((work_params.d_min is None) or
      (work_params.data is None) or
      ( (work_params.model is None) and work_params.scaling.algorithm != "mark1") ) :
    raise Usage("cxi.merge "
                "d_min=4.0 "
                "data=~/scratch/r0220/006/strong/ "
                "model=3bz1_3bz2_core.pdb")
  if ((work_params.rescale_with_average_cell) and
      (not work_params.set_average_unit_cell)) :
    raise Usage("If rescale_with_average_cell=True, you must also specify "+
      "set_average_unit_cell=True.")

  log = open("%s_%s.log" % (work_params.output.prefix,work_params.scaling.algorithm), "w")
  out = multi_out()
  out.register("log", log, atexit_send_to=None)
  out.register("stdout", sys.stdout)

  # Verify that the externally supplied isomorphous reference, if
  # present, defines a suitable column of intensities, and exit with
  # error if it does not.  Then warn if it is necessary to generate
  # Bijvoet mates.  Failure to catch these issues here would lead to
  # possibly obscure problems in cxi/cxi_cc.py later on.
  try:
    data_SR = mtz.object(work_params.scaling.mtz_file)
  except RuntimeError:
    pass
  else:
    array_SR = None
    obs_labels = []
    for array in data_SR.as_miller_arrays():
      this_label = array.info().label_string().lower()
      if array.observation_type() is not None:
        obs_labels.append(this_label.split(',')[0])
      if this_label.find('fobs')>=0:
        array_SR = array.as_intensity_array()
        break
      if this_label.find('imean')>=0:
        array_SR = array.as_intensity_array()
        break
      if this_label.find(work_params.scaling.mtz_column_F)==0:
        array_SR = array.as_intensity_array()
        break

    if array_SR is None:
      known_labels = ['fobs', 'imean', work_params.scaling.mtz_column_F]
      raise Usage(work_params.scaling.mtz_file +
                  " does not contain any observations labelled [" +
                  ", ".join(known_labels) +
                  "].  Please set scaling.mtz_column_F to one of [" +
                  ",".join(obs_labels) + "].")
    elif not work_params.merge_anomalous and not array_SR.anomalous_flag():
      print >> out, "Warning: Preserving anomalous contributors, but %s " \
        "has anomalous contributors merged.  Generating identical Bijvoet " \
        "mates." % work_params.scaling.mtz_file

  # Read Nat's reference model from an MTZ file.  XXX The observation
  # type is given as F, not I--should they be squared?  Check with Nat!
  print >> out, "I model"
  if work_params.model is not None:
    from xfel.cxi.merging.general_fcalc import run
    i_model = run(work_params)
    work_params.target_unit_cell = i_model.unit_cell()
    work_params.target_space_group = i_model.space_group_info()
    i_model.show_summary()
  else:
    i_model = None

  print >> out, "Target unit cell and space group:"
  print >> out, "  ", work_params.target_unit_cell
  print >> out, "  ", work_params.target_space_group

  miller_set = symmetry(
      unit_cell=work_params.target_unit_cell,
      space_group_info=work_params.target_space_group
    ).build_miller_set(
      anomalous_flag=not work_params.merge_anomalous,
      d_min=work_params.d_min / math.pow(
        1 + work_params.unit_cell_length_tolerance, 1 / 3))

# ---- Augment this code with any special procedures for x scaling
  scaler = xscaling_manager(
    miller_set=miller_set,
    i_model=i_model,
    params=work_params,
    log=out)
  scaler.scale_all()
  if scaler.n_accepted == 0:
    return None
# --- End of x scaling
  scaler.uc_values = unit_cell_distribution()
  for icell in xrange(len(scaler.frames["unit_cell"])):
    if scaler.params.model is None:
      scaler.uc_values.add_cell(
      unit_cell=scaler.frames["unit_cell"][icell])
    else:
      scaler.uc_values.add_cell(
      unit_cell=scaler.frames["unit_cell"][icell],
      rejected=(scaler.frames["cc"][icell] < scaler.params.min_corr))

  scaler.show_unit_cell_histograms()
  if (work_params.rescale_with_average_cell) :
    average_cell_abc = scaler.uc_values.get_average_cell_dimensions()
    average_cell = uctbx.unit_cell(list(average_cell_abc) +
      list(work_params.target_unit_cell.parameters()[3:]))
    work_params.target_unit_cell = average_cell
    print >> out, ""
    print >> out, "#" * 80
    print >> out, "RESCALING WITH NEW TARGET CELL"
    print >> out, "  average cell: %g %g %g %g %g %g" % \
      work_params.target_unit_cell.parameters()
    print >> out, ""
    scaler.reset()
    scaler = xscaling_manager(
      miller_set=miller_set,
      i_model=i_model,
      params=work_params,
      log=out)
    scaler.scale_all()
    scaler.uc_values = unit_cell_distribution()
    for icell in xrange(len(scaler.frames["unit_cell"])):
      if scaler.params.model is None:
        scaler.uc_values.add_cell(
        unit_cell=scaler.frames["unit_cell"][icell])
      else:
        scaler.uc_values.add_cell(
        unit_cell=scaler.frames["unit_cell"][icell],
        rejected=(scaler.frames["cc"][icell] < scaler.params.min_corr))
    scaler.show_unit_cell_histograms()
  if False : #(work_params.output.show_plots) :
    try :
      plot_overall_completeness(completeness)
    except Exception, e :
      print "ERROR: can't show plots"
      print "  %s" % str(e)
  print >> out, "\n"

  reserve_prefix = work_params.output.prefix
  for data_subset in [1,2,0]:
    work_params.data_subset = data_subset
    work_params.output.prefix = "%s_s%1d_%s"%(reserve_prefix,data_subset,work_params.scaling.algorithm)

    if work_params.data_subset == 0:
      scaler.frames["data_subset"] = flex.bool(scaler.frames["frame_id"].size(),True)
    elif work_params.data_subset == 1:
      scaler.frames["data_subset"] = scaler.frames["odd_numbered"]
    elif work_params.data_subset == 2:
      scaler.frames["data_subset"] = scaler.frames["odd_numbered"]==False

  # --------- New code ------------------
    #sanity check
    for mod,obs in zip(miller_set.indices(), scaler.millers["merged_asu_hkl"]):
      if mod!=obs: raise Exception("miller index lists inconsistent--check d_min are equal for merge and xmerge scripts")
      assert mod==obs

    """Sum the observations of I and I/sig(I) for each reflection.
    sum_I = flex.double(i_model.size(), 0.)
    sum_I_SIGI = flex.double(i_model.size(), 0.)
    scaler.completeness = flex.int(i_model.size(), 0)
    scaler.summed_N = flex.int(i_model.size(), 0)
    scaler.summed_wt_I = flex.double(i_model.size(), 0.)
    scaler.summed_weight = flex.double(i_model.size(), 0.)
    scaler.n_rejected = flex.double(scaler.frames["frame_id"].size(), 0.)
    scaler.n_obs = flex.double(scaler.frames["frame_id"].size(), 0.)
    scaler.d_min_values = flex.double(scaler.frames["frame_id"].size(), 0.)
    scaler.ISIGI = {}"""

    from xfel import scaling_results, get_scaling_results, get_isigi_dict
    results = scaling_results(scaler._observations, scaler._frames,
              scaler.millers["merged_asu_hkl"],scaler.frames["data_subset"])
    results.__getattribute__(
      work_params.scaling.algorithm)(
      scaler.params.min_corr, scaler.params.target_unit_cell)

    sum_I, sum_I_SIGI, \
    scaler.completeness, scaler.summed_N, \
    scaler.summed_wt_I, scaler.summed_weight, scaler.n_rejected, scaler.n_obs, \
    scaler.d_min_values, i_sigi_list = get_scaling_results(results)

    scaler.ISIGI = get_isigi_dict(results)

    if work_params.merging.refine_G_Imodel:
      from scitbx.lbfgs.tst_curvatures import lbfgs_with_curvatures_mix_in

      class find_scale(lbfgs_with_curvatures_mix_in):
        def __init__(self, millers, observations, frames, scaler):

          """This function is largely redundant, because it duplicates what is
          done during mark1 scaling.

          @param millers xxxx Ordered union of all Miller indices
                              observed on all frames
          @param observations Database structure of observations
          @param frames       Database structure of frames
          """

          self._millers = millers
          self._observations = observations

          self._data = observations.get_double('i')
          self._hkl = observations.get_int('hkl_id')
          self._sigmas = observations.get_double('sigi')
          self._frames = observations.get_int('frame_id')

          # XXX Could be more clever about this here, because this
          # will determine scale factors for rejected frames as well!
          # Better named selected_frames?
          self._subset = frames['data_subset']

          # XXX Useless assert?
          assert len(self._hkl) == len(self._data) \
            and  len(self._hkl) == len(self._sigmas)

          # Initialise all per-frame scale factors to one.
          n_frames = len(self._subset)
          self.x = flex.double(n_frames + len(self._millers))
          for i in range(n_frames):
            self.x[i] = 1

          # For each Miller index, the weighted (XXX) average
          # intensity of all the observations serves as an initial
          # estimate of the merged intensity.  This is all Monte Carlo
          # scaling would do.
          #
          # Filter non-positive reflections.  XXX Should apply
          # resolution filter as well, and use a weight vector (see
          # also the nan comment below).
          #
          # Could still have unobserved reflections.  Do not use
          # float('nan') for those, because it's tricky to get that to
          # play nice with the cctbx C++ environment.
          assert len(self._millers) == len(scaler.summed_wt_I) \
            and  len(self._millers) == len(scaler.summed_weight)

          for i in range(len(self._millers)):
            if scaler.summed_weight[i] > 0:
              self.x[n_frames + i] = scaler.summed_wt_I[i] / scaler.summed_weight[i]
              #self.weight[n_frames + i] = math.sqrt(1 / scaler.summed_weight[i])

          # Should be the last call in the application-specific minimizer
          # class.
          #super(find_scale, self).__init__()


        def compute_functional_and_gradients(self):
          """The compute_functional_and_gradients() function

          @return Two-tuple of the value of the functional, and an
                  <code>n</code>-long vector with the values of the
                  gradients at the current position
          """

          #from libtbx.development.timers import Profiler
          from xfel import compute_functional_and_gradients

          #p = Profiler("compute_functional_and_gradients [C++]")
          (f, g) = compute_functional_and_gradients(
            self.x, self._observations, self._subset)
          #del p

          # XXX Only output this every 100 iterations or so.
          print "* f =% 10.4e" % (math.sqrt(f))

          # Warn if there are non_positive per-frame scaling factors.
          scales = self.x[0:len(self._subset)]
          sel = (scales <= 1e-6) # XXX Or just zero!
          n_non_positive = sel.count(True)
          if n_non_positive > 0:
            print "Have %d non-positive per-frame scaling factors:" % \
              n_non_positive #, list(scales.select(sel))

          return (f, g)


        def curvatures(self):
          from xfel import curvatures
          return curvatures(self.x, self._observations, self._subset)


        def run(self):
          from scitbx import lbfgs
          termination_params = lbfgs.termination_parameters(
            traditional_convergence_test=False,
            max_iterations=2000) # XXX
          self._minimizer = lbfgs.run(target_evaluator=self)
                                      #termination_params=termination_params)


      my_find_scale = find_scale(
        scaler.millers['merged_asu_hkl'],
        scaler._observations,
        scaler.frames,
        scaler)
      my_find_scale.run()

      from xfel import get_scaling_results_mark2
      sum_I, sum_I_SIGI, \
        scaler.completeness, scaler.summed_N, \
        scaler.summed_wt_I, scaler.summed_weight, scaler.n_rejected, \
        scaler.n_obs, scaler.d_min_values, i_sigi_list = get_scaling_results_mark2(my_find_scale.x, results, scaler.params.target_unit_cell)
      scaler.ISIGI = get_isigi_dict(results)


    scaler.wavelength = scaler.frames["wavelength"]
    scaler.corr_values = scaler.frames["cc"]

    scaler.rejected_fractions = flex.double(scaler.frames["frame_id"].size(), 0.)
    for irej in xrange(len(scaler.rejected_fractions)):
      if scaler.n_obs[irej] > 0:
        scaler.rejected_fractions = scaler.n_rejected[irej]/scaler.n_obs[irej]
  # ---------- End of new code ----------------

    miller_set_avg = miller_set.customized_copy(
      unit_cell=work_params.target_unit_cell)

    table1 = show_overall_observations(
      obs=miller_set_avg,
      redundancy=scaler.completeness,
      summed_wt_I=scaler.summed_wt_I,
      summed_weight=scaler.summed_weight,
      ISIGI=scaler.ISIGI,
      n_bins=work_params.output.n_bins,
      title="Statistics for all reflections",
      out=out,
      work_params=work_params)
    print >> out, ""
    if work_params.scaling.algorithm == 'mark0':
      n_refl, corr = scaler.get_overall_correlation(sum_I)
    else:
      n_refl, corr = ((scaler.completeness > 0).count(True), 0)
    print >> out, "\n"
    table2 = show_overall_observations(
      obs=miller_set_avg,
      redundancy=scaler.summed_N,
      summed_wt_I=scaler.summed_wt_I,
      summed_weight=scaler.summed_weight,
      ISIGI=scaler.ISIGI,
      n_bins=work_params.output.n_bins,
      title="Statistics for reflections where I > 0",
      out=out,
      work_params=work_params)

    print >> out, ""
    mtz_file, miller_array = scaler.finalize_and_save_data()

    loggraph_file = os.path.abspath("%s_graphs.log" % work_params.output.prefix)
    f = open(loggraph_file, "w")
    f.write(table1.format_loggraph())
    f.write("\n")
    f.write(table2.format_loggraph())
    f.close()
    result = scaling_result(
      miller_array=miller_array,
      plots=scaler.get_plot_statistics(),
      mtz_file=mtz_file,
      loggraph_file=loggraph_file,
      obs_table=table1,
      all_obs_table=table2,
      n_reflections=n_refl,
      overall_correlation=corr)
    easy_pickle.dump("%s.pkl" % work_params.output.prefix, result)
  work_params.output.prefix = reserve_prefix

  # Output table with number of images contribution reflections per
  # resolution bin.
  from libtbx import table_utils

  miller_set_avg.setup_binner(
    d_max=100000, d_min=work_params.d_min, n_bins=work_params.output.n_bins)
  table_data = [["Bin", "Resolution Range", "# images"]]
  if work_params.model is None:
    appropriate_min_corr = -1.1 # lowest possible c.c.
  else:
    appropriate_min_corr = work_params.min_corr
  for i_bin in miller_set_avg.binner().range_used():
    col_count = '%8d' % results.count_frames(
      appropriate_min_corr, miller_set_avg.binner().selection(i_bin))
    col_legend = '%-13s' % miller_set_avg.binner().bin_legend(
      i_bin=i_bin, show_bin_number=False, show_bin_range=False,
      show_d_range=True, show_counts=False)
    table_data.append(['%3d' % i_bin, col_legend, col_count])

  n_frames = (scaler.frames['cc'] > appropriate_min_corr).count(True)
  table_data.append([""] * len(table_data[0]))
  table_data.append(["All", "", '%8d' % n_frames])
  print >> out
  print >> out, table_utils.format(
    table_data, has_header=1, justify='center', delim=' ')

  reindexing_ops = {"h,k,l":0} # get a list of all reindexing ops for this dataset
  if work_params.merging.reverse_lookup is not None:
    for key in scaler.reverse_lookup:
      if reindexing_ops.get(scaler.reverse_lookup[key], None) is None:
        reindexing_ops[scaler.reverse_lookup[key]]=0
      reindexing_ops[scaler.reverse_lookup[key]]+=1

  from xfel.cxi.cxi_cc import run_cc
  for key in reindexing_ops.keys():
    run_cc(work_params,reindexing_op=key,output=out)

  return result

if (__name__ == "__main__"):
  show_plots = False
  if ("--plots" in sys.argv) :
    sys.argv.remove("--plots")
    show_plots = True
  result = run(args=sys.argv[1:])
  if result is None:
    sys.exit(1)
  if (show_plots) :
    try :
      result.plots.show_all_pyplot()
      from wxtbx.command_line import loggraph
      loggraph.run([result.loggraph_file])
    except Exception, e :
      print "Can't display plots"
      print "You should be able to view them by running this command:"
      print "  wxtbx.loggraph %s" % result.loggraph_file
      raise e
