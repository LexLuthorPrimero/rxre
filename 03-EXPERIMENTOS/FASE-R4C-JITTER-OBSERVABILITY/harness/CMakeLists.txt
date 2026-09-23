cmake_minimum_required(VERSION 3.16)
project(jitter_harness C)

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

# --- capa de observabilidad (shared lib) ---
add_library(jitter_layer SHARED layer/layer.c perframe.c)
set_target_properties(jitter_layer PROPERTIES
  OUTPUT_NAME jitter_layer
  PREFIX lib
  C_VISIBILITY_PRESET hidden
)
target_include_directories(jitter_layer PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}")
target_link_libraries(jitter_layer PRIVATE Vulkan::Vulkan m)
# copia la .so y el manifest a entrada VARIA de la capa
set(LAYER_DIR "${CMAKE_BINARY_DIR}/layer")
add_custom_command(TARGET jitter_layer POST_BUILD
  COMMAND ${CMAKE_COMMAND} -E make_directory "${LAYER_DIR}"
  COMMAND ${CMAKE_COMMAND} -E copy_if_different
          "$<TARGET_FILE:jitter_layer>" "${LAYER_DIR}/libjitter_layer.so"
  COMMAND ${CMAKE_COMMAND} -E copy_if_different
          "${CMAKE_CURRENT_SOURCE_DIR}/layer/VkLayer_iterativero_jitter_observer.json"
          "${LAYER_DIR}/"
  COMMENT "Centro de capa listo en ${LAYER_DIR}"
)

# --- harness (aplicacion) ---
add_executable(jitter_harness app_vulkan.c perframe.c jittergen.c)
target_include_directories(jitter_harness PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}")
target_link_libraries(jitter_harness PRIVATE Vulkan::Vulkan m)
add_dependencies(jitter_harness shaders)

enable_testing()