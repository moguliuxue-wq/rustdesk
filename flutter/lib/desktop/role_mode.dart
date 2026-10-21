/// Set by build.py alongside the Cargo role feature.
const buildRole = String.fromEnvironment('RUSTDESK_ROLE', defaultValue: 'standard');
const isAgentBuild = buildRole == 'agent';
const isControllerBuild = buildRole == 'controller';
