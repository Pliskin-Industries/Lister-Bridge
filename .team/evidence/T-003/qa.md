# T-003 Independent QA Evidence

## Verdict

**PASS.** This final packet supersedes both earlier T-003 QA packets. All four acceptance criteria passed on `tier3-v2-roadmap`; the artifact evidence is tied only to the single controlled build completed at `2026-07-15T03:57:54.2563895Z`.

| Acceptance criterion | Verdict | Decisive evidence |
| --- | --- | --- |
| AC1 - locked dependencies | PASS | 85 locked packages matched 85 installed packages with zero delta; constrained installs and final dependency health checks exited 0. |
| AC2 - protected verification | PASS | Final canonical verification exited 0 after collecting and passing 166 tests. |
| AC3 - Windows package path | PASS | One controlled build passed its exit guard; the stable nonempty artifact has a matching 64-character SHA-256 sidecar. |
| AC4 - cache hygiene | PASS | Repository status and tracked-file checks found zero supported cache or build paths. |

## Incident Disclosure

The preceding QA cycle started two packaging commands. A delayed build replaced the artifact after it had been inspected, invalidating that cycle's recorded size and digest. Neither earlier packet is valid evidence for the current artifact.

The final cycle began only after the primary confirmed zero active Python or PyInstaller processes. This QA agent then started exactly one packaging command through hidden, waited `Start-Process`; no direct or second packaging invocation was used.

## Reproduction Evidence

### AC1 - Complete Locked Graph

The constrained installation run completed in workflow order before the final cycle. The final cycle then rechecked dependency health and the complete installed graph without changing packages.

```powershell
python -m pip install pip -c constraints-py312.txt
python -m pip install -r requirements.txt -r requirements-build.txt -c constraints-py312.txt
python -m pip check
python -m pip freeze --all
```

| Check | Result |
| --- | --- |
| Interpreter | Python 3.12.10 |
| Constrained pip install | Exit 0; pip 25.0.1 |
| Constrained requirement install | Exit 0 |
| Final `pip check` | Exit 0; no broken requirements |
| Final graph comparison | 85 locked; 85 installed; 0 missing, extra, or mismatched |

Package names were canonicalized across hyphens, underscores, dots, and case before comparison.

### AC2 - Canonical Verification

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/verify.ps1
```

- Exit code: 0.
- Interpreter: `.venv-py312\Scripts\python.exe`, Python 3.12.10.
- Collection: 166 tests in 0.33 seconds.
- Execution: 166 passed.
- Dependency precheck: `pip check` passed.

### AC3 - Workflow Contract

Static review of `.github/workflows/windows-ci.yml` passed 15 of 15 checks. The reviewed contract covers the triggers, read-only permission, Python version, constrained installation order, canonical verification, packaging, zero-byte rejection, hashing, missing-upload failure, indentation, and immutable action revisions.

| Action | Immutable revision | Release mapping |
| --- | --- | --- |
| `actions/checkout` | `9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0` | v7.0.0 |
| `actions/setup-python` | `ece7cb06caefa5fff74198d8649806c4678c61a1` | v6.3.0 |
| `actions/upload-artifact` | `043fb46d1a93c77aae656e7c1c64a875d1fc6a0a` | v7.0.1 |

### AC3 - Single Controlled Build

The final packaging command was initiated once:

```powershell
$process = Start-Process -FilePath $python `
  -ArgumentList '-m PyInstaller --clean --noconfirm packaging/lister_bridge.spec' `
  -WindowStyle Hidden -Wait -PassThru
$buildExit = $process.ExitCode
if ($buildExit -ne 0) { exit 1 }
```

| Build control | Result |
| --- | --- |
| Active processes before start | 0 |
| PyInstaller `ExitCode` | 0 |
| Active processes after completion | 0 |
| Packaging commands in final cycle | 1 |
| Executable write time | `2026-07-15T03:57:54.2563895Z` |

The orchestration output retrieval returned only the preflight process count. Exit code 0 remains independently enforced by control flow: sidecar generation and stability checks occur only after the waited process returns and the nonzero-exit guard passes; the cell completed successfully and those post-guard artifacts exist.

| Artifact check | Result |
| --- | --- |
| Executable size | 113,126,255 bytes |
| SHA-256 | `e64bab70a4d4202fd5c3fc9005132198dd63985d8835c7df6e18fda6cd158481` |
| Digest length | 64 characters |
| Sidecar | Exact digest match after generation and reread |
| First read | `2026-07-15T03:57:57.6823818Z` |
| Delayed reread | Unchanged at `2026-07-15T03:58:19.6935559Z` |

The delayed reread followed an additional three-second wait. Size, write time, executable digest, sidecar digest, and zero-process state were unchanged. Final dependency, test, workflow, and cache checks also left this artifact unchanged.

### AC4 - Cache Hygiene

```powershell
git -c core.excludesFile=.gitignore status --short --untracked-files=all
git -c core.excludesFile=.gitignore ls-files
git diff --check
```

- Status exit code: 0; nine expected task or coordination entries.
- Supported cache or build paths in status: 0.
- Supported cache or build paths tracked by Git: 0.
- `git diff --check` exit code: 0.
- Active Python or PyInstaller processes after all checks: 0.

## Limitations

- Hosted GitHub Actions execution and artifact upload remain unverified; T-013 owns that external proof.
- The executable was not launched, so GUI persistence remains outside this QA scope.
- Byte-identical PyInstaller output is not claimed; each produced artifact requires its own hash.
- No credentials, `.env` file, AppData application data, or product source was accessed.

This changes if the stable artifact is replaced, a hosted runner rejects the workflow, or the locked dependency graph changes.
