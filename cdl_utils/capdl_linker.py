#!/usr/bin/env python
#
# Copyright 201*, Data61
# Commonwealth Scientific and Industrial Research Organisation (CSIRO)
# ABN 41 687 119 230.
#
# This software may be distributed and modified according to the terms of
# the BSD 2-Clause license. Note that NO WARRANTY is provided.
# See "LICENSE_BSD2.txt" for details.
#
# @TAG(DATA61_BSD)
#

import sys
import argparse
import pickle
import logging
import os
import tempfile
import pkg_resources
import six
pkg_resources.require("jinja2>=2.10")
from jinja2 import Environment, BaseLoader, FileSystemLoader

from capdl import ELF, lookup_architecture

CSPACE_TEMPLATE_FILE = os.path.join(os.path.dirname(__file__), "templates/cspace.template.c")

SO_CSPACE_TEMPLATE_FILE = os.path.join(os.path.dirname(__file__), "templates/cspace.so.template.c")


def manifest(cap_symbols, region_symbols, architecture, targets):
    """
    Generates a c file from CSPACE_TEMPLATE_FILE with some runtime information
    about CSpace slots and special address ranges

    NOTE: the generated file is depended staticly compiled sel4 kernel,
    hence it's not directly usable for dynamic linking purpose
    """
    temp_file = open(CSPACE_TEMPLATE_FILE, 'r').read()
    template = Environment(loader=BaseLoader).from_string(temp_file)

    print("In manifest function")
    for (e, ccspace) in targets:
        print(e)
        print(ccspace)
        name = os.path.basename(e)

        if ccspace:
            data = template.render({'slots': cap_symbols[name],
                                    'symbols': region_symbols[name],
                                    'progname': name,
                                    'ipc_buffer_symbol': "mainIpcBuffer"})
            ccspace.write(data)


def so_manifest(cap_symbols, region_symbols, architecture, targets):
    """
    Generates a c file from CSPACE_TEMPLATE_FILE with some runtime information
    about CSpace slots and special address ranges
    """
    so_temp_file = open(SO_CSPACE_TEMPLATE_FILE, 'r').read()
    so_template = Environment(loader=BaseLoader).from_string(so_temp_file)

    print("In so_manifest function")
    for (e, ccspace) in targets:
        print(e)
        print(ccspace)
        name = os.path.basename(e)[3:-3]

        if ccspace:
            data = so_template.render({
                                    'symbols': region_symbols[name],
                                    'progname': name,
                                    'ipc_buffer_symbol': "mainIpcBuffer"})
            ccspace.write(data)



def final_spec(cspaces, obj_space, addr_spaces, elf_files, architecture, so_files):
    """
    Generates a final CapDL spec file that can be given to a capdl loader application
    """

    # cspaces : dict containes all the CSpaceAllocator for this app
    # obj_space : ObjectAllocator for all the objs in the spec
    # addr_spaces : dict containers all the AddressSpaceAllocator for this app
    print("In final_spec function")
    arch = lookup_architecture(architecture)

    # NOTE: handle shared lib so files here
    for e in [item for sublist in so_files for item in sublist]:
        name = os.path.basename(e)
        name = name[3:-3]
        print(name)

        elf = ELF(e, name, architecture)
        cspace = cspaces[name]

        print('the vspace root is ' + str(addr_spaces[name].vspace_root))
        print('The addr space allocator is ' + str(addr_spaces[name]))

        # Avoid inferring a TCB as we've already created our own.
        elf_spec = elf.get_spec(
            infer_tcb=False,
            infer_asid=False,
            pd=addr_spaces[name].vspace_root,
            addr_space=addr_spaces[name]
            )

        obj_space.merge(elf_spec)
        cspace.cnode.finalise_size(arch)

        # Fill in TCB object information.
        # NOTE: There will be a tcb for a shared lib file but handled in root task of capdl
        # loader
        # TODO: This should be generalised with what is in the Camkes filters
        tcb = obj_space["tcb_%s" % name]
        progsymbol = 0
        vsyscall = 0
        tcb.init = [0,0,0,0,2,progsymbol,1,0,0,32,vsyscall,0,0]
        tcb.addr = 0
        tcb.sp = 0
        tcb.ip = 0


    for e in [item for sublist in elf_files for item in sublist]:
        name = os.path.basename(e)
        print(name)

        # path, name, arch
        elf = ELF(e, name, architecture)

        # find the cspace for current elf
        cspace = cspaces[name]

        print('the vspace root is ' + str(addr_spaces[name].vspace_root))
        print('The addr space allocator is ' + str(addr_spaces[name]))

        # Avoid inferring a TCB as we've already created our own.
        elf_spec = elf.get_spec(
            infer_tcb=False,
            infer_asid=False,
            pd=addr_spaces[name].vspace_root,
            addr_space=addr_spaces[name]
            )
        obj_space.merge(elf_spec)
        cspace.cnode.finalise_size(arch)

        # Fill in TCB object information.
        # TODO: This should be generalised with what is in the Camkes filters
        tcb = obj_space["tcb_%s" % name]
        progsymbol = elf.get_symbol_vaddr("progname")
        vsyscall = elf.get_symbol_vaddr("sel4_vsyscall")
        tcb.init = [0,0,0,0,2,progsymbol,1,0,0,32,vsyscall,0,0]
        tcb.addr = elf.get_symbol_vaddr("mainIpcBuffer");
        tcb.sp = elf.get_symbol_vaddr("stack")+elf.get_symbol_size("stack");
        tcb.ip = elf.get_entry_point()

    return obj_space

def main():
    parser = argparse.ArgumentParser(
                description="")
    parser.add_argument('--architecture', '--arch', default='aarch32',
        type=lambda x: type('')(x).lower(), choices=('aarch32', 'arm_hyp', 'ia32', 'x86_64', 'aarch64'),
        help='Target architecture.')
    subparsers = parser.add_subparsers()
    parser_a = subparsers.add_parser('build_cnode')
    parser_a.add_argument('--ccspace', nargs='+', type=argparse.FileType('w'), action='append')
    parser_a.set_defaults(which="build_cnode")
    parser_a.add_argument('--manifest-in', type=argparse.FileType('rb'))
    parser_a.add_argument('--elffile', nargs='+', action='append')

    parser_b = subparsers.add_parser('gen_cdl')
    parser_b.add_argument('--outfile', type=argparse.FileType('w'))
    parser_b.set_defaults(which="gen_cdl")
    parser_b.add_argument('--manifest-in', type=argparse.FileType('rb'))
    parser_b.add_argument('--elffile', nargs='+', action='append')
    parser_b.add_argument('--sofile', nargs='+', action='append')

    parser_c = subparsers.add_parser('build_so_cnode')
    parser_c.set_defaults(which="build_so_cnode")
    parser_c.add_argument('--manifest-in', type=argparse.FileType('rb'))
    parser_c.add_argument('--sofile', nargs='+', action='append')
    parser_c.add_argument('--socspace', nargs='+', type=argparse.FileType('w'), action='append')

    args = parser.parse_args()

    (objects, cspaces, addr_spaces, cap_symbols, region_symbols, elfs) = pickle.load(args.manifest_in)
    if args.which is "build_cnode":
        elfs = [item for sublist in args.elffile for item in sublist]
        cspaces = [item for sublist in args.ccspace for item in sublist]
        targets = zip(elfs, cspaces)
        manifest(cap_symbols, region_symbols, args.architecture, targets)
        return 0

    if args.which is "build_so_cnode":
        print("shared lib passed in :")
        print(args.sofile)
        sos = [item for sublist in args.sofile for item in sublist]
        so_cspaces = [item for sublist in args.socspace for item in sublist]
        so_targets = zip(sos, so_cspaces)
        so_manifest(cap_symbols, region_symbols, args.architecture, so_targets)
        return 0

    if args.which is "gen_cdl":
        print("shared lib passed in :")
        print(args.sofile)
        # cspaces : dict containes all the CSpaceAllocator for this app
        # objects : ObjectAllocator for all the objs in the spec
        # addr_spaces : dict containers all the AddressSpaceAllocator for this app
        obj_space = final_spec(cspaces, objects, addr_spaces, args.elffile, args.architecture, args.sofile)
        args.outfile.write(repr(obj_space.spec))

    return 0

if __name__ == '__main__':
    sys.exit(main())
