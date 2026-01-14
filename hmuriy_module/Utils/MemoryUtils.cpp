#include "MemoryUtils.h"
#include <link.h>
#include <string.h>
#include <stddef.h>

struct CallbackData {
    const char* lib_name;
    uintptr_t addr;
};

static int find_lib_callback(struct dl_phdr_info* info, size_t size, void* data) {
    CallbackData* cb_data = (CallbackData*)data;

    if (info->dlpi_name && strstr(info->dlpi_name, cb_data->lib_name)) {
        cb_data->addr = (uintptr_t)info->dlpi_addr;
        
        return 1;
    }

    return 0;
}

uintptr_t get_lib_addr(const char* lib_name) {
    CallbackData data;
    data.lib_name = lib_name;
    data.addr = 0;

    dl_iterate_phdr(find_lib_callback, &data);

    return data.addr;
}