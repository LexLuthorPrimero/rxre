// Semantic patch to trace S_ADD_U32 decoding and translation path
// This finds where S_ADD_U32 is defined in opcode tables and where it's handled in translation

// Rule 1: Find S_ADD_U32 defined in opcode tables (Producer -> Decoding)
@@
  S_ADD_U32
@@
