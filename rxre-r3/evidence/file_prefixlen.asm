
/usr/bin/ls:     formato del fichero elf64-x86-64


Desensamblado de la sección .text:

0000000000004a80 <error_at_line@@Base+0x3728>:
    4a80:	48 8b 0e             	mov    rcx,QWORD PTR [rsi]
    4a83:	49 89 f1             	mov    r9,rsi
    4a86:	31 c0                	xor    eax,eax
    4a88:	45 31 c0             	xor    r8d,r8d
    4a8b:	eb 08                	jmp    4a95 <error_at_line@@Base+0x373d>
    4a8d:	0f 1f 00             	nop    DWORD PTR [rax]
    4a90:	80 fa 40             	cmp    dl,0x40
    4a93:	7f 49                	jg     4ade <error_at_line@@Base+0x3786>
    4a95:	48 85 c9             	test   rcx,rcx
    4a98:	78 71                	js     4b0b <error_at_line@@Base+0x37b3>
    4a9a:	48 39 c1             	cmp    rcx,rax
    4a9d:	0f 84 a8 00 00 00    	je     4b4b <error_at_line@@Base+0x37f3>
    4aa3:	4c 8d 40 01          	lea    r8,[rax+0x1]
    4aa7:	48 83 c0 02          	add    rax,0x2
    4aab:	48 39 c8             	cmp    rax,rcx
    4aae:	0f 83 9e 00 00 00    	jae    4b52 <error_at_line@@Base+0x37fa>
    4ab4:	4c 89 c0             	mov    rax,r8
    4ab7:	66 0f 1f 84 00 00 00 	nop    WORD PTR [rax+rax*1+0x0]
    4abe:	00 00 
    4ac0:	80 3c 07 2e          	cmp    BYTE PTR [rdi+rax*1],0x2e
    4ac4:	75 cf                	jne    4a95 <error_at_line@@Base+0x373d>
    4ac6:	0f b6 54 07 01       	movzx  edx,BYTE PTR [rdi+rax*1+0x1]
    4acb:	80 fa 5a             	cmp    dl,0x5a
    4ace:	7e c0                	jle    4a90 <error_at_line@@Base+0x3738>
    4ad0:	8d 72 9f             	lea    esi,[rdx-0x61]
    4ad3:	40 80 fe 19          	cmp    sil,0x19
    4ad7:	76 05                	jbe    4ade <error_at_line@@Base+0x3786>
    4ad9:	80 fa 7e             	cmp    dl,0x7e
    4adc:	75 b7                	jne    4a95 <error_at_line@@Base+0x373d>
    4ade:	48 83 c0 02          	add    rax,0x2
    4ae2:	48 39 c8             	cmp    rax,rcx
    4ae5:	73 16                	jae    4afd <error_at_line@@Base+0x37a5>
    4ae7:	0f b6 14 07          	movzx  edx,BYTE PTR [rdi+rax*1]
    4aeb:	80 fa 5a             	cmp    dl,0x5a
    4aee:	7f 38                	jg     4b28 <error_at_line@@Base+0x37d0>
    4af0:	80 fa 40             	cmp    dl,0x40
    4af3:	7f 4b                	jg     4b40 <error_at_line@@Base+0x37e8>
    4af5:	83 ea 30             	sub    edx,0x30
    4af8:	80 fa 09             	cmp    dl,0x9
    4afb:	76 43                	jbe    4b40 <error_at_line@@Base+0x37e8>
    4afd:	48 8d 50 01          	lea    rdx,[rax+0x1]
    4b01:	48 39 ca             	cmp    rdx,rcx
    4b04:	72 ba                	jb     4ac0 <error_at_line@@Base+0x3768>
    4b06:	48 85 c9             	test   rcx,rcx
    4b09:	79 8f                	jns    4a9a <error_at_line@@Base+0x3742>
    4b0b:	80 3c 07 00          	cmp    BYTE PTR [rdi+rax*1],0x0
    4b0f:	74 3a                	je     4b4b <error_at_line@@Base+0x37f3>
    4b11:	4c 8d 40 01          	lea    r8,[rax+0x1]
    4b15:	48 83 c0 02          	add    rax,0x2
    4b19:	48 39 c8             	cmp    rax,rcx
    4b1c:	72 96                	jb     4ab4 <error_at_line@@Base+0x375c>
    4b1e:	4c 89 c0             	mov    rax,r8
    4b21:	eb e8                	jmp    4b0b <error_at_line@@Base+0x37b3>
    4b23:	0f 1f 44 00 00       	nop    DWORD PTR [rax+rax*1+0x0]
    4b28:	8d 72 9f             	lea    esi,[rdx-0x61]
    4b2b:	40 80 fe 19          	cmp    sil,0x19
    4b2f:	76 0f                	jbe    4b40 <error_at_line@@Base+0x37e8>
    4b31:	80 fa 7e             	cmp    dl,0x7e
    4b34:	75 c7                	jne    4afd <error_at_line@@Base+0x37a5>
    4b36:	66 2e 0f 1f 84 00 00 	cs nop WORD PTR [rax+rax*1+0x0]
    4b3d:	00 00 00 
    4b40:	48 83 c0 01          	add    rax,0x1
    4b44:	48 39 c8             	cmp    rax,rcx
    4b47:	72 9e                	jb     4ae7 <error_at_line@@Base+0x378f>
    4b49:	eb b2                	jmp    4afd <error_at_line@@Base+0x37a5>
    4b4b:	49 89 01             	mov    QWORD PTR [r9],rax
    4b4e:	4c 89 c0             	mov    rax,r8
    4b51:	c3                   	ret
    4b52:	4c 89 c0             	mov    rax,r8
    4b55:	e9 40 ff ff ff       	jmp    4a9a <error_at_line@@Base+0x3742>
    4b5a:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]
