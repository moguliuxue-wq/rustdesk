cmake_minimum_required(VERSION 3.14)
project(runner LANGUAGES CXX)

# Define the application target. To change its name, change BINARY_NAME in the
# top-level CMakeLists.txt, not the value here, or `flutter run` will no longer
# work.
#
# Any new source files that you add to the application should be added here.
add_executable(${BINARY_NAME} WIN32
  "flutter_window.cpp"
  "main.cpp"
  "utils.cpp"
  "win32_desktop.cpp"
  "win32_window.cpp"
  "${FLUTTER_MANAGED_DIR}/generated_plugin_registrant.cc"
  "Runner.rc"
  "runner.exe.manifest"
)

# Apply the standard set of build settings. This can be removed for applications
# that need different build settings.
apply_standard_settings(${BINARY_NAME})

# Add preprocessor definitions for the build version.
target_compile_definitions(${BINARY_NAME} PRIVATE "FLUTTER_VERSION=\"${FLUTTER_VERSION}\"")
target_compile_definitions(${BINARY_NAME} PRIVATE "FLUTTER_VERSION_MAJOR=${FLUTTER_VERSION_MAJOR}")
target_compile_definitions(${BINARY_NAME} PRIVATE "FLUTTER_VERSION_MINOR=${FLUTTER_VERSION_MINOR}")
target_compile_definitions(${BINARY_NAME} PRIVATE "FLUTTER_VERSION_PATCH=${FLUTTER_VERSION_PATCH}")
target_compile_definitions(${BINARY_NAME} PRIVATE "FLUTTER_VERSION_BUILD=${FLUTTER_VERSION_BUILD}")

# Disable Windows macros that collide with C++ standard library functions.
target_compile_definitions(${BINARY_NAME} PRIVATE "NOMINMAX")

# Add dependency libraries and include directories. Add any application-specific
# dependencies here.
target_link_libraries(${BINARY_NAME} PRIVATE flutter flutter_wrapper_app)
target_include_directories(${BINARY_NAME} PRIVATE "${CMAKE_SOURCE_DIR}")

# Run the Flutter tool portions of the build. This must not be removed.
add_dependencies(${BINARY_NAME} flutter_assemble)

# Agent-only self-process Win32 diagnostic: compiled but disabled by default.
# We vendor MinHook 1.3.4 rather than loading or injecting a separate DLL.
# Controller and standard RustDesk never link the library.
if("$ENV{RUSTDESK_AGENT_MINHOOK_BUILD}" STREQUAL "1")
  enable_language(C)
  set(AGENT_MINHOOK_DIR "${CMAKE_CURRENT_SOURCE_DIR}/vendor/minhook-1.3.4")
  add_library(rustdesk_agent_minhook STATIC
    "${AGENT_MINHOOK_DIR}/src/buffer.c"
    "${AGENT_MINHOOK_DIR}/src/hook.c"
    "${AGENT_MINHOOK_DIR}/src/trampoline.c"
    "${AGENT_MINHOOK_DIR}/src/hde/hde64.c"
  )
  target_include_directories(rustdesk_agent_minhook PRIVATE
    "${AGENT_MINHOOK_DIR}/include"
    "${AGENT_MINHOOK_DIR}/src"
    "${AGENT_MINHOOK_DIR}/src/hde"
  )
  target_sources(${BINARY_NAME} PRIVATE "agent_hook_diagnostics.cpp")
  target_include_directories(${BINARY_NAME} PRIVATE "${AGENT_MINHOOK_DIR}/include")
  target_compile_definitions(${BINARY_NAME} PRIVATE RUSTDESK_AGENT_MINHOOK_BUILD=1)
  target_link_libraries(${BINARY_NAME} PRIVATE rustdesk_agent_minhook)
endif()
