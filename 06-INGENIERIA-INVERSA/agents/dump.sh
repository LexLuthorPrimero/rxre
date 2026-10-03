#!/bin/bash
K=/home/lucas/Escritorio/RX550-INVESTIGACION/RESEARCH/kernelbuild/linux-7.1.3
A=/var/tmp/rx550/agents
INC="-I$K/drivers/gpu/drm/amd/amdgpu -I$K/drivers/gpu/drm/amd/include -I$K/drivers/gpu/drm/amd/include/asic_reg/gca -I$K/drivers/gpu/drm/amd/include/asic_reg/gmc -I$K/drivers/gpu/drm/amd/include/asic_reg/oss -I$K/drivers/gpu/drm/amd/include/asic_reg/dce -I$K/include -I$K/arch/x86/include -I$K/arch/x86/include/generated -I$K/arch/x86/include/uapi -I$K/include/uapi -I$K/include/generated/uapi"
for f in "$@"; do
  out=$A/ast/$f.c.json
  clang -D__KERNEL__ -m64 -Xclang -ast-dump=json -fsyntax-only $INC $K/drivers/gpu/drm/amd/amdgpu/$f.c > $out.part 2> $A/ast/$f.err
  if python3 -c "import json,sys; json.load(open('$out.part'))" 2>/dev/null; then
     mv $out.part $out; echo "OK $f $(stat -c%s $out)"
  else
     echo "TRUNC $f $(stat -c%s $out.part)"; mv $out.part $out.bad
  fi
done
echo DONE_ALL
