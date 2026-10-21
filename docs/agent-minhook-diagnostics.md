# Agent-only MinHook 1.3.4 diagnostics

This integration vendors MinHook 1.3.4 and statically compiles it into the
**Windows x64 Agent executable only**. Controller does not include MinHook.

This is an **own-process Win32 API diagnostic**, not DLL injection or a
mechanism to hide processes, windows, remote sessions, or bypass capture
protections. It observes only `MessageBoxW` calls in the Agent process,
outputs a fixed event marker using `OutputDebugStringW`, and passes every
original argument to the real API unchanged. It does not read or log window
titles, message text, handles, keystrokes, or screen data.

## Opt-in

By default no API is hooked. To enable tracing for a local troubleshooting run,
set `RUSTDESK_AGENT_MINHOOK_DIAGNOSTICS=1` in the environment **before
launching** `RustDeskAgent.exe`, and attach a Windows debugger to view
`OutputDebugStringW` events. Close and reopen Agent without the environment
variable to disable diagnostics. No persistent setting is stored.

The opt-in is checked by the native Windows runner on startup, after creating
the Flutter main window, and removed on shutdown. No automatic service startup,
privilege changes or remote commands were added.

## Build details

`python build.py --portable --flutter --skip-portable-pack --hwcodec --vram
--role agent` sets the native runner's CMake selector and links MinHook
statically. All other roles set the selector to zero. There is **no** runtime
MinHook DLL. The packaged Agent bundle contains `MinHook-LICENSE.txt` for
third-party attribution.

The standard Windows role build workflow compiles both roles. After a build
completes, verify the Agent and Controller separately on disposable Windows
machines; self-process hook availability is not a remote-control acceptance
test.
