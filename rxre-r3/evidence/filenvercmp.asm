
/usr/bin/ls:     formato del fichero elf64-x86-64


Desensamblado de la sección .text:

0000000000004fa0 <error_at_line@@Base+0x3c48>:
    4fa0:	55                   	push   rbp
    4fa1:	48 89 e5             	mov    rbp,rsp
    4fa4:	48 83 ec 50          	sub    rsp,0x50
    4fa8:	0f b6 17             	movzx  edx,BYTE PTR [rdi]
    4fab:	64 48 8b 04 25 28 00 	mov    rax,QWORD PTR fs:0x28
    4fb2:	00 00 
    4fb4:	48 89 45 e8          	mov    QWORD PTR [rbp-0x18],rax
    4fb8:	31 c0                	xor    eax,eax
    4fba:	48 c7 45 e0 ff ff ff 	mov    QWORD PTR [rbp-0x20],0xffffffffffffffff
    4fc1:	ff 
    4fc2:	0f b6 06             	movzx  eax,BYTE PTR [rsi]
    4fc5:	48 c7 45 d8 ff ff ff 	mov    QWORD PTR [rbp-0x28],0xffffffffffffffff
    4fcc:	ff 
    4fcd:	84 d2                	test   dl,dl
    4fcf:	0f 84 1b 01 00 00    	je     50f0 <error_at_line@@Base+0x3d98>
    4fd5:	84 c0                	test   al,al
    4fd7:	0f 84 f7 00 00 00    	je     50d4 <error_at_line@@Base+0x3d7c>
    4fdd:	48 89 5d f8          	mov    QWORD PTR [rbp-0x8],rbx
    4fe1:	49 89 f8             	mov    r8,rdi
    4fe4:	48 89 f3             	mov    rbx,rsi
    4fe7:	80 fa 2e             	cmp    dl,0x2e
    4fea:	0f 84 a0 00 00 00    	je     5090 <error_at_line@@Base+0x3d38>
    4ff0:	3c 2e                	cmp    al,0x2e
    4ff2:	0f 84 d8 00 00 00    	je     50d0 <error_at_line@@Base+0x3d78>
    4ff8:	4c 89 c7             	mov    rdi,r8
    4ffb:	48 8d 75 d8          	lea    rsi,[rbp-0x28]
    4fff:	4c 89 45 c8          	mov    QWORD PTR [rbp-0x38],r8
    5003:	41 bb 01 00 00 00    	mov    r11d,0x1
    5009:	e8 72 fa ff ff       	call   4a80 <error_at_line@@Base+0x3728>
    500e:	48 8d 75 e0          	lea    rsi,[rbp-0x20]
    5012:	48 89 df             	mov    rdi,rbx
    5015:	49 89 c2             	mov    r10,rax
    5018:	e8 63 fa ff ff       	call   4a80 <error_at_line@@Base+0x3728>
    501d:	4c 8b 4d d8          	mov    r9,QWORD PTR [rbp-0x28]
    5021:	4c 8b 45 c8          	mov    r8,QWORD PTR [rbp-0x38]
    5025:	4d 39 ca             	cmp    r10,r9
    5028:	0f 84 d2 00 00 00    	je     5100 <error_at_line@@Base+0x3da8>
    502e:	48 89 c1             	mov    rcx,rax
    5031:	48 89 da             	mov    rdx,rbx
    5034:	4c 89 d6             	mov    rsi,r10
    5037:	4c 89 c7             	mov    rdi,r8
    503a:	4c 89 4d b8          	mov    QWORD PTR [rbp-0x48],r9
    503e:	44 88 5d c8          	mov    BYTE PTR [rbp-0x38],r11b
    5042:	4c 89 45 c0          	mov    QWORD PTR [rbp-0x40],r8
    5046:	e8 15 fb ff ff       	call   4b60 <error_at_line@@Base+0x3808>
    504b:	85 c0                	test   eax,eax
    504d:	0f 85 bd 00 00 00    	jne    5110 <error_at_line@@Base+0x3db8>
    5053:	80 7d c8 00          	cmp    BYTE PTR [rbp-0x38],0x0
    5057:	0f 84 b3 00 00 00    	je     5110 <error_at_line@@Base+0x3db8>
    505d:	48 8b 45 e8          	mov    rax,QWORD PTR [rbp-0x18]
    5061:	64 48 2b 04 25 28 00 	sub    rax,QWORD PTR fs:0x28
    5068:	00 00 
    506a:	0f 85 de 00 00 00    	jne    514e <error_at_line@@Base+0x3df6>
    5070:	48 8b 4d e0          	mov    rcx,QWORD PTR [rbp-0x20]
    5074:	48 8b 75 b8          	mov    rsi,QWORD PTR [rbp-0x48]
    5078:	48 89 da             	mov    rdx,rbx
    507b:	48 8b 7d c0          	mov    rdi,QWORD PTR [rbp-0x40]
    507f:	48 8b 5d f8          	mov    rbx,QWORD PTR [rbp-0x8]
    5083:	c9                   	leave
    5084:	e9 d7 fa ff ff       	jmp    4b60 <error_at_line@@Base+0x3808>
    5089:	0f 1f 80 00 00 00 00 	nop    DWORD PTR [rax+0x0]
    5090:	3c 2e                	cmp    al,0x2e
    5092:	0f 85 98 00 00 00    	jne    5130 <error_at_line@@Base+0x3dd8>
    5098:	0f b6 57 01          	movzx  edx,BYTE PTR [rdi+0x1]
    509c:	0f b6 46 01          	movzx  eax,BYTE PTR [rsi+0x1]
    50a0:	84 d2                	test   dl,dl
    50a2:	0f 84 98 00 00 00    	je     5140 <error_at_line@@Base+0x3de8>
    50a8:	84 c0                	test   al,al
    50aa:	74 24                	je     50d0 <error_at_line@@Base+0x3d78>
    50ac:	80 fa 2e             	cmp    dl,0x2e
    50af:	74 6f                	je     5120 <error_at_line@@Base+0x3dc8>
    50b1:	3c 2e                	cmp    al,0x2e
    50b3:	0f 85 3f ff ff ff    	jne    4ff8 <error_at_line@@Base+0x3ca0>
    50b9:	80 7e 02 00          	cmp    BYTE PTR [rsi+0x2],0x0
    50bd:	0f 85 35 ff ff ff    	jne    4ff8 <error_at_line@@Base+0x3ca0>
    50c3:	66 90                	xchg   ax,ax
    50c5:	66 66 2e 0f 1f 84 00 	data16 cs nop WORD PTR [rax+rax*1+0x0]
    50cc:	00 00 00 00 
    50d0:	48 8b 5d f8          	mov    rbx,QWORD PTR [rbp-0x8]
    50d4:	b8 01 00 00 00       	mov    eax,0x1
    50d9:	48 8b 55 e8          	mov    rdx,QWORD PTR [rbp-0x18]
    50dd:	64 48 2b 14 25 28 00 	sub    rdx,QWORD PTR fs:0x28
    50e4:	00 00 
    50e6:	75 62                	jne    514a <error_at_line@@Base+0x3df2>
    50e8:	c9                   	leave
    50e9:	c3                   	ret
    50ea:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]
    50f0:	f6 d8                	neg    al
    50f2:	19 c0                	sbb    eax,eax
    50f4:	eb e3                	jmp    50d9 <error_at_line@@Base+0x3d81>
    50f6:	66 2e 0f 1f 84 00 00 	cs nop WORD PTR [rax+rax*1+0x0]
    50fd:	00 00 00 
    5100:	48 39 45 e0          	cmp    QWORD PTR [rbp-0x20],rax
    5104:	41 0f 95 c3          	setne  r11b
    5108:	e9 21 ff ff ff       	jmp    502e <error_at_line@@Base+0x3cd6>
    510d:	0f 1f 00             	nop    DWORD PTR [rax]
    5110:	48 8b 5d f8          	mov    rbx,QWORD PTR [rbp-0x8]
    5114:	eb c3                	jmp    50d9 <error_at_line@@Base+0x3d81>
    5116:	66 2e 0f 1f 84 00 00 	cs nop WORD PTR [rax+rax*1+0x0]
    511d:	00 00 00 
    5120:	0f b6 57 02          	movzx  edx,BYTE PTR [rdi+0x2]
    5124:	3c 2e                	cmp    al,0x2e
    5126:	74 2b                	je     5153 <error_at_line@@Base+0x3dfb>
    5128:	84 d2                	test   dl,dl
    512a:	0f 85 c8 fe ff ff    	jne    4ff8 <error_at_line@@Base+0x3ca0>
    5130:	48 8b 5d f8          	mov    rbx,QWORD PTR [rbp-0x8]
    5134:	b8 ff ff ff ff       	mov    eax,0xffffffff
    5139:	eb 9e                	jmp    50d9 <error_at_line@@Base+0x3d81>
    513b:	0f 1f 44 00 00       	nop    DWORD PTR [rax+rax*1+0x0]
    5140:	f6 d8                	neg    al
    5142:	48 8b 5d f8          	mov    rbx,QWORD PTR [rbp-0x8]
    5146:	19 c0                	sbb    eax,eax
    5148:	eb 8f                	jmp    50d9 <error_at_line@@Base+0x3d81>
    514a:	48 89 5d f8          	mov    QWORD PTR [rbp-0x8],rbx
    514e:	e8 8d ba ff ff       	call   be0 <__stack_chk_fail@plt>
    5153:	80 7e 02 00          	cmp    BYTE PTR [rsi+0x2],0x0
    5157:	75 cf                	jne    5128 <error_at_line@@Base+0x3dd0>
    5159:	31 c0                	xor    eax,eax
    515b:	84 d2                	test   dl,dl
    515d:	48 8b 5d f8          	mov    rbx,QWORD PTR [rbp-0x8]
    5161:	0f 95 c0             	setne  al
    5164:	e9 70 ff ff ff       	jmp    50d9 <error_at_line@@Base+0x3d81>
    5169:	0f 1f 80 00 00 00 00 	nop    DWORD PTR [rax+0x0]
    5170:	f3 0f 1e fa          	endbr64
    5174:	55                   	push   rbp
    5175:	48 89 e5             	mov    rbp,rsp
    5178:	41 54                	push   r12
    517a:	53                   	push   rbx
    517b:	48 8b 1e             	mov    rbx,QWORD PTR [rsi]
    517e:	4c                   	rex.WR
    517f:	8b                   	.byte 0x8b
