#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>

#include "ppt_tipo.h"
int main(void){
    printf("sizeof(PPTable_t) = %zu\n", sizeof(PPTable_t));
    printf("sizeof(DpmDescriptor_t) = %zu\n", sizeof(DpmDescriptor_t));
    printf("sizeof(I2cControllerConfig_t) = %zu\n", sizeof(I2cControllerConfig_t));
    return 0;
}
