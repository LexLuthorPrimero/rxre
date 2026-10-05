"""DECLARACION CANDIDATA. No es una herramienta: es el DOC_LAYOUTS de
pm4_codec con los contratos de 1061, 1073, 1094 y 1106 aplicados.

Existe para poder MEDIR la reparacion sin tocar el fichero vivo, que es
de otra sesion. layoutcross --solo lo mide en aislamiento.
"""

DOC_LAYOUTS = {
    "PACKET3_CP_DMA": [
        "SRC_ADDR_LO | DATA",
        "CP_SYNC[31] | SRC_SEL[30:29] | ENGINE[27] | DST_SEL[21:20] | SRC_ADDR_HI[7:0]",
        "DST_ADDR_LO[31:0]",
        "DST_ADDR_HI[7:0]",
        "COMMAND[30:21] | BYTE_COUNT[20:0]"
    ],
    "PACKET3_DMA_DATA": [
        "CONTROL",
        "SRC_ADDR_LO | DATA",
        "SRC_ADDR_HI[31:0]",
        "DST_ADDR_LO[31:0]",
        "DST_ADDR_HI[7:0]",
        "COMMAND[30:21] | BYTE_COUNT[20:0]"
    ],
    "PACKET3_SET_RESOURCES": [
        "CONTROL[31:0]  (vmid_mask[15:0] | unmap_latency[23:16] | queue_type[31:29])",
        "QUEUE_MASK_LO[31:0]",
        "QUEUE_MASK_HI[31:0]",
        "GWS_MASK_LO[31:0]",
        "GWS_MASK_HI[31:0]",
        "OAC_MASK[15:0]",
        "GDS_HEAP_SIZE[16:11] | GDS_HEAP_BASE[5:0]"
    ],
    "PACKET3_MAP_QUEUES": [
        "CONTROL[31:0]  (queue_sel[5:4] | queue_type[23:21] | engine_sel[28:26] | num_queues[31:29])",
        "CONTROL2[31:0]  (check_disable[1] | doorbell_offset[25:2] | queue[28:26] | pipe[30:29] | me[31])",
        "MQD_ADDR_LO[31:0]",
        "MQD_ADDR_HI[31:0]",
        "WPTR_ADDR_LO[31:0]",
        "WPTR_ADDR_HI[31:0]"
    ],
    "PACKET3_UNMAP_QUEUES": [
        "CONTROL[31:0]  (action[1:0] | queue_sel[5:4] | engine_sel[28:26] | num_queues[31:29])",
        "DOORBELL_OFFSET0[22:2]",
        "dword[2]",
        "dword[3]",
        "dword[4]"
    ],
    "PACKET3_QUERY_STATUS": [
        "CONTROL / cadence",
        "CONTEXT_STATUS[21:12] | VMID[31:28]",
        "REGISTER_INDEX[23:0]",
        "STATUS_VALUE[31:0]",
        "dword[4]",
        "dword[5]"
    ],
    "PACKET3_RUN_CLEANER_SHADER": [
        "CLEANER_MODE / type"
    ]
}
