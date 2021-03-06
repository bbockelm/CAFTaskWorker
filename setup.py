import sys, os, os.path, re, shutil, string
from distutils.core import setup, Command
from distutils.command.build import build
from distutils.command.install import install
from distutils.spawn import spawn
from glob import glob


systems = \
{
  'CAFTaskWorker':
  {
    'python': ['TaskWorker']
  }
}

def get_relative_path():
  return os.path.dirname(os.path.abspath(os.path.join(os.getcwd(), sys.argv[0])))

def define_the_build(self, dist, system_name, patch_x = ''):
  # Expand various sources.
  docroot = "doc/build/html"
  system = systems[system_name]
  #binsrc = sum((glob("bin/%s" % x) for x in system['bin']), [])

  py_version = (string.split(sys.version))[0]
  pylibdir = '%slib/python%s/site-packages' % (patch_x, py_version[0:3])
  dist.packages = find_packages('src/python')
  dist.data_files = []
  if os.path.exists(docroot):
    for dirpath, dirs, files in os.walk(docroot):
      dist.data_files.append(("%sdoc%s" % (patch_x, dirpath[len(docroot):]),
                              ["%s/%s" % (dirpath, fname) for fname in files
                               if fname != '.buildinfo']))

def dirwalk(relativedir):
    """
    Walk a directory tree and look-up for __init__.py files.
    If found yield those dirs. Code based on
    http://code.activestate.com/recipes/105873-walk-a-directory-tree-using-a-generator/
    """
    idir = os.path.join(os.getcwd(), relativedir)
    for fname in os.listdir(idir):
        fullpath = os.path.join(idir, fname)
        if  os.path.isdir(fullpath) and not os.path.islink(fullpath):
            for subdir in dirwalk(fullpath):  # recurse into subdir
                yield subdir
        else:
            initdir, initfile = os.path.split(fullpath)
            if  initfile == '__init__.py':
                yield initdir

def find_packages(relativedir):
    "Find list of packages in a given dir"
    packages = []
    for idir in dirwalk(relativedir):
        package = idir.replace(os.getcwd() + '/', '')
        package = package.replace(relativedir + '/', '')
        package = package.replace('/', '.')
        packages.append(package)
    return packages

class BuildCommand(Command):
  """Build python modules for a specific system."""
  description = \
    "Build python modules for the specified system. The two supported systems\n" + \
    "\t\t   at the moment is 'CAFTaskWorker'.  Use with --force \n" + \
    "\t\t   to ensure a clean build of only the requested parts.\n"
  user_options = build.user_options
  user_options.append(('system=', 's', 'build the specified system (default: TaskWorker)'))
  user_options.append(('skip-docs=', 'd' , 'skip documentation'))

  def initialize_options(self):
    self.system = "TaskWorker"
    self.skip_docs = False

  def finalize_options(self):
    if self.system not in systems:
      print "System %s unrecognised, please use '-s TaskWorker'" % self.system
      sys.exit(1)

    # Expand various sources and maybe do the c++ build.
    define_the_build(self, self.distribution, self.system, '')

    # Force rebuild.
    shutil.rmtree("%s/build" % get_relative_path(), True)
    shutil.rmtree("doc/build", True)

  def generate_docs(self):
    if not self.skip_docs:
     # os.environ["PYTHONPATH"] = "%s/../WMCore/src/python/:%s" % (os.getcwd(), os.environ["PYTHONPATH"])
      os.environ["PYTHONPATH"] = "%s/build/lib:%s" % (os.getcwd(), os.environ["PYTHONPATH"])
      spawn(['make', '-C', 'doc', 'html', 'PROJECT=%s' % 'taskworker' ])

  def run(self):
    command = 'build'
    if self.distribution.have_run.get(command): return
    cmd = self.distribution.get_command_obj(command)
    cmd.force = self.force
    cmd.ensure_finalized()
    cmd.run()
    self.generate_docs()
    self.distribution.have_run[command] = 1

class InstallCommand(install):
  """Install a specific system."""
  description = \
    "Install a specific system. You can patch an existing\n" + \
    "\t\t   installation instead of normal full installation using the '-p' option.\n"
  user_options = install.user_options
  user_options.append(('system=', 's', 'install the specified system (default: TaskWorker)'))
  user_options.append(('patch', None, 'patch an existing installation (default: no patch)'))
  user_options.append(('skip-docs=', 'd' , 'skip documentation'))

  def initialize_options(self):
    install.initialize_options(self)
    self.system = "TaskWorker"
    self.patch = None
    self.skip_docs = False

  def finalize_options(self):
    # Check options.
    if self.system not in systems:
      print "System %s unrecognised, please use '-s TaskWorker'" % self.system
      sys.exit(1)
    if self.patch and not os.path.isdir("%s/xbin" % self.prefix):
      print "Patch destination %s does not look like a valid location." % self.prefix
      sys.exit(1)

    # Expand various sources, but don't build anything from c++ now.
    define_the_build(self, self.distribution, self.system, (self.patch and 'x') or '')

    # Whack the metadata name.
    self.distribution.metadata.name = self.system
    assert self.distribution.get_name() == self.system

    # Pass to base class.
    install.finalize_options(self)

    # Mangle paths if we are patching. Most of the mangling occurs
    # already in define_the_build(), but we need to fix up others.
    if self.patch:
      self.install_lib = re.sub(r'(.*)/lib/python(.*)', r'\1/xlib/python\2', self.install_lib)
      self.install_scripts = re.sub(r'(.*)/bin$', r'\1/xbin', self.install_scripts)

  def run(self):
    for cmd_name in self.get_sub_commands():
      cmd = self.distribution.get_command_obj(cmd_name)
      cmd.distribution = self.distribution
      if cmd_name == 'install_data':
        cmd.install_dir = self.prefix
      else:
        cmd.install_dir = self.install_lib
      cmd.ensure_finalized()
      self.run_command(cmd_name)
      self.distribution.have_run[cmd_name] = 1

setup(name = 'TaskWorker',
      version = '0.0.1',
      maintainer_email = 'hn-cms-crabdevelopment@cern.ch',
      cmdclass = { 'build_system': BuildCommand,
                   'install_system': InstallCommand },
      # base directory for all the packages
      package_dir = { '' : 'src/python' })
