cmake_minimum_required(VERSION 3.16)
project(governor_harness C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

find_package(Vulkan REQUIRED)

# --- SPIR-V de los shaders ---
file(MAKE_DIRECTORY "${CMAKE_BINARY_DIR}/_gen")
foreach(sh vert frag)
  set(spv_src "${CMAKE_CURRENT_SOURCE_DIR}/glsl/triangle.${sh}")
  set(spv_dst "${CMAKE_BINARY_DIR}/_gen/triangle.${sh}.spv")
  add_custom_command(
    OUTPUT "${spv_dst}"
    COMMAND glslangValidator -V "${spv_src}" -o "${spv_dst}"
    DEPENDS "${spv_src}"
    COMMENT "Compilando shader ${sh}"
  )
  list(APPEND SPV_OUT "${spv_dst}")
endforeach()
add_custom_target(shaders ALL DEPENDS ${SPV_OUT})

# --- harness (aplicación offscreen, Diseño B) ---
add_executable(governor_harness app_vulkan.c)
target_link_libraries(governor_harness PRIVATE Vulkan::Vulkan m)
add_dependencies(governor_harness shaders)

enable_testing()