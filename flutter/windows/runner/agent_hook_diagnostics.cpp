// Windows Agent diagnostic only. No process injection or security bypasses.
// The trace does not record message text, HWND or caller details.
#include "agent_hook_diagnostics.h"

#include <windows.h>
#include <MinHook.h>

namespace {
using MessageBoxWProc = int (WINAPI*)(HWND, LPCWSTR, LPCWSTR, UINT);
MessageBoxWProc original_message_box_w = nullptr;
LPVOID message_box_target = nullptr;
bool active = false;

int WINAPI TraceMessageBoxW(HWND owner, LPCWSTR text, LPCWSTR caption, UINT flags) {
  ::OutputDebugStringW(L"[RustDesk Agent diagnostics] MessageBoxW called in this process.\n");
  return original_message_box_w(owner, text, caption, flags);
}

bool ExplicitlyEnabled() {
  wchar_t flag[3] = {};
  const DWORD size = ::GetEnvironmentVariableW(
      L"RUSTDESK_AGENT_MINHOOK_DIAGNOSTICS", flag, 3);
  return size == 1 && flag[0] == L'1';
}
}  // namespace

namespace agent_hook_diagnostics {
void StartIfRequested() {
  if (!ExplicitlyEnabled()) {
    return;
  }
  if (MH_Initialize() != MH_OK) {
    ::OutputDebugStringW(L"[RustDesk Agent diagnostics] MinHook initialization failed.\n");
    return;
  }
  HMODULE user32 = ::GetModuleHandleW(L"user32.dll");
  message_box_target = user32
      ? reinterpret_cast<LPVOID>(::GetProcAddress(user32, "MessageBoxW"))
      : nullptr;
  if (!message_box_target ||
      MH_CreateHook(message_box_target,
          reinterpret_cast<LPVOID>(&TraceMessageBoxW),
          reinterpret_cast<LPVOID*>(&original_message_box_w)) != MH_OK) {
    ::OutputDebugStringW(L"[RustDesk Agent diagnostics] MessageBoxW hook creation failed.\n");
    MH_Uninitialize();
    return;
  }
  if (MH_EnableHook(message_box_target) != MH_OK) {
    ::OutputDebugStringW(L"[RustDesk Agent diagnostics] MessageBoxW hook enabling failed.\n");
    MH_RemoveHook(message_box_target);
    MH_Uninitialize();
    return;
  }
  active = true;
  ::OutputDebugStringW(L"[RustDesk Agent diagnostics] Own-process MessageBoxW trace enabled.\n");
}
void Stop() {
  if (!active) {
    return;
  }
  MH_DisableHook(message_box_target);
  MH_RemoveHook(message_box_target);
  MH_Uninitialize();
  active = false;
}
}  // namespace agent_hook_diagnostics
