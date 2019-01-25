
import os
import argparse
from jinja2 import Environment, BaseLoader, FileSystemLoader
from elftools.elf.elffile import ELFFile

SYMBOL_FILE_TEMPLATE = os.path.join(os.path.dirname(__file__), "templates/symbol.file.template")

def main(shared_lib_name, program_name, output_name):
    offset = find_shared_lib_frame(program_name)
    f = open(shared_lib_name, 'rb')
    elf = ELFFile(f)

    symtab = elf.get_section_by_name('.symtab')

    symbols = []

    for i in symtab.iter_symbols():
        if i.name == "":
            continue

        st_info = i['st_info']
        t = st_info['type']

        if t != 'STT_OBJECT' and t != 'STT_FUNC':
            continue
        if st_info['bind'] != 'STB_GLOBAL':
            continue
        if i.name == '_init' or i.name == '_fini':
            continue

        addr = i['st_value']

        #  print("{:X}".format(addr + offset))
        #  print(i.name)

        symbols.append((i.name, "0x{:X}".format(addr+offset)))

    output_file = open(output_name, 'w')
    template_file = open(SYMBOL_FILE_TEMPLATE, 'r').read()
    template = Environment(loader=BaseLoader).from_string(template_file)

    data =template.render({'symbols':symbols})
    print(data)
    output_file.write(data)


def find_shared_lib_frame(progname):
    f = open(progname, 'rb')
    elf = ELFFile(f)
    symtab = elf.get_section_by_name('.symtab')
    for i in symtab.iter_symbols():
        if i.name == "sharedLibFrame":
            addr = i['st_value']
            return addr

    return 0


if __name__ == "__main__":
    # here this program should be invoked by cmake
    # and then this program will calculate the relocation
    # for us and write to the symbol file

    parser = argparse.ArgumentParser()

    parser.add_argument('prog', type=str)
    parser.add_argument('so', type=str)
    parser.add_argument('symbolfile', type=str)

    print('in the calc relo script')

    args = parser.parse_args()

    main(args.so, args.prog, args.symbolfile)
