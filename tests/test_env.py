import subprocess
import sys
from pathlib import Path

import pytest
from packaging.version import Version

from pyprojectx.env import IsolatedVirtualEnv
from pyprojectx.log import set_verbosity


def test_isolated_env_path(tmp_dir):
    env = IsolatedVirtualEnv(
        tmp_dir,
        "env-name",
        [
            "requirement1",
            "requirement2",
        ],
    )
    assert (
        str(env.path)
        == f"{tmp_dir}/env-name-57b6e92d262b77ef47fda82ab9b9c617-py{sys.version_info.major}.{sys.version_info.minor}"
    )


def test_isolated_env_install(tmp_dir):
    env = IsolatedVirtualEnv(tmp_dir, "env-name", [])
    assert not env.is_installed

    env.install()
    assert env.scripts_path.exists()
    assert env.is_installed


def test_isolated_env_remove(tmp_dir):
    env = IsolatedVirtualEnv(tmp_dir, "env-name", [])
    env.install()
    assert env.path.exists()
    env.remove()
    assert not env.path.exists()


def test_isolation(tmp_dir):
    subprocess.check_call([sys.executable, "-c", "import pyprojectx.env"])
    env = IsolatedVirtualEnv(tmp_dir, "env-name", [])
    env.install()
    with pytest.raises(subprocess.CalledProcessError):
        debug = "import sys; import os; print(os.linesep.join(sys.path));"
        subprocess.check_call([env.executable, "-c", f"{debug} import pyprojectx.env"])


def test_isolated_env_install_arguments(mocker, tmp_dir):
    mocker.patch("subprocess.run")
    env = IsolatedVirtualEnv(
        tmp_dir,
        "env-name",
        ["some", "requirements"],
    )
    env.install()

    subprocess.run.assert_called()
    args = subprocess.run.call_args[0][0][:-1]
    assert args == [
        env.executable,
        "-Im",
        "pip",
        "install",
        "--use-pep517",
        "--no-warn-script-location",
        "-r",
    ]


def test_default_pip_is_never_too_old(tmp_dir):
    env = IsolatedVirtualEnv(tmp_dir, "env-name", [])
    env.install()
    version = subprocess.check_output(
        [env.executable, "-c", "import pip; print(pip.__version__)"], universal_newlines=True
    ).strip()
    assert Version(version) >= Version("19.1")


def test_run(tmp_dir, capfd):
    env = IsolatedVirtualEnv(
        tmp_dir,
        "env-name",
        [
            "virtualenv==20.10.0",
        ],
    )
    env.install()
    captured = capfd.readouterr()
    assert captured.err.startswith("Collecting virtualenv")

    env.run("virtualenv --version")
    captured = capfd.readouterr()
    assert captured.out.startswith("virtualenv")

    env.run(["virtualenv", "--version"])
    captured = capfd.readouterr()
    assert captured.out.startswith("virtualenv")

    env.run(["echo", "string", "with", "spaces"])
    captured = capfd.readouterr()
    assert captured.out == "string with spaces\n"

    env.run("echo string with spaces")
    captured = capfd.readouterr()
    assert captured.out == "string with spaces\n"

    set_verbosity(1)
    path = "%PATH%" if sys.platform == "win32" else "$PATH"
    env.run(f"echo {path}")
    captured = capfd.readouterr()
    assert str(env.scripts_path) in captured.out
