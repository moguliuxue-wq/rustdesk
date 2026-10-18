#pragma once

// Opt-in, Agent-only diagnostic. Enabled at runtime solely by an
// explicit RUSTDESK_AGENT_MINHOOK_DIAGNOSTICS=1 environment variable.
namespace agent_hook_diagnostics {
void StartIfRequested();
void Stop();
}  // namespace agent_hook_diagnostics
