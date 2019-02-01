#
# Copyright 2017, Data61
# Commonwealth Scientific and Industrial Research Organisation (CSIRO)
# ABN 41 687 119 230.
#
# This software may be distributed and modified according to the terms of
# the BSD 2-Clause license. Note that NO WARRANTY is provided.
# See "LICENSE_BSD2.txt" for details.
#
# @TAG(DATA61_BSD)
#

cmake_minimum_required(VERSION 3.7.2)

function(BuildCapDLApplication)
    cmake_parse_arguments(PARSE_ARGV 0 CAPDL_BUILD_APP "" "C_SPEC;L_SPEC;OUTPUT" "ELF;DEPENDS")
    if (NOT "${CAPDL_BUILD_APP_UNPARSED_ARGUMENTS}" STREQUAL "")
        message(FATAL_ERROR "Unknown arguments to BuildCapDLApplication ${CAPDL_BUILD_APP_UNPARSED_ARGUMENTS}")
    endif()
    # Require a cspec and an output
    if ("${CAPDL_BUILD_APP_C_SPEC}" STREQUAL "")
        message(FATAL_ERROR "C_SPEC is required argument to BuildCapDLApplication")
    endif()
    if ("${CAPDL_BUILD_APP_OUTPUT}" STREQUAL "")
        message(FATAL_ERROR "OUTPUT is required argument to BuildCapDLApplication")
    endif()
    # Build a CPIO archive out of the provided ELF files
    MakeCPIO(archive.o "${CAPDL_BUILD_APP_ELF}"
        CPIO_SYMBOL _capdl_archive
    )
    # Build the application
    add_executable("${CAPDL_BUILD_APP_OUTPUT}" EXCLUDE_FROM_ALL
        $<TARGET_PROPERTY:capdl_app_properties,C_FILES>
        ${CAPDL_LOADER_APP_C_FILES}
        archive.o
        ${CAPDL_BUILD_APP_C_SPEC}
        ${CAPDL_BUILD_APP_L_SPEC}
    )
    add_dependencies("${CAPDL_BUILD_APP_OUTPUT}" ${CAPDL_BUILD_APP_DEPENDS})
    target_include_directories("${CAPDL_BUILD_APP_OUTPUT}" PRIVATE $<TARGET_PROPERTY:capdl_app_properties,INCLUDE_DIRS>)
    target_link_libraries("${CAPDL_BUILD_APP_OUTPUT}" Configuration muslc sel4 elf cpio sel4platsupport sel4utils sel4muslcsys)
endfunction(BuildCapDLApplication)

function(cdl_ld_with_so outfile output_target)
    cmake_parse_arguments(PARSE_ARGV 2 CDL_LD "" "" "ELF;MANIFESTS;DEPENDS;SO")
    if (NOT "${CDL_LD_UNPARSED_ARGUMENTS}" STREQUAL "")
        message(FATAL_ERROR "Unknown arguments to cdl_ld_with_so")
    endif()

    add_custom_command(OUTPUT "${outfile}"
        COMMAND ${python_with_capdl} ${CDL_LD_MANIFESTS} |
        ${capdl_linker_tool}
            --arch=${KernelSel4Arch}
            gen_cdl
            --manifest-in -
            --elffile ${CDL_LD_ELF}
            --sofile ${CDL_LD_SO}
            --outfile ${outfile}
        DEPENDS ${CDL_LD_ELF} ${capdl_python} ${CDL_LD_MANIFESTS})

    add_custom_target(${output_target} DEPENDS "${outfile}")
    add_dependencies(${output_target} ${CDL_LD_DEPENDS})
endfunction()

function(cdl_pp_with_so manifest_in target target_so)
    cmake_parse_arguments(PARSE_ARGV 3 CDL_PP "" "" "ELF;CFILE;DEPENDS;SO;SO_CFILE")
    if (NOT "${CDL_PP_UNPARSED_ARGUMENTS}" STREQUAL "")
        message(FATAL_ERROR "${CDL_PP_UNPARSED_ARGUMENTS}")
        message(FATAL_ERROR "Unknown arguments to cdl_pp_with_so")
    endif()

    add_custom_command(OUTPUT ${CDL_PP_CFILE}
        COMMAND ${python_with_capdl} ${manifest_in} |
        ${capdl_linker_tool}
                --arch=${KernelSel4Arch}
                build_cnode
                --manifest-in=-
                --elffile ${CDL_PP_ELF}
                --ccspace ${CDL_PP_CFILE}
        DEPENDS  ${capdl_python} ${manifest_in} )

    add_custom_command(OUTPUT ${CDL_PP_SO_CFILE}
        COMMAND ${python_with_capdl} ${manifest_in} |
        ${capdl_linker_tool}
                --arch=${KernelSel4Arch}
                build_so_cnode
                --manifest-in=-
                --sofile ${CDL_PP_SO}
                --socspace ${CDL_PP_SO_CFILE}
        DEPENDS  ${capdl_python} ${manifest_in})

    add_custom_target(${target_so} DEPENDS ${CDL_PP_SO_CFILE})
    add_custom_target(${target} DEPENDS ${CDL_PP_CFILE})
endfunction()


function(cdl_calc_relo progname soname symbolfile target)

    add_custom_command(OUTPUT ${symbolfile}
        COMMAND python3 ${CMAKE_SOURCE_DIR}/projects/camkes/capdl/cdl_utils/calc_relo.py ${progname} ${soname} ${symbolfile}
        COMMENT "Generating symbolfile for ${progname} with ${soname}"
        )

    add_custom_target(${target} DEPENDS ${symbolfile})
endfunction()


function(cdl_pp_so shared_lib shared_lib_aux shared_lib_symbol)
    add_custom_command(OUTPUT ${shared_lib_aux}
        COMMAND python3 ${CMAKE_SOURCE_DIR}/projects/camkes/capdl/cdl_utils/so_pp.py ${shared_lib} ${shared_lib_aux} ${shared_lib_symbol}
        COMMENT "Generating shared library linking aux file for ${shared_lib}"
        )
endfunction()

function(DeclareCDLRootImageDyn cdl cdl_target)
    cmake_parse_arguments(PARSE_ARGV 2 CDLROOTTASK "" "" "ELF;ELF_DEPENDS")
    if (NOT "${CDLROOTTASK_UNPARSED_ARGUMENTS}" STREQUAL "")
        message(FATAL_ERROR "Unknown arguments to DeclareCDLRootImage")
    endif()

    CapDLToolCFileGen(${cdl_target}_cspec ${cdl_target}_cspec.c ${cdl} "${CAPDL_TOOL_BINARY}"
        MAX_IRQS ${CapDLLoaderMaxIRQs}
        DEPENDS ${cdl_target} install_capdl_tool "${CAPDL_TOOL_BINARY}")

    add_custom_command(OUTPUT link_spec.c
        COMMAND python3 ${CMAKE_SOURCE_DIR}/projects/camkes/capdl/cdl_utils/gen_so_mapping_info.py ${CDLROOTTASK_ELF}
        COMMENT "Generating shared library linking info for ${CDLROOTTASK_ELF}"
        DEPENDS ${CDLROOTTASK_ELF} ${CDLROOTTASK_ELF_DEPENDS}
        )

    add_custom_target(link_spec DEPENDS link_spec.c)

    # Ask the CapDL tool to generate an image with our given copied/mangled instances
    BuildCapDLApplication(
        C_SPEC "${cdl_target}_cspec.c"
        L_SPEC "link_spec.c"
        ELF ${CDLROOTTASK_ELF}
        DEPENDS ${CDLROOTTASK_ELF_DEPENDS} ${cdl_target}_cspec link_spec
        OUTPUT "capdl-loader"
    )
    DeclareRootserver("capdl-loader")
endfunction()
