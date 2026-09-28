# FSTR Command Probe

Read-only diagnostic AEGP for the AE 25.6 `AEGP_Command_ALL` candidate.

It requests `AEGP_HP_BeforeAE`, never handles commands, and records the actual callback priority. SDK 25.6 describes the callback priority as "currently always BeforeAE"; post-commit timing is therefore NOT established. It does not read or write project state.

Build on macOS with `FSTR_AE_SDK_ROOT=/path/to/sdk zsh scripts/build-command-probe.sh`. Each build has its own directory under `.artifacts/command-probe`, source hashes, Git state, toolchain record, build log, ad-hoc signed bundle and archive hash. The current build explicitly targets arm64.

Launch the AE process with `FSTR_COMMAND_PROBE_LOG` set to an absolute, non-existing file in a unique run directory. The parent directory must exist. The probe refuses an absent path or an existing log. Each event carries a Build ID, sequence number and microsecond elapsed time. Capture stops on the first callback after 10 minutes or 100,000 events; this is a capture limit, not an AE watchdog. A `loaded` record means registration succeeded, not that Timeline coverage passed.

Logging flushes synchronously for diagnostic durability and has unmeasured overhead. It cannot establish production performance acceptance. Installation, actual AE loading and coverage are separate required checks.

This is a diagnostic artifact, not part of the FSTR production extension. The log shows which commands reach the hook; it cannot alone prove that every Timeline mutation is represented.
