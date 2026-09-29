cmake_minimum_required(VERSION 3.16)
project(h12_probe LANGUAGES C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS OFF)

find_package(Vulkan REQUIRED)
find_package(PkgConfig REQUIRED)
pkg_check_modules(WAYLAND_CLIENT REQUIRED IMPORTED_TARGET wayland-client)
pkg_check_modules(WAYLAND_PROTOCOLS REQUIRED IMPORTED_TARGET wayland-protocols)
find_program(WAYLAND_SCANNER_EXECUTABLE NAMES wayland-scanner)
if(NOT WAYLAND_SCANNER_EXECUTABLE)
  message(FATAL_ERROR
    "wayland-scanner is required to generate xdg-shell bindings; "
    "this project does not install it automatically.")
endif()
pkg_get_variable(WAYLAND_PROTOCOLS_DIR wayland-protocols pkgdatadir)

set(XDG_SHELL_XML "${WAYLAND_PROTOCOLS_DIR}/stable/xdg-shell/xdg-shell.xml")
if(NOT EXISTS "${XDG_SHELL_XML}")
  message(FATAL_ERROR
    "Missing xdg-shell protocol XML: ${XDG_SHELL_XML}. "
    "Install the Wayland protocols development data before building; "
    "this project does not install it automatically.")
endif()

set(XDG_GENERATED_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated")
set(XDG_HEADER "${XDG_GENERATED_DIR}/xdg-shell-client-protocol.h")
set(XDG_CODE "${XDG_GENERATED_DIR}/xdg-shell-protocol.c")
add_custom_command(
  OUTPUT "${XDG_HEADER}"
  COMMAND "${CMAKE_COMMAND}" -E make_directory "${XDG_GENERATED_DIR}"
  COMMAND "${WAYLAND_SCANNER_EXECUTABLE}" client-header
          "${XDG_SHELL_XML}" "${XDG_HEADER}"
  DEPENDS "${XDG_SHELL_XML}" "${WAYLAND_SCANNER_EXECUTABLE}"
  COMMENT "Generating xdg-shell client header"
  VERBATIM
)
add_custom_command(
  OUTPUT "${XDG_CODE}"
  COMMAND "${CMAKE_COMMAND}" -E make_directory "${XDG_GENERATED_DIR}"
  COMMAND "${WAYLAND_SCANNER_EXECUTABLE}" private-code
          "${XDG_SHELL_XML}" "${XDG_CODE}"
  DEPENDS "${XDG_SHELL_XML}" "${WAYLAND_SCANNER_EXECUTABLE}"
  COMMENT "Generating xdg-shell client code"
  VERBATIM
)

add_executable(h12_probe
  src/h12_probe.c
  include/h12_probe.h
  "${XDG_HEADER}"
  "${XDG_CODE}"
)

target_include_directories(h12_probe PRIVATE
  "${CMAKE_CURRENT_SOURCE_DIR}/include"
  "${XDG_GENERATED_DIR}"
)
target_link_libraries(h12_probe PRIVATE
  Vulkan::Vulkan
  PkgConfig::WAYLAND_CLIENT
)
target_compile_definitions(h12_probe PRIVATE _POSIX_C_SOURCE=200809L)
target_compile_options(h12_probe PRIVATE -Wall -Wextra -Wpedantic)

# Deliberately no install(), test execution, benchmark target, or runtime hook.
