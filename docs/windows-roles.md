# Windows Controller / Agent

These are native RustDesk source builds, not downloaders. The base is fork commit
`209f4626`, whose parent `e400bb75` matches official rustdesk/rustdesk master inspected
on 2026-10-16. Cargo and the upstream Windows workflow report **1.5.1**. No official
`1.5.1` or `v1.5.1` tag existed when inspected; this is the official 1.5.1 development
source, not a claim of a tagged stable release.

## Roles

| Behavior | Controller | Agent |
|---|---|---|
| Initiate remote sessions | Yes | Rejected in Rust client, including side switching |
| Accept inbound sessions | No server startup; connection entry also rejects | Local click by default; owner may explicitly enroll a local password for unattended access |
| Home screen | Outgoing connections | Local ID, role notice and online status |
| Active connection status | Remote session window | Existing visible connection manager with peer and Disconnect |
| Password / trusted-session automatic approval | No receiving | Only an enrolled local permanent password may replace a click; temporary, preset and remembered sessions cannot |
| Install / system service / remote elevation | Disabled | Disabled |
| Privacy black screen / block local input | N/A | Rejected in native handlers |
| Terminal / TCP tunnel | Can initiate to compatible standard hosts | Disabled |

Cargo features `role-controller` and `role-agent` are mutually exclusive. Neither feature
means standard upstream behavior. `role::init()` applies after custom client config in
every process, fixes upstream direction flags consumed by Flutter and native code,
and assigns separate RustDeskController / RustDeskAgent app/config/IPC identities.
The binaries still contain shared upstream code; this is enforced role behavior,
not a claim that every unused source module has been removed.

The Agent uses upstream's accept/reject connection manager. Closing that window or
pressing Disconnect ends the session. No hidden connection-manager mode is permitted.
By default, the native authorization gate requires a local CM click for each connection,
including reconnects and remembered sessions. The device owner can explicitly enable
unattended access on Agent's home screen by confirming ownership and setting a new
local password of at least 12 characters. Only that local password can authorize a
later connection without a click; server presets and temporary passwords cannot.
The connection manager remains visible while connected, with peer status and Disconnect.
Revoking unattended access clears the password and restores click approval for new
connections; an already active session must be disconnected in the manager. Closing
Agent or the receiving process ends availability; this build does not install a service
or silently start at login. This does not defend against malware already running as
the local user.

Agent also has a local, manually enabled diagnostic panel. The owner must confirm
authorization in that window before running a self-test. It reports detected display
count and whether the normal capturer initializes; it does not read, save or transmit
frames, change another process, or override window capture restrictions. The panel
switch resets to off when Agent closes. Initialization success is not proof that a
particular protected window can be captured.

## Build

Use the **Windows Controller and Agent** workflow. Pushes to `role/controller-agent`
build both roles on separate Windows x64 runners, with the existing Flutter bridge,
patched Flutter 3.24.5 engine, Rust 1.75, LLVM and pinned vcpkg dependencies.
It does not publish standard releases or download an official RustDesk EXE.

With the same build prerequisites installed locally:

```powershell
git submodule update --init --recursive
python build.py --portable --flutter --skip-portable-pack --hwcodec --vram --role controller
python res/roles/package_windows.py --role controller --bundle flutter/build/windows/x64/runner/Release --output dist
# Use a fresh checkout or finish archiving Controller before building Agent.
python build.py --portable --flutter --skip-portable-pack --hwcodec --vram --role agent
python res/roles/package_windows.py --role agent --bundle flutter/build/windows/x64/runner/Release --output dist
```

Each artifact contains a ZIP with `RustDeskController.exe` or `RustDeskAgent.exe`,
the actual role-specific `librustdesk.dll`, Flutter engine/plugins, virtual-display
library and the entire `data/` directory. Extract the complete ZIP; the EXE alone
is not standalone. Windows x64 and the Microsoft Visual C++ 2015–2022 x64 runtime
are required. Optional printer / USB virtual-display drivers are not bundled by this
workflow. Normal desktop control does not require those drivers. Signing is not configured.

The same artifact also contains a self-extracting `*-portable.exe` built from that
verified bundle with the repository's native portable packer. It is one downloadable
EXE, but extracts the same DLLs and `data/` files under LocalAppData when launched.
The build verifies extraction and checks the role export of the extracted DLL.
The same owner enrollment, connection-manager visibility and native role restrictions
apply to this form too.
RustDesk already records debug logs under the role's app data directory; its
rendezvous server remains configurable. No shared default password is supplied.

Packaging fails unless all core bundle files exist, Windows can load the actual DLL,
the DLL export identifies the requested role, the compiled EXE reports 1.5.1,
and the packaged GUI process survives a ten-second launch smoke test.
The ZIP includes source commit and per-file SHA-256 hashes; a ZIP hash is uploaded too.
These checks establish build identity and startup, not successful remote control.

## Acceptance on two Windows desktops (required before production use)

1. Start Controller and Agent; verify their distinct titles/home screens and Agent ID.
2. In default mode, connect to Agent. Before local Allow, verify no screen/input/file
   access. Reject once, reconnect and click Allow.
3. On Agent, enroll unattended access with a fresh 12+ character password. Reconnect
   using that password: no click is needed, but the CM must show peer/status and Disconnect.
   Check that a temporary password, a server preset or a remembered session alone fails.
4. Disconnect from Agent, then close its CM window during a second session; both end control.
5. Revoke unattended access in Agent, disconnect any existing session, then verify a
   remembered password/session cannot reconnect without a fresh local Allow.
6. Try Agent `--connect`, URI, file transfer and side switching; outgoing sessions must fail.
7. Try Controller incoming direct IP and rendezvous; no receiving service/session is available.
8. Try black screen and block input against Agent; local display/input remain usable.
9. Test missing DLL/data on a disposable copy; confirm the full bundle is needed. Test on
   a clean Windows VM with the documented VC runtime, not just a developer machine.

Do not report executable availability until the role workflow has uploaded its artifacts.
Do not report interactive acceptance as passed until the two-desktop tests are performed.
