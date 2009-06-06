from scitbx.graph.tardy_tree import cluster_manager, find_paths, construct
from scitbx.graph.utils import construct_edge_sets
from libtbx.test_utils import Exception_expected, show_diff
from StringIO import StringIO
import sys

def random_permutation(s):
  from scitbx.array_family import flex
  return flex.select(s, flex.random_permutation(size=len(s)))

def exercise_cluster_manager():
  cm = cluster_manager(n_vertices=0)
  assert cm.cluster_indices == []
  assert cm.clusters == []
  cm = cluster_manager(n_vertices=5)
  for p in xrange(2):
    assert cm.cluster_indices == [0,1,2,3,4]
    assert cm.clusters == [[0],[1],[2],[3],[4]]
    cm.connect_vertices(i=0, j=0, optimize=True)
  for p in xrange(2):
    cm.connect_vertices(i=1, j=3, optimize=True)
    assert cm.cluster_indices == [0,1,2,1,4]
    assert cm.clusters == [[0],[1,3],[2],[],[4]]
  for p in xrange(2):
    cm.connect_vertices(i=0, j=3, optimize=True)
    assert cm.cluster_indices == [1,1,2,1,4]
    for q in xrange(2):
      assert cm.clusters == [[],[1,3,0],[2],[],[4]]
      cm.refresh_indices()
  cm.connect_vertices(i=2, j=4, optimize=True)
  assert cm.clusters == [[],[1,3,0],[2,4],[],[]]
  assert cm.cluster_indices == [1,1,2,1,2]
  cm.connect_vertices(i=2, j=3, optimize=True)
  assert cm.clusters == [[],[1,3,0,2,4],[],[],[]]
  assert cm.cluster_indices == [1,1,1,1,1]
  cm.tidy()
  assert cm.clusters == [[0,1,2,3,4]]
  assert cm.cluster_indices == [0,0,0,0,0]
  #
  cm = cluster_manager(n_vertices=6)
  cm.connect_vertices(i=3, j=0, optimize=True)
  cm.connect_vertices(i=2, j=4, optimize=True)
  cm.connect_vertices(i=1, j=2, optimize=True)
  cm.tidy()
  assert cm.clusters == [[1,2,4],[0,3],[5]]
  assert cm.cluster_indices == [1,0,0,1,0,2]
  edges = [(0,1), (0,2), (3,4), (4,5)]
  cm.connect_vertices(i=4, j=5, optimize=True)
  cm.tidy()
  assert cm.clusters == [[1,2,4,5],[0,3]]
  assert cm.cluster_indices == [1,0,0,1,0,0]
  es = construct_edge_sets(n_vertices=6, edge_list=edges)
  cm.construct_spanning_trees(edge_sets=es)
  assert cm.clusters == [[0,1,2,4,5],[3]]
  assert cm.cluster_indices == [0,0,0,1,0,0]
  assert cm.hinge_edges == [(-1,1), (1,0)]
  assert cm.loop_edges == [(2,0), (4,3)]
  assert cm.roots() == [0]
  assert cm.tree_ids() == [0,0]
  cm.find_loop_edge_bendings(edge_sets=es)
  assert cm.loop_edge_bendings == [(1,2), (3,5)]
  #
  cm.cluster_indices = [1,0,0,1,0,0]
  cm.clusters = [[1,2,4,5],[0,3]]
  cm.hinge_edges = None
  cm.loop_edges = None
  cm.loop_edge_bendings = None
  cm.merge_clusters_with_multiple_connections(edge_sets=es)
  assert cm.clusters == [[0,1,2,3,4,5]]
  assert cm.cluster_indices == [0,0,0,0,0,0]
  #
  sio = StringIO()
  assert cm.show_summary(out=sio, prefix=">") is cm
  assert not show_diff(sio.getvalue(), """\
>number of fixed vertex lists: 0
>number of fixed vertices: 0
>number of clusters: 1
>merge clusters with multiple connections: 2 passes
>number of overlapping rigid clusters: 2
>number of hinge edges: None
>number of loop edges: None
>number of loop edge bendings: None
""")

class test_case_data(object):

  def __init__(O,
        art,
        n_vertices,
        edge_list,
        clusters1,
        hinge_edges1,
        roots1,
        tree_ids1,
        loop_edges1=[],
        loop_edge_bendings1=[]):
    assert art[0] == "\n"
    O.art = art[1:]
    O.n_vertices = n_vertices
    O.edge_list = edge_list
    O.clusters1 = clusters1
    O.hinge_edges1 = hinge_edges1
    O.roots1 = roots1
    O.tree_ids1 = tree_ids1
    O.loop_edges1 = loop_edges1
    O.loop_edge_bendings1 = loop_edge_bendings1

test_cases = [
  test_case_data(
    art=r"""
0
""",
    n_vertices=1,
    edge_list=[],
    clusters1=[[0]],
    hinge_edges1=[(-1,0)],
    roots1=[0],
    tree_ids1=[0]),
  test_case_data(
    art=r"""
0 - 1
""",
    n_vertices=2,
    edge_list=[(0,1)],
    clusters1=[[0], [1]],
    hinge_edges1=[(-1,0)],
    roots1=[0],
    tree_ids1=[0]),
  test_case_data(
    art=r"""
6-membered loop
""",
    n_vertices=6,
    edge_list=[(0,1), (0,5), (1,2), (2,3), (3,4), (4,5)],
    clusters1=[[0, 1, 2, 3, 4, 5]],
    hinge_edges1=[(-1,0)],
    roots1=[0],
    tree_ids1=[0]),
  test_case_data(
    art=r"""
7-membered loop
""",
    n_vertices=7,
    edge_list=[(0,1), (0,6), (1,2), (2,3), (3,4), (4,5), (5,6)],
    clusters1=[[0], [1], [2], [3], [4], [5], [6]],
    hinge_edges1=[(-1,0), (0,1), (1,2), (2,3), (3,4)],
    roots1=[0],
    tree_ids1=[0, 0, 0, 0, 0],
    loop_edges1=[(5,6)],
    loop_edge_bendings1=[(0,5), (4,6)]),
  test_case_data(
    art=r"""
8-membered loop
""",
    n_vertices=8,
    edge_list=[(0,1), (0,7), (1,2), (2,3), (3,4), (4,5), (5,6), (6,7)],
    clusters1=[[0], [1], [2], [3], [4], [5], [6], [7]],
    hinge_edges1=[(-1,0), (0,1), (1,2), (2,3), (3,4), (4,5)],
    roots1=[0],
    tree_ids1=[0, 0, 0, 0, 0, 0],
    loop_edges1=[(6,7)],
    loop_edge_bendings1=[(0,6), (5,7)]),
  test_case_data(
    art=r"""
           7
           |
  5        1
   \     /   \
    4 - 0     2 - 8
   /         /
  6        3
           |
           9
""",
    n_vertices=10,
    edge_list=[
      (0,1), (0,4),
      (1,2), (1,7),
      (2,3), (2,8),
      (3,9),
      (4,5), (4,6)],
    clusters1=[[0], [1], [2], [3], [4], [5], [6], [7], [8], [9]],
    hinge_edges1=[(-1,1), (1,2), (1,0), (0,4), (2,3)],
    roots1=[0],
    tree_ids1=[0] * 5),
  test_case_data(
    art=r"""
           7
           |
  5        1
   \     /   \
    4 - 0     2 - 8
   /         //
  6        3 /
           |/
           9
""",
    n_vertices=10,
    edge_list=[
      (0,1), (0,4),
      (1,2), (1,7),
      (2,3), (2,8), (2,9),
      (3,9),
      (4,5), (4,6)],
    clusters1=[[2,3,9], [0], [1], [4], [5], [6], [7], [8]],
    hinge_edges1=[(-1,2), (2,1), (1,0), (0,4)],
    roots1=[0],
    tree_ids1=[0] * 4),
  test_case_data(
    art=r"""
           7
           |
  5        1
   \     /   \
    4 - 0     2 - 8
   /     \   /
  6        3
           |
           9
""",
    n_vertices=10,
    edge_list=[
      (0,1), (0,3), (0,4),
      (1,2), (1,7),
      (2,3), (2,8),
      (3,9),
      (4,5), (4,6)],
    clusters1=[[0,1,2,3], [4], [5], [6], [7], [8], [9]],
    hinge_edges1=[(-1,0), (0,4)],
    roots1=[0],
    tree_ids1=[0] * 2),
  test_case_data(
    art=r"""
           7
           |
  5        1--\
   \     /   \ \-\
    4 - 0     2 - 8
   /     \   /
  6        3
           |
           9
""",
    n_vertices=10,
    edge_list=[
      (0,1), (0,3), (0,4),
      (1,7), (1,8),
      (2,3), (2,8),
      (3,9),
      (4,5), (4,6)],
    clusters1=[[0, 1, 2, 3, 8], [4], [5], [6], [7], [9]],
    hinge_edges1=[(-1,0), (0,4)],
    roots1=[0],
    tree_ids1=[0] * 2),
  test_case_data(
    art=r"""
           7
           | \
  5        1   \
   \     /       \
    4 - 0     2 - 8
   /     \   /
  6        3
           |
           9
""",
    n_vertices=10,
    edge_list=[
      (0,1), (0,3), (0,4),
      (1,7),
      (2,3), (2,8),
      (3,9),
      (4,5), (4,6),
      (7,8)],
    clusters1=[[0, 1, 2, 3, 7, 8], [4], [5], [6], [9]],
    hinge_edges1=[(-1,0), (0,4)],
    roots1=[0],
    tree_ids1=[0] * 2),
  test_case_data(
    art=r"""
           7
           | \
  5        1   \
   \     /   \   \
    4 - 0     2 - 8
   /     \   /
  6        3
           |
           9
""",
    n_vertices=10,
    edge_list=[
      (0,1), (0,3), (0,4),
      (1,2), (1,7),
      (2,3), (2,8),
      (3,9),
      (4,5), (4,6),
      (7,8)],
    clusters1=[[0, 1, 2, 3, 7, 8], [4], [5], [6], [9]],
    hinge_edges1=[(-1,0), (0,4)],
    roots1=[0],
    tree_ids1=[0] * 2),
  test_case_data(
    art=r"""
           7
           |
  5        1
   \     /   \
    4 - 0     2 - 8
   /     \   /   /
  6        3   /
           | /
           9
""",
    n_vertices=10,
    edge_list=[
      (0,1), (0,3), (0,4),
      (1,2), (1,7),
      (2,3), (2,8),
      (3,9),
      (4,5), (4,6),
      (8,9)],
    clusters1=[[0, 1, 2, 3, 8, 9], [4], [5], [6], [7]],
    hinge_edges1=[(-1,0), (0,4)],
    roots1=[0],
    tree_ids1=[0] * 2),
  test_case_data(
    art=r"""
           7
           | \
  5        1   \
   \     /   \   \
    4 - 0     2 - 8
   /     \   /   /
  6        3   /
           | /
           9
""",
    n_vertices=10,
    edge_list=[
      (0,1), (0,3), (0,4),
      (1,2), (1,7),
      (2,3), (2,8),
      (3,9),
      (4,5), (4,6),
      (7,8),
      (8,9)],
    clusters1=[[0, 1, 2, 3, 7, 8, 9], [4], [5], [6]],
    hinge_edges1=[(-1,0), (0,4)],
    roots1=[0],
    tree_ids1=[0] * 2),
  test_case_data(
    art=r"""
           7
           |
  5        1
  |\     /   \
  | 4 - 0     2 - 8
  |/     \   /
  6        3
           |
           9
""",
    n_vertices=10,
    edge_list=[
      (0,1), (0,3), (0,4),
      (1,2), (1,7),
      (2,3), (2,8),
      (3,9),
      (4,5), (4,6),
      (5,6)],
    clusters1=[[0, 1, 2, 3], [4, 5, 6], [7], [8], [9]],
    hinge_edges1=[(-1,0), (0,4)],
    roots1=[0],
    tree_ids1=[0] * 2),
  test_case_data(
    art=r"""
0   1
""",
    n_vertices=2,
    edge_list=[],
    clusters1=[[0], [1]],
    hinge_edges1=[(-1,0), (-1,1)],
    roots1=[0, 1],
    tree_ids1=[0, 1]),
  test_case_data(
    art=r"""
0 - 2   1
""",
    n_vertices=3,
    edge_list=[(0,2)],
    clusters1=[[0], [1], [2]],
    hinge_edges1=[(-1,0), (-1,1)],
    roots1=[0, 1],
    tree_ids1=[0, 1]),
  test_case_data(
    art=r"""
           7
           | \
  5        1   \
  |\         \   \
  | 4 - 0     2 - 8
  |/         /
  6        3
           |
           9
""",
    n_vertices=10,
    edge_list=[
      (0,4),
      (1,2), (1,7),
      (2,3), (2,8),
      (3,9),
      (4,5), (4,6),
      (5,6),
      (7,8)],
    clusters1=[[1, 2, 7, 8], [4, 5, 6], [0], [3], [9]],
    hinge_edges1=[(-1,1), (2,3), (-1,4)],
    roots1=[0, 2],
    tree_ids1=[0, 0, 1]),
  test_case_data(
    art=r"""
           7
           | \
  5        1   \
             \   \
    4 - 0     2 - 8
   /     \   /
  6 ------ 3
           |
           9
""",
    n_vertices=10,
    edge_list=[
      (0,3), (0,4),
      (1,2), (1,7),
      (2,3), (2,8),
      (3,6), (3,9),
      (4,6),
      (7,8)],
    clusters1=[[0, 3, 4, 6], [1, 2, 7, 8], [5], [9]],
    hinge_edges1=[(-1,0), (3,2), (-1,5)],
    roots1=[0, 2],
    tree_ids1=[0, 0, 1]),
  test_case_data(
    art=r"""
    3 - 6 ----- 4 - 0
   /     \     /     \
  8       1   5       9
    \   /       \   /
      2 --------  7
""",
    n_vertices=10,
    edge_list=[
      (0,4), (0,9),
      (1,2), (1,6),
      (2,7), (2,8),
      (3,6), (3,8),
      (4,5), (4,6),
      (5,7),
      (7,9)],
    clusters1=[[0, 1, 2, 3, 4, 5, 6, 7, 8, 9]],
    hinge_edges1=[(-1,0)],
    roots1=[0],
    tree_ids1=[0]),
  test_case_data(
    art=r"""
  1        5
  |\     / |
  | 0 - 3  |
  |/     \ |
  2        4
""",
    n_vertices=6,
    edge_list=[
      (0,1), (0,2), (0,3),
      (1,2),
      (3,4), (3,5),
      (4,5)],
    clusters1=[[0, 1, 2], [3, 4, 5]],
    hinge_edges1=[(-1, 0), (0, 3)],
    roots1=[0],
    tree_ids1=[0] * 2),

  ]

def exercise_test_cases(out):
  for i_tc,tc in enumerate(test_cases):
    print >> out, "test_case index:", i_tc
    print >> out, tc.art
    tc_c1, tc_he1, tc_r1, tc_tid1, tc_le1, tc_leb1, \
    tc_c2, tc_he2, tc_le2, tc_leb2 = \
      tc.clusters1, tc.hinge_edges1, \
      tc.roots1, tc.tree_ids1, tc.loop_edges1, tc.loop_edge_bendings1, \
      tc.clusters1, tc.hinge_edges1, tc.loop_edges1, tc.loop_edge_bendings1
    def assert_same(label, have, expected):
      print >> out, label, have
      if (expected is not None):
        if (have != expected):
          print >> out, "expected:", expected
        assert have == expected, "Note: --verbose for details"
    #
    tt = construct(n_vertices=tc.n_vertices, edge_list=tc.edge_list)
    assert tt.collinear_bonds_edge_list is None
    cm = tt.cluster_manager
    assert_same("c1:", cm.clusters, tc_c1)
    cm.construct_spanning_trees(edge_sets=tt.edge_sets)
    print >> out, "c1t:", cm.clusters
    assert_same("he1:", cm.hinge_edges, tc_he1)
    assert_same("le1:", cm.loop_edges, tc_le1)
    r = cm.roots()
    assert_same("r1:", r, tc_r1)
    tid = cm.tree_ids()
    assert_same("tid1:", tid, tc_tid1)
    cm.find_loop_edge_bendings(edge_sets=tt.edge_sets)
    assert_same("leb1:", cm.loop_edge_bendings, tc_leb1)
    #
    tt = construct(n_vertices=tc.n_vertices, edge_list=tc.edge_list)
    cm = tt.cluster_manager
    cm.merge_clusters_with_multiple_connections(edge_sets=tt.edge_sets)
    assert_same("c2:", cm.clusters, tc_c2)
    cm.construct_spanning_trees(edge_sets=tt.edge_sets)
    print >> out, "c2t:", cm.clusters
    assert_same("he2:", cm.hinge_edges, tc_he2)
    assert_same("le2:", cm.loop_edges, tc_le2)
    cm.find_loop_edge_bendings(edge_sets=tt.edge_sets)
    assert_same("leb2:", cm.loop_edge_bendings, tc_leb2)
    #
    fp = find_paths(edge_sets=tt.edge_sets)
    for iv in xrange(len(tt.edge_sets)):
      fp.search_from(iv=iv)
    #
    print >> out

def exercise_pdb_test_cases(out):
  from scitbx.graph import tst_tardy_pdb
  for i_tc,tc in enumerate(tst_tardy_pdb.test_cases):
    print >> out, "tst_tardy_pdb index:", i_tc
    tc.tardy_tree_construct()

def exercise_special_case_ZINC03847121():
  # Only case out of 69587 cases with a RIGID_MINUS_TARDY_6 cluster of
  # size different from 3:
  # RIGID_MINUS_TARDY_6: 3 NILE=0 LE=2 NV=13 ZINC03847121
  #   [(0, 10, 11), (3, 10, 12), (9, 10, 11, 12)]
  # ZINC03847121 c1ccc2ccc(=O)ccc(c1)C2
  # simplified (oxygen removed): c1ccc2cccccc(c1)C2
  n_vertices = 12
  edge_list = [
    (0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 8), (8, 9),
    (9, 10), (9, 11), (0, 10), (3, 11)]
  tt = construct(n_vertices=n_vertices, edge_list=edge_list)
  cm = tt.cluster_manager
  cm.sort_by_overlapping_rigid_cluster_sizes(edge_sets=tt.edge_sets)
  assert cm.overlapping_rigid_clusters == [
    (0, 1, 2), (0, 1, 10), (0, 9, 10), (1, 2, 3), (2, 3, 4, 11),
    (3, 4, 5), (3, 9, 11), (4, 5, 6), (5, 6, 7), (6, 7, 8), (7, 8, 9),
    (8, 9, 10, 11)]
  #
  tt = construct(n_vertices=n_vertices, edge_list=edge_list)
  sio = StringIO()
  assert tt.show_summary(vertex_labels=None, out=sio, prefix="$") is tt
  assert not show_diff(sio.getvalue(), """\
$number of vertices: 12
$number of edges: 13
$collinear bonds tolerance: 1 deg
$find cluster loops: None
$number of collinear bonds: None
$number of fixed vertex lists: 0
$number of fixed vertices: 0
$number of clusters: 12
$merge clusters with multiple connections: 0 passes
$number of overlapping rigid clusters: None
$number of hinge edges: None
$number of loop edges: None
$number of loop edge bendings: None
""")
  tt.finalize()
  sio = StringIO()
  assert tt.show_summary(vertex_labels=None, out=sio, prefix=">") is tt
  assert not show_diff(sio.getvalue(), """\
>number of vertices: 12
>number of edges: 13
>collinear bonds tolerance: 1 deg
>find cluster loops: 0 repeats
>number of collinear bonds: None
>number of fixed vertex lists: 0
>number of fixed vertices: 0
>number of clusters: 9
>merge clusters with multiple connections: 1 pass
>number of overlapping rigid clusters: 12
>number of hinge edges: 9
>number of loop edges: 2
>number of loop edge bendings: 5
""")

def exercise_external_clusters(n_trials=10):
  # copy of phenix_regression/tardy_action/gly_gly_box.pdb:
  """
CRYST1   12.661   12.601   14.403  90.00  90.00  90.00 P 1
ATOM      0  C   GLY A 138       5.965   6.290   5.906  1.00 35.93           C
ATOM      1  O   GLY A 138       5.429   5.188   5.784  1.00 40.71           O
ATOM      2  N   GLY A 138       7.860   7.800   5.206  1.00 34.54           N
ATOM      3  CA  GLY A 138       6.857   6.828   4.801  1.00 33.64           C
ATOM      4  N   GLY A 139       5.798   7.062   6.977  1.00 33.49           N
ATOM      5  CA  GLY A 139       4.960   6.636   8.087  1.00 33.25           C
ATOM      6  C   GLY A 139       5.536   5.495   8.904  1.00 32.97           C
ATOM      7  O   GLY A 139       4.801   4.801   9.602  1.00 35.18           O
ATOM      8  OXT GLY A 139       6.772   5.318   8.862  1.00 34.96           O
END
  """
  edge_list = [(0,1), (0,3), (0,4), (2,3), (4,5), (5,6), (6,7), (6,8)]
  expected = [
    (None,
     [[0], [1], [2], [3], [4], [5], [6], [7], [8]],
     0),
    ([[3,0,4,5], [0,1,3,4], [5,6,7,8]], # actual
     [[0,4], [1], [2], [3], [5], [6], [7], [8]],
     1),
    ([[3,0,4,5], [0,1,2,3], [5,6,7,8]], # artificial
     [[0,3,4], [1], [2], [5], [6], [7], [8]],
     2),
    ([[3,0,4,5], [0,1,2,3], [0,4,5,6]], # artificial
     [[0,3,4,5], [1], [2], [6], [7], [8]],
     3),
    ([[3,0,4,5], [0,1,2,3], [0,4,5,6], [4,5,6,8]], # artificial
     [[0,3,4,5,6], [1], [2], [7], [8]],
     4),
    ([[3,0,4,5], [0,1,2,3], [4,5,6,8]], # artificial
     [[0,3,4], [5,6], [1], [2], [7], [8]],
     3),
    ([[0,1,2,3], [4,5,6,8]], # artificial
     [[0,3], [5,6], [1], [2], [4], [7], [8]],
     2)]
  for external_clusters,expected_clusters,expected_count in expected:
    tt = construct(
      n_vertices=9, edge_list=edge_list, external_clusters=external_clusters)
    assert tt.cluster_manager.clusters == expected_clusters
    assert tt.external_clusters_connect_count == expected_count
  for external_clusters,expected_clusters,expected_count in expected:
    if (external_clusters is None): external_clusters = []
    for i_trial in xrange(n_trials):
      tt = construct(
        n_vertices=9,
        edge_list=random_permutation(edge_list),
        external_clusters=[random_permutation(c) for c in external_clusters])
      assert tt.cluster_manager.clusters == expected_clusters
      assert tt.external_clusters_connect_count == expected_count

def exercise_fixed_vertices(n_trials=10):
  cm = cluster_manager(n_vertices=2, fixed_vertex_lists=[[0]])
  assert cm.clusters == [[0], [1]]
  cm = cluster_manager(n_vertices=2, fixed_vertex_lists=[[1]])
  assert cm.clusters == [[1], [0]]
  edge_list = [(0,1),(1,2),(2,3),(1,3)]
  edge_sets = construct_edge_sets(n_vertices=4, edge_list=edge_list)
  for fixed_vertex in [0,1]:
    for optimize in [False, True]:
      for connects in [[(1,2),(2,3)], [(2,3),(1,2)], [(2,1),(3,2)]]:
        cm = cluster_manager(n_vertices=4, fixed_vertex_lists=[[fixed_vertex]])
        for i,j in connects:
          cm.connect_vertices(i=i, j=j, optimize=optimize)
        if (fixed_vertex == 0):
          if (connects[0] == (2,1)):
            if (not optimize):
              assert cm.clusters == [[0], [], [], [3, 2, 1]]
            else:
              assert cm.clusters == [[0], [], [2, 1, 3], []]
          else:
            if (not optimize or connects[0][0] == 1):
              assert cm.clusters == [[0], [1,2,3], [], []]
            else:
              assert cm.clusters == [[0], [], [2,3,1], []]
          cm.tidy()
          assert cm.clusters == [[0], [1,2,3]]
          assert cm.sort_by_overlapping_rigid_cluster_sizes(
            edge_sets=edge_sets) == [2, 4]
          cm.overlapping_rigid_clusters = None
          cm.construct_spanning_trees(edge_sets=edge_sets)
          assert cm.clusters == [[0,1], [2,3]]
          assert cm.hinge_edges == [(-1,0), (0,1)]
          assert cm.loop_edges == []
        else:
          assert cm.clusters == [[1,2,3], [0], [], []]
          cm.tidy()
          assert cm.clusters == [[1,2,3], [0]]
          assert cm.sort_by_overlapping_rigid_cluster_sizes(
            edge_sets=edge_sets) == [4, 2]
          cm.overlapping_rigid_clusters = None
          cm.construct_spanning_trees(edge_sets=edge_sets)
          assert cm.clusters == [[0,1,2,3]]
          assert cm.hinge_edges == [(-1,1)]
          assert cm.loop_edges == []
  #
  from scitbx.graph import tst_tardy_pdb
  tc = tst_tardy_pdb.test_cases[5]
  assert tc.tag == "tyr_with_h"
  tt = tc.tardy_tree_construct(fixed_vertex_lists=[[0,16,17]])
  assert tt.cluster_manager.clusters == [
    [0,1,2,3,4,5,6,7,8,9,10,12,13,14,15,16,17,18,19],
    [11], [20]]
  try:
    tc.tardy_tree_construct(fixed_vertex_lists=[[0],[1]])
  except RuntimeError, e:
    assert str(e) == \
      "connect_clusters(): fixed vertex lists in same connected tree."
  else: raise Exception_expected
  try:
    tc.tardy_tree_construct(fixed_vertex_lists=[[0],[10]])
  except RuntimeError, e:
    assert str(e) == \
      "construct_spanning_trees(): fixed vertex lists in same connected tree."
  else: raise Exception_expected
  #
  for tc in test_cases:
    if (max(tc.tree_ids1) == 0): continue
    tt = construct(n_vertices=tc.n_vertices, edge_list=tc.edge_list).finalize()
    cm = tt.cluster_manager
    cl = cm.clusters
    ti = cm.tree_ids()
    assert ti[0] != ti[-1]
    for lfvl0 in xrange(1,len(cl[0])+1):
      for lfvl1 in xrange(1,len(cl[-1])+1):
        for i_trial in xrange(n_trials):
          fvl0 = random_permutation(cl[0])[:lfvl0]
          fvl1 = random_permutation(cl[-1])[:lfvl1]
          ttf = construct(
            n_vertices=tc.n_vertices,
            edge_list=tc.edge_list,
            fixed_vertex_lists=[fvl0, fvl1]).finalize()

def exercise_show_summary():
  from scitbx.graph import tst_tardy_pdb
  tcs = tst_tardy_pdb.select_test_cases(tags_or_indices=["ZINC03847120"])
  assert len(tcs) == 1
  tt = tcs[0].tardy_tree_construct()
  for vl,cb in [(None, ("10", "12")),
                (list("ABCDEFGHIKLMNO"), ("L", "N"))]:
    sio = StringIO()
    assert tt.show_summary(vertex_labels=vl, out=sio, prefix="&") is tt
    assert not show_diff(sio.getvalue(), """\
&number of vertices: 14
&number of edges: 15
&collinear bonds tolerance: 1 deg
&find cluster loops: 0 repeats
&number of collinear bonds: 1
&tardy collinear bond: %s
&                      %s
&number of fixed vertex lists: 0
&number of fixed vertices: 0
&number of clusters: 1
&merge clusters with multiple connections: 1 pass
&number of overlapping rigid clusters: 2
&number of hinge edges: 1
&number of loop edges: 0
&number of loop edge bendings: 0
""" % cb)

def exercise_edge_classifier():
  from scitbx.graph import tst_tardy_pdb
  tcs = tst_tardy_pdb.select_test_cases(tags_or_indices=["van_fragment"])
  assert len(tcs) == 1
  tt = tcs[0].tardy_tree_construct()
  ec = tt.cluster_manager.edge_classifier()
  edge_classes = {
    "base":  [],
    "hinge": [],
    "intra": [],
    "loop":  []}
  for e in tt.edge_list:
    edge_classes[ec(edge=e)].append(e)
  assert edge_classes == {
    "base": [
      (16,17), (16,23), (17,18), (18,19), (18,20), (20,21), (21,22), (21,23)],
    "hinge": [
      (0,1), (0,8), (3,17), (8,10), (10,11), (11,12), (15,16), (15,24)],
    "intra": [
      (1,2), (1,7), (2,3), (3,4), (4,5), (4,6), (6,7), (8,9), (12,13),
      (14,15), (24,25), (24,26)],
    "loop": [(12, 14)]}
  #
  for f,i,j in [(False,5,29), (True,6,32)]:
    vlcl = tt.viewer_lines_with_colors_legend(include_loop_edge_bendings=f)
    assert len(vlcl) == i
    vlc = tt.viewer_lines_with_colors(include_loop_edge_bendings=f)
    assert len(vlc) == j

def run(args):
  assert args in [[], ["--verbose"]]
  verbose = "--verbose" in args
  if (verbose):
    out = sys.stdout
  else:
    out = StringIO()
  exercise_cluster_manager()
  exercise_test_cases(out=out)
  exercise_pdb_test_cases(out=out)
  exercise_special_case_ZINC03847121()
  exercise_external_clusters()
  exercise_fixed_vertices()
  exercise_show_summary()
  exercise_edge_classifier()
  #
  print "OK"

if (__name__ == "__main__"):
  run(sys.argv[1:])
