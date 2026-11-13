
/usr/bin/ls:     formato del fichero elf64-x86-64


Desensamblado de la sección .text:

0000000000004b60 <error_at_line@@Base+0x3808>:
    4b60:	55                   	push   rbp
    4b61:	49 89 d1             	mov    r9,rdx
    4b64:	49 89 f8             	mov    r8,rdi
    4b67:	31 d2                	xor    edx,edx
    4b69:	31 c0                	xor    eax,eax
    4b6b:	48 89 e5             	mov    rbp,rsp
    4b6e:	53                   	push   rbx
    4b6f:	48 39 f0             	cmp    rax,rsi
    4b72:	7c 1c                	jl     4b90 <error_at_line@@Base+0x3838>
    4b74:	48 39 ca             	cmp    rdx,rcx
    4b77:	0f 8d 52 03 00 00    	jge    4ecf <error_at_line@@Base+0x3b77>
    4b7d:	48 39 f0             	cmp    rax,rsi
    4b80:	0f 8d 90 00 00 00    	jge    4c16 <error_at_line@@Base+0x38be>
    4b86:	66 2e 0f 1f 84 00 00 	cs nop WORD PTR [rax+rax*1+0x0]
    4b8d:	00 00 00 
    4b90:	41 0f b6 3c 00       	movzx  edi,BYTE PTR [r8+rax*1]
    4b95:	44 0f be d7          	movsx  r10d,dil
    4b99:	41 83 ea 30          	sub    r10d,0x30
    4b9d:	41 83 fa 09          	cmp    r10d,0x9
    4ba1:	76 73                	jbe    4c16 <error_at_line@@Base+0x38be>
    4ba3:	40 80 ff 5a          	cmp    dil,0x5a
    4ba7:	0f 8f db 00 00 00    	jg     4c88 <error_at_line@@Base+0x3930>
    4bad:	40 80 ff 40          	cmp    dil,0x40
    4bb1:	0f 8f df 00 00 00    	jg     4c96 <error_at_line@@Base+0x393e>
    4bb7:	40 80 ff 7e          	cmp    dil,0x7e
    4bbb:	0f 84 57 03 00 00    	je     4f18 <error_at_line@@Base+0x3bc0>
    4bc1:	48 39 ca             	cmp    rdx,rcx
    4bc4:	0f 84 98 03 00 00    	je     4f62 <error_at_line@@Base+0x3c0a>
    4bca:	45 0f b6 1c 11       	movzx  r11d,BYTE PTR [r9+rdx*1]
    4bcf:	81 c7 00 01 00 00    	add    edi,0x100
    4bd5:	41 8d 5b d0          	lea    ebx,[r11-0x30]
    4bd9:	45 89 da             	mov    r10d,r11d
    4bdc:	83 fb 09             	cmp    ebx,0x9
    4bdf:	0f 86 94 00 00 00    	jbe    4c79 <error_at_line@@Base+0x3921>
    4be5:	41 80 fb 5a          	cmp    r11b,0x5a
    4be9:	0f 8f 59 02 00 00    	jg     4e48 <error_at_line@@Base+0x3af0>
    4bef:	41 80 fb 40          	cmp    r11b,0x40
    4bf3:	0f 8f 58 02 00 00    	jg     4e51 <error_at_line@@Base+0x3af9>
    4bf9:	45 8d 93 00 01 00 00 	lea    r10d,[r11+0x100]
    4c00:	41 39 fa             	cmp    r10d,edi
    4c03:	75 71                	jne    4c76 <error_at_line@@Base+0x391e>
    4c05:	48 83 c0 01          	add    rax,0x1
    4c09:	48 83 c2 01          	add    rdx,0x1
    4c0d:	48 39 f0             	cmp    rax,rsi
    4c10:	0f 8c 7a ff ff ff    	jl     4b90 <error_at_line@@Base+0x3838>
    4c16:	48 39 ca             	cmp    rdx,rcx
    4c19:	0f 8d 83 02 00 00    	jge    4ea2 <error_at_line@@Base+0x3b4a>
    4c1f:	45 0f b6 1c 11       	movzx  r11d,BYTE PTR [r9+rdx*1]
    4c24:	45 0f be d3          	movsx  r10d,r11b
    4c28:	41 8d 7a d0          	lea    edi,[r10-0x30]
    4c2c:	83 ff 09             	cmp    edi,0x9
    4c2f:	0f 86 a3 00 00 00    	jbe    4cd8 <error_at_line@@Base+0x3980>
    4c35:	48 39 f0             	cmp    rax,rsi
    4c38:	0f 84 98 02 00 00    	je     4ed6 <error_at_line@@Base+0x3b7e>
    4c3e:	41 0f b6 1c 00       	movzx  ebx,BYTE PTR [r8+rax*1]
    4c43:	89 df                	mov    edi,ebx
    4c45:	83 eb 30             	sub    ebx,0x30
    4c48:	83 fb 09             	cmp    ebx,0x9
    4c4b:	0f 87 52 ff ff ff    	ja     4ba3 <error_at_line@@Base+0x384b>
    4c51:	41 80 fb 5a          	cmp    r11b,0x5a
    4c55:	0f 8e 9d 01 00 00    	jle    4df8 <error_at_line@@Base+0x3aa0>
    4c5b:	41 8d 43 9f          	lea    eax,[r11-0x61]
    4c5f:	3c 19                	cmp    al,0x19
    4c61:	76 11                	jbe    4c74 <error_at_line@@Base+0x391c>
    4c63:	41 80 fb 7e          	cmp    r11b,0x7e
    4c67:	0f 84 23 03 00 00    	je     4f90 <error_at_line@@Base+0x3c38>
    4c6d:	45 8d 93 00 01 00 00 	lea    r10d,[r11+0x100]
    4c74:	31 ff                	xor    edi,edi
    4c76:	44 29 d7             	sub    edi,r10d
    4c79:	48 8b 5d f8          	mov    rbx,QWORD PTR [rbp-0x8]
    4c7d:	89 f8                	mov    eax,edi
    4c7f:	c9                   	leave
    4c80:	c3                   	ret
    4c81:	0f 1f 80 00 00 00 00 	nop    DWORD PTR [rax+0x0]
    4c88:	44 8d 57 9f          	lea    r10d,[rdi-0x61]
    4c8c:	41 80 fa 19          	cmp    r10b,0x19
    4c90:	0f 87 21 ff ff ff    	ja     4bb7 <error_at_line@@Base+0x385f>
    4c96:	40 0f be ff          	movsx  edi,dil
    4c9a:	48 39 ca             	cmp    rdx,rcx
    4c9d:	0f 84 ad 02 00 00    	je     4f50 <error_at_line@@Base+0x3bf8>
    4ca3:	45 0f b6 14 11       	movzx  r10d,BYTE PTR [r9+rdx*1]
    4ca8:	41 8d 5a d0          	lea    ebx,[r10-0x30]
    4cac:	45 89 d3             	mov    r11d,r10d
    4caf:	83 fb 09             	cmp    ebx,0x9
    4cb2:	76 c5                	jbe    4c79 <error_at_line@@Base+0x3921>
    4cb4:	41 80 fa 5a          	cmp    r10b,0x5a
    4cb8:	0f 8f a2 01 00 00    	jg     4e60 <error_at_line@@Base+0x3b08>
    4cbe:	41 80 fa 40          	cmp    r10b,0x40
    4cc2:	0f 8f a1 01 00 00    	jg     4e69 <error_at_line@@Base+0x3b11>
    4cc8:	41 81 c2 00 01 00 00 	add    r10d,0x100
    4ccf:	eb a5                	jmp    4c76 <error_at_line@@Base+0x391e>
    4cd1:	0f 1f 80 00 00 00 00 	nop    DWORD PTR [rax+0x0]
    4cd8:	48 39 f0             	cmp    rax,rsi
    4cdb:	7c 20                	jl     4cfd <error_at_line@@Base+0x39a5>
    4cdd:	e9 e6 00 00 00       	jmp    4dc8 <error_at_line@@Base+0x3a70>
    4ce2:	0f 1f 00             	nop    DWORD PTR [rax]
    4ce5:	66 66 2e 0f 1f 84 00 	data16 cs nop WORD PTR [rax+rax*1+0x0]
    4cec:	00 00 00 00 
    4cf0:	48 83 c0 01          	add    rax,0x1
    4cf4:	48 39 c6             	cmp    rsi,rax
    4cf7:	0f 84 cb 00 00 00    	je     4dc8 <error_at_line@@Base+0x3a70>
    4cfd:	41 80 3c 00 30       	cmp    BYTE PTR [r8+rax*1],0x30
    4d02:	74 ec                	je     4cf0 <error_at_line@@Base+0x3998>
    4d04:	48 39 ca             	cmp    rdx,rcx
    4d07:	7c 14                	jl     4d1d <error_at_line@@Base+0x39c5>
    4d09:	e9 a2 01 00 00       	jmp    4eb0 <error_at_line@@Base+0x3b58>
    4d0e:	66 90                	xchg   ax,ax
    4d10:	48 83 c2 01          	add    rdx,0x1
    4d14:	48 39 d1             	cmp    rcx,rdx
    4d17:	0f 84 ea 00 00 00    	je     4e07 <error_at_line@@Base+0x3aaf>
    4d1d:	41 80 3c 11 30       	cmp    BYTE PTR [r9+rdx*1],0x30
    4d22:	74 ec                	je     4d10 <error_at_line@@Base+0x39b8>
    4d24:	48 39 f0             	cmp    rax,rsi
    4d27:	41 0f 9c c2          	setl   r10b
    4d2b:	48 39 d1             	cmp    rcx,rdx
    4d2e:	40 0f 9f c7          	setg   dil
    4d32:	41 89 fb             	mov    r11d,edi
    4d35:	45 84 d2             	test   r10b,r10b
    4d38:	0f 84 dc 00 00 00    	je     4e1a <error_at_line@@Base+0x3ac2>
    4d3e:	40 84 ff             	test   dil,dil
    4d41:	0f 84 ca 00 00 00    	je     4e11 <error_at_line@@Base+0x3ab9>
    4d47:	31 ff                	xor    edi,edi
    4d49:	45 0f be 14 00       	movsx  r10d,BYTE PTR [r8+rax*1]
    4d4e:	45 8d 5a d0          	lea    r11d,[r10-0x30]
    4d52:	41 83 fb 09          	cmp    r11d,0x9
    4d56:	77 38                	ja     4d90 <error_at_line@@Base+0x3a38>
    4d58:	45 0f be 1c 11       	movsx  r11d,BYTE PTR [r9+rdx*1]
    4d5d:	41 8d 5b d0          	lea    ebx,[r11-0x30]
    4d61:	83 fb 09             	cmp    ebx,0x9
    4d64:	77 7a                	ja     4de0 <error_at_line@@Base+0x3a88>
    4d66:	45 29 da             	sub    r10d,r11d
    4d69:	85 ff                	test   edi,edi
    4d6b:	41 0f 44 fa          	cmove  edi,r10d
    4d6f:	48 83 c0 01          	add    rax,0x1
    4d73:	48 83 c2 01          	add    rdx,0x1
    4d77:	48 39 c6             	cmp    rsi,rax
    4d7a:	7e 28                	jle    4da4 <error_at_line@@Base+0x3a4c>
    4d7c:	48 39 d1             	cmp    rcx,rdx
    4d7f:	7f c8                	jg     4d49 <error_at_line@@Base+0x39f1>
    4d81:	0f 1f 40 00          	nop    DWORD PTR [rax+0x0]
    4d85:	66 66 2e 0f 1f 84 00 	data16 cs nop WORD PTR [rax+rax*1+0x0]
    4d8c:	00 00 00 00 
    4d90:	48 39 c6             	cmp    rsi,rax
    4d93:	7e 0f                	jle    4da4 <error_at_line@@Base+0x3a4c>
    4d95:	45 0f be 14 00       	movsx  r10d,BYTE PTR [r8+rax*1]
    4d9a:	41 83 ea 30          	sub    r10d,0x30
    4d9e:	41 83 fa 09          	cmp    r10d,0x9
    4da2:	76 41                	jbe    4de5 <error_at_line@@Base+0x3a8d>
    4da4:	48 39 d1             	cmp    rcx,rdx
    4da7:	7e 0f                	jle    4db8 <error_at_line@@Base+0x3a60>
    4da9:	45 0f be 14 11       	movsx  r10d,BYTE PTR [r9+rdx*1]
    4dae:	41 83 ea 30          	sub    r10d,0x30
    4db2:	41 83 fa 09          	cmp    r10d,0x9
    4db6:	76 7c                	jbe    4e34 <error_at_line@@Base+0x3adc>
    4db8:	85 ff                	test   edi,edi
    4dba:	0f 84 af fd ff ff    	je     4b6f <error_at_line@@Base+0x3817>
    4dc0:	e9 b4 fe ff ff       	jmp    4c79 <error_at_line@@Base+0x3921>
    4dc5:	0f 1f 00             	nop    DWORD PTR [rax]
    4dc8:	48 39 ca             	cmp    rdx,rcx
    4dcb:	0f 8c 4c ff ff ff    	jl     4d1d <error_at_line@@Base+0x39c5>
    4dd1:	e9 99 fd ff ff       	jmp    4b6f <error_at_line@@Base+0x3817>
    4dd6:	66 2e 0f 1f 84 00 00 	cs nop WORD PTR [rax+rax*1+0x0]
    4ddd:	00 00 00 
    4de0:	48 39 c6             	cmp    rsi,rax
    4de3:	7e bf                	jle    4da4 <error_at_line@@Base+0x3a4c>
    4de5:	bf 01 00 00 00       	mov    edi,0x1
    4dea:	48 8b 5d f8          	mov    rbx,QWORD PTR [rbp-0x8]
    4dee:	c9                   	leave
    4def:	89 f8                	mov    eax,edi
    4df1:	c3                   	ret
    4df2:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]
    4df8:	41 80 fb 40          	cmp    r11b,0x40
    4dfc:	0f 8f 72 fe ff ff    	jg     4c74 <error_at_line@@Base+0x391c>
    4e02:	e9 66 fe ff ff       	jmp    4c6d <error_at_line@@Base+0x3915>
    4e07:	48 39 f0             	cmp    rax,rsi
    4e0a:	41 0f 9c c2          	setl   r10b
    4e0e:	45 31 db             	xor    r11d,r11d
    4e11:	45 84 d2             	test   r10b,r10b
    4e14:	0f 85 9f 00 00 00    	jne    4eb9 <error_at_line@@Base+0x3b61>
    4e1a:	45 84 db             	test   r11b,r11b
    4e1d:	0f 84 4c fd ff ff    	je     4b6f <error_at_line@@Base+0x3817>
    4e23:	41 0f be 3c 11       	movsx  edi,BYTE PTR [r9+rdx*1]
    4e28:	83 ef 30             	sub    edi,0x30
    4e2b:	83 ff 09             	cmp    edi,0x9
    4e2e:	0f 87 3b fd ff ff    	ja     4b6f <error_at_line@@Base+0x3817>
    4e34:	bf ff ff ff ff       	mov    edi,0xffffffff
    4e39:	48 8b 5d f8          	mov    rbx,QWORD PTR [rbp-0x8]
    4e3d:	c9                   	leave
    4e3e:	89 f8                	mov    eax,edi
    4e40:	c3                   	ret
    4e41:	0f 1f 80 00 00 00 00 	nop    DWORD PTR [rax+0x0]
    4e48:	41 8d 5b 9f          	lea    ebx,[r11-0x61]
    4e4c:	80 fb 19             	cmp    bl,0x19
    4e4f:	77 21                	ja     4e72 <error_at_line@@Base+0x3b1a>
    4e51:	45 0f be d2          	movsx  r10d,r10b
    4e55:	e9 1c fe ff ff       	jmp    4c76 <error_at_line@@Base+0x391e>
    4e5a:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]
    4e60:	41 8d 5a 9f          	lea    ebx,[r10-0x61]
    4e64:	80 fb 19             	cmp    bl,0x19
    4e67:	77 27                	ja     4e90 <error_at_line@@Base+0x3b38>
    4e69:	45 0f be d3          	movsx  r10d,r11b
    4e6d:	e9 8e fd ff ff       	jmp    4c00 <error_at_line@@Base+0x38a8>
    4e72:	41 80 fb 7e          	cmp    r11b,0x7e
    4e76:	0f 85 7d fd ff ff    	jne    4bf9 <error_at_line@@Base+0x38a1>
    4e7c:	41 ba fe ff ff ff    	mov    r10d,0xfffffffe
    4e82:	e9 ef fd ff ff       	jmp    4c76 <error_at_line@@Base+0x391e>
    4e87:	66 0f 1f 84 00 00 00 	nop    WORD PTR [rax+rax*1+0x0]
    4e8e:	00 00 
    4e90:	41 80 fa 7e          	cmp    r10b,0x7e
    4e94:	74 e6                	je     4e7c <error_at_line@@Base+0x3b24>
    4e96:	41 81 c2 00 01 00 00 	add    r10d,0x100
    4e9d:	e9 d4 fd ff ff       	jmp    4c76 <error_at_line@@Base+0x391e>
    4ea2:	48 39 f0             	cmp    rax,rsi
    4ea5:	0f 8c 52 fe ff ff    	jl     4cfd <error_at_line@@Base+0x39a5>
    4eab:	e9 c4 fc ff ff       	jmp    4b74 <error_at_line@@Base+0x381c>
    4eb0:	48 39 c6             	cmp    rsi,rax
    4eb3:	0f 8e b6 fc ff ff    	jle    4b6f <error_at_line@@Base+0x3817>
    4eb9:	41 0f be 3c 00       	movsx  edi,BYTE PTR [r8+rax*1]
    4ebe:	83 ef 30             	sub    edi,0x30
    4ec1:	83 ff 09             	cmp    edi,0x9
    4ec4:	0f 87 a5 fc ff ff    	ja     4b6f <error_at_line@@Base+0x3817>
    4eca:	e9 16 ff ff ff       	jmp    4de5 <error_at_line@@Base+0x3a8d>
    4ecf:	31 ff                	xor    edi,edi
    4ed1:	e9 a3 fd ff ff       	jmp    4c79 <error_at_line@@Base+0x3921>
    4ed6:	41 80 fb 5a          	cmp    r11b,0x5a
    4eda:	7f 17                	jg     4ef3 <error_at_line@@Base+0x3b9b>
    4edc:	41 80 fb 40          	cmp    r11b,0x40
    4ee0:	7f 07                	jg     4ee9 <error_at_line@@Base+0x3b91>
    4ee2:	45 8d 93 00 01 00 00 	lea    r10d,[r11+0x100]
    4ee9:	bf ff ff ff ff       	mov    edi,0xffffffff
    4eee:	e9 83 fd ff ff       	jmp    4c76 <error_at_line@@Base+0x391e>
    4ef3:	41 8d 43 9f          	lea    eax,[r11-0x61]
    4ef7:	3c 19                	cmp    al,0x19
    4ef9:	76 ee                	jbe    4ee9 <error_at_line@@Base+0x3b91>
    4efb:	41 80 fb 7e          	cmp    r11b,0x7e
    4eff:	75 e1                	jne    4ee2 <error_at_line@@Base+0x3b8a>
    4f01:	bf ff ff ff ff       	mov    edi,0xffffffff
    4f06:	41 ba fe ff ff ff    	mov    r10d,0xfffffffe
    4f0c:	e9 65 fd ff ff       	jmp    4c76 <error_at_line@@Base+0x391e>
    4f11:	0f 1f 80 00 00 00 00 	nop    DWORD PTR [rax+0x0]
    4f18:	48 39 ca             	cmp    rdx,rcx
    4f1b:	0f 84 13 ff ff ff    	je     4e34 <error_at_line@@Base+0x3adc>
    4f21:	45 0f b6 14 11       	movzx  r10d,BYTE PTR [r9+rdx*1]
    4f26:	45 8d 5a d0          	lea    r11d,[r10-0x30]
    4f2a:	44 89 d7             	mov    edi,r10d
    4f2d:	41 83 fb 09          	cmp    r11d,0x9
    4f31:	76 25                	jbe    4f58 <error_at_line@@Base+0x3c00>
    4f33:	41 80 fa 5a          	cmp    r10b,0x5a
    4f37:	7f 42                	jg     4f7b <error_at_line@@Base+0x3c23>
    4f39:	41 80 fa 40          	cmp    r10b,0x40
    4f3d:	7f 2e                	jg     4f6d <error_at_line@@Base+0x3c15>
    4f3f:	41 81 c2 00 01 00 00 	add    r10d,0x100
    4f46:	bf fe ff ff ff       	mov    edi,0xfffffffe
    4f4b:	e9 26 fd ff ff       	jmp    4c76 <error_at_line@@Base+0x391e>
    4f50:	83 c7 01             	add    edi,0x1
    4f53:	e9 21 fd ff ff       	jmp    4c79 <error_at_line@@Base+0x3921>
    4f58:	bf fe ff ff ff       	mov    edi,0xfffffffe
    4f5d:	e9 17 fd ff ff       	jmp    4c79 <error_at_line@@Base+0x3921>
    4f62:	81 c7 01 01 00 00    	add    edi,0x101
    4f68:	e9 0c fd ff ff       	jmp    4c79 <error_at_line@@Base+0x3921>
    4f6d:	44 0f be d7          	movsx  r10d,dil
    4f71:	bf fe ff ff ff       	mov    edi,0xfffffffe
    4f76:	e9 fb fc ff ff       	jmp    4c76 <error_at_line@@Base+0x391e>
    4f7b:	45 8d 5a 9f          	lea    r11d,[r10-0x61]
    4f7f:	41 80 fb 19          	cmp    r11b,0x19
    4f83:	76 e8                	jbe    4f6d <error_at_line@@Base+0x3c15>
    4f85:	41 80 fa 7e          	cmp    r10b,0x7e
    4f89:	75 b4                	jne    4f3f <error_at_line@@Base+0x3be7>
    4f8b:	e9 75 fc ff ff       	jmp    4c05 <error_at_line@@Base+0x38ad>
    4f90:	31 ff                	xor    edi,edi
    4f92:	41 ba fe ff ff ff    	mov    r10d,0xfffffffe
    4f98:	e9 d9 fc ff ff       	jmp    4c76 <error_at_line@@Base+0x391e>
    4f9d:	0f 1f 00             	nop    DWORD PTR [rax]
