"""Distutils based setup script for Biopython.

This uses Distutils (http://python.org/sigs/distutils-sig/) the standard
python mechanism for installing packages. For the easiest installation
just type the command:

python setup.py install

For more in-depth instructions, see the installation section of the
biopython manual, linked to from:

http://www.biopython.org/documentation/

Or for more details about the options available from distutils, look at
the 'Installing Python Modules' distutils documentation, available from:

http://python.org/sigs/distutils-sig/doc/

Or, if all else fails, feel free to write to the biopython list at
biopython@biopython.org and ask for help.
"""
import sys
import os

# Make sure I have the right Python version.
if sys.version_info[:2] < (2, 2):
    print "Biopython requires Python 2.2 or better.  Python %d.%d detected" % \
          sys.version_info[:2]
    sys.exit(-1)

from distutils.core import setup
from distutils.core import Command
from distutils.command.install import install
from distutils.command.install_data import install_data
from distutils.command.build_py import build_py
from distutils.command.build_ext import build_ext
from distutils.extension import Extension

def get_yes_or_no(question, default):
    if default:
        option_str = "(Y/n)"
        default_str = 'y'
    else:
        option_str = "(y/N)"
        default_str = 'n'

    while 1:
        print "%s %s " % (question, option_str),
        response = raw_input().lower()
        if not response:
            response = default_str
        if response[0] in ['y', 'n']:
            break
        print "Please answer y or n."
    return response[0] == 'y'

_CHECKED = None
def check_dependencies_once():
    # Call check_dependencies, but cache the result for subsequent
    # calls.
    global _CHECKED
    if _CHECKED is None:
        _CHECKED = check_dependencies()
    return _CHECKED

def check_dependencies():
    """Return whether the installation should continue."""
    # There should be some way for the user to tell specify not to
    # check dependencies.  For example, it probably should not if
    # the user specified "-q".  However, I'm not sure where
    # distutils stores that information.  Also, install has a
    # --force option that gets saved in self.user_options.  It
    # means overwrite previous installations.  If the user has
    # forced an installation, should we also ignore dependencies?
    dependencies = [
        ("mxTextTools", is_mxTextTools_installed, 1,
         "http://www.egenix.com/files/python/eGenix-mx-Extensions.html"),
        ("Numerical Python", is_Numpy_installed, 0,
         "http://numpy.sourceforge.net/"),
        ("Reportlab", is_reportlab_installed, 0,
         "http://www.reportlab.org/downloads.html"),
        ]

    for name, is_installed_fn, is_required, url in dependencies:
        if is_installed_fn():
            continue

        print "*** %s *** is either not installed or out of date." % name
        if is_required:

            print """
This package is required for many Biopython features.  Please install
it before you install Biopython."""
            default = 0
        else:
            print """
This package is optional, which means it is only used in a few
specialized modules in Biopython.  You probably don't need this if you
are unsure.  You can ignore this requirement, and install it later if
you see ImportErrors."""
            default = 1
        print "You can find %s at %s." % (name, url)
        print
        # exit automatically if required packages not installed
        if not(default):
            sys.exit(-1)

        if not get_yes_or_no(
            "Do you want to continue this installation?", default):
            return 0
    return 1

class install_biopython(install):
    """Override the standard install to check for dependencies.

    This will just run the normal install, and then print warning messages
    if packages are missing.

    """
    def run(self):
        if check_dependencies_once():
            # Run the normal install.
            install.run(self)

class build_py_biopython(build_py):
    def run(self):
        if not check_dependencies_once():
            return
        # Check to see if Martel is installed.  If not, then install
        # it automatically.
        if not is_Martel_installed():
            self.packages.append("Martel")
        # Only install the clustering software if Numpy is installed.
        if is_Numpy_installed():
            self.packages.append("Bio.Cluster")
        build_py.run(self)

class build_ext_biopython(build_ext):
    def run(self):
        if not check_dependencies_once():
            return
        # Only install the clustering software if Numpy is installed.
        # Otherwise, it will not compile.
        if is_Numpy_installed():
            self.extensions.append(
                Extension('Bio.Cluster.cluster',
                          ['Bio/Cluster/clustermodule.c',
                           'Bio/Cluster/cluster.c',
                           'Bio/Cluster/ranlib.c',
                           'Bio/Cluster/com.c',
                           'Bio/Cluster/linpack.c'],
                          include_dirs=["Bio/Cluster"]
                          )
                )
        build_ext.run(self)

class test_biopython(Command):
    """Run all of the tests for the package.

    This is a automatic test run class to make distutils kind of act like
    perl. With this you can do:

    python setup.py build
    python setup.py install
    python setup.py test
    
    """
    description = "Automatically run the test suite for Biopython."
    user_options = []  # distutils complains if this is not here.
    def initialize_options(self):  # distutils wants this
        pass
    def finalize_options(self):    # this too
        pass
    def run(self):
        this_dir = os.getcwd()

        # change to the test dir and run the tests
        os.chdir("Tests")
        sys.path.insert(0, '')
        import run_tests
        run_tests.main([])

        # change back to the current directory
        os.chdir(this_dir)

def can_import(module_name):
    """can_import(module_name) -> module or None"""
    try:
        return __import__(module_name)
    except ImportError:
        return None
    raise AssertionError, "how did I get here?"

def is_Martel_installed():
    old_path = sys.path[:]

    # First, check the version of the Martel that's bundled with
    # Biopython.
    sys.path.insert(0, '')   # Make sure I'm importing the current one.
    m = can_import("Martel")
    sys.path = old_path
    if m:
        bundled_martel_version = m.__version__
    else:
        bundled_martel_version = None
    del sys.modules["Martel"]   # Delete the old version of Martel.

    # Now try and import a Martel that's not bundled with Biopython.
    # To do that, I need to delete all the references to the current
    # path from sys.path.
    i = 0
    while i < len(sys.path):
        if sys.path[i] in ['', '.', os.getcwd()]:
            del sys.path[i]
        else:
            i += 1
    m = can_import("Martel")
    sys.path = old_path
    if m:
        old_martel_version = m.__version__
    else:
        old_martel_version = None

    installed = 0
    # If the bundled one is the older, then ignore it
    if old_martel_version and bundled_martel_version and \
           bundled_martel_version < old_martel_version:
        installed = 1
    return installed

def is_mxTextTools_installed():
    if can_import("TextTools"):
        return 1
    return can_import("mx.TextTools")

def is_Numpy_installed():
    return can_import("Numeric")

def is_reportlab_installed():
    return can_import("reportlab")
                  
# --- set up the packages we are going to install
# standard biopython packages
PACKAGES = [
    'Bio',
    'Bio.Ais',
    'Bio.Align',
    'Bio.AlignAce',
    'Bio.Alphabet',
    'Bio.Application',
    'Bio.Blast',
    'Bio.builders',
    'Bio.builders.Search',
    'Bio.builders.SeqRecord',
    'Bio.CDD',
    'Bio.Clustalw',
    'Bio.config',
    'Bio.Crystal',
    'Bio.Data',
    'Bio.dbdefs',
    'Bio.ECell',
    'Bio.Emboss',
    'Bio.Encodings',
    'Bio.Enzyme',
    'Bio.expressions',
    'Bio.expressions.blast',
    'Bio.expressions.embl',
    'Bio.expressions.swissprot',
    'Bio.EUtils',
    'Bio.EUtils.DTDs',
    'Bio.Fasta',
    'Bio.formatdefs',
    'Bio.FSSP',
    'Bio.GA',
    'Bio.GA.Crossover',
    'Bio.GA.Mutation',
    'Bio.GA.Repair',
    'Bio.GA.Selection',
    'Bio.GenBank',
    'Bio.Geo',
    'Bio.GFF',
    'Bio.Gobase',
    'Bio.Graphics',
    'Bio.HMM',
    'Bio.IntelliGenetics',
    'Bio.InterPro',
    'Bio.Kabat',
    'Bio.KDTree',
    'Bio.KEGG',
    'Bio.KEGG.Compound',
    'Bio.KEGG.Enzyme',
    'Bio.KEGG.Map',
    'Bio.LocusLink',
    'Bio.Medline',
    'Bio.MetaTool',
    'Bio.Mindy',
    'Bio.MultiProc',
    'Bio.NBRF',
    'Bio.Ndb',
    'Bio.NeuralNetwork',
    'Bio.NeuralNetwork.BackPropagation',
    'Bio.NeuralNetwork.Gene',
    'Bio.NMR',
    'Bio.Parsers',
    'Bio.Pathway',
    'Bio.Pathway.Rep',
    'Bio.PDB',
    'Bio.PDB.mmCIF',
    'Bio.Prosite',
    'Bio.Rebase',
    'Bio.Saf',
    'Bio.SCOP',
    'Bio.SCOP.tests',
    'Bio.SeqIO',
    'Bio.SeqUtils',
    'Bio.Sequencing',
    'Bio.SubsMat',
    'Bio.SVDSuperimposer',
    'Bio.SwissProt',
    'Bio.UniGene',
    'Bio.writers',
    'Bio.writers.SeqRecord',
    'Bio.Wise',
    'Bio.WWW',
    ]

EXTENSIONS = [
    Extension('Bio.cSVM',
              ['Bio/cSVMmodule.c',
               'Bio/csupport.c'],
              include_dirs=["Bio"]
              ),
    Extension('Bio.ckMeans',
              ['Bio/ckMeansmodule.c',
               'Bio/csupport.c'],
              include_dirs=["Bio"]
              ),
    Extension('Bio.clistfns',
              ['Bio/clistfnsmodule.c']
              ),
    Extension('Bio.cmathfns',
              ['Bio/cmathfnsmodule.c',
               'Bio/csupport.c'],
              include_dirs=["Bio"]
              ),
    Extension('Bio.cstringfns',
              ['Bio/cstringfnsmodule.c']
              ),
    Extension('Bio.cdistance',
              ['Bio/cdistancemodule.c',
               'Bio/csupport.c'],
              include_dirs=["Bio"]
              ),
    Extension('Bio.cpairwise2',
              ['Bio/cpairwise2module.c',
               'Bio/csupport.c'],
              include_dirs=["Bio"]
              ),
    Extension('Bio.trie',
              ['Bio/triemodule.c',
               'Bio/trie.c'],
              include_dirs=["Bio"]
              ),
    Extension('Bio.cMarkovModel',
              ['Bio/cMarkovModelmodule.c',
               'Bio/csupport.c'],
              include_dirs=["Bio"]
              ),
    Extension('Bio.PDB.mmCIF.MMCIFlex',
              ['Bio/PDB/mmCIF/lex.yy.c',
               'Bio/PDB/mmCIF/MMCIFlexmodule.c'],
              include_dirs=["Bio"],
              libraries=["fl"]
              ),
    #Extension('Bio.KDTree._CKDTree',
    #          ["Bio/KDTree/KDTree.C",
    #           "Bio/KDTree/KDTree.swig.C"],
    #          libraries=["stdc++"]
    #          ),
    ]

DATA_FILES=[
    "Bio/EUtils/DTDs/*.dtd",
    ]

# EUtils contains dtd files that need to be installed in the same
# directory as the python modules.  Distutils doesn't have a simple
# way of handling this, and we need to subclass install_data.  This
# code is adapted from the mx.TextTools distribution.

class install_data_biopython(install_data):
    def finalize_options(self):
        if self.install_dir is None:
            installobj = self.distribution.get_command_obj('install')
            self.install_dir = installobj.install_platlib
        install_data.finalize_options(self)

    def run (self):
        import glob
        if not self.dry_run:
            self.mkpath(self.install_dir)
        data_files = self.get_inputs()
        for entry in data_files:
            if type(entry) is not type(""):
                raise ValueError, "data_files must be strings"
            # Unix- to platform-convention conversion
            entry = os.sep.join(entry.split("/"))
            filenames = glob.glob(entry)
            for filename in filenames:
                dst = os.path.join(self.install_dir, filename)
                dstdir = os.path.split(dst)[0]
                if not self.dry_run:
                    self.mkpath(dstdir)
                    outfile = self.copy_file(filename, dst)[0]
                else:
                    outfile = dst
                self.outfiles.append(outfile)


# Install BioSQL.
PACKAGES.append("BioSQL")

setup(
    name='biopython',
    version='1.24',
    author='The Biopython Consortium',
    author_email='biopython@biopython.org',
    url='http://www.biopython.org/',
    cmdclass={
        "install" : install_biopython,
        "build_py" : build_py_biopython,
        "build_ext" : build_ext_biopython,
        "install_data" : install_data_biopython,
        "test" : test_biopython,
        },
    packages=PACKAGES,
    ext_modules=EXTENSIONS,
    data_files=DATA_FILES,
    )
