# cesm-runner-mcp

MCP server for driving CESM case lifecycle: setup → build → submit → monitor.

Complements the [CrocoDash MCP](https://github.com/CROCODILE-CESM/MCP_CrocoDash), which handles grid creation and forcing. This server picks up where that one leaves off — once a case directory exists, this server drives the CIME build/run pipeline.

## Tools

### Case inspection
| Tool | Purpose |
|------|---------|
| `list_cases(search_root)` | Find all CESM cases under a directory |
| `get_case_status(case_dir)` | Read CaseStatus log + key XML config |
| `check_input_data(case_dir)` | Verify all required input files are staged |

### Case lifecycle
All three accept an optional `container=<session_name>` arg to run inside a crocontainer session instead of on the host.

| Tool | Purpose |
|------|---------|
| `case_setup(case_dir, [container])` | Run `./case.setup` |
| `case_build(case_dir, [container])` | Compile the model (`./case.build`) |
| `case_submit(case_dir, no_batch, [container])` | Submit to PBS/slurm or run interactively |

### XML config
| Tool | Purpose |
|------|---------|
| `xmlquery(case_dir, variable)` | Query any CESM XML variable |
| `xmlchange(case_dir, variable, value)` | Set a CESM XML variable |
| `preview_run(case_dir)` | Show PE layout and batch script without submitting |

### Monitoring
| Tool | Purpose |
|------|---------|
| `tail_log(case_dir, component, lines)` | Read recent run log output |
| `get_job_status(case_dir)` | Check PBS/slurm queue for this case's job |
| `list_compsets(cesmroot, filter)` | List available compsets in a CESM install |

### Container management (crocontainer fast-iteration path)
| Tool | Purpose |
|------|---------|
| `build_sandbox([sandbox_dir])` | One-time: build Apptainer sandbox from registry image (~1hr on Derecho) |
| `start_container(scratch_dir, [sandbox_or_image, inputdata_dir, name, runtime])` | Start a persistent container session |
| `container_exec(name, case_dir, command)` | Run any command inside a running session |
| `stop_container(name)` | Stop and clean up the session |
| `list_containers()` | Show running sessions |

## Resources

| URI | Content |
|-----|---------|
| `cesm://case/{case_dir}/env` | All XML config variables |
| `cesm://case/{case_dir}/status` | CaseStatus log |
| `cesm://case/{case_dir}/logs` | List of run log files |

## Setup

```bash
pip install -e .
# or in the CrocoDash conda env:
conda run -n CrocoDash pip install -e .
```

## Running

```bash
cesm-runner-mcp
# or
python server.py
```

Wire up to Claude Code by adding to `.mcp.json`:

```json
{
  "mcpServers": {
    "cesm-runner": {
      "command": "python",
      "args": ["/path/to/MCP_cesm_runner/server.py"]
    }
  }
}
```

## Fast iteration with crocontainer

Instead of waiting in the PBS queue, run CESM interactively inside a container.
On Derecho, the full GLADE filesystem is mounted transparently so all host paths work inside.

### One-time setup (Derecho)
```bash
# Build the writable sandbox (~1 hr on a compute node)
# Or call build_sandbox() via the MCP
qcmd -l walltime=03:00:00 -- apptainer build --sandbox \
  /glade/derecho/scratch/$USER/crocontainer_sandbox \
  docker://ghcr.io/crocodile-cesm/crocontainer:latest-amd64
```

### Typical MCP session
```
start_container(scratch_dir="~/scratch/croc_scratch")
  → Apptainer instance starts; /glade mounted; inputdata at /glade/campaign/cesm/cesmdata/inputdata

case_setup("~/croc_cases/mycase", container="croc_session")
case_build("~/croc_cases/mycase", container="croc_session")
  → compiles interactively, no queue

xmlchange("~/croc_cases/mycase", "STOP_N", "3")
case_submit("~/croc_cases/mycase", no_batch=True, container="croc_session")
  → runs synchronously; returns output in seconds

# Debugger MCP finds an error → fix → resubmit in the same conversation:
xmlchange("~/croc_cases/mycase", "DT", "900")
case_submit("~/croc_cases/mycase", no_batch=True, container="croc_session")

stop_container("croc_session")
```

### Inputdata on Derecho
CESM inputdata is mounted directly from GLADE — no downloading required:
`/glade/campaign/cesm/cesmdata/inputdata` → `/root/cesm/inputdata` inside container

### On a laptop (Podman)
```
start_container(
  scratch_dir="./scratch",
  sandbox_or_image="ghcr.io/crocodile-cesm/crocontainer:latest",
  inputdata_dir="./cesm_nyf_inputdata",   # pre-downloaded NYF data
  runtime="podman"
)
```

## Design

- **Stateless**: each tool reads from the filesystem; no in-memory state
- **Shells out to CIME scripts**: uses `./xmlquery`, `./case.setup`, etc. directly — version-safe and matches what users run manually
- **Works with any CESM install**: not specific to CrocoDash or MOM6
- **Container-aware**: lifecycle tools accept `container=` to route via `apptainer exec instance://` or `podman exec` instead of running on the host

## CESM install on Derecho

Default reference install: `~/work/installs/cesm3_maddd_new`

Cases live in: `~/croc_cases/`

CESM inputdata: `/glade/campaign/cesm/cesmdata/inputdata`
