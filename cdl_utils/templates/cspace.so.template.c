/*
 * Copyright 2018, Data61
 * Commonwealth Scientific and Industrial Research Organisation (CSIRO)
 * ABN 41 687 119 230.
 *
 * This software may be distributed and modified according to the terms of
 * the BSD 2-Clause license. Note that NO WARRANTY is provided.
 * See "LICENSE_BSD2.txt" for details.
 *
 * @TAG(DATA61_BSD)
 */
#define VISIBLE      __attribute__((externally_visible))
#define ALIGN(n)     __attribute__((__aligned__(n)))
#define SECTION(sec) __attribute__((__section__(sec)))

#define SIZED_SYMBOL(symbol, size, section) \
	char symbol[size] VISIBLE ALIGN(4096) SECTION(section);

#define FUNC_SYMBOL(symbol, type) \
    type VISIBLE symbol();

{% for (symbol, size, section) in symbols -%}
SIZED_SYMBOL({{symbol}}, {{size}}, "{{section}}")
{% endfor %}

{% for (symbol, ty) in func_symbols -%}
FUNC_SYMBOL({{symbol}}, {{ty}})
{% endfor %}

char VISIBLE progname[] = "{{progname}}";
