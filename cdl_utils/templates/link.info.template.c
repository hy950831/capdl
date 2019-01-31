/* Generated file. Your changes will be overwritten. */
#include <capdl.h>

CDL_Link_Model capdl_link_spec = {
    .num = {{num}},

    .objects = (CDL_Link_Object[]) {

    {% for (from, to, index, size, base) in items -%}
    [{{index}}] = {
        .from = "{{from}}",
        .to = "{{to}}",
        .size = {{size}},
        .base = {{base}},
    },
    {% endfor %}

    },
};
