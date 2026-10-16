//! Compile-time desktop roles, independent of executable names and config files.
#[cfg(all(feature = "role-controller", feature = "role-agent"))]
compile_error!("Select exactly one of role-controller and role-agent");

pub const CONTROLLER: bool = cfg!(feature = "role-controller");
pub const AGENT: bool = cfg!(feature = "role-agent");
pub const SPLIT: bool = CONTROLLER || AGENT;
pub const AGENT_UNATTENDED_OPTION: &str = "agent-unattended-enabled";

/// An owner must opt in locally and set a usable *local* permanent password.
/// A server-supplied preset password or an overridden option cannot enable this.
pub fn agent_unattended_enabled() -> bool {
    AGENT
        && hbb_common::config::Config2::get()
            .options
            .get(AGENT_UNATTENDED_OPTION)
            .map(String::as_str)
            == Some("Y")
        && hbb_common::config::Config::has_local_permanent_password()
}

pub const fn name() -> &'static str {
    if CONTROLLER { "Controller" } else if AGENT { "Agent" } else { "Standard" }
}

/// Apply after signed custom settings, in every UI/server/CM process.
pub fn init() {
    if !SPLIT { return; }
    use hbb_common::config;
    *config::APP_NAME.write().unwrap() = format!("RustDesk{}", name());
    let mut hard = config::HARD_SETTINGS.write().unwrap();
    hard.insert("conn-type".into(), if CONTROLLER { "outgoing" } else { "incoming" }.into());
    hard.insert("disable-installation".into(), "Y".into());
    drop(hard);
    if AGENT {
        let mut fixed = config::OVERWRITE_SETTINGS.write().unwrap();
        for (key, value) in [
            ("approve-mode", "click"),
            ("allow-hide-cm", "N"),
            ("enable-terminal", "N"),
            ("enable-tunnel", "N"),
            ("enable-block-input", "N"),
            ("enable-privacy-mode", "N"),
            ("enable-remote-restart", "N"),
        ] {
            fixed.insert(key.into(), value.into());
        }
        config::BUILTIN_SETTINGS.write().unwrap()
            .insert("allow-logon-screen-password".into(), "N".into());
    }
}

/// Build identity can be checked from the actual DLL without trusting its name.
#[no_mangle]
pub extern "C" fn rustdesk_build_role() -> u32 {
    if CONTROLLER { 1 } else if AGENT { 2 } else { 0 }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn role_policy_overrides_saved_and_custom_settings() {
        if !SPLIT { return; }
        use hbb_common::{config, password_security};
        config::HARD_SETTINGS.write().unwrap().insert("conn-type".into(), "both".into());
        config::OVERWRITE_SETTINGS.write().unwrap().insert("approve-mode".into(), "password".into());
        init();
        assert_eq!(config::is_outgoing_only(), CONTROLLER);
        assert_eq!(config::is_incoming_only(), AGENT);
        assert!(config::is_disable_installation());
        if AGENT {
            assert_eq!(password_security::approve_mode(), password_security::ApproveMode::Click);
            assert!(!password_security::hide_cm());
            config::Config::set_option("approve-mode".into(), "password".into());
            assert_eq!(password_security::approve_mode(), password_security::ApproveMode::Click);
        }
    }
}
