import os
import argparse
from jinja2 import Environment, BaseLoader, FileSystemLoader
from elftools.elf.elffile import ELFFile

items = []

LINK_INFO_TEMPLATE_FILE = os.path.join(os.path.dirname(__file__), "templates/link.info.template.c")

def main(prog):
    f = open(prog, 'rb')
    elf = ELFFile(f)

    dyn = elf.get_section_by_name('.dynamic')
    for i in dyn.iter_tags():
        tag_type = i['d_tag']
        if tag_type == 'DT_NEEDED':
            so = i.needed
            so_filename = os.path.basename(so)
            handle_so(so_filename, elf, prog)


def handle_so(so, prog_elf, progname):
    so_file = open(so, 'rb')
    so_elf = ELFFile(so_file)

    to = 0;
    for i in so_elf.iter_segments():
        if i['p_type'] == 'PT_LOAD':
            begin = i['p_vaddr']
            end = i['p_memsz']
            if begin + end > to:
                to = begin + end

    base = find_shared_lib_frame(prog_elf)
    so_name = 'tcb_' + so[3:-3]
    items.append((so_name, 'tcb_' + progname, len(items), to, base))


def find_shared_lib_frame(prog):
    symtab = prog.get_section_by_name('.symtab')
    for i in symtab.iter_symbols():
        if i.name == "sharedLibFrame":
            addr = i['st_value']
            return addr

    return 0


if __name__ == "__main__":
    #  parser = argparse.ArgumentParser()
    #  parser.add_argument('prog', type=str)
    main('program_2')

    template_file = open(LINK_INFO_TEMPLATE_FILE, 'r').read()
    template = Environment(loader=BaseLoader).from_string(template_file)
    print(items)

    data =template.render({'items':items, 'num': len(items)})
    print(data)

    out = open('linking.spec.c', 'w')
    out.write(data)
