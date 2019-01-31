#!/usr/bin/env python3
# encoding: utf-8

import os
import argparse
from jinja2 import Environment, BaseLoader, FileSystemLoader
from elftools.elf.elffile import ELFFile

SO_AUX_TEMPLATE = os.path.join(os.path.dirname(__file__), "templates/so.aux.template")

SYMBOL_FILE_TEMPLATE = os.path.join(os.path.dirname(__file__), "templates/symbol.file.template")

def main(so_name, aux_name, symbolfile):
    f = open(so_name, 'rb')
    elf = ELFFile(f)

    relatable = elf.get_section_by_name('.rela.dyn')
    dyn_symtable = elf.get_section_by_name('.dynsym')

    relos = []
    symbols = []

    for i in relatable.iter_relocations():

        n = i['r_info_sym']
        sym = dyn_symtable.get_symbol(n)

        addr = "0x{:X}".format(i['r_offset'])
        to = "0x{:X}".format(sym['st_value'])
        relos.append((addr, to, len(relos)))
        name = 'a{}'.format(len(symbols))
        symbols.append((name, addr))

    template_file = open(SO_AUX_TEMPLATE, 'r').read()
    template = Environment(loader=BaseLoader).from_string(template_file)
    output_file = open(aux_name, 'w')

    data =template.render({'relos':relos})
    print(data)
    output_file.write(data)


    symbol_template_file = open(SYMBOL_FILE_TEMPLATE, 'r').read()
    symbol_template = Environment(loader=BaseLoader).from_string(symbol_template_file)
    symbol_output = open(symbolfile, 'w')


    data = symbol_template.render({'symbols':symbols})
    print(data)
    symbol_output.write(data)





if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument('so', type=str)
    parser.add_argument('aux', type=str)
    parser.add_argument('symbolfile', type=str)

    print('in the so pp script')
    args = parser.parse_args()

    main(args.so, args.aux, args.symbolfile)

