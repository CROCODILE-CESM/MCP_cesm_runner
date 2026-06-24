"""
Container management tools for interactive CESM runs via crocontainer.

Supports two runtimes:
  - apptainer  — used on HPC systems (Derecho). Requires a pre-built writable sandbox.
                 On Derecho, /glade is bind-mounted transparently so all host paths
                 work identically inside the container.
  - podman     — used on laptops / local Linux. Uses the ghcr.io registry image directly.

Typical session (Derecho):
    start_container(scratch_dir="~/scratch/croc_scratch", name="croc")
    → container_exec("croc", "~/croc_cases/mycase", "./case.build")
    → container_exec("croc", "~/croc_cases/mycase", "./case.submit --no-batch")
    → stop_container("croc")
"""

import os
import shutil
import subprocess
from pathlib import Path

CONTAINER_IMAGE = "ghcr.io/crocodile-cesm/crocontainer:latest-amd64"
DERECHO_INPUTDATA = "/glade/campaign/cesm/cesmdata/inputdata"
DERECHO_SCRATCH_ROOT = f"/glade/derecho/scratch/{os.environ.get('USER', 'unknown')}"

# Apptainer sandbox default location (built once from the image)
DEFAULT_SANDBOX = Path(DERECHO_SCRATCH_ROOT) / "crocontainer_sandbox"

# Required env vars for OpenMPI inside the container
OMPI_ENV = ["OMPI_CC=gcc", "OMPI_FC=gfortran", "OMPI_CXX=g++"]


def _try_module_load(module: str) -> bool:
    """Try 'module load <module>' via a login shell and update PATH if it succeeds."""
    try:
        # Use --login so /etc/profile.d/ is sourced and the module function is available.
        result = subprocess.run(
            ["bash", "--login", "-c", f"module load {module} && echo $PATH"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            # The last line of stdout is the PATH printed after module load.
            path_line = result.stdout.strip().splitlines()[-1]
            os.environ["PATH"] = path_line
            return True
    except Exception:
        pass
    return False


def _detect_runtime() -> str:
    if shutil.which("apptainer"):
        return "apptainer"
    if shutil.which("podman"):
        return "podman"
    # On Derecho/Casper, apptainer may need to be loaded via the module system
    if _try_module_load("apptainer") and shutil.which("apptainer"):
        return "apptainer"
    return "none"


def _resolve_runtime(runtime: str) -> str:
    if runtime == "auto":
        rt = _detect_runtime()
        if rt == "none":
            raise RuntimeError(
                "Neither apptainer nor podman found on PATH. "
                "On Derecho/Casper run 'module load apptainer' before starting the MCP server, "
                "or on a laptop ensure podman is installed."
            )
        return rt
    return runtime


def build_sandbox(sandbox_dir: str = "", queue_walltime: str = "03:00:00") -> str:
    """
    Build the Apptainer writable sandbox from the crocontainer registry image.

    This is a one-time setup step required on Derecho before start_container can be used.
    Takes ~1 hour on a compute node. Submits via qcmd if queue_walltime is set.

    sandbox_dir: where to create the sandbox (default: ~/scratch/crocontainer_sandbox).
    queue_walltime: PBS walltime for the build job (default 3h).
    """
    sandbox = Path(sandbox_dir).expanduser() if sandbox_dir else DEFAULT_SANDBOX
    if sandbox.exists():
        return f"Sandbox already exists at {sandbox}\nDelete it first if you want to rebuild."

    tmp = Path(DERECHO_SCRATCH_ROOT) / "crocontainer" / "tmp"
    cache = Path(DERECHO_SCRATCH_ROOT) / "crocontainer" / "cache"
    tmp.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["APPTAINER_TMPDIR"] = str(tmp)
    env["APPTAINER_CACHEDIR"] = str(cache)

    build_cmd = [
        "apptainer", "build", "--sandbox", str(sandbox),
        f"docker://{CONTAINER_IMAGE}",
    ]

    if queue_walltime:
        cmd = ["qcmd", "-l", f"walltime={queue_walltime}", "--"] + build_cmd
    else:
        cmd = build_cmd

    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    output = result.stdout + result.stderr
    if result.returncode != 0:
        return f"FAILED (returncode={result.returncode}):\n{output}"
    return f"Sandbox built at {sandbox}\n\n{output.strip()}"


def start_container(
    scratch_dir: str,
    sandbox_or_image: str = "",
    inputdata_dir: str = "",
    name: str = "croc_session",
    runtime: str = "auto",
) -> str:
    """
    Start a persistent container session for interactive CESM runs.

    On Derecho (Apptainer):
      - sandbox_or_image: path to the writable sandbox directory. Defaults to
        ~/scratch/crocontainer_sandbox. Build it first with build_sandbox().
      - inputdata_dir: defaults to /glade/campaign/cesm/cesmdata/inputdata.
      - /glade is bind-mounted transparently so all host paths work inside container.

    On local (Podman):
      - sandbox_or_image: container image name (default: ghcr.io/... crocontainer).
      - inputdata_dir: required — path to pre-downloaded CESM inputdata.

    scratch_dir: host directory for CESM output (bound to /root/cesm/scratch inside).
    name: name for this session (used in container_exec and stop_container).

    Returns the session name on success.
    """
    rt = _resolve_runtime(runtime)
    scratch = Path(scratch_dir).expanduser()
    scratch.mkdir(parents=True, exist_ok=True)

    if rt == "apptainer":
        sandbox = Path(sandbox_or_image).expanduser() if sandbox_or_image else DEFAULT_SANDBOX
        if not sandbox.exists():
            return (
                f"ERROR: Apptainer sandbox not found at {sandbox}\n"
                "Build it first with build_sandbox(), then retry."
            )
        inputdata = inputdata_dir or DERECHO_INPUTDATA

        cmd = [
            "apptainer", "instance", "start",
            "--writable",
        ]
        for e in OMPI_ENV:
            cmd += ["--env", e]
        # Transparent GLADE mount so all host paths work inside container
        cmd += ["--bind", "/glade:/glade"]
        # CESM inputdata at the path it expects
        cmd += ["--bind", f"{inputdata}:/root/cesm/inputdata"]
        # Scratch output
        cmd += ["--bind", f"{scratch}:/root/cesm/scratch"]
        cmd += [str(sandbox), name]

    elif rt == "podman":
        image = sandbox_or_image or CONTAINER_IMAGE
        if not inputdata_dir:
            return "ERROR: inputdata_dir is required for Podman (no default on non-Derecho systems)"
        inputdata = inputdata_dir

        cmd = [
            "podman", "run", "-d",
            "--name", name,
            "-v", f"{inputdata}:/root/cesm/inputdata",
            "-v", f"{scratch}:/root/cesm/scratch",
            image,
            "sleep", "infinity",
        ]
    else:
        return f"ERROR: unknown runtime '{rt}'"

    result = subprocess.run(cmd, capture_output=True, text=True)
    output = result.stdout.strip() + ("\n" + result.stderr.strip() if result.stderr.strip() else "")
    if result.returncode != 0:
        return f"FAILED starting container (returncode={result.returncode}):\n{output}"
    return f"Container session '{name}' started ({rt}).\nUse container_exec('{name}', case_dir, command) to run commands inside."


def container_exec(name: str, case_dir: str, command: str, runtime: str = "auto") -> str:
    """
    Run a CIME command inside a running container session.

    name: session name from start_container.
    case_dir: absolute path to the CESM case directory on the host.
              On Derecho this path is identical inside the container (/glade is mounted).
              On Podman, this dir is passed as -v and mounted at the same path.
    command: shell command to run (e.g. './case.build', './case.submit --no-batch').

    Returns the full stdout+stderr from the command.
    """
    rt = _resolve_runtime(runtime)
    case = Path(case_dir).expanduser()
    shell_cmd = f"cd {case} && {command}"

    if rt == "apptainer":
        # Unset NCAR_HOST so CESM machine detection works correctly inside the container
        # (NCAR_HOST=casper on the host would cause a machine mismatch for derecho cases).
        cmd = ["apptainer", "exec", "--env", "NCAR_HOST=", f"instance://{name}", "bash", "-c", shell_cmd]
    elif rt == "podman":
        # For podman: bind the case dir at start time isn't possible after launch,
        # so we use podman exec (case dir must have been mounted at start, or is on a
        # shared filesystem the container can see).
        cmd = ["podman", "exec", name, "bash", "-c", shell_cmd]
    else:
        return f"ERROR: unknown runtime '{rt}'"

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=7200)
    output = result.stdout + ("\n" + result.stderr if result.stderr.strip() else "")
    if result.returncode != 0:
        output = f"FAILED (returncode={result.returncode}):\n" + output
    return output.strip()


def stop_container(name: str, runtime: str = "auto") -> str:
    """
    Stop and clean up a container session started with start_container.

    name: session name passed to start_container.
    """
    rt = _resolve_runtime(runtime)

    if rt == "apptainer":
        cmd = ["apptainer", "instance", "stop", name]
    elif rt == "podman":
        stop = subprocess.run(["podman", "stop", name], capture_output=True, text=True)
        rm = subprocess.run(["podman", "rm", name], capture_output=True, text=True)
        if stop.returncode != 0:
            return f"FAILED stopping podman container:\n{stop.stderr}"
        return f"Container '{name}' stopped and removed."
    else:
        return f"ERROR: unknown runtime '{rt}'"

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return f"FAILED (returncode={result.returncode}):\n{result.stderr}"
    return f"Container session '{name}' stopped."


def run_case_in_container(
    container: str,
    bundle_dir: str,
    runtime: str = "auto",
    timeout: int = 7200,
) -> str:
    """
    Deploy a CrocoDash bundle to a running container and run it end-to-end.

    This is the fast-iteration path for running a regional MOM6 case without
    touching the HPC batch queue. It combines three steps into one call:
      1. Copy the bundle into /workspace/bundle/ inside the container
      2. Run /workspace/run_case.sh (case setup → build → submit --no-batch)
      3. Return the full output for inspection

    On Derecho (Apptainer): /glade is bind-mounted so the copy is just a shell
    cp from the mounted path. On laptop (Podman): uses `podman cp` to push the
    bundle into the container before running.

    Prerequisites:
      - start_container must already be running (use start_container first)
      - bundle_case (CrocoDash MCP) must have been run to create the bundle
      - For Derecho, the Apptainer sandbox must exist (build_sandbox)

    Parameters
    ----------
    container : str
        Session name from start_container.
    bundle_dir : str
        Host path to the bundle folder created by bundle_case.
        On Derecho this can be any /glade path — it's visible inside the container.
    runtime : str
        "auto" (default), "apptainer", or "podman".
    timeout : int
        Seconds to wait for the full case run (default 7200 = 2h).

    Returns
    -------
    The full stdout+stderr from run_case.sh. Check for "SUCCESSFUL" near the end.
    """
    rt = _resolve_runtime(runtime)
    bundle_path = Path(bundle_dir).expanduser().resolve()

    if not bundle_path.exists():
        return f"ERROR: bundle_dir does not exist: {bundle_path}"

    if rt == "apptainer":
        # /glade is mounted transparently — copy bundle to /workspace/bundle/ via shell
        copy_cmd = f"rm -rf /workspace/bundle && cp -r {bundle_path} /workspace/bundle"
        copy_result = subprocess.run(
            ["apptainer", "exec", "--env", "NCAR_HOST=", f"instance://{container}",
             "bash", "-c", copy_cmd],
            capture_output=True, text=True, timeout=120,
        )
        if copy_result.returncode != 0:
            return f"FAILED copying bundle into container:\n{copy_result.stderr}"

    elif rt == "podman":
        # podman cp pushes the bundle directory into the container
        rm_result = subprocess.run(
            ["podman", "exec", container, "bash", "-c", "rm -rf /workspace/bundle"],
            capture_output=True, text=True,
        )
        cp_result = subprocess.run(
            ["podman", "cp", str(bundle_path), f"{container}:/workspace/bundle"],
            capture_output=True, text=True,
        )
        if cp_result.returncode != 0:
            return f"FAILED copying bundle into podman container:\n{cp_result.stderr}"
    else:
        return f"ERROR: unknown runtime '{rt}'"

    # Run the full case pipeline inside the container
    return container_exec(container, "/workspace", "/bin/bash /workspace/run_case.sh", runtime=runtime)


def list_containers(runtime: str = "auto") -> str:
    """
    List running crocontainer sessions.

    Shows active Apptainer instances or Podman containers by name.
    """
    rt = _resolve_runtime(runtime)

    if rt == "apptainer":
        result = subprocess.run(
            ["apptainer", "instance", "list"],
            capture_output=True, text=True,
        )
    elif rt == "podman":
        result = subprocess.run(
            ["podman", "ps", "--filter", "name=croc", "--format",
             "table {{.Names}}\t{{.Status}}\t{{.Image}}"],
            capture_output=True, text=True,
        )
    else:
        return f"ERROR: unknown runtime '{rt}'"

    return result.stdout.strip() or "No running container sessions found."
