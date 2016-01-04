import os
import sys
import argparse
import subprocess
import zipapp
import zipfile
import shutil
from pathlib import Path
from .bootstrap import PYTHON_VERSION_MAP
from .venv import ACTIVATE_SCRIPT, PIP_SCRIPT


def create_binary(dst_path, pyrun, zip_file):
    with dst_path.open('wb') as dst_fp, pyrun.open('rb') as pyrun_fp, zip_file.open('rb') as zip_fp:
        shutil.copyfileobj(pyrun_fp, dst_fp)
        shutil.copyfileobj(zip_fp, dst_fp)
    dst_path.chmod(0o0755)


def create_virtualenv(args):
    builddir = Path('build')
    targetdir = builddir / 'target-{}'.format(args.py_version)
    if not targetdir.exists():
        sys.exit('unsupported python version: {}'.format(args.py_version))
    pyrun = (targetdir / 'bin' / 'pyrun{}'.format(args.py_version)).resolve()
    envdir = Path(args.envdir)
    bindir = envdir / 'bin'
    libdir = envdir / 'lib' / 'python{}'.format(args.py_version) / 'site-packages'
    pipdir = envdir / 'pip'
    for d in (bindir, libdir, pipdir):
        d.mkdir(parents=True, exist_ok=True)
    # setup bin dir
    shutil.copy(str(pyrun), str(bindir))
    (bindir / 'python').symlink_to(pyrun.name)
    (bindir / 'python{}'.format(args.py_version[0])).symlink_to(pyrun.name)
    (bindir / 'python{}'.format(args.py_version)).symlink_to(pyrun.name)
    activate_buf = ACTIVATE_SCRIPT.replace('__VENV_PATH__', str(envdir.resolve()))
    activate_buf = activate_buf.replace('__VENV_NAME__', envdir.name)
    activate_buf = activate_buf.replace('__VENV_PYRUN_VERSION__', args.py_version)
    with (bindir / 'activate').open('w') as fp:
        fp.write(activate_buf)
    # setup include dir
    shutil.copytree(str(targetdir / 'include'), str(envdir / 'include'))
    # install setuptools & pip
    zf = zipfile.ZipFile(str(targetdir / 'setuptools.egg'))
    zf.extractall(str(pipdir))
    zf2 = zipfile.ZipFile(str(targetdir / 'pip.egg'))
    zf2.extractall(str(pipdir))
    pip_bin = bindir / 'pip'
    with (pip_bin).open('w') as fp:
        fp.write(PIP_SCRIPT)
    pip_bin.chmod(0o755)


def build(args):
    envdir = os.environ.get('VIRTUAL_ENV')
    if envdir is None:
        sys.exit('virtualenv not activated')
    envdir = Path(envdir)
    py_version = os.environ.get('VIRTUAL_ENV_PYRUN_VERSION')
    if py_version is None:
        sys.exit('current virtualenv is not an exxo virtualenv')
    pyrun = envdir / 'bin' / 'pyrun{}'.format(py_version)
    site_packages = envdir / 'lib' / 'python{}'.format(py_version) / 'site-packages'
    zip_file = envdir / 'app.zip'
    # make sure pip undestands it as a local directory
    source_path = args.source_path.rstrip(os.sep) + os.sep
    subprocess.check_call(['pip', 'install', '-U', source_path])
    # TODO: how not to bundle setuptools and pip?
    zipapp.create_archive(site_packages, zip_file, main=args.main)
    create_binary(Path(args.dest_bin), pyrun, zip_file)


def main():
    py_versions = list(PYTHON_VERSION_MAP.keys())
    parser = argparse.ArgumentParser(description='exxo builder', prog='exxo')
    subparsers = parser.add_subparsers(title='subcommands', description='valid commands', dest='cmd')
    subparsers.required = True
    parser_venv = subparsers.add_parser('venv', help='create virtualenv')
    parser_venv.add_argument('envdir', help='virtualenv directory')
    parser_venv.add_argument('-p', '--py-version', choices=py_versions, default='3.4',
                             help='python version to use (default: 3.4)')
    parser_venv.set_defaults(func=create_virtualenv)
    parser_build = subparsers.add_parser('build', help='build')
    parser_build.add_argument('main', help='main function: package.module:function')
    parser_build.add_argument('dest_bin', help='target binary')
    parser_build.add_argument('-s', '--source-path', default='.', help='path to project source')
    parser_build.set_defaults(func=build)
    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
