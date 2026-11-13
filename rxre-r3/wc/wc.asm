
/usr/bin/wc:     formato del fichero elf64-x86-64


Desensamblado de la sección .init:

000000000000033c <.init>:
 33c:	f3 0f 1e fa          	endbr64
 340:	48 83 ec 08          	sub    rsp,0x8
 344:	48 8b 05 65 ec 00 00 	mov    rax,QWORD PTR [rip+0xec65]        # efb0 <__gmon_start__>
 34b:	48 85 c0             	test   rax,rax
 34e:	74 02                	je     352 <getenv@plt-0x46e>
 350:	ff d0                	call   rax
 352:	48 83 c4 08          	add    rsp,0x8
 356:	c3                   	ret

Desensamblado de la sección .plt:

0000000000000360 <.plt>:
 360:	ff 35 da e9 00 00    	push   QWORD PTR [rip+0xe9da]        # ed40 <error_at_line@@Base+0xddd7>
 366:	ff 25 dc e9 00 00    	jmp    QWORD PTR [rip+0xe9dc]        # ed48 <error_at_line@@Base+0xdddf>
 36c:	0f 1f 40 00          	nop    DWORD PTR [rax+0x0]
 370:	f3 0f 1e fa          	endbr64
 374:	68 00 00 00 00       	push   0x0
 379:	e9 e2 ff ff ff       	jmp    360 <getenv@plt-0x460>
 37e:	66 90                	xchg   ax,ax
 380:	f3 0f 1e fa          	endbr64
 384:	68 01 00 00 00       	push   0x1
 389:	e9 d2 ff ff ff       	jmp    360 <getenv@plt-0x460>
 38e:	66 90                	xchg   ax,ax
 390:	f3 0f 1e fa          	endbr64
 394:	68 02 00 00 00       	push   0x2
 399:	e9 c2 ff ff ff       	jmp    360 <getenv@plt-0x460>
 39e:	66 90                	xchg   ax,ax
 3a0:	f3 0f 1e fa          	endbr64
 3a4:	68 03 00 00 00       	push   0x3
 3a9:	e9 b2 ff ff ff       	jmp    360 <getenv@plt-0x460>
 3ae:	66 90                	xchg   ax,ax
 3b0:	f3 0f 1e fa          	endbr64
 3b4:	68 04 00 00 00       	push   0x4
 3b9:	e9 a2 ff ff ff       	jmp    360 <getenv@plt-0x460>
 3be:	66 90                	xchg   ax,ax
 3c0:	f3 0f 1e fa          	endbr64
 3c4:	68 05 00 00 00       	push   0x5
 3c9:	e9 92 ff ff ff       	jmp    360 <getenv@plt-0x460>
 3ce:	66 90                	xchg   ax,ax
 3d0:	f3 0f 1e fa          	endbr64
 3d4:	68 06 00 00 00       	push   0x6
 3d9:	e9 82 ff ff ff       	jmp    360 <getenv@plt-0x460>
 3de:	66 90                	xchg   ax,ax
 3e0:	f3 0f 1e fa          	endbr64
 3e4:	68 07 00 00 00       	push   0x7
 3e9:	e9 72 ff ff ff       	jmp    360 <getenv@plt-0x460>
 3ee:	66 90                	xchg   ax,ax
 3f0:	f3 0f 1e fa          	endbr64
 3f4:	68 08 00 00 00       	push   0x8
 3f9:	e9 62 ff ff ff       	jmp    360 <getenv@plt-0x460>
 3fe:	66 90                	xchg   ax,ax
 400:	f3 0f 1e fa          	endbr64
 404:	68 09 00 00 00       	push   0x9
 409:	e9 52 ff ff ff       	jmp    360 <getenv@plt-0x460>
 40e:	66 90                	xchg   ax,ax
 410:	f3 0f 1e fa          	endbr64
 414:	68 0a 00 00 00       	push   0xa
 419:	e9 42 ff ff ff       	jmp    360 <getenv@plt-0x460>
 41e:	66 90                	xchg   ax,ax
 420:	f3 0f 1e fa          	endbr64
 424:	68 0b 00 00 00       	push   0xb
 429:	e9 32 ff ff ff       	jmp    360 <getenv@plt-0x460>
 42e:	66 90                	xchg   ax,ax
 430:	f3 0f 1e fa          	endbr64
 434:	68 0c 00 00 00       	push   0xc
 439:	e9 22 ff ff ff       	jmp    360 <getenv@plt-0x460>
 43e:	66 90                	xchg   ax,ax
 440:	f3 0f 1e fa          	endbr64
 444:	68 0d 00 00 00       	push   0xd
 449:	e9 12 ff ff ff       	jmp    360 <getenv@plt-0x460>
 44e:	66 90                	xchg   ax,ax
 450:	f3 0f 1e fa          	endbr64
 454:	68 0e 00 00 00       	push   0xe
 459:	e9 02 ff ff ff       	jmp    360 <getenv@plt-0x460>
 45e:	66 90                	xchg   ax,ax
 460:	f3 0f 1e fa          	endbr64
 464:	68 0f 00 00 00       	push   0xf
 469:	e9 f2 fe ff ff       	jmp    360 <getenv@plt-0x460>
 46e:	66 90                	xchg   ax,ax
 470:	f3 0f 1e fa          	endbr64
 474:	68 10 00 00 00       	push   0x10
 479:	e9 e2 fe ff ff       	jmp    360 <getenv@plt-0x460>
 47e:	66 90                	xchg   ax,ax
 480:	f3 0f 1e fa          	endbr64
 484:	68 11 00 00 00       	push   0x11
 489:	e9 d2 fe ff ff       	jmp    360 <getenv@plt-0x460>
 48e:	66 90                	xchg   ax,ax
 490:	f3 0f 1e fa          	endbr64
 494:	68 12 00 00 00       	push   0x12
 499:	e9 c2 fe ff ff       	jmp    360 <getenv@plt-0x460>
 49e:	66 90                	xchg   ax,ax
 4a0:	f3 0f 1e fa          	endbr64
 4a4:	68 13 00 00 00       	push   0x13
 4a9:	e9 b2 fe ff ff       	jmp    360 <getenv@plt-0x460>
 4ae:	66 90                	xchg   ax,ax
 4b0:	f3 0f 1e fa          	endbr64
 4b4:	68 14 00 00 00       	push   0x14
 4b9:	e9 a2 fe ff ff       	jmp    360 <getenv@plt-0x460>
 4be:	66 90                	xchg   ax,ax
 4c0:	f3 0f 1e fa          	endbr64
 4c4:	68 15 00 00 00       	push   0x15
 4c9:	e9 92 fe ff ff       	jmp    360 <getenv@plt-0x460>
 4ce:	66 90                	xchg   ax,ax
 4d0:	f3 0f 1e fa          	endbr64
 4d4:	68 16 00 00 00       	push   0x16
 4d9:	e9 82 fe ff ff       	jmp    360 <getenv@plt-0x460>
 4de:	66 90                	xchg   ax,ax
 4e0:	f3 0f 1e fa          	endbr64
 4e4:	68 17 00 00 00       	push   0x17
 4e9:	e9 72 fe ff ff       	jmp    360 <getenv@plt-0x460>
 4ee:	66 90                	xchg   ax,ax
 4f0:	f3 0f 1e fa          	endbr64
 4f4:	68 18 00 00 00       	push   0x18
 4f9:	e9 62 fe ff ff       	jmp    360 <getenv@plt-0x460>
 4fe:	66 90                	xchg   ax,ax
 500:	f3 0f 1e fa          	endbr64
 504:	68 19 00 00 00       	push   0x19
 509:	e9 52 fe ff ff       	jmp    360 <getenv@plt-0x460>
 50e:	66 90                	xchg   ax,ax
 510:	f3 0f 1e fa          	endbr64
 514:	68 1a 00 00 00       	push   0x1a
 519:	e9 42 fe ff ff       	jmp    360 <getenv@plt-0x460>
 51e:	66 90                	xchg   ax,ax
 520:	f3 0f 1e fa          	endbr64
 524:	68 1b 00 00 00       	push   0x1b
 529:	e9 32 fe ff ff       	jmp    360 <getenv@plt-0x460>
 52e:	66 90                	xchg   ax,ax
 530:	f3 0f 1e fa          	endbr64
 534:	68 1c 00 00 00       	push   0x1c
 539:	e9 22 fe ff ff       	jmp    360 <getenv@plt-0x460>
 53e:	66 90                	xchg   ax,ax
 540:	f3 0f 1e fa          	endbr64
 544:	68 1d 00 00 00       	push   0x1d
 549:	e9 12 fe ff ff       	jmp    360 <getenv@plt-0x460>
 54e:	66 90                	xchg   ax,ax
 550:	f3 0f 1e fa          	endbr64
 554:	68 1e 00 00 00       	push   0x1e
 559:	e9 02 fe ff ff       	jmp    360 <getenv@plt-0x460>
 55e:	66 90                	xchg   ax,ax
 560:	f3 0f 1e fa          	endbr64
 564:	68 1f 00 00 00       	push   0x1f
 569:	e9 f2 fd ff ff       	jmp    360 <getenv@plt-0x460>
 56e:	66 90                	xchg   ax,ax
 570:	f3 0f 1e fa          	endbr64
 574:	68 20 00 00 00       	push   0x20
 579:	e9 e2 fd ff ff       	jmp    360 <getenv@plt-0x460>
 57e:	66 90                	xchg   ax,ax
 580:	f3 0f 1e fa          	endbr64
 584:	68 21 00 00 00       	push   0x21
 589:	e9 d2 fd ff ff       	jmp    360 <getenv@plt-0x460>
 58e:	66 90                	xchg   ax,ax
 590:	f3 0f 1e fa          	endbr64
 594:	68 22 00 00 00       	push   0x22
 599:	e9 c2 fd ff ff       	jmp    360 <getenv@plt-0x460>
 59e:	66 90                	xchg   ax,ax
 5a0:	f3 0f 1e fa          	endbr64
 5a4:	68 23 00 00 00       	push   0x23
 5a9:	e9 b2 fd ff ff       	jmp    360 <getenv@plt-0x460>
 5ae:	66 90                	xchg   ax,ax
 5b0:	f3 0f 1e fa          	endbr64
 5b4:	68 24 00 00 00       	push   0x24
 5b9:	e9 a2 fd ff ff       	jmp    360 <getenv@plt-0x460>
 5be:	66 90                	xchg   ax,ax
 5c0:	f3 0f 1e fa          	endbr64
 5c4:	68 25 00 00 00       	push   0x25
 5c9:	e9 92 fd ff ff       	jmp    360 <getenv@plt-0x460>
 5ce:	66 90                	xchg   ax,ax
 5d0:	f3 0f 1e fa          	endbr64
 5d4:	68 26 00 00 00       	push   0x26
 5d9:	e9 82 fd ff ff       	jmp    360 <getenv@plt-0x460>
 5de:	66 90                	xchg   ax,ax
 5e0:	f3 0f 1e fa          	endbr64
 5e4:	68 27 00 00 00       	push   0x27
 5e9:	e9 72 fd ff ff       	jmp    360 <getenv@plt-0x460>
 5ee:	66 90                	xchg   ax,ax
 5f0:	f3 0f 1e fa          	endbr64
 5f4:	68 28 00 00 00       	push   0x28
 5f9:	e9 62 fd ff ff       	jmp    360 <getenv@plt-0x460>
 5fe:	66 90                	xchg   ax,ax
 600:	f3 0f 1e fa          	endbr64
 604:	68 29 00 00 00       	push   0x29
 609:	e9 52 fd ff ff       	jmp    360 <getenv@plt-0x460>
 60e:	66 90                	xchg   ax,ax
 610:	f3 0f 1e fa          	endbr64
 614:	68 2a 00 00 00       	push   0x2a
 619:	e9 42 fd ff ff       	jmp    360 <getenv@plt-0x460>
 61e:	66 90                	xchg   ax,ax
 620:	f3 0f 1e fa          	endbr64
 624:	68 2b 00 00 00       	push   0x2b
 629:	e9 32 fd ff ff       	jmp    360 <getenv@plt-0x460>
 62e:	66 90                	xchg   ax,ax
 630:	f3 0f 1e fa          	endbr64
 634:	68 2c 00 00 00       	push   0x2c
 639:	e9 22 fd ff ff       	jmp    360 <getenv@plt-0x460>
 63e:	66 90                	xchg   ax,ax
 640:	f3 0f 1e fa          	endbr64
 644:	68 2d 00 00 00       	push   0x2d
 649:	e9 12 fd ff ff       	jmp    360 <getenv@plt-0x460>
 64e:	66 90                	xchg   ax,ax
 650:	f3 0f 1e fa          	endbr64
 654:	68 2e 00 00 00       	push   0x2e
 659:	e9 02 fd ff ff       	jmp    360 <getenv@plt-0x460>
 65e:	66 90                	xchg   ax,ax
 660:	f3 0f 1e fa          	endbr64
 664:	68 2f 00 00 00       	push   0x2f
 669:	e9 f2 fc ff ff       	jmp    360 <getenv@plt-0x460>
 66e:	66 90                	xchg   ax,ax
 670:	f3 0f 1e fa          	endbr64
 674:	68 30 00 00 00       	push   0x30
 679:	e9 e2 fc ff ff       	jmp    360 <getenv@plt-0x460>
 67e:	66 90                	xchg   ax,ax
 680:	f3 0f 1e fa          	endbr64
 684:	68 31 00 00 00       	push   0x31
 689:	e9 d2 fc ff ff       	jmp    360 <getenv@plt-0x460>
 68e:	66 90                	xchg   ax,ax
 690:	f3 0f 1e fa          	endbr64
 694:	68 32 00 00 00       	push   0x32
 699:	e9 c2 fc ff ff       	jmp    360 <getenv@plt-0x460>
 69e:	66 90                	xchg   ax,ax
 6a0:	f3 0f 1e fa          	endbr64
 6a4:	68 33 00 00 00       	push   0x33
 6a9:	e9 b2 fc ff ff       	jmp    360 <getenv@plt-0x460>
 6ae:	66 90                	xchg   ax,ax
 6b0:	f3 0f 1e fa          	endbr64
 6b4:	68 34 00 00 00       	push   0x34
 6b9:	e9 a2 fc ff ff       	jmp    360 <getenv@plt-0x460>
 6be:	66 90                	xchg   ax,ax
 6c0:	f3 0f 1e fa          	endbr64
 6c4:	68 35 00 00 00       	push   0x35
 6c9:	e9 92 fc ff ff       	jmp    360 <getenv@plt-0x460>
 6ce:	66 90                	xchg   ax,ax
 6d0:	f3 0f 1e fa          	endbr64
 6d4:	68 36 00 00 00       	push   0x36
 6d9:	e9 82 fc ff ff       	jmp    360 <getenv@plt-0x460>
 6de:	66 90                	xchg   ax,ax
 6e0:	f3 0f 1e fa          	endbr64
 6e4:	68 37 00 00 00       	push   0x37
 6e9:	e9 72 fc ff ff       	jmp    360 <getenv@plt-0x460>
 6ee:	66 90                	xchg   ax,ax
 6f0:	f3 0f 1e fa          	endbr64
 6f4:	68 38 00 00 00       	push   0x38
 6f9:	e9 62 fc ff ff       	jmp    360 <getenv@plt-0x460>
 6fe:	66 90                	xchg   ax,ax
 700:	f3 0f 1e fa          	endbr64
 704:	68 39 00 00 00       	push   0x39
 709:	e9 52 fc ff ff       	jmp    360 <getenv@plt-0x460>
 70e:	66 90                	xchg   ax,ax
 710:	f3 0f 1e fa          	endbr64
 714:	68 3a 00 00 00       	push   0x3a
 719:	e9 42 fc ff ff       	jmp    360 <getenv@plt-0x460>
 71e:	66 90                	xchg   ax,ax
 720:	f3 0f 1e fa          	endbr64
 724:	68 3b 00 00 00       	push   0x3b
 729:	e9 32 fc ff ff       	jmp    360 <getenv@plt-0x460>
 72e:	66 90                	xchg   ax,ax
 730:	f3 0f 1e fa          	endbr64
 734:	68 3c 00 00 00       	push   0x3c
 739:	e9 22 fc ff ff       	jmp    360 <getenv@plt-0x460>
 73e:	66 90                	xchg   ax,ax
 740:	f3 0f 1e fa          	endbr64
 744:	68 3d 00 00 00       	push   0x3d
 749:	e9 12 fc ff ff       	jmp    360 <getenv@plt-0x460>
 74e:	66 90                	xchg   ax,ax
 750:	f3 0f 1e fa          	endbr64
 754:	68 3e 00 00 00       	push   0x3e
 759:	e9 02 fc ff ff       	jmp    360 <getenv@plt-0x460>
 75e:	66 90                	xchg   ax,ax
 760:	f3 0f 1e fa          	endbr64
 764:	68 3f 00 00 00       	push   0x3f
 769:	e9 f2 fb ff ff       	jmp    360 <getenv@plt-0x460>
 76e:	66 90                	xchg   ax,ax
 770:	f3 0f 1e fa          	endbr64
 774:	68 40 00 00 00       	push   0x40
 779:	e9 e2 fb ff ff       	jmp    360 <getenv@plt-0x460>
 77e:	66 90                	xchg   ax,ax
 780:	f3 0f 1e fa          	endbr64
 784:	68 41 00 00 00       	push   0x41
 789:	e9 d2 fb ff ff       	jmp    360 <getenv@plt-0x460>
 78e:	66 90                	xchg   ax,ax
 790:	f3 0f 1e fa          	endbr64
 794:	68 42 00 00 00       	push   0x42
 799:	e9 c2 fb ff ff       	jmp    360 <getenv@plt-0x460>
 79e:	66 90                	xchg   ax,ax
 7a0:	f3 0f 1e fa          	endbr64
 7a4:	68 43 00 00 00       	push   0x43
 7a9:	e9 b2 fb ff ff       	jmp    360 <getenv@plt-0x460>
 7ae:	66 90                	xchg   ax,ax
 7b0:	f3 0f 1e fa          	endbr64
 7b4:	68 44 00 00 00       	push   0x44
 7b9:	e9 a2 fb ff ff       	jmp    360 <getenv@plt-0x460>
 7be:	66 90                	xchg   ax,ax

Desensamblado de la sección .plt.sec:

00000000000007c0 <getenv@plt>:
 7c0:	f3 0f 1e fa          	endbr64
 7c4:	ff 25 86 e5 00 00    	jmp    QWORD PTR [rip+0xe586]        # ed50 <getenv@GLIBC_2.2.5>
 7ca:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

00000000000007d0 <free@plt>:
 7d0:	f3 0f 1e fa          	endbr64
 7d4:	ff 25 7e e5 00 00    	jmp    QWORD PTR [rip+0xe57e]        # ed58 <free@GLIBC_2.2.5>
 7da:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

00000000000007e0 <__vfprintf_chk@plt>:
 7e0:	f3 0f 1e fa          	endbr64
 7e4:	ff 25 76 e5 00 00    	jmp    QWORD PTR [rip+0xe576]        # ed60 <__vfprintf_chk@GLIBC_2.3.4>
 7ea:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

00000000000007f0 <abort@plt>:
 7f0:	f3 0f 1e fa          	endbr64
 7f4:	ff 25 6e e5 00 00    	jmp    QWORD PTR [rip+0xe56e]        # ed68 <abort@GLIBC_2.2.5>
 7fa:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000800 <__errno_location@plt>:
 800:	f3 0f 1e fa          	endbr64
 804:	ff 25 66 e5 00 00    	jmp    QWORD PTR [rip+0xe566]        # ed70 <__errno_location@GLIBC_2.2.5>
 80a:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000810 <strncmp@plt>:
 810:	f3 0f 1e fa          	endbr64
 814:	ff 25 5e e5 00 00    	jmp    QWORD PTR [rip+0xe55e]        # ed78 <strncmp@GLIBC_2.2.5>
 81a:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000820 <_exit@plt>:
 820:	f3 0f 1e fa          	endbr64
 824:	ff 25 56 e5 00 00    	jmp    QWORD PTR [rip+0xe556]        # ed80 <_exit@GLIBC_2.2.5>
 82a:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000830 <__fpending@plt>:
 830:	f3 0f 1e fa          	endbr64
 834:	ff 25 4e e5 00 00    	jmp    QWORD PTR [rip+0xe54e]        # ed88 <__fpending@GLIBC_2.2.5>
 83a:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000840 <__read_chk@plt>:
 840:	f3 0f 1e fa          	endbr64
 844:	ff 25 46 e5 00 00    	jmp    QWORD PTR [rip+0xe546]        # ed90 <__read_chk@GLIBC_2.4>
 84a:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000850 <ferror@plt>:
 850:	f3 0f 1e fa          	endbr64
 854:	ff 25 3e e5 00 00    	jmp    QWORD PTR [rip+0xe53e]        # ed98 <ferror@GLIBC_2.2.5>
 85a:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000860 <fcntl@plt>:
 860:	f3 0f 1e fa          	endbr64
 864:	ff 25 36 e5 00 00    	jmp    QWORD PTR [rip+0xe536]        # eda0 <fcntl@GLIBC_2.2.5>
 86a:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000870 <clearerr_unlocked@plt>:
 870:	f3 0f 1e fa          	endbr64
 874:	ff 25 2e e5 00 00    	jmp    QWORD PTR [rip+0xe52e]        # eda8 <clearerr_unlocked@GLIBC_2.2.5>
 87a:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000880 <__fpurge@plt>:
 880:	f3 0f 1e fa          	endbr64
 884:	ff 25 26 e5 00 00    	jmp    QWORD PTR [rip+0xe526]        # edb0 <__fpurge@GLIBC_2.2.5>
 88a:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000890 <textdomain@plt>:
 890:	f3 0f 1e fa          	endbr64
 894:	ff 25 1e e5 00 00    	jmp    QWORD PTR [rip+0xe51e]        # edb8 <textdomain@GLIBC_2.2.5>
 89a:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

00000000000008a0 <fclose@plt>:
 8a0:	f3 0f 1e fa          	endbr64
 8a4:	ff 25 16 e5 00 00    	jmp    QWORD PTR [rip+0xe516]        # edc0 <fclose@GLIBC_2.2.5>
 8aa:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

00000000000008b0 <bindtextdomain@plt>:
 8b0:	f3 0f 1e fa          	endbr64
 8b4:	ff 25 0e e5 00 00    	jmp    QWORD PTR [rip+0xe50e]        # edc8 <bindtextdomain@GLIBC_2.2.5>
 8ba:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

00000000000008c0 <dcgettext@plt>:
 8c0:	f3 0f 1e fa          	endbr64
 8c4:	ff 25 06 e5 00 00    	jmp    QWORD PTR [rip+0xe506]        # edd0 <dcgettext@GLIBC_2.2.5>
 8ca:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

00000000000008d0 <__ctype_get_mb_cur_max@plt>:
 8d0:	f3 0f 1e fa          	endbr64
 8d4:	ff 25 fe e4 00 00    	jmp    QWORD PTR [rip+0xe4fe]        # edd8 <__ctype_get_mb_cur_max@GLIBC_2.2.5>
 8da:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

00000000000008e0 <strlen@plt>:
 8e0:	f3 0f 1e fa          	endbr64
 8e4:	ff 25 f6 e4 00 00    	jmp    QWORD PTR [rip+0xe4f6]        # ede0 <strlen@GLIBC_2.2.5>
 8ea:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

00000000000008f0 <__stack_chk_fail@plt>:
 8f0:	f3 0f 1e fa          	endbr64
 8f4:	ff 25 ee e4 00 00    	jmp    QWORD PTR [rip+0xe4ee]        # ede8 <__stack_chk_fail@GLIBC_2.4>
 8fa:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000900 <getopt_long@plt>:
 900:	f3 0f 1e fa          	endbr64
 904:	ff 25 e6 e4 00 00    	jmp    QWORD PTR [rip+0xe4e6]        # edf0 <getopt_long@GLIBC_2.2.5>
 90a:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000910 <mbrtowc@plt>:
 910:	f3 0f 1e fa          	endbr64
 914:	ff 25 de e4 00 00    	jmp    QWORD PTR [rip+0xe4de]        # edf8 <mbrtowc@GLIBC_2.2.5>
 91a:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000920 <strchr@plt>:
 920:	f3 0f 1e fa          	endbr64
 924:	ff 25 d6 e4 00 00    	jmp    QWORD PTR [rip+0xe4d6]        # ee00 <strchr@GLIBC_2.2.5>
 92a:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000930 <__overflow@plt>:
 930:	f3 0f 1e fa          	endbr64
 934:	ff 25 ce e4 00 00    	jmp    QWORD PTR [rip+0xe4ce]        # ee08 <__overflow@GLIBC_2.2.5>
 93a:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000940 <strrchr@plt>:
 940:	f3 0f 1e fa          	endbr64
 944:	ff 25 c6 e4 00 00    	jmp    QWORD PTR [rip+0xe4c6]        # ee10 <strrchr@GLIBC_2.2.5>
 94a:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000950 <lseek@plt>:
 950:	f3 0f 1e fa          	endbr64
 954:	ff 25 be e4 00 00    	jmp    QWORD PTR [rip+0xe4be]        # ee18 <lseek@GLIBC_2.2.5>
 95a:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000960 <fileno_unlocked@plt>:
 960:	f3 0f 1e fa          	endbr64
 964:	ff 25 b6 e4 00 00    	jmp    QWORD PTR [rip+0xe4b6]        # ee20 <fileno_unlocked@GLIBC_2.2.5>
 96a:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000970 <fgetc@plt>:
 970:	f3 0f 1e fa          	endbr64
 974:	ff 25 ae e4 00 00    	jmp    QWORD PTR [rip+0xe4ae]        # ee28 <fgetc@GLIBC_2.2.5>
 97a:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000980 <close@plt>:
 980:	f3 0f 1e fa          	endbr64
 984:	ff 25 a6 e4 00 00    	jmp    QWORD PTR [rip+0xe4a6]        # ee30 <close@GLIBC_2.2.5>
 98a:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000990 <mbrtoc32@plt>:
 990:	f3 0f 1e fa          	endbr64
 994:	ff 25 9e e4 00 00    	jmp    QWORD PTR [rip+0xe49e]        # ee38 <mbrtoc32@GLIBC_2.16>
 99a:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

00000000000009a0 <strspn@plt>:
 9a0:	f3 0f 1e fa          	endbr64
 9a4:	ff 25 96 e4 00 00    	jmp    QWORD PTR [rip+0xe496]        # ee40 <strspn@GLIBC_2.2.5>
 9aa:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

00000000000009b0 <posix_fadvise@plt>:
 9b0:	f3 0f 1e fa          	endbr64
 9b4:	ff 25 8e e4 00 00    	jmp    QWORD PTR [rip+0xe48e]        # ee48 <posix_fadvise@GLIBC_2.2.5>
 9ba:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

00000000000009c0 <strcspn@plt>:
 9c0:	f3 0f 1e fa          	endbr64
 9c4:	ff 25 86 e4 00 00    	jmp    QWORD PTR [rip+0xe486]        # ee50 <strcspn@GLIBC_2.2.5>
 9ca:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

00000000000009d0 <read@plt>:
 9d0:	f3 0f 1e fa          	endbr64
 9d4:	ff 25 7e e4 00 00    	jmp    QWORD PTR [rip+0xe47e]        # ee58 <read@GLIBC_2.2.5>
 9da:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

00000000000009e0 <memcmp@plt>:
 9e0:	f3 0f 1e fa          	endbr64
 9e4:	ff 25 76 e4 00 00    	jmp    QWORD PTR [rip+0xe476]        # ee60 <memcmp@GLIBC_2.2.5>
 9ea:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

00000000000009f0 <fputs_unlocked@plt>:
 9f0:	f3 0f 1e fa          	endbr64
 9f4:	ff 25 6e e4 00 00    	jmp    QWORD PTR [rip+0xe46e]        # ee68 <fputs_unlocked@GLIBC_2.2.5>
 9fa:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000a00 <rawmemchr@plt>:
 a00:	f3 0f 1e fa          	endbr64
 a04:	ff 25 66 e4 00 00    	jmp    QWORD PTR [rip+0xe466]        # ee70 <rawmemchr@GLIBC_2.2.5>
 a0a:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000a10 <strcmp@plt>:
 a10:	f3 0f 1e fa          	endbr64
 a14:	ff 25 5e e4 00 00    	jmp    QWORD PTR [rip+0xe45e]        # ee78 <strcmp@GLIBC_2.2.5>
 a1a:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000a20 <fputc_unlocked@plt>:
 a20:	f3 0f 1e fa          	endbr64
 a24:	ff 25 56 e4 00 00    	jmp    QWORD PTR [rip+0xe456]        # ee80 <fputc_unlocked@GLIBC_2.2.5>
 a2a:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000a30 <__memmove_chk@plt>:
 a30:	f3 0f 1e fa          	endbr64
 a34:	ff 25 4e e4 00 00    	jmp    QWORD PTR [rip+0xe44e]        # ee88 <__memmove_chk@GLIBC_2.3.4>
 a3a:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000a40 <feof@plt>:
 a40:	f3 0f 1e fa          	endbr64
 a44:	ff 25 46 e4 00 00    	jmp    QWORD PTR [rip+0xe446]        # ee90 <feof@GLIBC_2.2.5>
 a4a:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000a50 <stat@plt>:
 a50:	f3 0f 1e fa          	endbr64
 a54:	ff 25 3e e4 00 00    	jmp    QWORD PTR [rip+0xe43e]        # ee98 <stat@GLIBC_2.33>
 a5a:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000a60 <memcpy@plt>:
 a60:	f3 0f 1e fa          	endbr64
 a64:	ff 25 36 e4 00 00    	jmp    QWORD PTR [rip+0xe436]        # eea0 <memcpy@GLIBC_2.14>
 a6a:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000a70 <strerror_r@plt>:
 a70:	f3 0f 1e fa          	endbr64
 a74:	ff 25 2e e4 00 00    	jmp    QWORD PTR [rip+0xe42e]        # eea8 <strerror_r@GLIBC_2.2.5>
 a7a:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000a80 <wcwidth@plt>:
 a80:	f3 0f 1e fa          	endbr64
 a84:	ff 25 26 e4 00 00    	jmp    QWORD PTR [rip+0xe426]        # eeb0 <wcwidth@GLIBC_2.2.5>
 a8a:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000a90 <malloc@plt>:
 a90:	f3 0f 1e fa          	endbr64
 a94:	ff 25 1e e4 00 00    	jmp    QWORD PTR [rip+0xe41e]        # eeb8 <malloc@GLIBC_2.2.5>
 a9a:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000aa0 <fwrite_unlocked@plt>:
 aa0:	f3 0f 1e fa          	endbr64
 aa4:	ff 25 16 e4 00 00    	jmp    QWORD PTR [rip+0xe416]        # eec0 <fwrite_unlocked@GLIBC_2.2.5>
 aaa:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000ab0 <realloc@plt>:
 ab0:	f3 0f 1e fa          	endbr64
 ab4:	ff 25 0e e4 00 00    	jmp    QWORD PTR [rip+0xe40e]        # eec8 <realloc@GLIBC_2.2.5>
 aba:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000ac0 <setlocale@plt>:
 ac0:	f3 0f 1e fa          	endbr64
 ac4:	ff 25 06 e4 00 00    	jmp    QWORD PTR [rip+0xe406]        # eed0 <setlocale@GLIBC_2.2.5>
 aca:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000ad0 <__printf_chk@plt>:
 ad0:	f3 0f 1e fa          	endbr64
 ad4:	ff 25 fe e3 00 00    	jmp    QWORD PTR [rip+0xe3fe]        # eed8 <__printf_chk@GLIBC_2.3.4>
 ada:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000ae0 <setvbuf@plt>:
 ae0:	f3 0f 1e fa          	endbr64
 ae4:	ff 25 f6 e3 00 00    	jmp    QWORD PTR [rip+0xe3f6]        # eee0 <setvbuf@GLIBC_2.2.5>
 aea:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000af0 <iswspace@plt>:
 af0:	f3 0f 1e fa          	endbr64
 af4:	ff 25 ee e3 00 00    	jmp    QWORD PTR [rip+0xe3ee]        # eee8 <iswspace@GLIBC_2.2.5>
 afa:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000b00 <open@plt>:
 b00:	f3 0f 1e fa          	endbr64
 b04:	ff 25 e6 e3 00 00    	jmp    QWORD PTR [rip+0xe3e6]        # eef0 <open@GLIBC_2.2.5>
 b0a:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000b10 <fopen@plt>:
 b10:	f3 0f 1e fa          	endbr64
 b14:	ff 25 de e3 00 00    	jmp    QWORD PTR [rip+0xe3de]        # eef8 <fopen@GLIBC_2.2.5>
 b1a:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000b20 <sysconf@plt>:
 b20:	f3 0f 1e fa          	endbr64
 b24:	ff 25 d6 e3 00 00    	jmp    QWORD PTR [rip+0xe3d6]        # ef00 <sysconf@GLIBC_2.2.5>
 b2a:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000b30 <__cxa_atexit@plt>:
 b30:	f3 0f 1e fa          	endbr64
 b34:	ff 25 ce e3 00 00    	jmp    QWORD PTR [rip+0xe3ce]        # ef08 <__cxa_atexit@GLIBC_2.2.5>
 b3a:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000b40 <sysinfo@plt>:
 b40:	f3 0f 1e fa          	endbr64
 b44:	ff 25 c6 e3 00 00    	jmp    QWORD PTR [rip+0xe3c6]        # ef10 <sysinfo@GLIBC_2.2.5>
 b4a:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000b50 <getpagesize@plt>:
 b50:	f3 0f 1e fa          	endbr64
 b54:	ff 25 be e3 00 00    	jmp    QWORD PTR [rip+0xe3be]        # ef18 <getpagesize@GLIBC_2.2.5>
 b5a:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000b60 <__memset_chk@plt>:
 b60:	f3 0f 1e fa          	endbr64
 b64:	ff 25 b6 e3 00 00    	jmp    QWORD PTR [rip+0xe3b6]        # ef20 <__memset_chk@GLIBC_2.3.4>
 b6a:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000b70 <exit@plt>:
 b70:	f3 0f 1e fa          	endbr64
 b74:	ff 25 ae e3 00 00    	jmp    QWORD PTR [rip+0xe3ae]        # ef28 <exit@GLIBC_2.2.5>
 b7a:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000b80 <__fprintf_chk@plt>:
 b80:	f3 0f 1e fa          	endbr64
 b84:	ff 25 a6 e3 00 00    	jmp    QWORD PTR [rip+0xe3a6]        # ef30 <__fprintf_chk@GLIBC_2.3.4>
 b8a:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000b90 <fflush_unlocked@plt>:
 b90:	f3 0f 1e fa          	endbr64
 b94:	ff 25 9e e3 00 00    	jmp    QWORD PTR [rip+0xe39e]        # ef38 <fflush_unlocked@GLIBC_2.2.5>
 b9a:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000ba0 <mbsinit@plt>:
 ba0:	f3 0f 1e fa          	endbr64
 ba4:	ff 25 96 e3 00 00    	jmp    QWORD PTR [rip+0xe396]        # ef40 <mbsinit@GLIBC_2.2.5>
 baa:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000bb0 <iswprint@plt>:
 bb0:	f3 0f 1e fa          	endbr64
 bb4:	ff 25 8e e3 00 00    	jmp    QWORD PTR [rip+0xe38e]        # ef48 <iswprint@GLIBC_2.2.5>
 bba:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000bc0 <fstat@plt>:
 bc0:	f3 0f 1e fa          	endbr64
 bc4:	ff 25 86 e3 00 00    	jmp    QWORD PTR [rip+0xe386]        # ef50 <fstat@GLIBC_2.33>
 bca:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000bd0 <__cxa_finalize@plt>:
 bd0:	f3 0f 1e fa          	endbr64
 bd4:	ff 25 7e e3 00 00    	jmp    QWORD PTR [rip+0xe37e]        # ef58 <__cxa_finalize@GLIBC_2.2.5>
 bda:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000be0 <getdelim@plt>:
 be0:	f3 0f 1e fa          	endbr64
 be4:	ff 25 76 e3 00 00    	jmp    QWORD PTR [rip+0xe376]        # ef60 <getdelim@GLIBC_2.2.5>
 bea:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000bf0 <strstr@plt>:
 bf0:	f3 0f 1e fa          	endbr64
 bf4:	ff 25 6e e3 00 00    	jmp    QWORD PTR [rip+0xe36e]        # ef68 <strstr@GLIBC_2.2.5>
 bfa:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

0000000000000c00 <__ctype_b_loc@plt>:
 c00:	f3 0f 1e fa          	endbr64
 c04:	ff 25 66 e3 00 00    	jmp    QWORD PTR [rip+0xe366]        # ef70 <__ctype_b_loc@GLIBC_2.3>
 c0a:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]

Desensamblado de la sección .text:

0000000000000c40 <error@@Base-0x12d>:
     c40:	55                   	push   rbp
     c41:	31 c0                	xor    eax,eax
     c43:	be 03 00 00 00       	mov    esi,0x3
     c48:	bf 01 00 00 00       	mov    edi,0x1
     c4d:	48 89 e5             	mov    rbp,rsp
     c50:	e8 0b fc ff ff       	call   860 <fcntl@plt>
     c55:	85 c0                	test   eax,eax
     c57:	78 10                	js     c69 <__ctype_b_loc@plt+0x69>
     c59:	48 8b 05 30 e3 00 00 	mov    rax,QWORD PTR [rip+0xe330]        # ef90 <error_at_line@@Base+0xe027>
     c60:	5d                   	pop    rbp
     c61:	48 8b 38             	mov    rdi,QWORD PTR [rax]
     c64:	e9 27 ff ff ff       	jmp    b90 <fflush_unlocked@plt>
     c69:	5d                   	pop    rbp
     c6a:	c3                   	ret
     c6b:	55                   	push   rbp
     c6c:	ba 00 04 00 00       	mov    edx,0x400
     c71:	48 89 e5             	mov    rbp,rsp
     c74:	48 81 ec 10 04 00 00 	sub    rsp,0x410
     c7b:	64 48 8b 34 25 28 00 	mov    rsi,QWORD PTR fs:0x28
     c82:	00 00 
     c84:	48 89 75 f8          	mov    QWORD PTR [rbp-0x8],rsi
     c88:	48 8d b5 f8 fb ff ff 	lea    rsi,[rbp-0x408]
     c8f:	e8 dc fd ff ff       	call   a70 <strerror_r@plt>
     c94:	48 85 c0             	test   rax,rax
     c97:	75 18                	jne    cb1 <__ctype_b_loc@plt+0xb1>
     c99:	ba 05 00 00 00       	mov    edx,0x5
     c9e:	48 8d 35 6c ab 00 00 	lea    rsi,[rip+0xab6c]        # b811 <error_at_line@@Base+0xa8a8>
     ca5:	48 8d 3d 03 aa 00 00 	lea    rdi,[rip+0xaa03]        # b6af <error_at_line@@Base+0xa746>
     cac:	e8 0f fc ff ff       	call   8c0 <dcgettext@plt>
     cb1:	48 89 c1             	mov    rcx,rax
     cb4:	48 8b 05 25 e3 00 00 	mov    rax,QWORD PTR [rip+0xe325]        # efe0 <error_at_line@@Base+0xe077>
     cbb:	48 8d 15 ec ac 00 00 	lea    rdx,[rip+0xacec]        # b9ae <error_at_line@@Base+0xaa45>
     cc2:	be 02 00 00 00       	mov    esi,0x2
     cc7:	48 8b 38             	mov    rdi,QWORD PTR [rax]
     cca:	31 c0                	xor    eax,eax
     ccc:	e8 af fe ff ff       	call   b80 <__fprintf_chk@plt>
     cd1:	48 8b 45 f8          	mov    rax,QWORD PTR [rbp-0x8]
     cd5:	64 48 2b 04 25 28 00 	sub    rax,QWORD PTR fs:0x28
     cdc:	00 00 
     cde:	74 05                	je     ce5 <__ctype_b_loc@plt+0xe5>
     ce0:	e8 0b fc ff ff       	call   8f0 <__stack_chk_fail@plt>
     ce5:	c9                   	leave
     ce6:	c3                   	ret
     ce7:	55                   	push   rbp
     ce8:	48 89 e5             	mov    rbp,rsp
     ceb:	41 55                	push   r13
     ced:	41 89 f5             	mov    r13d,esi
     cf0:	be 02 00 00 00       	mov    esi,0x2
     cf5:	41 54                	push   r12
     cf7:	41 89 fc             	mov    r12d,edi
     cfa:	53                   	push   rbx
     cfb:	41 50                	push   r8
     cfd:	48 8b 1d dc e2 00 00 	mov    rbx,QWORD PTR [rip+0xe2dc]        # efe0 <error_at_line@@Base+0xe077>
     d04:	48 8b 3b             	mov    rdi,QWORD PTR [rbx]
     d07:	e8 d4 fa ff ff       	call   7e0 <__vfprintf_chk@plt>
     d0c:	48 8d 05 cd e3 00 00 	lea    rax,[rip+0xe3cd]        # f0e0 <error_message_count@@Base>
     d13:	ff 00                	inc    DWORD PTR [rax]
     d15:	45 85 ed             	test   r13d,r13d
     d18:	74 08                	je     d22 <__ctype_b_loc@plt+0x122>
     d1a:	44 89 ef             	mov    edi,r13d
     d1d:	e8 49 ff ff ff       	call   c6b <__ctype_b_loc@plt+0x6b>
     d22:	48 8b 3b             	mov    rdi,QWORD PTR [rbx]
     d25:	48 8b 47 28          	mov    rax,QWORD PTR [rdi+0x28]
     d29:	48 3b 47 30          	cmp    rax,QWORD PTR [rdi+0x30]
     d2d:	72 0c                	jb     d3b <__ctype_b_loc@plt+0x13b>
     d2f:	be 0a 00 00 00       	mov    esi,0xa
     d34:	e8 f7 fb ff ff       	call   930 <__overflow@plt>
     d39:	eb 0b                	jmp    d46 <__ctype_b_loc@plt+0x146>
     d3b:	48 8d 50 01          	lea    rdx,[rax+0x1]
     d3f:	48 89 57 28          	mov    QWORD PTR [rdi+0x28],rdx
     d43:	c6 00 0a             	mov    BYTE PTR [rax],0xa
     d46:	48 8b 3b             	mov    rdi,QWORD PTR [rbx]
     d49:	e8 42 fe ff ff       	call   b90 <fflush_unlocked@plt>
     d4e:	45 85 e4             	test   r12d,r12d
     d51:	74 08                	je     d5b <__ctype_b_loc@plt+0x15b>
     d53:	44 89 e7             	mov    edi,r12d
     d56:	e8 15 fe ff ff       	call   b70 <exit@plt>
     d5b:	58                   	pop    rax
     d5c:	5b                   	pop    rbx
     d5d:	41 5c                	pop    r12
     d5f:	41 5d                	pop    r13
     d61:	5d                   	pop    rbp
     d62:	c3                   	ret
     d63:	e8 88 fa ff ff       	call   7f0 <abort@plt>
     d68:	e8 83 fa ff ff       	call   7f0 <abort@plt>

0000000000000d6d <error@@Base>:
     d6d:	f3 0f 1e fa          	endbr64
     d71:	55                   	push   rbp
     d72:	48 89 e5             	mov    rbp,rsp
     d75:	41 55                	push   r13
     d77:	49 89 d5             	mov    r13,rdx
     d7a:	41 54                	push   r12
     d7c:	41 89 f4             	mov    r12d,esi
     d7f:	53                   	push   rbx
     d80:	89 fb                	mov    ebx,edi
     d82:	48 81 ec d8 00 00 00 	sub    rsp,0xd8
     d89:	48 89 8d 48 ff ff ff 	mov    QWORD PTR [rbp-0xb8],rcx
     d90:	4c 89 85 50 ff ff ff 	mov    QWORD PTR [rbp-0xb0],r8
     d97:	4c 89 8d 58 ff ff ff 	mov    QWORD PTR [rbp-0xa8],r9
     d9e:	84 c0                	test   al,al
     da0:	74 26                	je     dc8 <error@@Base+0x5b>
     da2:	0f 29 85 60 ff ff ff 	movaps XMMWORD PTR [rbp-0xa0],xmm0
     da9:	0f 29 8d 70 ff ff ff 	movaps XMMWORD PTR [rbp-0x90],xmm1
     db0:	0f 29 55 80          	movaps XMMWORD PTR [rbp-0x80],xmm2
     db4:	0f 29 5d 90          	movaps XMMWORD PTR [rbp-0x70],xmm3
     db8:	0f 29 65 a0          	movaps XMMWORD PTR [rbp-0x60],xmm4
     dbc:	0f 29 6d b0          	movaps XMMWORD PTR [rbp-0x50],xmm5
     dc0:	0f 29 75 c0          	movaps XMMWORD PTR [rbp-0x40],xmm6
     dc4:	0f 29 7d d0          	movaps XMMWORD PTR [rbp-0x30],xmm7
     dc8:	64 48 8b 04 25 28 00 	mov    rax,QWORD PTR fs:0x28
     dcf:	00 00 
     dd1:	48 89 85 28 ff ff ff 	mov    QWORD PTR [rbp-0xd8],rax
     dd8:	31 c0                	xor    eax,eax
     dda:	48 8d 45 10          	lea    rax,[rbp+0x10]
     dde:	c7 85 10 ff ff ff 18 	mov    DWORD PTR [rbp-0xf0],0x18
     de5:	00 00 00 
     de8:	48 89 85 18 ff ff ff 	mov    QWORD PTR [rbp-0xe8],rax
     def:	48 8d 85 30 ff ff ff 	lea    rax,[rbp-0xd0]
     df6:	48 89 85 20 ff ff ff 	mov    QWORD PTR [rbp-0xe0],rax
     dfd:	c7 85 14 ff ff ff 30 	mov    DWORD PTR [rbp-0xec],0x30
     e04:	00 00 00 
     e07:	e8 34 fe ff ff       	call   c40 <__ctype_b_loc@plt+0x40>
     e0c:	48 8d 05 d5 e2 00 00 	lea    rax,[rip+0xe2d5]        # f0e8 <error_print_progname@@Base>
     e13:	48 8b 00             	mov    rax,QWORD PTR [rax]
     e16:	48 85 c0             	test   rax,rax
     e19:	74 04                	je     e1f <error@@Base+0xb2>
     e1b:	ff d0                	call   rax
     e1d:	eb 27                	jmp    e46 <error@@Base+0xd9>
     e1f:	48 8b 05 aa e1 00 00 	mov    rax,QWORD PTR [rip+0xe1aa]        # efd0 <error_at_line@@Base+0xe067>
     e26:	48 8d 15 05 aa 00 00 	lea    rdx,[rip+0xaa05]        # b832 <error_at_line@@Base+0xa8c9>
     e2d:	be 02 00 00 00       	mov    esi,0x2
     e32:	48 8b 08             	mov    rcx,QWORD PTR [rax]
     e35:	48 8b 05 a4 e1 00 00 	mov    rax,QWORD PTR [rip+0xe1a4]        # efe0 <error_at_line@@Base+0xe077>
     e3c:	48 8b 38             	mov    rdi,QWORD PTR [rax]
     e3f:	31 c0                	xor    eax,eax
     e41:	e8 3a fd ff ff       	call   b80 <__fprintf_chk@plt>
     e46:	48 8d 8d 10 ff ff ff 	lea    rcx,[rbp-0xf0]
     e4d:	4c 89 ea             	mov    rdx,r13
     e50:	44 89 e6             	mov    esi,r12d
     e53:	89 df                	mov    edi,ebx
     e55:	e8 8d fe ff ff       	call   ce7 <__ctype_b_loc@plt+0xe7>
     e5a:	48 8b 85 28 ff ff ff 	mov    rax,QWORD PTR [rbp-0xd8]
     e61:	64 48 2b 04 25 28 00 	sub    rax,QWORD PTR fs:0x28
     e68:	00 00 
     e6a:	74 05                	je     e71 <error@@Base+0x104>
     e6c:	e8 7f fa ff ff       	call   8f0 <__stack_chk_fail@plt>
     e71:	48 81 c4 d8 00 00 00 	add    rsp,0xd8
     e78:	5b                   	pop    rbx
     e79:	41 5c                	pop    r12
     e7b:	41 5d                	pop    r13
     e7d:	5d                   	pop    rbp
     e7e:	c3                   	ret
     e7f:	ba 05 00 00 00       	mov    edx,0x5
     e84:	48 8d 35 ac a9 00 00 	lea    rsi,[rip+0xa9ac]        # b837 <error_at_line@@Base+0xa8ce>
     e8b:	48 8d 3d 1d a8 00 00 	lea    rdi,[rip+0xa81d]        # b6af <error_at_line@@Base+0xa746>
     e92:	48 89 5d f8          	mov    QWORD PTR [rbp-0x8],rbx
     e96:	e8 25 fa ff ff       	call   8c0 <dcgettext@plt>
     e9b:	48 89 c3             	mov    rbx,rax
     e9e:	e8 5d f9 ff ff       	call   800 <__errno_location@plt>
     ea3:	31 ff                	xor    edi,edi
     ea5:	48 89 d9             	mov    rcx,rbx
     ea8:	48 8d 15 86 aa 00 00 	lea    rdx,[rip+0xaa86]        # b935 <error_at_line@@Base+0xa9cc>
     eaf:	8b 30                	mov    esi,DWORD PTR [rax]
     eb1:	31 c0                	xor    eax,eax
     eb3:	e8 b5 fe ff ff       	call   d6d <error@@Base>
     eb8:	8b 3d 66 e1 00 00    	mov    edi,DWORD PTR [rip+0xe166]        # f024 <error_at_line@@Base+0xe0bb>
     ebe:	e8 5d f9 ff ff       	call   820 <_exit@plt>
     ec3:	31 ff                	xor    edi,edi
     ec5:	ba 05 00 00 00       	mov    edx,0x5
     eca:	48 8d 35 9a a9 00 00 	lea    rsi,[rip+0xa99a]        # b86b <error_at_line@@Base+0xa902>
     ed1:	e8 ea f9 ff ff       	call   8c0 <dcgettext@plt>
     ed6:	31 f6                	xor    esi,esi
     ed8:	31 ff                	xor    edi,edi
     eda:	48 89 c2             	mov    rdx,rax
     edd:	31 c0                	xor    eax,eax
     edf:	e8 89 fe ff ff       	call   d6d <error@@Base>
     ee4:	e9 a2 80 00 00       	jmp    8f8b <error_at_line@@Base+0x8022>
     ee9:	ba 05 00 00 00       	mov    edx,0x5
     eee:	48 8d 35 ca a9 00 00 	lea    rsi,[rip+0xa9ca]        # b8bf <error_at_line@@Base+0xa956>
     ef5:	31 ff                	xor    edi,edi
     ef7:	e8 c4 f9 ff ff       	call   8c0 <dcgettext@plt>
     efc:	31 f6                	xor    esi,esi
     efe:	31 ff                	xor    edi,edi
     f00:	48 89 c2             	mov    rdx,rax
     f03:	31 c0                	xor    eax,eax
     f05:	e8 63 fe ff ff       	call   d6d <error@@Base>
     f0a:	c6 05 19 e3 00 00 ff 	mov    BYTE PTR [rip+0xe319],0xff        # f22a <error_print_progname@@Base+0x142>
     f11:	e9 ba 74 00 00       	jmp    83d0 <error_at_line@@Base+0x7467>
     f16:	ba 05 00 00 00       	mov    edx,0x5
     f1b:	48 8d 35 65 a9 00 00 	lea    rsi,[rip+0xa965]        # b887 <error_at_line@@Base+0xa91e>
     f22:	31 ff                	xor    edi,edi
     f24:	e8 97 f9 ff ff       	call   8c0 <dcgettext@plt>
     f29:	31 f6                	xor    esi,esi
     f2b:	31 ff                	xor    edi,edi
     f2d:	48 89 c2             	mov    rdx,rax
     f30:	31 c0                	xor    eax,eax
     f32:	e8 36 fe ff ff       	call   d6d <error@@Base>
     f37:	c6 05 eb e2 00 00 ff 	mov    BYTE PTR [rip+0xe2eb],0xff        # f229 <error_print_progname@@Base+0x141>
     f3e:	e9 51 7d 00 00       	jmp    8c94 <error_at_line@@Base+0x7d2b>
     f43:	31 ff                	xor    edi,edi
     f45:	ba 05 00 00 00       	mov    edx,0x5
     f4a:	48 8d 35 50 a9 00 00 	lea    rsi,[rip+0xa950]        # b8a1 <error_at_line@@Base+0xa938>
     f51:	e8 6a f9 ff ff       	call   8c0 <dcgettext@plt>
     f56:	31 f6                	xor    esi,esi
     f58:	31 ff                	xor    edi,edi
     f5a:	48 89 c2             	mov    rdx,rax
     f5d:	31 c0                	xor    eax,eax
     f5f:	e8 09 fe ff ff       	call   d6d <error@@Base>
     f64:	e9 70 7f 00 00       	jmp    8ed9 <error_at_line@@Base+0x7f70>

0000000000000f69 <error_at_line@@Base>:
     f69:	f3 0f 1e fa          	endbr64
     f6d:	55                   	push   rbp
     f6e:	48 89 e5             	mov    rbp,rsp
     f71:	41 57                	push   r15
     f73:	4d 89 c7             	mov    r15,r8
     f76:	41 56                	push   r14
     f78:	41 89 f6             	mov    r14d,esi
     f7b:	41 55                	push   r13
     f7d:	41 89 fd             	mov    r13d,edi
     f80:	41 54                	push   r12
     f82:	41 89 cc             	mov    r12d,ecx
     f85:	53                   	push   rbx
     f86:	48 89 d3             	mov    rbx,rdx
     f89:	48 81 ec d8 00 00 00 	sub    rsp,0xd8
     f90:	4c 89 8d 48 ff ff ff 	mov    QWORD PTR [rbp-0xb8],r9
     f97:	84 c0                	test   al,al
     f99:	74 29                	je     fc4 <error_at_line@@Base+0x5b>
     f9b:	0f 29 85 50 ff ff ff 	movaps XMMWORD PTR [rbp-0xb0],xmm0
     fa2:	0f 29 8d 60 ff ff ff 	movaps XMMWORD PTR [rbp-0xa0],xmm1
     fa9:	0f 29 95 70 ff ff ff 	movaps XMMWORD PTR [rbp-0x90],xmm2
     fb0:	0f 29 5d 80          	movaps XMMWORD PTR [rbp-0x80],xmm3
     fb4:	0f 29 65 90          	movaps XMMWORD PTR [rbp-0x70],xmm4
     fb8:	0f 29 6d a0          	movaps XMMWORD PTR [rbp-0x60],xmm5
     fbc:	0f 29 75 b0          	movaps XMMWORD PTR [rbp-0x50],xmm6
     fc0:	0f 29 7d c0          	movaps XMMWORD PTR [rbp-0x40],xmm7
     fc4:	64 48 8b 04 25 28 00 	mov    rax,QWORD PTR fs:0x28
     fcb:	00 00 
     fcd:	48 89 85 18 ff ff ff 	mov    QWORD PTR [rbp-0xe8],rax
     fd4:	31 c0                	xor    eax,eax
     fd6:	48 8d 45 10          	lea    rax,[rbp+0x10]
     fda:	c7 85 00 ff ff ff 28 	mov    DWORD PTR [rbp-0x100],0x28
     fe1:	00 00 00 
     fe4:	48 89 85 08 ff ff ff 	mov    QWORD PTR [rbp-0xf8],rax
     feb:	48 8d 85 20 ff ff ff 	lea    rax,[rbp-0xe0]
     ff2:	48 89 85 10 ff ff ff 	mov    QWORD PTR [rbp-0xf0],rax
     ff9:	48 8d 05 e4 e0 00 00 	lea    rax,[rip+0xe0e4]        # f0e4 <error_one_per_line@@Base>
    1000:	c7 85 04 ff ff ff 30 	mov    DWORD PTR [rbp-0xfc],0x30
    1007:	00 00 00 
    100a:	83 38 00             	cmp    DWORD PTR [rax],0x0
    100d:	74 41                	je     1050 <error_at_line@@Base+0xe7>
    100f:	44 3b 25 f2 e1 00 00 	cmp    r12d,DWORD PTR [rip+0xe1f2]        # f208 <error_print_progname@@Base+0x120>
    1016:	75 2a                	jne    1042 <error_at_line@@Base+0xd9>
    1018:	48 8b 3d e1 e1 00 00 	mov    rdi,QWORD PTR [rip+0xe1e1]        # f200 <error_print_progname@@Base+0x118>
    101f:	48 39 fb             	cmp    rbx,rdi
    1022:	0f 84 ad 00 00 00    	je     10d5 <error_at_line@@Base+0x16c>
    1028:	48 85 ff             	test   rdi,rdi
    102b:	74 15                	je     1042 <error_at_line@@Base+0xd9>
    102d:	48 85 db             	test   rbx,rbx
    1030:	74 10                	je     1042 <error_at_line@@Base+0xd9>
    1032:	48 89 de             	mov    rsi,rbx
    1035:	e8 d6 f9 ff ff       	call   a10 <strcmp@plt>
    103a:	85 c0                	test   eax,eax
    103c:	0f 84 93 00 00 00    	je     10d5 <error_at_line@@Base+0x16c>
    1042:	48 89 1d b7 e1 00 00 	mov    QWORD PTR [rip+0xe1b7],rbx        # f200 <error_print_progname@@Base+0x118>
    1049:	44 89 25 b8 e1 00 00 	mov    DWORD PTR [rip+0xe1b8],r12d        # f208 <error_print_progname@@Base+0x120>
    1050:	e8 eb fb ff ff       	call   c40 <__ctype_b_loc@plt+0x40>
    1055:	48 8d 05 8c e0 00 00 	lea    rax,[rip+0xe08c]        # f0e8 <error_print_progname@@Base>
    105c:	48 8b 00             	mov    rax,QWORD PTR [rax]
    105f:	48 85 c0             	test   rax,rax
    1062:	74 04                	je     1068 <error_at_line@@Base+0xff>
    1064:	ff d0                	call   rax
    1066:	eb 27                	jmp    108f <error_at_line@@Base+0x126>
    1068:	48 8b 05 61 df 00 00 	mov    rax,QWORD PTR [rip+0xdf61]        # efd0 <error_at_line@@Base+0xe067>
    106f:	48 8d 15 c1 a9 00 00 	lea    rdx,[rip+0xa9c1]        # ba37 <error_at_line@@Base+0xaace>
    1076:	be 02 00 00 00       	mov    esi,0x2
    107b:	48 8b 08             	mov    rcx,QWORD PTR [rax]
    107e:	48 8b 05 5b df 00 00 	mov    rax,QWORD PTR [rip+0xdf5b]        # efe0 <error_at_line@@Base+0xe077>
    1085:	48 8b 38             	mov    rdi,QWORD PTR [rax]
    1088:	31 c0                	xor    eax,eax
    108a:	e8 f1 fa ff ff       	call   b80 <__fprintf_chk@plt>
    108f:	48 85 db             	test   rbx,rbx
    1092:	48 8d 05 96 a9 00 00 	lea    rax,[rip+0xa996]        # ba2f <error_at_line@@Base+0xaac6>
    1099:	48 89 d9             	mov    rcx,rbx
    109c:	45 89 e0             	mov    r8d,r12d
    109f:	48 8d 15 8f a7 00 00 	lea    rdx,[rip+0xa78f]        # b835 <error_at_line@@Base+0xa8cc>
    10a6:	be 02 00 00 00       	mov    esi,0x2
    10ab:	48 0f 45 d0          	cmovne rdx,rax
    10af:	48 8b 05 2a df 00 00 	mov    rax,QWORD PTR [rip+0xdf2a]        # efe0 <error_at_line@@Base+0xe077>
    10b6:	48 8b 38             	mov    rdi,QWORD PTR [rax]
    10b9:	31 c0                	xor    eax,eax
    10bb:	e8 c0 fa ff ff       	call   b80 <__fprintf_chk@plt>
    10c0:	4c 89 fa             	mov    rdx,r15
    10c3:	44 89 f6             	mov    esi,r14d
    10c6:	44 89 ef             	mov    edi,r13d
    10c9:	48 8d 8d 00 ff ff ff 	lea    rcx,[rbp-0x100]
    10d0:	e8 12 fc ff ff       	call   ce7 <__ctype_b_loc@plt+0xe7>
    10d5:	48 8b 85 18 ff ff ff 	mov    rax,QWORD PTR [rbp-0xe8]
    10dc:	64 48 2b 04 25 28 00 	sub    rax,QWORD PTR fs:0x28
    10e3:	00 00 
    10e5:	74 05                	je     10ec <error_at_line@@Base+0x183>
    10e7:	e8 04 f8 ff ff       	call   8f0 <__stack_chk_fail@plt>
    10ec:	48 81 c4 d8 00 00 00 	add    rsp,0xd8
    10f3:	5b                   	pop    rbx
    10f4:	41 5c                	pop    r12
    10f6:	41 5d                	pop    r13
    10f8:	41 5e                	pop    r14
    10fa:	41 5f                	pop    r15
    10fc:	5d                   	pop    rbp
    10fd:	c3                   	ret
    10fe:	66 90                	xchg   ax,ax
    1100:	f3 0f 1e fa          	endbr64
    1104:	55                   	push   rbp
    1105:	48 89 e5             	mov    rbp,rsp
    1108:	41 57                	push   r15
    110a:	41 56                	push   r14
    110c:	41 55                	push   r13
    110e:	41 54                	push   r12
    1110:	53                   	push   rbx
    1111:	48 81 ec 48 02 00 00 	sub    rsp,0x248
    1118:	89 bd f0 fd ff ff    	mov    DWORD PTR [rbp-0x210],edi
    111e:	48 89 b5 e0 fd ff ff 	mov    QWORD PTR [rbp-0x220],rsi
    1125:	64 48 8b 1c 25 28 00 	mov    rbx,QWORD PTR fs:0x28
    112c:	00 00 
    112e:	48 89 5d c8          	mov    QWORD PTR [rbp-0x38],rbx
    1132:	48 8b 1e             	mov    rbx,QWORD PTR [rsi]
    1135:	be 2f 00 00 00       	mov    esi,0x2f
    113a:	48 89 df             	mov    rdi,rbx
    113d:	49 89 dc             	mov    r12,rbx
    1140:	e8 fb f7 ff ff       	call   940 <strrchr@plt>
    1145:	48 85 c0             	test   rax,rax
    1148:	74 30                	je     117a <error_at_line@@Base+0x211>
    114a:	4c 8d 60 01          	lea    r12,[rax+0x1]
    114e:	49 89 c6             	mov    r14,rax
    1151:	4c 89 e0             	mov    rax,r12
    1154:	48 29 d8             	sub    rax,rbx
    1157:	48 83 f8 06          	cmp    rax,0x6
    115b:	7e 1d                	jle    117a <error_at_line@@Base+0x211>
    115d:	49 8d 7e fa          	lea    rdi,[r14-0x6]
    1161:	ba 07 00 00 00       	mov    edx,0x7
    1166:	48 8d 35 73 a7 00 00 	lea    rsi,[rip+0xa773]        # b8e0 <error_at_line@@Base+0xa977>
    116d:	e8 6e f8 ff ff       	call   9e0 <memcmp@plt>
    1172:	85 c0                	test   eax,eax
    1174:	0f 84 08 03 00 00    	je     1482 <error_at_line@@Base+0x519>
    117a:	48 8b 05 37 de 00 00 	mov    rax,QWORD PTR [rip+0xde37]        # efb8 <error_at_line@@Base+0xe04f>
    1181:	48 8d 35 c9 a4 00 00 	lea    rsi,[rip+0xa4c9]        # b651 <error_at_line@@Base+0xa6e8>
    1188:	bf 06 00 00 00       	mov    edi,0x6
    118d:	48 89 1d 04 e3 00 00 	mov    QWORD PTR [rip+0xe304],rbx        # f498 <error_print_progname@@Base+0x3b0>
    1194:	48 89 18             	mov    QWORD PTR [rax],rbx
    1197:	48 8b 05 32 de 00 00 	mov    rax,QWORD PTR [rip+0xde32]        # efd0 <error_at_line@@Base+0xe067>
    119e:	4c 89 20             	mov    QWORD PTR [rax],r12
    11a1:	e8 1a f9 ff ff       	call   ac0 <setlocale@plt>
    11a6:	48 8d 35 3f a7 00 00 	lea    rsi,[rip+0xa73f]        # b8ec <error_at_line@@Base+0xa983>
    11ad:	48 8d 3d a3 a5 00 00 	lea    rdi,[rip+0xa5a3]        # b757 <error_at_line@@Base+0xa7ee>
    11b4:	e8 f7 f6 ff ff       	call   8b0 <bindtextdomain@plt>
    11b9:	48 8d 3d 97 a5 00 00 	lea    rdi,[rip+0xa597]        # b757 <error_at_line@@Base+0xa7ee>
    11c0:	e8 cb f6 ff ff       	call   890 <textdomain@plt>
    11c5:	48 8d 3d f4 69 00 00 	lea    rdi,[rip+0x69f4]        # 7bc0 <error_at_line@@Base+0x6c57>
    11cc:	e8 af 7e 00 00       	call   9080 <error_at_line@@Base+0x8117>
    11d1:	e8 7a f9 ff ff       	call   b50 <getpagesize@plt>
    11d6:	31 c9                	xor    ecx,ecx
    11d8:	31 f6                	xor    esi,esi
    11da:	ba 01 00 00 00       	mov    edx,0x1
    11df:	48 98                	cdqe
    11e1:	48 89 05 98 e2 00 00 	mov    QWORD PTR [rip+0xe298],rax        # f480 <error_print_progname@@Base+0x398>
    11e8:	48 8b 05 a1 dd 00 00 	mov    rax,QWORD PTR [rip+0xdda1]        # ef90 <error_at_line@@Base+0xe027>
    11ef:	48 8b 38             	mov    rdi,QWORD PTR [rax]
    11f2:	e8 e9 f8 ff ff       	call   ae0 <setvbuf@plt>
    11f7:	48 8d 3d 00 a7 00 00 	lea    rdi,[rip+0xa700]        # b8fe <error_at_line@@Base+0xa995>
    11fe:	e8 bd f5 ff ff       	call   7c0 <getenv@plt>
    1203:	c6 05 7f e2 00 00 00 	mov    BYTE PTR [rip+0xe27f],0x0        # f489 <error_print_progname@@Base+0x3a1>
    120a:	48 89 85 c8 fd ff ff 	mov    QWORD PTR [rbp-0x238],rax
    1211:	48 85 c0             	test   rax,rax
    1214:	c6 05 6f e2 00 00 00 	mov    BYTE PTR [rip+0xe26f],0x0        # f48a <error_print_progname@@Base+0x3a2>
    121b:	c6 05 69 e2 00 00 00 	mov    BYTE PTR [rip+0xe269],0x0        # f48b <error_print_progname@@Base+0x3a3>
    1222:	c6 05 67 e2 00 00 00 	mov    BYTE PTR [rip+0xe267],0x0        # f490 <error_print_progname@@Base+0x3a8>
    1229:	c6 05 58 e2 00 00 00 	mov    BYTE PTR [rip+0xe258],0x0        # f488 <error_print_progname@@Base+0x3a0>
    1230:	48 c7 05 f5 df 00 00 	mov    QWORD PTR [rip+0xdff5],0x0        # f230 <error_print_progname@@Base+0x148>
    1237:	00 00 00 00 
    123b:	48 c7 05 fa df 00 00 	mov    QWORD PTR [rip+0xdffa],0x0        # f240 <error_print_progname@@Base+0x158>
    1242:	00 00 00 00 
    1246:	48 c7 05 ff df 00 00 	mov    QWORD PTR [rip+0xdfff],0x0        # f250 <error_print_progname@@Base+0x168>
    124d:	00 00 00 00 
    1251:	48 c7 05 04 e0 00 00 	mov    QWORD PTR [rip+0xe004],0x0        # f260 <error_print_progname@@Base+0x178>
    1258:	00 00 00 00 
    125c:	48 c7 05 09 e0 00 00 	mov    QWORD PTR [rip+0xe009],0x0        # f270 <error_print_progname@@Base+0x188>
    1263:	00 00 00 00 
    1267:	48 c7 85 d0 fd ff ff 	mov    QWORD PTR [rbp-0x230],0x0
    126e:	00 00 00 00 
    1272:	0f 95 05 b2 df 00 00 	setne  BYTE PTR [rip+0xdfb2]        # f22b <error_print_progname@@Base+0x143>
    1279:	0f 1f 80 00 00 00 00 	nop    DWORD PTR [rax+0x0]
    1280:	48 8b b5 e0 fd ff ff 	mov    rsi,QWORD PTR [rbp-0x220]
    1287:	8b bd f0 fd ff ff    	mov    edi,DWORD PTR [rbp-0x210]
    128d:	45 31 c0             	xor    r8d,r8d
    1290:	48 8d 0d c9 d6 00 00 	lea    rcx,[rip+0xd6c9]        # e960 <error_at_line@@Base+0xd9f7>
    1297:	48 8d 15 ba a6 00 00 	lea    rdx,[rip+0xa6ba]        # b958 <error_at_line@@Base+0xa9ef>
    129e:	e8 5d f6 ff ff       	call   900 <getopt_long@plt>
    12a3:	83 f8 ff             	cmp    eax,0xffffffff
    12a6:	0f 84 02 02 00 00    	je     14ae <error_at_line@@Base+0x545>
    12ac:	3d 82 00 00 00       	cmp    eax,0x82
    12b1:	0f 8f 6f 0a 00 00    	jg     1d26 <error_at_line@@Base+0xdbd>
    12b7:	83 f8 4b             	cmp    eax,0x4b
    12ba:	0f 8e 30 01 00 00    	jle    13f0 <error_at_line@@Base+0x487>
    12c0:	83 e8 4c             	sub    eax,0x4c
    12c3:	83 f8 36             	cmp    eax,0x36
    12c6:	0f 87 5a 0a 00 00    	ja     1d26 <error_at_line@@Base+0xdbd>
    12cc:	48 8d 0d d1 b3 00 00 	lea    rcx,[rip+0xb3d1]        # c6a4 <error_at_line@@Base+0xb73b>
    12d3:	48 63 04 81          	movsxd rax,DWORD PTR [rcx+rax*4]
    12d7:	48 01 c8             	add    rax,rcx
    12da:	3e ff e0             	notrack jmp rax
    12dd:	0f 1f 00             	nop    DWORD PTR [rax]
    12e0:	48 8b 05 c1 dc 00 00 	mov    rax,QWORD PTR [rip+0xdcc1]        # efa8 <error_at_line@@Base+0xe03f>
    12e7:	49 c7 c6 ff ff ff ff 	mov    r14,0xffffffffffffffff
    12ee:	45 31 e4             	xor    r12d,r12d
    12f1:	4c 8d 2d e3 a5 00 00 	lea    r13,[rip+0xa5e3]        # b8db <error_at_line@@Base+0xa972>
    12f8:	48 8b 18             	mov    rbx,QWORD PTR [rax]
    12fb:	48 89 df             	mov    rdi,rbx
    12fe:	e8 dd f5 ff ff       	call   8e0 <strlen@plt>
    1303:	c6 85 d8 fd ff ff 00 	mov    BYTE PTR [rbp-0x228],0x0
    130a:	49 89 c7             	mov    r15,rax
    130d:	eb 31                	jmp    1340 <error_at_line@@Base+0x3d7>
    130f:	90                   	nop
    1310:	48 8d 05 a9 b4 00 00 	lea    rax,[rip+0xb4a9]        # c7c0 <error_at_line@@Base+0xb857>
    1317:	42 8b 34 a0          	mov    esi,DWORD PTR [rax+r12*4]
    131b:	42 39 34 b0          	cmp    DWORD PTR [rax+r14*4],esi
    131f:	0f 95 c0             	setne  al
    1322:	08 85 d8 fd ff ff    	or     BYTE PTR [rbp-0x228],al
    1328:	49 83 c4 01          	add    r12,0x1
    132c:	48 8d 05 8d d7 00 00 	lea    rax,[rip+0xd78d]        # eac0 <error_at_line@@Base+0xdb57>
    1333:	4e 8b 2c e0          	mov    r13,QWORD PTR [rax+r12*8]
    1337:	4d 85 ed             	test   r13,r13
    133a:	0f 84 15 01 00 00    	je     1455 <error_at_line@@Base+0x4ec>
    1340:	4c 89 fa             	mov    rdx,r15
    1343:	48 89 de             	mov    rsi,rbx
    1346:	4c 89 ef             	mov    rdi,r13
    1349:	e8 c2 f4 ff ff       	call   810 <strncmp@plt>
    134e:	85 c0                	test   eax,eax
    1350:	75 d6                	jne    1328 <error_at_line@@Base+0x3bf>
    1352:	4c 89 ef             	mov    rdi,r13
    1355:	e8 86 f5 ff ff       	call   8e0 <strlen@plt>
    135a:	49 39 c7             	cmp    r15,rax
    135d:	0f 84 46 01 00 00    	je     14a9 <error_at_line@@Base+0x540>
    1363:	49 83 fe ff          	cmp    r14,0xffffffffffffffff
    1367:	75 a7                	jne    1310 <error_at_line@@Base+0x3a7>
    1369:	4d 89 e6             	mov    r14,r12
    136c:	eb ba                	jmp    1328 <error_at_line@@Base+0x3bf>
    136e:	66 90                	xchg   ax,ax
    1370:	48 8b 05 31 dc 00 00 	mov    rax,QWORD PTR [rip+0xdc31]        # efa8 <error_at_line@@Base+0xe03f>
    1377:	48 8b 00             	mov    rax,QWORD PTR [rax]
    137a:	48 89 85 d0 fd ff ff 	mov    QWORD PTR [rbp-0x230],rax
    1381:	e9 fa fe ff ff       	jmp    1280 <error_at_line@@Base+0x317>
    1386:	66 2e 0f 1f 84 00 00 	cs nop WORD PTR [rax+rax*1+0x0]
    138d:	00 00 00 
    1390:	c6 05 91 de 00 00 01 	mov    BYTE PTR [rip+0xde91],0x1        # f228 <error_print_progname@@Base+0x140>
    1397:	e9 e4 fe ff ff       	jmp    1280 <error_at_line@@Base+0x317>
    139c:	0f 1f 40 00          	nop    DWORD PTR [rax+0x0]
    13a0:	c6 05 e4 e0 00 00 01 	mov    BYTE PTR [rip+0xe0e4],0x1        # f48b <error_print_progname@@Base+0x3a3>
    13a7:	e9 d4 fe ff ff       	jmp    1280 <error_at_line@@Base+0x317>
    13ac:	0f 1f 40 00          	nop    DWORD PTR [rax+0x0]
    13b0:	c6 05 d3 e0 00 00 01 	mov    BYTE PTR [rip+0xe0d3],0x1        # f48a <error_print_progname@@Base+0x3a2>
    13b7:	e9 c4 fe ff ff       	jmp    1280 <error_at_line@@Base+0x317>
    13bc:	0f 1f 40 00          	nop    DWORD PTR [rax+0x0]
    13c0:	c6 05 c9 e0 00 00 01 	mov    BYTE PTR [rip+0xe0c9],0x1        # f490 <error_print_progname@@Base+0x3a8>
    13c7:	e9 b4 fe ff ff       	jmp    1280 <error_at_line@@Base+0x317>
    13cc:	0f 1f 40 00          	nop    DWORD PTR [rax+0x0]
    13d0:	c6 05 b2 e0 00 00 01 	mov    BYTE PTR [rip+0xe0b2],0x1        # f489 <error_print_progname@@Base+0x3a1>
    13d7:	e9 a4 fe ff ff       	jmp    1280 <error_at_line@@Base+0x317>
    13dc:	0f 1f 40 00          	nop    DWORD PTR [rax+0x0]
    13e0:	c6 05 a1 e0 00 00 01 	mov    BYTE PTR [rip+0xe0a1],0x1        # f488 <error_print_progname@@Base+0x3a0>
    13e7:	e9 94 fe ff ff       	jmp    1280 <error_at_line@@Base+0x317>
    13ec:	0f 1f 40 00          	nop    DWORD PTR [rax+0x0]
    13f0:	3d 7d ff ff ff       	cmp    eax,0xffffff7d
    13f5:	0f 85 54 11 00 00    	jne    254f <error_at_line@@Base+0x15e6>
    13fb:	48 8d 35 36 a5 00 00 	lea    rsi,[rip+0xa536]        # b938 <error_at_line@@Base+0xa9cf>
    1402:	48 89 f7             	mov    rdi,rsi
    1405:	e8 c6 3e 00 00       	call   52d0 <error_at_line@@Base+0x4367>
    140a:	48 8d 35 37 a5 00 00 	lea    rsi,[rip+0xa537]        # b948 <error_at_line@@Base+0xa9df>
    1411:	48 89 f7             	mov    rdi,rsi
    1414:	48 89 c3             	mov    rbx,rax
    1417:	e8 b4 3e 00 00       	call   52d0 <error_at_line@@Base+0x4367>
    141c:	48 83 ec 08          	sub    rsp,0x8
    1420:	49 89 d9             	mov    r9,rbx
    1423:	48 8d 0d 29 a5 00 00 	lea    rcx,[rip+0xa529]        # b953 <error_at_line@@Base+0xa9ea>
    142a:	49 89 c0             	mov    r8,rax
    142d:	48 8b 05 5c db 00 00 	mov    rax,QWORD PTR [rip+0xdb5c]        # ef90 <error_at_line@@Base+0xe027>
    1434:	48 8d 15 18 a3 00 00 	lea    rdx,[rip+0xa318]        # b753 <error_at_line@@Base+0xa7ea>
    143b:	48 8d 35 27 a2 00 00 	lea    rsi,[rip+0xa227]        # b669 <error_at_line@@Base+0xa700>
    1442:	48 8b 38             	mov    rdi,QWORD PTR [rax]
    1445:	6a 00                	push   0x0
    1447:	31 c0                	xor    eax,eax
    1449:	e8 e2 34 00 00       	call   4930 <error_at_line@@Base+0x39c7>
    144e:	31 ff                	xor    edi,edi
    1450:	e8 1b f7 ff ff       	call   b70 <exit@plt>
    1455:	80 bd d8 fd ff ff 00 	cmp    BYTE PTR [rbp-0x228],0x0
    145c:	0f 85 6a 0d 00 00    	jne    21cc <error_at_line@@Base+0x1263>
    1462:	49 83 fe ff          	cmp    r14,0xffffffffffffffff
    1466:	0f 84 08 11 00 00    	je     2574 <error_at_line@@Base+0x160b>
    146c:	48 8d 05 4d b3 00 00 	lea    rax,[rip+0xb34d]        # c7c0 <error_at_line@@Base+0xb857>
    1473:	42 8b 04 b0          	mov    eax,DWORD PTR [rax+r14*4]
    1477:	89 05 fb dd 00 00    	mov    DWORD PTR [rip+0xddfb],eax        # f278 <error_print_progname@@Base+0x190>
    147d:	e9 fe fd ff ff       	jmp    1280 <error_at_line@@Base+0x317>
    1482:	4c 89 e7             	mov    rdi,r12
    1485:	ba 03 00 00 00       	mov    edx,0x3
    148a:	48 8d 35 57 a4 00 00 	lea    rsi,[rip+0xa457]        # b8e8 <error_at_line@@Base+0xa97f>
    1491:	e8 7a f3 ff ff       	call   810 <strncmp@plt>
    1496:	49 8d 5e 04          	lea    rbx,[r14+0x4]
    149a:	85 c0                	test   eax,eax
    149c:	49 0f 45 dc          	cmovne rbx,r12
    14a0:	4c 0f 44 e3          	cmove  r12,rbx
    14a4:	e9 d1 fc ff ff       	jmp    117a <error_at_line@@Base+0x211>
    14a9:	4d 89 e6             	mov    r14,r12
    14ac:	eb be                	jmp    146c <error_at_line@@Base+0x503>
    14ae:	80 3d db df 00 00 00 	cmp    BYTE PTR [rip+0xdfdb],0x0        # f490 <error_print_progname@@Base+0x3a8>
    14b5:	0f b6 05 cc df 00 00 	movzx  eax,BYTE PTR [rip+0xdfcc]        # f488 <error_print_progname@@Base+0x3a0>
    14bc:	0f 85 09 01 00 00    	jne    15cb <error_at_line@@Base+0x662>
    14c2:	80 3d c2 df 00 00 00 	cmp    BYTE PTR [rip+0xdfc2],0x0        # f48b <error_print_progname@@Base+0x3a3>
    14c9:	0f 85 75 03 00 00    	jne    1844 <error_at_line@@Base+0x8db>
    14cf:	80 3d b4 df 00 00 00 	cmp    BYTE PTR [rip+0xdfb4],0x0        # f48a <error_print_progname@@Base+0x3a2>
    14d6:	0f 85 e8 09 00 00    	jne    1ec4 <error_at_line@@Base+0xf5b>
    14dc:	80 3d a6 df 00 00 00 	cmp    BYTE PTR [rip+0xdfa6],0x0        # f489 <error_print_progname@@Base+0x3a1>
    14e3:	0f 85 db 09 00 00    	jne    1ec4 <error_at_line@@Base+0xf5b>
    14e9:	84 c0                	test   al,al
    14eb:	0f 85 5b 03 00 00    	jne    184c <error_at_line@@Base+0x8e3>
    14f1:	c6 05 91 df 00 00 01 	mov    BYTE PTR [rip+0xdf91],0x1        # f489 <error_print_progname@@Base+0x3a1>
    14f8:	c6 05 8c df 00 00 01 	mov    BYTE PTR [rip+0xdf8c],0x1        # f48b <error_print_progname@@Base+0x3a3>
    14ff:	c6 05 8a df 00 00 01 	mov    BYTE PTR [rip+0xdf8a],0x1        # f490 <error_print_progname@@Base+0x3a8>
    1506:	e8 f5 f6 ff ff       	call   c00 <__ctype_b_loc@plt>
    150b:	31 db                	xor    ebx,ebx
    150d:	4c 8b ad c8 fd ff ff 	mov    r13,QWORD PTR [rbp-0x238]
    1514:	4c 8d 25 65 dd 00 00 	lea    r12,[rip+0xdd65]        # f280 <error_print_progname@@Base+0x198>
    151b:	49 89 c6             	mov    r14,rax
    151e:	eb 51                	jmp    1571 <error_at_line@@Base+0x608>
    1520:	8b 95 00 fe ff ff    	mov    edx,DWORD PTR [rbp-0x200]
    1526:	4d 85 ed             	test   r13,r13
    1529:	0f 85 98 00 00 00    	jne    15c7 <error_at_line@@Base+0x65e>
    152f:	81 fa a0 00 00 00    	cmp    edx,0xa0
    1535:	0f 94 c0             	sete   al
    1538:	81 fa 07 20 00 00    	cmp    edx,0x2007
    153e:	0f 94 c1             	sete   cl
    1541:	08 c8                	or     al,cl
    1543:	0f 84 44 07 00 00    	je     1c8d <error_at_line@@Base+0xd24>
    1549:	90                   	nop
    154a:	66 66 2e 0f 1f 84 00 	data16 cs nop WORD PTR [rax+rax*1+0x0]
    1551:	00 00 00 00 
    1555:	66 66 2e 0f 1f 84 00 	data16 cs nop WORD PTR [rax+rax*1+0x0]
    155c:	00 00 00 00 
    1560:	41 88 04 1c          	mov    BYTE PTR [r12+rbx*1],al
    1564:	48 83 c3 01          	add    rbx,0x1
    1568:	48 81 fb 00 01 00 00 	cmp    rbx,0x100
    156f:	74 6f                	je     15e0 <error_at_line@@Base+0x677>
    1571:	49 8b 16             	mov    rdx,QWORD PTR [r14]
    1574:	b8 01 00 00 00       	mov    eax,0x1
    1579:	f6 44 5a 01 20       	test   BYTE PTR [rdx+rbx*2+0x1],0x20
    157e:	75 e0                	jne    1560 <error_at_line@@Base+0x5f7>
    1580:	48 8d 8d 30 ff ff ff 	lea    rcx,[rbp-0xd0]
    1587:	ba 01 00 00 00       	mov    edx,0x1
    158c:	48 8d b5 2f ff ff ff 	lea    rsi,[rbp-0xd1]
    1593:	88 9d 2f ff ff ff    	mov    BYTE PTR [rbp-0xd1],bl
    1599:	48 8d bd 00 fe ff ff 	lea    rdi,[rbp-0x200]
    15a0:	48 c7 85 30 ff ff ff 	mov    QWORD PTR [rbp-0xd0],0x0
    15a7:	00 00 00 00 
    15ab:	e8 60 f3 ff ff       	call   910 <mbrtowc@plt>
    15b0:	48 83 f8 fd          	cmp    rax,0xfffffffffffffffd
    15b4:	0f 86 66 ff ff ff    	jbe    1520 <error_at_line@@Base+0x5b7>
    15ba:	e8 61 3f 00 00       	call   5520 <error_at_line@@Base+0x45b7>
    15bf:	84 c0                	test   al,al
    15c1:	0f 84 89 05 00 00    	je     1b50 <error_at_line@@Base+0xbe7>
    15c7:	31 c0                	xor    eax,eax
    15c9:	eb 95                	jmp    1560 <error_at_line@@Base+0x5f7>
    15cb:	84 c0                	test   al,al
    15cd:	0f 85 79 02 00 00    	jne    184c <error_at_line@@Base+0x8e3>
    15d3:	80 3d b1 de 00 00 00 	cmp    BYTE PTR [rip+0xdeb1],0x0        # f48b <error_print_progname@@Base+0x3a3>
    15da:	0f 85 26 ff ff ff    	jne    1506 <error_at_line@@Base+0x59d>
    15e0:	48 8b 05 b9 d9 00 00 	mov    rax,QWORD PTR [rip+0xd9b9]        # efa0 <error_at_line@@Base+0xe037>
    15e7:	4c 63 20             	movsxd r12,DWORD PTR [rax]
    15ea:	48 83 bd d0 fd ff ff 	cmp    QWORD PTR [rbp-0x230],0x0
    15f1:	00 
    15f2:	0f 84 6a 05 00 00    	je     1b62 <error_at_line@@Base+0xbf9>
    15f8:	44 39 a5 f0 fd ff ff 	cmp    DWORD PTR [rbp-0x210],r12d
    15ff:	0f 8f b7 06 00 00    	jg     1cbc <error_at_line@@Base+0xd53>
    1605:	48 8b bd d0 fd ff ff 	mov    rdi,QWORD PTR [rbp-0x230]
    160c:	48 8d 35 d7 a2 00 00 	lea    rsi,[rip+0xa2d7]        # b8ea <error_at_line@@Base+0xa981>
    1613:	e8 f8 f3 ff ff       	call   a10 <strcmp@plt>
    1618:	85 c0                	test   eax,eax
    161a:	0f 85 34 08 00 00    	jne    1e54 <error_at_line@@Base+0xeeb>
    1620:	48 8b 05 71 d9 00 00 	mov    rax,QWORD PTR [rip+0xd971]        # ef98 <error_at_line@@Base+0xe02f>
    1627:	4c 8b 20             	mov    r12,QWORD PTR [rax]
    162a:	4c 89 e7             	mov    rdi,r12
    162d:	e8 2e f3 ff ff       	call   960 <fileno_unlocked@plt>
    1632:	48 8d b5 30 ff ff ff 	lea    rsi,[rbp-0xd0]
    1639:	89 c7                	mov    edi,eax
    163b:	e8 80 f5 ff ff       	call   bc0 <fstat@plt>
    1640:	85 c0                	test   eax,eax
    1642:	75 16                	jne    165a <error_at_line@@Base+0x6f1>
    1644:	8b 85 48 ff ff ff    	mov    eax,DWORD PTR [rbp-0xb8]
    164a:	25 00 f0 00 00       	and    eax,0xf000
    164f:	3d 00 80 00 00       	cmp    eax,0x8000
    1654:	0f 84 85 09 00 00    	je     1fdf <error_at_line@@Base+0x1076>
    165a:	4c 89 e7             	mov    rdi,r12
    165d:	45 31 ff             	xor    r15d,r15d
    1660:	e8 db 27 00 00       	call   3e40 <error_at_line@@Base+0x2ed7>
    1665:	c6 85 bf fd ff ff 00 	mov    BYTE PTR [rbp-0x241],0x0
    166c:	49 89 c6             	mov    r14,rax
    166f:	31 c0                	xor    eax,eax
    1671:	48 89 85 f0 fd ff ff 	mov    QWORD PTR [rbp-0x210],rax
    1678:	4d 85 f6             	test   r14,r14
    167b:	0f 84 3b 05 00 00    	je     1bbc <error_at_line@@Base+0xc53>
    1681:	4d 85 ff             	test   r15,r15
    1684:	0f 85 19 05 00 00    	jne    1ba3 <error_at_line@@Base+0xc3a>
    168a:	bf 98 00 00 00       	mov    edi,0x98
    168f:	e8 fc f3 ff ff       	call   a90 <malloc@plt>
    1694:	48 89 85 e0 fd ff ff 	mov    QWORD PTR [rbp-0x220],rax
    169b:	48 85 c0             	test   rax,rax
    169e:	0f 84 18 05 00 00    	je     1bbc <error_at_line@@Base+0xc53>
    16a4:	48 8b 85 e0 fd ff ff 	mov    rax,QWORD PTR [rbp-0x220]
    16ab:	b9 01 00 00 00       	mov    ecx,0x1
    16b0:	c7 00 01 00 00 00    	mov    DWORD PTR [rax],0x1
    16b6:	49 8d 46 18          	lea    rax,[r14+0x18]
    16ba:	4c 89 bd f0 fd ff ff 	mov    QWORD PTR [rbp-0x210],r15
    16c1:	31 db                	xor    ebx,ebx
    16c3:	4d 89 f7             	mov    r15,r14
    16c6:	89 0d c0 dd 00 00    	mov    DWORD PTR [rip+0xddc0],ecx        # f48c <error_print_progname@@Base+0x3a4>
    16cc:	4c 8b ad d0 fd ff ff 	mov    r13,QWORD PTR [rbp-0x230]
    16d3:	41 bc 01 00 00 00    	mov    r12d,0x1
    16d9:	48 89 85 d8 fd ff ff 	mov    QWORD PTR [rbp-0x228],rax
    16e0:	e9 fa 00 00 00       	jmp    17df <error_at_line@@Base+0x876>
    16e5:	0f 1f 00             	nop    DWORD PTR [rax]
    16e8:	48 8b b5 d8 fd ff ff 	mov    rsi,QWORD PTR [rbp-0x228]
    16ef:	31 d2                	xor    edx,edx
    16f1:	49 8d 7f 10          	lea    rdi,[r15+0x10]
    16f5:	e8 e6 f4 ff ff       	call   be0 <getdelim@plt>
    16fa:	48 85 c0             	test   rax,rax
    16fd:	0f 88 f7 03 00 00    	js     1afa <error_at_line@@Base+0xb91>
    1703:	49 83 47 08 01       	add    QWORD PTR [r15+0x8],0x1
    1708:	4d 8b 77 10          	mov    r14,QWORD PTR [r15+0x10]
    170c:	4d 85 ed             	test   r13,r13
    170f:	0f 84 f8 00 00 00    	je     180d <error_at_line@@Base+0x8a4>
    1715:	41 80 7d 00 2d       	cmp    BYTE PTR [r13+0x0],0x2d
    171a:	0f 85 2f 02 00 00    	jne    194f <error_at_line@@Base+0x9e6>
    1720:	41 80 7d 01 00       	cmp    BYTE PTR [r13+0x1],0x0
    1725:	0f 85 24 02 00 00    	jne    194f <error_at_line@@Base+0x9e6>
    172b:	48 8d 05 b8 a1 00 00 	lea    rax,[rip+0xa1b8]        # b8ea <error_at_line@@Base+0xa981>
    1732:	4c 89 f7             	mov    rdi,r14
    1735:	48 89 c6             	mov    rsi,rax
    1738:	48 89 85 c8 fd ff ff 	mov    QWORD PTR [rbp-0x238],rax
    173f:	e8 cc f2 ff ff       	call   a10 <strcmp@plt>
    1744:	85 c0                	test   eax,eax
    1746:	0f 84 7c 01 00 00    	je     18c8 <error_at_line@@Base+0x95f>
    174c:	41 80 3e 00          	cmp    BYTE PTR [r14],0x0
    1750:	0f 84 aa 01 00 00    	je     1900 <error_at_line@@Base+0x997>
    1756:	48 83 bd f0 fd ff ff 	cmp    QWORD PTR [rbp-0x210],0x0
    175d:	00 
    175e:	0f 85 67 02 00 00    	jne    19cb <error_at_line@@Base+0xa62>
    1764:	48 8b 85 e0 fd ff ff 	mov    rax,QWORD PTR [rbp-0x220]
    176b:	48 89 85 c0 fd ff ff 	mov    QWORD PTR [rbp-0x240],rax
    1772:	4c 89 f7             	mov    rdi,r14
    1775:	31 f6                	xor    esi,esi
    1777:	31 c0                	xor    eax,eax
    1779:	e8 82 f3 ff ff       	call   b00 <open@plt>
    177e:	89 c7                	mov    edi,eax
    1780:	83 f8 ff             	cmp    eax,0xffffffff
    1783:	0f 84 b6 0f 00 00    	je     273f <error_at_line@@Base+0x17d6>
    1789:	48 8b 95 c0 fd ff ff 	mov    rdx,QWORD PTR [rbp-0x240]
    1790:	4c 89 f6             	mov    rsi,r14
    1793:	89 85 c0 fd ff ff    	mov    DWORD PTR [rbp-0x240],eax
    1799:	e8 92 69 00 00       	call   8130 <error_at_line@@Base+0x71c7>
    179e:	8b bd c0 fd ff ff    	mov    edi,DWORD PTR [rbp-0x240]
    17a4:	88 85 c8 fd ff ff    	mov    BYTE PTR [rbp-0x238],al
    17aa:	e8 d1 f1 ff ff       	call   980 <close@plt>
    17af:	0f b6 95 c8 fd ff ff 	movzx  edx,BYTE PTR [rbp-0x238]
    17b6:	85 c0                	test   eax,eax
    17b8:	0f 85 81 0f 00 00    	jne    273f <error_at_line@@Base+0x17d6>
    17be:	41 21 d4             	and    r12d,edx
    17c1:	48 83 bd f0 fd ff ff 	cmp    QWORD PTR [rbp-0x210],0x0
    17c8:	00 
    17c9:	75 0d                	jne    17d8 <error_at_line@@Base+0x86f>
    17cb:	48 8b 85 e0 fd ff ff 	mov    rax,QWORD PTR [rbp-0x220]
    17d2:	c7 00 01 00 00 00    	mov    DWORD PTR [rax],0x1
    17d8:	48 81 c3 98 00 00 00 	add    rbx,0x98
    17df:	49 8b 0f             	mov    rcx,QWORD PTR [r15]
    17e2:	48 85 c9             	test   rcx,rcx
    17e5:	0f 85 fd fe ff ff    	jne    16e8 <error_at_line@@Base+0x77f>
    17eb:	49 8b 47 28          	mov    rax,QWORD PTR [r15+0x28]
    17ef:	48 83 38 00          	cmp    QWORD PTR [rax],0x0
    17f3:	0f 84 d7 01 00 00    	je     19d0 <error_at_line@@Base+0xa67>
    17f9:	48 8d 50 08          	lea    rdx,[rax+0x8]
    17fd:	49 89 57 28          	mov    QWORD PTR [r15+0x28],rdx
    1801:	4c 8b 30             	mov    r14,QWORD PTR [rax]
    1804:	4d 85 ed             	test   r13,r13
    1807:	0f 85 08 ff ff ff    	jne    1715 <error_at_line@@Base+0x7ac>
    180d:	41 80 3e 00          	cmp    BYTE PTR [r14],0x0
    1811:	0f 85 3e 01 00 00    	jne    1955 <error_at_line@@Base+0x9ec>
    1817:	31 ff                	xor    edi,edi
    1819:	ba 05 00 00 00       	mov    edx,0x5
    181e:	48 8d 35 65 a1 00 00 	lea    rsi,[rip+0xa165]        # b98a <error_at_line@@Base+0xaa21>
    1825:	e8 96 f0 ff ff       	call   8c0 <dcgettext@plt>
    182a:	48 8d 15 04 a1 00 00 	lea    rdx,[rip+0xa104]        # b935 <error_at_line@@Base+0xa9cc>
    1831:	31 f6                	xor    esi,esi
    1833:	31 ff                	xor    edi,edi
    1835:	48 89 c1             	mov    rcx,rax
    1838:	31 c0                	xor    eax,eax
    183a:	e8 2e f5 ff ff       	call   d6d <error@@Base>
    183f:	e9 03 01 00 00       	jmp    1947 <error_at_line@@Base+0x9de>
    1844:	84 c0                	test   al,al
    1846:	0f 84 ba fc ff ff    	je     1506 <error_at_line@@Base+0x59d>
    184c:	e8 af f3 ff ff       	call   c00 <__ctype_b_loc@plt>
    1851:	48 8d 0d 28 db 00 00 	lea    rcx,[rip+0xdb28]        # f380 <error_print_progname@@Base+0x298>
    1858:	66 0f ef d2          	pxor   xmm2,xmm2
    185c:	66 0f 6f 25 4c b0 00 	movdqa xmm4,XMMWORD PTR [rip+0xb04c]        # c8b0 <error_at_line@@Base+0xb947>
    1863:	00 
    1864:	66 0f 6f 1d 34 b0 00 	movdqa xmm3,XMMWORD PTR [rip+0xb034]        # c8a0 <error_at_line@@Base+0xb937>
    186b:	00 
    186c:	66 0f 6f 2d 1c b0 00 	movdqa xmm5,XMMWORD PTR [rip+0xb01c]        # c890 <error_at_line@@Base+0xb927>
    1873:	00 
    1874:	48 8b 10             	mov    rdx,QWORD PTR [rax]
    1877:	31 c0                	xor    eax,eax
    1879:	0f 1f 80 00 00 00 00 	nop    DWORD PTR [rax+0x0]
    1880:	f3 0f 6f 04 42       	movdqu xmm0,XMMWORD PTR [rdx+rax*2]
    1885:	f3 0f 6f 4c 42 10    	movdqu xmm1,XMMWORD PTR [rdx+rax*2+0x10]
    188b:	66 0f db c4          	pand   xmm0,xmm4
    188f:	66 0f db cc          	pand   xmm1,xmm4
    1893:	66 0f 75 c2          	pcmpeqw xmm0,xmm2
    1897:	66 0f 75 ca          	pcmpeqw xmm1,xmm2
    189b:	66 0f 75 c2          	pcmpeqw xmm0,xmm2
    189f:	66 0f 75 ca          	pcmpeqw xmm1,xmm2
    18a3:	66 0f db c3          	pand   xmm0,xmm3
    18a7:	66 0f db cb          	pand   xmm1,xmm3
    18ab:	66 0f 67 c1          	packuswb xmm0,xmm1
    18af:	66 0f db c5          	pand   xmm0,xmm5
    18b3:	0f 29 04 01          	movaps XMMWORD PTR [rcx+rax*1],xmm0
    18b7:	48 83 c0 10          	add    rax,0x10
    18bb:	48 3d 00 01 00 00    	cmp    rax,0x100
    18c1:	75 bd                	jne    1880 <error_at_line@@Base+0x917>
    18c3:	e9 0b fd ff ff       	jmp    15d3 <error_at_line@@Base+0x66a>
    18c8:	4c 89 f7             	mov    rdi,r14
    18cb:	e8 40 63 00 00       	call   7c10 <error_at_line@@Base+0x6ca7>
    18d0:	31 ff                	xor    edi,edi
    18d2:	ba 05 00 00 00       	mov    edx,0x5
    18d7:	48 8d 35 42 aa 00 00 	lea    rsi,[rip+0xaa42]        # c320 <error_at_line@@Base+0xb3b7>
    18de:	49 89 c4             	mov    r12,rax
    18e1:	e8 da ef ff ff       	call   8c0 <dcgettext@plt>
    18e6:	31 f6                	xor    esi,esi
    18e8:	31 ff                	xor    edi,edi
    18ea:	4c 89 e1             	mov    rcx,r12
    18ed:	48 89 c2             	mov    rdx,rax
    18f0:	31 c0                	xor    eax,eax
    18f2:	e8 76 f4 ff ff       	call   d6d <error@@Base>
    18f7:	41 80 3e 00          	cmp    BYTE PTR [r14],0x0
    18fb:	75 4a                	jne    1947 <error_at_line@@Base+0x9de>
    18fd:	0f 1f 00             	nop    DWORD PTR [rax]
    1900:	ba 05 00 00 00       	mov    edx,0x5
    1905:	48 8d 35 7e a0 00 00 	lea    rsi,[rip+0xa07e]        # b98a <error_at_line@@Base+0xaa21>
    190c:	31 ff                	xor    edi,edi
    190e:	e8 ad ef ff ff       	call   8c0 <dcgettext@plt>
    1913:	49 89 c6             	mov    r14,rax
    1916:	49 83 3f 00          	cmp    QWORD PTR [r15],0x0
    191a:	0f 84 9a 00 00 00    	je     19ba <error_at_line@@Base+0xa51>
    1920:	4d 8b 67 08          	mov    r12,QWORD PTR [r15+0x8]
    1924:	4c 89 ef             	mov    rdi,r13
    1927:	e8 44 63 00 00       	call   7c70 <error_at_line@@Base+0x6d07>
    192c:	4d 89 f1             	mov    r9,r14
    192f:	4d 89 e0             	mov    r8,r12
    1932:	31 f6                	xor    esi,esi
    1934:	48 89 c1             	mov    rcx,rax
    1937:	48 8d 15 6a a0 00 00 	lea    rdx,[rip+0xa06a]        # b9a8 <error_at_line@@Base+0xaa3f>
    193e:	31 ff                	xor    edi,edi
    1940:	31 c0                	xor    eax,eax
    1942:	e8 26 f4 ff ff       	call   d6d <error@@Base>
    1947:	45 31 e4             	xor    r12d,r12d
    194a:	e9 72 fe ff ff       	jmp    17c1 <error_at_line@@Base+0x858>
    194f:	41 80 3e 00          	cmp    BYTE PTR [r14],0x0
    1953:	74 ab                	je     1900 <error_at_line@@Base+0x997>
    1955:	48 83 bd f0 fd ff ff 	cmp    QWORD PTR [rbp-0x210],0x0
    195c:	00 
    195d:	0f 85 43 03 00 00    	jne    1ca6 <error_at_line@@Base+0xd3d>
    1963:	48 8d 0d 80 9f 00 00 	lea    rcx,[rip+0x9f80]        # b8ea <error_at_line@@Base+0xa981>
    196a:	31 c0                	xor    eax,eax
    196c:	48 89 8d c8 fd ff ff 	mov    QWORD PTR [rbp-0x238],rcx
    1973:	48 8b 95 e0 fd ff ff 	mov    rdx,QWORD PTR [rbp-0x220]
    197a:	48 8b b5 c8 fd ff ff 	mov    rsi,QWORD PTR [rbp-0x238]
    1981:	4c 89 f7             	mov    rdi,r14
    1984:	48 01 d0             	add    rax,rdx
    1987:	48 89 85 c0 fd ff ff 	mov    QWORD PTR [rbp-0x240],rax
    198e:	e8 7d f0 ff ff       	call   a10 <strcmp@plt>
    1993:	85 c0                	test   eax,eax
    1995:	0f 85 d7 fd ff ff    	jne    1772 <error_at_line@@Base+0x809>
    199b:	48 8b 95 c0 fd ff ff 	mov    rdx,QWORD PTR [rbp-0x240]
    19a2:	4c 89 f6             	mov    rsi,r14
    19a5:	31 ff                	xor    edi,edi
    19a7:	c6 05 6a d8 00 00 01 	mov    BYTE PTR [rip+0xd86a],0x1        # f218 <error_print_progname@@Base+0x130>
    19ae:	e8 7d 67 00 00       	call   8130 <error_at_line@@Base+0x71c7>
    19b3:	89 c2                	mov    edx,eax
    19b5:	e9 04 fe ff ff       	jmp    17be <error_at_line@@Base+0x855>
    19ba:	4d 8b 67 28          	mov    r12,QWORD PTR [r15+0x28]
    19be:	4d 2b 67 20          	sub    r12,QWORD PTR [r15+0x20]
    19c2:	49 c1 fc 03          	sar    r12,0x3
    19c6:	e9 59 ff ff ff       	jmp    1924 <error_at_line@@Base+0x9bb>
    19cb:	48 89 d8             	mov    rax,rbx
    19ce:	eb a3                	jmp    1973 <error_at_line@@Base+0xa0a>
    19d0:	4d 89 fe             	mov    r14,r15
    19d3:	48 83 bd d0 fd ff ff 	cmp    QWORD PTR [rbp-0x230],0x0
    19da:	00 
    19db:	0f 94 c0             	sete   al
    19de:	44 20 e0             	and    al,r12b
    19e1:	74 1a                	je     19fd <error_at_line@@Base+0xa94>
    19e3:	49 83 3e 00          	cmp    QWORD PTR [r14],0x0
    19e7:	0f 84 e1 05 00 00    	je     1fce <error_at_line@@Base+0x1065>
    19ed:	49 8b 56 08          	mov    rdx,QWORD PTR [r14+0x8]
    19f1:	41 89 c4             	mov    r12d,eax
    19f4:	48 85 d2             	test   rdx,rdx
    19f7:	0f 84 0d 05 00 00    	je     1f0a <error_at_line@@Base+0xfa1>
    19fd:	80 bd bf fd ff ff 00 	cmp    BYTE PTR [rbp-0x241],0x0
    1a04:	0f 85 ca 01 00 00    	jne    1bd4 <error_at_line@@Base+0xc6b>
    1a0a:	8b 05 68 d8 00 00    	mov    eax,DWORD PTR [rip+0xd868]        # f278 <error_print_progname@@Base+0x190>
    1a10:	83 f8 03             	cmp    eax,0x3
    1a13:	0f 84 96 00 00 00    	je     1aaf <error_at_line@@Base+0xb46>
    1a19:	85 c0                	test   eax,eax
    1a1b:	75 14                	jne    1a31 <error_at_line@@Base+0xac8>
    1a1d:	49 83 3e 00          	cmp    QWORD PTR [r14],0x0
    1a21:	0f 84 f7 03 00 00    	je     1e1e <error_at_line@@Base+0xeb5>
    1a27:	49 8b 46 08          	mov    rax,QWORD PTR [r14+0x8]
    1a2b:	48 83 f8 01          	cmp    rax,0x1
    1a2f:	76 7e                	jbe    1aaf <error_at_line@@Base+0xb46>
    1a31:	80 3d 30 d8 00 00 00 	cmp    BYTE PTR [rip+0xd830],0x0        # f268 <error_print_progname@@Base+0x180>
    1a38:	0f 85 69 0d 00 00    	jne    27a7 <error_at_line@@Base+0x183e>
    1a3e:	80 3d 13 d8 00 00 00 	cmp    BYTE PTR [rip+0xd813],0x0        # f258 <error_print_progname@@Base+0x170>
    1a45:	0f 85 ca 0d 00 00    	jne    2815 <error_at_line@@Base+0x18ac>
    1a4b:	80 3d f6 d7 00 00 00 	cmp    BYTE PTR [rip+0xd7f6],0x0        # f248 <error_print_progname@@Base+0x160>
    1a52:	0f 85 86 0d 00 00    	jne    27de <error_at_line@@Base+0x1875>
    1a58:	80 3d d9 d7 00 00 00 	cmp    BYTE PTR [rip+0xd7d9],0x0        # f238 <error_print_progname@@Base+0x150>
    1a5f:	0f 85 0b 0d 00 00    	jne    2770 <error_at_line@@Base+0x1807>
    1a65:	45 31 c9             	xor    r9d,r9d
    1a68:	83 3d 09 d8 00 00 02 	cmp    DWORD PTR [rip+0xd809],0x2        # f278 <error_print_progname@@Base+0x190>
    1a6f:	74 16                	je     1a87 <error_at_line@@Base+0xb1e>
    1a71:	ba 05 00 00 00       	mov    edx,0x5
    1a76:	48 8d 35 93 9e 00 00 	lea    rsi,[rip+0x9e93]        # b910 <error_at_line@@Base+0xa9a7>
    1a7d:	31 ff                	xor    edi,edi
    1a7f:	e8 3c ee ff ff       	call   8c0 <dcgettext@plt>
    1a84:	49 89 c1             	mov    r9,rax
    1a87:	4c 8b 05 a2 d7 00 00 	mov    r8,QWORD PTR [rip+0xd7a2]        # f230 <error_print_progname@@Base+0x148>
    1a8e:	48 8b 0d ab d7 00 00 	mov    rcx,QWORD PTR [rip+0xd7ab]        # f240 <error_print_progname@@Base+0x158>
    1a95:	48 8b 15 b4 d7 00 00 	mov    rdx,QWORD PTR [rip+0xd7b4]        # f250 <error_print_progname@@Base+0x168>
    1a9c:	48 8b 35 bd d7 00 00 	mov    rsi,QWORD PTR [rip+0xd7bd]        # f260 <error_print_progname@@Base+0x178>
    1aa3:	48 8b 3d c6 d7 00 00 	mov    rdi,QWORD PTR [rip+0xd7c6]        # f270 <error_print_progname@@Base+0x188>
    1aaa:	e8 21 62 00 00       	call   7cd0 <error_at_line@@Base+0x6d67>
    1aaf:	4c 89 f7             	mov    rdi,r14
    1ab2:	e8 d9 23 00 00       	call   3e90 <error_at_line@@Base+0x2f27>
    1ab7:	48 8b bd e0 fd ff ff 	mov    rdi,QWORD PTR [rbp-0x220]
    1abe:	e8 0d ed ff ff       	call   7d0 <free@plt>
    1ac3:	80 3d 4e d7 00 00 00 	cmp    BYTE PTR [rip+0xd74e],0x0        # f218 <error_print_progname@@Base+0x130>
    1aca:	0f 85 81 01 00 00    	jne    1c51 <error_at_line@@Base+0xce8>
    1ad0:	41 83 f4 01          	xor    r12d,0x1
    1ad4:	41 0f b6 c4          	movzx  eax,r12b
    1ad8:	48 8b 55 c8          	mov    rdx,QWORD PTR [rbp-0x38]
    1adc:	64 48 2b 14 25 28 00 	sub    rdx,QWORD PTR fs:0x28
    1ae3:	00 00 
    1ae5:	0f 85 80 0c 00 00    	jne    276b <error_at_line@@Base+0x1802>
    1aeb:	48 8d 65 d8          	lea    rsp,[rbp-0x28]
    1aef:	5b                   	pop    rbx
    1af0:	41 5c                	pop    r12
    1af2:	41 5d                	pop    r13
    1af4:	41 5e                	pop    r14
    1af6:	41 5f                	pop    r15
    1af8:	5d                   	pop    rbp
    1af9:	c3                   	ret
    1afa:	49 8b 3f             	mov    rdi,QWORD PTR [r15]
    1afd:	4d 89 fe             	mov    r14,r15
    1b00:	e8 3b ef ff ff       	call   a40 <feof@plt>
    1b05:	85 c0                	test   eax,eax
    1b07:	0f 85 c6 fe ff ff    	jne    19d3 <error_at_line@@Base+0xa6a>
    1b0d:	48 8b bd d0 fd ff ff 	mov    rdi,QWORD PTR [rbp-0x230]
    1b14:	e8 57 61 00 00       	call   7c70 <error_at_line@@Base+0x6d07>
    1b19:	ba 05 00 00 00       	mov    edx,0x5
    1b1e:	48 8d 35 8e 9e 00 00 	lea    rsi,[rip+0x9e8e]        # b9b3 <error_at_line@@Base+0xaa4a>
    1b25:	31 ff                	xor    edi,edi
    1b27:	49 89 c4             	mov    r12,rax
    1b2a:	e8 91 ed ff ff       	call   8c0 <dcgettext@plt>
    1b2f:	48 89 c3             	mov    rbx,rax
    1b32:	e8 c9 ec ff ff       	call   800 <__errno_location@plt>
    1b37:	4c 89 e1             	mov    rcx,r12
    1b3a:	48 89 da             	mov    rdx,rbx
    1b3d:	31 ff                	xor    edi,edi
    1b3f:	8b 30                	mov    esi,DWORD PTR [rax]
    1b41:	31 c0                	xor    eax,eax
    1b43:	45 31 e4             	xor    r12d,r12d
    1b46:	e8 22 f2 ff ff       	call   d6d <error@@Base>
    1b4b:	e9 ad fe ff ff       	jmp    19fd <error_at_line@@Base+0xa94>
    1b50:	0f b6 85 2f ff ff ff 	movzx  eax,BYTE PTR [rbp-0xd1]
    1b57:	89 85 00 fe ff ff    	mov    DWORD PTR [rbp-0x200],eax
    1b5d:	e9 be f9 ff ff       	jmp    1520 <error_at_line@@Base+0x5b7>
    1b62:	8b 9d f0 fd ff ff    	mov    ebx,DWORD PTR [rbp-0x210]
    1b68:	44 39 e3             	cmp    ebx,r12d
    1b6b:	0f 8e d2 01 00 00    	jle    1d43 <error_at_line@@Base+0xdda>
    1b71:	48 8b 8d e0 fd ff ff 	mov    rcx,QWORD PTR [rbp-0x220]
    1b78:	49 63 c4             	movsxd rax,r12d
    1b7b:	48 8d 04 c1          	lea    rax,[rcx+rax*8]
    1b7f:	48 89 c7             	mov    rdi,rax
    1b82:	48 89 85 f0 fd ff ff 	mov    QWORD PTR [rbp-0x210],rax
    1b89:	e8 72 22 00 00       	call   3e00 <error_at_line@@Base+0x2e97>
    1b8e:	49 89 c6             	mov    r14,rax
    1b91:	48 85 c0             	test   rax,rax
    1b94:	74 26                	je     1bbc <error_at_line@@Base+0xc53>
    1b96:	c6 85 bf fd ff ff 00 	mov    BYTE PTR [rbp-0x241],0x0
    1b9d:	41 89 df             	mov    r15d,ebx
    1ba0:	45 29 e7             	sub    r15d,r12d
    1ba3:	b8 98 00 00 00       	mov    eax,0x98
    1ba8:	49 f7 e7             	mul    r15
    1bab:	0f 81 ca 01 00 00    	jno    1d7b <error_at_line@@Base+0xe12>
    1bb1:	e8 4a ec ff ff       	call   800 <__errno_location@plt>
    1bb6:	c7 00 0c 00 00 00    	mov    DWORD PTR [rax],0xc
    1bbc:	48 8b 45 c8          	mov    rax,QWORD PTR [rbp-0x38]
    1bc0:	64 48 2b 04 25 28 00 	sub    rax,QWORD PTR fs:0x28
    1bc7:	00 00 
    1bc9:	0f 85 9c 0b 00 00    	jne    276b <error_at_line@@Base+0x1802>
    1bcf:	e8 7c 5d 00 00       	call   7950 <error_at_line@@Base+0x69e7>
    1bd4:	48 8b 85 b0 fd ff ff 	mov    rax,QWORD PTR [rbp-0x250]
    1bdb:	48 8d bd 18 fe ff ff 	lea    rdi,[rbp-0x1e8]
    1be2:	48 89 85 00 fe ff ff 	mov    QWORD PTR [rbp-0x200],rax
    1be9:	48 8b 85 a0 fd ff ff 	mov    rax,QWORD PTR [rbp-0x260]
    1bf0:	48 89 85 30 fe ff ff 	mov    QWORD PTR [rbp-0x1d0],rax
    1bf7:	48 8b 85 a8 fd ff ff 	mov    rax,QWORD PTR [rbp-0x258]
    1bfe:	48 89 85 38 fe ff ff 	mov    QWORD PTR [rbp-0x1c8],rax
    1c05:	48 8b 85 98 fd ff ff 	mov    rax,QWORD PTR [rbp-0x268]
    1c0c:	48 89 85 80 fe ff ff 	mov    QWORD PTR [rbp-0x180],rax
    1c13:	48 89 85 88 fe ff ff 	mov    QWORD PTR [rbp-0x178],rax
    1c1a:	48 8b 85 90 fd ff ff 	mov    rax,QWORD PTR [rbp-0x270]
    1c21:	48 89 85 d8 fe ff ff 	mov    QWORD PTR [rbp-0x128],rax
    1c28:	48 89 85 e0 fe ff ff 	mov    QWORD PTR [rbp-0x120],rax
    1c2f:	e8 dc 34 00 00       	call   5110 <error_at_line@@Base+0x41a7>
    1c34:	48 8d bd 70 fe ff ff 	lea    rdi,[rbp-0x190]
    1c3b:	e8 d0 34 00 00       	call   5110 <error_at_line@@Base+0x41a7>
    1c40:	48 8d bd c8 fe ff ff 	lea    rdi,[rbp-0x138]
    1c47:	e8 c4 34 00 00       	call   5110 <error_at_line@@Base+0x41a7>
    1c4c:	e9 b9 fd ff ff       	jmp    1a0a <error_at_line@@Base+0xaa1>
    1c51:	31 ff                	xor    edi,edi
    1c53:	e8 28 ed ff ff       	call   980 <close@plt>
    1c58:	85 c0                	test   eax,eax
    1c5a:	0f 84 70 fe ff ff    	je     1ad0 <error_at_line@@Base+0xb67>
    1c60:	e8 9b eb ff ff       	call   800 <__errno_location@plt>
    1c65:	48 8b 55 c8          	mov    rdx,QWORD PTR [rbp-0x38]
    1c69:	64 48 2b 14 25 28 00 	sub    rdx,QWORD PTR fs:0x28
    1c70:	00 00 
    1c72:	0f 85 f3 0a 00 00    	jne    276b <error_at_line@@Base+0x1802>
    1c78:	8b 30                	mov    esi,DWORD PTR [rax]
    1c7a:	48 8d 15 69 9c 00 00 	lea    rdx,[rip+0x9c69]        # b8ea <error_at_line@@Base+0xa981>
    1c81:	bf 01 00 00 00       	mov    edi,0x1
    1c86:	31 c0                	xor    eax,eax
    1c88:	e8 e0 f0 ff ff       	call   d6d <error@@Base>
    1c8d:	81 fa 60 20 00 00    	cmp    edx,0x2060
    1c93:	0f 94 c0             	sete   al
    1c96:	81 fa 2f 20 00 00    	cmp    edx,0x202f
    1c9c:	0f 94 c2             	sete   dl
    1c9f:	09 d0                	or     eax,edx
    1ca1:	e9 ba f8 ff ff       	jmp    1560 <error_at_line@@Base+0x5f7>
    1ca6:	48 8d 35 3d 9c 00 00 	lea    rsi,[rip+0x9c3d]        # b8ea <error_at_line@@Base+0xa981>
    1cad:	48 89 d8             	mov    rax,rbx
    1cb0:	48 89 b5 c8 fd ff ff 	mov    QWORD PTR [rbp-0x238],rsi
    1cb7:	e9 b7 fc ff ff       	jmp    1973 <error_at_line@@Base+0xa0a>
    1cbc:	48 8b 85 e0 fd ff ff 	mov    rax,QWORD PTR [rbp-0x220]
    1cc3:	4a 8b 3c e0          	mov    rdi,QWORD PTR [rax+r12*8]
    1cc7:	e8 44 5f 00 00       	call   7c10 <error_at_line@@Base+0x6ca7>
    1ccc:	ba 05 00 00 00       	mov    edx,0x5
    1cd1:	48 8d 35 86 9c 00 00 	lea    rsi,[rip+0x9c86]        # b95e <error_at_line@@Base+0xa9f5>
    1cd8:	31 ff                	xor    edi,edi
    1cda:	48 89 c3             	mov    rbx,rax
    1cdd:	e8 de eb ff ff       	call   8c0 <dcgettext@plt>
    1ce2:	48 89 d9             	mov    rcx,rbx
    1ce5:	31 f6                	xor    esi,esi
    1ce7:	31 ff                	xor    edi,edi
    1ce9:	48 89 c2             	mov    rdx,rax
    1cec:	31 c0                	xor    eax,eax
    1cee:	e8 7a f0 ff ff       	call   d6d <error@@Base>
    1cf3:	ba 05 00 00 00       	mov    edx,0x5
    1cf8:	48 8d 35 c9 a5 00 00 	lea    rsi,[rip+0xa5c9]        # c2c8 <error_at_line@@Base+0xb35f>
    1cff:	31 ff                	xor    edi,edi
    1d01:	e8 ba eb ff ff       	call   8c0 <dcgettext@plt>
    1d06:	48 8d 15 98 9a 00 00 	lea    rdx,[rip+0x9a98]        # b7a5 <error_at_line@@Base+0xa83c>
    1d0d:	be 02 00 00 00       	mov    esi,0x2
    1d12:	48 89 c1             	mov    rcx,rax
    1d15:	48 8b 05 c4 d2 00 00 	mov    rax,QWORD PTR [rip+0xd2c4]        # efe0 <error_at_line@@Base+0xe077>
    1d1c:	48 8b 38             	mov    rdi,QWORD PTR [rax]
    1d1f:	31 c0                	xor    eax,eax
    1d21:	e8 5a ee ff ff       	call   b80 <__fprintf_chk@plt>
    1d26:	48 8b 45 c8          	mov    rax,QWORD PTR [rbp-0x38]
    1d2a:	64 48 2b 04 25 28 00 	sub    rax,QWORD PTR fs:0x28
    1d31:	00 00 
    1d33:	0f 85 32 0a 00 00    	jne    276b <error_at_line@@Base+0x1802>
    1d39:	bf 01 00 00 00       	mov    edi,0x1
    1d3e:	e8 fd 25 00 00       	call   4340 <error_at_line@@Base+0x33d7>
    1d43:	48 8d 3d d6 d4 00 00 	lea    rdi,[rip+0xd4d6]        # f220 <error_print_progname@@Base+0x138>
    1d4a:	e8 b1 20 00 00       	call   3e00 <error_at_line@@Base+0x2e97>
    1d4f:	49 89 c6             	mov    r14,rax
    1d52:	48 85 c0             	test   rax,rax
    1d55:	0f 84 61 fe ff ff    	je     1bbc <error_at_line@@Base+0xc53>
    1d5b:	c6 85 bf fd ff ff 00 	mov    BYTE PTR [rbp-0x241],0x0
    1d62:	48 8d 05 b7 d4 00 00 	lea    rax,[rip+0xd4b7]        # f220 <error_print_progname@@Base+0x138>
    1d69:	41 bf 01 00 00 00    	mov    r15d,0x1
    1d6f:	48 89 85 f0 fd ff ff 	mov    QWORD PTR [rbp-0x210],rax
    1d76:	b8 98 00 00 00       	mov    eax,0x98
    1d7b:	48 85 c0             	test   rax,rax
    1d7e:	ba 01 00 00 00       	mov    edx,0x1
    1d83:	48 0f 45 d0          	cmovne rdx,rax
    1d87:	48 89 d7             	mov    rdi,rdx
    1d8a:	e8 01 ed ff ff       	call   a90 <malloc@plt>
    1d8f:	48 89 85 e0 fd ff ff 	mov    QWORD PTR [rbp-0x220],rax
    1d96:	48 85 c0             	test   rax,rax
    1d99:	0f 84 1d fe ff ff    	je     1bbc <error_at_line@@Base+0xc53>
    1d9f:	49 83 ff 01          	cmp    r15,0x1
    1da3:	0f 84 28 01 00 00    	je     1ed1 <error_at_line@@Base+0xf68>
    1da9:	4d 85 ff             	test   r15,r15
    1dac:	0f 8e 98 00 00 00    	jle    1e4a <error_at_line@@Base+0xee1>
    1db2:	48 8b 85 e0 fd ff ff 	mov    rax,QWORD PTR [rbp-0x220]
    1db9:	48 8b 9d f0 fd ff ff 	mov    rbx,QWORD PTR [rbp-0x210]
    1dc0:	4c 89 b5 d8 fd ff ff 	mov    QWORD PTR [rbp-0x228],r14
    1dc7:	45 31 e4             	xor    r12d,r12d
    1dca:	48 89 85 f0 fd ff ff 	mov    QWORD PTR [rbp-0x210],rax
    1dd1:	4c 8d 68 08          	lea    r13,[rax+0x8]
    1dd5:	eb 1e                	jmp    1df5 <error_at_line@@Base+0xe8c>
    1dd7:	4c 89 ee             	mov    rsi,r13
    1dda:	31 ff                	xor    edi,edi
    1ddc:	e8 df ed ff ff       	call   bc0 <fstat@plt>
    1de1:	49 83 c4 01          	add    r12,0x1
    1de5:	41 89 45 f8          	mov    DWORD PTR [r13-0x8],eax
    1de9:	49 81 c5 98 00 00 00 	add    r13,0x98
    1df0:	4d 39 fc             	cmp    r12,r15
    1df3:	74 3a                	je     1e2f <error_at_line@@Base+0xec6>
    1df5:	4e 8b 34 e3          	mov    r14,QWORD PTR [rbx+r12*8]
    1df9:	4d 85 f6             	test   r14,r14
    1dfc:	74 d9                	je     1dd7 <error_at_line@@Base+0xe6e>
    1dfe:	48 8d 35 e5 9a 00 00 	lea    rsi,[rip+0x9ae5]        # b8ea <error_at_line@@Base+0xa981>
    1e05:	4c 89 f7             	mov    rdi,r14
    1e08:	e8 03 ec ff ff       	call   a10 <strcmp@plt>
    1e0d:	85 c0                	test   eax,eax
    1e0f:	74 c6                	je     1dd7 <error_at_line@@Base+0xe6e>
    1e11:	4c 89 ee             	mov    rsi,r13
    1e14:	4c 89 f7             	mov    rdi,r14
    1e17:	e8 34 ec ff ff       	call   a50 <stat@plt>
    1e1c:	eb c3                	jmp    1de1 <error_at_line@@Base+0xe78>
    1e1e:	49 8b 46 28          	mov    rax,QWORD PTR [r14+0x28]
    1e22:	49 2b 46 20          	sub    rax,QWORD PTR [r14+0x20]
    1e26:	48 c1 f8 03          	sar    rax,0x3
    1e2a:	e9 fc fb ff ff       	jmp    1a2b <error_at_line@@Base+0xac2>
    1e2f:	83 3d 42 d4 00 00 02 	cmp    DWORD PTR [rip+0xd442],0x2        # f278 <error_print_progname@@Base+0x190>
    1e36:	48 8b 95 f0 fd ff ff 	mov    rdx,QWORD PTR [rbp-0x210]
    1e3d:	4c 8b b5 d8 fd ff ff 	mov    r14,QWORD PTR [rbp-0x228]
    1e44:	0f 85 df 00 00 00    	jne    1f29 <error_at_line@@Base+0xfc0>
    1e4a:	b9 01 00 00 00       	mov    ecx,0x1
    1e4f:	e9 62 f8 ff ff       	jmp    16b6 <error_at_line@@Base+0x74d>
    1e54:	48 8b bd d0 fd ff ff 	mov    rdi,QWORD PTR [rbp-0x230]
    1e5b:	48 8d 35 11 9c 00 00 	lea    rsi,[rip+0x9c11]        # ba73 <error_at_line@@Base+0xab0a>
    1e62:	e8 a9 ec ff ff       	call   b10 <fopen@plt>
    1e67:	49 89 c4             	mov    r12,rax
    1e6a:	48 85 c0             	test   rax,rax
    1e6d:	0f 85 b7 f7 ff ff    	jne    162a <error_at_line@@Base+0x6c1>
    1e73:	48 8b bd d0 fd ff ff 	mov    rdi,QWORD PTR [rbp-0x230]
    1e7a:	e8 91 5d 00 00       	call   7c10 <error_at_line@@Base+0x6ca7>
    1e7f:	ba 05 00 00 00       	mov    edx,0x5
    1e84:	31 ff                	xor    edi,edi
    1e86:	48 8d 35 e2 9a 00 00 	lea    rsi,[rip+0x9ae2]        # b96f <error_at_line@@Base+0xaa06>
    1e8d:	49 89 c4             	mov    r12,rax
    1e90:	e8 2b ea ff ff       	call   8c0 <dcgettext@plt>
    1e95:	48 89 c3             	mov    rbx,rax
    1e98:	e8 63 e9 ff ff       	call   800 <__errno_location@plt>
    1e9d:	48 8b 55 c8          	mov    rdx,QWORD PTR [rbp-0x38]
    1ea1:	64 48 2b 14 25 28 00 	sub    rdx,QWORD PTR fs:0x28
    1ea8:	00 00 
    1eaa:	0f 85 bb 08 00 00    	jne    276b <error_at_line@@Base+0x1802>
    1eb0:	8b 30                	mov    esi,DWORD PTR [rax]
    1eb2:	4c 89 e1             	mov    rcx,r12
    1eb5:	48 89 da             	mov    rdx,rbx
    1eb8:	bf 01 00 00 00       	mov    edi,0x1
    1ebd:	31 c0                	xor    eax,eax
    1ebf:	e8 a9 ee ff ff       	call   d6d <error@@Base>
    1ec4:	84 c0                	test   al,al
    1ec6:	0f 84 14 f7 ff ff    	je     15e0 <error_at_line@@Base+0x677>
    1ecc:	e9 7b f9 ff ff       	jmp    184c <error_at_line@@Base+0x8e3>
    1ed1:	0f b6 15 b3 d5 00 00 	movzx  edx,BYTE PTR [rip+0xd5b3]        # f48b <error_print_progname@@Base+0x3a3>
    1ed8:	0f b6 05 b1 d5 00 00 	movzx  eax,BYTE PTR [rip+0xd5b1]        # f490 <error_print_progname@@Base+0x3a8>
    1edf:	01 d0                	add    eax,edx
    1ee1:	0f b6 15 a2 d5 00 00 	movzx  edx,BYTE PTR [rip+0xd5a2]        # f48a <error_print_progname@@Base+0x3a2>
    1ee8:	01 d0                	add    eax,edx
    1eea:	0f b6 15 98 d5 00 00 	movzx  edx,BYTE PTR [rip+0xd598]        # f489 <error_print_progname@@Base+0x3a1>
    1ef1:	01 d0                	add    eax,edx
    1ef3:	0f b6 15 8e d5 00 00 	movzx  edx,BYTE PTR [rip+0xd58e]        # f488 <error_print_progname@@Base+0x3a0>
    1efa:	01 d0                	add    eax,edx
    1efc:	83 e8 01             	sub    eax,0x1
    1eff:	0f 85 ad fe ff ff    	jne    1db2 <error_at_line@@Base+0xe49>
    1f05:	e9 9a f7 ff ff       	jmp    16a4 <error_at_line@@Base+0x73b>
    1f0a:	48 8b 95 e0 fd ff ff 	mov    rdx,QWORD PTR [rbp-0x220]
    1f11:	31 f6                	xor    esi,esi
    1f13:	31 ff                	xor    edi,edi
    1f15:	c6 05 fc d2 00 00 01 	mov    BYTE PTR [rip+0xd2fc],0x1        # f218 <error_print_progname@@Base+0x130>
    1f1c:	e8 0f 62 00 00       	call   8130 <error_at_line@@Base+0x71c7>
    1f21:	41 89 c4             	mov    r12d,eax
    1f24:	e9 d4 fa ff ff       	jmp    19fd <error_at_line@@Base+0xa94>
    1f29:	48 8b 85 e0 fd ff ff 	mov    rax,QWORD PTR [rbp-0x220]
    1f30:	83 38 00             	cmp    DWORD PTR [rax],0x0
    1f33:	0f 8f 11 ff ff ff    	jg     1e4a <error_at_line@@Base+0xee1>
    1f39:	41 b8 01 00 00 00    	mov    r8d,0x1
    1f3f:	31 c0                	xor    eax,eax
    1f41:	31 ff                	xor    edi,edi
    1f43:	49 b9 00 00 00 00 00 	movabs r9,0x8000000000000000
    1f4a:	00 00 80 
    1f4d:	eb 16                	jmp    1f65 <error_at_line@@Base+0xffc>
    1f4f:	41 b8 07 00 00 00    	mov    r8d,0x7
    1f55:	48 83 c7 01          	add    rdi,0x1
    1f59:	48 81 c2 98 00 00 00 	add    rdx,0x98
    1f60:	4c 39 ff             	cmp    rdi,r15
    1f63:	74 31                	je     1f96 <error_at_line@@Base+0x102d>
    1f65:	83 3a 00             	cmp    DWORD PTR [rdx],0x0
    1f68:	75 eb                	jne    1f55 <error_at_line@@Base+0xfec>
    1f6a:	8b 4a 20             	mov    ecx,DWORD PTR [rdx+0x20]
    1f6d:	81 e1 00 f0 00 00    	and    ecx,0xf000
    1f73:	81 f9 00 80 00 00    	cmp    ecx,0x8000
    1f79:	75 d4                	jne    1f4f <error_at_line@@Base+0xfe6>
    1f7b:	31 c9                	xor    ecx,ecx
    1f7d:	4c 01 c8             	add    rax,r9
    1f80:	48 03 42 38          	add    rax,QWORD PTR [rdx+0x38]
    1f84:	0f 90 c1             	seto   cl
    1f87:	4c 01 c8             	add    rax,r9
    1f8a:	48 85 c9             	test   rcx,rcx
    1f8d:	74 c6                	je     1f55 <error_at_line@@Base+0xfec>
    1f8f:	48 c7 c0 ff ff ff ff 	mov    rax,0xffffffffffffffff
    1f96:	b9 01 00 00 00       	mov    ecx,0x1
    1f9b:	bf 0a 00 00 00       	mov    edi,0xa
    1fa0:	eb 16                	jmp    1fb8 <error_at_line@@Base+0x104f>
    1fa2:	0f 1f 00             	nop    DWORD PTR [rax]
    1fa5:	66 66 2e 0f 1f 84 00 	data16 cs nop WORD PTR [rax+rax*1+0x0]
    1fac:	00 00 00 00 
    1fb0:	31 d2                	xor    edx,edx
    1fb2:	83 c1 01             	add    ecx,0x1
    1fb5:	48 f7 f7             	div    rdi
    1fb8:	48 83 f8 09          	cmp    rax,0x9
    1fbc:	77 f2                	ja     1fb0 <error_at_line@@Base+0x1047>
    1fbe:	44 39 c1             	cmp    ecx,r8d
    1fc1:	b8 07 00 00 00       	mov    eax,0x7
    1fc6:	0f 4c c8             	cmovl  ecx,eax
    1fc9:	e9 e8 f6 ff ff       	jmp    16b6 <error_at_line@@Base+0x74d>
    1fce:	49 8b 56 28          	mov    rdx,QWORD PTR [r14+0x28]
    1fd2:	49 2b 56 20          	sub    rdx,QWORD PTR [r14+0x20]
    1fd6:	48 c1 fa 03          	sar    rdx,0x3
    1fda:	e9 12 fa ff ff       	jmp    19f1 <error_at_line@@Base+0xa88>
    1fdf:	66 0f ef ff          	pxor   xmm7,xmm7
    1fe3:	f2 48 0f 2a bd 60 ff 	cvtsi2sd xmm7,QWORD PTR [rbp-0xa0]
    1fea:	ff ff 
    1fec:	f2 0f 11 bd f0 fd ff 	movsd  QWORD PTR [rbp-0x210],xmm7
    1ff3:	ff 
    1ff4:	e8 67 33 00 00       	call   5360 <error_at_line@@Base+0x43f7>
    1ff9:	f2 0f 59 05 57 a8 00 	mulsd  xmm0,QWORD PTR [rip+0xa857]        # c858 <error_at_line@@Base+0xb8ef>
    2000:	00 
    2001:	f2 0f 10 0d 47 a8 00 	movsd  xmm1,QWORD PTR [rip+0xa847]        # c850 <error_at_line@@Base+0xb8e7>
    2008:	00 
    2009:	66 0f 2f c1          	comisd xmm0,xmm1
    200d:	0f 86 26 05 00 00    	jbe    2539 <error_at_line@@Base+0x15d0>
    2013:	66 0f 2f 8d f0 fd ff 	comisd xmm1,QWORD PTR [rbp-0x210]
    201a:	ff 
    201b:	0f 82 39 f6 ff ff    	jb     165a <error_at_line@@Base+0x6f1>
    2021:	31 c9                	xor    ecx,ecx
    2023:	66 0f ef c9          	pxor   xmm1,xmm1
    2027:	48 8d bd 18 fe ff ff 	lea    rdi,[rbp-0x1e8]
    202e:	f3 0f 7e 05 8a cf 00 	movq   xmm0,QWORD PTR [rip+0xcf8a]        # efc0 <error_at_line@@Base+0xe057>
    2035:	00 
    2036:	48 89 8d 00 fe ff ff 	mov    QWORD PTR [rbp-0x200],rcx
    203d:	0f 16 05 34 cf 00 00 	movhps xmm0,QWORD PTR [rip+0xcf34]        # ef78 <error_at_line@@Base+0xe00f>
    2044:	48 89 8d 30 fe ff ff 	mov    QWORD PTR [rbp-0x1d0],rcx
    204b:	48 89 8d 38 fe ff ff 	mov    QWORD PTR [rbp-0x1c8],rcx
    2052:	48 89 8d 80 fe ff ff 	mov    QWORD PTR [rbp-0x180],rcx
    2059:	48 89 8d 88 fe ff ff 	mov    QWORD PTR [rbp-0x178],rcx
    2060:	48 89 8d d8 fe ff ff 	mov    QWORD PTR [rbp-0x128],rcx
    2067:	48 89 8d e0 fe ff ff 	mov    QWORD PTR [rbp-0x120],rcx
    206e:	0f 11 8d 08 fe ff ff 	movups XMMWORD PTR [rbp-0x1f8],xmm1
    2075:	0f 29 85 50 fe ff ff 	movaps XMMWORD PTR [rbp-0x1b0],xmm0
    207c:	0f 29 85 f0 fd ff ff 	movaps XMMWORD PTR [rbp-0x210],xmm0
    2083:	80 a5 68 fe ff ff fe 	and    BYTE PTR [rbp-0x198],0xfe
    208a:	e8 31 1e 00 00       	call   3ec0 <error_at_line@@Base+0x2f57>
    208f:	66 0f 6f 85 f0 fd ff 	movdqa xmm0,XMMWORD PTR [rbp-0x210]
    2096:	ff 
    2097:	48 8d bd 70 fe ff ff 	lea    rdi,[rbp-0x190]
    209e:	80 a5 c0 fe ff ff fe 	and    BYTE PTR [rbp-0x140],0xfe
    20a5:	0f 11 85 a8 fe ff ff 	movups XMMWORD PTR [rbp-0x158],xmm0
    20ac:	e8 0f 1e 00 00       	call   3ec0 <error_at_line@@Base+0x2f57>
    20b1:	66 0f 6f 85 f0 fd ff 	movdqa xmm0,XMMWORD PTR [rbp-0x210]
    20b8:	ff 
    20b9:	48 8d bd c8 fe ff ff 	lea    rdi,[rbp-0x138]
    20c0:	80 a5 18 ff ff ff fe 	and    BYTE PTR [rbp-0xe8],0xfe
    20c7:	0f 29 85 00 ff ff ff 	movaps XMMWORD PTR [rbp-0x100],xmm0
    20ce:	e8 ed 1d 00 00       	call   3ec0 <error_at_line@@Base+0x2f57>
    20d3:	48 8b 85 00 fe ff ff 	mov    rax,QWORD PTR [rbp-0x200]
    20da:	66 0f 6f bd 80 fe ff 	movdqa xmm7,XMMWORD PTR [rbp-0x180]
    20e1:	ff 
    20e2:	f3 0f 6f b5 d8 fe ff 	movdqu xmm6,XMMWORD PTR [rbp-0x128]
    20e9:	ff 
    20ea:	48 8b 9d 30 fe ff ff 	mov    rbx,QWORD PTR [rbp-0x1d0]
    20f1:	48 89 85 b0 fd ff ff 	mov    QWORD PTR [rbp-0x250],rax
    20f8:	4c 8b ad 38 fe ff ff 	mov    r13,QWORD PTR [rbp-0x1c8]
    20ff:	0f 29 bd f0 fd ff ff 	movaps XMMWORD PTR [rbp-0x210],xmm7
    2106:	0f 29 b5 e0 fd ff ff 	movaps XMMWORD PTR [rbp-0x220],xmm6
    210d:	eb 0e                	jmp    211d <error_at_line@@Base+0x11b4>
    210f:	88 02                	mov    BYTE PTR [rdx],al
    2111:	48 8d 5a 01          	lea    rbx,[rdx+0x1]
    2115:	85 c0                	test   eax,eax
    2117:	0f 84 d1 03 00 00    	je     24ee <error_at_line@@Base+0x1585>
    211d:	4c 89 e7             	mov    rdi,r12
    2120:	e8 4b e8 ff ff       	call   970 <fgetc@plt>
    2125:	83 f8 ff             	cmp    eax,0xffffffff
    2128:	0f 84 18 02 00 00    	je     2346 <error_at_line@@Base+0x13dd>
    212e:	48 89 da             	mov    rdx,rbx
    2131:	4c 39 eb             	cmp    rbx,r13
    2134:	75 d9                	jne    210f <error_at_line@@Base+0x11a6>
    2136:	66 0f 6f bd f0 fd ff 	movdqa xmm7,XMMWORD PTR [rbp-0x210]
    213d:	ff 
    213e:	89 85 d8 fd ff ff    	mov    DWORD PTR [rbp-0x228],eax
    2144:	be 01 00 00 00       	mov    esi,0x1
    2149:	48 8d bd 18 fe ff ff 	lea    rdi,[rbp-0x1e8]
    2150:	48 8b 85 b0 fd ff ff 	mov    rax,QWORD PTR [rbp-0x250]
    2157:	66 0f 6f b5 e0 fd ff 	movdqa xmm6,XMMWORD PTR [rbp-0x220]
    215e:	ff 
    215f:	4c 89 ad 30 fe ff ff 	mov    QWORD PTR [rbp-0x1d0],r13
    2166:	4c 89 ad 38 fe ff ff 	mov    QWORD PTR [rbp-0x1c8],r13
    216d:	48 89 85 00 fe ff ff 	mov    QWORD PTR [rbp-0x200],rax
    2174:	0f 29 bd 80 fe ff ff 	movaps XMMWORD PTR [rbp-0x180],xmm7
    217b:	0f 11 b5 d8 fe ff ff 	movups XMMWORD PTR [rbp-0x128],xmm6
    2182:	e8 e9 4f 00 00       	call   7170 <error_at_line@@Base+0x6207>
    2187:	48 8b 85 00 fe ff ff 	mov    rax,QWORD PTR [rbp-0x200]
    218e:	66 0f 6f bd 80 fe ff 	movdqa xmm7,XMMWORD PTR [rbp-0x180]
    2195:	ff 
    2196:	f3 0f 6f b5 d8 fe ff 	movdqu xmm6,XMMWORD PTR [rbp-0x128]
    219d:	ff 
    219e:	48 8b 95 30 fe ff ff 	mov    rdx,QWORD PTR [rbp-0x1d0]
    21a5:	48 89 85 b0 fd ff ff 	mov    QWORD PTR [rbp-0x250],rax
    21ac:	4c 8b ad 38 fe ff ff 	mov    r13,QWORD PTR [rbp-0x1c8]
    21b3:	8b 85 d8 fd ff ff    	mov    eax,DWORD PTR [rbp-0x228]
    21b9:	0f 29 bd f0 fd ff ff 	movaps XMMWORD PTR [rbp-0x210],xmm7
    21c0:	0f 29 b5 e0 fd ff ff 	movaps XMMWORD PTR [rbp-0x220],xmm6
    21c7:	e9 43 ff ff ff       	jmp    210f <error_at_line@@Base+0x11a6>
    21cc:	4c 8d 25 dc 94 00 00 	lea    r12,[rip+0x94dc]        # b6af <error_at_line@@Base+0xa746>
    21d3:	ba 05 00 00 00       	mov    edx,0x5
    21d8:	48 8d 35 33 98 00 00 	lea    rsi,[rip+0x9833]        # ba12 <error_at_line@@Base+0xaaa9>
    21df:	4c 89 e7             	mov    rdi,r12
    21e2:	e8 d9 e6 ff ff       	call   8c0 <dcgettext@plt>
    21e7:	49 89 c6             	mov    r14,rax
    21ea:	48 8d 15 4f ce 00 00 	lea    rdx,[rip+0xce4f]        # f040 <error_at_line@@Base+0xe0d7>
    21f1:	48 8d 35 16 97 00 00 	lea    rsi,[rip+0x9716]        # b90e <error_at_line@@Base+0xa9a5>
    21f8:	bf 01 00 00 00       	mov    edi,0x1
    21fd:	e8 8e 57 00 00       	call   7990 <error_at_line@@Base+0x6a27>
    2202:	66 0f ef c0          	pxor   xmm0,xmm0
    2206:	48 89 de             	mov    rsi,rbx
    2209:	31 ff                	xor    edi,edi
    220b:	0f 11 85 38 ff ff ff 	movups XMMWORD PTR [rbp-0xc8],xmm0
    2212:	48 8d 95 30 ff ff ff 	lea    rdx,[rbp-0xd0]
    2219:	49 89 c7             	mov    r15,rax
    221c:	0f 11 85 48 ff ff ff 	movups XMMWORD PTR [rbp-0xb8],xmm0
    2223:	66 0f ef c0          	pxor   xmm0,xmm0
    2227:	0f 11 85 58 ff ff ff 	movups XMMWORD PTR [rbp-0xa8],xmm0
    222e:	48 c7 85 30 ff ff ff 	mov    QWORD PTR [rbp-0xd0],0x8
    2235:	08 00 00 00 
    2239:	e8 52 57 00 00       	call   7990 <error_at_line@@Base+0x6a27>
    223e:	4d 89 f8             	mov    r8,r15
    2241:	4c 89 f2             	mov    rdx,r14
    2244:	31 f6                	xor    esi,esi
    2246:	48 89 c1             	mov    rcx,rax
    2249:	31 ff                	xor    edi,edi
    224b:	31 c0                	xor    eax,eax
    224d:	e8 1b eb ff ff       	call   d6d <error@@Base>
    2252:	48 8b 05 87 cd 00 00 	mov    rax,QWORD PTR [rip+0xcd87]        # efe0 <error_at_line@@Base+0xe077>
    2259:	4c 89 e7             	mov    rdi,r12
    225c:	ba 05 00 00 00       	mov    edx,0x5
    2261:	48 8d 35 ae 96 00 00 	lea    rsi,[rip+0x96ae]        # b916 <error_at_line@@Base+0xa9ad>
    2268:	4c 8d 25 51 a5 00 00 	lea    r12,[rip+0xa551]        # c7c0 <error_at_line@@Base+0xb857>
    226f:	48 8b 18             	mov    rbx,QWORD PTR [rax]
    2272:	e8 49 e6 ff ff       	call   8c0 <dcgettext@plt>
    2277:	48 89 c7             	mov    rdi,rax
    227a:	48 89 de             	mov    rsi,rbx
    227d:	31 db                	xor    ebx,ebx
    227f:	e8 6c e7 ff ff       	call   9f0 <fputs_unlocked@plt>
    2284:	eb 30                	jmp    22b6 <error_at_line@@Base+0x134d>
    2286:	e8 05 57 00 00       	call   7990 <error_at_line@@Base+0x6a27>
    228b:	48 8d 15 99 96 00 00 	lea    rdx,[rip+0x9699]        # b92b <error_at_line@@Base+0xa9c2>
    2292:	be 02 00 00 00       	mov    esi,0x2
    2297:	48 89 c1             	mov    rcx,rax
    229a:	48 8b 05 3f cd 00 00 	mov    rax,QWORD PTR [rip+0xcd3f]        # efe0 <error_at_line@@Base+0xe077>
    22a1:	48 8b 38             	mov    rdi,QWORD PTR [rax]
    22a4:	31 c0                	xor    eax,eax
    22a6:	e8 d5 e8 ff ff       	call   b80 <__fprintf_chk@plt>
    22ab:	48 83 c3 01          	add    rbx,0x1
    22af:	49 83 c4 04          	add    r12,0x4
    22b3:	4d 89 f5             	mov    r13,r14
    22b6:	48 8d 05 03 c8 00 00 	lea    rax,[rip+0xc803]        # eac0 <error_at_line@@Base+0xdb57>
    22bd:	48 8b 34 d8          	mov    rsi,QWORD PTR [rax+rbx*8]
    22c1:	48 85 f6             	test   rsi,rsi
    22c4:	74 45                	je     230b <error_at_line@@Base+0x13a2>
    22c6:	4d 89 e6             	mov    r14,r12
    22c9:	48 8d 15 70 cd 00 00 	lea    rdx,[rip+0xcd70]        # f040 <error_at_line@@Base+0xe0d7>
    22d0:	31 ff                	xor    edi,edi
    22d2:	48 85 db             	test   rbx,rbx
    22d5:	74 af                	je     2286 <error_at_line@@Base+0x131d>
    22d7:	41 8b 45 00          	mov    eax,DWORD PTR [r13+0x0]
    22db:	41 39 04 24          	cmp    DWORD PTR [r12],eax
    22df:	75 a5                	jne    2286 <error_at_line@@Base+0x131d>
    22e1:	e8 aa 56 00 00       	call   7990 <error_at_line@@Base+0x6a27>
    22e6:	48 8d 15 46 96 00 00 	lea    rdx,[rip+0x9646]        # b933 <error_at_line@@Base+0xa9ca>
    22ed:	be 02 00 00 00       	mov    esi,0x2
    22f2:	4d 89 ee             	mov    r14,r13
    22f5:	48 89 c1             	mov    rcx,rax
    22f8:	48 8b 05 e1 cc 00 00 	mov    rax,QWORD PTR [rip+0xcce1]        # efe0 <error_at_line@@Base+0xe077>
    22ff:	48 8b 38             	mov    rdi,QWORD PTR [rax]
    2302:	31 c0                	xor    eax,eax
    2304:	e8 77 e8 ff ff       	call   b80 <__fprintf_chk@plt>
    2309:	eb a0                	jmp    22ab <error_at_line@@Base+0x1342>
    230b:	48 8b 05 ce cc 00 00 	mov    rax,QWORD PTR [rip+0xccce]        # efe0 <error_at_line@@Base+0xe077>
    2312:	48 8b 38             	mov    rdi,QWORD PTR [rax]
    2315:	48 8b 47 28          	mov    rax,QWORD PTR [rdi+0x28]
    2319:	48 3b 47 30          	cmp    rax,QWORD PTR [rdi+0x30]
    231d:	0f 83 c8 03 00 00    	jae    26eb <error_at_line@@Base+0x1782>
    2323:	48 8d 50 01          	lea    rdx,[rax+0x1]
    2327:	48 89 57 28          	mov    QWORD PTR [rdi+0x28],rdx
    232b:	c6 00 0a             	mov    BYTE PTR [rax],0xa
    232e:	48 8b 45 c8          	mov    rax,QWORD PTR [rbp-0x38]
    2332:	64 48 2b 04 25 28 00 	sub    rax,QWORD PTR fs:0x28
    2339:	00 00 
    233b:	0f 85 2a 04 00 00    	jne    276b <error_at_line@@Base+0x1802>
    2341:	e8 ca 25 00 00       	call   4910 <error_at_line@@Base+0x39a7>
    2346:	48 8b 85 28 fe ff ff 	mov    rax,QWORD PTR [rbp-0x1d8]
    234d:	4c 89 ad a8 fd ff ff 	mov    QWORD PTR [rbp-0x258],r13
    2354:	48 89 85 a0 fd ff ff 	mov    QWORD PTR [rbp-0x260],rax
    235b:	48 39 c3             	cmp    rbx,rax
    235e:	0f 84 a5 00 00 00    	je     2409 <error_at_line@@Base+0x14a0>
    2364:	4c 39 eb             	cmp    rbx,r13
    2367:	0f 84 ed 02 00 00    	je     265a <error_at_line@@Base+0x16f1>
    236d:	48 8b 85 b0 fd ff ff 	mov    rax,QWORD PTR [rbp-0x250]
    2374:	c6 03 00             	mov    BYTE PTR [rbx],0x0
    2377:	48 83 c3 01          	add    rbx,0x1
    237b:	48 8d bd 00 fe ff ff 	lea    rdi,[rbp-0x200]
    2382:	66 0f 6f bd f0 fd ff 	movdqa xmm7,XMMWORD PTR [rbp-0x210]
    2389:	ff 
    238a:	66 0f 6f b5 e0 fd ff 	movdqa xmm6,XMMWORD PTR [rbp-0x220]
    2391:	ff 
    2392:	48 89 9d 30 fe ff ff 	mov    QWORD PTR [rbp-0x1d0],rbx
    2399:	48 89 85 00 fe ff ff 	mov    QWORD PTR [rbp-0x200],rax
    23a0:	48 8b 85 a8 fd ff ff 	mov    rax,QWORD PTR [rbp-0x258]
    23a7:	0f 29 bd 80 fe ff ff 	movaps XMMWORD PTR [rbp-0x180],xmm7
    23ae:	48 89 85 38 fe ff ff 	mov    QWORD PTR [rbp-0x1c8],rax
    23b5:	0f 11 b5 d8 fe ff ff 	movups XMMWORD PTR [rbp-0x128],xmm6
    23bc:	e8 3f 4f 00 00       	call   7300 <error_at_line@@Base+0x6397>
    23c1:	48 8b 85 00 fe ff ff 	mov    rax,QWORD PTR [rbp-0x200]
    23c8:	66 0f 6f bd 80 fe ff 	movdqa xmm7,XMMWORD PTR [rbp-0x180]
    23cf:	ff 
    23d0:	f3 0f 6f b5 d8 fe ff 	movdqu xmm6,XMMWORD PTR [rbp-0x128]
    23d7:	ff 
    23d8:	48 89 85 b0 fd ff ff 	mov    QWORD PTR [rbp-0x250],rax
    23df:	48 8b 85 30 fe ff ff 	mov    rax,QWORD PTR [rbp-0x1d0]
    23e6:	0f 29 bd f0 fd ff ff 	movaps XMMWORD PTR [rbp-0x210],xmm7
    23ed:	48 89 85 a0 fd ff ff 	mov    QWORD PTR [rbp-0x260],rax
    23f4:	48 8b 85 38 fe ff ff 	mov    rax,QWORD PTR [rbp-0x1c8]
    23fb:	0f 29 b5 e0 fd ff ff 	movaps XMMWORD PTR [rbp-0x220],xmm6
    2402:	48 89 85 a8 fd ff ff 	mov    QWORD PTR [rbp-0x258],rax
    2409:	66 0f 6f b5 f0 fd ff 	movdqa xmm6,XMMWORD PTR [rbp-0x210]
    2410:	ff 
    2411:	48 8b 85 90 fe ff ff 	mov    rax,QWORD PTR [rbp-0x170]
    2418:	0f 12 fe             	movhlps xmm7,xmm6
    241b:	66 49 0f 7e fd       	movq   r13,xmm7
    2420:	4c 29 e8             	sub    rax,r13
    2423:	48 83 f8 07          	cmp    rax,0x7
    2427:	0f 86 82 01 00 00    	jbe    25af <error_at_line@@Base+0x1646>
    242d:	4c 8b b5 e8 fd ff ff 	mov    r14,QWORD PTR [rbp-0x218]
    2434:	48 8b 85 e0 fd ff ff 	mov    rax,QWORD PTR [rbp-0x220]
    243b:	66 0f d6 b5 f0 fd ff 	movq   QWORD PTR [rbp-0x210],xmm6
    2442:	ff 
    2443:	31 d2                	xor    edx,edx
    2445:	49 83 c5 08          	add    r13,0x8
    2449:	49 89 55 f8          	mov    QWORD PTR [r13-0x8],rdx
    244d:	4c 3b ad f0 fd ff ff 	cmp    r13,QWORD PTR [rbp-0x210]
    2454:	0f 84 49 01 00 00    	je     25a3 <error_at_line@@Base+0x163a>
    245a:	48 8b b5 f0 fd ff ff 	mov    rsi,QWORD PTR [rbp-0x210]
    2461:	4c 8b bd a0 fe ff ff 	mov    r15,QWORD PTR [rbp-0x160]
    2468:	48 89 b5 08 fe ff ff 	mov    QWORD PTR [rbp-0x1f8],rsi
    246f:	4c 39 f0             	cmp    rax,r14
    2472:	0f 84 1f 01 00 00    	je     2597 <error_at_line@@Base+0x162e>
    2478:	4c 89 e7             	mov    rdi,r12
    247b:	48 89 85 10 fe ff ff 	mov    QWORD PTR [rbp-0x1f0],rax
    2482:	48 8b 9d f8 fe ff ff 	mov    rbx,QWORD PTR [rbp-0x108]
    2489:	e8 c2 e3 ff ff       	call   850 <ferror@plt>
    248e:	85 c0                	test   eax,eax
    2490:	0f 85 64 02 00 00    	jne    26fa <error_at_line@@Base+0x1791>
    2496:	4c 89 e7             	mov    rdi,r12
    2499:	e8 02 e4 ff ff       	call   8a0 <fclose@plt>
    249e:	85 c0                	test   eax,eax
    24a0:	0f 85 54 02 00 00    	jne    26fa <error_at_line@@Base+0x1791>
    24a6:	4c 89 e8             	mov    rax,r13
    24a9:	48 8b bd f0 fd ff ff 	mov    rdi,QWORD PTR [rbp-0x210]
    24b0:	48 f7 d8             	neg    rax
    24b3:	4c 21 f8             	and    rax,r15
    24b6:	4c 8b bd b0 fd ff ff 	mov    r15,QWORD PTR [rbp-0x250]
    24bd:	4c 01 e8             	add    rax,r13
    24c0:	48 89 85 98 fd ff ff 	mov    QWORD PTR [rbp-0x268],rax
    24c7:	4c 89 f0             	mov    rax,r14
    24ca:	48 f7 d8             	neg    rax
    24cd:	48 21 d8             	and    rax,rbx
    24d0:	4c 01 f0             	add    rax,r14
    24d3:	48 89 85 90 fd ff ff 	mov    QWORD PTR [rbp-0x270],rax
    24da:	e8 21 19 00 00       	call   3e00 <error_at_line@@Base+0x2e97>
    24df:	c6 85 bf fd ff ff 01 	mov    BYTE PTR [rbp-0x241],0x1
    24e6:	49 89 c6             	mov    r14,rax
    24e9:	e9 8a f1 ff ff       	jmp    1678 <error_at_line@@Base+0x70f>
    24ee:	48 8b 85 b0 fd ff ff 	mov    rax,QWORD PTR [rbp-0x250]
    24f5:	66 0f 6f bd f0 fd ff 	movdqa xmm7,XMMWORD PTR [rbp-0x210]
    24fc:	ff 
    24fd:	48 8d bd 00 fe ff ff 	lea    rdi,[rbp-0x200]
    2504:	48 89 9d 30 fe ff ff 	mov    QWORD PTR [rbp-0x1d0],rbx
    250b:	66 0f 6f b5 e0 fd ff 	movdqa xmm6,XMMWORD PTR [rbp-0x220]
    2512:	ff 
    2513:	4c 89 ad 38 fe ff ff 	mov    QWORD PTR [rbp-0x1c8],r13
    251a:	48 89 85 00 fe ff ff 	mov    QWORD PTR [rbp-0x200],rax
    2521:	0f 29 bd 80 fe ff ff 	movaps XMMWORD PTR [rbp-0x180],xmm7
    2528:	0f 11 b5 d8 fe ff ff 	movups XMMWORD PTR [rbp-0x128],xmm6
    252f:	e8 cc 4d 00 00       	call   7300 <error_at_line@@Base+0x6397>
    2534:	e9 9a fb ff ff       	jmp    20d3 <error_at_line@@Base+0x116a>
    2539:	e8 22 2e 00 00       	call   5360 <error_at_line@@Base+0x43f7>
    253e:	f2 0f 10 0d 12 a3 00 	movsd  xmm1,QWORD PTR [rip+0xa312]        # c858 <error_at_line@@Base+0xb8ef>
    2545:	00 
    2546:	f2 0f 59 c8          	mulsd  xmm1,xmm0
    254a:	e9 c4 fa ff ff       	jmp    2013 <error_at_line@@Base+0x10aa>
    254f:	3d 7e ff ff ff       	cmp    eax,0xffffff7e
    2554:	0f 85 cc f7 ff ff    	jne    1d26 <error_at_line@@Base+0xdbd>
    255a:	48 8b 45 c8          	mov    rax,QWORD PTR [rbp-0x38]
    255e:	64 48 2b 04 25 28 00 	sub    rax,QWORD PTR fs:0x28
    2565:	00 00 
    2567:	0f 85 fe 01 00 00    	jne    276b <error_at_line@@Base+0x1802>
    256d:	31 ff                	xor    edi,edi
    256f:	e8 cc 1d 00 00       	call   4340 <error_at_line@@Base+0x33d7>
    2574:	4c 8d 25 34 91 00 00 	lea    r12,[rip+0x9134]        # b6af <error_at_line@@Base+0xa746>
    257b:	ba 05 00 00 00       	mov    edx,0x5
    2580:	48 8d 35 70 94 00 00 	lea    rsi,[rip+0x9470]        # b9f7 <error_at_line@@Base+0xaa8e>
    2587:	4c 89 e7             	mov    rdi,r12
    258a:	e8 31 e3 ff ff       	call   8c0 <dcgettext@plt>
    258f:	49 89 c6             	mov    r14,rax
    2592:	e9 53 fc ff ff       	jmp    21ea <error_at_line@@Base+0x1281>
    2597:	80 8d 18 ff ff ff 02 	or     BYTE PTR [rbp-0xe8],0x2
    259e:	e9 d5 fe ff ff       	jmp    2478 <error_at_line@@Base+0x150f>
    25a3:	80 8d c0 fe ff ff 02 	or     BYTE PTR [rbp-0x140],0x2
    25aa:	e9 ab fe ff ff       	jmp    245a <error_at_line@@Base+0x14f1>
    25af:	48 8b 85 b0 fd ff ff 	mov    rax,QWORD PTR [rbp-0x250]
    25b6:	66 0f 6f bd f0 fd ff 	movdqa xmm7,XMMWORD PTR [rbp-0x210]
    25bd:	ff 
    25be:	be 08 00 00 00       	mov    esi,0x8
    25c3:	48 8d bd 70 fe ff ff 	lea    rdi,[rbp-0x190]
    25ca:	66 0f 6f b5 e0 fd ff 	movdqa xmm6,XMMWORD PTR [rbp-0x220]
    25d1:	ff 
    25d2:	48 89 85 00 fe ff ff 	mov    QWORD PTR [rbp-0x200],rax
    25d9:	48 8b 85 a0 fd ff ff 	mov    rax,QWORD PTR [rbp-0x260]
    25e0:	0f 29 bd 80 fe ff ff 	movaps XMMWORD PTR [rbp-0x180],xmm7
    25e7:	48 89 85 30 fe ff ff 	mov    QWORD PTR [rbp-0x1d0],rax
    25ee:	48 8b 85 a8 fd ff ff 	mov    rax,QWORD PTR [rbp-0x258]
    25f5:	0f 11 b5 d8 fe ff ff 	movups XMMWORD PTR [rbp-0x128],xmm6
    25fc:	48 89 85 38 fe ff ff 	mov    QWORD PTR [rbp-0x1c8],rax
    2603:	e8 68 4b 00 00       	call   7170 <error_at_line@@Base+0x6207>
    2608:	48 8b 85 00 fe ff ff 	mov    rax,QWORD PTR [rbp-0x200]
    260f:	4c 8b ad 88 fe ff ff 	mov    r13,QWORD PTR [rbp-0x178]
    2616:	4c 8b b5 e0 fe ff ff 	mov    r14,QWORD PTR [rbp-0x120]
    261d:	48 89 85 b0 fd ff ff 	mov    QWORD PTR [rbp-0x250],rax
    2624:	48 8b 85 30 fe ff ff 	mov    rax,QWORD PTR [rbp-0x1d0]
    262b:	48 89 85 a0 fd ff ff 	mov    QWORD PTR [rbp-0x260],rax
    2632:	48 8b 85 38 fe ff ff 	mov    rax,QWORD PTR [rbp-0x1c8]
    2639:	48 89 85 a8 fd ff ff 	mov    QWORD PTR [rbp-0x258],rax
    2640:	48 8b 85 80 fe ff ff 	mov    rax,QWORD PTR [rbp-0x180]
    2647:	48 89 85 f0 fd ff ff 	mov    QWORD PTR [rbp-0x210],rax
    264e:	48 8b 85 d8 fe ff ff 	mov    rax,QWORD PTR [rbp-0x128]
    2655:	e9 e9 fd ff ff       	jmp    2443 <error_at_line@@Base+0x14da>
    265a:	48 8b 85 b0 fd ff ff 	mov    rax,QWORD PTR [rbp-0x250]
    2661:	66 0f 6f bd f0 fd ff 	movdqa xmm7,XMMWORD PTR [rbp-0x210]
    2668:	ff 
    2669:	be 01 00 00 00       	mov    esi,0x1
    266e:	48 8d bd 18 fe ff ff 	lea    rdi,[rbp-0x1e8]
    2675:	66 0f 6f b5 e0 fd ff 	movdqa xmm6,XMMWORD PTR [rbp-0x220]
    267c:	ff 
    267d:	48 89 9d 30 fe ff ff 	mov    QWORD PTR [rbp-0x1d0],rbx
    2684:	48 89 85 00 fe ff ff 	mov    QWORD PTR [rbp-0x200],rax
    268b:	48 89 9d 38 fe ff ff 	mov    QWORD PTR [rbp-0x1c8],rbx
    2692:	0f 29 bd 80 fe ff ff 	movaps XMMWORD PTR [rbp-0x180],xmm7
    2699:	0f 11 b5 d8 fe ff ff 	movups XMMWORD PTR [rbp-0x128],xmm6
    26a0:	e8 cb 4a 00 00       	call   7170 <error_at_line@@Base+0x6207>
    26a5:	48 8b 85 00 fe ff ff 	mov    rax,QWORD PTR [rbp-0x200]
    26ac:	66 0f 6f bd 80 fe ff 	movdqa xmm7,XMMWORD PTR [rbp-0x180]
    26b3:	ff 
    26b4:	f3 0f 6f b5 d8 fe ff 	movdqu xmm6,XMMWORD PTR [rbp-0x128]
    26bb:	ff 
    26bc:	48 8b 9d 30 fe ff ff 	mov    rbx,QWORD PTR [rbp-0x1d0]
    26c3:	48 89 85 b0 fd ff ff 	mov    QWORD PTR [rbp-0x250],rax
    26ca:	48 8b 85 38 fe ff ff 	mov    rax,QWORD PTR [rbp-0x1c8]
    26d1:	0f 29 bd f0 fd ff ff 	movaps XMMWORD PTR [rbp-0x210],xmm7
    26d8:	48 89 85 a8 fd ff ff 	mov    QWORD PTR [rbp-0x258],rax
    26df:	0f 29 b5 e0 fd ff ff 	movaps XMMWORD PTR [rbp-0x220],xmm6
    26e6:	e9 82 fc ff ff       	jmp    236d <error_at_line@@Base+0x1404>
    26eb:	be 0a 00 00 00       	mov    esi,0xa
    26f0:	e8 3b e2 ff ff       	call   930 <__overflow@plt>
    26f5:	e9 34 fc ff ff       	jmp    232e <error_at_line@@Base+0x13c5>
    26fa:	48 8b bd d0 fd ff ff 	mov    rdi,QWORD PTR [rbp-0x230]
    2701:	e8 0a 55 00 00       	call   7c10 <error_at_line@@Base+0x6ca7>
    2706:	ba 05 00 00 00       	mov    edx,0x5
    270b:	31 ff                	xor    edi,edi
    270d:	48 8d 35 ec 9b 00 00 	lea    rsi,[rip+0x9bec]        # c300 <error_at_line@@Base+0xb397>
    2714:	48 89 c3             	mov    rbx,rax
    2717:	e8 a4 e1 ff ff       	call   8c0 <dcgettext@plt>
    271c:	48 8b 55 c8          	mov    rdx,QWORD PTR [rbp-0x38]
    2720:	64 48 2b 14 25 28 00 	sub    rdx,QWORD PTR fs:0x28
    2727:	00 00 
    2729:	75 40                	jne    276b <error_at_line@@Base+0x1802>
    272b:	48 89 c2             	mov    rdx,rax
    272e:	48 89 d9             	mov    rcx,rbx
    2731:	31 f6                	xor    esi,esi
    2733:	bf 01 00 00 00       	mov    edi,0x1
    2738:	31 c0                	xor    eax,eax
    273a:	e8 2e e6 ff ff       	call   d6d <error@@Base>
    273f:	4c 89 f7             	mov    rdi,r14
    2742:	e8 29 55 00 00       	call   7c70 <error_at_line@@Base+0x6d07>
    2747:	49 89 c6             	mov    r14,rax
    274a:	e8 b1 e0 ff ff       	call   800 <__errno_location@plt>
    274f:	48 8d 15 df 91 00 00 	lea    rdx,[rip+0x91df]        # b935 <error_at_line@@Base+0xa9cc>
    2756:	4c 89 f1             	mov    rcx,r14
    2759:	31 ff                	xor    edi,edi
    275b:	8b 30                	mov    esi,DWORD PTR [rax]
    275d:	31 c0                	xor    eax,eax
    275f:	e8 09 e6 ff ff       	call   d6d <error@@Base>
    2764:	31 d2                	xor    edx,edx
    2766:	e9 53 f0 ff ff       	jmp    17be <error_at_line@@Base+0x855>
    276b:	e8 80 e1 ff ff       	call   8f0 <__stack_chk_fail@plt>
    2770:	ba 05 00 00 00       	mov    edx,0x5
    2775:	31 ff                	xor    edi,edi
    2777:	45 31 e4             	xor    r12d,r12d
    277a:	48 c7 05 bb ca 00 00 	mov    QWORD PTR [rip+0xcabb],0xffffffffffffffff        # f240 <error_print_progname@@Base+0x158>
    2781:	ff ff ff ff 
    2785:	48 8d 35 5f 92 00 00 	lea    rsi,[rip+0x925f]        # b9eb <error_at_line@@Base+0xaa82>
    278c:	e8 2f e1 ff ff       	call   8c0 <dcgettext@plt>
    2791:	be 4b 00 00 00       	mov    esi,0x4b
    2796:	31 ff                	xor    edi,edi
    2798:	48 89 c2             	mov    rdx,rax
    279b:	31 c0                	xor    eax,eax
    279d:	e8 cb e5 ff ff       	call   d6d <error@@Base>
    27a2:	e9 be f2 ff ff       	jmp    1a65 <error_at_line@@Base+0xafc>
    27a7:	ba 05 00 00 00       	mov    edx,0x5
    27ac:	31 ff                	xor    edi,edi
    27ae:	45 31 e4             	xor    r12d,r12d
    27b1:	48 c7 05 b4 ca 00 00 	mov    QWORD PTR [rip+0xcab4],0xffffffffffffffff        # f270 <error_print_progname@@Base+0x188>
    27b8:	ff ff ff ff 
    27bc:	48 8d 35 ff 91 00 00 	lea    rsi,[rip+0x91ff]        # b9c2 <error_at_line@@Base+0xaa59>
    27c3:	e8 f8 e0 ff ff       	call   8c0 <dcgettext@plt>
    27c8:	be 4b 00 00 00       	mov    esi,0x4b
    27cd:	31 ff                	xor    edi,edi
    27cf:	48 89 c2             	mov    rdx,rax
    27d2:	31 c0                	xor    eax,eax
    27d4:	e8 94 e5 ff ff       	call   d6d <error@@Base>
    27d9:	e9 60 f2 ff ff       	jmp    1a3e <error_at_line@@Base+0xad5>
    27de:	ba 05 00 00 00       	mov    edx,0x5
    27e3:	31 ff                	xor    edi,edi
    27e5:	45 31 e4             	xor    r12d,r12d
    27e8:	48 c7 05 5d ca 00 00 	mov    QWORD PTR [rip+0xca5d],0xffffffffffffffff        # f250 <error_print_progname@@Base+0x168>
    27ef:	ff ff ff ff 
    27f3:	48 8d 35 e0 91 00 00 	lea    rsi,[rip+0x91e0]        # b9da <error_at_line@@Base+0xaa71>
    27fa:	e8 c1 e0 ff ff       	call   8c0 <dcgettext@plt>
    27ff:	be 4b 00 00 00       	mov    esi,0x4b
    2804:	31 ff                	xor    edi,edi
    2806:	48 89 c2             	mov    rdx,rax
    2809:	31 c0                	xor    eax,eax
    280b:	e8 5d e5 ff ff       	call   d6d <error@@Base>
    2810:	e9 43 f2 ff ff       	jmp    1a58 <error_at_line@@Base+0xaef>
    2815:	ba 05 00 00 00       	mov    edx,0x5
    281a:	31 ff                	xor    edi,edi
    281c:	45 31 e4             	xor    r12d,r12d
    281f:	48 c7 05 36 ca 00 00 	mov    QWORD PTR [rip+0xca36],0xffffffffffffffff        # f260 <error_print_progname@@Base+0x178>
    2826:	ff ff ff ff 
    282a:	48 8d 35 9d 91 00 00 	lea    rsi,[rip+0x919d]        # b9ce <error_at_line@@Base+0xaa65>
    2831:	e8 8a e0 ff ff       	call   8c0 <dcgettext@plt>
    2836:	be 4b 00 00 00       	mov    esi,0x4b
    283b:	31 ff                	xor    edi,edi
    283d:	48 89 c2             	mov    rdx,rax
    2840:	31 c0                	xor    eax,eax
    2842:	e8 26 e5 ff ff       	call   d6d <error@@Base>
    2847:	e9 ff f1 ff ff       	jmp    1a4b <error_at_line@@Base+0xae2>
    284c:	0f 1f 40 00          	nop    DWORD PTR [rax+0x0]
    2850:	f3 0f 1e fa          	endbr64
    2854:	8b 05 56 cc 00 00    	mov    eax,DWORD PTR [rip+0xcc56]        # f4b0 <error_print_progname@@Base+0x3c8>
    285a:	85 c0                	test   eax,eax
    285c:	0f 85 0e 07 00 00    	jne    2f70 <error_at_line@@Base+0x2007>
    2862:	48 83 ec 30          	sub    rsp,0x30
    2866:	31 c0                	xor    eax,eax
    2868:	48 89 1c 24          	mov    QWORD PTR [rsp],rbx
    286c:	0f a2                	cpuid
    286e:	85 c0                	test   eax,eax
    2870:	0f 84 e2 06 00 00    	je     2f58 <error_at_line@@Base+0x1fef>
    2876:	31 c0                	xor    eax,eax
    2878:	0f a2                	cpuid
    287a:	41 89 db             	mov    r11d,ebx
    287d:	89 c7                	mov    edi,eax
    287f:	85 c0                	test   eax,eax
    2881:	0f 8e d1 06 00 00    	jle    2f58 <error_at_line@@Base+0x1fef>
    2887:	31 c0                	xor    eax,eax
    2889:	0f a2                	cpuid
    288b:	85 c0                	test   eax,eax
    288d:	0f 84 c5 06 00 00    	je     2f58 <error_at_line@@Base+0x1fef>
    2893:	48 89 6c 24 08       	mov    QWORD PTR [rsp+0x8],rbp
    2898:	b8 01 00 00 00       	mov    eax,0x1
    289d:	4c 89 64 24 10       	mov    QWORD PTR [rsp+0x10],r12
    28a2:	4c 89 6c 24 18       	mov    QWORD PTR [rsp+0x18],r13
    28a7:	4c 89 74 24 20       	mov    QWORD PTR [rsp+0x20],r14
    28ac:	4c 89 7c 24 28       	mov    QWORD PTR [rsp+0x28],r15
    28b1:	0f a2                	cpuid
    28b3:	89 d5                	mov    ebp,edx
    28b5:	89 c2                	mov    edx,eax
    28b7:	41 89 c2             	mov    r10d,eax
    28ba:	41 89 c8             	mov    r8d,ecx
    28bd:	c1 ea 04             	shr    edx,0x4
    28c0:	41 c1 ea 08          	shr    r10d,0x8
    28c4:	83 e2 0f             	and    edx,0xf
    28c7:	41 83 e2 0f          	and    r10d,0xf
    28cb:	41 89 d5             	mov    r13d,edx
    28ce:	89 c2                	mov    edx,eax
    28d0:	c1 e8 14             	shr    eax,0x14
    28d3:	45 89 d6             	mov    r14d,r10d
    28d6:	0f b6 c0             	movzx  eax,al
    28d9:	c1 ea 0c             	shr    edx,0xc
    28dc:	89 44 24 fc          	mov    DWORD PTR [rsp-0x4],eax
    28e0:	89 c8                	mov    eax,ecx
    28e2:	81 e2 f0 00 00 00    	and    edx,0xf0
    28e8:	25 00 00 00 08       	and    eax,0x8000000
    28ed:	89 54 24 f8          	mov    DWORD PTR [rsp-0x8],edx
    28f1:	41 89 c7             	mov    r15d,eax
    28f4:	0f 85 79 06 00 00    	jne    2f73 <error_at_line@@Base+0x200a>
    28fa:	45 31 c9             	xor    r9d,r9d
    28fd:	45 31 e4             	xor    r12d,r12d
    2900:	45 31 d2             	xor    r10d,r10d
    2903:	31 f6                	xor    esi,esi
    2905:	f7 c5 00 80 00 00    	test   ebp,0x8000
    290b:	74 07                	je     2914 <error_at_line@@Base+0x19ab>
    290d:	83 0d a8 cb 00 00 01 	or     DWORD PTR [rip+0xcba8],0x1        # f4bc <error_print_progname@@Base+0x3d4>
    2914:	f7 c5 00 00 80 00    	test   ebp,0x800000
    291a:	74 07                	je     2923 <error_at_line@@Base+0x19ba>
    291c:	83 0d 99 cb 00 00 02 	or     DWORD PTR [rip+0xcb99],0x2        # f4bc <error_print_progname@@Base+0x3d4>
    2923:	f7 c5 00 00 00 02    	test   ebp,0x2000000
    2929:	74 07                	je     2932 <error_at_line@@Base+0x19c9>
    292b:	83 0d 8a cb 00 00 08 	or     DWORD PTR [rip+0xcb8a],0x8        # f4bc <error_print_progname@@Base+0x3d4>
    2932:	f7 c5 00 00 00 04    	test   ebp,0x4000000
    2938:	74 07                	je     2941 <error_at_line@@Base+0x19d8>
    293a:	83 0d 7b cb 00 00 10 	or     DWORD PTR [rip+0xcb7b],0x10        # f4bc <error_print_progname@@Base+0x3d4>
    2941:	f7 c5 00 01 00 00    	test   ebp,0x100
    2947:	0f 85 7b 06 00 00    	jne    2fc8 <error_at_line@@Base+0x205f>
    294d:	81 e5 00 00 00 01    	and    ebp,0x1000000
    2953:	0f 85 8d 06 00 00    	jne    2fe6 <error_at_line@@Base+0x207d>
    2959:	41 f7 c0 00 00 80 00 	test   r8d,0x800000
    2960:	74 07                	je     2969 <error_at_line@@Base+0x1a00>
    2962:	83 0d 53 cb 00 00 04 	or     DWORD PTR [rip+0xcb53],0x4        # f4bc <error_print_progname@@Base+0x3d4>
    2969:	44 89 c0             	mov    eax,r8d
    296c:	25 00 00 00 02       	and    eax,0x2000000
    2971:	74 0a                	je     297d <error_at_line@@Base+0x1a14>
    2973:	81 0d 3f cb 00 00 00 	or     DWORD PTR [rip+0xcb3f],0x40000        # f4bc <error_print_progname@@Base+0x3d4>
    297a:	00 04 00 
    297d:	41 f6 c0 02          	test   r8b,0x2
    2981:	74 0a                	je     298d <error_at_line@@Base+0x1a24>
    2983:	81 0d 2f cb 00 00 00 	or     DWORD PTR [rip+0xcb2f],0x80000        # f4bc <error_print_progname@@Base+0x3d4>
    298a:	00 08 00 
    298d:	41 f6 c0 01          	test   r8b,0x1
    2991:	74 07                	je     299a <error_at_line@@Base+0x1a31>
    2993:	83 0d 22 cb 00 00 20 	or     DWORD PTR [rip+0xcb22],0x20        # f4bc <error_print_progname@@Base+0x3d4>
    299a:	41 f7 c0 00 02 00 00 	test   r8d,0x200
    29a1:	74 07                	je     29aa <error_at_line@@Base+0x1a41>
    29a3:	83 0d 12 cb 00 00 40 	or     DWORD PTR [rip+0xcb12],0x40        # f4bc <error_print_progname@@Base+0x3d4>
    29aa:	41 f7 c0 00 00 08 00 	test   r8d,0x80000
    29b1:	74 0a                	je     29bd <error_at_line@@Base+0x1a54>
    29b3:	81 0d ff ca 00 00 80 	or     DWORD PTR [rip+0xcaff],0x80        # f4bc <error_print_progname@@Base+0x3d4>
    29ba:	00 00 00 
    29bd:	41 f7 c0 00 00 10 00 	test   r8d,0x100000
    29c4:	74 0a                	je     29d0 <error_at_line@@Base+0x1a67>
    29c6:	81 0d ec ca 00 00 00 	or     DWORD PTR [rip+0xcaec],0x100        # f4bc <error_print_progname@@Base+0x3d4>
    29cd:	01 00 00 
    29d0:	45 85 ff             	test   r15d,r15d
    29d3:	0f 85 fe 05 00 00    	jne    2fd7 <error_at_line@@Base+0x206e>
    29d9:	41 f7 c0 00 20 00 00 	test   r8d,0x2000
    29e0:	0f 85 39 06 00 00    	jne    301f <error_at_line@@Base+0x20b6>
    29e6:	41 f7 c0 00 00 40 00 	test   r8d,0x400000
    29ed:	0f 85 1d 06 00 00    	jne    3010 <error_at_line@@Base+0x20a7>
    29f3:	85 c0                	test   eax,eax
    29f5:	74 0a                	je     2a01 <error_at_line@@Base+0x1a98>
    29f7:	81 0d bb ca 00 00 00 	or     DWORD PTR [rip+0xcabb],0x40000        # f4bc <error_print_progname@@Base+0x3d4>
    29fe:	00 04 00 
    2a01:	41 f7 c0 00 00 00 40 	test   r8d,0x40000000
    2a08:	0f 85 f6 05 00 00    	jne    3004 <error_at_line@@Base+0x209b>
    2a0e:	41 f7 c0 00 00 00 04 	test   r8d,0x4000000
    2a15:	0f 85 da 05 00 00    	jne    2ff5 <error_at_line@@Base+0x208c>
    2a1b:	85 f6                	test   esi,esi
    2a1d:	74 33                	je     2a52 <error_at_line@@Base+0x1ae9>
    2a1f:	41 f7 c0 00 00 00 10 	test   r8d,0x10000000
    2a26:	74 0a                	je     2a32 <error_at_line@@Base+0x1ac9>
    2a28:	81 0d 8a ca 00 00 00 	or     DWORD PTR [rip+0xca8a],0x200        # f4bc <error_print_progname@@Base+0x3d4>
    2a2f:	02 00 00 
    2a32:	41 f7 c0 00 10 00 00 	test   r8d,0x1000
    2a39:	74 0a                	je     2a45 <error_at_line@@Base+0x1adc>
    2a3b:	81 0d 77 ca 00 00 00 	or     DWORD PTR [rip+0xca77],0x4000        # f4bc <error_print_progname@@Base+0x3d4>
    2a42:	40 00 00 
    2a45:	41 81 e0 00 00 00 20 	and    r8d,0x20000000
    2a4c:	0f 85 e7 0c 00 00    	jne    3739 <error_at_line@@Base+0x27d0>
    2a52:	83 ff 06             	cmp    edi,0x6
    2a55:	0f 86 a0 03 00 00    	jbe    2dfb <error_at_line@@Base+0x1e92>
    2a5b:	b8 07 00 00 00       	mov    eax,0x7
    2a60:	31 c9                	xor    ecx,ecx
    2a62:	0f a2                	cpuid
    2a64:	41 89 c8             	mov    r8d,ecx
    2a67:	89 dd                	mov    ebp,ebx
    2a69:	f6 c3 08             	test   bl,0x8
    2a6c:	74 0a                	je     2a78 <error_at_line@@Base+0x1b0f>
    2a6e:	81 0d 44 ca 00 00 00 	or     DWORD PTR [rip+0xca44],0x10000        # f4bc <error_print_progname@@Base+0x3d4>
    2a75:	00 01 00 
    2a78:	40 f6 c5 04          	test   bpl,0x4
    2a7c:	0f 85 a8 0c 00 00    	jne    372a <error_at_line@@Base+0x27c1>
    2a82:	40 f6 c5 10          	test   bpl,0x10
    2a86:	0f 85 8f 0c 00 00    	jne    371b <error_at_line@@Base+0x27b2>
    2a8c:	f7 c5 00 08 00 00    	test   ebp,0x800
    2a92:	0f 85 74 0c 00 00    	jne    370c <error_at_line@@Base+0x27a3>
    2a98:	85 f6                	test   esi,esi
    2a9a:	74 2a                	je     2ac6 <error_at_line@@Base+0x1b5d>
    2a9c:	40 f6 c5 20          	test   bpl,0x20
    2aa0:	74 0a                	je     2aac <error_at_line@@Base+0x1b43>
    2aa2:	81 0d 10 ca 00 00 00 	or     DWORD PTR [rip+0xca10],0x400        # f4bc <error_print_progname@@Base+0x3d4>
    2aa9:	04 00 00 
    2aac:	41 f7 c0 00 04 00 00 	test   r8d,0x400
    2ab3:	0f 85 f1 06 00 00    	jne    31aa <error_at_line@@Base+0x2241>
    2ab9:	41 f7 c0 00 02 00 00 	test   r8d,0x200
    2ac0:	0f 85 d5 06 00 00    	jne    319b <error_at_line@@Base+0x2232>
    2ac6:	f7 c5 00 01 00 00    	test   ebp,0x100
    2acc:	74 0a                	je     2ad8 <error_at_line@@Base+0x1b6f>
    2ace:	81 0d e4 c9 00 00 00 	or     DWORD PTR [rip+0xc9e4],0x20000        # f4bc <error_print_progname@@Base+0x3d4>
    2ad5:	00 02 00 
    2ad8:	40 f6 c5 01          	test   bpl,0x1
    2adc:	0f 85 c6 0c 00 00    	jne    37a8 <error_at_line@@Base+0x283f>
    2ae2:	f7 c5 00 00 04 00    	test   ebp,0x40000
    2ae8:	0f 85 ae 0c 00 00    	jne    379c <error_at_line@@Base+0x2833>
    2aee:	f7 c5 00 00 08 00    	test   ebp,0x80000
    2af4:	0f 85 93 0c 00 00    	jne    378d <error_at_line@@Base+0x2824>
    2afa:	f7 c5 00 00 00 20    	test   ebp,0x20000000
    2b00:	0f 85 78 0c 00 00    	jne    377e <error_at_line@@Base+0x2815>
    2b06:	f7 c5 00 00 80 00    	test   ebp,0x800000
    2b0c:	0f 85 5d 0c 00 00    	jne    376f <error_at_line@@Base+0x2806>
    2b12:	f7 c5 00 00 00 01    	test   ebp,0x1000000
    2b18:	0f 85 42 0c 00 00    	jne    3760 <error_at_line@@Base+0x27f7>
    2b1e:	41 f6 c0 10          	test   r8b,0x10
    2b22:	0f 85 2c 0c 00 00    	jne    3754 <error_at_line@@Base+0x27eb>
    2b28:	41 f7 c0 00 00 40 00 	test   r8d,0x400000
    2b2f:	0f 85 13 0c 00 00    	jne    3748 <error_at_line@@Base+0x27df>
    2b35:	41 f7 c0 00 01 00 00 	test   r8d,0x100
    2b3c:	0f 85 53 0d 00 00    	jne    3895 <error_at_line@@Base+0x292c>
    2b42:	41 f7 c0 00 00 00 08 	test   r8d,0x8000000
    2b49:	0f 85 37 0d 00 00    	jne    3886 <error_at_line@@Base+0x291d>
    2b4f:	41 f7 c0 00 00 00 10 	test   r8d,0x10000000
    2b56:	0f 85 1b 0d 00 00    	jne    3877 <error_at_line@@Base+0x290e>
    2b5c:	41 f7 c0 00 00 00 20 	test   r8d,0x20000000
    2b63:	0f 85 ff 0c 00 00    	jne    3868 <error_at_line@@Base+0x28ff>
    2b69:	41 f7 c0 00 00 00 02 	test   r8d,0x2000000
    2b70:	0f 85 e3 0c 00 00    	jne    3859 <error_at_line@@Base+0x28f0>
    2b76:	41 f6 c0 20          	test   r8b,0x20
    2b7a:	0f 85 ca 0c 00 00    	jne    384a <error_at_line@@Base+0x28e1>
    2b80:	41 f6 c0 80          	test   r8b,0x80
    2b84:	0f 85 b1 0c 00 00    	jne    383b <error_at_line@@Base+0x28d2>
    2b8a:	f6 c6 40             	test   dh,0x40
    2b8d:	0f 85 99 0c 00 00    	jne    382c <error_at_line@@Base+0x28c3>
    2b93:	f7 c2 00 00 01 00    	test   edx,0x10000
    2b99:	0f 85 7e 0c 00 00    	jne    381d <error_at_line@@Base+0x28b4>
    2b9f:	f7 c2 00 00 04 00    	test   edx,0x40000
    2ba5:	0f 85 63 0c 00 00    	jne    380e <error_at_line@@Base+0x28a5>
    2bab:	f7 c2 00 00 10 00    	test   edx,0x100000
    2bb1:	0f 85 48 0c 00 00    	jne    37ff <error_at_line@@Base+0x2896>
    2bb7:	f6 c2 20             	test   dl,0x20
    2bba:	0f 85 30 0c 00 00    	jne    37f0 <error_at_line@@Base+0x2887>
    2bc0:	45 85 e4             	test   r12d,r12d
    2bc3:	74 24                	je     2be9 <error_at_line@@Base+0x1c80>
    2bc5:	f7 c2 00 00 00 01    	test   edx,0x1000000
    2bcb:	0f 85 78 06 00 00    	jne    3249 <error_at_line@@Base+0x22e0>
    2bd1:	f7 c2 00 00 00 02    	test   edx,0x2000000
    2bd7:	0f 85 5d 06 00 00    	jne    323a <error_at_line@@Base+0x22d1>
    2bdd:	f7 c2 00 00 40 00    	test   edx,0x400000
    2be3:	0f 85 6f 06 00 00    	jne    3258 <error_at_line@@Base+0x22ef>
    2be9:	45 85 d2             	test   r10d,r10d
    2bec:	0f 84 c4 00 00 00    	je     2cb6 <error_at_line@@Base+0x1d4d>
    2bf2:	f7 c5 00 00 01 00    	test   ebp,0x10000
    2bf8:	74 0a                	je     2c04 <error_at_line@@Base+0x1c9b>
    2bfa:	81 0d b8 c8 00 00 00 	or     DWORD PTR [rip+0xc8b8],0x8000        # f4bc <error_print_progname@@Base+0x3d4>
    2c01:	80 00 00 
    2c04:	85 ed                	test   ebp,ebp
    2c06:	0f 88 a5 04 00 00    	js     30b1 <error_at_line@@Base+0x2148>
    2c0c:	f7 c5 00 00 00 40    	test   ebp,0x40000000
    2c12:	74 0a                	je     2c1e <error_at_line@@Base+0x1cb5>
    2c14:	81 0d 9e c8 00 00 00 	or     DWORD PTR [rip+0xc89e],0x200000        # f4bc <error_print_progname@@Base+0x3d4>
    2c1b:	00 20 00 
    2c1e:	f7 c5 00 00 02 00    	test   ebp,0x20000
    2c24:	74 0a                	je     2c30 <error_at_line@@Base+0x1cc7>
    2c26:	81 0d 8c c8 00 00 00 	or     DWORD PTR [rip+0xc88c],0x400000        # f4bc <error_print_progname@@Base+0x3d4>
    2c2d:	00 40 00 
    2c30:	f7 c5 00 00 00 10    	test   ebp,0x10000000
    2c36:	74 0a                	je     2c42 <error_at_line@@Base+0x1cd9>
    2c38:	81 0d 7a c8 00 00 00 	or     DWORD PTR [rip+0xc87a],0x800000        # f4bc <error_print_progname@@Base+0x3d4>
    2c3f:	00 80 00 
    2c42:	81 e5 00 00 20 00    	and    ebp,0x200000
    2c48:	74 0a                	je     2c54 <error_at_line@@Base+0x1ceb>
    2c4a:	81 0d 68 c8 00 00 00 	or     DWORD PTR [rip+0xc868],0x8000000        # f4bc <error_print_progname@@Base+0x3d4>
    2c51:	00 00 08 
    2c54:	41 f6 c0 02          	test   r8b,0x2
    2c58:	74 0a                	je     2c64 <error_at_line@@Base+0x1cfb>
    2c5a:	81 0d 58 c8 00 00 00 	or     DWORD PTR [rip+0xc858],0x4000000        # f4bc <error_print_progname@@Base+0x3d4>
    2c61:	00 00 04 
    2c64:	41 f6 c0 40          	test   r8b,0x40
    2c68:	74 0a                	je     2c74 <error_at_line@@Base+0x1d0b>
    2c6a:	81 0d 48 c8 00 00 00 	or     DWORD PTR [rip+0xc848],0x80000000        # f4bc <error_print_progname@@Base+0x3d4>
    2c71:	00 00 80 
    2c74:	41 f7 c0 00 08 00 00 	test   r8d,0x800
    2c7b:	0f 85 ff 04 00 00    	jne    3180 <error_at_line@@Base+0x2217>
    2c81:	41 f7 c0 00 10 00 00 	test   r8d,0x1000
    2c88:	0f 85 e6 04 00 00    	jne    3174 <error_at_line@@Base+0x220b>
    2c8e:	41 f7 c0 00 40 00 00 	test   r8d,0x4000
    2c95:	74 0a                	je     2ca1 <error_at_line@@Base+0x1d38>
    2c97:	81 0d 1b c8 00 00 00 	or     DWORD PTR [rip+0xc81b],0x40000000        # f4bc <error_print_progname@@Base+0x3d4>
    2c9e:	00 00 40 
    2ca1:	f6 c6 01             	test   dh,0x1
    2ca4:	0f 85 be 04 00 00    	jne    3168 <error_at_line@@Base+0x21ff>
    2caa:	81 e2 00 00 80 00    	and    edx,0x800000
    2cb0:	0f 85 a3 04 00 00    	jne    3159 <error_at_line@@Base+0x21f0>
    2cb6:	85 c0                	test   eax,eax
    2cb8:	0f 84 70 03 00 00    	je     302e <error_at_line@@Base+0x20c5>
    2cbe:	b8 07 00 00 00       	mov    eax,0x7
    2cc3:	b9 01 00 00 00       	mov    ecx,0x1
    2cc8:	0f a2                	cpuid
    2cca:	a9 00 00 40 00       	test   eax,0x400000
    2ccf:	0f 85 56 05 00 00    	jne    322b <error_at_line@@Base+0x22c2>
    2cd5:	a8 80                	test   al,0x80
    2cd7:	0f 85 42 05 00 00    	jne    321f <error_at_line@@Base+0x22b6>
    2cdd:	f6 c6 40             	test   dh,0x40
    2ce0:	0f 85 2a 05 00 00    	jne    3210 <error_at_line@@Base+0x22a7>
    2ce6:	a8 08                	test   al,0x8
    2ce8:	0f 85 13 05 00 00    	jne    3201 <error_at_line@@Base+0x2298>
    2cee:	f6 c6 80             	test   dh,0x80
    2cf1:	0f 85 bf 04 00 00    	jne    31b6 <error_at_line@@Base+0x224d>
    2cf7:	85 c0                	test   eax,eax
    2cf9:	0f 88 ef 0b 00 00    	js     38ee <error_at_line@@Base+0x2985>
    2cff:	85 f6                	test   esi,esi
    2d01:	74 4c                	je     2d4f <error_at_line@@Base+0x1de6>
    2d03:	a8 10                	test   al,0x10
    2d05:	0f 85 97 0c 00 00    	jne    39a2 <error_at_line@@Base+0x2a39>
    2d0b:	a9 00 00 80 00       	test   eax,0x800000
    2d10:	0f 85 80 0c 00 00    	jne    3996 <error_at_line@@Base+0x2a2d>
    2d16:	f6 c2 10             	test   dl,0x10
    2d19:	0f 85 6b 0c 00 00    	jne    398a <error_at_line@@Base+0x2a21>
    2d1f:	f6 c2 20             	test   dl,0x20
    2d22:	0f 85 56 0c 00 00    	jne    397e <error_at_line@@Base+0x2a15>
    2d28:	f6 c6 04             	test   dh,0x4
    2d2b:	0f 85 3e 0c 00 00    	jne    396f <error_at_line@@Base+0x2a06>
    2d31:	a8 02                	test   al,0x2
    2d33:	0f 85 27 0c 00 00    	jne    3960 <error_at_line@@Base+0x29f7>
    2d39:	a8 01                	test   al,0x1
    2d3b:	0f 85 8b 0c 00 00    	jne    39cc <error_at_line@@Base+0x2a63>
    2d41:	a8 04                	test   al,0x4
    2d43:	74 0a                	je     2d4f <error_at_line@@Base+0x1de6>
    2d45:	81 0d 59 c7 00 00 00 	or     DWORD PTR [rip+0xc759],0x4000        # f4a8 <error_print_progname@@Base+0x3c0>
    2d4c:	40 00 00 
    2d4f:	45 85 d2             	test   r10d,r10d
    2d52:	74 13                	je     2d67 <error_at_line@@Base+0x1dfe>
    2d54:	a8 20                	test   al,0x20
    2d56:	0f 85 55 0c 00 00    	jne    39b1 <error_at_line@@Base+0x2a48>
    2d5c:	89 d1                	mov    ecx,edx
    2d5e:	c1 e9 13             	shr    ecx,0x13
    2d61:	83 e1 01             	and    ecx,0x1
    2d64:	41 89 ca             	mov    r10d,ecx
    2d67:	45 85 e4             	test   r12d,r12d
    2d6a:	74 1a                	je     2d86 <error_at_line@@Base+0x1e1d>
    2d6c:	a9 00 00 20 00       	test   eax,0x200000
    2d71:	0f 85 46 0c 00 00    	jne    39bd <error_at_line@@Base+0x2a54>
    2d77:	f6 c6 01             	test   dh,0x1
    2d7a:	74 0a                	je     2d86 <error_at_line@@Base+0x1e1d>
    2d7c:	81 0d 22 c7 00 00 00 	or     DWORD PTR [rip+0xc722],0x400        # f4a8 <error_print_progname@@Base+0x3c0>
    2d83:	04 00 00 
    2d86:	45 85 c9             	test   r9d,r9d
    2d89:	74 12                	je     2d9d <error_at_line@@Base+0x1e34>
    2d8b:	81 e2 00 00 20 00    	and    edx,0x200000
    2d91:	74 0a                	je     2d9d <error_at_line@@Base+0x1e34>
    2d93:	81 0d 0b c7 00 00 00 	or     DWORD PTR [rip+0xc70b],0x8000        # f4a8 <error_print_progname@@Base+0x3c0>
    2d9a:	80 00 00 
    2d9d:	83 ff 0c             	cmp    edi,0xc
    2da0:	76 59                	jbe    2dfb <error_at_line@@Base+0x1e92>
    2da2:	b8 0d 00 00 00       	mov    eax,0xd
    2da7:	b9 01 00 00 00       	mov    ecx,0x1
    2dac:	0f a2                	cpuid
    2dae:	a8 01                	test   al,0x1
    2db0:	0f 85 1e 04 00 00    	jne    31d4 <error_at_line@@Base+0x226b>
    2db6:	a8 02                	test   al,0x2
    2db8:	0f 85 07 04 00 00    	jne    31c5 <error_at_line@@Base+0x225c>
    2dbe:	a8 08                	test   al,0x8
    2dc0:	0f 85 c6 03 00 00    	jne    318c <error_at_line@@Base+0x2223>
    2dc6:	83 ff 13             	cmp    edi,0x13
    2dc9:	76 30                	jbe    2dfb <error_at_line@@Base+0x1e92>
    2dcb:	b8 14 00 00 00       	mov    eax,0x14
    2dd0:	31 c9                	xor    ecx,ecx
    2dd2:	0f a2                	cpuid
    2dd4:	80 e3 10             	and    bl,0x10
    2dd7:	0f 85 d0 0a 00 00    	jne    38ad <error_at_line@@Base+0x2944>
    2ddd:	83 ff 18             	cmp    edi,0x18
    2de0:	76 19                	jbe    2dfb <error_at_line@@Base+0x1e92>
    2de2:	b8 19 00 00 00       	mov    eax,0x19
    2de7:	0f a2                	cpuid
    2de9:	f6 c3 01             	test   bl,0x1
    2dec:	0f 85 d6 04 00 00    	jne    32c8 <error_at_line@@Base+0x235f>
    2df2:	83 ff 1d             	cmp    edi,0x1d
    2df5:	0f 87 c5 02 00 00    	ja     30c0 <error_at_line@@Base+0x2157>
    2dfb:	b8 00 00 00 80       	mov    eax,0x80000000
    2e00:	0f a2                	cpuid
    2e02:	89 c7                	mov    edi,eax
    2e04:	3d 00 00 00 80       	cmp    eax,0x80000000
    2e09:	0f 86 cf 00 00 00    	jbe    2ede <error_at_line@@Base+0x1f75>
    2e0f:	b8 01 00 00 80       	mov    eax,0x80000001
    2e14:	0f a2                	cpuid
    2e16:	f6 c1 40             	test   cl,0x40
    2e19:	74 0a                	je     2e25 <error_at_line@@Base+0x1ebc>
    2e1b:	81 0d 97 c6 00 00 00 	or     DWORD PTR [rip+0xc697],0x800        # f4bc <error_print_progname@@Base+0x3d4>
    2e22:	08 00 00 
    2e25:	f6 c1 01             	test   cl,0x1
    2e28:	0f 85 c0 08 00 00    	jne    36ee <error_at_line@@Base+0x2785>
    2e2e:	89 c8                	mov    eax,ecx
    2e30:	83 e0 20             	and    eax,0x20
    2e33:	0f 85 a6 08 00 00    	jne    36df <error_at_line@@Base+0x2776>
    2e39:	f6 c5 80             	test   ch,0x80
    2e3c:	0f 85 8e 08 00 00    	jne    36d0 <error_at_line@@Base+0x2767>
    2e42:	f7 c1 00 00 20 00    	test   ecx,0x200000
    2e48:	0f 85 73 08 00 00    	jne    36c1 <error_at_line@@Base+0x2758>
    2e4e:	85 c0                	test   eax,eax
    2e50:	0f 85 8b 09 00 00    	jne    37e1 <error_at_line@@Base+0x2878>
    2e56:	f6 c5 01             	test   ch,0x1
    2e59:	0f 85 76 09 00 00    	jne    37d5 <error_at_line@@Base+0x286c>
    2e5f:	f7 c1 00 00 00 20    	test   ecx,0x20000000
    2e65:	0f 85 5b 09 00 00    	jne    37c6 <error_at_line@@Base+0x285d>
    2e6b:	f7 c2 00 00 00 20    	test   edx,0x20000000
    2e71:	0f 85 40 09 00 00    	jne    37b7 <error_at_line@@Base+0x284e>
    2e77:	f7 c2 00 00 00 40    	test   edx,0x40000000
    2e7d:	0f 85 7a 08 00 00    	jne    36fd <error_at_line@@Base+0x2794>
    2e83:	85 d2                	test   edx,edx
    2e85:	0f 88 16 0a 00 00    	js     38a1 <error_at_line@@Base+0x2938>
    2e8b:	85 f6                	test   esi,esi
    2e8d:	74 1b                	je     2eaa <error_at_line@@Base+0x1f41>
    2e8f:	f7 c1 00 00 01 00    	test   ecx,0x10000
    2e95:	74 0a                	je     2ea1 <error_at_line@@Base+0x1f38>
    2e97:	81 0d 1b c6 00 00 00 	or     DWORD PTR [rip+0xc61b],0x1000        # f4bc <error_print_progname@@Base+0x3d4>
    2e9e:	10 00 00 
    2ea1:	80 e5 08             	and    ch,0x8
    2ea4:	0f 85 f8 01 00 00    	jne    30a2 <error_at_line@@Base+0x2139>
    2eaa:	81 ff 07 00 00 80    	cmp    edi,0x80000007
    2eb0:	76 2c                	jbe    2ede <error_at_line@@Base+0x1f75>
    2eb2:	b8 08 00 00 80       	mov    eax,0x80000008
    2eb7:	0f a2                	cpuid
    2eb9:	41 89 d8             	mov    r8d,ebx
    2ebc:	f6 c3 01             	test   bl,0x1
    2ebf:	0f 85 2d 03 00 00    	jne    31f2 <error_at_line@@Base+0x2289>
    2ec5:	41 81 e0 00 02 00 00 	and    r8d,0x200
    2ecc:	0f 85 11 03 00 00    	jne    31e3 <error_at_line@@Base+0x227a>
    2ed2:	81 ff 20 00 00 80    	cmp    edi,0x80000020
    2ed8:	0f 87 a3 01 00 00    	ja     3081 <error_at_line@@Base+0x2118>
    2ede:	41 81 fb 47 65 6e 75 	cmp    r11d,0x756e6547
    2ee5:	0f 84 bf 00 00 00    	je     2faa <error_at_line@@Base+0x2041>
    2eeb:	41 81 fb 41 75 74 68 	cmp    r11d,0x68747541
    2ef2:	0f 84 3e 01 00 00    	je     3036 <error_at_line@@Base+0x20cd>
    2ef8:	41 81 fb 43 65 6e 74 	cmp    r11d,0x746e6543
    2eff:	0f 94 c2             	sete   dl
    2f02:	41 83 fe 06          	cmp    r14d,0x6
    2f06:	0f 87 3e 01 00 00    	ja     304a <error_at_line@@Base+0x20e1>
    2f0c:	b8 05 00 00 00       	mov    eax,0x5
    2f11:	84 d2                	test   dl,dl
    2f13:	0f 84 31 01 00 00    	je     304a <error_at_line@@Base+0x20e1>
    2f19:	89 05 91 c5 00 00    	mov    DWORD PTR [rip+0xc591],eax        # f4b0 <error_print_progname@@Base+0x3c8>
    2f1f:	8b 05 7b c5 00 00    	mov    eax,DWORD PTR [rip+0xc57b]        # f4a0 <error_print_progname@@Base+0x3b8>
    2f25:	a9 00 00 80 00       	test   eax,0x800000
    2f2a:	74 0f                	je     2f3b <error_at_line@@Base+0x1fd2>
    2f2c:	8b 15 8a c5 00 00    	mov    edx,DWORD PTR [rip+0xc58a]        # f4bc <error_print_progname@@Base+0x3d4>
    2f32:	f6 c2 10             	test   dl,0x10
    2f35:	0f 85 0e 07 00 00    	jne    3649 <error_at_line@@Base+0x26e0>
    2f3b:	48 8b 6c 24 08       	mov    rbp,QWORD PTR [rsp+0x8]
    2f40:	4c 8b 64 24 10       	mov    r12,QWORD PTR [rsp+0x10]
    2f45:	31 c0                	xor    eax,eax
    2f47:	4c 8b 6c 24 18       	mov    r13,QWORD PTR [rsp+0x18]
    2f4c:	4c 8b 74 24 20       	mov    r14,QWORD PTR [rsp+0x20]
    2f51:	4c 8b 7c 24 28       	mov    r15,QWORD PTR [rsp+0x28]
    2f56:	eb 0f                	jmp    2f67 <error_at_line@@Base+0x1ffe>
    2f58:	c7 05 4e c5 00 00 04 	mov    DWORD PTR [rip+0xc54e],0x4        # f4b0 <error_print_progname@@Base+0x3c8>
    2f5f:	00 00 00 
    2f62:	b8 ff ff ff ff       	mov    eax,0xffffffff
    2f67:	48 8b 1c 24          	mov    rbx,QWORD PTR [rsp]
    2f6b:	48 83 c4 30          	add    rsp,0x30
    2f6f:	c3                   	ret
    2f70:	31 c0                	xor    eax,eax
    2f72:	c3                   	ret
    2f73:	31 c9                	xor    ecx,ecx
    2f75:	0f 01 d0             	xgetbv
    2f78:	89 c2                	mov    edx,eax
    2f7a:	f7 d2                	not    edx
    2f7c:	80 e2 06             	and    dl,0x6
    2f7f:	0f 84 9c 06 00 00    	je     3621 <error_at_line@@Base+0x26b8>
    2f85:	45 31 d2             	xor    r10d,r10d
    2f88:	31 f6                	xor    esi,esi
    2f8a:	89 c2                	mov    edx,eax
    2f8c:	45 31 e4             	xor    r12d,r12d
    2f8f:	f7 d2                	not    edx
    2f91:	81 e2 00 00 06 00    	and    edx,0x60000
    2f97:	41 0f 94 c4          	sete   r12b
    2f9b:	c1 e8 13             	shr    eax,0x13
    2f9e:	41 89 c1             	mov    r9d,eax
    2fa1:	41 83 e1 01          	and    r9d,0x1
    2fa5:	e9 5b f9 ff ff       	jmp    2905 <error_at_line@@Base+0x199c>
    2faa:	41 83 fe 0f          	cmp    r14d,0xf
    2fae:	0f 84 05 09 00 00    	je     38b9 <error_at_line@@Base+0x2950>
    2fb4:	41 83 fe 06          	cmp    r14d,0x6
    2fb8:	0f 84 a9 02 00 00    	je     3267 <error_at_line@@Base+0x22fe>
    2fbe:	b8 01 00 00 00       	mov    eax,0x1
    2fc3:	e9 51 ff ff ff       	jmp    2f19 <error_at_line@@Base+0x1fb0>
    2fc8:	81 0d ce c4 00 00 00 	or     DWORD PTR [rip+0xc4ce],0x8000        # f4a0 <error_print_progname@@Base+0x3b8>
    2fcf:	80 00 00 
    2fd2:	e9 76 f9 ff ff       	jmp    294d <error_at_line@@Base+0x19e4>
    2fd7:	81 0d bf c4 00 00 00 	or     DWORD PTR [rip+0xc4bf],0x40000000        # f4a0 <error_print_progname@@Base+0x3b8>
    2fde:	00 00 40 
    2fe1:	e9 f3 f9 ff ff       	jmp    29d9 <error_at_line@@Base+0x1a70>
    2fe6:	81 0d b0 c4 00 00 00 	or     DWORD PTR [rip+0xc4b0],0x80000        # f4a0 <error_print_progname@@Base+0x3b8>
    2fed:	00 08 00 
    2ff0:	e9 64 f9 ff ff       	jmp    2959 <error_at_line@@Base+0x19f0>
    2ff5:	81 0d a5 c4 00 00 00 	or     DWORD PTR [rip+0xc4a5],0x20000        # f4a4 <error_print_progname@@Base+0x3bc>
    2ffc:	00 02 00 
    2fff:	e9 17 fa ff ff       	jmp    2a1b <error_at_line@@Base+0x1ab2>
    3004:	83 0d 99 c4 00 00 20 	or     DWORD PTR [rip+0xc499],0x20        # f4a4 <error_print_progname@@Base+0x3bc>
    300b:	e9 fe f9 ff ff       	jmp    2a0e <error_at_line@@Base+0x1aa5>
    3010:	81 0d 86 c4 00 00 00 	or     DWORD PTR [rip+0xc486],0x4000000        # f4a0 <error_print_progname@@Base+0x3b8>
    3017:	00 00 04 
    301a:	e9 d4 f9 ff ff       	jmp    29f3 <error_at_line@@Base+0x1a8a>
    301f:	81 0d 77 c4 00 00 00 	or     DWORD PTR [rip+0xc477],0x4000        # f4a0 <error_print_progname@@Base+0x3b8>
    3026:	40 00 00 
    3029:	e9 b8 f9 ff ff       	jmp    29e6 <error_at_line@@Base+0x1a7d>
    302e:	45 31 d2             	xor    r10d,r10d
    3031:	e9 67 fd ff ff       	jmp    2d9d <error_at_line@@Base+0x1e34>
    3036:	41 83 fe 0f          	cmp    r14d,0xf
    303a:	0f 84 60 02 00 00    	je     32a0 <error_at_line@@Base+0x2337>
    3040:	b8 02 00 00 00       	mov    eax,0x2
    3045:	e9 cf fe ff ff       	jmp    2f19 <error_at_line@@Base+0x1fb0>
    304a:	41 81 fb 20 20 53 68 	cmp    r11d,0x68532020
    3051:	0f 84 a7 02 00 00    	je     32fe <error_at_line@@Base+0x2395>
    3057:	84 d2                	test   dl,dl
    3059:	0f 85 9f 02 00 00    	jne    32fe <error_at_line@@Base+0x2395>
    305f:	41 81 fb 43 79 72 69 	cmp    r11d,0x69727943
    3066:	0f 84 6f 09 00 00    	je     39db <error_at_line@@Base+0x2a72>
    306c:	31 c0                	xor    eax,eax
    306e:	41 81 fb 47 65 6f 64 	cmp    r11d,0x646f6547
    3075:	0f 94 c0             	sete   al
    3078:	8d 44 40 04          	lea    eax,[rax+rax*2+0x4]
    307c:	e9 98 fe ff ff       	jmp    2f19 <error_at_line@@Base+0x1fb0>
    3081:	b8 21 00 00 80       	mov    eax,0x80000021
    3086:	0f a2                	cpuid
    3088:	a9 00 00 10 00       	test   eax,0x100000
    308d:	0f 84 4b fe ff ff    	je     2ede <error_at_line@@Base+0x1f75>
    3093:	81 0d 0b c4 00 00 00 	or     DWORD PTR [rip+0xc40b],0x100        # f4a8 <error_print_progname@@Base+0x3c0>
    309a:	01 00 00 
    309d:	e9 3c fe ff ff       	jmp    2ede <error_at_line@@Base+0x1f75>
    30a2:	81 0d 10 c4 00 00 00 	or     DWORD PTR [rip+0xc410],0x2000        # f4bc <error_print_progname@@Base+0x3d4>
    30a9:	20 00 00 
    30ac:	e9 f9 fd ff ff       	jmp    2eaa <error_at_line@@Base+0x1f41>
    30b1:	81 0d 01 c4 00 00 00 	or     DWORD PTR [rip+0xc401],0x100000        # f4bc <error_print_progname@@Base+0x3d4>
    30b8:	00 10 00 
    30bb:	e9 4c fb ff ff       	jmp    2c0c <error_at_line@@Base+0x1ca3>
    30c0:	b8 1e 00 00 00       	mov    eax,0x1e
    30c5:	b9 01 00 00 00       	mov    ecx,0x1
    30ca:	0f a2                	cpuid
    30cc:	45 85 e4             	test   r12d,r12d
    30cf:	74 21                	je     30f2 <error_at_line@@Base+0x2189>
    30d1:	a8 80                	test   al,0x80
    30d3:	0f 85 44 0a 00 00    	jne    3b1d <error_at_line@@Base+0x2bb4>
    30d9:	a8 40                	test   al,0x40
    30db:	0f 85 2d 0a 00 00    	jne    3b0e <error_at_line@@Base+0x2ba5>
    30e1:	a8 10                	test   al,0x10
    30e3:	0f 85 16 0a 00 00    	jne    3aff <error_at_line@@Base+0x2b96>
    30e9:	f6 c4 01             	test   ah,0x1
    30ec:	0f 85 fe 09 00 00    	jne    3af0 <error_at_line@@Base+0x2b87>
    30f2:	83 ff 20             	cmp    edi,0x20
    30f5:	0f 86 00 fd ff ff    	jbe    2dfb <error_at_line@@Base+0x1e92>
    30fb:	b8 21 00 00 00       	mov    eax,0x21
    3100:	0f a2                	cpuid
    3102:	a9 00 00 80 00       	test   eax,0x800000
    3107:	0f 85 d4 09 00 00    	jne    3ae1 <error_at_line@@Base+0x2b78>
    310d:	83 ff 23             	cmp    edi,0x23
    3110:	0f 86 e5 fc ff ff    	jbe    2dfb <error_at_line@@Base+0x1e92>
    3116:	45 85 d2             	test   r10d,r10d
    3119:	0f 84 dc fc ff ff    	je     2dfb <error_at_line@@Base+0x1e92>
    311f:	b8 24 00 00 00       	mov    eax,0x24
    3124:	31 c9                	xor    ecx,ecx
    3126:	0f a2                	cpuid
    3128:	0f b6 d3             	movzx  edx,bl
    312b:	80 eb 01             	sub    bl,0x1
    312e:	74 1a                	je     314a <error_at_line@@Base+0x21e1>
    3130:	8b 05 72 c3 00 00    	mov    eax,DWORD PTR [rip+0xc372]        # f4a8 <error_print_progname@@Base+0x3c0>
    3136:	83 fa 02             	cmp    edx,0x2
    3139:	0f 85 fa 04 00 00    	jne    3639 <error_at_line@@Base+0x26d0>
    313f:	0d 00 00 10 00       	or     eax,0x100000
    3144:	89 05 5e c3 00 00    	mov    DWORD PTR [rip+0xc35e],eax        # f4a8 <error_print_progname@@Base+0x3c0>
    314a:	81 0d 54 c3 00 00 00 	or     DWORD PTR [rip+0xc354],0x40000        # f4a8 <error_print_progname@@Base+0x3c0>
    3151:	00 04 00 
    3154:	e9 a2 fc ff ff       	jmp    2dfb <error_at_line@@Base+0x1e92>
    3159:	81 0d 41 c3 00 00 00 	or     DWORD PTR [rip+0xc341],0x40000000        # f4a4 <error_print_progname@@Base+0x3bc>
    3160:	00 00 40 
    3163:	e9 4e fb ff ff       	jmp    2cb6 <error_at_line@@Base+0x1d4d>
    3168:	83 0d 31 c3 00 00 20 	or     DWORD PTR [rip+0xc331],0x20        # f4a0 <error_print_progname@@Base+0x3b8>
    316f:	e9 36 fb ff ff       	jmp    2caa <error_at_line@@Base+0x1d41>
    3174:	83 0d 25 c3 00 00 08 	or     DWORD PTR [rip+0xc325],0x8        # f4a0 <error_print_progname@@Base+0x3b8>
    317b:	e9 0e fb ff ff       	jmp    2c8e <error_at_line@@Base+0x1d25>
    3180:	83 0d 19 c3 00 00 04 	or     DWORD PTR [rip+0xc319],0x4        # f4a0 <error_print_progname@@Base+0x3b8>
    3187:	e9 f5 fa ff ff       	jmp    2c81 <error_at_line@@Base+0x1d18>
    318c:	81 0d 0e c3 00 00 00 	or     DWORD PTR [rip+0xc30e],0x100000        # f4a4 <error_print_progname@@Base+0x3bc>
    3193:	00 10 00 
    3196:	e9 2b fc ff ff       	jmp    2dc6 <error_at_line@@Base+0x1e5d>
    319b:	81 0d ff c2 00 00 00 	or     DWORD PTR [rip+0xc2ff],0x4000        # f4a4 <error_print_progname@@Base+0x3bc>
    31a2:	40 00 00 
    31a5:	e9 1c f9 ff ff       	jmp    2ac6 <error_at_line@@Base+0x1b5d>
    31aa:	83 0d ef c2 00 00 02 	or     DWORD PTR [rip+0xc2ef],0x2        # f4a0 <error_print_progname@@Base+0x3b8>
    31b1:	e9 03 f9 ff ff       	jmp    2ab9 <error_at_line@@Base+0x1b50>
    31b6:	81 0d e8 c2 00 00 00 	or     DWORD PTR [rip+0xc2e8],0x10000        # f4a8 <error_print_progname@@Base+0x3c0>
    31bd:	00 01 00 
    31c0:	e9 32 fb ff ff       	jmp    2cf7 <error_at_line@@Base+0x1d8e>
    31c5:	81 0d d5 c2 00 00 00 	or     DWORD PTR [rip+0xc2d5],0x40000        # f4a4 <error_print_progname@@Base+0x3bc>
    31cc:	00 04 00 
    31cf:	e9 ea fb ff ff       	jmp    2dbe <error_at_line@@Base+0x1e55>
    31d4:	81 0d c6 c2 00 00 00 	or     DWORD PTR [rip+0xc2c6],0x80000        # f4a4 <error_print_progname@@Base+0x3bc>
    31db:	00 08 00 
    31de:	e9 d3 fb ff ff       	jmp    2db6 <error_at_line@@Base+0x1e4d>
    31e3:	81 0d b7 c2 00 00 00 	or     DWORD PTR [rip+0xc2b7],0x10000        # f4a4 <error_print_progname@@Base+0x3bc>
    31ea:	00 01 00 
    31ed:	e9 e0 fc ff ff       	jmp    2ed2 <error_at_line@@Base+0x1f69>
    31f2:	81 0d a4 c2 00 00 00 	or     DWORD PTR [rip+0xc2a4],0x2000        # f4a0 <error_print_progname@@Base+0x3b8>
    31f9:	20 00 00 
    31fc:	e9 c4 fc ff ff       	jmp    2ec5 <error_at_line@@Base+0x1f5c>
    3201:	81 0d 9d c2 00 00 00 	or     DWORD PTR [rip+0xc29d],0x200        # f4a8 <error_print_progname@@Base+0x3c0>
    3208:	02 00 00 
    320b:	e9 de fa ff ff       	jmp    2cee <error_at_line@@Base+0x1d85>
    3210:	81 0d 8e c2 00 00 00 	or     DWORD PTR [rip+0xc28e],0x100        # f4a8 <error_print_progname@@Base+0x3c0>
    3217:	01 00 00 
    321a:	e9 c7 fa ff ff       	jmp    2ce6 <error_at_line@@Base+0x1d7d>
    321f:	83 0d 82 c2 00 00 40 	or     DWORD PTR [rip+0xc282],0x40        # f4a8 <error_print_progname@@Base+0x3c0>
    3226:	e9 b2 fa ff ff       	jmp    2cdd <error_at_line@@Base+0x1d74>
    322b:	81 0d 6f c2 00 00 00 	or     DWORD PTR [rip+0xc26f],0x2000000        # f4a4 <error_print_progname@@Base+0x3bc>
    3232:	00 00 02 
    3235:	e9 9b fa ff ff       	jmp    2cd5 <error_at_line@@Base+0x1d6c>
    323a:	81 0d 60 c2 00 00 00 	or     DWORD PTR [rip+0xc260],0x400000        # f4a4 <error_print_progname@@Base+0x3bc>
    3241:	00 40 00 
    3244:	e9 94 f9 ff ff       	jmp    2bdd <error_at_line@@Base+0x1c74>
    3249:	81 0d 51 c2 00 00 00 	or     DWORD PTR [rip+0xc251],0x200000        # f4a4 <error_print_progname@@Base+0x3bc>
    3250:	00 20 00 
    3253:	e9 79 f9 ff ff       	jmp    2bd1 <error_at_line@@Base+0x1c68>
    3258:	81 0d 42 c2 00 00 00 	or     DWORD PTR [rip+0xc242],0x800000        # f4a4 <error_print_progname@@Base+0x3bc>
    325f:	00 80 00 
    3262:	e9 82 f9 ff ff       	jmp    2be9 <error_at_line@@Base+0x1c80>
    3267:	8b 4c 24 f8          	mov    ecx,DWORD PTR [rsp-0x8]
    326b:	44 09 e9             	or     ecx,r13d
    326e:	81 f9 b6 00 00 00    	cmp    ecx,0xb6
    3274:	0f 87 03 08 00 00    	ja     3a7d <error_at_line@@Base+0x2b14>
    327a:	83 f9 49             	cmp    ecx,0x49
    327d:	0f 86 62 07 00 00    	jbe    39e5 <error_at_line@@Base+0x2a7c>
    3283:	83 e9 4a             	sub    ecx,0x4a
    3286:	83 f9 6c             	cmp    ecx,0x6c
    3289:	0f 87 2f fd ff ff    	ja     2fbe <error_at_line@@Base+0x2055>
    328f:	48 8d 15 2a 96 00 00 	lea    rdx,[rip+0x962a]        # c8c0 <error_at_line@@Base+0xb957>
    3296:	48 63 04 8a          	movsxd rax,DWORD PTR [rdx+rcx*4]
    329a:	48 01 d0             	add    rax,rdx
    329d:	3e ff e0             	notrack jmp rax
    32a0:	8b 74 24 fc          	mov    esi,DWORD PTR [rsp-0x4]
    32a4:	8b 44 24 f8          	mov    eax,DWORD PTR [rsp-0x8]
    32a8:	83 ee 01             	sub    esi,0x1
    32ab:	44 09 e8             	or     eax,r13d
    32ae:	83 fe 0a             	cmp    esi,0xa
    32b1:	0f 87 89 fd ff ff    	ja     3040 <error_at_line@@Base+0x20d7>
    32b7:	48 8d 0d b6 97 00 00 	lea    rcx,[rip+0x97b6]        # ca74 <error_at_line@@Base+0xbb0b>
    32be:	48 63 14 b1          	movsxd rdx,DWORD PTR [rcx+rsi*4]
    32c2:	48 01 ca             	add    rdx,rcx
    32c5:	3e ff e2             	notrack jmp rdx
    32c8:	8b 05 d6 c1 00 00    	mov    eax,DWORD PTR [rip+0xc1d6]        # f4a4 <error_print_progname@@Base+0x3bc>
    32ce:	89 c2                	mov    edx,eax
    32d0:	0d 00 00 00 18       	or     eax,0x18000000
    32d5:	81 ca 00 00 00 08    	or     edx,0x8000000
    32db:	80 e3 04             	and    bl,0x4
    32de:	0f 44 c2             	cmove  eax,edx
    32e1:	89 c2                	mov    edx,eax
    32e3:	81 ca 00 00 00 04    	or     edx,0x4000000
    32e9:	41 81 e0 00 00 80 00 	and    r8d,0x800000
    32f0:	0f 45 c2             	cmovne eax,edx
    32f3:	89 05 ab c1 00 00    	mov    DWORD PTR [rip+0xc1ab],eax        # f4a4 <error_print_progname@@Base+0x3bc>
    32f9:	e9 f4 fa ff ff       	jmp    2df2 <error_at_line@@Base+0x1e89>
    32fe:	41 83 fe 07          	cmp    r14d,0x7
    3302:	0f 84 f5 05 00 00    	je     38fd <error_at_line@@Base+0x2994>
    3308:	b8 03 00 00 00       	mov    eax,0x3
    330d:	e9 07 fc ff ff       	jmp    2f19 <error_at_line@@Base+0x1fb0>
    3312:	c7 05 98 c1 00 00 14 	mov    DWORD PTR [rip+0xc198],0x14        # f4b4 <error_print_progname@@Base+0x3cc>
    3319:	00 00 00 
    331c:	8d 50 a0             	lea    edx,[rax-0x60]
    331f:	83 fa 17             	cmp    edx,0x17
    3322:	0f 86 46 07 00 00    	jbe    3a6e <error_at_line@@Base+0x2b05>
    3328:	83 f8 4f             	cmp    eax,0x4f
    332b:	0f 86 3d 07 00 00    	jbe    3a6e <error_at_line@@Base+0x2b05>
    3331:	8d 90 30 ff ff ff    	lea    edx,[rax-0xd0]
    3337:	83 fa 07             	cmp    edx,0x7
    333a:	0f 86 2e 07 00 00    	jbe    3a6e <error_at_line@@Base+0x2b05>
    3340:	8d 50 b0             	lea    edx,[rax-0x50]
    3343:	83 fa 0f             	cmp    edx,0xf
    3346:	76 2c                	jbe    3374 <error_at_line@@Base+0x240b>
    3348:	8d 50 80             	lea    edx,[rax-0x80]
    334b:	83 fa 4f             	cmp    edx,0x4f
    334e:	76 24                	jbe    3374 <error_at_line@@Base+0x240b>
    3350:	2d d8 00 00 00       	sub    eax,0xd8
    3355:	83 f8 0f             	cmp    eax,0xf
    3358:	76 1a                	jbe    3374 <error_at_line@@Base+0x240b>
    335a:	f6 05 3f c1 00 00 20 	test   BYTE PTR [rip+0xc13f],0x20        # f4a0 <error_print_progname@@Base+0x3b8>
    3361:	0f 85 07 07 00 00    	jne    3a6e <error_at_line@@Base+0x2b05>
    3367:	f6 05 3d c1 00 00 08 	test   BYTE PTR [rip+0xc13d],0x8        # f4ab <error_print_progname@@Base+0x3c3>
    336e:	0f 84 cc fc ff ff    	je     3040 <error_at_line@@Base+0x20d7>
    3374:	c7 05 3a c1 00 00 28 	mov    DWORD PTR [rip+0xc13a],0x28        # f4b8 <error_print_progname@@Base+0x3d0>
    337b:	00 00 00 
    337e:	e9 bd fc ff ff       	jmp    3040 <error_at_line@@Base+0x20d7>
    3383:	c7 05 27 c1 00 00 09 	mov    DWORD PTR [rip+0xc127],0x9        # f4b4 <error_print_progname@@Base+0x3cc>
    338a:	00 00 00 
    338d:	e9 ae fc ff ff       	jmp    3040 <error_at_line@@Base+0x20d7>
    3392:	c7 05 18 c1 00 00 05 	mov    DWORD PTR [rip+0xc118],0x5        # f4b4 <error_print_progname@@Base+0x3cc>
    3399:	00 00 00 
    339c:	83 f8 02             	cmp    eax,0x2
    339f:	0f 84 87 07 00 00    	je     3b2c <error_at_line@@Base+0x2bc3>
    33a5:	83 f8 0f             	cmp    eax,0xf
    33a8:	0f 87 4f 08 00 00    	ja     3bfd <error_at_line@@Base+0x2c94>
    33ae:	c7 05 00 c1 00 00 07 	mov    DWORD PTR [rip+0xc100],0x7        # f4b8 <error_print_progname@@Base+0x3d0>
    33b5:	00 00 00 
    33b8:	e9 83 fc ff ff       	jmp    3040 <error_at_line@@Base+0x20d7>
    33bd:	c7 05 ed c0 00 00 08 	mov    DWORD PTR [rip+0xc0ed],0x8        # f4b4 <error_print_progname@@Base+0x3cc>
    33c4:	00 00 00 
    33c7:	e9 74 fc ff ff       	jmp    3040 <error_at_line@@Base+0x20d7>
    33cc:	c7 05 de c0 00 00 04 	mov    DWORD PTR [rip+0xc0de],0x4        # f4b4 <error_print_progname@@Base+0x3cc>
    33d3:	00 00 00 
    33d6:	83 f8 04             	cmp    eax,0x4
    33d9:	0f 84 b9 08 00 00    	je     3c98 <error_at_line@@Base+0x2d2f>
    33df:	83 f8 08             	cmp    eax,0x8
    33e2:	0f 84 a1 08 00 00    	je     3c89 <error_at_line@@Base+0x2d20>
    33e8:	83 f8 02             	cmp    eax,0x2
    33eb:	0f 85 4f fc ff ff    	jne    3040 <error_at_line@@Base+0x20d7>
    33f1:	c7 05 bd c0 00 00 04 	mov    DWORD PTR [rip+0xc0bd],0x4        # f4b8 <error_print_progname@@Base+0x3d0>
    33f8:	00 00 00 
    33fb:	e9 19 fb ff ff       	jmp    2f19 <error_at_line@@Base+0x1fb0>
    3400:	c7 05 aa c0 00 00 0f 	mov    DWORD PTR [rip+0xc0aa],0xf        # f4b4 <error_print_progname@@Base+0x3cc>
    3407:	00 00 00 
    340a:	83 f8 0f             	cmp    eax,0xf
    340d:	76 32                	jbe    3441 <error_at_line@@Base+0x24d8>
    340f:	8d 50 f0             	lea    edx,[rax-0x10]
    3412:	83 fa 0f             	cmp    edx,0xf
    3415:	0f 86 8b 07 00 00    	jbe    3ba6 <error_at_line@@Base+0x2c3d>
    341b:	83 e8 60             	sub    eax,0x60
    341e:	83 f8 4f             	cmp    eax,0x4f
    3421:	0f 86 7f 07 00 00    	jbe    3ba6 <error_at_line@@Base+0x2c3d>
    3427:	f6 05 8f c0 00 00 80 	test   BYTE PTR [rip+0xc08f],0x80        # f4bd <error_print_progname@@Base+0x3d5>
    342e:	0f 85 72 07 00 00    	jne    3ba6 <error_at_line@@Base+0x2c3d>
    3434:	f6 05 6a c0 00 00 40 	test   BYTE PTR [rip+0xc06a],0x40        # f4a5 <error_print_progname@@Base+0x3bd>
    343b:	0f 84 ff fb ff ff    	je     3040 <error_at_line@@Base+0x20d7>
    3441:	c7 05 6d c0 00 00 1a 	mov    DWORD PTR [rip+0xc06d],0x1a        # f4b8 <error_print_progname@@Base+0x3d0>
    3448:	00 00 00 
    344b:	e9 f0 fb ff ff       	jmp    3040 <error_at_line@@Base+0x20d7>
    3450:	c7 05 5a c0 00 00 0a 	mov    DWORD PTR [rip+0xc05a],0xa        # f4b4 <error_print_progname@@Base+0x3cc>
    3457:	00 00 00 
    345a:	83 f8 1f             	cmp    eax,0x1f
    345d:	76 21                	jbe    3480 <error_at_line@@Base+0x2517>
    345f:	83 f8 2f             	cmp    eax,0x2f
    3462:	0f 87 4d 07 00 00    	ja     3bb5 <error_at_line@@Base+0x2c4c>
    3468:	8b 05 32 c0 00 00    	mov    eax,DWORD PTR [rip+0xc032]        # f4a0 <error_print_progname@@Base+0x3b8>
    346e:	f6 c4 10             	test   ah,0x10
    3471:	0f 85 3e 07 00 00    	jne    3bb5 <error_at_line@@Base+0x2c4c>
    3477:	f6 c4 20             	test   ah,0x20
    347a:	0f 84 c0 fb ff ff    	je     3040 <error_at_line@@Base+0x20d7>
    3480:	c7 05 2e c0 00 00 0b 	mov    DWORD PTR [rip+0xc02e],0xb        # f4b8 <error_print_progname@@Base+0x3d0>
    3487:	00 00 00 
    348a:	e9 b1 fb ff ff       	jmp    3040 <error_at_line@@Base+0x20d7>
    348f:	48 b8 03 00 00 00 0f 	movabs rax,0xf00000003
    3496:	00 00 00 
    3499:	48 89 05 14 c0 00 00 	mov    QWORD PTR [rip+0xc014],rax        # f4b4 <error_print_progname@@Base+0x3cc>
    34a0:	e9 19 fb ff ff       	jmp    2fbe <error_at_line@@Base+0x2055>
    34a5:	c7 05 05 c0 00 00 06 	mov    DWORD PTR [rip+0xc005],0x6        # f4b4 <error_print_progname@@Base+0x3cc>
    34ac:	00 00 00 
    34af:	e9 0a fb ff ff       	jmp    2fbe <error_at_line@@Base+0x2055>
    34b4:	48 b8 03 00 00 00 19 	movabs rax,0x1900000003
    34bb:	00 00 00 
    34be:	48 89 05 ef bf 00 00 	mov    QWORD PTR [rip+0xbfef],rax        # f4b4 <error_print_progname@@Base+0x3cc>
    34c5:	e9 f4 fa ff ff       	jmp    2fbe <error_at_line@@Base+0x2055>
    34ca:	c7 05 e0 bf 00 00 0e 	mov    DWORD PTR [rip+0xbfe0],0xe        # f4b4 <error_print_progname@@Base+0x3cc>
    34d1:	00 00 00 
    34d4:	e9 e5 fa ff ff       	jmp    2fbe <error_at_line@@Base+0x2055>
    34d9:	48 b8 03 00 00 00 12 	movabs rax,0x1200000003
    34e0:	00 00 00 
    34e3:	48 89 05 ca bf 00 00 	mov    QWORD PTR [rip+0xbfca],rax        # f4b4 <error_print_progname@@Base+0x3cc>
    34ea:	e9 cf fa ff ff       	jmp    2fbe <error_at_line@@Base+0x2055>
    34ef:	48 b8 03 00 00 00 13 	movabs rax,0x1300000003
    34f6:	00 00 00 
    34f9:	48 89 05 b4 bf 00 00 	mov    QWORD PTR [rip+0xbfb4],rax        # f4b4 <error_print_progname@@Base+0x3cc>
    3500:	e9 b9 fa ff ff       	jmp    2fbe <error_at_line@@Base+0x2055>
    3505:	48 b8 03 00 00 00 16 	movabs rax,0x1600000003
    350c:	00 00 00 
    350f:	48 89 05 9e bf 00 00 	mov    QWORD PTR [rip+0xbf9e],rax        # f4b4 <error_print_progname@@Base+0x3cc>
    3516:	e9 a3 fa ff ff       	jmp    2fbe <error_at_line@@Base+0x2055>
    351b:	c7 05 8f bf 00 00 0c 	mov    DWORD PTR [rip+0xbf8f],0xc        # f4b4 <error_print_progname@@Base+0x3cc>
    3522:	00 00 00 
    3525:	e9 94 fa ff ff       	jmp    2fbe <error_at_line@@Base+0x2055>
    352a:	48 b8 03 00 00 00 0e 	movabs rax,0xe00000003
    3531:	00 00 00 
    3534:	48 89 05 79 bf 00 00 	mov    QWORD PTR [rip+0xbf79],rax        # f4b4 <error_print_progname@@Base+0x3cc>
    353b:	e9 7e fa ff ff       	jmp    2fbe <error_at_line@@Base+0x2055>
    3540:	c7 05 6a bf 00 00 03 	mov    DWORD PTR [rip+0xbf6a],0x3        # f4b4 <error_print_progname@@Base+0x3cc>
    3547:	00 00 00 
    354a:	8b 05 50 bf 00 00    	mov    eax,DWORD PTR [rip+0xbf50]        # f4a0 <error_print_progname@@Base+0x3b8>
    3550:	a8 10                	test   al,0x10
    3552:	0f 84 92 07 00 00    	je     3cea <error_at_line@@Base+0x2d81>
    3558:	c7 05 56 bf 00 00 17 	mov    DWORD PTR [rip+0xbf56],0x17        # f4b8 <error_print_progname@@Base+0x3d0>
    355f:	00 00 00 
    3562:	e9 57 fa ff ff       	jmp    2fbe <error_at_line@@Base+0x2055>
    3567:	48 b8 03 00 00 00 18 	movabs rax,0x1800000003
    356e:	00 00 00 
    3571:	48 89 05 3c bf 00 00 	mov    QWORD PTR [rip+0xbf3c],rax        # f4b4 <error_print_progname@@Base+0x3cc>
    3578:	e9 41 fa ff ff       	jmp    2fbe <error_at_line@@Base+0x2055>
    357d:	48 b8 03 00 00 00 11 	movabs rax,0x1100000003
    3584:	00 00 00 
    3587:	48 89 05 26 bf 00 00 	mov    QWORD PTR [rip+0xbf26],rax        # f4b4 <error_print_progname@@Base+0x3cc>
    358e:	e9 2b fa ff ff       	jmp    2fbe <error_at_line@@Base+0x2055>
    3593:	48 b8 03 00 00 00 1b 	movabs rax,0x1b00000003
    359a:	00 00 00 
    359d:	48 89 05 10 bf 00 00 	mov    QWORD PTR [rip+0xbf10],rax        # f4b4 <error_print_progname@@Base+0x3cc>
    35a4:	e9 15 fa ff ff       	jmp    2fbe <error_at_line@@Base+0x2055>
    35a9:	c7 05 01 bf 00 00 0d 	mov    DWORD PTR [rip+0xbf01],0xd        # f4b4 <error_print_progname@@Base+0x3cc>
    35b0:	00 00 00 
    35b3:	e9 06 fa ff ff       	jmp    2fbe <error_at_line@@Base+0x2055>
    35b8:	83 f9 0e             	cmp    ecx,0xe
    35bb:	0f 85 fd f9 ff ff    	jne    2fbe <error_at_line@@Base+0x2055>
    35c1:	48 b8 03 00 00 00 20 	movabs rax,0x2000000003
    35c8:	00 00 00 
    35cb:	48 89 05 e2 be 00 00 	mov    QWORD PTR [rip+0xbee2],rax        # f4b4 <error_print_progname@@Base+0x3cc>
    35d2:	e9 e7 f9 ff ff       	jmp    2fbe <error_at_line@@Base+0x2055>
    35d7:	c7 05 d3 be 00 00 11 	mov    DWORD PTR [rip+0xbed3],0x11        # f4b4 <error_print_progname@@Base+0x3cc>
    35de:	00 00 00 
    35e1:	e9 d8 f9 ff ff       	jmp    2fbe <error_at_line@@Base+0x2055>
    35e6:	48 b8 03 00 00 00 1f 	movabs rax,0x1f00000003
    35ed:	00 00 00 
    35f0:	48 89 05 bd be 00 00 	mov    QWORD PTR [rip+0xbebd],rax        # f4b4 <error_print_progname@@Base+0x3cc>
    35f7:	e9 c2 f9 ff ff       	jmp    2fbe <error_at_line@@Base+0x2055>
    35fc:	48 b8 03 00 00 00 1e 	movabs rax,0x1e00000003
    3603:	00 00 00 
    3606:	48 89 05 a7 be 00 00 	mov    QWORD PTR [rip+0xbea7],rax        # f4b4 <error_print_progname@@Base+0x3cc>
    360d:	e9 ac f9 ff ff       	jmp    2fbe <error_at_line@@Base+0x2055>
    3612:	c7 05 98 be 00 00 12 	mov    DWORD PTR [rip+0xbe98],0x12        # f4b4 <error_print_progname@@Base+0x3cc>
    3619:	00 00 00 
    361c:	e9 9d f9 ff ff       	jmp    2fbe <error_at_line@@Base+0x2055>
    3621:	89 c2                	mov    edx,eax
    3623:	45 31 d2             	xor    r10d,r10d
    3626:	be 01 00 00 00       	mov    esi,0x1
    362b:	f7 d2                	not    edx
    362d:	80 e2 e6             	and    dl,0xe6
    3630:	41 0f 94 c2          	sete   r10b
    3634:	e9 51 f9 ff ff       	jmp    2f8a <error_at_line@@Base+0x2021>
    3639:	0d 00 00 04 00       	or     eax,0x40000
    363e:	89 05 64 be 00 00    	mov    DWORD PTR [rip+0xbe64],eax        # f4a8 <error_print_progname@@Base+0x3c0>
    3644:	e9 b2 f7 ff ff       	jmp    2dfb <error_at_line@@Base+0x1e92>
    3649:	81 0d 51 be 00 00 00 	or     DWORD PTR [rip+0xbe51],0x80000000        # f4a4 <error_print_progname@@Base+0x3bc>
    3650:	00 00 80 
    3653:	89 c1                	mov    ecx,eax
    3655:	f7 d1                	not    ecx
    3657:	81 e1 00 40 40 00    	and    ecx,0x404000
    365d:	0f 85 d8 f8 ff ff    	jne    2f3b <error_at_line@@Base+0x1fd2>
    3663:	89 d1                	mov    ecx,edx
    3665:	f7 d1                	not    ecx
    3667:	81 e1 04 01 00 00    	and    ecx,0x104
    366d:	0f 85 c8 f8 ff ff    	jne    2f3b <error_at_line@@Base+0x1fd2>
    3673:	8b 0d 2f be 00 00    	mov    ecx,DWORD PTR [rip+0xbe2f]        # f4a8 <error_print_progname@@Base+0x3c0>
    3679:	89 ce                	mov    esi,ecx
    367b:	83 ce 01             	or     esi,0x1
    367e:	89 35 24 be 00 00    	mov    DWORD PTR [rip+0xbe24],esi        # f4a8 <error_print_progname@@Base+0x3c0>
    3684:	89 d6                	mov    esi,edx
    3686:	f7 d6                	not    esi
    3688:	81 e6 00 44 03 00    	and    esi,0x34400
    368e:	0f 85 a7 f8 ff ff    	jne    2f3b <error_at_line@@Base+0x1fd2>
    3694:	f7 d0                	not    eax
    3696:	a9 00 00 02 06       	test   eax,0x6020000
    369b:	0f 85 9a f8 ff ff    	jne    2f3b <error_at_line@@Base+0x1fd2>
    36a1:	89 ce                	mov    esi,ecx
    36a3:	89 c8                	mov    eax,ecx
    36a5:	f7 d2                	not    edx
    36a7:	83 ce 07             	or     esi,0x7
    36aa:	83 c8 03             	or     eax,0x3
    36ad:	81 e2 00 00 f0 00    	and    edx,0xf00000
    36b3:	0f 44 c6             	cmove  eax,esi
    36b6:	89 05 ec bd 00 00    	mov    DWORD PTR [rip+0xbdec],eax        # f4a8 <error_print_progname@@Base+0x3c0>
    36bc:	e9 7a f8 ff ff       	jmp    2f3b <error_at_line@@Base+0x1fd2>
    36c1:	81 0d d9 bd 00 00 00 	or     DWORD PTR [rip+0xbdd9],0x1000        # f4a4 <error_print_progname@@Base+0x3bc>
    36c8:	10 00 00 
    36cb:	e9 7e f7 ff ff       	jmp    2e4e <error_at_line@@Base+0x1ee5>
    36d0:	81 0d c6 bd 00 00 00 	or     DWORD PTR [rip+0xbdc6],0x1000000        # f4a0 <error_print_progname@@Base+0x3b8>
    36d7:	00 00 01 
    36da:	e9 63 f7 ff ff       	jmp    2e42 <error_at_line@@Base+0x1ed9>
    36df:	81 0d b7 bd 00 00 00 	or     DWORD PTR [rip+0xbdb7],0x200        # f4a0 <error_print_progname@@Base+0x3b8>
    36e6:	02 00 00 
    36e9:	e9 4b f7 ff ff       	jmp    2e39 <error_at_line@@Base+0x1ed0>
    36ee:	81 0d a8 bd 00 00 00 	or     DWORD PTR [rip+0xbda8],0x400000        # f4a0 <error_print_progname@@Base+0x3b8>
    36f5:	00 40 00 
    36f8:	e9 31 f7 ff ff       	jmp    2e2e <error_at_line@@Base+0x1ec5>
    36fd:	81 0d 99 bd 00 00 80 	or     DWORD PTR [rip+0xbd99],0x80        # f4a0 <error_print_progname@@Base+0x3b8>
    3704:	00 00 00 
    3707:	e9 77 f7 ff ff       	jmp    2e83 <error_at_line@@Base+0x1f1a>
    370c:	81 0d 8e bd 00 00 80 	or     DWORD PTR [rip+0xbd8e],0x80        # f4a4 <error_print_progname@@Base+0x3bc>
    3713:	00 00 00 
    3716:	e9 7d f3 ff ff       	jmp    2a98 <error_at_line@@Base+0x1b2f>
    371b:	81 0d 7b bd 00 00 00 	or     DWORD PTR [rip+0xbd7b],0x100000        # f4a0 <error_print_progname@@Base+0x3b8>
    3722:	00 10 00 
    3725:	e9 62 f3 ff ff       	jmp    2a8c <error_at_line@@Base+0x1b23>
    372a:	81 0d 70 bd 00 00 00 	or     DWORD PTR [rip+0xbd70],0x200        # f4a4 <error_print_progname@@Base+0x3bc>
    3731:	02 00 00 
    3734:	e9 49 f3 ff ff       	jmp    2a82 <error_at_line@@Base+0x1b19>
    3739:	81 0d 5d bd 00 00 00 	or     DWORD PTR [rip+0xbd5d],0x20000        # f4a0 <error_print_progname@@Base+0x3b8>
    3740:	00 02 00 
    3743:	e9 0a f3 ff ff       	jmp    2a52 <error_at_line@@Base+0x1ae9>
    3748:	83 0d 55 bd 00 00 10 	or     DWORD PTR [rip+0xbd55],0x10        # f4a4 <error_print_progname@@Base+0x3bc>
    374f:	e9 e1 f3 ff ff       	jmp    2b35 <error_at_line@@Base+0x1bcc>
    3754:	83 0d 49 bd 00 00 01 	or     DWORD PTR [rip+0xbd49],0x1        # f4a4 <error_print_progname@@Base+0x3bc>
    375b:	e9 c8 f3 ff ff       	jmp    2b28 <error_at_line@@Base+0x1bbf>
    3760:	81 0d 36 bd 00 00 00 	or     DWORD PTR [rip+0xbd36],0x1000        # f4a0 <error_print_progname@@Base+0x3b8>
    3767:	10 00 00 
    376a:	e9 af f3 ff ff       	jmp    2b1e <error_at_line@@Base+0x1bb5>
    376f:	81 0d 27 bd 00 00 00 	or     DWORD PTR [rip+0xbd27],0x800        # f4a0 <error_print_progname@@Base+0x3b8>
    3776:	08 00 00 
    3779:	e9 94 f3 ff ff       	jmp    2b12 <error_at_line@@Base+0x1ba9>
    377e:	81 0d 1c bd 00 00 00 	or     DWORD PTR [rip+0xbd1c],0x400        # f4a4 <error_print_progname@@Base+0x3bc>
    3785:	04 00 00 
    3788:	e9 79 f3 ff ff       	jmp    2b06 <error_at_line@@Base+0x1b9d>
    378d:	81 0d 09 bd 00 00 00 	or     DWORD PTR [rip+0xbd09],0x100        # f4a0 <error_print_progname@@Base+0x3b8>
    3794:	01 00 00 
    3797:	e9 5e f3 ff ff       	jmp    2afa <error_at_line@@Base+0x1b91>
    379c:	83 0d 01 bd 00 00 40 	or     DWORD PTR [rip+0xbd01],0x40        # f4a4 <error_print_progname@@Base+0x3bc>
    37a3:	e9 46 f3 ff ff       	jmp    2aee <error_at_line@@Base+0x1b85>
    37a8:	81 0d ee bc 00 00 00 	or     DWORD PTR [rip+0xbcee],0x40000        # f4a0 <error_print_progname@@Base+0x3b8>
    37af:	00 04 00 
    37b2:	e9 2b f3 ff ff       	jmp    2ae2 <error_at_line@@Base+0x1b79>
    37b7:	81 0d df bc 00 00 00 	or     DWORD PTR [rip+0xbcdf],0x800000        # f4a0 <error_print_progname@@Base+0x3b8>
    37be:	00 80 00 
    37c1:	e9 b1 f6 ff ff       	jmp    2e77 <error_at_line@@Base+0x1f0e>
    37c6:	81 0d d0 bc 00 00 00 	or     DWORD PTR [rip+0xbcd0],0x20000000        # f4a0 <error_print_progname@@Base+0x3b8>
    37cd:	00 00 20 
    37d0:	e9 96 f6 ff ff       	jmp    2e6b <error_at_line@@Base+0x1f02>
    37d5:	83 0d c8 bc 00 00 04 	or     DWORD PTR [rip+0xbcc8],0x4        # f4a4 <error_print_progname@@Base+0x3bc>
    37dc:	e9 7e f6 ff ff       	jmp    2e5f <error_at_line@@Base+0x1ef6>
    37e1:	81 0d b5 bc 00 00 00 	or     DWORD PTR [rip+0xbcb5],0x2000000        # f4a0 <error_print_progname@@Base+0x3b8>
    37e8:	00 00 02 
    37eb:	e9 66 f6 ff ff       	jmp    2e56 <error_at_line@@Base+0x1eed>
    37f0:	81 0d aa bc 00 00 00 	or     DWORD PTR [rip+0xbcaa],0x1000000        # f4a4 <error_print_progname@@Base+0x3bc>
    37f7:	00 00 01 
    37fa:	e9 c1 f3 ff ff       	jmp    2bc0 <error_at_line@@Base+0x1c57>
    37ff:	81 0d 97 bc 00 00 00 	or     DWORD PTR [rip+0xbc97],0x200000        # f4a0 <error_print_progname@@Base+0x3b8>
    3806:	00 20 00 
    3809:	e9 a9 f3 ff ff       	jmp    2bb7 <error_at_line@@Base+0x1c4e>
    380e:	81 0d 88 bc 00 00 00 	or     DWORD PTR [rip+0xbc88],0x80000000        # f4a0 <error_print_progname@@Base+0x3b8>
    3815:	00 00 80 
    3818:	e9 8e f3 ff ff       	jmp    2bab <error_at_line@@Base+0x1c42>
    381d:	81 0d 7d bc 00 00 00 	or     DWORD PTR [rip+0xbc7d],0x2000        # f4a4 <error_print_progname@@Base+0x3bc>
    3824:	20 00 00 
    3827:	e9 73 f3 ff ff       	jmp    2b9f <error_at_line@@Base+0x1c36>
    382c:	81 0d 6e bc 00 00 00 	or     DWORD PTR [rip+0xbc6e],0x100        # f4a4 <error_print_progname@@Base+0x3bc>
    3833:	01 00 00 
    3836:	e9 58 f3 ff ff       	jmp    2b93 <error_at_line@@Base+0x1c2a>
    383b:	81 0d 5f bc 00 00 00 	or     DWORD PTR [rip+0xbc5f],0x800        # f4a4 <error_print_progname@@Base+0x3bc>
    3842:	08 00 00 
    3845:	e9 40 f3 ff ff       	jmp    2b8a <error_at_line@@Base+0x1c21>
    384a:	81 0d 50 bc 00 00 00 	or     DWORD PTR [rip+0xbc50],0x8000        # f4a4 <error_print_progname@@Base+0x3bc>
    3851:	80 00 00 
    3854:	e9 27 f3 ff ff       	jmp    2b80 <error_at_line@@Base+0x1c17>
    3859:	81 0d 3d bc 00 00 00 	or     DWORD PTR [rip+0xbc3d],0x400        # f4a0 <error_print_progname@@Base+0x3b8>
    3860:	04 00 00 
    3863:	e9 0e f3 ff ff       	jmp    2b76 <error_at_line@@Base+0x1c0d>
    3868:	81 0d 2e bc 00 00 00 	or     DWORD PTR [rip+0xbc2e],0x10000        # f4a0 <error_print_progname@@Base+0x3b8>
    386f:	00 01 00 
    3872:	e9 f2 f2 ff ff       	jmp    2b69 <error_at_line@@Base+0x1c00>
    3877:	81 0d 1f bc 00 00 00 	or     DWORD PTR [rip+0xbc1f],0x8000000        # f4a0 <error_print_progname@@Base+0x3b8>
    387e:	00 00 08 
    3881:	e9 d6 f2 ff ff       	jmp    2b5c <error_at_line@@Base+0x1bf3>
    3886:	81 0d 10 bc 00 00 00 	or     DWORD PTR [rip+0xbc10],0x10000000        # f4a0 <error_print_progname@@Base+0x3b8>
    388d:	00 00 10 
    3890:	e9 ba f2 ff ff       	jmp    2b4f <error_at_line@@Base+0x1be6>
    3895:	83 0d 04 bc 00 00 01 	or     DWORD PTR [rip+0xbc04],0x1        # f4a0 <error_print_progname@@Base+0x3b8>
    389c:	e9 a1 f2 ff ff       	jmp    2b42 <error_at_line@@Base+0x1bd9>
    38a1:	83 0d f8 bb 00 00 40 	or     DWORD PTR [rip+0xbbf8],0x40        # f4a0 <error_print_progname@@Base+0x3b8>
    38a8:	e9 de f5 ff ff       	jmp    2e8b <error_at_line@@Base+0x1f22>
    38ad:	83 0d f0 bb 00 00 08 	or     DWORD PTR [rip+0xbbf0],0x8        # f4a4 <error_print_progname@@Base+0x3bc>
    38b4:	e9 24 f5 ff ff       	jmp    2ddd <error_at_line@@Base+0x1e74>
    38b9:	8b 74 24 fc          	mov    esi,DWORD PTR [rsp-0x4]
    38bd:	8b 44 24 f8          	mov    eax,DWORD PTR [rsp-0x8]
    38c1:	8d 56 0f             	lea    edx,[rsi+0xf]
    38c4:	44 09 e8             	or     eax,r13d
    38c7:	83 fe 03             	cmp    esi,0x3
    38ca:	75 6c                	jne    3938 <error_at_line@@Base+0x29cf>
    38cc:	83 e0 fd             	and    eax,0xfffffffd
    38cf:	83 f8 01             	cmp    eax,0x1
    38d2:	0f 85 e6 f6 ff ff    	jne    2fbe <error_at_line@@Base+0x2055>
    38d8:	48 ba 03 00 00 00 27 	movabs rdx,0x2700000003
    38df:	00 00 00 
    38e2:	48 89 15 cb bb 00 00 	mov    QWORD PTR [rip+0xbbcb],rdx        # f4b4 <error_print_progname@@Base+0x3cc>
    38e9:	e9 2b f6 ff ff       	jmp    2f19 <error_at_line@@Base+0x1fb0>
    38ee:	81 0d b0 bb 00 00 00 	or     DWORD PTR [rip+0xbbb0],0x2000000        # f4a8 <error_print_progname@@Base+0x3c0>
    38f5:	00 00 02 
    38f8:	e9 02 f4 ff ff       	jmp    2cff <error_at_line@@Base+0x1d96>
    38fd:	c7 05 ad bb 00 00 10 	mov    DWORD PTR [rip+0xbbad],0x10        # f4b4 <error_print_progname@@Base+0x3cc>
    3904:	00 00 00 
    3907:	8b 44 24 f8          	mov    eax,DWORD PTR [rsp-0x8]
    390b:	44 09 e8             	or     eax,r13d
    390e:	83 f8 3b             	cmp    eax,0x3b
    3911:	0f 84 24 02 00 00    	je     3b3b <error_at_line@@Base+0x2bd2>
    3917:	83 f8 5b             	cmp    eax,0x5b
    391a:	0f 84 b2 01 00 00    	je     3ad2 <error_at_line@@Base+0x2b69>
    3920:	83 f8 6a             	cmp    eax,0x6a
    3923:	0f 86 df f9 ff ff    	jbe    3308 <error_at_line@@Base+0x239f>
    3929:	c7 05 85 bb 00 00 25 	mov    DWORD PTR [rip+0xbb85],0x25        # f4b8 <error_print_progname@@Base+0x3d0>
    3930:	00 00 00 
    3933:	e9 d0 f9 ff ff       	jmp    3308 <error_at_line@@Base+0x239f>
    3938:	83 fa 13             	cmp    edx,0x13
    393b:	0f 85 7d f6 ff ff    	jne    2fbe <error_at_line@@Base+0x2055>
    3941:	83 e8 01             	sub    eax,0x1
    3944:	0f 85 74 f6 ff ff    	jne    2fbe <error_at_line@@Base+0x2055>
    394a:	48 b8 03 00 00 00 26 	movabs rax,0x2600000003
    3951:	00 00 00 
    3954:	48 89 05 59 bb 00 00 	mov    QWORD PTR [rip+0xbb59],rax        # f4b4 <error_print_progname@@Base+0x3cc>
    395b:	e9 5e f6 ff ff       	jmp    2fbe <error_at_line@@Base+0x2055>
    3960:	81 0d 3e bb 00 00 00 	or     DWORD PTR [rip+0xbb3e],0x1000        # f4a8 <error_print_progname@@Base+0x3c0>
    3967:	10 00 00 
    396a:	e9 ca f3 ff ff       	jmp    2d39 <error_at_line@@Base+0x1dd0>
    396f:	81 0d 2f bb 00 00 00 	or     DWORD PTR [rip+0xbb2f],0x800        # f4a8 <error_print_progname@@Base+0x3c0>
    3976:	08 00 00 
    3979:	e9 b3 f3 ff ff       	jmp    2d31 <error_at_line@@Base+0x1dc8>
    397e:	83 0d 23 bb 00 00 20 	or     DWORD PTR [rip+0xbb23],0x20        # f4a8 <error_print_progname@@Base+0x3c0>
    3985:	e9 9e f3 ff ff       	jmp    2d28 <error_at_line@@Base+0x1dbf>
    398a:	83 0d 17 bb 00 00 10 	or     DWORD PTR [rip+0xbb17],0x10        # f4a8 <error_print_progname@@Base+0x3c0>
    3991:	e9 89 f3 ff ff       	jmp    2d1f <error_at_line@@Base+0x1db6>
    3996:	83 0d 0b bb 00 00 08 	or     DWORD PTR [rip+0xbb0b],0x8        # f4a8 <error_print_progname@@Base+0x3c0>
    399d:	e9 74 f3 ff ff       	jmp    2d16 <error_at_line@@Base+0x1dad>
    39a2:	81 0d f8 ba 00 00 00 	or     DWORD PTR [rip+0xbaf8],0x20000000        # f4a4 <error_print_progname@@Base+0x3bc>
    39a9:	00 00 20 
    39ac:	e9 5a f3 ff ff       	jmp    2d0b <error_at_line@@Base+0x1da2>
    39b1:	83 0d e8 ba 00 00 10 	or     DWORD PTR [rip+0xbae8],0x10        # f4a0 <error_print_progname@@Base+0x3b8>
    39b8:	e9 9f f3 ff ff       	jmp    2d5c <error_at_line@@Base+0x1df3>
    39bd:	81 0d e1 ba 00 00 80 	or     DWORD PTR [rip+0xbae1],0x80        # f4a8 <error_print_progname@@Base+0x3c0>
    39c4:	00 00 00 
    39c7:	e9 ab f3 ff ff       	jmp    2d77 <error_at_line@@Base+0x1e0e>
    39cc:	81 0d d2 ba 00 00 00 	or     DWORD PTR [rip+0xbad2],0x2000        # f4a8 <error_print_progname@@Base+0x3c0>
    39d3:	20 00 00 
    39d6:	e9 66 f3 ff ff       	jmp    2d41 <error_at_line@@Base+0x1dd8>
    39db:	b8 06 00 00 00       	mov    eax,0x6
    39e0:	e9 34 f5 ff ff       	jmp    2f19 <error_at_line@@Base+0x1fb0>
    39e5:	83 f9 37             	cmp    ecx,0x37
    39e8:	0f 87 70 01 00 00    	ja     3b5e <error_at_line@@Base+0x2bf5>
    39ee:	83 f9 24             	cmp    ecx,0x24
    39f1:	0f 86 cd 01 00 00    	jbe    3bc4 <error_at_line@@Base+0x2c5b>
    39f7:	83 e9 25             	sub    ecx,0x25
    39fa:	83 f9 12             	cmp    ecx,0x12
    39fd:	0f 87 bb f5 ff ff    	ja     2fbe <error_at_line@@Base+0x2055>
    3a03:	48 8d 15 96 90 00 00 	lea    rdx,[rip+0x9096]        # caa0 <error_at_line@@Base+0xbb37>
    3a0a:	48 63 04 8a          	movsxd rax,DWORD PTR [rdx+rcx*4]
    3a0e:	48 01 d0             	add    rax,rdx
    3a11:	3e ff e0             	notrack jmp rax
    3a14:	48 b8 03 00 00 00 02 	movabs rax,0x200000003
    3a1b:	00 00 00 
    3a1e:	48 89 05 8f ba 00 00 	mov    QWORD PTR [rip+0xba8f],rax        # f4b4 <error_print_progname@@Base+0x3cc>
    3a25:	e9 94 f5 ff ff       	jmp    2fbe <error_at_line@@Base+0x2055>
    3a2a:	48 b8 03 00 00 00 03 	movabs rax,0x300000003
    3a31:	00 00 00 
    3a34:	48 89 05 79 ba 00 00 	mov    QWORD PTR [rip+0xba79],rax        # f4b4 <error_print_progname@@Base+0x3cc>
    3a3b:	e9 7e f5 ff ff       	jmp    2fbe <error_at_line@@Base+0x2055>
    3a40:	83 f9 1c             	cmp    ecx,0x1c
    3a43:	0f 85 75 f5 ff ff    	jne    2fbe <error_at_line@@Base+0x2055>
    3a49:	c7 05 61 ba 00 00 01 	mov    DWORD PTR [rip+0xba61],0x1        # f4b4 <error_print_progname@@Base+0x3cc>
    3a50:	00 00 00 
    3a53:	e9 66 f5 ff ff       	jmp    2fbe <error_at_line@@Base+0x2055>
    3a58:	48 b8 03 00 00 00 01 	movabs rax,0x100000003
    3a5f:	00 00 00 
    3a62:	48 89 05 4b ba 00 00 	mov    QWORD PTR [rip+0xba4b],rax        # f4b4 <error_print_progname@@Base+0x3cc>
    3a69:	e9 50 f5 ff ff       	jmp    2fbe <error_at_line@@Base+0x2055>
    3a6e:	c7 05 40 ba 00 00 24 	mov    DWORD PTR [rip+0xba40],0x24        # f4b8 <error_print_progname@@Base+0x3d0>
    3a75:	00 00 00 
    3a78:	e9 c3 f5 ff ff       	jmp    3040 <error_at_line@@Base+0x20d7>
    3a7d:	81 f9 cc 00 00 00    	cmp    ecx,0xcc
    3a83:	0f 84 ea 01 00 00    	je     3c73 <error_at_line@@Base+0x2d0a>
    3a89:	0f 87 be 01 00 00    	ja     3c4d <error_at_line@@Base+0x2ce4>
    3a8f:	81 e9 b7 00 00 00    	sub    ecx,0xb7
    3a95:	83 f9 0f             	cmp    ecx,0xf
    3a98:	0f 87 20 f5 ff ff    	ja     2fbe <error_at_line@@Base+0x2055>
    3a9e:	b8 01 00 00 00       	mov    eax,0x1
    3aa3:	48 d3 e0             	shl    rax,cl
    3aa6:	a9 89 01 00 00       	test   eax,0x189
    3aab:	0f 85 03 fa ff ff    	jne    34b4 <error_at_line@@Base+0x254b>
    3ab1:	a9 40 80 00 00       	test   eax,0x8040
    3ab6:	0f 84 fc fa ff ff    	je     35b8 <error_at_line@@Base+0x264f>
    3abc:	48 b8 03 00 00 00 21 	movabs rax,0x2100000003
    3ac3:	00 00 00 
    3ac6:	48 89 05 e7 b9 00 00 	mov    QWORD PTR [rip+0xb9e7],rax        # f4b4 <error_print_progname@@Base+0x3cc>
    3acd:	e9 ec f4 ff ff       	jmp    2fbe <error_at_line@@Base+0x2055>
    3ad2:	c7 05 dc b9 00 00 23 	mov    DWORD PTR [rip+0xb9dc],0x23        # f4b8 <error_print_progname@@Base+0x3d0>
    3ad9:	00 00 00 
    3adc:	e9 27 f8 ff ff       	jmp    3308 <error_at_line@@Base+0x239f>
    3ae1:	81 0d bd b9 00 00 00 	or     DWORD PTR [rip+0xb9bd],0x8000000        # f4a8 <error_print_progname@@Base+0x3c0>
    3ae8:	00 00 08 
    3aeb:	e9 1d f6 ff ff       	jmp    310d <error_at_line@@Base+0x21a4>
    3af0:	81 0d ae b9 00 00 00 	or     DWORD PTR [rip+0xb9ae],0x4000000        # f4a8 <error_print_progname@@Base+0x3c0>
    3af7:	00 00 04 
    3afa:	e9 f3 f5 ff ff       	jmp    30f2 <error_at_line@@Base+0x2189>
    3aff:	81 0d 9f b9 00 00 00 	or     DWORD PTR [rip+0xb99f],0x1000000        # f4a8 <error_print_progname@@Base+0x3c0>
    3b06:	00 00 01 
    3b09:	e9 db f5 ff ff       	jmp    30e9 <error_at_line@@Base+0x2180>
    3b0e:	81 0d 90 b9 00 00 00 	or     DWORD PTR [rip+0xb990],0x400000        # f4a8 <error_print_progname@@Base+0x3c0>
    3b15:	00 40 00 
    3b18:	e9 c4 f5 ff ff       	jmp    30e1 <error_at_line@@Base+0x2178>
    3b1d:	81 0d 81 b9 00 00 00 	or     DWORD PTR [rip+0xb981],0x200000        # f4a8 <error_print_progname@@Base+0x3c0>
    3b24:	00 20 00 
    3b27:	e9 ad f5 ff ff       	jmp    30d9 <error_at_line@@Base+0x2170>
    3b2c:	c7 05 82 b9 00 00 08 	mov    DWORD PTR [rip+0xb982],0x8        # f4b8 <error_print_progname@@Base+0x3d0>
    3b33:	00 00 00 
    3b36:	e9 05 f5 ff ff       	jmp    3040 <error_at_line@@Base+0x20d7>
    3b3b:	81 25 77 b9 00 00 ff 	and    DWORD PTR [rip+0xb977],0xfffffdff        # f4bc <error_print_progname@@Base+0x3d4>
    3b42:	fd ff ff 
    3b45:	81 25 51 b9 00 00 ff 	and    DWORD PTR [rip+0xb951],0xfffdffff        # f4a0 <error_print_progname@@Base+0x3b8>
    3b4c:	ff fd ff 
    3b4f:	c7 05 5f b9 00 00 1c 	mov    DWORD PTR [rip+0xb95f],0x1c        # f4b8 <error_print_progname@@Base+0x3d0>
    3b56:	00 00 00 
    3b59:	e9 aa f7 ff ff       	jmp    3308 <error_at_line@@Base+0x239f>
    3b5e:	83 e9 3a             	sub    ecx,0x3a
    3b61:	83 f9 0d             	cmp    ecx,0xd
    3b64:	0f 87 54 f4 ff ff    	ja     2fbe <error_at_line@@Base+0x2055>
    3b6a:	b8 01 00 00 00       	mov    eax,0x1
    3b6f:	48 d3 e0             	shl    rax,cl
    3b72:	a9 24 18 00 00       	test   eax,0x1824
    3b77:	0f 85 39 01 00 00    	jne    3cb6 <error_at_line@@Base+0x2d4d>
    3b7d:	a9 08 20 00 00       	test   eax,0x2008
    3b82:	0f 85 a2 f9 ff ff    	jne    352a <error_at_line@@Base+0x25c1>
    3b88:	a8 11                	test   al,0x11
    3b8a:	0f 84 2e f4 ff ff    	je     2fbe <error_at_line@@Base+0x2055>
    3b90:	48 b8 03 00 00 00 0c 	movabs rax,0xc00000003
    3b97:	00 00 00 
    3b9a:	48 89 05 13 b9 00 00 	mov    QWORD PTR [rip+0xb913],rax        # f4b4 <error_print_progname@@Base+0x3cc>
    3ba1:	e9 18 f4 ff ff       	jmp    2fbe <error_at_line@@Base+0x2055>
    3ba6:	c7 05 08 b9 00 00 1d 	mov    DWORD PTR [rip+0xb908],0x1d        # f4b8 <error_print_progname@@Base+0x3d0>
    3bad:	00 00 00 
    3bb0:	e9 8b f4 ff ff       	jmp    3040 <error_at_line@@Base+0x20d7>
    3bb5:	c7 05 f9 b8 00 00 14 	mov    DWORD PTR [rip+0xb8f9],0x14        # f4b8 <error_print_progname@@Base+0x3d0>
    3bbc:	00 00 00 
    3bbf:	e9 7c f4 ff ff       	jmp    3040 <error_at_line@@Base+0x20d7>
    3bc4:	8d 41 f1             	lea    eax,[rcx-0xf]
    3bc7:	83 f8 10             	cmp    eax,0x10
    3bca:	0f 87 ee f3 ff ff    	ja     2fbe <error_at_line@@Base+0x2055>
    3bd0:	b8 01 00 00 00       	mov    eax,0x1
    3bd5:	48 d3 e0             	shl    rax,cl
    3bd8:	a9 00 00 00 c4       	test   eax,0xc4000000
    3bdd:	0f 85 75 fe ff ff    	jne    3a58 <error_at_line@@Base+0x2aef>
    3be3:	a9 00 80 80 20       	test   eax,0x20808000
    3be8:	0f 84 52 fe ff ff    	je     3a40 <error_at_line@@Base+0x2ad7>
    3bee:	c7 05 bc b8 00 00 02 	mov    DWORD PTR [rip+0xb8bc],0x2        # f4b4 <error_print_progname@@Base+0x3cc>
    3bf5:	00 00 00 
    3bf8:	e9 c1 f3 ff ff       	jmp    2fbe <error_at_line@@Base+0x2055>
    3bfd:	83 f8 2f             	cmp    eax,0x2f
    3c00:	0f 86 26 ff ff ff    	jbe    3b2c <error_at_line@@Base+0x2bc3>
    3c06:	83 f8 4f             	cmp    eax,0x4f
    3c09:	0f 86 bd 00 00 00    	jbe    3ccc <error_at_line@@Base+0x2d63>
    3c0f:	83 f8 7f             	cmp    eax,0x7f
    3c12:	0f 86 c3 00 00 00    	jbe    3cdb <error_at_line@@Base+0x2d72>
    3c18:	8b 05 9e b8 00 00    	mov    eax,DWORD PTR [rip+0xb89e]        # f4bc <error_print_progname@@Base+0x3d4>
    3c1e:	f6 c4 04             	test   ah,0x4
    3c21:	0f 85 b4 00 00 00    	jne    3cdb <error_at_line@@Base+0x2d72>
    3c27:	f6 05 78 b8 00 00 08 	test   BYTE PTR [rip+0xb878],0x8        # f4a6 <error_print_progname@@Base+0x3be>
    3c2e:	0f 85 98 00 00 00    	jne    3ccc <error_at_line@@Base+0x2d63>
    3c34:	a9 00 00 01 00       	test   eax,0x10000
    3c39:	0f 85 ed fe ff ff    	jne    3b2c <error_at_line@@Base+0x2bc3>
    3c3f:	f6 c4 20             	test   ah,0x20
    3c42:	0f 85 66 f7 ff ff    	jne    33ae <error_at_line@@Base+0x2445>
    3c48:	e9 f3 f3 ff ff       	jmp    3040 <error_at_line@@Base+0x20d7>
    3c4d:	81 f9 dd 00 00 00    	cmp    ecx,0xdd
    3c53:	74 52                	je     3ca7 <error_at_line@@Base+0x2d3e>
    3c55:	0f 87 63 f3 ff ff    	ja     2fbe <error_at_line@@Base+0x2055>
    3c5b:	81 f9 cf 00 00 00    	cmp    ecx,0xcf
    3c61:	0f 84 00 f9 ff ff    	je     3567 <error_at_line@@Base+0x25fe>
    3c67:	81 f9 d5 00 00 00    	cmp    ecx,0xd5
    3c6d:	0f 85 4b f3 ff ff    	jne    2fbe <error_at_line@@Base+0x2055>
    3c73:	48 b8 03 00 00 00 22 	movabs rax,0x2200000003
    3c7a:	00 00 00 
    3c7d:	48 89 05 30 b8 00 00 	mov    QWORD PTR [rip+0xb830],rax        # f4b4 <error_print_progname@@Base+0x3cc>
    3c84:	e9 35 f3 ff ff       	jmp    2fbe <error_at_line@@Base+0x2055>
    3c89:	c7 05 25 b8 00 00 06 	mov    DWORD PTR [rip+0xb825],0x6        # f4b8 <error_print_progname@@Base+0x3d0>
    3c90:	00 00 00 
    3c93:	e9 a8 f3 ff ff       	jmp    3040 <error_at_line@@Base+0x20d7>
    3c98:	c7 05 16 b8 00 00 05 	mov    DWORD PTR [rip+0xb816],0x5        # f4b8 <error_print_progname@@Base+0x3d0>
    3c9f:	00 00 00 
    3ca2:	e9 99 f3 ff ff       	jmp    3040 <error_at_line@@Base+0x20d7>
    3ca7:	c7 05 03 b8 00 00 13 	mov    DWORD PTR [rip+0xb803],0x13        # f4b4 <error_print_progname@@Base+0x3cc>
    3cae:	00 00 00 
    3cb1:	e9 08 f3 ff ff       	jmp    2fbe <error_at_line@@Base+0x2055>
    3cb6:	48 b8 03 00 00 00 0d 	movabs rax,0xd00000003
    3cbd:	00 00 00 
    3cc0:	48 89 05 ed b7 00 00 	mov    QWORD PTR [rip+0xb7ed],rax        # f4b4 <error_print_progname@@Base+0x3cc>
    3cc7:	e9 f2 f2 ff ff       	jmp    2fbe <error_at_line@@Base+0x2055>
    3ccc:	c7 05 e2 b7 00 00 09 	mov    DWORD PTR [rip+0xb7e2],0x9        # f4b8 <error_print_progname@@Base+0x3d0>
    3cd3:	00 00 00 
    3cd6:	e9 65 f3 ff ff       	jmp    3040 <error_at_line@@Base+0x20d7>
    3cdb:	c7 05 d3 b7 00 00 0a 	mov    DWORD PTR [rip+0xb7d3],0xa        # f4b8 <error_print_progname@@Base+0x3d0>
    3ce2:	00 00 00 
    3ce5:	e9 56 f3 ff ff       	jmp    3040 <error_at_line@@Base+0x20d7>
    3cea:	83 e0 04             	and    eax,0x4
    3ced:	83 f8 01             	cmp    eax,0x1
    3cf0:	19 c0                	sbb    eax,eax
    3cf2:	83 e0 fb             	and    eax,0xfffffffb
    3cf5:	83 c0 15             	add    eax,0x15
    3cf8:	89 05 ba b7 00 00    	mov    DWORD PTR [rip+0xb7ba],eax        # f4b8 <error_print_progname@@Base+0x3d0>
    3cfe:	e9 bb f2 ff ff       	jmp    2fbe <error_at_line@@Base+0x2055>
    3d03:	66 2e 0f 1f 84 00 00 	cs nop WORD PTR [rax+rax*1+0x0]
    3d0a:	00 00 00 
    3d0d:	0f 1f 00             	nop    DWORD PTR [rax]
    3d10:	f3 0f 1e fa          	endbr64
    3d14:	31 ed                	xor    ebp,ebp
    3d16:	49 89 d1             	mov    r9,rdx
    3d19:	5e                   	pop    rsi
    3d1a:	48 89 e2             	mov    rdx,rsp
    3d1d:	48 83 e4 f0          	and    rsp,0xfffffffffffffff0
    3d21:	50                   	push   rax
    3d22:	54                   	push   rsp
    3d23:	45 31 c0             	xor    r8d,r8d
    3d26:	31 c9                	xor    ecx,ecx
    3d28:	48 8d 3d d1 d3 ff ff 	lea    rdi,[rip+0xffffffffffffd3d1]        # 1100 <error_at_line@@Base+0x197>
    3d2f:	ff 15 4b b2 00 00    	call   QWORD PTR [rip+0xb24b]        # ef80 <error_at_line@@Base+0xe017>
    3d35:	f4                   	hlt
    3d36:	66 2e 0f 1f 84 00 00 	cs nop WORD PTR [rax+rax*1+0x0]
    3d3d:	00 00 00 
    3d40:	48 8d 3d 61 b3 00 00 	lea    rdi,[rip+0xb361]        # f0a8 <obstack_alloc_failed_handler@@Base+0x28>
    3d47:	48 8d 05 5a b3 00 00 	lea    rax,[rip+0xb35a]        # f0a8 <obstack_alloc_failed_handler@@Base+0x28>
    3d4e:	48 39 f8             	cmp    rax,rdi
    3d51:	74 15                	je     3d68 <error_at_line@@Base+0x2dff>
    3d53:	48 8b 05 2e b2 00 00 	mov    rax,QWORD PTR [rip+0xb22e]        # ef88 <error_at_line@@Base+0xe01f>
    3d5a:	48 85 c0             	test   rax,rax
    3d5d:	74 09                	je     3d68 <error_at_line@@Base+0x2dff>
    3d5f:	ff e0                	jmp    rax
    3d61:	0f 1f 80 00 00 00 00 	nop    DWORD PTR [rax+0x0]
    3d68:	c3                   	ret
    3d69:	0f 1f 80 00 00 00 00 	nop    DWORD PTR [rax+0x0]
    3d70:	48 8d 3d 31 b3 00 00 	lea    rdi,[rip+0xb331]        # f0a8 <obstack_alloc_failed_handler@@Base+0x28>
    3d77:	48 8d 35 2a b3 00 00 	lea    rsi,[rip+0xb32a]        # f0a8 <obstack_alloc_failed_handler@@Base+0x28>
    3d7e:	48 29 fe             	sub    rsi,rdi
    3d81:	48 89 f0             	mov    rax,rsi
    3d84:	48 c1 ee 3f          	shr    rsi,0x3f
    3d88:	48 c1 f8 03          	sar    rax,0x3
    3d8c:	48 01 c6             	add    rsi,rax
    3d8f:	48 d1 fe             	sar    rsi,1
    3d92:	74 14                	je     3da8 <error_at_line@@Base+0x2e3f>
    3d94:	48 8b 05 2d b2 00 00 	mov    rax,QWORD PTR [rip+0xb22d]        # efc8 <error_at_line@@Base+0xe05f>
    3d9b:	48 85 c0             	test   rax,rax
    3d9e:	74 08                	je     3da8 <error_at_line@@Base+0x2e3f>
    3da0:	ff e0                	jmp    rax
    3da2:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]
    3da8:	c3                   	ret
    3da9:	0f 1f 80 00 00 00 00 	nop    DWORD PTR [rax+0x0]
    3db0:	f3 0f 1e fa          	endbr64
    3db4:	80 3d 05 b3 00 00 00 	cmp    BYTE PTR [rip+0xb305],0x0        # f0c0 <obstack_alloc_failed_handler@@Base+0x40>
    3dbb:	75 2b                	jne    3de8 <error_at_line@@Base+0x2e7f>
    3dbd:	55                   	push   rbp
    3dbe:	48 83 3d 12 b2 00 00 	cmp    QWORD PTR [rip+0xb212],0x0        # efd8 <error_at_line@@Base+0xe06f>
    3dc5:	00 
    3dc6:	48 89 e5             	mov    rbp,rsp
    3dc9:	74 0c                	je     3dd7 <error_at_line@@Base+0x2e6e>
    3dcb:	48 8d 3d 6e ab 00 00 	lea    rdi,[rip+0xab6e]        # e940 <error_at_line@@Base+0xd9d7>
    3dd2:	e8 f9 cd ff ff       	call   bd0 <__cxa_finalize@plt>
    3dd7:	e8 64 ff ff ff       	call   3d40 <error_at_line@@Base+0x2dd7>
    3ddc:	c6 05 dd b2 00 00 01 	mov    BYTE PTR [rip+0xb2dd],0x1        # f0c0 <obstack_alloc_failed_handler@@Base+0x40>
    3de3:	5d                   	pop    rbp
    3de4:	c3                   	ret
    3de5:	0f 1f 00             	nop    DWORD PTR [rax]
    3de8:	c3                   	ret
    3de9:	0f 1f 80 00 00 00 00 	nop    DWORD PTR [rax+0x0]
    3df0:	f3 0f 1e fa          	endbr64
    3df4:	e9 77 ff ff ff       	jmp    3d70 <error_at_line@@Base+0x2e07>
    3df9:	0f 1f 80 00 00 00 00 	nop    DWORD PTR [rax+0x0]
    3e00:	55                   	push   rbp
    3e01:	48 89 e5             	mov    rbp,rsp
    3e04:	53                   	push   rbx
    3e05:	48 89 fb             	mov    rbx,rdi
    3e08:	bf 30 00 00 00       	mov    edi,0x30
    3e0d:	48 83 ec 08          	sub    rsp,0x8
    3e11:	e8 7a cc ff ff       	call   a90 <malloc@plt>
    3e16:	48 85 c0             	test   rax,rax
    3e19:	74 0f                	je     3e2a <error_at_line@@Base+0x2ec1>
    3e1b:	48 c7 00 00 00 00 00 	mov    QWORD PTR [rax],0x0
    3e22:	48 89 58 20          	mov    QWORD PTR [rax+0x20],rbx
    3e26:	48 89 58 28          	mov    QWORD PTR [rax+0x28],rbx
    3e2a:	48 83 c4 08          	add    rsp,0x8
    3e2e:	5b                   	pop    rbx
    3e2f:	5d                   	pop    rbp
    3e30:	c3                   	ret
    3e31:	0f 1f 40 00          	nop    DWORD PTR [rax+0x0]
    3e35:	66 66 2e 0f 1f 84 00 	data16 cs nop WORD PTR [rax+rax*1+0x0]
    3e3c:	00 00 00 00 
    3e40:	55                   	push   rbp
    3e41:	48 89 e5             	mov    rbp,rsp
    3e44:	53                   	push   rbx
    3e45:	48 89 fb             	mov    rbx,rdi
    3e48:	bf 30 00 00 00       	mov    edi,0x30
    3e4d:	48 83 ec 08          	sub    rsp,0x8
    3e51:	e8 3a cc ff ff       	call   a90 <malloc@plt>
    3e56:	48 85 c0             	test   rax,rax
    3e59:	74 23                	je     3e7e <error_at_line@@Base+0x2f15>
    3e5b:	48 89 18             	mov    QWORD PTR [rax],rbx
    3e5e:	48 c7 40 10 00 00 00 	mov    QWORD PTR [rax+0x10],0x0
    3e65:	00 
    3e66:	48 c7 40 18 00 00 00 	mov    QWORD PTR [rax+0x18],0x0
    3e6d:	00 
    3e6e:	48 c7 40 08 00 00 00 	mov    QWORD PTR [rax+0x8],0x0
    3e75:	00 
    3e76:	48 c7 40 20 00 00 00 	mov    QWORD PTR [rax+0x20],0x0
    3e7d:	00 
    3e7e:	48 83 c4 08          	add    rsp,0x8
    3e82:	5b                   	pop    rbx
    3e83:	5d                   	pop    rbp
    3e84:	c3                   	ret
    3e85:	66 66 2e 0f 1f 84 00 	data16 cs nop WORD PTR [rax+rax*1+0x0]
    3e8c:	00 00 00 00 
    3e90:	48 89 f8             	mov    rax,rdi
    3e93:	48 83 3f 00          	cmp    QWORD PTR [rdi],0x0
    3e97:	74 1f                	je     3eb8 <error_at_line@@Base+0x2f4f>
    3e99:	55                   	push   rbp
    3e9a:	48 89 e5             	mov    rbp,rsp
    3e9d:	48 83 ec 10          	sub    rsp,0x10
    3ea1:	48 8b 7f 10          	mov    rdi,QWORD PTR [rdi+0x10]
    3ea5:	48 89 45 f8          	mov    QWORD PTR [rbp-0x8],rax
    3ea9:	e8 22 c9 ff ff       	call   7d0 <free@plt>
    3eae:	48 8b 7d f8          	mov    rdi,QWORD PTR [rbp-0x8]
    3eb2:	c9                   	leave
    3eb3:	e9 18 c9 ff ff       	jmp    7d0 <free@plt>
    3eb8:	e9 13 c9 ff ff       	jmp    7d0 <free@plt>
    3ebd:	0f 1f 00             	nop    DWORD PTR [rax]
    3ec0:	55                   	push   rbp
    3ec1:	48 89 e5             	mov    rbp,rsp
    3ec4:	53                   	push   rbx
    3ec5:	48 89 fb             	mov    rbx,rdi
    3ec8:	48 83 ec 08          	sub    rsp,0x8
    3ecc:	48 c7 07 a0 0f 00 00 	mov    QWORD PTR [rdi],0xfa0
    3ed3:	48 8b 47 38          	mov    rax,QWORD PTR [rdi+0x38]
    3ed7:	48 c7 47 30 0f 00 00 	mov    QWORD PTR [rdi+0x30],0xf
    3ede:	00 
    3edf:	f6 47 50 01          	test   BYTE PTR [rdi+0x50],0x1
    3ee3:	74 56                	je     3f3b <error_at_line@@Base+0x2fd2>
    3ee5:	48 8b 7f 48          	mov    rdi,QWORD PTR [rdi+0x48]
    3ee9:	be a0 0f 00 00       	mov    esi,0xfa0
    3eee:	ff d0                	call   rax
    3ef0:	48 89 43 08          	mov    QWORD PTR [rbx+0x8],rax
    3ef4:	48 85 c0             	test   rax,rax
    3ef7:	74 4b                	je     3f44 <error_at_line@@Base+0x2fdb>
    3ef9:	48 8d 48 10          	lea    rcx,[rax+0x10]
    3efd:	48 f7 d9             	neg    rcx
    3f00:	83 e1 0f             	and    ecx,0xf
    3f03:	48 8d 54 08 10       	lea    rdx,[rax+rcx*1+0x10]
    3f08:	48 89 53 10          	mov    QWORD PTR [rbx+0x10],rdx
    3f0c:	48 89 53 18          	mov    QWORD PTR [rbx+0x18],rdx
    3f10:	48 89 c2             	mov    rdx,rax
    3f13:	48 f7 d2             	not    rdx
    3f16:	83 e2 0f             	and    edx,0xf
    3f19:	48 8d 94 10 91 0f 00 	lea    rdx,[rax+rdx*1+0xf91]
    3f20:	00 
    3f21:	48 89 10             	mov    QWORD PTR [rax],rdx
    3f24:	48 89 53 20          	mov    QWORD PTR [rbx+0x20],rdx
    3f28:	48 c7 40 08 00 00 00 	mov    QWORD PTR [rax+0x8],0x0
    3f2f:	00 
    3f30:	80 63 50 f9          	and    BYTE PTR [rbx+0x50],0xf9
    3f34:	48 83 c4 08          	add    rsp,0x8
    3f38:	5b                   	pop    rbx
    3f39:	5d                   	pop    rbp
    3f3a:	c3                   	ret
    3f3b:	bf a0 0f 00 00       	mov    edi,0xfa0
    3f40:	ff d0                	call   rax
    3f42:	eb ac                	jmp    3ef0 <error_at_line@@Base+0x2f87>
    3f44:	48 8d 05 35 b1 00 00 	lea    rax,[rip+0xb135]        # f080 <obstack_alloc_failed_handler@@Base>
    3f4b:	ff 10                	call   QWORD PTR [rax]
    3f4d:	0f 1f 00             	nop    DWORD PTR [rax]
    3f50:	55                   	push   rbp
    3f51:	48 89 e5             	mov    rbp,rsp
    3f54:	48 83 ec 60          	sub    rsp,0x60
    3f58:	8b 05 1a b1 00 00    	mov    eax,DWORD PTR [rip+0xb11a]        # f078 <error_at_line@@Base+0xe10f>
    3f5e:	4c 89 65 e0          	mov    QWORD PTR [rbp-0x20],r12
    3f62:	49 89 fc             	mov    r12,rdi
    3f65:	83 f8 ff             	cmp    eax,0xffffffff
    3f68:	0f 84 dc 02 00 00    	je     424a <error_at_line@@Base+0x32e1>
    3f6e:	48 89 5d d8          	mov    QWORD PTR [rbp-0x28],rbx
    3f72:	48 8b 1d 17 b0 00 00 	mov    rbx,QWORD PTR [rip+0xb017]        # ef90 <error_at_line@@Base+0xe027>
    3f79:	48 8b 3b             	mov    rdi,QWORD PTR [rbx]
    3f7c:	48 89 7d c8          	mov    QWORD PTR [rbp-0x38],rdi
    3f80:	85 c0                	test   eax,eax
    3f82:	0f 85 54 03 00 00    	jne    42dc <error_at_line@@Base+0x3373>
    3f88:	48 8d 35 bf 76 00 00 	lea    rsi,[rip+0x76bf]        # b64e <error_at_line@@Base+0xa6e5>
    3f8f:	4c 89 e7             	mov    rdi,r12
    3f92:	4c 89 6d e8          	mov    QWORD PTR [rbp-0x18],r13
    3f96:	4c 89 7d f8          	mov    QWORD PTR [rbp-0x8],r15
    3f9a:	4c 89 75 f0          	mov    QWORD PTR [rbp-0x10],r14
    3f9e:	e8 fd c9 ff ff       	call   9a0 <strspn@plt>
    3fa3:	be 2d 00 00 00       	mov    esi,0x2d
    3fa8:	4c 89 e7             	mov    rdi,r12
    3fab:	48 89 45 c0          	mov    QWORD PTR [rbp-0x40],rax
    3faf:	4d 8d 2c 04          	lea    r13,[r12+rax*1]
    3fb3:	e8 68 c9 ff ff       	call   920 <strchr@plt>
    3fb8:	49 89 c7             	mov    r15,rax
    3fbb:	48 85 c0             	test   rax,rax
    3fbe:	0f 84 7b 02 00 00    	je     423f <error_at_line@@Base+0x32d6>
    3fc4:	49 39 c5             	cmp    r13,rax
    3fc7:	0f 84 43 02 00 00    	je     4210 <error_at_line@@Base+0x32a7>
    3fcd:	0f 83 3d 02 00 00    	jae    4210 <error_at_line@@Base+0x32a7>
    3fd3:	e8 28 cc ff ff       	call   c00 <__ctype_b_loc@plt>
    3fd8:	4c 89 ea             	mov    rdx,r13
    3fdb:	31 c9                	xor    ecx,ecx
    3fdd:	48 8b 38             	mov    rdi,QWORD PTR [rax]
    3fe0:	66 2e 0f 1f 84 00 00 	cs nop WORD PTR [rax+rax*1+0x0]
    3fe7:	00 00 00 
    3fea:	66 66 2e 0f 1f 84 00 	data16 cs nop WORD PTR [rax+rax*1+0x0]
    3ff1:	00 00 00 00 
    3ff5:	66 66 2e 0f 1f 84 00 	data16 cs nop WORD PTR [rax+rax*1+0x0]
    3ffc:	00 00 00 00 
    4000:	48 0f be 02          	movsx  rax,BYTE PTR [rdx]
    4004:	48 83 c2 01          	add    rdx,0x1
    4008:	0f b6 44 47 01       	movzx  eax,BYTE PTR [rdi+rax*2+0x1]
    400d:	c0 e8 05             	shr    al,0x5
    4010:	83 e0 01             	and    eax,0x1
    4013:	48 01 c1             	add    rcx,rax
    4016:	4c 39 fa             	cmp    rdx,r15
    4019:	40 0f 92 c6          	setb   sil
    401d:	48 83 f9 02          	cmp    rcx,0x2
    4021:	0f 95 c0             	setne  al
    4024:	40 84 c6             	test   sil,al
    4027:	75 d7                	jne    4000 <error_at_line@@Base+0x3097>
    4029:	48 83 f9 02          	cmp    rcx,0x2
    402d:	41 89 c0             	mov    r8d,eax
    4030:	4d 0f 44 fd          	cmove  r15,r13
    4034:	48 8d 35 17 76 00 00 	lea    rsi,[rip+0x7617]        # b652 <error_at_line@@Base+0xa6e9>
    403b:	4c 89 ff             	mov    rdi,r15
    403e:	44 88 45 b7          	mov    BYTE PTR [rbp-0x49],r8b
    4042:	e8 79 c9 ff ff       	call   9c0 <strcspn@plt>
    4047:	4d 8d 34 07          	lea    r14,[r15+rax*1]
    404b:	48 89 45 b8          	mov    QWORD PTR [rbp-0x48],rax
    404f:	41 0f b6 16          	movzx  edx,BYTE PTR [r14]
    4053:	84 d2                	test   dl,dl
    4055:	0f 84 a5 00 00 00    	je     4100 <error_at_line@@Base+0x3197>
    405b:	80 fa 0a             	cmp    dl,0xa
    405e:	0f 84 9c 00 00 00    	je     4100 <error_at_line@@Base+0x3197>
    4064:	49 8d 4e 01          	lea    rcx,[r14+0x1]
    4068:	88 55 b6             	mov    BYTE PTR [rbp-0x4a],dl
    406b:	48 89 4d a8          	mov    QWORD PTR [rbp-0x58],rcx
    406f:	e8 8c cb ff ff       	call   c00 <__ctype_b_loc@plt>
    4074:	44 0f b6 45 b7       	movzx  r8d,BYTE PTR [rbp-0x49]
    4079:	0f b6 55 b6          	movzx  edx,BYTE PTR [rbp-0x4a]
    407d:	48 8b 30             	mov    rsi,QWORD PTR [rax]
    4080:	48 8b 4d a8          	mov    rcx,QWORD PTR [rbp-0x58]
    4084:	eb 26                	jmp    40ac <error_at_line@@Base+0x3143>
    4086:	66 2e 0f 1f 84 00 00 	cs nop WORD PTR [rax+rax*1+0x0]
    408d:	00 00 00 
    4090:	f6 c4 20             	test   ah,0x20
    4093:	0f 85 87 01 00 00    	jne    4220 <error_at_line@@Base+0x32b7>
    4099:	0f b6 11             	movzx  edx,BYTE PTR [rcx]
    409c:	49 89 ce             	mov    r14,rcx
    409f:	48 83 c1 01          	add    rcx,0x1
    40a3:	84 d2                	test   dl,dl
    40a5:	74 59                	je     4100 <error_at_line@@Base+0x3197>
    40a7:	80 fa 0a             	cmp    dl,0xa
    40aa:	74 54                	je     4100 <error_at_line@@Base+0x3197>
    40ac:	48 0f be c2          	movsx  rax,dl
    40b0:	48 8d 79 ff          	lea    rdi,[rcx-0x1]
    40b4:	0f b7 04 46          	movzx  eax,WORD PTR [rsi+rax*2]
    40b8:	80 fa 2d             	cmp    dl,0x2d
    40bb:	75 d3                	jne    4090 <error_at_line@@Base+0x3127>
    40bd:	0f b6 11             	movzx  edx,BYTE PTR [rcx]
    40c0:	49 89 ce             	mov    r14,rcx
    40c3:	80 fa 2d             	cmp    dl,0x2d
    40c6:	41 0f 95 c1          	setne  r9b
    40ca:	45 21 c8             	and    r8d,r9d
    40cd:	f6 c4 20             	test   ah,0x20
    40d0:	74 cd                	je     409f <error_at_line@@Base+0x3136>
    40d2:	48 0f be c2          	movsx  rax,dl
    40d6:	f6 44 46 01 20       	test   BYTE PTR [rsi+rax*2+0x1],0x20
    40db:	0f 85 56 01 00 00    	jne    4237 <error_at_line@@Base+0x32ce>
    40e1:	45 84 c0             	test   r8b,r8b
    40e4:	75 09                	jne    40ef <error_at_line@@Base+0x3186>
    40e6:	80 fa 2d             	cmp    dl,0x2d
    40e9:	0f 85 48 01 00 00    	jne    4237 <error_at_line@@Base+0x32ce>
    40ef:	49 89 ce             	mov    r14,rcx
    40f2:	48 83 c1 01          	add    rcx,0x1
    40f6:	84 d2                	test   dl,dl
    40f8:	75 ad                	jne    40a7 <error_at_line@@Base+0x313e>
    40fa:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]
    4100:	48 8b 55 c0          	mov    rdx,QWORD PTR [rbp-0x40]
    4104:	48 8b 4d c8          	mov    rcx,QWORD PTR [rbp-0x38]
    4108:	be 01 00 00 00       	mov    esi,0x1
    410d:	4c 89 e7             	mov    rdi,r12
    4110:	e8 8b c9 ff ff       	call   aa0 <fwrite_unlocked@plt>
    4115:	ba 06 00 00 00       	mov    edx,0x6
    411a:	48 8d 35 37 75 00 00 	lea    rsi,[rip+0x7537]        # b658 <error_at_line@@Base+0xa6ef>
    4121:	4c 89 ff             	mov    rdi,r15
    4124:	e8 e7 c6 ff ff       	call   810 <strncmp@plt>
    4129:	85 c0                	test   eax,eax
    412b:	74 1c                	je     4149 <error_at_line@@Base+0x31e0>
    412d:	ba 09 00 00 00       	mov    edx,0x9
    4132:	48 8d 35 26 75 00 00 	lea    rsi,[rip+0x7526]        # b65f <error_at_line@@Base+0xa6f6>
    4139:	4c 89 ff             	mov    rdi,r15
    413c:	e8 cf c6 ff ff       	call   810 <strncmp@plt>
    4141:	85 c0                	test   eax,eax
    4143:	0f 85 66 01 00 00    	jne    42af <error_at_line@@Base+0x3346>
    4149:	50                   	push   rax
    414a:	4c 8d 05 18 75 00 00 	lea    r8,[rip+0x7518]        # b669 <error_at_line@@Base+0xa700>
    4151:	31 c0                	xor    eax,eax
    4153:	44 8b 4d b8          	mov    r9d,DWORD PTR [rbp-0x48]
    4157:	41 57                	push   r15
    4159:	4c 89 c1             	mov    rcx,r8
    415c:	48 8d 15 15 79 00 00 	lea    rdx,[rip+0x7915]        # ba78 <error_at_line@@Base+0xab0f>
    4163:	48 8d 35 02 75 00 00 	lea    rsi,[rip+0x7502]        # b66c <error_at_line@@Base+0xa703>
    416a:	bf 02 00 00 00       	mov    edi,0x2
    416f:	e8 5c c9 ff ff       	call   ad0 <__printf_chk@plt>
    4174:	5a                   	pop    rdx
    4175:	59                   	pop    rcx
    4176:	48 8b 0b             	mov    rcx,QWORD PTR [rbx]
    4179:	ba 02 00 00 00       	mov    edx,0x2
    417e:	be 01 00 00 00       	mov    esi,0x1
    4183:	48 8d 3d 11 75 00 00 	lea    rdi,[rip+0x7511]        # b69b <error_at_line@@Base+0xa732>
    418a:	e8 11 c9 ff ff       	call   aa0 <fwrite_unlocked@plt>
    418f:	48 8b 0b             	mov    rcx,QWORD PTR [rbx]
    4192:	ba 04 00 00 00       	mov    edx,0x4
    4197:	be 01 00 00 00       	mov    esi,0x1
    419c:	48 8d 3d e9 74 00 00 	lea    rdi,[rip+0x74e9]        # b68c <error_at_line@@Base+0xa723>
    41a3:	e8 f8 c8 ff ff       	call   aa0 <fwrite_unlocked@plt>
    41a8:	48 8b 0b             	mov    rcx,QWORD PTR [rbx]
    41ab:	4c 89 f2             	mov    rdx,r14
    41ae:	4c 89 ef             	mov    rdi,r13
    41b1:	4c 29 ea             	sub    rdx,r13
    41b4:	be 01 00 00 00       	mov    esi,0x1
    41b9:	e8 e2 c8 ff ff       	call   aa0 <fwrite_unlocked@plt>
    41be:	48 8b 0b             	mov    rcx,QWORD PTR [rbx]
    41c1:	ba 04 00 00 00       	mov    edx,0x4
    41c6:	be 01 00 00 00       	mov    esi,0x1
    41cb:	48 8d 3d bf 74 00 00 	lea    rdi,[rip+0x74bf]        # b691 <error_at_line@@Base+0xa728>
    41d2:	e8 c9 c8 ff ff       	call   aa0 <fwrite_unlocked@plt>
    41d7:	48 8b 0b             	mov    rcx,QWORD PTR [rbx]
    41da:	be 01 00 00 00       	mov    esi,0x1
    41df:	48 8d 3d b0 74 00 00 	lea    rdi,[rip+0x74b0]        # b696 <error_at_line@@Base+0xa72d>
    41e6:	ba 07 00 00 00       	mov    edx,0x7
    41eb:	e8 b0 c8 ff ff       	call   aa0 <fwrite_unlocked@plt>
    41f0:	48 8b 33             	mov    rsi,QWORD PTR [rbx]
    41f3:	4c 8b 6d e8          	mov    r13,QWORD PTR [rbp-0x18]
    41f7:	4c 89 f7             	mov    rdi,r14
    41fa:	48 8b 5d d8          	mov    rbx,QWORD PTR [rbp-0x28]
    41fe:	4c 8b 75 f0          	mov    r14,QWORD PTR [rbp-0x10]
    4202:	4c 8b 7d f8          	mov    r15,QWORD PTR [rbp-0x8]
    4206:	4c 8b 65 e0          	mov    r12,QWORD PTR [rbp-0x20]
    420a:	c9                   	leave
    420b:	e9 e0 c7 ff ff       	jmp    9f0 <fputs_unlocked@plt>
    4210:	41 b8 01 00 00 00    	mov    r8d,0x1
    4216:	e9 19 fe ff ff       	jmp    4034 <error_at_line@@Base+0x30cb>
    421b:	0f 1f 44 00 00       	nop    DWORD PTR [rax+rax*1+0x0]
    4220:	80 fa 09             	cmp    dl,0x9
    4223:	74 12                	je     4237 <error_at_line@@Base+0x32ce>
    4225:	0f b6 11             	movzx  edx,BYTE PTR [rcx]
    4228:	48 0f be c2          	movsx  rax,dl
    422c:	f6 44 46 01 20       	test   BYTE PTR [rsi+rax*2+0x1],0x20
    4231:	0f 84 aa fe ff ff    	je     40e1 <error_at_line@@Base+0x3178>
    4237:	49 89 fe             	mov    r14,rdi
    423a:	e9 c1 fe ff ff       	jmp    4100 <error_at_line@@Base+0x3197>
    423f:	4d 89 ef             	mov    r15,r13
    4242:	45 31 c0             	xor    r8d,r8d
    4245:	e9 ea fd ff ff       	jmp    4034 <error_at_line@@Base+0x30cb>
    424a:	48 8d 3d f3 73 00 00 	lea    rdi,[rip+0x73f3]        # b644 <error_at_line@@Base+0xa6db>
    4251:	e8 6a c5 ff ff       	call   7c0 <getenv@plt>
    4256:	48 85 c0             	test   rax,rax
    4259:	74 2b                	je     4286 <error_at_line@@Base+0x331d>
    425b:	80 38 00             	cmp    BYTE PTR [rax],0x0
    425e:	74 26                	je     4286 <error_at_line@@Base+0x331d>
    4260:	48 8d 35 e2 73 00 00 	lea    rsi,[rip+0x73e2]        # b649 <error_at_line@@Base+0xa6e0>
    4267:	48 89 c7             	mov    rdi,rax
    426a:	48 89 5d d8          	mov    QWORD PTR [rbp-0x28],rbx
    426e:	e8 9d c7 ff ff       	call   a10 <strcmp@plt>
    4273:	85 c0                	test   eax,eax
    4275:	0f 94 c0             	sete   al
    4278:	0f b6 c0             	movzx  eax,al
    427b:	89 05 f7 ad 00 00    	mov    DWORD PTR [rip+0xadf7],eax        # f078 <error_at_line@@Base+0xe10f>
    4281:	e9 ec fc ff ff       	jmp    3f72 <error_at_line@@Base+0x3009>
    4286:	48 8b 05 03 ad 00 00 	mov    rax,QWORD PTR [rip+0xad03]        # ef90 <error_at_line@@Base+0xe027>
    428d:	c7 05 e1 ad 00 00 01 	mov    DWORD PTR [rip+0xade1],0x1        # f078 <error_at_line@@Base+0xe10f>
    4294:	00 00 00 
    4297:	48 8b 00             	mov    rax,QWORD PTR [rax]
    429a:	48 89 45 c8          	mov    QWORD PTR [rbp-0x38],rax
    429e:	48 8b 75 c8          	mov    rsi,QWORD PTR [rbp-0x38]
    42a2:	4c 89 e7             	mov    rdi,r12
    42a5:	4c 8b 65 e0          	mov    r12,QWORD PTR [rbp-0x20]
    42a9:	c9                   	leave
    42aa:	e9 41 c7 ff ff       	jmp    9f0 <fputs_unlocked@plt>
    42af:	44 8b 45 b8          	mov    r8d,DWORD PTR [rbp-0x48]
    42b3:	4d 89 f9             	mov    r9,r15
    42b6:	48 8d 0d ac 73 00 00 	lea    rcx,[rip+0x73ac]        # b669 <error_at_line@@Base+0xa700>
    42bd:	31 c0                	xor    eax,eax
    42bf:	48 8d 15 da 77 00 00 	lea    rdx,[rip+0x77da]        # baa0 <error_at_line@@Base+0xab37>
    42c6:	48 8d 35 b0 73 00 00 	lea    rsi,[rip+0x73b0]        # b67d <error_at_line@@Base+0xa714>
    42cd:	bf 02 00 00 00       	mov    edi,0x2
    42d2:	e8 f9 c7 ff ff       	call   ad0 <__printf_chk@plt>
    42d7:	e9 9a fe ff ff       	jmp    4176 <error_at_line@@Base+0x320d>
    42dc:	48 8b 5d d8          	mov    rbx,QWORD PTR [rbp-0x28]
    42e0:	eb bc                	jmp    429e <error_at_line@@Base+0x3335>
    42e2:	0f 1f 00             	nop    DWORD PTR [rax]
    42e5:	66 66 2e 0f 1f 84 00 	data16 cs nop WORD PTR [rax+rax*1+0x0]
    42ec:	00 00 00 00 
    42f0:	f3 0f 1e fa          	endbr64
    42f4:	55                   	push   rbp
    42f5:	ba 05 00 00 00       	mov    edx,0x5
    42fa:	48 8d 35 9d 73 00 00 	lea    rsi,[rip+0x739d]        # b69e <error_at_line@@Base+0xa735>
    4301:	48 8d 3d a7 73 00 00 	lea    rdi,[rip+0x73a7]        # b6af <error_at_line@@Base+0xa746>
    4308:	48 89 e5             	mov    rbp,rsp
    430b:	e8 b0 c5 ff ff       	call   8c0 <dcgettext@plt>
    4310:	48 8b 15 c9 ac 00 00 	mov    rdx,QWORD PTR [rip+0xacc9]        # efe0 <error_at_line@@Base+0xe077>
    4317:	be 02 00 00 00       	mov    esi,0x2
    431c:	48 89 c1             	mov    rcx,rax
    431f:	31 c0                	xor    eax,eax
    4321:	48 8b 3a             	mov    rdi,QWORD PTR [rdx]
    4324:	48 8d 15 7a 74 00 00 	lea    rdx,[rip+0x747a]        # b7a5 <error_at_line@@Base+0xa83c>
    432b:	e8 50 c8 ff ff       	call   b80 <__fprintf_chk@plt>
    4330:	8b 3d ee ac 00 00    	mov    edi,DWORD PTR [rip+0xacee]        # f024 <error_at_line@@Base+0xe0bb>
    4336:	e8 35 c8 ff ff       	call   b70 <exit@plt>
    433b:	0f 1f 44 00 00       	nop    DWORD PTR [rax+rax*1+0x0]
    4340:	55                   	push   rbp
    4341:	48 89 e5             	mov    rbp,rsp
    4344:	41 57                	push   r15
    4346:	41 56                	push   r14
    4348:	41 55                	push   r13
    434a:	41 54                	push   r12
    434c:	53                   	push   rbx
    434d:	48 81 ec d8 00 00 00 	sub    rsp,0xd8
    4354:	4c 8b 25 3d b1 00 00 	mov    r12,QWORD PTR [rip+0xb13d]        # f498 <error_print_progname@@Base+0x3b0>
    435b:	64 48 8b 1c 25 28 00 	mov    rbx,QWORD PTR fs:0x28
    4362:	00 00 
    4364:	48 89 5d c8          	mov    QWORD PTR [rbp-0x38],rbx
    4368:	89 fb                	mov    ebx,edi
    436a:	85 ff                	test   edi,edi
    436c:	74 36                	je     43a4 <error_at_line@@Base+0x343b>
    436e:	ba 05 00 00 00       	mov    edx,0x5
    4373:	48 8d 35 6e 77 00 00 	lea    rsi,[rip+0x776e]        # bae8 <error_at_line@@Base+0xab7f>
    437a:	31 ff                	xor    edi,edi
    437c:	e8 3f c5 ff ff       	call   8c0 <dcgettext@plt>
    4381:	4c 89 e1             	mov    rcx,r12
    4384:	be 02 00 00 00       	mov    esi,0x2
    4389:	48 89 c2             	mov    rdx,rax
    438c:	48 8b 05 4d ac 00 00 	mov    rax,QWORD PTR [rip+0xac4d]        # efe0 <error_at_line@@Base+0xe077>
    4393:	48 8b 38             	mov    rdi,QWORD PTR [rax]
    4396:	31 c0                	xor    eax,eax
    4398:	e8 e3 c7 ff ff       	call   b80 <__fprintf_chk@plt>
    439d:	89 df                	mov    edi,ebx
    439f:	e8 cc c7 ff ff       	call   b70 <exit@plt>
    43a4:	48 8d 05 0d 73 00 00 	lea    rax,[rip+0x730d]        # b6b8 <error_at_line@@Base+0xa74f>
    43ab:	31 ff                	xor    edi,edi
    43ad:	f3 0f 7e 2d 33 a7 00 	movq   xmm5,QWORD PTR [rip+0xa733]        # eae8 <error_at_line@@Base+0xdb7f>
    43b4:	00 
    43b5:	f3 0f 7e 25 33 a7 00 	movq   xmm4,QWORD PTR [rip+0xa733]        # eaf0 <error_at_line@@Base+0xdb87>
    43bc:	00 
    43bd:	66 48 0f 6e f0       	movq   xmm6,rax
    43c2:	48 8d 05 15 73 00 00 	lea    rax,[rip+0x7315]        # b6de <error_at_line@@Base+0xa775>
    43c9:	f3 0f 7e 1d 27 a7 00 	movq   xmm3,QWORD PTR [rip+0xa727]        # eaf8 <error_at_line@@Base+0xdb8f>
    43d0:	00 
    43d1:	f3 0f 7e 15 27 a7 00 	movq   xmm2,QWORD PTR [rip+0xa727]        # eb00 <error_at_line@@Base+0xdb97>
    43d8:	00 
    43d9:	66 48 0f 6e c0       	movq   xmm0,rax
    43de:	66 0f 6c ee          	punpcklqdq xmm5,xmm6
    43e2:	f3 0f 7e 0d 1e a7 00 	movq   xmm1,QWORD PTR [rip+0xa71e]        # eb08 <error_at_line@@Base+0xdb9f>
    43e9:	00 
    43ea:	ba 05 00 00 00       	mov    edx,0x5
    43ef:	66 0f 6c e0          	punpcklqdq xmm4,xmm0
    43f3:	66 0f 6c d8          	punpcklqdq xmm3,xmm0
    43f7:	66 0f 6c d0          	punpcklqdq xmm2,xmm0
    43fb:	0f 29 ad 00 ff ff ff 	movaps XMMWORD PTR [rbp-0x100],xmm5
    4402:	66 0f 6c c8          	punpcklqdq xmm1,xmm0
    4406:	48 8d 35 03 77 00 00 	lea    rsi,[rip+0x7703]        # bb10 <error_at_line@@Base+0xaba7>
    440d:	0f 29 a5 10 ff ff ff 	movaps XMMWORD PTR [rbp-0xf0],xmm4
    4414:	0f 29 9d 20 ff ff ff 	movaps XMMWORD PTR [rbp-0xe0],xmm3
    441b:	0f 29 95 30 ff ff ff 	movaps XMMWORD PTR [rbp-0xd0],xmm2
    4422:	0f 29 8d 40 ff ff ff 	movaps XMMWORD PTR [rbp-0xc0],xmm1
    4429:	e8 92 c4 ff ff       	call   8c0 <dcgettext@plt>
    442e:	4c 89 e1             	mov    rcx,r12
    4431:	4c 89 e2             	mov    rdx,r12
    4434:	bf 02 00 00 00       	mov    edi,0x2
    4439:	48 89 c6             	mov    rsi,rax
    443c:	31 c0                	xor    eax,eax
    443e:	e8 8d c6 ff ff       	call   ad0 <__printf_chk@plt>
    4443:	4c 8b 25 46 ab 00 00 	mov    r12,QWORD PTR [rip+0xab46]        # ef90 <error_at_line@@Base+0xe027>
    444a:	31 ff                	xor    edi,edi
    444c:	ba 05 00 00 00       	mov    edx,0x5
    4451:	48 8d 35 00 77 00 00 	lea    rsi,[rip+0x7700]        # bb58 <error_at_line@@Base+0xabef>
    4458:	4d 8b 2c 24          	mov    r13,QWORD PTR [r12]
    445c:	e8 5f c4 ff ff       	call   8c0 <dcgettext@plt>
    4461:	48 89 c7             	mov    rdi,rax
    4464:	4c 89 ee             	mov    rsi,r13
    4467:	e8 84 c5 ff ff       	call   9f0 <fputs_unlocked@plt>
    446c:	4d 8b 2c 24          	mov    r13,QWORD PTR [r12]
    4470:	ba 05 00 00 00       	mov    edx,0x5
    4475:	31 ff                	xor    edi,edi
    4477:	48 8d 35 ba 77 00 00 	lea    rsi,[rip+0x77ba]        # bc38 <error_at_line@@Base+0xaccf>
    447e:	e8 3d c4 ff ff       	call   8c0 <dcgettext@plt>
    4483:	4c 89 ee             	mov    rsi,r13
    4486:	48 89 c7             	mov    rdi,rax
    4489:	e8 62 c5 ff ff       	call   9f0 <fputs_unlocked@plt>
    448e:	ba 05 00 00 00       	mov    edx,0x5
    4493:	31 ff                	xor    edi,edi
    4495:	4d 8b 2c 24          	mov    r13,QWORD PTR [r12]
    4499:	48 8d 35 d0 77 00 00 	lea    rsi,[rip+0x77d0]        # bc70 <error_at_line@@Base+0xad07>
    44a0:	e8 1b c4 ff ff       	call   8c0 <dcgettext@plt>
    44a5:	4c 89 ee             	mov    rsi,r13
    44a8:	48 89 c7             	mov    rdi,rax
    44ab:	e8 40 c5 ff ff       	call   9f0 <fputs_unlocked@plt>
    44b0:	ba 05 00 00 00       	mov    edx,0x5
    44b5:	48 8d 35 4c 78 00 00 	lea    rsi,[rip+0x784c]        # bd08 <error_at_line@@Base+0xad9f>
    44bc:	31 ff                	xor    edi,edi
    44be:	e8 fd c3 ff ff       	call   8c0 <dcgettext@plt>
    44c3:	48 89 c7             	mov    rdi,rax
    44c6:	e8 85 fa ff ff       	call   3f50 <error_at_line@@Base+0x2fe7>
    44cb:	ba 05 00 00 00       	mov    edx,0x5
    44d0:	48 8d 35 61 78 00 00 	lea    rsi,[rip+0x7861]        # bd38 <error_at_line@@Base+0xadcf>
    44d7:	31 ff                	xor    edi,edi
    44d9:	e8 e2 c3 ff ff       	call   8c0 <dcgettext@plt>
    44de:	48 89 c7             	mov    rdi,rax
    44e1:	e8 6a fa ff ff       	call   3f50 <error_at_line@@Base+0x2fe7>
    44e6:	ba 05 00 00 00       	mov    edx,0x5
    44eb:	48 8d 35 7e 78 00 00 	lea    rsi,[rip+0x787e]        # bd70 <error_at_line@@Base+0xae07>
    44f2:	31 ff                	xor    edi,edi
    44f4:	e8 c7 c3 ff ff       	call   8c0 <dcgettext@plt>
    44f9:	48 89 c7             	mov    rdi,rax
    44fc:	e8 4f fa ff ff       	call   3f50 <error_at_line@@Base+0x2fe7>
    4501:	ba 05 00 00 00       	mov    edx,0x5
    4506:	48 8d 35 9b 78 00 00 	lea    rsi,[rip+0x789b]        # bda8 <error_at_line@@Base+0xae3f>
    450d:	31 ff                	xor    edi,edi
    450f:	e8 ac c3 ff ff       	call   8c0 <dcgettext@plt>
    4514:	48 89 c7             	mov    rdi,rax
    4517:	e8 34 fa ff ff       	call   3f50 <error_at_line@@Base+0x2fe7>
    451c:	ba 05 00 00 00       	mov    edx,0x5
    4521:	48 8d 35 c8 78 00 00 	lea    rsi,[rip+0x78c8]        # bdf0 <error_at_line@@Base+0xae87>
    4528:	31 ff                	xor    edi,edi
    452a:	e8 91 c3 ff ff       	call   8c0 <dcgettext@plt>
    452f:	48 89 c7             	mov    rdi,rax
    4532:	e8 19 fa ff ff       	call   3f50 <error_at_line@@Base+0x2fe7>
    4537:	ba 05 00 00 00       	mov    edx,0x5
    453c:	48 8d 35 55 79 00 00 	lea    rsi,[rip+0x7955]        # be98 <error_at_line@@Base+0xaf2f>
    4543:	31 ff                	xor    edi,edi
    4545:	e8 76 c3 ff ff       	call   8c0 <dcgettext@plt>
    454a:	48 89 c7             	mov    rdi,rax
    454d:	e8 fe f9 ff ff       	call   3f50 <error_at_line@@Base+0x2fe7>
    4552:	ba 05 00 00 00       	mov    edx,0x5
    4557:	48 8d 35 82 79 00 00 	lea    rsi,[rip+0x7982]        # bee0 <error_at_line@@Base+0xaf77>
    455e:	31 ff                	xor    edi,edi
    4560:	e8 5b c3 ff ff       	call   8c0 <dcgettext@plt>
    4565:	48 89 c7             	mov    rdi,rax
    4568:	e8 e3 f9 ff ff       	call   3f50 <error_at_line@@Base+0x2fe7>
    456d:	ba 05 00 00 00       	mov    edx,0x5
    4572:	48 8d 35 97 79 00 00 	lea    rsi,[rip+0x7997]        # bf10 <error_at_line@@Base+0xafa7>
    4579:	31 ff                	xor    edi,edi
    457b:	e8 40 c3 ff ff       	call   8c0 <dcgettext@plt>
    4580:	48 89 c7             	mov    rdi,rax
    4583:	e8 c8 f9 ff ff       	call   3f50 <error_at_line@@Base+0x2fe7>
    4588:	ba 05 00 00 00       	mov    edx,0x5
    458d:	48 8d 35 f4 79 00 00 	lea    rsi,[rip+0x79f4]        # bf88 <error_at_line@@Base+0xb01f>
    4594:	31 ff                	xor    edi,edi
    4596:	e8 25 c3 ff ff       	call   8c0 <dcgettext@plt>
    459b:	48 89 c7             	mov    rdi,rax
    459e:	e8 ad f9 ff ff       	call   3f50 <error_at_line@@Base+0x2fe7>
    45a3:	ba 05 00 00 00       	mov    edx,0x5
    45a8:	48 8d 35 11 7a 00 00 	lea    rsi,[rip+0x7a11]        # bfc0 <error_at_line@@Base+0xb057>
    45af:	31 ff                	xor    edi,edi
    45b1:	e8 0a c3 ff ff       	call   8c0 <dcgettext@plt>
    45b6:	48 89 c7             	mov    rdi,rax
    45b9:	e8 92 f9 ff ff       	call   3f50 <error_at_line@@Base+0x2fe7>
    45be:	48 8d 05 03 71 00 00 	lea    rax,[rip+0x7103]        # b6c8 <error_at_line@@Base+0xa75f>
    45c5:	f3 0f 7e 05 43 a5 00 	movq   xmm0,QWORD PTR [rip+0xa543]        # eb10 <error_at_line@@Base+0xdba7>
    45cc:	00 
    45cd:	66 0f 6f ad 00 ff ff 	movdqa xmm5,XMMWORD PTR [rbp-0x100]
    45d4:	ff 
    45d5:	66 48 0f 6e f8       	movq   xmm7,rax
    45da:	66 0f 6f a5 10 ff ff 	movdqa xmm4,XMMWORD PTR [rbp-0xf0]
    45e1:	ff 
    45e2:	66 0f 6f 9d 20 ff ff 	movdqa xmm3,XMMWORD PTR [rbp-0xe0]
    45e9:	ff 
    45ea:	48 8d 05 c5 70 00 00 	lea    rax,[rip+0x70c5]        # b6b6 <error_at_line@@Base+0xa74d>
    45f1:	66 0f 6c c7          	punpcklqdq xmm0,xmm7
    45f5:	66 0f 6f 95 30 ff ff 	movdqa xmm2,XMMWORD PTR [rbp-0xd0]
    45fc:	ff 
    45fd:	66 0f 6f 8d 40 ff ff 	movdqa xmm1,XMMWORD PTR [rbp-0xc0]
    4604:	ff 
    4605:	0f 29 ad 50 ff ff ff 	movaps XMMWORD PTR [rbp-0xb0],xmm5
    460c:	0f 29 5d 80          	movaps XMMWORD PTR [rbp-0x80],xmm3
    4610:	48 8d 95 50 ff ff ff 	lea    rdx,[rbp-0xb0]
    4617:	be 77 00 00 00       	mov    esi,0x77
    461c:	bf 63 00 00 00       	mov    edi,0x63
    4621:	0f 29 85 60 ff ff ff 	movaps XMMWORD PTR [rbp-0xa0],xmm0
    4628:	66 0f ef c0          	pxor   xmm0,xmm0
    462c:	0f 29 a5 70 ff ff ff 	movaps XMMWORD PTR [rbp-0x90],xmm4
    4633:	0f 29 55 90          	movaps XMMWORD PTR [rbp-0x70],xmm2
    4637:	0f 29 4d a0          	movaps XMMWORD PTR [rbp-0x60],xmm1
    463b:	0f 29 45 b0          	movaps XMMWORD PTR [rbp-0x50],xmm0
    463f:	eb 2c                	jmp    466d <error_at_line@@Base+0x3704>
    4641:	66 0f 1f 84 00 00 00 	nop    WORD PTR [rax+rax*1+0x0]
    4648:	00 00 
    464a:	66 66 2e 0f 1f 84 00 	data16 cs nop WORD PTR [rax+rax*1+0x0]
    4651:	00 00 00 00 
    4655:	66 66 2e 0f 1f 84 00 	data16 cs nop WORD PTR [rax+rax*1+0x0]
    465c:	00 00 00 00 
    4660:	48 8b 42 10          	mov    rax,QWORD PTR [rdx+0x10]
    4664:	48 83 c2 10          	add    rdx,0x10
    4668:	48 85 c0             	test   rax,rax
    466b:	74 15                	je     4682 <error_at_line@@Base+0x3719>
    466d:	0f b6 08             	movzx  ecx,BYTE PTR [rax]
    4670:	39 ce                	cmp    esi,ecx
    4672:	75 ec                	jne    4660 <error_at_line@@Base+0x36f7>
    4674:	0f b6 48 01          	movzx  ecx,BYTE PTR [rax+0x1]
    4678:	39 cf                	cmp    edi,ecx
    467a:	75 e4                	jne    4660 <error_at_line@@Base+0x36f7>
    467c:	80 78 02 00          	cmp    BYTE PTR [rax+0x2],0x0
    4680:	75 de                	jne    4660 <error_at_line@@Base+0x36f7>
    4682:	4c 8b 6a 08          	mov    r13,QWORD PTR [rdx+0x8]
    4686:	49 8b 34 24          	mov    rsi,QWORD PTR [r12]
    468a:	bf 0a 00 00 00       	mov    edi,0xa
    468f:	4d 85 ed             	test   r13,r13
    4692:	0f 84 3e 01 00 00    	je     47d6 <error_at_line@@Base+0x386d>
    4698:	e8 83 c3 ff ff       	call   a20 <fputc_unlocked@plt>
    469d:	ba 05 00 00 00       	mov    edx,0x5
    46a2:	48 8d 35 6c 70 00 00 	lea    rsi,[rip+0x706c]        # b715 <error_at_line@@Base+0xa7ac>
    46a9:	48 8d 3d ff 6f 00 00 	lea    rdi,[rip+0x6fff]        # b6af <error_at_line@@Base+0xa746>
    46b0:	e8 0b c2 ff ff       	call   8c0 <dcgettext@plt>
    46b5:	48 8d 15 6d 70 00 00 	lea    rdx,[rip+0x706d]        # b729 <error_at_line@@Base+0xa7c0>
    46bc:	bf 02 00 00 00       	mov    edi,0x2
    46c1:	4c 8d 35 b0 73 00 00 	lea    r14,[rip+0x73b0]        # ba78 <error_at_line@@Base+0xab0f>
    46c8:	48 89 c6             	mov    rsi,rax
    46cb:	31 c0                	xor    eax,eax
    46cd:	4c 8d 3d 95 6f 00 00 	lea    r15,[rip+0x6f95]        # b669 <error_at_line@@Base+0xa700>
    46d4:	e8 f7 c3 ff ff       	call   ad0 <__printf_chk@plt>
    46d9:	ba 05 00 00 00       	mov    edx,0x5
    46de:	48 8d 35 5a 70 00 00 	lea    rsi,[rip+0x705a]        # b73f <error_at_line@@Base+0xa7d6>
    46e5:	48 8d 3d c3 6f 00 00 	lea    rdi,[rip+0x6fc3]        # b6af <error_at_line@@Base+0xa746>
    46ec:	e8 cf c1 ff ff       	call   8c0 <dcgettext@plt>
    46f1:	4c 89 f1             	mov    rcx,r14
    46f4:	bf 02 00 00 00       	mov    edi,0x2
    46f9:	48 8d 15 53 70 00 00 	lea    rdx,[rip+0x7053]        # b753 <error_at_line@@Base+0xa7ea>
    4700:	48 89 c6             	mov    rsi,rax
    4703:	31 c0                	xor    eax,eax
    4705:	e8 c6 c3 ff ff       	call   ad0 <__printf_chk@plt>
    470a:	ba 05 00 00 00       	mov    edx,0x5
    470f:	48 8d 35 ea 78 00 00 	lea    rsi,[rip+0x78ea]        # c000 <error_at_line@@Base+0xb097>
    4716:	48 8d 3d 92 6f 00 00 	lea    rdi,[rip+0x6f92]        # b6af <error_at_line@@Base+0xa746>
    471d:	e8 9e c1 ff ff       	call   8c0 <dcgettext@plt>
    4722:	48 8d 15 38 70 00 00 	lea    rdx,[rip+0x7038]        # b761 <error_at_line@@Base+0xa7f8>
    4729:	bf 02 00 00 00       	mov    edi,0x2
    472e:	48 89 c6             	mov    rsi,rax
    4731:	31 c0                	xor    eax,eax
    4733:	e8 98 c3 ff ff       	call   ad0 <__printf_chk@plt>
    4738:	31 f6                	xor    esi,esi
    473a:	bf 05 00 00 00       	mov    edi,0x5
    473f:	e8 7c c3 ff ff       	call   ac0 <setlocale@plt>
    4744:	48 85 c0             	test   rax,rax
    4747:	74 23                	je     476c <error_at_line@@Base+0x3803>
    4749:	ba 03 00 00 00       	mov    edx,0x3
    474e:	48 8d 35 29 70 00 00 	lea    rsi,[rip+0x7029]        # b77e <error_at_line@@Base+0xa815>
    4755:	48 89 c7             	mov    rdi,rax
    4758:	e8 b3 c0 ff ff       	call   810 <strncmp@plt>
    475d:	4c 8d 3d 05 6f 00 00 	lea    r15,[rip+0x6f05]        # b669 <error_at_line@@Base+0xa700>
    4764:	85 c0                	test   eax,eax
    4766:	0f 85 75 01 00 00    	jne    48e1 <error_at_line@@Base+0x3978>
    476c:	31 ff                	xor    edi,edi
    476e:	ba 05 00 00 00       	mov    edx,0x5
    4773:	48 8d 35 08 70 00 00 	lea    rsi,[rip+0x7008]        # b782 <error_at_line@@Base+0xa819>
    477a:	e8 41 c1 ff ff       	call   8c0 <dcgettext@plt>
    477f:	4c 89 f9             	mov    rcx,r15
    4782:	4c 89 f2             	mov    rdx,r14
    4785:	bf 02 00 00 00       	mov    edi,0x2
    478a:	48 89 c6             	mov    rsi,rax
    478d:	31 c0                	xor    eax,eax
    478f:	4c 8d 25 bb 6e 00 00 	lea    r12,[rip+0x6ebb]        # b651 <error_at_line@@Base+0xa6e8>
    4796:	e8 35 c3 ff ff       	call   ad0 <__printf_chk@plt>
    479b:	4d 39 fd             	cmp    r13,r15
    479e:	48 8d 05 2d 6f 00 00 	lea    rax,[rip+0x6f2d]        # b6d2 <error_at_line@@Base+0xa769>
    47a5:	4c 0f 44 e0          	cmove  r12,rax
    47a9:	31 ff                	xor    edi,edi
    47ab:	48 8d 35 be 78 00 00 	lea    rsi,[rip+0x78be]        # c070 <error_at_line@@Base+0xb107>
    47b2:	ba 05 00 00 00       	mov    edx,0x5
    47b7:	e8 04 c1 ff ff       	call   8c0 <dcgettext@plt>
    47bc:	4c 89 e1             	mov    rcx,r12
    47bf:	4c 89 ea             	mov    rdx,r13
    47c2:	bf 02 00 00 00       	mov    edi,0x2
    47c7:	48 89 c6             	mov    rsi,rax
    47ca:	31 c0                	xor    eax,eax
    47cc:	e8 ff c2 ff ff       	call   ad0 <__printf_chk@plt>
    47d1:	e9 c7 fb ff ff       	jmp    439d <error_at_line@@Base+0x3434>
    47d6:	e8 45 c2 ff ff       	call   a20 <fputc_unlocked@plt>
    47db:	ba 05 00 00 00       	mov    edx,0x5
    47e0:	48 8d 35 2e 6f 00 00 	lea    rsi,[rip+0x6f2e]        # b715 <error_at_line@@Base+0xa7ac>
    47e7:	48 8d 3d c1 6e 00 00 	lea    rdi,[rip+0x6ec1]        # b6af <error_at_line@@Base+0xa746>
    47ee:	e8 cd c0 ff ff       	call   8c0 <dcgettext@plt>
    47f3:	48 8d 15 2f 6f 00 00 	lea    rdx,[rip+0x6f2f]        # b729 <error_at_line@@Base+0xa7c0>
    47fa:	bf 02 00 00 00       	mov    edi,0x2
    47ff:	4c 8d 35 72 72 00 00 	lea    r14,[rip+0x7272]        # ba78 <error_at_line@@Base+0xab0f>
    4806:	48 89 c6             	mov    rsi,rax
    4809:	31 c0                	xor    eax,eax
    480b:	e8 c0 c2 ff ff       	call   ad0 <__printf_chk@plt>
    4810:	ba 05 00 00 00       	mov    edx,0x5
    4815:	48 8d 35 23 6f 00 00 	lea    rsi,[rip+0x6f23]        # b73f <error_at_line@@Base+0xa7d6>
    481c:	48 8d 3d 8c 6e 00 00 	lea    rdi,[rip+0x6e8c]        # b6af <error_at_line@@Base+0xa746>
    4823:	e8 98 c0 ff ff       	call   8c0 <dcgettext@plt>
    4828:	4c 89 f1             	mov    rcx,r14
    482b:	bf 02 00 00 00       	mov    edi,0x2
    4830:	48 8d 15 1c 6f 00 00 	lea    rdx,[rip+0x6f1c]        # b753 <error_at_line@@Base+0xa7ea>
    4837:	48 89 c6             	mov    rsi,rax
    483a:	31 c0                	xor    eax,eax
    483c:	e8 8f c2 ff ff       	call   ad0 <__printf_chk@plt>
    4841:	ba 05 00 00 00       	mov    edx,0x5
    4846:	48 8d 35 b3 77 00 00 	lea    rsi,[rip+0x77b3]        # c000 <error_at_line@@Base+0xb097>
    484d:	48 8d 3d 5b 6e 00 00 	lea    rdi,[rip+0x6e5b]        # b6af <error_at_line@@Base+0xa746>
    4854:	e8 67 c0 ff ff       	call   8c0 <dcgettext@plt>
    4859:	bf 02 00 00 00       	mov    edi,0x2
    485e:	48 8d 15 fc 6e 00 00 	lea    rdx,[rip+0x6efc]        # b761 <error_at_line@@Base+0xa7f8>
    4865:	48 89 c6             	mov    rsi,rax
    4868:	31 c0                	xor    eax,eax
    486a:	e8 61 c2 ff ff       	call   ad0 <__printf_chk@plt>
    486f:	31 f6                	xor    esi,esi
    4871:	bf 05 00 00 00       	mov    edi,0x5
    4876:	e8 45 c2 ff ff       	call   ac0 <setlocale@plt>
    487b:	48 85 c0             	test   rax,rax
    487e:	74 18                	je     4898 <error_at_line@@Base+0x392f>
    4880:	ba 03 00 00 00       	mov    edx,0x3
    4885:	48 8d 35 f2 6e 00 00 	lea    rsi,[rip+0x6ef2]        # b77e <error_at_line@@Base+0xa815>
    488c:	48 89 c7             	mov    rdi,rax
    488f:	e8 7c bf ff ff       	call   810 <strncmp@plt>
    4894:	85 c0                	test   eax,eax
    4896:	75 3f                	jne    48d7 <error_at_line@@Base+0x396e>
    4898:	ba 05 00 00 00       	mov    edx,0x5
    489d:	48 8d 35 de 6e 00 00 	lea    rsi,[rip+0x6ede]        # b782 <error_at_line@@Base+0xa819>
    48a4:	31 ff                	xor    edi,edi
    48a6:	e8 15 c0 ff ff       	call   8c0 <dcgettext@plt>
    48ab:	4c 89 f2             	mov    rdx,r14
    48ae:	48 8d 0d b4 6d 00 00 	lea    rcx,[rip+0x6db4]        # b669 <error_at_line@@Base+0xa700>
    48b5:	bf 02 00 00 00       	mov    edi,0x2
    48ba:	48 89 c6             	mov    rsi,rax
    48bd:	31 c0                	xor    eax,eax
    48bf:	4c 8d 2d a3 6d 00 00 	lea    r13,[rip+0x6da3]        # b669 <error_at_line@@Base+0xa700>
    48c6:	e8 05 c2 ff ff       	call   ad0 <__printf_chk@plt>
    48cb:	4c 8d 25 00 6e 00 00 	lea    r12,[rip+0x6e00]        # b6d2 <error_at_line@@Base+0xa769>
    48d2:	e9 d2 fe ff ff       	jmp    47a9 <error_at_line@@Base+0x3840>
    48d7:	4c 8d 3d 8b 6d 00 00 	lea    r15,[rip+0x6d8b]        # b669 <error_at_line@@Base+0xa700>
    48de:	4d 89 fd             	mov    r13,r15
    48e1:	4d 8b 24 24          	mov    r12,QWORD PTR [r12]
    48e5:	31 ff                	xor    edi,edi
    48e7:	ba 05 00 00 00       	mov    edx,0x5
    48ec:	48 8d 35 35 77 00 00 	lea    rsi,[rip+0x7735]        # c028 <error_at_line@@Base+0xb0bf>
    48f3:	e8 c8 bf ff ff       	call   8c0 <dcgettext@plt>
    48f8:	48 89 c7             	mov    rdi,rax
    48fb:	4c 89 e6             	mov    rsi,r12
    48fe:	e8 ed c0 ff ff       	call   9f0 <fputs_unlocked@plt>
    4903:	e9 64 fe ff ff       	jmp    476c <error_at_line@@Base+0x3803>
    4908:	0f 1f 84 00 00 00 00 	nop    DWORD PTR [rax+rax*1+0x0]
    490f:	00 
    4910:	f3 0f 1e fa          	endbr64
    4914:	55                   	push   rbp
    4915:	bf 01 00 00 00       	mov    edi,0x1
    491a:	48 89 e5             	mov    rbp,rsp
    491d:	e8 1e fa ff ff       	call   4340 <error_at_line@@Base+0x33d7>
    4922:	0f 1f 00             	nop    DWORD PTR [rax]
    4925:	66 66 2e 0f 1f 84 00 	data16 cs nop WORD PTR [rax+rax*1+0x0]
    492c:	00 00 00 00 
    4930:	55                   	push   rbp
    4931:	48 89 e5             	mov    rbp,rsp
    4934:	48 81 ec 90 01 00 00 	sub    rsp,0x190
    493b:	4c 89 65 e0          	mov    QWORD PTR [rbp-0x20],r12
    493f:	49 89 fc             	mov    r12,rdi
    4942:	48 89 5d d8          	mov    QWORD PTR [rbp-0x28],rbx
    4946:	4c 89 85 40 ff ff ff 	mov    QWORD PTR [rbp-0xc0],r8
    494d:	4c 89 8d 48 ff ff ff 	mov    QWORD PTR [rbp-0xb8],r9
    4954:	84 c0                	test   al,al
    4956:	74 29                	je     4981 <error_at_line@@Base+0x3a18>
    4958:	0f 29 85 50 ff ff ff 	movaps XMMWORD PTR [rbp-0xb0],xmm0
    495f:	0f 29 8d 60 ff ff ff 	movaps XMMWORD PTR [rbp-0xa0],xmm1
    4966:	0f 29 95 70 ff ff ff 	movaps XMMWORD PTR [rbp-0x90],xmm2
    496d:	0f 29 5d 80          	movaps XMMWORD PTR [rbp-0x80],xmm3
    4971:	0f 29 65 90          	movaps XMMWORD PTR [rbp-0x70],xmm4
    4975:	0f 29 6d a0          	movaps XMMWORD PTR [rbp-0x60],xmm5
    4979:	0f 29 75 b0          	movaps XMMWORD PTR [rbp-0x50],xmm6
    497d:	0f 29 7d c0          	movaps XMMWORD PTR [rbp-0x40],xmm7
    4981:	64 48 8b 04 25 28 00 	mov    rax,QWORD PTR fs:0x28
    4988:	00 00 
    498a:	48 89 85 18 ff ff ff 	mov    QWORD PTR [rbp-0xe8],rax
    4991:	31 c0                	xor    eax,eax
    4993:	48 8d 45 10          	lea    rax,[rbp+0x10]
    4997:	be 20 00 00 00       	mov    esi,0x20
    499c:	48 8d 7d 10          	lea    rdi,[rbp+0x10]
    49a0:	48 89 85 a8 fe ff ff 	mov    QWORD PTR [rbp-0x158],rax
    49a7:	48 8d 85 20 ff ff ff 	lea    rax,[rbp-0xe0]
    49ae:	31 db                	xor    ebx,ebx
    49b0:	48 89 85 b0 fe ff ff 	mov    QWORD PTR [rbp-0x150],rax
    49b7:	48 8d 85 c0 fe ff ff 	lea    rax,[rbp-0x140]
    49be:	c7 85 a0 fe ff ff 20 	mov    DWORD PTR [rbp-0x160],0x20
    49c5:	00 00 00 
    49c8:	c7 85 a4 fe ff ff 30 	mov    DWORD PTR [rbp-0x15c],0x30
    49cf:	00 00 00 
    49d2:	eb 2e                	jmp    4a02 <error_at_line@@Base+0x3a99>
    49d4:	0f 1f 40 00          	nop    DWORD PTR [rax+0x0]
    49d8:	89 f2                	mov    edx,esi
    49da:	83 c6 08             	add    esi,0x8
    49dd:	48 8d 94 15 20 ff ff 	lea    rdx,[rbp+rdx*1-0xe0]
    49e4:	ff 
    49e5:	48 8b 12             	mov    rdx,QWORD PTR [rdx]
    49e8:	48 89 10             	mov    QWORD PTR [rax],rdx
    49eb:	48 85 d2             	test   rdx,rdx
    49ee:	74 29                	je     4a19 <error_at_line@@Base+0x3ab0>
    49f0:	48 83 c3 01          	add    rbx,0x1
    49f4:	48 83 c0 08          	add    rax,0x8
    49f8:	48 83 fb 0a          	cmp    rbx,0xa
    49fc:	0f 84 d4 05 00 00    	je     4fd6 <error_at_line@@Base+0x406d>
    4a02:	83 fe 2f             	cmp    esi,0x2f
    4a05:	76 d1                	jbe    49d8 <error_at_line@@Base+0x3a6f>
    4a07:	48 89 fa             	mov    rdx,rdi
    4a0a:	48 83 c7 08          	add    rdi,0x8
    4a0e:	48 8b 12             	mov    rdx,QWORD PTR [rdx]
    4a11:	48 89 10             	mov    QWORD PTR [rax],rdx
    4a14:	48 85 d2             	test   rdx,rdx
    4a17:	75 d7                	jne    49f0 <error_at_line@@Base+0x3a87>
    4a19:	49 89 c9             	mov    r9,rcx
    4a1c:	4c 8d 05 30 6d 00 00 	lea    r8,[rip+0x6d30]        # b753 <error_at_line@@Base+0xa7ea>
    4a23:	4c 89 e7             	mov    rdi,r12
    4a26:	31 c0                	xor    eax,eax
    4a28:	48 8d 0d 3a 6c 00 00 	lea    rcx,[rip+0x6c3a]        # b669 <error_at_line@@Base+0xa700>
    4a2f:	48 8d 15 67 6d 00 00 	lea    rdx,[rip+0x6d67]        # b79d <error_at_line@@Base+0xa834>
    4a36:	be 02 00 00 00       	mov    esi,0x2
    4a3b:	e8 40 c1 ff ff       	call   b80 <__fprintf_chk@plt>
    4a40:	ba 05 00 00 00       	mov    edx,0x5
    4a45:	48 8d 35 5d 6d 00 00 	lea    rsi,[rip+0x6d5d]        # b7a9 <error_at_line@@Base+0xa840>
    4a4c:	48 8d 3d 5c 6c 00 00 	lea    rdi,[rip+0x6c5c]        # b6af <error_at_line@@Base+0xa746>
    4a53:	e8 68 be ff ff       	call   8c0 <dcgettext@plt>
    4a58:	41 b8 ea 07 00 00    	mov    r8d,0x7ea
    4a5e:	be 02 00 00 00       	mov    esi,0x2
    4a63:	4c 89 e7             	mov    rdi,r12
    4a66:	48 89 c1             	mov    rcx,rax
    4a69:	48 8d 15 10 7d 00 00 	lea    rdx,[rip+0x7d10]        # c780 <error_at_line@@Base+0xb817>
    4a70:	31 c0                	xor    eax,eax
    4a72:	e8 09 c1 ff ff       	call   b80 <__fprintf_chk@plt>
    4a77:	4c 89 e6             	mov    rsi,r12
    4a7a:	bf 0a 00 00 00       	mov    edi,0xa
    4a7f:	e8 9c bf ff ff       	call   a20 <fputc_unlocked@plt>
    4a84:	ba 05 00 00 00       	mov    edx,0x5
    4a89:	48 8d 35 18 76 00 00 	lea    rsi,[rip+0x7618]        # c0a8 <error_at_line@@Base+0xb13f>
    4a90:	48 8d 3d 18 6c 00 00 	lea    rdi,[rip+0x6c18]        # b6af <error_at_line@@Base+0xa746>
    4a97:	e8 24 be ff ff       	call   8c0 <dcgettext@plt>
    4a9c:	be 02 00 00 00       	mov    esi,0x2
    4aa1:	4c 89 e7             	mov    rdi,r12
    4aa4:	48 8d 0d ad 76 00 00 	lea    rcx,[rip+0x76ad]        # c158 <error_at_line@@Base+0xb1ef>
    4aab:	48 89 c2             	mov    rdx,rax
    4aae:	31 c0                	xor    eax,eax
    4ab0:	e8 cb c0 ff ff       	call   b80 <__fprintf_chk@plt>
    4ab5:	4c 89 e6             	mov    rsi,r12
    4ab8:	bf 0a 00 00 00       	mov    edi,0xa
    4abd:	e8 5e bf ff ff       	call   a20 <fputc_unlocked@plt>
    4ac2:	48 83 fb 09          	cmp    rbx,0x9
    4ac6:	0f 87 f4 00 00 00    	ja     4bc0 <error_at_line@@Base+0x3c57>
    4acc:	48 8d 15 ad 78 00 00 	lea    rdx,[rip+0x78ad]        # c380 <error_at_line@@Base+0xb417>
    4ad3:	48 63 04 9a          	movsxd rax,DWORD PTR [rdx+rbx*4]
    4ad7:	48 01 d0             	add    rax,rdx
    4ada:	3e ff e0             	notrack jmp rax
    4add:	4c 8b 9d e8 fe ff ff 	mov    r11,QWORD PTR [rbp-0x118]
    4ae4:	4c 8b 95 e0 fe ff ff 	mov    r10,QWORD PTR [rbp-0x120]
    4aeb:	4c 89 6d e8          	mov    QWORD PTR [rbp-0x18],r13
    4aef:	ba 05 00 00 00       	mov    edx,0x5
    4af4:	4c 8b 8d d0 fe ff ff 	mov    r9,QWORD PTR [rbp-0x130]
    4afb:	4c 8b 85 c8 fe ff ff 	mov    r8,QWORD PTR [rbp-0x138]
    4b02:	4c 89 75 f0          	mov    QWORD PTR [rbp-0x10],r14
    4b06:	48 8d 35 43 77 00 00 	lea    rsi,[rip+0x7743]        # c250 <error_at_line@@Base+0xb2e7>
    4b0d:	48 8b 8d c0 fe ff ff 	mov    rcx,QWORD PTR [rbp-0x140]
    4b14:	4c 8b b5 f8 fe ff ff 	mov    r14,QWORD PTR [rbp-0x108]
    4b1b:	4c 89 7d f8          	mov    QWORD PTR [rbp-0x8],r15
    4b1f:	4c 89 9d 78 fe ff ff 	mov    QWORD PTR [rbp-0x188],r11
    4b26:	4c 8b bd 00 ff ff ff 	mov    r15,QWORD PTR [rbp-0x100]
    4b2d:	4c 89 95 80 fe ff ff 	mov    QWORD PTR [rbp-0x180],r10
    4b34:	4c 8b ad f0 fe ff ff 	mov    r13,QWORD PTR [rbp-0x110]
    4b3b:	4c 89 8d 88 fe ff ff 	mov    QWORD PTR [rbp-0x178],r9
    4b42:	48 8b 9d d8 fe ff ff 	mov    rbx,QWORD PTR [rbp-0x128]
    4b49:	4c 89 85 90 fe ff ff 	mov    QWORD PTR [rbp-0x170],r8
    4b50:	48 89 8d 98 fe ff ff 	mov    QWORD PTR [rbp-0x168],rcx
    4b57:	48 8d 3d 51 6b 00 00 	lea    rdi,[rip+0x6b51]        # b6af <error_at_line@@Base+0xa746>
    4b5e:	e8 5d bd ff ff       	call   8c0 <dcgettext@plt>
    4b63:	4c 8b 9d 78 fe ff ff 	mov    r11,QWORD PTR [rbp-0x188]
    4b6a:	41 57                	push   r15
    4b6c:	be 02 00 00 00       	mov    esi,0x2
    4b71:	4c 8b 95 80 fe ff ff 	mov    r10,QWORD PTR [rbp-0x180]
    4b78:	41 56                	push   r14
    4b7a:	48 89 c2             	mov    rdx,rax
    4b7d:	4c 89 e7             	mov    rdi,r12
    4b80:	41 55                	push   r13
    4b82:	4c 8b 8d 88 fe ff ff 	mov    r9,QWORD PTR [rbp-0x178]
    4b89:	31 c0                	xor    eax,eax
    4b8b:	4c 8b 85 90 fe ff ff 	mov    r8,QWORD PTR [rbp-0x170]
    4b92:	48 8b 8d 98 fe ff ff 	mov    rcx,QWORD PTR [rbp-0x168]
    4b99:	41 53                	push   r11
    4b9b:	41 52                	push   r10
    4b9d:	53                   	push   rbx
    4b9e:	e8 dd bf ff ff       	call   b80 <__fprintf_chk@plt>
    4ba3:	4c 8b 6d e8          	mov    r13,QWORD PTR [rbp-0x18]
    4ba7:	4c 8b 75 f0          	mov    r14,QWORD PTR [rbp-0x10]
    4bab:	48 83 c4 30          	add    rsp,0x30
    4baf:	4c 8b 7d f8          	mov    r15,QWORD PTR [rbp-0x8]
    4bb3:	66 90                	xchg   ax,ax
    4bb5:	66 66 2e 0f 1f 84 00 	data16 cs nop WORD PTR [rax+rax*1+0x0]
    4bbc:	00 00 00 00 
    4bc0:	48 8b 85 18 ff ff ff 	mov    rax,QWORD PTR [rbp-0xe8]
    4bc7:	64 48 2b 04 25 28 00 	sub    rax,QWORD PTR fs:0x28
    4bce:	00 00 
    4bd0:	0f 85 28 05 00 00    	jne    50fe <error_at_line@@Base+0x4195>
    4bd6:	48 8b 5d d8          	mov    rbx,QWORD PTR [rbp-0x28]
    4bda:	4c 8b 65 e0          	mov    r12,QWORD PTR [rbp-0x20]
    4bde:	c9                   	leave
    4bdf:	c3                   	ret
    4be0:	4c 8b 9d e8 fe ff ff 	mov    r11,QWORD PTR [rbp-0x118]
    4be7:	4c 8b 95 e0 fe ff ff 	mov    r10,QWORD PTR [rbp-0x120]
    4bee:	ba 05 00 00 00       	mov    edx,0x5
    4bf3:	48 8d 35 26 76 00 00 	lea    rsi,[rip+0x7626]        # c220 <error_at_line@@Base+0xb2b7>
    4bfa:	4c 8b 8d d0 fe ff ff 	mov    r9,QWORD PTR [rbp-0x130]
    4c01:	4c 8b 85 c8 fe ff ff 	mov    r8,QWORD PTR [rbp-0x138]
    4c08:	4c 89 75 f0          	mov    QWORD PTR [rbp-0x10],r14
    4c0c:	48 8d 3d 9c 6a 00 00 	lea    rdi,[rip+0x6a9c]        # b6af <error_at_line@@Base+0xa746>
    4c13:	48 8b 8d c0 fe ff ff 	mov    rcx,QWORD PTR [rbp-0x140]
    4c1a:	4c 89 7d f8          	mov    QWORD PTR [rbp-0x8],r15
    4c1e:	4c 8b b5 f8 fe ff ff 	mov    r14,QWORD PTR [rbp-0x108]
    4c25:	4c 8b bd f0 fe ff ff 	mov    r15,QWORD PTR [rbp-0x110]
    4c2c:	4c 89 9d 78 fe ff ff 	mov    QWORD PTR [rbp-0x188],r11
    4c33:	4c 89 95 80 fe ff ff 	mov    QWORD PTR [rbp-0x180],r10
    4c3a:	48 8b 9d d8 fe ff ff 	mov    rbx,QWORD PTR [rbp-0x128]
    4c41:	4c 89 8d 88 fe ff ff 	mov    QWORD PTR [rbp-0x178],r9
    4c48:	4c 89 85 90 fe ff ff 	mov    QWORD PTR [rbp-0x170],r8
    4c4f:	48 89 8d 98 fe ff ff 	mov    QWORD PTR [rbp-0x168],rcx
    4c56:	e8 65 bc ff ff       	call   8c0 <dcgettext@plt>
    4c5b:	4c 8b 9d 78 fe ff ff 	mov    r11,QWORD PTR [rbp-0x188]
    4c62:	4c 89 e7             	mov    rdi,r12
    4c65:	4c 8b 95 80 fe ff ff 	mov    r10,QWORD PTR [rbp-0x180]
    4c6c:	52                   	push   rdx
    4c6d:	be 02 00 00 00       	mov    esi,0x2
    4c72:	48 89 c2             	mov    rdx,rax
    4c75:	4c 8b 8d 88 fe ff ff 	mov    r9,QWORD PTR [rbp-0x178]
    4c7c:	41 56                	push   r14
    4c7e:	4c 8b 85 90 fe ff ff 	mov    r8,QWORD PTR [rbp-0x170]
    4c85:	31 c0                	xor    eax,eax
    4c87:	41 57                	push   r15
    4c89:	48 8b 8d 98 fe ff ff 	mov    rcx,QWORD PTR [rbp-0x168]
    4c90:	41 53                	push   r11
    4c92:	41 52                	push   r10
    4c94:	53                   	push   rbx
    4c95:	e8 e6 be ff ff       	call   b80 <__fprintf_chk@plt>
    4c9a:	4c 8b 75 f0          	mov    r14,QWORD PTR [rbp-0x10]
    4c9e:	4c 8b 7d f8          	mov    r15,QWORD PTR [rbp-0x8]
    4ca2:	48 83 c4 30          	add    rsp,0x30
    4ca6:	e9 15 ff ff ff       	jmp    4bc0 <error_at_line@@Base+0x3c57>
    4cab:	48 8b 9d c0 fe ff ff 	mov    rbx,QWORD PTR [rbp-0x140]
    4cb2:	ba 05 00 00 00       	mov    edx,0x5
    4cb7:	48 8d 35 ef 6a 00 00 	lea    rsi,[rip+0x6aef]        # b7ad <error_at_line@@Base+0xa844>
    4cbe:	48 8d 3d ea 69 00 00 	lea    rdi,[rip+0x69ea]        # b6af <error_at_line@@Base+0xa746>
    4cc5:	e8 f6 bb ff ff       	call   8c0 <dcgettext@plt>
    4cca:	be 02 00 00 00       	mov    esi,0x2
    4ccf:	4c 89 e7             	mov    rdi,r12
    4cd2:	48 89 c2             	mov    rdx,rax
    4cd5:	48 89 d9             	mov    rcx,rbx
    4cd8:	31 c0                	xor    eax,eax
    4cda:	e8 a1 be ff ff       	call   b80 <__fprintf_chk@plt>
    4cdf:	e9 dc fe ff ff       	jmp    4bc0 <error_at_line@@Base+0x3c57>
    4ce4:	4c 8b 85 c8 fe ff ff 	mov    r8,QWORD PTR [rbp-0x138]
    4ceb:	48 8b 9d c0 fe ff ff 	mov    rbx,QWORD PTR [rbp-0x140]
    4cf2:	ba 05 00 00 00       	mov    edx,0x5
    4cf7:	48 8d 35 bf 6a 00 00 	lea    rsi,[rip+0x6abf]        # b7bd <error_at_line@@Base+0xa854>
    4cfe:	48 8d 3d aa 69 00 00 	lea    rdi,[rip+0x69aa]        # b6af <error_at_line@@Base+0xa746>
    4d05:	4c 89 85 98 fe ff ff 	mov    QWORD PTR [rbp-0x168],r8
    4d0c:	e8 af bb ff ff       	call   8c0 <dcgettext@plt>
    4d11:	48 89 d9             	mov    rcx,rbx
    4d14:	be 02 00 00 00       	mov    esi,0x2
    4d19:	4c 89 e7             	mov    rdi,r12
    4d1c:	4c 8b 85 98 fe ff ff 	mov    r8,QWORD PTR [rbp-0x168]
    4d23:	48 89 c2             	mov    rdx,rax
    4d26:	31 c0                	xor    eax,eax
    4d28:	e8 53 be ff ff       	call   b80 <__fprintf_chk@plt>
    4d2d:	e9 8e fe ff ff       	jmp    4bc0 <error_at_line@@Base+0x3c57>
    4d32:	4c 8b 8d d0 fe ff ff 	mov    r9,QWORD PTR [rbp-0x130]
    4d39:	4c 8b 85 c8 fe ff ff 	mov    r8,QWORD PTR [rbp-0x138]
    4d40:	ba 05 00 00 00       	mov    edx,0x5
    4d45:	48 8d 35 88 6a 00 00 	lea    rsi,[rip+0x6a88]        # b7d4 <error_at_line@@Base+0xa86b>
    4d4c:	48 8b 9d c0 fe ff ff 	mov    rbx,QWORD PTR [rbp-0x140]
    4d53:	48 8d 3d 55 69 00 00 	lea    rdi,[rip+0x6955]        # b6af <error_at_line@@Base+0xa746>
    4d5a:	4c 89 8d 90 fe ff ff 	mov    QWORD PTR [rbp-0x170],r9
    4d61:	4c 89 85 98 fe ff ff 	mov    QWORD PTR [rbp-0x168],r8
    4d68:	e8 53 bb ff ff       	call   8c0 <dcgettext@plt>
    4d6d:	48 89 d9             	mov    rcx,rbx
    4d70:	be 02 00 00 00       	mov    esi,0x2
    4d75:	4c 89 e7             	mov    rdi,r12
    4d78:	4c 8b 8d 90 fe ff ff 	mov    r9,QWORD PTR [rbp-0x170]
    4d7f:	4c 8b 85 98 fe ff ff 	mov    r8,QWORD PTR [rbp-0x168]
    4d86:	48 89 c2             	mov    rdx,rax
    4d89:	31 c0                	xor    eax,eax
    4d8b:	e8 f0 bd ff ff       	call   b80 <__fprintf_chk@plt>
    4d90:	e9 2b fe ff ff       	jmp    4bc0 <error_at_line@@Base+0x3c57>
    4d95:	4c 8b 85 c8 fe ff ff 	mov    r8,QWORD PTR [rbp-0x138]
    4d9c:	4c 8b 8d d0 fe ff ff 	mov    r9,QWORD PTR [rbp-0x130]
    4da3:	ba 05 00 00 00       	mov    edx,0x5
    4da8:	48 8d 35 d1 73 00 00 	lea    rsi,[rip+0x73d1]        # c180 <error_at_line@@Base+0xb217>
    4daf:	48 8b 8d c0 fe ff ff 	mov    rcx,QWORD PTR [rbp-0x140]
    4db6:	48 8d 3d f2 68 00 00 	lea    rdi,[rip+0x68f2]        # b6af <error_at_line@@Base+0xa746>
    4dbd:	48 8b 9d d8 fe ff ff 	mov    rbx,QWORD PTR [rbp-0x128]
    4dc4:	4c 89 85 90 fe ff ff 	mov    QWORD PTR [rbp-0x170],r8
    4dcb:	4c 89 8d 88 fe ff ff 	mov    QWORD PTR [rbp-0x178],r9
    4dd2:	48 89 8d 98 fe ff ff 	mov    QWORD PTR [rbp-0x168],rcx
    4dd9:	e8 e2 ba ff ff       	call   8c0 <dcgettext@plt>
    4dde:	41 50                	push   r8
    4de0:	53                   	push   rbx
    4de1:	4c 8b 8d 88 fe ff ff 	mov    r9,QWORD PTR [rbp-0x178]
    4de8:	48 89 c2             	mov    rdx,rax
    4deb:	be 02 00 00 00       	mov    esi,0x2
    4df0:	4c 8b 85 90 fe ff ff 	mov    r8,QWORD PTR [rbp-0x170]
    4df7:	48 8b 8d 98 fe ff ff 	mov    rcx,QWORD PTR [rbp-0x168]
    4dfe:	4c 89 e7             	mov    rdi,r12
    4e01:	31 c0                	xor    eax,eax
    4e03:	e8 78 bd ff ff       	call   b80 <__fprintf_chk@plt>
    4e08:	5e                   	pop    rsi
    4e09:	5f                   	pop    rdi
    4e0a:	e9 b1 fd ff ff       	jmp    4bc0 <error_at_line@@Base+0x3c57>
    4e0f:	4c 8b 95 e0 fe ff ff 	mov    r10,QWORD PTR [rbp-0x120]
    4e16:	4c 8b 8d d0 fe ff ff 	mov    r9,QWORD PTR [rbp-0x130]
    4e1d:	ba 05 00 00 00       	mov    edx,0x5
    4e22:	48 8d 35 77 73 00 00 	lea    rsi,[rip+0x7377]        # c1a0 <error_at_line@@Base+0xb237>
    4e29:	4c 8b 85 c8 fe ff ff 	mov    r8,QWORD PTR [rbp-0x138]
    4e30:	48 8b 8d c0 fe ff ff 	mov    rcx,QWORD PTR [rbp-0x140]
    4e37:	48 8d 3d 71 68 00 00 	lea    rdi,[rip+0x6871]        # b6af <error_at_line@@Base+0xa746>
    4e3e:	4c 89 95 80 fe ff ff 	mov    QWORD PTR [rbp-0x180],r10
    4e45:	48 8b 9d d8 fe ff ff 	mov    rbx,QWORD PTR [rbp-0x128]
    4e4c:	4c 89 8d 88 fe ff ff 	mov    QWORD PTR [rbp-0x178],r9
    4e53:	4c 89 85 90 fe ff ff 	mov    QWORD PTR [rbp-0x170],r8
    4e5a:	48 89 8d 98 fe ff ff 	mov    QWORD PTR [rbp-0x168],rcx
    4e61:	e8 5a ba ff ff       	call   8c0 <dcgettext@plt>
    4e66:	4c 8b 95 80 fe ff ff 	mov    r10,QWORD PTR [rbp-0x180]
    4e6d:	41 52                	push   r10
    4e6f:	e9 6c ff ff ff       	jmp    4de0 <error_at_line@@Base+0x3e77>
    4e74:	48 8b 8d c0 fe ff ff 	mov    rcx,QWORD PTR [rbp-0x140]
    4e7b:	4c 8b 9d e8 fe ff ff 	mov    r11,QWORD PTR [rbp-0x118]
    4e82:	ba 05 00 00 00       	mov    edx,0x5
    4e87:	48 8d 35 3a 73 00 00 	lea    rsi,[rip+0x733a]        # c1c8 <error_at_line@@Base+0xb25f>
    4e8e:	4c 8b 95 e0 fe ff ff 	mov    r10,QWORD PTR [rbp-0x120]
    4e95:	4c 8b 8d d0 fe ff ff 	mov    r9,QWORD PTR [rbp-0x130]
    4e9c:	48 8d 3d 0c 68 00 00 	lea    rdi,[rip+0x680c]        # b6af <error_at_line@@Base+0xa746>
    4ea3:	4c 8b 85 c8 fe ff ff 	mov    r8,QWORD PTR [rbp-0x138]
    4eaa:	48 89 8d 98 fe ff ff 	mov    QWORD PTR [rbp-0x168],rcx
    4eb1:	4c 89 9d 78 fe ff ff 	mov    QWORD PTR [rbp-0x188],r11
    4eb8:	48 8b 9d d8 fe ff ff 	mov    rbx,QWORD PTR [rbp-0x128]
    4ebf:	4c 89 95 80 fe ff ff 	mov    QWORD PTR [rbp-0x180],r10
    4ec6:	4c 89 8d 88 fe ff ff 	mov    QWORD PTR [rbp-0x178],r9
    4ecd:	4c 89 85 90 fe ff ff 	mov    QWORD PTR [rbp-0x170],r8
    4ed4:	e8 e7 b9 ff ff       	call   8c0 <dcgettext@plt>
    4ed9:	4c 8b 9d 78 fe ff ff 	mov    r11,QWORD PTR [rbp-0x188]
    4ee0:	4c 89 e7             	mov    rdi,r12
    4ee3:	4c 8b 95 80 fe ff ff 	mov    r10,QWORD PTR [rbp-0x180]
    4eea:	51                   	push   rcx
    4eeb:	4c 8b 8d 88 fe ff ff 	mov    r9,QWORD PTR [rbp-0x178]
    4ef2:	48 89 c2             	mov    rdx,rax
    4ef5:	be 02 00 00 00       	mov    esi,0x2
    4efa:	41 53                	push   r11
    4efc:	4c 8b 85 90 fe ff ff 	mov    r8,QWORD PTR [rbp-0x170]
    4f03:	31 c0                	xor    eax,eax
    4f05:	41 52                	push   r10
    4f07:	48 8b 8d 98 fe ff ff 	mov    rcx,QWORD PTR [rbp-0x168]
    4f0e:	53                   	push   rbx
    4f0f:	e8 6c bc ff ff       	call   b80 <__fprintf_chk@plt>
    4f14:	48 83 c4 20          	add    rsp,0x20
    4f18:	e9 a3 fc ff ff       	jmp    4bc0 <error_at_line@@Base+0x3c57>
    4f1d:	4c 8b 9d e8 fe ff ff 	mov    r11,QWORD PTR [rbp-0x118]
    4f24:	4c 8b 95 e0 fe ff ff 	mov    r10,QWORD PTR [rbp-0x120]
    4f2b:	ba 05 00 00 00       	mov    edx,0x5
    4f30:	48 8d 35 b9 72 00 00 	lea    rsi,[rip+0x72b9]        # c1f0 <error_at_line@@Base+0xb287>
    4f37:	4c 8b 8d d0 fe ff ff 	mov    r9,QWORD PTR [rbp-0x130]
    4f3e:	4c 8b 85 c8 fe ff ff 	mov    r8,QWORD PTR [rbp-0x138]
    4f45:	4c 89 75 f0          	mov    QWORD PTR [rbp-0x10],r14
    4f49:	48 8d 3d 5f 67 00 00 	lea    rdi,[rip+0x675f]        # b6af <error_at_line@@Base+0xa746>
    4f50:	48 8b 8d c0 fe ff ff 	mov    rcx,QWORD PTR [rbp-0x140]
    4f57:	4c 8b b5 f0 fe ff ff 	mov    r14,QWORD PTR [rbp-0x110]
    4f5e:	4c 89 9d 78 fe ff ff 	mov    QWORD PTR [rbp-0x188],r11
    4f65:	4c 89 95 80 fe ff ff 	mov    QWORD PTR [rbp-0x180],r10
    4f6c:	48 8b 9d d8 fe ff ff 	mov    rbx,QWORD PTR [rbp-0x128]
    4f73:	4c 89 8d 88 fe ff ff 	mov    QWORD PTR [rbp-0x178],r9
    4f7a:	4c 89 85 90 fe ff ff 	mov    QWORD PTR [rbp-0x170],r8
    4f81:	48 89 8d 98 fe ff ff 	mov    QWORD PTR [rbp-0x168],rcx
    4f88:	e8 33 b9 ff ff       	call   8c0 <dcgettext@plt>
    4f8d:	4c 8b 9d 78 fe ff ff 	mov    r11,QWORD PTR [rbp-0x188]
    4f94:	41 56                	push   r14
    4f96:	be 02 00 00 00       	mov    esi,0x2
    4f9b:	4c 8b 95 80 fe ff ff 	mov    r10,QWORD PTR [rbp-0x180]
    4fa2:	48 89 c2             	mov    rdx,rax
    4fa5:	4c 89 e7             	mov    rdi,r12
    4fa8:	31 c0                	xor    eax,eax
    4faa:	4c 8b 8d 88 fe ff ff 	mov    r9,QWORD PTR [rbp-0x178]
    4fb1:	4c 8b 85 90 fe ff ff 	mov    r8,QWORD PTR [rbp-0x170]
    4fb8:	41 53                	push   r11
    4fba:	41 52                	push   r10
    4fbc:	48 8b 8d 98 fe ff ff 	mov    rcx,QWORD PTR [rbp-0x168]
    4fc3:	53                   	push   rbx
    4fc4:	e8 b7 bb ff ff       	call   b80 <__fprintf_chk@plt>
    4fc9:	4c 8b 75 f0          	mov    r14,QWORD PTR [rbp-0x10]
    4fcd:	48 83 c4 20          	add    rsp,0x20
    4fd1:	e9 ea fb ff ff       	jmp    4bc0 <error_at_line@@Base+0x3c57>
    4fd6:	49 89 c9             	mov    r9,rcx
    4fd9:	4c 8d 05 73 67 00 00 	lea    r8,[rip+0x6773]        # b753 <error_at_line@@Base+0xa7ea>
    4fe0:	4c 89 e7             	mov    rdi,r12
    4fe3:	31 c0                	xor    eax,eax
    4fe5:	48 8d 0d 7d 66 00 00 	lea    rcx,[rip+0x667d]        # b669 <error_at_line@@Base+0xa700>
    4fec:	48 8d 15 aa 67 00 00 	lea    rdx,[rip+0x67aa]        # b79d <error_at_line@@Base+0xa834>
    4ff3:	be 02 00 00 00       	mov    esi,0x2
    4ff8:	4c 89 6d e8          	mov    QWORD PTR [rbp-0x18],r13
    4ffc:	4c 89 75 f0          	mov    QWORD PTR [rbp-0x10],r14
    5000:	4c 89 7d f8          	mov    QWORD PTR [rbp-0x8],r15
    5004:	e8 77 bb ff ff       	call   b80 <__fprintf_chk@plt>
    5009:	ba 05 00 00 00       	mov    edx,0x5
    500e:	48 8d 35 94 67 00 00 	lea    rsi,[rip+0x6794]        # b7a9 <error_at_line@@Base+0xa840>
    5015:	48 8d 3d 93 66 00 00 	lea    rdi,[rip+0x6693]        # b6af <error_at_line@@Base+0xa746>
    501c:	e8 9f b8 ff ff       	call   8c0 <dcgettext@plt>
    5021:	41 b8 ea 07 00 00    	mov    r8d,0x7ea
    5027:	be 02 00 00 00       	mov    esi,0x2
    502c:	4c 89 e7             	mov    rdi,r12
    502f:	48 89 c1             	mov    rcx,rax
    5032:	48 8d 15 47 77 00 00 	lea    rdx,[rip+0x7747]        # c780 <error_at_line@@Base+0xb817>
    5039:	31 c0                	xor    eax,eax
    503b:	e8 40 bb ff ff       	call   b80 <__fprintf_chk@plt>
    5040:	4c 89 e6             	mov    rsi,r12
    5043:	bf 0a 00 00 00       	mov    edi,0xa
    5048:	e8 d3 b9 ff ff       	call   a20 <fputc_unlocked@plt>
    504d:	ba 05 00 00 00       	mov    edx,0x5
    5052:	48 8d 35 4f 70 00 00 	lea    rsi,[rip+0x704f]        # c0a8 <error_at_line@@Base+0xb13f>
    5059:	48 8d 3d 4f 66 00 00 	lea    rdi,[rip+0x664f]        # b6af <error_at_line@@Base+0xa746>
    5060:	e8 5b b8 ff ff       	call   8c0 <dcgettext@plt>
    5065:	48 8d 0d ec 70 00 00 	lea    rcx,[rip+0x70ec]        # c158 <error_at_line@@Base+0xb1ef>
    506c:	be 02 00 00 00       	mov    esi,0x2
    5071:	4c 89 e7             	mov    rdi,r12
    5074:	48 89 c2             	mov    rdx,rax
    5077:	31 c0                	xor    eax,eax
    5079:	e8 02 bb ff ff       	call   b80 <__fprintf_chk@plt>
    507e:	4c 89 e6             	mov    rsi,r12
    5081:	bf 0a 00 00 00       	mov    edi,0xa
    5086:	e8 95 b9 ff ff       	call   a20 <fputc_unlocked@plt>
    508b:	4c 8b 9d e8 fe ff ff 	mov    r11,QWORD PTR [rbp-0x118]
    5092:	4c 8b 95 e0 fe ff ff 	mov    r10,QWORD PTR [rbp-0x120]
    5099:	ba 05 00 00 00       	mov    edx,0x5
    509e:	4c 8b 8d d0 fe ff ff 	mov    r9,QWORD PTR [rbp-0x130]
    50a5:	4c 8b 85 c8 fe ff ff 	mov    r8,QWORD PTR [rbp-0x138]
    50ac:	48 8d 35 d5 71 00 00 	lea    rsi,[rip+0x71d5]        # c288 <error_at_line@@Base+0xb31f>
    50b3:	48 8b 8d c0 fe ff ff 	mov    rcx,QWORD PTR [rbp-0x140]
    50ba:	4c 89 9d 78 fe ff ff 	mov    QWORD PTR [rbp-0x188],r11
    50c1:	4c 89 95 80 fe ff ff 	mov    QWORD PTR [rbp-0x180],r10
    50c8:	4c 8b bd 00 ff ff ff 	mov    r15,QWORD PTR [rbp-0x100]
    50cf:	4c 89 8d 88 fe ff ff 	mov    QWORD PTR [rbp-0x178],r9
    50d6:	4c 8b b5 f8 fe ff ff 	mov    r14,QWORD PTR [rbp-0x108]
    50dd:	4c 89 85 90 fe ff ff 	mov    QWORD PTR [rbp-0x170],r8
    50e4:	4c 8b ad f0 fe ff ff 	mov    r13,QWORD PTR [rbp-0x110]
    50eb:	48 89 8d 98 fe ff ff 	mov    QWORD PTR [rbp-0x168],rcx
    50f2:	48 8b 9d d8 fe ff ff 	mov    rbx,QWORD PTR [rbp-0x128]
    50f9:	e9 59 fa ff ff       	jmp    4b57 <error_at_line@@Base+0x3bee>
    50fe:	4c 89 6d e8          	mov    QWORD PTR [rbp-0x18],r13
    5102:	4c 89 75 f0          	mov    QWORD PTR [rbp-0x10],r14
    5106:	4c 89 7d f8          	mov    QWORD PTR [rbp-0x8],r15
    510a:	e8 e1 b7 ff ff       	call   8f0 <__stack_chk_fail@plt>
    510f:	90                   	nop
    5110:	55                   	push   rbp
    5111:	48 89 e5             	mov    rbp,rsp
    5114:	48 83 ec 10          	sub    rsp,0x10
    5118:	4c 89 65 f8          	mov    QWORD PTR [rbp-0x8],r12
    511c:	4c 8b 67 08          	mov    r12,QWORD PTR [rdi+0x8]
    5120:	4d 85 e4             	test   r12,r12
    5123:	74 41                	je     5166 <error_at_line@@Base+0x41fd>
    5125:	48 89 5d f0          	mov    QWORD PTR [rbp-0x10],rbx
    5129:	48 89 fb             	mov    rbx,rdi
    512c:	eb 14                	jmp    5142 <error_at_line@@Base+0x41d9>
    512e:	66 90                	xchg   ax,ax
    5130:	48 8b 7b 48          	mov    rdi,QWORD PTR [rbx+0x48]
    5134:	48 89 d6             	mov    rsi,rdx
    5137:	ff d0                	call   rax
    5139:	80 4b 50 02          	or     BYTE PTR [rbx+0x50],0x2
    513d:	4d 85 e4             	test   r12,r12
    5140:	74 20                	je     5162 <error_at_line@@Base+0x41f9>
    5142:	4c 89 e2             	mov    rdx,r12
    5145:	48 8b 43 40          	mov    rax,QWORD PTR [rbx+0x40]
    5149:	4d 8b 64 24 08       	mov    r12,QWORD PTR [r12+0x8]
    514e:	f6 43 50 01          	test   BYTE PTR [rbx+0x50],0x1
    5152:	75 dc                	jne    5130 <error_at_line@@Base+0x41c7>
    5154:	48 89 d7             	mov    rdi,rdx
    5157:	ff d0                	call   rax
    5159:	80 4b 50 02          	or     BYTE PTR [rbx+0x50],0x2
    515d:	4d 85 e4             	test   r12,r12
    5160:	75 e0                	jne    5142 <error_at_line@@Base+0x41d9>
    5162:	48 8b 5d f0          	mov    rbx,QWORD PTR [rbp-0x10]
    5166:	4c 8b 65 f8          	mov    r12,QWORD PTR [rbp-0x8]
    516a:	c9                   	leave
    516b:	c3                   	ret
    516c:	0f 1f 40 00          	nop    DWORD PTR [rax+0x0]
    5170:	48 85 ff             	test   rdi,rdi
    5173:	0f 84 a7 00 00 00    	je     5220 <error_at_line@@Base+0x42b7>
    5179:	80 3f 2d             	cmp    BYTE PTR [rdi],0x2d
    517c:	0f 85 9e 00 00 00    	jne    5220 <error_at_line@@Base+0x42b7>
    5182:	55                   	push   rbp
    5183:	48 89 e5             	mov    rbp,rsp
    5186:	48 83 ec 20          	sub    rsp,0x20
    518a:	48 89 5d e8          	mov    QWORD PTR [rbp-0x18],rbx
    518e:	48 8b 1d 7b a0 00 00 	mov    rbx,QWORD PTR [rip+0xa07b]        # f210 <error_print_progname@@Base+0x128>
    5195:	4c 89 6d f8          	mov    QWORD PTR [rbp-0x8],r13
    5199:	49 89 fd             	mov    r13,rdi
    519c:	48 85 db             	test   rbx,rbx
    519f:	0f 84 b3 00 00 00    	je     5258 <error_at_line@@Base+0x42ef>
    51a5:	0f b6 03             	movzx  eax,BYTE PTR [rbx]
    51a8:	84 c0                	test   al,al
    51aa:	0f 84 94 00 00 00    	je     5244 <error_at_line@@Base+0x42db>
    51b0:	be 3a 00 00 00       	mov    esi,0x3a
    51b5:	48 89 df             	mov    rdi,rbx
    51b8:	4c 89 65 f0          	mov    QWORD PTR [rbp-0x10],r12
    51bc:	e8 5f b7 ff ff       	call   920 <strchr@plt>
    51c1:	49 89 c4             	mov    r12,rax
    51c4:	48 85 c0             	test   rax,rax
    51c7:	74 67                	je     5230 <error_at_line@@Base+0x42c7>
    51c9:	0f 1f 80 00 00 00 00 	nop    DWORD PTR [rax+0x0]
    51d0:	48 89 df             	mov    rdi,rbx
    51d3:	4c 89 ee             	mov    rsi,r13
    51d6:	e8 15 ba ff ff       	call   bf0 <strstr@plt>
    51db:	48 89 c3             	mov    rbx,rax
    51de:	48 85 c0             	test   rax,rax
    51e1:	74 5d                	je     5240 <error_at_line@@Base+0x42d7>
    51e3:	4c 39 e0             	cmp    rax,r12
    51e6:	73 58                	jae    5240 <error_at_line@@Base+0x42d7>
    51e8:	4c 89 ef             	mov    rdi,r13
    51eb:	e8 f0 b6 ff ff       	call   8e0 <strlen@plt>
    51f0:	48 01 c3             	add    rbx,rax
    51f3:	0f b6 03             	movzx  eax,BYTE PTR [rbx]
    51f6:	3c 3a                	cmp    al,0x3a
    51f8:	77 d6                	ja     51d0 <error_at_line@@Base+0x4267>
    51fa:	48 ba 01 00 00 00 00 	movabs rdx,0x400100000000001
    5201:	10 00 04 
    5204:	48 0f a3 c2          	bt     rdx,rax
    5208:	73 c6                	jae    51d0 <error_at_line@@Base+0x4267>
    520a:	4c 8b 65 f0          	mov    r12,QWORD PTR [rbp-0x10]
    520e:	48 8b 5d e8          	mov    rbx,QWORD PTR [rbp-0x18]
    5212:	31 c0                	xor    eax,eax
    5214:	4c 8b 6d f8          	mov    r13,QWORD PTR [rbp-0x8]
    5218:	c9                   	leave
    5219:	c3                   	ret
    521a:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]
    5220:	b8 01 00 00 00       	mov    eax,0x1
    5225:	c3                   	ret
    5226:	66 2e 0f 1f 84 00 00 	cs nop WORD PTR [rax+rax*1+0x0]
    522d:	00 00 00 
    5230:	48 89 df             	mov    rdi,rbx
    5233:	e8 a8 b6 ff ff       	call   8e0 <strlen@plt>
    5238:	4c 8d 24 03          	lea    r12,[rbx+rax*1]
    523c:	eb 92                	jmp    51d0 <error_at_line@@Base+0x4267>
    523e:	66 90                	xchg   ax,ax
    5240:	4c 8b 65 f0          	mov    r12,QWORD PTR [rbp-0x10]
    5244:	48 8b 5d e8          	mov    rbx,QWORD PTR [rbp-0x18]
    5248:	4c 8b 6d f8          	mov    r13,QWORD PTR [rbp-0x8]
    524c:	b8 01 00 00 00       	mov    eax,0x1
    5251:	c9                   	leave
    5252:	c3                   	ret
    5253:	0f 1f 44 00 00       	nop    DWORD PTR [rax+rax*1+0x0]
    5258:	48 8d 3d 91 65 00 00 	lea    rdi,[rip+0x6591]        # b7f0 <error_at_line@@Base+0xa887>
    525f:	4c 89 65 f0          	mov    QWORD PTR [rbp-0x10],r12
    5263:	e8 58 b5 ff ff       	call   7c0 <getenv@plt>
    5268:	48 89 05 a1 9f 00 00 	mov    QWORD PTR [rip+0x9fa1],rax        # f210 <error_print_progname@@Base+0x128>
    526f:	49 89 c4             	mov    r12,rax
    5272:	48 89 c3             	mov    rbx,rax
    5275:	48 85 c0             	test   rax,rax
    5278:	75 11                	jne    528b <error_at_line@@Base+0x4322>
    527a:	eb 34                	jmp    52b0 <error_at_line@@Base+0x4347>
    527c:	0f 1f 40 00          	nop    DWORD PTR [rax+0x0]
    5280:	48 8d 58 11          	lea    rbx,[rax+0x11]
    5284:	48 89 1d 85 9f 00 00 	mov    QWORD PTR [rip+0x9f85],rbx        # f210 <error_print_progname@@Base+0x128>
    528b:	48 8d 35 6d 65 00 00 	lea    rsi,[rip+0x656d]        # b7ff <error_at_line@@Base+0xa896>
    5292:	48 89 df             	mov    rdi,rbx
    5295:	e8 56 b9 ff ff       	call   bf0 <strstr@plt>
    529a:	48 85 c0             	test   rax,rax
    529d:	75 e1                	jne    5280 <error_at_line@@Base+0x4317>
    529f:	49 39 dc             	cmp    r12,rbx
    52a2:	74 0c                	je     52b0 <error_at_line@@Base+0x4347>
    52a4:	0f b6 03             	movzx  eax,BYTE PTR [rbx]
    52a7:	4c 8b 65 f0          	mov    r12,QWORD PTR [rbp-0x10]
    52ab:	e9 f8 fe ff ff       	jmp    51a8 <error_at_line@@Base+0x423f>
    52b0:	48 8d 05 9a 63 00 00 	lea    rax,[rip+0x639a]        # b651 <error_at_line@@Base+0xa6e8>
    52b7:	4c 8b 65 f0          	mov    r12,QWORD PTR [rbp-0x10]
    52bb:	48 89 05 4e 9f 00 00 	mov    QWORD PTR [rip+0x9f4e],rax        # f210 <error_print_progname@@Base+0x128>
    52c2:	eb 80                	jmp    5244 <error_at_line@@Base+0x42db>
    52c4:	90                   	nop
    52c5:	66 66 2e 0f 1f 84 00 	data16 cs nop WORD PTR [rax+rax*1+0x0]
    52cc:	00 00 00 00 
    52d0:	55                   	push   rbp
    52d1:	ba 05 00 00 00       	mov    edx,0x5
    52d6:	48 89 e5             	mov    rbp,rsp
    52d9:	41 56                	push   r14
    52db:	53                   	push   rbx
    52dc:	48 89 fb             	mov    rbx,rdi
    52df:	48 83 ec 30          	sub    rsp,0x30
    52e3:	64 4c 8b 34 25 28 00 	mov    r14,QWORD PTR fs:0x28
    52ea:	00 00 
    52ec:	4c 89 75 e8          	mov    QWORD PTR [rbp-0x18],r14
    52f0:	49 89 f6             	mov    r14,rsi
    52f3:	48 89 fe             	mov    rsi,rdi
    52f6:	31 ff                	xor    edi,edi
    52f8:	e8 c3 b5 ff ff       	call   8c0 <dcgettext@plt>
    52fd:	49 89 c0             	mov    r8,rax
    5300:	48 39 c3             	cmp    rbx,rax
    5303:	74 1b                	je     5320 <error_at_line@@Base+0x43b7>
    5305:	48 8b 45 e8          	mov    rax,QWORD PTR [rbp-0x18]
    5309:	64 48 2b 04 25 28 00 	sub    rax,QWORD PTR fs:0x28
    5310:	00 00 
    5312:	75 46                	jne    535a <error_at_line@@Base+0x43f1>
    5314:	48 83 c4 30          	add    rsp,0x30
    5318:	4c 89 c0             	mov    rax,r8
    531b:	5b                   	pop    rbx
    531c:	41 5e                	pop    r14
    531e:	5d                   	pop    rbp
    531f:	c3                   	ret
    5320:	48 89 45 c8          	mov    QWORD PTR [rbp-0x38],rax
    5324:	48 8d 4d e0          	lea    rcx,[rbp-0x20]
    5328:	31 c0                	xor    eax,eax
    532a:	48 8d 7d dc          	lea    rdi,[rbp-0x24]
    532e:	ba 02 00 00 00       	mov    edx,0x2
    5333:	48 8d 35 7e 74 00 00 	lea    rsi,[rip+0x747e]        # c7b8 <error_at_line@@Base+0xb84f>
    533a:	48 89 45 e0          	mov    QWORD PTR [rbp-0x20],rax
    533e:	e8 4d b6 ff ff       	call   990 <mbrtoc32@plt>
    5343:	4c 8b 45 c8          	mov    r8,QWORD PTR [rbp-0x38]
    5347:	48 83 f8 02          	cmp    rax,0x2
    534b:	75 b8                	jne    5305 <error_at_line@@Base+0x439c>
    534d:	81 7d dc ff 07 00 00 	cmp    DWORD PTR [rbp-0x24],0x7ff
    5354:	4d 0f 44 c6          	cmove  r8,r14
    5358:	eb ab                	jmp    5305 <error_at_line@@Base+0x439c>
    535a:	e8 91 b5 ff ff       	call   8f0 <__stack_chk_fail@plt>
    535f:	90                   	nop
    5360:	55                   	push   rbp
    5361:	48 89 e5             	mov    rbp,rsp
    5364:	48 81 ec 90 00 00 00 	sub    rsp,0x90
    536b:	64 48 8b 3c 25 28 00 	mov    rdi,QWORD PTR fs:0x28
    5372:	00 00 
    5374:	48 89 7d f8          	mov    QWORD PTR [rbp-0x8],rdi
    5378:	bf 56 00 00 00       	mov    edi,0x56
    537d:	e8 9e b7 ff ff       	call   b20 <sysconf@plt>
    5382:	66 0f ef c0          	pxor   xmm0,xmm0
    5386:	bf 1e 00 00 00       	mov    edi,0x1e
    538b:	f2 48 0f 2a c0       	cvtsi2sd xmm0,rax
    5390:	f2 0f 11 85 78 ff ff 	movsd  QWORD PTR [rbp-0x88],xmm0
    5397:	ff 
    5398:	e8 83 b7 ff ff       	call   b20 <sysconf@plt>
    539d:	f2 0f 10 85 78 ff ff 	movsd  xmm0,QWORD PTR [rbp-0x88]
    53a4:	ff 
    53a5:	66 0f ef c9          	pxor   xmm1,xmm1
    53a9:	66 0f 2f c1          	comisd xmm0,xmm1
    53ad:	72 13                	jb     53c2 <error_at_line@@Base+0x4459>
    53af:	66 0f ef d2          	pxor   xmm2,xmm2
    53b3:	f2 48 0f 2a d0       	cvtsi2sd xmm2,rax
    53b8:	66 0f 2f d1          	comisd xmm2,xmm1
    53bc:	0f 83 c7 00 00 00    	jae    5489 <error_at_line@@Base+0x4520>
    53c2:	48 8d 7d 80          	lea    rdi,[rbp-0x80]
    53c6:	e8 75 b7 ff ff       	call   b40 <sysinfo@plt>
    53cb:	85 c0                	test   eax,eax
    53cd:	75 55                	jne    5424 <error_at_line@@Base+0x44bb>
    53cf:	48 8b 45 a8          	mov    rax,QWORD PTR [rbp-0x58]
    53d3:	48 85 c0             	test   rax,rax
    53d6:	0f 88 fb 00 00 00    	js     54d7 <error_at_line@@Base+0x456e>
    53dc:	66 0f ef c0          	pxor   xmm0,xmm0
    53e0:	f2 48 0f 2a c0       	cvtsi2sd xmm0,rax
    53e5:	48 8b 45 b8          	mov    rax,QWORD PTR [rbp-0x48]
    53e9:	48 85 c0             	test   rax,rax
    53ec:	0f 88 c7 00 00 00    	js     54b9 <error_at_line@@Base+0x4550>
    53f2:	66 0f ef c9          	pxor   xmm1,xmm1
    53f6:	f2 48 0f 2a c8       	cvtsi2sd xmm1,rax
    53fb:	f2 0f 58 c1          	addsd  xmm0,xmm1
    53ff:	8b 45 e8             	mov    eax,DWORD PTR [rbp-0x18]
    5402:	66 0f ef c9          	pxor   xmm1,xmm1
    5406:	f2 48 0f 2a c8       	cvtsi2sd xmm1,rax
    540b:	f2 0f 59 c1          	mulsd  xmm0,xmm1
    540f:	48 8b 45 f8          	mov    rax,QWORD PTR [rbp-0x8]
    5413:	64 48 2b 04 25 28 00 	sub    rax,QWORD PTR fs:0x28
    541a:	00 00 
    541c:	0f 85 ee 00 00 00    	jne    5510 <error_at_line@@Base+0x45a7>
    5422:	c9                   	leave
    5423:	c3                   	ret
    5424:	bf 55 00 00 00       	mov    edi,0x55
    5429:	e8 f2 b6 ff ff       	call   b20 <sysconf@plt>
    542e:	66 0f ef c0          	pxor   xmm0,xmm0
    5432:	bf 1e 00 00 00       	mov    edi,0x1e
    5437:	f2 48 0f 2a c0       	cvtsi2sd xmm0,rax
    543c:	f2 0f 11 85 78 ff ff 	movsd  QWORD PTR [rbp-0x88],xmm0
    5443:	ff 
    5444:	e8 d7 b6 ff ff       	call   b20 <sysconf@plt>
    5449:	f2 0f 10 85 78 ff ff 	movsd  xmm0,QWORD PTR [rbp-0x88]
    5450:	ff 
    5451:	66 0f ef c9          	pxor   xmm1,xmm1
    5455:	66 0f 2f c1          	comisd xmm0,xmm1
    5459:	72 0f                	jb     546a <error_at_line@@Base+0x4501>
    545b:	66 0f ef d2          	pxor   xmm2,xmm2
    545f:	f2 48 0f 2a d0       	cvtsi2sd xmm2,rax
    5464:	66 0f 2f d1          	comisd xmm2,xmm1
    5468:	73 25                	jae    548f <error_at_line@@Base+0x4526>
    546a:	48 8d 7d 80          	lea    rdi,[rbp-0x80]
    546e:	e8 cd b6 ff ff       	call   b40 <sysinfo@plt>
    5473:	85 c0                	test   eax,eax
    5475:	74 1e                	je     5495 <error_at_line@@Base+0x452c>
    5477:	f2 0f 10 05 c1 73 00 	movsd  xmm0,QWORD PTR [rip+0x73c1]        # c840 <error_at_line@@Base+0xb8d7>
    547e:	00 
    547f:	f2 0f 59 05 c1 73 00 	mulsd  xmm0,QWORD PTR [rip+0x73c1]        # c848 <error_at_line@@Base+0xb8df>
    5486:	00 
    5487:	eb 86                	jmp    540f <error_at_line@@Base+0x44a6>
    5489:	f2 0f 59 c2          	mulsd  xmm0,xmm2
    548d:	eb 80                	jmp    540f <error_at_line@@Base+0x44a6>
    548f:	f2 0f 59 c2          	mulsd  xmm0,xmm2
    5493:	eb ea                	jmp    547f <error_at_line@@Base+0x4516>
    5495:	48 8b 45 a0          	mov    rax,QWORD PTR [rbp-0x60]
    5499:	48 85 c0             	test   rax,rax
    549c:	78 57                	js     54f5 <error_at_line@@Base+0x458c>
    549e:	66 0f ef c0          	pxor   xmm0,xmm0
    54a2:	f2 48 0f 2a c0       	cvtsi2sd xmm0,rax
    54a7:	8b 45 e8             	mov    eax,DWORD PTR [rbp-0x18]
    54aa:	66 0f ef c9          	pxor   xmm1,xmm1
    54ae:	f2 48 0f 2a c8       	cvtsi2sd xmm1,rax
    54b3:	f2 0f 59 c1          	mulsd  xmm0,xmm1
    54b7:	eb c6                	jmp    547f <error_at_line@@Base+0x4516>
    54b9:	48 89 c2             	mov    rdx,rax
    54bc:	83 e0 01             	and    eax,0x1
    54bf:	66 0f ef c9          	pxor   xmm1,xmm1
    54c3:	48 d1 ea             	shr    rdx,1
    54c6:	48 09 c2             	or     rdx,rax
    54c9:	f2 48 0f 2a ca       	cvtsi2sd xmm1,rdx
    54ce:	f2 0f 58 c9          	addsd  xmm1,xmm1
    54d2:	e9 24 ff ff ff       	jmp    53fb <error_at_line@@Base+0x4492>
    54d7:	48 89 c2             	mov    rdx,rax
    54da:	83 e0 01             	and    eax,0x1
    54dd:	66 0f ef c0          	pxor   xmm0,xmm0
    54e1:	48 d1 ea             	shr    rdx,1
    54e4:	48 09 c2             	or     rdx,rax
    54e7:	f2 48 0f 2a c2       	cvtsi2sd xmm0,rdx
    54ec:	f2 0f 58 c0          	addsd  xmm0,xmm0
    54f0:	e9 f0 fe ff ff       	jmp    53e5 <error_at_line@@Base+0x447c>
    54f5:	48 89 c2             	mov    rdx,rax
    54f8:	83 e0 01             	and    eax,0x1
    54fb:	66 0f ef c0          	pxor   xmm0,xmm0
    54ff:	48 d1 ea             	shr    rdx,1
    5502:	48 09 c2             	or     rdx,rax
    5505:	f2 48 0f 2a c2       	cvtsi2sd xmm0,rdx
    550a:	f2 0f 58 c0          	addsd  xmm0,xmm0
    550e:	eb 97                	jmp    54a7 <error_at_line@@Base+0x453e>
    5510:	e8 db b3 ff ff       	call   8f0 <__stack_chk_fail@plt>
    5515:	66 66 2e 0f 1f 84 00 	data16 cs nop WORD PTR [rax+rax*1+0x0]
    551c:	00 00 00 00 
    5520:	55                   	push   rbp
    5521:	31 ff                	xor    edi,edi
    5523:	48 89 e5             	mov    rbp,rsp
    5526:	48 81 ec 20 01 00 00 	sub    rsp,0x120
    552d:	64 48 8b 34 25 28 00 	mov    rsi,QWORD PTR fs:0x28
    5534:	00 00 
    5536:	48 89 75 e8          	mov    QWORD PTR [rbp-0x18],rsi
    553a:	31 f6                	xor    esi,esi
    553c:	e8 7f b5 ff ff       	call   ac0 <setlocale@plt>
    5541:	48 85 c0             	test   rax,rax
    5544:	74 1b                	je     5561 <error_at_line@@Base+0x45f8>
    5546:	48 89 c7             	mov    rdi,rax
    5549:	48 89 5d f8          	mov    QWORD PTR [rbp-0x8],rbx
    554d:	48 89 c3             	mov    rbx,rax
    5550:	e8 8b b3 ff ff       	call   8e0 <strlen@plt>
    5555:	48 3d 00 01 00 00    	cmp    rax,0x100
    555b:	76 1b                	jbe    5578 <error_at_line@@Base+0x460f>
    555d:	48 8b 5d f8          	mov    rbx,QWORD PTR [rbp-0x8]
    5561:	31 c0                	xor    eax,eax
    5563:	48 8b 55 e8          	mov    rdx,QWORD PTR [rbp-0x18]
    5567:	64 48 2b 14 25 28 00 	sub    rdx,QWORD PTR fs:0x28
    556e:	00 00 
    5570:	75 55                	jne    55c7 <error_at_line@@Base+0x465e>
    5572:	c9                   	leave
    5573:	c3                   	ret
    5574:	0f 1f 40 00          	nop    DWORD PTR [rax+0x0]
    5578:	48 8d 50 01          	lea    rdx,[rax+0x1]
    557c:	48 89 de             	mov    rsi,rbx
    557f:	48 8d bd e0 fe ff ff 	lea    rdi,[rbp-0x120]
    5586:	e8 d5 b4 ff ff       	call   a60 <memcpy@plt>
    558b:	80 bd e0 fe ff ff 43 	cmp    BYTE PTR [rbp-0x120],0x43
    5592:	74 24                	je     55b8 <error_at_line@@Base+0x464f>
    5594:	48 8d 35 8b 62 00 00 	lea    rsi,[rip+0x628b]        # b826 <error_at_line@@Base+0xa8bd>
    559b:	48 8d bd e0 fe ff ff 	lea    rdi,[rbp-0x120]
    55a2:	e8 69 b4 ff ff       	call   a10 <strcmp@plt>
    55a7:	48 8b 5d f8          	mov    rbx,QWORD PTR [rbp-0x8]
    55ab:	85 c0                	test   eax,eax
    55ad:	0f 95 c0             	setne  al
    55b0:	eb b1                	jmp    5563 <error_at_line@@Base+0x45fa>
    55b2:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]
    55b8:	80 bd e1 fe ff ff 00 	cmp    BYTE PTR [rbp-0x11f],0x0
    55bf:	75 d3                	jne    5594 <error_at_line@@Base+0x462b>
    55c1:	48 8b 5d f8          	mov    rbx,QWORD PTR [rbp-0x8]
    55c5:	eb 9a                	jmp    5561 <error_at_line@@Base+0x45f8>
    55c7:	48 89 5d f8          	mov    QWORD PTR [rbp-0x8],rbx
    55cb:	e8 20 b3 ff ff       	call   8f0 <__stack_chk_fail@plt>
    55d0:	55                   	push   rbp
    55d1:	48 89 e5             	mov    rbp,rsp
    55d4:	41 57                	push   r15
    55d6:	41 bf 01 00 00 00    	mov    r15d,0x1
    55dc:	41 56                	push   r14
    55de:	49 89 ce             	mov    r14,rcx
    55e1:	41 55                	push   r13
    55e3:	4c 8d 2d 67 60 00 00 	lea    r13,[rip+0x6067]        # b651 <error_at_line@@Base+0xa6e8>
    55ea:	41 54                	push   r12
    55ec:	45 31 e4             	xor    r12d,r12d
    55ef:	53                   	push   rbx
    55f0:	48 83 ec 08          	sub    rsp,0x8
    55f4:	48 85 f6             	test   rsi,rsi
    55f7:	4c 0f 45 e7          	cmovne r12,rdi
    55fb:	4c 0f 45 fa          	cmovne r15,rdx
    55ff:	4c 0f 45 ee          	cmovne r13,rsi
    5603:	4c 89 fa             	mov    rdx,r15
    5606:	4c 89 ee             	mov    rsi,r13
    5609:	4c 89 e7             	mov    rdi,r12
    560c:	e8 7f b3 ff ff       	call   990 <mbrtoc32@plt>
    5611:	48 89 c3             	mov    rbx,rax
    5614:	48 83 f8 fc          	cmp    rax,0xfffffffffffffffc
    5618:	77 26                	ja     5640 <error_at_line@@Base+0x46d7>
    561a:	4c 89 f7             	mov    rdi,r14
    561d:	e8 7e b5 ff ff       	call   ba0 <mbsinit@plt>
    5622:	85 c0                	test   eax,eax
    5624:	74 4a                	je     5670 <error_at_line@@Base+0x4707>
    5626:	48 83 c4 08          	add    rsp,0x8
    562a:	48 89 d8             	mov    rax,rbx
    562d:	5b                   	pop    rbx
    562e:	41 5c                	pop    r12
    5630:	41 5d                	pop    r13
    5632:	41 5e                	pop    r14
    5634:	41 5f                	pop    r15
    5636:	5d                   	pop    rbp
    5637:	c3                   	ret
    5638:	0f 1f 84 00 00 00 00 	nop    DWORD PTR [rax+rax*1+0x0]
    563f:	00 
    5640:	48 83 f8 fd          	cmp    rax,0xfffffffffffffffd
    5644:	0f 84 19 b7 ff ff    	je     d63 <__ctype_b_loc@plt+0x163>
    564a:	4d 85 ff             	test   r15,r15
    564d:	74 d7                	je     5626 <error_at_line@@Base+0x46bd>
    564f:	e8 cc fe ff ff       	call   5520 <error_at_line@@Base+0x45b7>
    5654:	84 c0                	test   al,al
    5656:	75 ce                	jne    5626 <error_at_line@@Base+0x46bd>
    5658:	4d 85 e4             	test   r12,r12
    565b:	74 09                	je     5666 <error_at_line@@Base+0x46fd>
    565d:	41 0f b6 45 00       	movzx  eax,BYTE PTR [r13+0x0]
    5662:	41 89 04 24          	mov    DWORD PTR [r12],eax
    5666:	bb 01 00 00 00       	mov    ebx,0x1
    566b:	eb b9                	jmp    5626 <error_at_line@@Base+0x46bd>
    566d:	0f 1f 00             	nop    DWORD PTR [rax]
    5670:	49 c7 06 00 00 00 00 	mov    QWORD PTR [r14],0x0
    5677:	eb ad                	jmp    5626 <error_at_line@@Base+0x46bd>
    5679:	0f 1f 80 00 00 00 00 	nop    DWORD PTR [rax+0x0]
    5680:	55                   	push   rbp
    5681:	ba 05 00 00 00       	mov    edx,0x5
    5686:	48 89 e5             	mov    rbp,rsp
    5689:	41 56                	push   r14
    568b:	53                   	push   rbx
    568c:	48 89 fb             	mov    rbx,rdi
    568f:	48 83 ec 30          	sub    rsp,0x30
    5693:	64 4c 8b 34 25 28 00 	mov    r14,QWORD PTR fs:0x28
    569a:	00 00 
    569c:	4c 89 75 e8          	mov    QWORD PTR [rbp-0x18],r14
    56a0:	41 89 f6             	mov    r14d,esi
    56a3:	48 89 fe             	mov    rsi,rdi
    56a6:	48 8d 3d 02 60 00 00 	lea    rdi,[rip+0x6002]        # b6af <error_at_line@@Base+0xa746>
    56ad:	e8 0e b2 ff ff       	call   8c0 <dcgettext@plt>
    56b2:	49 89 c0             	mov    r8,rax
    56b5:	48 39 c3             	cmp    rbx,rax
    56b8:	74 1e                	je     56d8 <error_at_line@@Base+0x476f>
    56ba:	48 8b 45 e8          	mov    rax,QWORD PTR [rbp-0x18]
    56be:	64 48 2b 04 25 28 00 	sub    rax,QWORD PTR fs:0x28
    56c5:	00 00 
    56c7:	75 79                	jne    5742 <error_at_line@@Base+0x47d9>
    56c9:	48 83 c4 30          	add    rsp,0x30
    56cd:	4c 89 c0             	mov    rax,r8
    56d0:	5b                   	pop    rbx
    56d1:	41 5e                	pop    r14
    56d3:	5d                   	pop    rbp
    56d4:	c3                   	ret
    56d5:	0f 1f 00             	nop    DWORD PTR [rax]
    56d8:	48 8d 4d e0          	lea    rcx,[rbp-0x20]
    56dc:	48 8d 7d dc          	lea    rdi,[rbp-0x24]
    56e0:	ba 03 00 00 00       	mov    edx,0x3
    56e5:	48 89 45 c8          	mov    QWORD PTR [rbp-0x38],rax
    56e9:	48 8d 35 c0 70 00 00 	lea    rsi,[rip+0x70c0]        # c7b0 <error_at_line@@Base+0xb847>
    56f0:	48 c7 45 e0 00 00 00 	mov    QWORD PTR [rbp-0x20],0x0
    56f7:	00 
    56f8:	e8 d3 fe ff ff       	call   55d0 <error_at_line@@Base+0x4667>
    56fd:	4c 8b 45 c8          	mov    r8,QWORD PTR [rbp-0x38]
    5701:	48 83 f8 03          	cmp    rax,0x3
    5705:	74 19                	je     5720 <error_at_line@@Base+0x47b7>
    5707:	4c 8d 05 20 61 00 00 	lea    r8,[rip+0x6120]        # b82e <error_at_line@@Base+0xa8c5>
    570e:	41 83 fe 09          	cmp    r14d,0x9
    5712:	48 8d 05 13 61 00 00 	lea    rax,[rip+0x6113]        # b82c <error_at_line@@Base+0xa8c3>
    5719:	4c 0f 44 c0          	cmove  r8,rax
    571d:	eb 9b                	jmp    56ba <error_at_line@@Base+0x4751>
    571f:	90                   	nop
    5720:	81 7d dc 18 20 00 00 	cmp    DWORD PTR [rbp-0x24],0x2018
    5727:	75 de                	jne    5707 <error_at_line@@Base+0x479e>
    5729:	31 c0                	xor    eax,eax
    572b:	41 80 38 27          	cmp    BYTE PTR [r8],0x27
    572f:	48 8d 0d 7a 70 00 00 	lea    rcx,[rip+0x707a]        # c7b0 <error_at_line@@Base+0xb847>
    5736:	0f 94 c0             	sete   al
    5739:	4c 8d 04 81          	lea    r8,[rcx+rax*4]
    573d:	e9 78 ff ff ff       	jmp    56ba <error_at_line@@Base+0x4751>
    5742:	e8 a9 b1 ff ff       	call   8f0 <__stack_chk_fail@plt>
    5747:	66 0f 1f 84 00 00 00 	nop    WORD PTR [rax+rax*1+0x0]
    574e:	00 00 
    5750:	55                   	push   rbp
    5751:	49 89 fb             	mov    r11,rdi
    5754:	48 89 e5             	mov    rbp,rsp
    5757:	41 57                	push   r15
    5759:	49 c7 c7 ff ff ff ff 	mov    r15,0xffffffffffffffff
    5760:	41 56                	push   r14
    5762:	41 55                	push   r13
    5764:	41 54                	push   r12
    5766:	53                   	push   rbx
    5767:	48 81 ec b8 00 00 00 	sub    rsp,0xb8
    576e:	48 89 55 a8          	mov    QWORD PTR [rbp-0x58],rdx
    5772:	4c 8b 6d 10          	mov    r13,QWORD PTR [rbp+0x10]
    5776:	89 4d 84             	mov    DWORD PTR [rbp-0x7c],ecx
    5779:	44 89 85 4c ff ff ff 	mov    DWORD PTR [rbp-0xb4],r8d
    5780:	4c 89 4d 90          	mov    QWORD PTR [rbp-0x70],r9
    5784:	64 4c 8b 34 25 28 00 	mov    r14,QWORD PTR fs:0x28
    578b:	00 00 
    578d:	4c 89 75 c8          	mov    QWORD PTR [rbp-0x38],r14
    5791:	4c 8b 75 18          	mov    r14,QWORD PTR [rbp+0x18]
    5795:	4c 89 ad 28 ff ff ff 	mov    QWORD PTR [rbp-0xd8],r13
    579c:	4c 89 b5 30 ff ff ff 	mov    QWORD PTR [rbp-0xd0],r14
    57a3:	49 89 f6             	mov    r14,rsi
    57a6:	66 2e 0f 1f 84 00 00 	cs nop WORD PTR [rax+rax*1+0x0]
    57ad:	00 00 00 
    57b0:	4c 89 5d a0          	mov    QWORD PTR [rbp-0x60],r11
    57b4:	e8 17 b1 ff ff       	call   8d0 <__ctype_get_mb_cur_max@plt>
    57b9:	8b 95 4c ff ff ff    	mov    edx,DWORD PTR [rbp-0xb4]
    57bf:	c6 45 9d 01          	mov    BYTE PTR [rbp-0x63],0x1
    57c3:	4d 89 f8             	mov    r8,r15
    57c6:	48 89 85 50 ff ff ff 	mov    QWORD PTR [rbp-0xb0],rax
    57cd:	4c 8b 7d a0          	mov    r15,QWORD PTR [rbp-0x60]
    57d1:	d1 ea                	shr    edx,1
    57d3:	c6 45 82 00          	mov    BYTE PTR [rbp-0x7e],0x0
    57d7:	89 d0                	mov    eax,edx
    57d9:	c6 45 9b 00          	mov    BYTE PTR [rbp-0x65],0x0
    57dd:	83 e0 01             	and    eax,0x1
    57e0:	48 c7 45 88 00 00 00 	mov    QWORD PTR [rbp-0x78],0x0
    57e7:	00 
    57e8:	88 45 9f             	mov    BYTE PTR [rbp-0x61],al
    57eb:	48 c7 85 60 ff ff ff 	mov    QWORD PTR [rbp-0xa0],0x0
    57f2:	00 00 00 00 
    57f6:	48 c7 85 58 ff ff ff 	mov    QWORD PTR [rbp-0xa8],0x0
    57fd:	00 00 00 00 
    5801:	8b 45 84             	mov    eax,DWORD PTR [rbp-0x7c]
    5804:	83 f8 0a             	cmp    eax,0xa
    5807:	0f 87 5b b5 ff ff    	ja     d68 <__ctype_b_loc@plt+0x168>
    580d:	48 8d 35 94 6b 00 00 	lea    rsi,[rip+0x6b94]        # c3a8 <error_at_line@@Base+0xb43f>
    5814:	48 63 04 86          	movsxd rax,DWORD PTR [rsi+rax*4]
    5818:	48 01 f0             	add    rax,rsi
    581b:	3e ff e0             	notrack jmp rax
    581e:	66 90                	xchg   ax,ax
    5820:	8b 5d 84             	mov    ebx,DWORD PTR [rbp-0x7c]
    5823:	83 fb 0a             	cmp    ebx,0xa
    5826:	74 32                	je     585a <error_at_line@@Base+0x48f1>
    5828:	89 de                	mov    esi,ebx
    582a:	48 8d 3d ff 5f 00 00 	lea    rdi,[rip+0x5fff]        # b830 <error_at_line@@Base+0xa8c7>
    5831:	4c 89 45 a0          	mov    QWORD PTR [rbp-0x60],r8
    5835:	e8 46 fe ff ff       	call   5680 <error_at_line@@Base+0x4717>
    583a:	89 de                	mov    esi,ebx
    583c:	48 8d 3d eb 5f 00 00 	lea    rdi,[rip+0x5feb]        # b82e <error_at_line@@Base+0xa8c5>
    5843:	48 89 85 28 ff ff ff 	mov    QWORD PTR [rbp-0xd8],rax
    584a:	e8 31 fe ff ff       	call   5680 <error_at_line@@Base+0x4717>
    584f:	4c 8b 45 a0          	mov    r8,QWORD PTR [rbp-0x60]
    5853:	48 89 85 30 ff ff ff 	mov    QWORD PTR [rbp-0xd0],rax
    585a:	80 7d 9f 00          	cmp    BYTE PTR [rbp-0x61],0x0
    585e:	0f 84 fc 06 00 00    	je     5f60 <error_at_line@@Base+0x4ff7>
    5864:	31 db                	xor    ebx,ebx
    5866:	4c 8b ad 30 ff ff ff 	mov    r13,QWORD PTR [rbp-0xd0]
    586d:	4c 89 45 a0          	mov    QWORD PTR [rbp-0x60],r8
    5871:	4c 89 ef             	mov    rdi,r13
    5874:	e8 67 b0 ff ff       	call   8e0 <strlen@plt>
    5879:	4c 89 ad 60 ff ff ff 	mov    QWORD PTR [rbp-0xa0],r13
    5880:	4c 8b 45 a0          	mov    r8,QWORD PTR [rbp-0x60]
    5884:	48 83 f8 01          	cmp    rax,0x1
    5888:	48 89 45 88          	mov    QWORD PTR [rbp-0x78],rax
    588c:	0f 95 45 83          	setne  BYTE PTR [rbp-0x7d]
    5890:	48 85 c0             	test   rax,rax
    5893:	c6 45 9a 00          	mov    BYTE PTR [rbp-0x66],0x0
    5897:	c6 45 99 00          	mov    BYTE PTR [rbp-0x67],0x0
    589b:	c6 45 9c 00          	mov    BYTE PTR [rbp-0x64],0x0
    589f:	c6 45 81 01          	mov    BYTE PTR [rbp-0x7f],0x1
    58a3:	c6 45 9b 01          	mov    BYTE PTR [rbp-0x65],0x1
    58a7:	0f 95 45 9e          	setne  BYTE PTR [rbp-0x62]
    58ab:	eb 33                	jmp    58e0 <error_at_line@@Base+0x4977>
    58ad:	48 8b 45 88          	mov    rax,QWORD PTR [rbp-0x78]
    58b1:	c6 45 9a 00          	mov    BYTE PTR [rbp-0x66],0x0
    58b5:	c6 45 99 00          	mov    BYTE PTR [rbp-0x67],0x0
    58b9:	48 83 f8 01          	cmp    rax,0x1
    58bd:	c6 45 9c 00          	mov    BYTE PTR [rbp-0x64],0x0
    58c1:	c6 45 81 01          	mov    BYTE PTR [rbp-0x7f],0x1
    58c5:	c6 45 9f 00          	mov    BYTE PTR [rbp-0x61],0x0
    58c9:	c6 45 9b 01          	mov    BYTE PTR [rbp-0x65],0x1
    58cd:	0f 95 45 83          	setne  BYTE PTR [rbp-0x7d]
    58d1:	48 85 c0             	test   rax,rax
    58d4:	0f 95 45 9e          	setne  BYTE PTR [rbp-0x62]
    58d8:	31 db                	xor    ebx,ebx
    58da:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]
    58e0:	45 31 ed             	xor    r13d,r13d
    58e3:	45 31 db             	xor    r11d,r11d
    58e6:	4d 39 c5             	cmp    r13,r8
    58e9:	41 0f 95 c2          	setne  r10b
    58ed:	49 83 f8 ff          	cmp    r8,0xffffffffffffffff
    58f1:	0f 84 8d 01 00 00    	je     5a84 <error_at_line@@Base+0x4b1b>
    58f7:	66 0f 1f 84 00 00 00 	nop    WORD PTR [rax+rax*1+0x0]
    58fe:	00 00 
    5900:	45 84 d2             	test   r10b,r10b
    5903:	0f 84 98 01 00 00    	je     5aa1 <error_at_line@@Base+0x4b38>
    5909:	48 8b 45 a8          	mov    rax,QWORD PTR [rbp-0x58]
    590d:	4e 8d 0c 28          	lea    r9,[rax+r13*1]
    5911:	80 7d 9e 00          	cmp    BYTE PTR [rbp-0x62],0x0
    5915:	0f 85 85 06 00 00    	jne    5fa0 <error_at_line@@Base+0x5037>
    591b:	45 0f b6 21          	movzx  r12d,BYTE PTR [r9]
    591f:	41 80 fc 23          	cmp    r12b,0x23
    5923:	0f 8f 77 03 00 00    	jg     5ca0 <error_at_line@@Base+0x4d37>
    5929:	45 84 e4             	test   r12b,r12b
    592c:	78 32                	js     5960 <error_at_line@@Base+0x49f7>
    592e:	41 80 fc 23          	cmp    r12b,0x23
    5932:	77 2c                	ja     5960 <error_at_line@@Base+0x49f7>
    5934:	48 8d 3d 99 6a 00 00 	lea    rdi,[rip+0x6a99]        # c3d4 <error_at_line@@Base+0xb46b>
    593b:	41 0f b6 c4          	movzx  eax,r12b
    593f:	48 63 04 87          	movsxd rax,DWORD PTR [rdi+rax*4]
    5943:	48 01 f8             	add    rax,rdi
    5946:	3e ff e0             	notrack jmp rax
    5949:	0f 1f 80 00 00 00 00 	nop    DWORD PTR [rax+0x0]
    5950:	c6 45 a0 00          	mov    BYTE PTR [rbp-0x60],0x0
    5954:	41 80 fc 7e          	cmp    r12b,0x7e
    5958:	0f 84 ec 03 00 00    	je     5d4a <error_at_line@@Base+0x4de1>
    595e:	66 90                	xchg   ax,ax
    5960:	c6 45 a0 00          	mov    BYTE PTR [rbp-0x60],0x0
    5964:	48 83 bd 50 ff ff ff 	cmp    QWORD PTR [rbp-0xb0],0x1
    596b:	01 
    596c:	0f 85 23 07 00 00    	jne    6095 <error_at_line@@Base+0x512c>
    5972:	44 88 9d 68 ff ff ff 	mov    BYTE PTR [rbp-0x98],r11b
    5979:	4c 89 85 70 ff ff ff 	mov    QWORD PTR [rbp-0x90],r8
    5980:	44 88 95 78 ff ff ff 	mov    BYTE PTR [rbp-0x88],r10b
    5987:	e8 74 b2 ff ff       	call   c00 <__ctype_b_loc@plt>
    598c:	44 0f b6 95 78 ff ff 	movzx  r10d,BYTE PTR [rbp-0x88]
    5993:	ff 
    5994:	b9 01 00 00 00       	mov    ecx,0x1
    5999:	4c 8b 85 70 ff ff ff 	mov    r8,QWORD PTR [rbp-0x90]
    59a0:	48 89 c2             	mov    rdx,rax
    59a3:	41 0f b6 c4          	movzx  eax,r12b
    59a7:	44 0f b6 9d 68 ff ff 	movzx  r11d,BYTE PTR [rbp-0x98]
    59ae:	ff 
    59af:	48 8b 12             	mov    rdx,QWORD PTR [rdx]
    59b2:	0f b7 14 42          	movzx  edx,WORD PTR [rdx+rax*2]
    59b6:	66 81 e2 00 40       	and    dx,0x4000
    59bb:	66 c1 ea 0e          	shr    dx,0xe
    59bf:	89 d0                	mov    eax,edx
    59c1:	83 f0 01             	xor    eax,0x1
    59c4:	22 45 9b             	and    al,BYTE PTR [rbp-0x65]
    59c7:	84 c0                	test   al,al
    59c9:	0f 85 e9 0e 00 00    	jne    68b8 <error_at_line@@Base+0x594f>
    59cf:	90                   	nop
    59d0:	80 7d 9a 00          	cmp    BYTE PTR [rbp-0x66],0x0
    59d4:	0f 85 c7 01 00 00    	jne    5ba1 <error_at_line@@Base+0x4c38>
    59da:	48 83 7d 90 00       	cmp    QWORD PTR [rbp-0x70],0x0
    59df:	0f 84 1b 01 00 00    	je     5b00 <error_at_line@@Base+0x4b97>
    59e5:	44 89 e0             	mov    eax,r12d
    59e8:	48 8b 75 90          	mov    rsi,QWORD PTR [rbp-0x70]
    59ec:	44 89 e1             	mov    ecx,r12d
    59ef:	c0 e8 05             	shr    al,0x5
    59f2:	83 e1 1f             	and    ecx,0x1f
    59f5:	0f b6 c0             	movzx  eax,al
    59f8:	48 c1 e0 02          	shl    rax,0x2
    59fc:	8b 04 06             	mov    eax,DWORD PTR [rsi+rax*1]
    59ff:	0f a3 c8             	bt     eax,ecx
    5a02:	0f 83 f8 00 00 00    	jae    5b00 <error_at_line@@Base+0x4b97>
    5a08:	80 7d 9f 00          	cmp    BYTE PTR [rbp-0x61],0x0
    5a0c:	0f 85 6e 0a 00 00    	jne    6480 <error_at_line@@Base+0x5517>
    5a12:	49 8d 4d 01          	lea    rcx,[r13+0x1]
    5a16:	20 55 9d             	and    BYTE PTR [rbp-0x63],dl
    5a19:	44 89 d8             	mov    eax,r11d
    5a1c:	49 89 cd             	mov    r13,rcx
    5a1f:	83 f0 01             	xor    eax,0x1
    5a22:	22 45 9c             	and    al,BYTE PTR [rbp-0x64]
    5a25:	84 c0                	test   al,al
    5a27:	74 2f                	je     5a58 <error_at_line@@Base+0x4aef>
    5a29:	4c 39 f3             	cmp    rbx,r14
    5a2c:	73 05                	jae    5a33 <error_at_line@@Base+0x4aca>
    5a2e:	41 c6 04 1f 27       	mov    BYTE PTR [r15+rbx*1],0x27
    5a33:	48 8d 43 01          	lea    rax,[rbx+0x1]
    5a37:	4c 39 f0             	cmp    rax,r14
    5a3a:	73 06                	jae    5a42 <error_at_line@@Base+0x4ad9>
    5a3c:	41 c6 44 1f 01 24    	mov    BYTE PTR [r15+rbx*1+0x1],0x24
    5a42:	48 8d 43 02          	lea    rax,[rbx+0x2]
    5a46:	4c 39 f0             	cmp    rax,r14
    5a49:	73 06                	jae    5a51 <error_at_line@@Base+0x4ae8>
    5a4b:	41 c6 44 1f 02 27    	mov    BYTE PTR [r15+rbx*1+0x2],0x27
    5a51:	48 83 c3 03          	add    rbx,0x3
    5a55:	45 89 d3             	mov    r11d,r10d
    5a58:	4c 39 f3             	cmp    rbx,r14
    5a5b:	73 05                	jae    5a62 <error_at_line@@Base+0x4af9>
    5a5d:	41 c6 04 1f 5c       	mov    BYTE PTR [r15+rbx*1],0x5c
    5a62:	48 83 c3 01          	add    rbx,0x1
    5a66:	4c 39 f3             	cmp    rbx,r14
    5a69:	73 04                	jae    5a6f <error_at_line@@Base+0x4b06>
    5a6b:	45 88 24 1f          	mov    BYTE PTR [r15+rbx*1],r12b
    5a6f:	48 83 c3 01          	add    rbx,0x1
    5a73:	4d 39 c5             	cmp    r13,r8
    5a76:	41 0f 95 c2          	setne  r10b
    5a7a:	49 83 f8 ff          	cmp    r8,0xffffffffffffffff
    5a7e:	0f 85 7c fe ff ff    	jne    5900 <error_at_line@@Base+0x4997>
    5a84:	48 8b 45 a8          	mov    rax,QWORD PTR [rbp-0x58]
    5a88:	49 c7 c0 ff ff ff ff 	mov    r8,0xffffffffffffffff
    5a8f:	42 80 3c 28 00       	cmp    BYTE PTR [rax+r13*1],0x0
    5a94:	41 0f 95 c2          	setne  r10b
    5a98:	45 84 d2             	test   r10b,r10b
    5a9b:	0f 85 68 fe ff ff    	jne    5909 <error_at_line@@Base+0x49a0>
    5aa1:	48 85 db             	test   rbx,rbx
    5aa4:	0f 85 d6 0f 00 00    	jne    6a80 <error_at_line@@Base+0x5b17>
    5aaa:	80 7d 9c 00          	cmp    BYTE PTR [rbp-0x64],0x0
    5aae:	0f 84 cc 0f 00 00    	je     6a80 <error_at_line@@Base+0x5b17>
    5ab4:	80 7d 9f 00          	cmp    BYTE PTR [rbp-0x61],0x0
    5ab8:	0f 85 a2 00 00 00    	jne    5b60 <error_at_line@@Base+0x4bf7>
    5abe:	80 7d 82 00          	cmp    BYTE PTR [rbp-0x7e],0x0
    5ac2:	0f 84 e6 15 00 00    	je     70ae <error_at_line@@Base+0x6145>
    5ac8:	80 7d 9d 00          	cmp    BYTE PTR [rbp-0x63],0x0
    5acc:	0f 85 c3 15 00 00    	jne    7095 <error_at_line@@Base+0x612c>
    5ad2:	4d 85 f6             	test   r14,r14
    5ad5:	0f 94 c0             	sete   al
    5ad8:	48 83 bd 58 ff ff ff 	cmp    QWORD PTR [rbp-0xa8],0x0
    5adf:	00 
    5ae0:	0f 95 c2             	setne  dl
    5ae3:	20 d0                	and    al,dl
    5ae5:	0f 84 98 15 00 00    	je     7083 <error_at_line@@Base+0x611a>
    5aeb:	88 45 82             	mov    BYTE PTR [rbp-0x7e],al
    5aee:	4c 8b b5 58 ff ff ff 	mov    r14,QWORD PTR [rbp-0xa8]
    5af5:	c6 45 9f 00          	mov    BYTE PTR [rbp-0x61],0x0
    5af9:	e9 03 fd ff ff       	jmp    5801 <error_at_line@@Base+0x4898>
    5afe:	66 90                	xchg   ax,ax
    5b00:	31 c0                	xor    eax,eax
    5b02:	80 7d a0 00          	cmp    BYTE PTR [rbp-0x60],0x0
    5b06:	0f 85 fc fe ff ff    	jne    5a08 <error_at_line@@Base+0x4a9f>
    5b0c:	20 55 9d             	and    BYTE PTR [rbp-0x63],dl
    5b0f:	83 f0 01             	xor    eax,0x1
    5b12:	49 83 c5 01          	add    r13,0x1
    5b16:	44 21 d8             	and    eax,r11d
    5b19:	84 c0                	test   al,al
    5b1b:	0f 84 45 ff ff ff    	je     5a66 <error_at_line@@Base+0x4afd>
    5b21:	4c 39 f3             	cmp    rbx,r14
    5b24:	73 05                	jae    5b2b <error_at_line@@Base+0x4bc2>
    5b26:	41 c6 04 1f 27       	mov    BYTE PTR [r15+rbx*1],0x27
    5b2b:	48 8d 43 01          	lea    rax,[rbx+0x1]
    5b2f:	4c 39 f0             	cmp    rax,r14
    5b32:	73 06                	jae    5b3a <error_at_line@@Base+0x4bd1>
    5b34:	41 c6 44 1f 01 27    	mov    BYTE PTR [r15+rbx*1+0x1],0x27
    5b3a:	48 83 c3 02          	add    rbx,0x2
    5b3e:	45 31 db             	xor    r11d,r11d
    5b41:	e9 20 ff ff ff       	jmp    5a66 <error_at_line@@Base+0x4afd>
    5b46:	66 2e 0f 1f 84 00 00 	cs nop WORD PTR [rax+rax*1+0x0]
    5b4d:	00 00 00 
    5b50:	c6 45 a0 00          	mov    BYTE PTR [rbp-0x60],0x0
    5b54:	31 d2                	xor    edx,edx
    5b56:	80 7d 99 00          	cmp    BYTE PTR [rbp-0x67],0x0
    5b5a:	0f 84 70 fe ff ff    	je     59d0 <error_at_line@@Base+0x4a67>
    5b60:	0f b6 45 9b          	movzx  eax,BYTE PTR [rbp-0x65]
    5b64:	4d 89 fb             	mov    r11,r15
    5b67:	c7 45 84 02 00 00 00 	mov    DWORD PTR [rbp-0x7c],0x2
    5b6e:	4d 89 c7             	mov    r15,r8
    5b71:	88 45 9c             	mov    BYTE PTR [rbp-0x64],al
    5b74:	eb 59                	jmp    5bcf <error_at_line@@Base+0x4c66>
    5b76:	66 2e 0f 1f 84 00 00 	cs nop WORD PTR [rax+rax*1+0x0]
    5b7d:	00 00 00 
    5b80:	41 bc 0a 00 00 00    	mov    r12d,0xa
    5b86:	b8 6e 00 00 00       	mov    eax,0x6e
    5b8b:	80 7d 99 00          	cmp    BYTE PTR [rbp-0x67],0x0
    5b8f:	75 cf                	jne    5b60 <error_at_line@@Base+0x4bf7>
    5b91:	80 7d 9b 00          	cmp    BYTE PTR [rbp-0x65],0x0
    5b95:	0f 85 05 0a 00 00    	jne    65a0 <error_at_line@@Base+0x5637>
    5b9b:	c6 45 a0 00          	mov    BYTE PTR [rbp-0x60],0x0
    5b9f:	31 d2                	xor    edx,edx
    5ba1:	31 c0                	xor    eax,eax
    5ba3:	80 7d 9f 00          	cmp    BYTE PTR [rbp-0x61],0x0
    5ba7:	0f 84 73 06 00 00    	je     6220 <error_at_line@@Base+0x52b7>
    5bad:	48 83 7d 90 00       	cmp    QWORD PTR [rbp-0x70],0x0
    5bb2:	0f 85 2d fe ff ff    	jne    59e5 <error_at_line@@Base+0x4a7c>
    5bb8:	80 7d a0 00          	cmp    BYTE PTR [rbp-0x60],0x0
    5bbc:	0f 84 1e 0c 00 00    	je     67e0 <error_at_line@@Base+0x5877>
    5bc2:	0f b6 55 9b          	movzx  edx,BYTE PTR [rbp-0x65]
    5bc6:	20 55 9c             	and    BYTE PTR [rbp-0x64],dl
    5bc9:	4d 89 fb             	mov    r11,r15
    5bcc:	4d 89 c7             	mov    r15,r8
    5bcf:	80 7d 9c 00          	cmp    BYTE PTR [rbp-0x64],0x0
    5bd3:	b8 04 00 00 00       	mov    eax,0x4
    5bd8:	0f 44 45 84          	cmove  eax,DWORD PTR [rbp-0x7c]
    5bdc:	89 45 84             	mov    DWORD PTR [rbp-0x7c],eax
    5bdf:	83 a5 4c ff ff ff fd 	and    DWORD PTR [rbp-0xb4],0xfffffffd
    5be6:	48 c7 45 90 00 00 00 	mov    QWORD PTR [rbp-0x70],0x0
    5bed:	00 
    5bee:	e9 bd fb ff ff       	jmp    57b0 <error_at_line@@Base+0x4847>
    5bf3:	0f 1f 44 00 00       	nop    DWORD PTR [rax+rax*1+0x0]
    5bf8:	80 7d 9b 00          	cmp    BYTE PTR [rbp-0x65],0x0
    5bfc:	0f 85 3e 0e 00 00    	jne    6a40 <error_at_line@@Base+0x5ad7>
    5c02:	80 7d 9f 00          	cmp    BYTE PTR [rbp-0x61],0x0
    5c06:	0f 84 8c 0c 00 00    	je     6898 <error_at_line@@Base+0x592f>
    5c0c:	48 83 7d 90 00       	cmp    QWORD PTR [rbp-0x70],0x0
    5c11:	0f 84 c1 0b 00 00    	je     67d8 <error_at_line@@Base+0x586f>
    5c17:	c6 45 a0 00          	mov    BYTE PTR [rbp-0x60],0x0
    5c1b:	31 d2                	xor    edx,edx
    5c1d:	41 bc 0b 00 00 00    	mov    r12d,0xb
    5c23:	e9 bd fd ff ff       	jmp    59e5 <error_at_line@@Base+0x4a7c>
    5c28:	0f 1f 84 00 00 00 00 	nop    DWORD PTR [rax+rax*1+0x0]
    5c2f:	00 
    5c30:	80 7d 9b 00          	cmp    BYTE PTR [rbp-0x65],0x0
    5c34:	0f 85 16 0e 00 00    	jne    6a50 <error_at_line@@Base+0x5ae7>
    5c3a:	80 7d 9f 00          	cmp    BYTE PTR [rbp-0x61],0x0
    5c3e:	0f 84 14 0c 00 00    	je     6858 <error_at_line@@Base+0x58ef>
    5c44:	48 83 7d 90 00       	cmp    QWORD PTR [rbp-0x70],0x0
    5c49:	0f 84 ba 0f 00 00    	je     6c09 <error_at_line@@Base+0x5ca0>
    5c4f:	c6 45 a0 00          	mov    BYTE PTR [rbp-0x60],0x0
    5c53:	31 d2                	xor    edx,edx
    5c55:	41 bc 08 00 00 00    	mov    r12d,0x8
    5c5b:	e9 85 fd ff ff       	jmp    59e5 <error_at_line@@Base+0x4a7c>
    5c60:	80 7d 9b 00          	cmp    BYTE PTR [rbp-0x65],0x0
    5c64:	0f 85 76 07 00 00    	jne    63e0 <error_at_line@@Base+0x5477>
    5c6a:	49 83 c5 01          	add    r13,0x1
    5c6e:	49 83 f8 ff          	cmp    r8,0xffffffffffffffff
    5c72:	0f 84 0c fe ff ff    	je     5a84 <error_at_line@@Base+0x4b1b>
    5c78:	4d 39 c5             	cmp    r13,r8
    5c7b:	0f 84 20 fe ff ff    	je     5aa1 <error_at_line@@Base+0x4b38>
    5c81:	48 8b 45 a8          	mov    rax,QWORD PTR [rbp-0x58]
    5c85:	4e 8d 0c 28          	lea    r9,[rax+r13*1]
    5c89:	45 0f b6 21          	movzx  r12d,BYTE PTR [r9]
    5c8d:	41 80 fc 23          	cmp    r12b,0x23
    5c91:	0f 8e 92 fc ff ff    	jle    5929 <error_at_line@@Base+0x49c0>
    5c97:	66 0f 1f 84 00 00 00 	nop    WORD PTR [rax+rax*1+0x0]
    5c9e:	00 00 
    5ca0:	41 80 fc 7a          	cmp    r12b,0x7a
    5ca4:	0f 8f b6 08 00 00    	jg     6560 <error_at_line@@Base+0x55f7>
    5caa:	41 80 fc 40          	cmp    r12b,0x40
    5cae:	0f 8f 4c 08 00 00    	jg     6500 <error_at_line@@Base+0x5597>
    5cb4:	41 80 fc 3e          	cmp    r12b,0x3e
    5cb8:	0f 8f 52 09 00 00    	jg     6610 <error_at_line@@Base+0x56a7>
    5cbe:	41 8d 4c 24 dc       	lea    ecx,[r12-0x24]
    5cc3:	b8 01 00 00 00       	mov    eax,0x1
    5cc8:	48 d3 e0             	shl    rax,cl
    5ccb:	a9 82 ff 7f 00       	test   eax,0x7fff82
    5cd0:	0f 85 fa 09 00 00    	jne    66d0 <error_at_line@@Base+0x5767>
    5cd6:	a9 75 00 80 07       	test   eax,0x7800075
    5cdb:	0f 85 6f fe ff ff    	jne    5b50 <error_at_line@@Base+0x4be7>
    5ce1:	83 7d 84 02          	cmp    DWORD PTR [rbp-0x7c],0x2
    5ce5:	0f 84 05 0b 00 00    	je     67f0 <error_at_line@@Base+0x5887>
    5ceb:	44 88 55 82          	mov    BYTE PTR [rbp-0x7e],r10b
    5cef:	44 89 d2             	mov    edx,r10d
    5cf2:	41 bc 27 00 00 00    	mov    r12d,0x27
    5cf8:	c6 45 a0 00          	mov    BYTE PTR [rbp-0x60],0x0
    5cfc:	e9 cf fc ff ff       	jmp    59d0 <error_at_line@@Base+0x4a67>
    5d01:	0f 1f 80 00 00 00 00 	nop    DWORD PTR [rax+0x0]
    5d08:	80 7d 9b 00          	cmp    BYTE PTR [rbp-0x65],0x0
    5d0c:	0f 85 4e 0d 00 00    	jne    6a60 <error_at_line@@Base+0x5af7>
    5d12:	80 7d 9f 00          	cmp    BYTE PTR [rbp-0x61],0x0
    5d16:	0f 84 5c 0b 00 00    	je     6878 <error_at_line@@Base+0x590f>
    5d1c:	48 83 7d 90 00       	cmp    QWORD PTR [rbp-0x70],0x0
    5d21:	0f 84 f9 0e 00 00    	je     6c20 <error_at_line@@Base+0x5cb7>
    5d27:	c6 45 a0 00          	mov    BYTE PTR [rbp-0x60],0x0
    5d2b:	31 d2                	xor    edx,edx
    5d2d:	41 bc 0c 00 00 00    	mov    r12d,0xc
    5d33:	e9 ad fc ff ff       	jmp    59e5 <error_at_line@@Base+0x4a7c>
    5d38:	0f 1f 84 00 00 00 00 	nop    DWORD PTR [rax+rax*1+0x0]
    5d3f:	00 
    5d40:	c6 45 a0 00          	mov    BYTE PTR [rbp-0x60],0x0
    5d44:	41 bc 23 00 00 00    	mov    r12d,0x23
    5d4a:	44 89 d2             	mov    edx,r10d
    5d4d:	4d 85 ed             	test   r13,r13
    5d50:	0f 84 00 fe ff ff    	je     5b56 <error_at_line@@Base+0x4bed>
    5d56:	31 d2                	xor    edx,edx
    5d58:	e9 73 fc ff ff       	jmp    59d0 <error_at_line@@Base+0x4a67>
    5d5d:	0f 1f 00             	nop    DWORD PTR [rax]
    5d60:	41 bc 09 00 00 00    	mov    r12d,0x9
    5d66:	b8 74 00 00 00       	mov    eax,0x74
    5d6b:	e9 1b fe ff ff       	jmp    5b8b <error_at_line@@Base+0x4c22>
    5d70:	41 bc 0d 00 00 00    	mov    r12d,0xd
    5d76:	b8 72 00 00 00       	mov    eax,0x72
    5d7b:	e9 0b fe ff ff       	jmp    5b8b <error_at_line@@Base+0x4c22>
    5d80:	c6 45 a0 00          	mov    BYTE PTR [rbp-0x60],0x0
    5d84:	44 89 d2             	mov    edx,r10d
    5d87:	41 bc 20 00 00 00    	mov    r12d,0x20
    5d8d:	e9 c4 fd ff ff       	jmp    5b56 <error_at_line@@Base+0x4bed>
    5d92:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]
    5d98:	80 7d 9b 00          	cmp    BYTE PTR [rbp-0x65],0x0
    5d9c:	0f 85 7d 0f 00 00    	jne    6d1f <error_at_line@@Base+0x5db6>
    5da2:	80 7d 9f 00          	cmp    BYTE PTR [rbp-0x61],0x0
    5da6:	0f 84 c7 0e 00 00    	je     6c73 <error_at_line@@Base+0x5d0a>
    5dac:	48 83 7d 90 00       	cmp    QWORD PTR [rbp-0x70],0x0
    5db1:	0f 84 f1 11 00 00    	je     6fa8 <error_at_line@@Base+0x603f>
    5db7:	c6 45 a0 00          	mov    BYTE PTR [rbp-0x60],0x0
    5dbb:	31 d2                	xor    edx,edx
    5dbd:	41 bc 07 00 00 00    	mov    r12d,0x7
    5dc3:	e9 1d fc ff ff       	jmp    59e5 <error_at_line@@Base+0x4a7c>
    5dc8:	80 7d 9f 00          	cmp    BYTE PTR [rbp-0x61],0x0
    5dcc:	0f 85 11 11 00 00    	jne    6ee3 <error_at_line@@Base+0x5f7a>
    5dd2:	4d 85 f6             	test   r14,r14
    5dd5:	74 04                	je     5ddb <error_at_line@@Base+0x4e72>
    5dd7:	41 c6 07 27          	mov    BYTE PTR [r15],0x27
    5ddb:	48 8d 05 4c 5a 00 00 	lea    rax,[rip+0x5a4c]        # b82e <error_at_line@@Base+0xa8c5>
    5de2:	c6 45 9e 00          	mov    BYTE PTR [rbp-0x62],0x0
    5de6:	bb 01 00 00 00       	mov    ebx,0x1
    5deb:	c6 45 9a 01          	mov    BYTE PTR [rbp-0x66],0x1
    5def:	c6 45 99 00          	mov    BYTE PTR [rbp-0x67],0x0
    5df3:	c6 45 9c 01          	mov    BYTE PTR [rbp-0x64],0x1
    5df7:	c6 45 83 00          	mov    BYTE PTR [rbp-0x7d],0x0
    5dfb:	c6 45 81 00          	mov    BYTE PTR [rbp-0x7f],0x0
    5dff:	c6 45 9f 00          	mov    BYTE PTR [rbp-0x61],0x0
    5e03:	48 c7 45 88 01 00 00 	mov    QWORD PTR [rbp-0x78],0x1
    5e0a:	00 
    5e0b:	48 89 85 60 ff ff ff 	mov    QWORD PTR [rbp-0xa0],rax
    5e12:	c7 45 84 02 00 00 00 	mov    DWORD PTR [rbp-0x7c],0x2
    5e19:	e9 c2 fa ff ff       	jmp    58e0 <error_at_line@@Base+0x4977>
    5e1e:	0f b6 7d 9b          	movzx  edi,BYTE PTR [rbp-0x65]
    5e22:	48 8b 55 88          	mov    rdx,QWORD PTR [rbp-0x78]
    5e26:	c6 45 99 00          	mov    BYTE PTR [rbp-0x67],0x0
    5e2a:	c6 45 9c 00          	mov    BYTE PTR [rbp-0x64],0x0
    5e2e:	48 83 fa 01          	cmp    rdx,0x1
    5e32:	89 f8                	mov    eax,edi
    5e34:	40 88 7d 81          	mov    BYTE PTR [rbp-0x7f],dil
    5e38:	0f 95 45 83          	setne  BYTE PTR [rbp-0x7d]
    5e3c:	83 f0 01             	xor    eax,0x1
    5e3f:	48 85 d2             	test   rdx,rdx
    5e42:	88 45 9a             	mov    BYTE PTR [rbp-0x66],al
    5e45:	0f 95 c0             	setne  al
    5e48:	31 db                	xor    ebx,ebx
    5e4a:	21 f8                	and    eax,edi
    5e4c:	c6 45 9f 00          	mov    BYTE PTR [rbp-0x61],0x0
    5e50:	88 45 9e             	mov    BYTE PTR [rbp-0x62],al
    5e53:	e9 88 fa ff ff       	jmp    58e0 <error_at_line@@Base+0x4977>
    5e58:	80 7d 9f 00          	cmp    BYTE PTR [rbp-0x61],0x0
    5e5c:	0f 85 29 10 00 00    	jne    6e8b <error_at_line@@Base+0x5f22>
    5e62:	4d 85 f6             	test   r14,r14
    5e65:	74 04                	je     5e6b <error_at_line@@Base+0x4f02>
    5e67:	41 c6 07 22          	mov    BYTE PTR [r15],0x22
    5e6b:	48 8d 05 ba 59 00 00 	lea    rax,[rip+0x59ba]        # b82c <error_at_line@@Base+0xa8c3>
    5e72:	c6 45 9a 00          	mov    BYTE PTR [rbp-0x66],0x0
    5e76:	bb 01 00 00 00       	mov    ebx,0x1
    5e7b:	c6 45 99 00          	mov    BYTE PTR [rbp-0x67],0x0
    5e7f:	c6 45 9c 00          	mov    BYTE PTR [rbp-0x64],0x0
    5e83:	c6 45 83 00          	mov    BYTE PTR [rbp-0x7d],0x0
    5e87:	c6 45 9e 01          	mov    BYTE PTR [rbp-0x62],0x1
    5e8b:	c6 45 81 01          	mov    BYTE PTR [rbp-0x7f],0x1
    5e8f:	c6 45 9b 01          	mov    BYTE PTR [rbp-0x65],0x1
    5e93:	48 c7 45 88 01 00 00 	mov    QWORD PTR [rbp-0x78],0x1
    5e9a:	00 
    5e9b:	48 89 85 60 ff ff ff 	mov    QWORD PTR [rbp-0xa0],rax
    5ea2:	e9 39 fa ff ff       	jmp    58e0 <error_at_line@@Base+0x4977>
    5ea7:	80 7d 9f 00          	cmp    BYTE PTR [rbp-0x61],0x0
    5eab:	0f 85 14 10 00 00    	jne    6ec5 <error_at_line@@Base+0x5f5c>
    5eb1:	c6 45 9b 01          	mov    BYTE PTR [rbp-0x65],0x1
    5eb5:	e9 18 ff ff ff       	jmp    5dd2 <error_at_line@@Base+0x4e69>
    5eba:	c6 45 9e 00          	mov    BYTE PTR [rbp-0x62],0x0
    5ebe:	c6 45 9a 01          	mov    BYTE PTR [rbp-0x66],0x1
    5ec2:	c6 45 99 01          	mov    BYTE PTR [rbp-0x67],0x1
    5ec6:	c6 45 9c 01          	mov    BYTE PTR [rbp-0x64],0x1
    5eca:	c6 45 83 00          	mov    BYTE PTR [rbp-0x7d],0x0
    5ece:	c6 45 81 00          	mov    BYTE PTR [rbp-0x7f],0x0
    5ed2:	c6 45 9f 01          	mov    BYTE PTR [rbp-0x61],0x1
    5ed6:	48 8d 05 51 59 00 00 	lea    rax,[rip+0x5951]        # b82e <error_at_line@@Base+0xa8c5>
    5edd:	48 c7 45 88 01 00 00 	mov    QWORD PTR [rbp-0x78],0x1
    5ee4:	00 
    5ee5:	31 db                	xor    ebx,ebx
    5ee7:	48 89 85 60 ff ff ff 	mov    QWORD PTR [rbp-0xa0],rax
    5eee:	c7 45 84 02 00 00 00 	mov    DWORD PTR [rbp-0x7c],0x2
    5ef5:	e9 e6 f9 ff ff       	jmp    58e0 <error_at_line@@Base+0x4977>
    5efa:	c6 45 9e 00          	mov    BYTE PTR [rbp-0x62],0x0
    5efe:	c6 45 9a 01          	mov    BYTE PTR [rbp-0x66],0x1
    5f02:	c6 45 99 01          	mov    BYTE PTR [rbp-0x67],0x1
    5f06:	c6 45 9c 01          	mov    BYTE PTR [rbp-0x64],0x1
    5f0a:	c6 45 83 00          	mov    BYTE PTR [rbp-0x7d],0x0
    5f0e:	c6 45 81 00          	mov    BYTE PTR [rbp-0x7f],0x0
    5f12:	c6 45 9f 01          	mov    BYTE PTR [rbp-0x61],0x1
    5f16:	c6 45 9b 01          	mov    BYTE PTR [rbp-0x65],0x1
    5f1a:	eb ba                	jmp    5ed6 <error_at_line@@Base+0x4f6d>
    5f1c:	48 8d 05 09 59 00 00 	lea    rax,[rip+0x5909]        # b82c <error_at_line@@Base+0xa8c3>
    5f23:	c6 45 9e 01          	mov    BYTE PTR [rbp-0x62],0x1
    5f27:	31 db                	xor    ebx,ebx
    5f29:	c6 45 9a 00          	mov    BYTE PTR [rbp-0x66],0x0
    5f2d:	c6 45 99 00          	mov    BYTE PTR [rbp-0x67],0x0
    5f31:	c6 45 9c 00          	mov    BYTE PTR [rbp-0x64],0x0
    5f35:	c6 45 83 00          	mov    BYTE PTR [rbp-0x7d],0x0
    5f39:	c6 45 81 01          	mov    BYTE PTR [rbp-0x7f],0x1
    5f3d:	c6 45 9f 01          	mov    BYTE PTR [rbp-0x61],0x1
    5f41:	c6 45 9b 01          	mov    BYTE PTR [rbp-0x65],0x1
    5f45:	48 c7 45 88 01 00 00 	mov    QWORD PTR [rbp-0x78],0x1
    5f4c:	00 
    5f4d:	48 89 85 60 ff ff ff 	mov    QWORD PTR [rbp-0xa0],rax
    5f54:	c7 45 84 05 00 00 00 	mov    DWORD PTR [rbp-0x7c],0x5
    5f5b:	e9 80 f9 ff ff       	jmp    58e0 <error_at_line@@Base+0x4977>
    5f60:	48 8b 85 28 ff ff ff 	mov    rax,QWORD PTR [rbp-0xd8]
    5f67:	4c 8b a5 28 ff ff ff 	mov    r12,QWORD PTR [rbp-0xd8]
    5f6e:	31 db                	xor    ebx,ebx
    5f70:	0f b6 00             	movzx  eax,BYTE PTR [rax]
    5f73:	84 c0                	test   al,al
    5f75:	0f 84 e9 f8 ff ff    	je     5864 <error_at_line@@Base+0x48fb>
    5f7b:	0f 1f 44 00 00       	nop    DWORD PTR [rax+rax*1+0x0]
    5f80:	4c 39 f3             	cmp    rbx,r14
    5f83:	73 04                	jae    5f89 <error_at_line@@Base+0x5020>
    5f85:	41 88 04 1f          	mov    BYTE PTR [r15+rbx*1],al
    5f89:	48 83 c3 01          	add    rbx,0x1
    5f8d:	41 0f b6 04 1c       	movzx  eax,BYTE PTR [r12+rbx*1]
    5f92:	84 c0                	test   al,al
    5f94:	75 ea                	jne    5f80 <error_at_line@@Base+0x5017>
    5f96:	e9 cb f8 ff ff       	jmp    5866 <error_at_line@@Base+0x48fd>
    5f9b:	0f 1f 44 00 00       	nop    DWORD PTR [rax+rax*1+0x0]
    5fa0:	48 8b 45 88          	mov    rax,QWORD PTR [rbp-0x78]
    5fa4:	4e 8d 24 28          	lea    r12,[rax+r13*1]
    5fa8:	49 83 f8 ff          	cmp    r8,0xffffffffffffffff
    5fac:	75 38                	jne    5fe6 <error_at_line@@Base+0x507d>
    5fae:	80 7d 83 00          	cmp    BYTE PTR [rbp-0x7d],0x0
    5fb2:	74 32                	je     5fe6 <error_at_line@@Base+0x507d>
    5fb4:	48 8b 7d a8          	mov    rdi,QWORD PTR [rbp-0x58]
    5fb8:	44 88 9d 70 ff ff ff 	mov    BYTE PTR [rbp-0x90],r11b
    5fbf:	4c 89 8d 78 ff ff ff 	mov    QWORD PTR [rbp-0x88],r9
    5fc6:	44 88 55 a0          	mov    BYTE PTR [rbp-0x60],r10b
    5fca:	e8 11 a9 ff ff       	call   8e0 <strlen@plt>
    5fcf:	44 0f b6 9d 70 ff ff 	movzx  r11d,BYTE PTR [rbp-0x90]
    5fd6:	ff 
    5fd7:	44 0f b6 55 a0       	movzx  r10d,BYTE PTR [rbp-0x60]
    5fdc:	4c 8b 8d 78 ff ff ff 	mov    r9,QWORD PTR [rbp-0x88]
    5fe3:	49 89 c0             	mov    r8,rax
    5fe6:	4d 39 e0             	cmp    r8,r12
    5fe9:	0f 82 b1 03 00 00    	jb     63a0 <error_at_line@@Base+0x5437>
    5fef:	48 8b 55 88          	mov    rdx,QWORD PTR [rbp-0x78]
    5ff3:	4c 89 cf             	mov    rdi,r9
    5ff6:	48 8b b5 60 ff ff ff 	mov    rsi,QWORD PTR [rbp-0xa0]
    5ffd:	44 88 9d 68 ff ff ff 	mov    BYTE PTR [rbp-0x98],r11b
    6004:	4c 89 85 70 ff ff ff 	mov    QWORD PTR [rbp-0x90],r8
    600b:	44 88 95 78 ff ff ff 	mov    BYTE PTR [rbp-0x88],r10b
    6012:	4c 89 4d a0          	mov    QWORD PTR [rbp-0x60],r9
    6016:	e8 c5 a9 ff ff       	call   9e0 <memcmp@plt>
    601b:	4c 8b 4d a0          	mov    r9,QWORD PTR [rbp-0x60]
    601f:	44 0f b6 95 78 ff ff 	movzx  r10d,BYTE PTR [rbp-0x88]
    6026:	ff 
    6027:	85 c0                	test   eax,eax
    6029:	4c 8b 85 70 ff ff ff 	mov    r8,QWORD PTR [rbp-0x90]
    6030:	44 0f b6 9d 68 ff ff 	movzx  r11d,BYTE PTR [rbp-0x98]
    6037:	ff 
    6038:	0f 85 72 05 00 00    	jne    65b0 <error_at_line@@Base+0x5647>
    603e:	80 7d 9f 00          	cmp    BYTE PTR [rbp-0x61],0x0
    6042:	0f 85 0c 05 00 00    	jne    6554 <error_at_line@@Base+0x55eb>
    6048:	45 0f b6 21          	movzx  r12d,BYTE PTR [r9]
    604c:	41 80 fc 23          	cmp    r12b,0x23
    6050:	0f 8f ca 06 00 00    	jg     6720 <error_at_line@@Base+0x57b7>
    6056:	45 84 e4             	test   r12b,r12b
    6059:	78 25                	js     6080 <error_at_line@@Base+0x5117>
    605b:	41 80 fc 23          	cmp    r12b,0x23
    605f:	77 1f                	ja     6080 <error_at_line@@Base+0x5117>
    6061:	48 8d 15 fc 63 00 00 	lea    rdx,[rip+0x63fc]        # c464 <error_at_line@@Base+0xb4fb>
    6068:	41 0f b6 c4          	movzx  eax,r12b
    606c:	48 63 04 82          	movsxd rax,DWORD PTR [rdx+rax*4]
    6070:	48 01 d0             	add    rax,rdx
    6073:	3e ff e0             	notrack jmp rax
    6076:	66 2e 0f 1f 84 00 00 	cs nop WORD PTR [rax+rax*1+0x0]
    607d:	00 00 00 
    6080:	0f b6 45 9e          	movzx  eax,BYTE PTR [rbp-0x62]
    6084:	88 45 a0             	mov    BYTE PTR [rbp-0x60],al
    6087:	48 83 bd 50 ff ff ff 	cmp    QWORD PTR [rbp-0xb0],0x1
    608e:	01 
    608f:	0f 84 dd f8 ff ff    	je     5972 <error_at_line@@Base+0x4a09>
    6095:	48 c7 45 c0 00 00 00 	mov    QWORD PTR [rbp-0x40],0x0
    609c:	00 
    609d:	48 8d 4d c0          	lea    rcx,[rbp-0x40]
    60a1:	49 83 f8 ff          	cmp    r8,0xffffffffffffffff
    60a5:	75 3c                	jne    60e3 <error_at_line@@Base+0x517a>
    60a7:	48 8b 7d a8          	mov    rdi,QWORD PTR [rbp-0x58]
    60ab:	44 88 9d 68 ff ff ff 	mov    BYTE PTR [rbp-0x98],r11b
    60b2:	4c 89 8d 70 ff ff ff 	mov    QWORD PTR [rbp-0x90],r9
    60b9:	44 88 95 78 ff ff ff 	mov    BYTE PTR [rbp-0x88],r10b
    60c0:	e8 1b a8 ff ff       	call   8e0 <strlen@plt>
    60c5:	4c 8b 8d 70 ff ff ff 	mov    r9,QWORD PTR [rbp-0x90]
    60cc:	48 8d 4d c0          	lea    rcx,[rbp-0x40]
    60d0:	44 0f b6 9d 68 ff ff 	movzx  r11d,BYTE PTR [rbp-0x98]
    60d7:	ff 
    60d8:	44 0f b6 95 78 ff ff 	movzx  r10d,BYTE PTR [rbp-0x88]
    60df:	ff 
    60e0:	49 89 c0             	mov    r8,rax
    60e3:	4c 89 c0             	mov    rax,r8
    60e6:	48 8d 7d bc          	lea    rdi,[rbp-0x44]
    60ea:	4c 89 ce             	mov    rsi,r9
    60ed:	44 88 9d 68 ff ff ff 	mov    BYTE PTR [rbp-0x98],r11b
    60f4:	4c 29 e8             	sub    rax,r13
    60f7:	44 88 95 70 ff ff ff 	mov    BYTE PTR [rbp-0x90],r10b
    60fe:	48 89 c2             	mov    rdx,rax
    6101:	4c 89 85 78 ff ff ff 	mov    QWORD PTR [rbp-0x88],r8
    6108:	48 89 85 38 ff ff ff 	mov    QWORD PTR [rbp-0xc8],rax
    610f:	4c 89 8d 40 ff ff ff 	mov    QWORD PTR [rbp-0xc0],r9
    6116:	e8 b5 f4 ff ff       	call   55d0 <error_at_line@@Base+0x4667>
    611b:	4c 8b 85 78 ff ff ff 	mov    r8,QWORD PTR [rbp-0x88]
    6122:	44 0f b6 95 70 ff ff 	movzx  r10d,BYTE PTR [rbp-0x90]
    6129:	ff 
    612a:	48 85 c0             	test   rax,rax
    612d:	44 0f b6 9d 68 ff ff 	movzx  r11d,BYTE PTR [rbp-0x98]
    6134:	ff 
    6135:	48 89 c1             	mov    rcx,rax
    6138:	0f 84 82 00 00 00    	je     61c0 <error_at_line@@Base+0x5257>
    613e:	48 83 f8 ff          	cmp    rax,0xffffffffffffffff
    6142:	4c 8b 8d 40 ff ff ff 	mov    r9,QWORD PTR [rbp-0xc0]
    6149:	0f 84 17 0b 00 00    	je     6c66 <error_at_line@@Base+0x5cfd>
    614f:	48 83 f8 fe          	cmp    rax,0xfffffffffffffffe
    6153:	0f 84 35 0b 00 00    	je     6c8e <error_at_line@@Base+0x5d25>
    6159:	80 7d 99 00          	cmp    BYTE PTR [rbp-0x67],0x0
    615d:	0f 85 82 0c 00 00    	jne    6de5 <error_at_line@@Base+0x5e7c>
    6163:	8b 7d bc             	mov    edi,DWORD PTR [rbp-0x44]
    6166:	44 88 9d 40 ff ff ff 	mov    BYTE PTR [rbp-0xc0],r11b
    616d:	4c 89 85 68 ff ff ff 	mov    QWORD PTR [rbp-0x98],r8
    6174:	44 88 95 70 ff ff ff 	mov    BYTE PTR [rbp-0x90],r10b
    617b:	48 89 85 78 ff ff ff 	mov    QWORD PTR [rbp-0x88],rax
    6182:	e8 29 aa ff ff       	call   bb0 <iswprint@plt>
    6187:	48 8b 8d 78 ff ff ff 	mov    rcx,QWORD PTR [rbp-0x88]
    618e:	44 0f b6 95 70 ff ff 	movzx  r10d,BYTE PTR [rbp-0x90]
    6195:	ff 
    6196:	85 c0                	test   eax,eax
    6198:	4c 8b 85 68 ff ff ff 	mov    r8,QWORD PTR [rbp-0x98]
    619f:	44 0f b6 9d 40 ff ff 	movzx  r11d,BYTE PTR [rbp-0xc0]
    61a6:	ff 
    61a7:	0f 84 13 0b 00 00    	je     6cc0 <error_at_line@@Base+0x5d57>
    61ad:	48 83 f9 01          	cmp    rcx,0x1
    61b1:	0f 85 96 0e 00 00    	jne    704d <error_at_line@@Base+0x60e4>
    61b7:	66 0f 1f 84 00 00 00 	nop    WORD PTR [rax+rax*1+0x0]
    61be:	00 00 
    61c0:	44 89 d2             	mov    edx,r10d
    61c3:	e9 08 f8 ff ff       	jmp    59d0 <error_at_line@@Base+0x4a67>
    61c8:	0f b6 45 9e          	movzx  eax,BYTE PTR [rbp-0x62]
    61cc:	88 45 a0             	mov    BYTE PTR [rbp-0x60],al
    61cf:	41 80 fc 7d          	cmp    r12b,0x7d
    61d3:	0f 84 a1 03 00 00    	je     657a <error_at_line@@Base+0x5611>
    61d9:	0f 8f f1 0b 00 00    	jg     6dd0 <error_at_line@@Base+0x5e67>
    61df:	41 80 fc 7b          	cmp    r12b,0x7b
    61e3:	0f 84 91 03 00 00    	je     657a <error_at_line@@Base+0x5611>
    61e9:	0f b6 45 9e          	movzx  eax,BYTE PTR [rbp-0x62]
    61ed:	31 d2                	xor    edx,edx
    61ef:	88 45 a0             	mov    BYTE PTR [rbp-0x60],al
    61f2:	e9 5f f9 ff ff       	jmp    5b56 <error_at_line@@Base+0x4bed>
    61f7:	80 7d 99 00          	cmp    BYTE PTR [rbp-0x67],0x0
    61fb:	0f 85 5f f9 ff ff    	jne    5b60 <error_at_line@@Base+0x4bf7>
    6201:	80 7d 9b 00          	cmp    BYTE PTR [rbp-0x65],0x0
    6205:	0f 85 0d 0e 00 00    	jne    7018 <error_at_line@@Base+0x60af>
    620b:	0f b6 45 9e          	movzx  eax,BYTE PTR [rbp-0x62]
    620f:	31 d2                	xor    edx,edx
    6211:	41 bc 0d 00 00 00    	mov    r12d,0xd
    6217:	88 45 a0             	mov    BYTE PTR [rbp-0x60],al
    621a:	31 c0                	xor    eax,eax
    621c:	0f 1f 40 00          	nop    DWORD PTR [rax+0x0]
    6220:	20 55 9d             	and    BYTE PTR [rbp-0x63],dl
    6223:	49 83 c5 01          	add    r13,0x1
    6227:	80 7d a0 00          	cmp    BYTE PTR [rbp-0x60],0x0
    622b:	0f 84 43 04 00 00    	je     6674 <error_at_line@@Base+0x570b>
    6231:	44 89 d8             	mov    eax,r11d
    6234:	83 f0 01             	xor    eax,0x1
    6237:	22 45 9c             	and    al,BYTE PTR [rbp-0x64]
    623a:	e9 e6 f7 ff ff       	jmp    5a25 <error_at_line@@Base+0x4abc>
    623f:	80 7d 9b 00          	cmp    BYTE PTR [rbp-0x65],0x0
    6243:	0f 85 b6 0d 00 00    	jne    6fff <error_at_line@@Base+0x6096>
    6249:	c6 45 9d 00          	mov    BYTE PTR [rbp-0x63],0x0
    624d:	49 83 c5 01          	add    r13,0x1
    6251:	41 bc 0b 00 00 00    	mov    r12d,0xb
    6257:	eb d8                	jmp    6231 <error_at_line@@Base+0x52c8>
    6259:	80 7d 9b 00          	cmp    BYTE PTR [rbp-0x65],0x0
    625d:	0f 85 8f 0d 00 00    	jne    6ff2 <error_at_line@@Base+0x6089>
    6263:	c6 45 9d 00          	mov    BYTE PTR [rbp-0x63],0x0
    6267:	49 83 c5 01          	add    r13,0x1
    626b:	41 bc 08 00 00 00    	mov    r12d,0x8
    6271:	eb be                	jmp    6231 <error_at_line@@Base+0x52c8>
    6273:	80 7d 99 00          	cmp    BYTE PTR [rbp-0x67],0x0
    6277:	0f 85 e3 f8 ff ff    	jne    5b60 <error_at_line@@Base+0x4bf7>
    627d:	80 7d 9b 00          	cmp    BYTE PTR [rbp-0x65],0x0
    6281:	0f 85 a2 0d 00 00    	jne    7029 <error_at_line@@Base+0x60c0>
    6287:	0f b6 45 9e          	movzx  eax,BYTE PTR [rbp-0x62]
    628b:	31 d2                	xor    edx,edx
    628d:	41 bc 0a 00 00 00    	mov    r12d,0xa
    6293:	88 45 a0             	mov    BYTE PTR [rbp-0x60],al
    6296:	31 c0                	xor    eax,eax
    6298:	eb 86                	jmp    6220 <error_at_line@@Base+0x52b7>
    629a:	80 7d 9b 00          	cmp    BYTE PTR [rbp-0x65],0x0
    629e:	0f 85 3d 0d 00 00    	jne    6fe1 <error_at_line@@Base+0x6078>
    62a4:	c6 45 9d 00          	mov    BYTE PTR [rbp-0x63],0x0
    62a8:	49 83 c5 01          	add    r13,0x1
    62ac:	41 bc 0c 00 00 00    	mov    r12d,0xc
    62b2:	e9 7a ff ff ff       	jmp    6231 <error_at_line@@Base+0x52c8>
    62b7:	0f b6 45 9e          	movzx  eax,BYTE PTR [rbp-0x62]
    62bb:	88 45 a0             	mov    BYTE PTR [rbp-0x60],al
    62be:	44 89 d8             	mov    eax,r11d
    62c1:	83 f0 01             	xor    eax,0x1
    62c4:	22 45 9c             	and    al,BYTE PTR [rbp-0x64]
    62c7:	0f 84 30 01 00 00    	je     63fd <error_at_line@@Base+0x5494>
    62cd:	0f 1f 00             	nop    DWORD PTR [rax]
    62d0:	4c 39 f3             	cmp    rbx,r14
    62d3:	73 05                	jae    62da <error_at_line@@Base+0x5371>
    62d5:	41 c6 04 1f 27       	mov    BYTE PTR [r15+rbx*1],0x27
    62da:	48 8d 53 01          	lea    rdx,[rbx+0x1]
    62de:	4c 39 f2             	cmp    rdx,r14
    62e1:	73 06                	jae    62e9 <error_at_line@@Base+0x5380>
    62e3:	41 c6 44 1f 01 24    	mov    BYTE PTR [r15+rbx*1+0x1],0x24
    62e9:	48 8d 53 02          	lea    rdx,[rbx+0x2]
    62ed:	4c 39 f2             	cmp    rdx,r14
    62f0:	73 06                	jae    62f8 <error_at_line@@Base+0x538f>
    62f2:	41 c6 44 1f 02 27    	mov    BYTE PTR [r15+rbx*1+0x2],0x27
    62f8:	48 8d 53 03          	lea    rdx,[rbx+0x3]
    62fc:	48 83 c3 04          	add    rbx,0x4
    6300:	4c 39 f2             	cmp    rdx,r14
    6303:	0f 83 9e 08 00 00    	jae    6ba7 <error_at_line@@Base+0x5c3e>
    6309:	41 c6 04 17 5c       	mov    BYTE PTR [r15+rdx*1],0x5c
    630e:	49 83 c5 01          	add    r13,0x1
    6312:	80 7d a0 00          	cmp    BYTE PTR [rbp-0x60],0x0
    6316:	0f 84 81 0a 00 00    	je     6d9d <error_at_line@@Base+0x5e34>
    631c:	c6 45 9d 00          	mov    BYTE PTR [rbp-0x63],0x0
    6320:	44 0f b6 5d a0       	movzx  r11d,BYTE PTR [rbp-0x60]
    6325:	41 bc 30 00 00 00    	mov    r12d,0x30
    632b:	e9 28 f7 ff ff       	jmp    5a58 <error_at_line@@Base+0x4aef>
    6330:	0f b6 45 9e          	movzx  eax,BYTE PTR [rbp-0x62]
    6334:	41 bc 23 00 00 00    	mov    r12d,0x23
    633a:	88 45 a0             	mov    BYTE PTR [rbp-0x60],al
    633d:	e9 08 fa ff ff       	jmp    5d4a <error_at_line@@Base+0x4de1>
    6342:	80 7d 99 00          	cmp    BYTE PTR [rbp-0x67],0x0
    6346:	0f 85 14 f8 ff ff    	jne    5b60 <error_at_line@@Base+0x4bf7>
    634c:	80 7d 9b 00          	cmp    BYTE PTR [rbp-0x65],0x0
    6350:	0f 85 7c 0d 00 00    	jne    70d2 <error_at_line@@Base+0x6169>
    6356:	0f b6 45 9e          	movzx  eax,BYTE PTR [rbp-0x62]
    635a:	31 d2                	xor    edx,edx
    635c:	41 bc 09 00 00 00    	mov    r12d,0x9
    6362:	88 45 a0             	mov    BYTE PTR [rbp-0x60],al
    6365:	31 c0                	xor    eax,eax
    6367:	e9 b4 fe ff ff       	jmp    6220 <error_at_line@@Base+0x52b7>
    636c:	80 7d 9b 00          	cmp    BYTE PTR [rbp-0x65],0x0
    6370:	0f 85 4b 0d 00 00    	jne    70c1 <error_at_line@@Base+0x6158>
    6376:	c6 45 9d 00          	mov    BYTE PTR [rbp-0x63],0x0
    637a:	49 83 c5 01          	add    r13,0x1
    637e:	41 bc 07 00 00 00    	mov    r12d,0x7
    6384:	e9 a8 fe ff ff       	jmp    6231 <error_at_line@@Base+0x52c8>
    6389:	0f b6 55 9e          	movzx  edx,BYTE PTR [rbp-0x62]
    638d:	41 bc 20 00 00 00    	mov    r12d,0x20
    6393:	88 55 a0             	mov    BYTE PTR [rbp-0x60],dl
    6396:	e9 bb f7 ff ff       	jmp    5b56 <error_at_line@@Base+0x4bed>
    639b:	0f 1f 44 00 00       	nop    DWORD PTR [rax+rax*1+0x0]
    63a0:	45 0f b6 21          	movzx  r12d,BYTE PTR [r9]
    63a4:	41 80 fc 23          	cmp    r12b,0x23
    63a8:	0f 8f d2 02 00 00    	jg     6680 <error_at_line@@Base+0x5717>
    63ae:	45 84 e4             	test   r12b,r12b
    63b1:	0f 88 a9 f5 ff ff    	js     5960 <error_at_line@@Base+0x49f7>
    63b7:	41 80 fc 23          	cmp    r12b,0x23
    63bb:	0f 87 9f f5 ff ff    	ja     5960 <error_at_line@@Base+0x49f7>
    63c1:	48 8d 15 2c 61 00 00 	lea    rdx,[rip+0x612c]        # c4f4 <error_at_line@@Base+0xb58b>
    63c8:	41 0f b6 c4          	movzx  eax,r12b
    63cc:	48 63 04 82          	movsxd rax,DWORD PTR [rdx+rax*4]
    63d0:	48 01 d0             	add    rax,rdx
    63d3:	3e ff e0             	notrack jmp rax
    63d6:	66 2e 0f 1f 84 00 00 	cs nop WORD PTR [rax+rax*1+0x0]
    63dd:	00 00 00 
    63e0:	80 7d 9f 00          	cmp    BYTE PTR [rbp-0x61],0x0
    63e4:	0f 85 6a 01 00 00    	jne    6554 <error_at_line@@Base+0x55eb>
    63ea:	44 89 d8             	mov    eax,r11d
    63ed:	c6 45 a0 00          	mov    BYTE PTR [rbp-0x60],0x0
    63f1:	83 f0 01             	xor    eax,0x1
    63f4:	22 45 9c             	and    al,BYTE PTR [rbp-0x64]
    63f7:	0f 85 d3 fe ff ff    	jne    62d0 <error_at_line@@Base+0x5367>
    63fd:	4c 39 f3             	cmp    rbx,r14
    6400:	73 05                	jae    6407 <error_at_line@@Base+0x549e>
    6402:	41 c6 04 1f 5c       	mov    BYTE PTR [r15+rbx*1],0x5c
    6407:	48 8d 73 01          	lea    rsi,[rbx+0x1]
    640b:	49 8d 4d 01          	lea    rcx,[r13+0x1]
    640f:	80 7d 81 00          	cmp    BYTE PTR [rbp-0x7f],0x0
    6413:	0f 84 2e 08 00 00    	je     6c47 <error_at_line@@Base+0x5cde>
    6419:	4c 39 c1             	cmp    rcx,r8
    641c:	73 1b                	jae    6439 <error_at_line@@Base+0x54d0>
    641e:	48 8b 45 a8          	mov    rax,QWORD PTR [rbp-0x58]
    6422:	42 0f b6 44 28 01    	movzx  eax,BYTE PTR [rax+r13*1+0x1]
    6428:	88 85 78 ff ff ff    	mov    BYTE PTR [rbp-0x88],al
    642e:	83 e8 30             	sub    eax,0x30
    6431:	3c 09                	cmp    al,0x9
    6433:	0f 86 1f 09 00 00    	jbe    6d58 <error_at_line@@Base+0x5def>
    6439:	48 8b 45 90          	mov    rax,QWORD PTR [rbp-0x70]
    643d:	48 85 c0             	test   rax,rax
    6440:	0f 84 01 08 00 00    	je     6c47 <error_at_line@@Base+0x5cde>
    6446:	f6 40 06 01          	test   BYTE PTR [rax+0x6],0x1
    644a:	0f 85 e7 07 00 00    	jne    6c37 <error_at_line@@Base+0x5cce>
    6450:	0f b6 45 81          	movzx  eax,BYTE PTR [rbp-0x7f]
    6454:	31 d2                	xor    edx,edx
    6456:	48 89 f3             	mov    rbx,rsi
    6459:	41 bc 30 00 00 00    	mov    r12d,0x30
    645f:	e9 9e f6 ff ff       	jmp    5b02 <error_at_line@@Base+0x4b99>
    6464:	80 7d 9b 00          	cmp    BYTE PTR [rbp-0x65],0x0
    6468:	0f 84 a4 f8 ff ff    	je     5d12 <error_at_line@@Base+0x4da9>
    646e:	41 bc 66 00 00 00    	mov    r12d,0x66
    6474:	31 d2                	xor    edx,edx
    6476:	80 7d 9f 00          	cmp    BYTE PTR [rbp-0x61],0x0
    647a:	0f 84 92 f5 ff ff    	je     5a12 <error_at_line@@Base+0x4aa9>
    6480:	0f b6 4d 9b          	movzx  ecx,BYTE PTR [rbp-0x65]
    6484:	4d 89 fb             	mov    r11,r15
    6487:	20 4d 9c             	and    BYTE PTR [rbp-0x64],cl
    648a:	4d 89 c7             	mov    r15,r8
    648d:	e9 3d f7 ff ff       	jmp    5bcf <error_at_line@@Base+0x4c66>
    6492:	80 7d 9b 00          	cmp    BYTE PTR [rbp-0x65],0x0
    6496:	0f 84 66 f7 ff ff    	je     5c02 <error_at_line@@Base+0x4c99>
    649c:	41 bc 76 00 00 00    	mov    r12d,0x76
    64a2:	31 d2                	xor    edx,edx
    64a4:	e9 5f f5 ff ff       	jmp    5a08 <error_at_line@@Base+0x4a9f>
    64a9:	80 7d 9b 00          	cmp    BYTE PTR [rbp-0x65],0x0
    64ad:	0f 84 87 f7 ff ff    	je     5c3a <error_at_line@@Base+0x4cd1>
    64b3:	41 bc 62 00 00 00    	mov    r12d,0x62
    64b9:	31 d2                	xor    edx,edx
    64bb:	e9 48 f5 ff ff       	jmp    5a08 <error_at_line@@Base+0x4a9f>
    64c0:	b8 74 00 00 00       	mov    eax,0x74
    64c5:	e9 c1 f6 ff ff       	jmp    5b8b <error_at_line@@Base+0x4c22>
    64ca:	c6 45 a0 00          	mov    BYTE PTR [rbp-0x60],0x0
    64ce:	e9 77 f8 ff ff       	jmp    5d4a <error_at_line@@Base+0x4de1>
    64d3:	c6 45 a0 00          	mov    BYTE PTR [rbp-0x60],0x0
    64d7:	0f b6 55 9e          	movzx  edx,BYTE PTR [rbp-0x62]
    64db:	e9 76 f6 ff ff       	jmp    5b56 <error_at_line@@Base+0x4bed>
    64e0:	80 7d 9b 00          	cmp    BYTE PTR [rbp-0x65],0x0
    64e4:	0f 84 b8 f8 ff ff    	je     5da2 <error_at_line@@Base+0x4e39>
    64ea:	41 bc 61 00 00 00    	mov    r12d,0x61
    64f0:	31 d2                	xor    edx,edx
    64f2:	e9 11 f5 ff ff       	jmp    5a08 <error_at_line@@Base+0x4a9f>
    64f7:	66 0f 1f 84 00 00 00 	nop    WORD PTR [rax+rax*1+0x0]
    64fe:	00 00 
    6500:	41 8d 4c 24 bf       	lea    ecx,[r12-0x41]
    6505:	b8 01 00 00 00       	mov    eax,0x1
    650a:	48 be ff ff ff 53 ff 	movabs rsi,0x3ffffff53ffffff
    6511:	ff ff 03 
    6514:	48 d3 e0             	shl    rax,cl
    6517:	48 85 f0             	test   rax,rsi
    651a:	0f 85 b0 01 00 00    	jne    66d0 <error_at_line@@Base+0x5767>
    6520:	a9 00 00 00 a4       	test   eax,0xa4000000
    6525:	0f 85 25 f6 ff ff    	jne    5b50 <error_at_line@@Base+0x4be7>
    652b:	83 7d 84 02          	cmp    DWORD PTR [rbp-0x7c],0x2
    652f:	0f 84 bb 01 00 00    	je     66f0 <error_at_line@@Base+0x5787>
    6535:	80 7d 9b 00          	cmp    BYTE PTR [rbp-0x65],0x0
    6539:	0f 84 5c f6 ff ff    	je     5b9b <error_at_line@@Base+0x4c32>
    653f:	80 7d 9f 00          	cmp    BYTE PTR [rbp-0x61],0x0
    6543:	0f 84 a4 06 00 00    	je     6bed <error_at_line@@Base+0x5c84>
    6549:	48 83 7d 88 00       	cmp    QWORD PTR [rbp-0x78],0x0
    654e:	0f 85 a6 01 00 00    	jne    66fa <error_at_line@@Base+0x5791>
    6554:	4d 89 fb             	mov    r11,r15
    6557:	4d 89 c7             	mov    r15,r8
    655a:	e9 70 f6 ff ff       	jmp    5bcf <error_at_line@@Base+0x4c66>
    655f:	90                   	nop
    6560:	41 80 fc 7d          	cmp    r12b,0x7d
    6564:	74 10                	je     6576 <error_at_line@@Base+0x560d>
    6566:	0f 8f e4 f3 ff ff    	jg     5950 <error_at_line@@Base+0x49e7>
    656c:	41 80 fc 7b          	cmp    r12b,0x7b
    6570:	0f 85 da f5 ff ff    	jne    5b50 <error_at_line@@Base+0x4be7>
    6576:	c6 45 a0 00          	mov    BYTE PTR [rbp-0x60],0x0
    657a:	49 83 f8 ff          	cmp    r8,0xffffffffffffffff
    657e:	0f 84 3c 01 00 00    	je     66c0 <error_at_line@@Base+0x5757>
    6584:	49 83 f8 01          	cmp    r8,0x1
    6588:	0f 95 c0             	setne  al
    658b:	84 c0                	test   al,al
    658d:	0f 84 b7 f7 ff ff    	je     5d4a <error_at_line@@Base+0x4de1>
    6593:	31 d2                	xor    edx,edx
    6595:	e9 36 f4 ff ff       	jmp    59d0 <error_at_line@@Base+0x4a67>
    659a:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]
    65a0:	41 89 c4             	mov    r12d,eax
    65a3:	31 d2                	xor    edx,edx
    65a5:	e9 5e f4 ff ff       	jmp    5a08 <error_at_line@@Base+0x4a9f>
    65aa:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]
    65b0:	45 0f b6 21          	movzx  r12d,BYTE PTR [r9]
    65b4:	41 80 fc 23          	cmp    r12b,0x23
    65b8:	0f 8e f0 fd ff ff    	jle    63ae <error_at_line@@Base+0x5445>
    65be:	41 80 fc 7a          	cmp    r12b,0x7a
    65c2:	0f 8f ef 05 00 00    	jg     6bb7 <error_at_line@@Base+0x5c4e>
    65c8:	41 80 fc 40          	cmp    r12b,0x40
    65cc:	0f 8f b6 01 00 00    	jg     6788 <error_at_line@@Base+0x581f>
    65d2:	41 80 fc 3e          	cmp    r12b,0x3e
    65d6:	7f 38                	jg     6610 <error_at_line@@Base+0x56a7>
    65d8:	41 8d 4c 24 dc       	lea    ecx,[r12-0x24]
    65dd:	b8 01 00 00 00       	mov    eax,0x1
    65e2:	48 d3 e0             	shl    rax,cl
    65e5:	a9 82 ff 7f 00       	test   eax,0x7fff82
    65ea:	0f 84 e6 f6 ff ff    	je     5cd6 <error_at_line@@Base+0x4d6d>
    65f0:	80 7d 9a 00          	cmp    BYTE PTR [rbp-0x66],0x0
    65f4:	0f 85 b8 01 00 00    	jne    67b2 <error_at_line@@Base+0x5849>
    65fa:	c6 45 a0 00          	mov    BYTE PTR [rbp-0x60],0x0
    65fe:	0f b6 55 9e          	movzx  edx,BYTE PTR [rbp-0x62]
    6602:	e9 d3 f3 ff ff       	jmp    59da <error_at_line@@Base+0x4a71>
    6607:	66 0f 1f 84 00 00 00 	nop    WORD PTR [rax+rax*1+0x0]
    660e:	00 00 
    6610:	41 80 fc 3f          	cmp    r12b,0x3f
    6614:	0f 85 46 f3 ff ff    	jne    5960 <error_at_line@@Base+0x49f7>
    661a:	c6 45 a0 00          	mov    BYTE PTR [rbp-0x60],0x0
    661e:	83 7d 84 02          	cmp    DWORD PTR [rbp-0x7c],0x2
    6622:	74 3c                	je     6660 <error_at_line@@Base+0x56f7>
    6624:	83 7d 84 05          	cmp    DWORD PTR [rbp-0x7c],0x5
    6628:	75 26                	jne    6650 <error_at_line@@Base+0x56e7>
    662a:	f6 85 4c ff ff ff 04 	test   BYTE PTR [rbp-0xb4],0x4
    6631:	74 1d                	je     6650 <error_at_line@@Base+0x56e7>
    6633:	49 8d 45 02          	lea    rax,[r13+0x2]
    6637:	4c 39 c0             	cmp    rax,r8
    663a:	73 14                	jae    6650 <error_at_line@@Base+0x56e7>
    663c:	48 8b 7d a8          	mov    rdi,QWORD PTR [rbp-0x58]
    6640:	42 80 7c 2f 01 3f    	cmp    BYTE PTR [rdi+r13*1+0x1],0x3f
    6646:	0f 84 cd 08 00 00    	je     6f19 <error_at_line@@Base+0x5fb0>
    664c:	0f 1f 40 00          	nop    DWORD PTR [rax+0x0]
    6650:	41 bc 3f 00 00 00    	mov    r12d,0x3f
    6656:	31 d2                	xor    edx,edx
    6658:	e9 73 f3 ff ff       	jmp    59d0 <error_at_line@@Base+0x4a67>
    665d:	0f 1f 00             	nop    DWORD PTR [rax]
    6660:	80 7d 9f 00          	cmp    BYTE PTR [rbp-0x61],0x0
    6664:	0f 85 d5 01 00 00    	jne    683f <error_at_line@@Base+0x58d6>
    666a:	c6 45 9d 00          	mov    BYTE PTR [rbp-0x63],0x0
    666e:	49 83 c5 01          	add    r13,0x1
    6672:	31 c0                	xor    eax,eax
    6674:	83 f0 01             	xor    eax,0x1
    6677:	44 21 d8             	and    eax,r11d
    667a:	e9 9a f4 ff ff       	jmp    5b19 <error_at_line@@Base+0x4bb0>
    667f:	90                   	nop
    6680:	41 80 fc 7a          	cmp    r12b,0x7a
    6684:	0f 8e 3e ff ff ff    	jle    65c8 <error_at_line@@Base+0x565f>
    668a:	41 80 fc 7d          	cmp    r12b,0x7d
    668e:	0f 84 98 06 00 00    	je     6d2c <error_at_line@@Base+0x5dc3>
    6694:	c6 45 a0 00          	mov    BYTE PTR [rbp-0x60],0x0
    6698:	41 80 fc 7d          	cmp    r12b,0x7d
    669c:	0f 8f 2d 05 00 00    	jg     6bcf <error_at_line@@Base+0x5c66>
    66a2:	41 80 fc 7b          	cmp    r12b,0x7b
    66a6:	0f 85 a8 f4 ff ff    	jne    5b54 <error_at_line@@Base+0x4beb>
    66ac:	49 83 f8 ff          	cmp    r8,0xffffffffffffffff
    66b0:	0f 85 ce fe ff ff    	jne    6584 <error_at_line@@Base+0x561b>
    66b6:	66 2e 0f 1f 84 00 00 	cs nop WORD PTR [rax+rax*1+0x0]
    66bd:	00 00 00 
    66c0:	48 8b 45 a8          	mov    rax,QWORD PTR [rbp-0x58]
    66c4:	80 78 01 00          	cmp    BYTE PTR [rax+0x1],0x0
    66c8:	0f 95 c0             	setne  al
    66cb:	e9 bb fe ff ff       	jmp    658b <error_at_line@@Base+0x5622>
    66d0:	80 7d 9a 00          	cmp    BYTE PTR [rbp-0x66],0x0
    66d4:	0f 85 23 06 00 00    	jne    6cfd <error_at_line@@Base+0x5d94>
    66da:	c6 45 a0 00          	mov    BYTE PTR [rbp-0x60],0x0
    66de:	44 89 d2             	mov    edx,r10d
    66e1:	e9 f4 f2 ff ff       	jmp    59da <error_at_line@@Base+0x4a71>
    66e6:	66 2e 0f 1f 84 00 00 	cs nop WORD PTR [rax+rax*1+0x0]
    66ed:	00 00 00 
    66f0:	80 7d 9f 00          	cmp    BYTE PTR [rbp-0x61],0x0
    66f4:	0f 85 45 01 00 00    	jne    683f <error_at_line@@Base+0x58d6>
    66fa:	49 83 c5 01          	add    r13,0x1
    66fe:	45 84 db             	test   r11b,r11b
    6701:	0f 85 69 03 00 00    	jne    6a70 <error_at_line@@Base+0x5b07>
    6707:	4c 39 f3             	cmp    rbx,r14
    670a:	0f 82 ce 04 00 00    	jb     6bde <error_at_line@@Base+0x5c75>
    6710:	c6 45 9d 00          	mov    BYTE PTR [rbp-0x63],0x0
    6714:	48 83 c3 01          	add    rbx,0x1
    6718:	e9 c9 f1 ff ff       	jmp    58e6 <error_at_line@@Base+0x497d>
    671d:	0f 1f 00             	nop    DWORD PTR [rax]
    6720:	41 80 fc 7a          	cmp    r12b,0x7a
    6724:	0f 8f 9e fa ff ff    	jg     61c8 <error_at_line@@Base+0x525f>
    672a:	41 80 fc 40          	cmp    r12b,0x40
    672e:	0f 8f 28 04 00 00    	jg     6b5c <error_at_line@@Base+0x5bf3>
    6734:	41 80 fc 3e          	cmp    r12b,0x3e
    6738:	0f 8f 97 05 00 00    	jg     6cd5 <error_at_line@@Base+0x5d6c>
    673e:	41 8d 4c 24 dc       	lea    ecx,[r12-0x24]
    6743:	b8 01 00 00 00       	mov    eax,0x1
    6748:	48 d3 e0             	shl    rax,cl
    674b:	a9 82 ff 7f 00       	test   eax,0x7fff82
    6750:	0f 85 59 06 00 00    	jne    6daf <error_at_line@@Base+0x5e46>
    6756:	a9 75 00 80 07       	test   eax,0x7800075
    675b:	0f 85 88 fa ff ff    	jne    61e9 <error_at_line@@Base+0x5280>
    6761:	0f b6 45 9e          	movzx  eax,BYTE PTR [rbp-0x62]
    6765:	83 7d 84 02          	cmp    DWORD PTR [rbp-0x7c],0x2
    6769:	0f 84 6a 08 00 00    	je     6fd9 <error_at_line@@Base+0x6070>
    676f:	88 45 a0             	mov    BYTE PTR [rbp-0x60],al
    6772:	89 c2                	mov    edx,eax
    6774:	41 bc 27 00 00 00    	mov    r12d,0x27
    677a:	88 45 82             	mov    BYTE PTR [rbp-0x7e],al
    677d:	e9 4e f2 ff ff       	jmp    59d0 <error_at_line@@Base+0x4a67>
    6782:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]
    6788:	41 8d 4c 24 bf       	lea    ecx,[r12-0x41]
    678d:	b8 01 00 00 00       	mov    eax,0x1
    6792:	48 ba ff ff ff 53 ff 	movabs rdx,0x3ffffff53ffffff
    6799:	ff ff 03 
    679c:	48 d3 e0             	shl    rax,cl
    679f:	48 85 d0             	test   rax,rdx
    67a2:	0f 84 78 fd ff ff    	je     6520 <error_at_line@@Base+0x55b7>
    67a8:	80 7d 9a 00          	cmp    BYTE PTR [rbp-0x66],0x0
    67ac:	0f 84 48 fe ff ff    	je     65fa <error_at_line@@Base+0x5691>
    67b2:	80 7d 9f 00          	cmp    BYTE PTR [rbp-0x61],0x0
    67b6:	0f 84 c0 06 00 00    	je     6e7c <error_at_line@@Base+0x5f13>
    67bc:	48 83 7d 90 00       	cmp    QWORD PTR [rbp-0x70],0x0
    67c1:	0f 84 73 08 00 00    	je     703a <error_at_line@@Base+0x60d1>
    67c7:	c6 45 a0 00          	mov    BYTE PTR [rbp-0x60],0x0
    67cb:	0f b6 55 9f          	movzx  edx,BYTE PTR [rbp-0x61]
    67cf:	e9 11 f2 ff ff       	jmp    59e5 <error_at_line@@Base+0x4a7c>
    67d4:	0f 1f 40 00          	nop    DWORD PTR [rax+0x0]
    67d8:	31 d2                	xor    edx,edx
    67da:	41 bc 0b 00 00 00    	mov    r12d,0xb
    67e0:	20 55 9d             	and    BYTE PTR [rbp-0x63],dl
    67e3:	49 83 c5 01          	add    r13,0x1
    67e7:	44 89 d8             	mov    eax,r11d
    67ea:	e9 2a f3 ff ff       	jmp    5b19 <error_at_line@@Base+0x4bb0>
    67ef:	90                   	nop
    67f0:	80 7d 9f 00          	cmp    BYTE PTR [rbp-0x61],0x0
    67f4:	75 49                	jne    683f <error_at_line@@Base+0x58d6>
    67f6:	c6 45 82 00          	mov    BYTE PTR [rbp-0x7e],0x0
    67fa:	4d 85 f6             	test   r14,r14
    67fd:	0f 95 c0             	setne  al
    6800:	48 83 bd 58 ff ff ff 	cmp    QWORD PTR [rbp-0xa8],0x0
    6807:	00 
    6808:	0f 94 c2             	sete   dl
    680b:	20 d0                	and    al,dl
    680d:	0f 84 fd 02 00 00    	je     6b10 <error_at_line@@Base+0x5ba7>
    6813:	49 83 c5 01          	add    r13,0x1
    6817:	80 7d 82 00          	cmp    BYTE PTR [rbp-0x7e],0x0
    681b:	0f 84 14 05 00 00    	je     6d35 <error_at_line@@Base+0x5dcc>
    6821:	4c 89 b5 58 ff ff ff 	mov    QWORD PTR [rbp-0xa8],r14
    6828:	44 0f b6 5d 82       	movzx  r11d,BYTE PTR [rbp-0x7e]
    682d:	48 83 c3 06          	add    rbx,0x6
    6831:	45 31 f6             	xor    r14d,r14d
    6834:	41 bc 27 00 00 00    	mov    r12d,0x27
    683a:	e9 23 f2 ff ff       	jmp    5a62 <error_at_line@@Base+0x4af9>
    683f:	0f b6 45 9b          	movzx  eax,BYTE PTR [rbp-0x65]
    6843:	4d 89 fb             	mov    r11,r15
    6846:	4d 89 c7             	mov    r15,r8
    6849:	88 45 9c             	mov    BYTE PTR [rbp-0x64],al
    684c:	e9 7e f3 ff ff       	jmp    5bcf <error_at_line@@Base+0x4c66>
    6851:	0f 1f 80 00 00 00 00 	nop    DWORD PTR [rax+0x0]
    6858:	31 c0                	xor    eax,eax
    685a:	c6 45 9d 00          	mov    BYTE PTR [rbp-0x63],0x0
    685e:	49 83 c5 01          	add    r13,0x1
    6862:	41 bc 08 00 00 00    	mov    r12d,0x8
    6868:	83 f0 01             	xor    eax,0x1
    686b:	44 21 d8             	and    eax,r11d
    686e:	e9 a6 f2 ff ff       	jmp    5b19 <error_at_line@@Base+0x4bb0>
    6873:	0f 1f 44 00 00       	nop    DWORD PTR [rax+rax*1+0x0]
    6878:	31 c0                	xor    eax,eax
    687a:	c6 45 9d 00          	mov    BYTE PTR [rbp-0x63],0x0
    687e:	49 83 c5 01          	add    r13,0x1
    6882:	41 bc 0c 00 00 00    	mov    r12d,0xc
    6888:	83 f0 01             	xor    eax,0x1
    688b:	44 21 d8             	and    eax,r11d
    688e:	e9 86 f2 ff ff       	jmp    5b19 <error_at_line@@Base+0x4bb0>
    6893:	0f 1f 44 00 00       	nop    DWORD PTR [rax+rax*1+0x0]
    6898:	31 c0                	xor    eax,eax
    689a:	c6 45 9d 00          	mov    BYTE PTR [rbp-0x63],0x0
    689e:	49 83 c5 01          	add    r13,0x1
    68a2:	41 bc 0b 00 00 00    	mov    r12d,0xb
    68a8:	83 f0 01             	xor    eax,0x1
    68ab:	44 21 d8             	and    eax,r11d
    68ae:	e9 66 f2 ff ff       	jmp    5b19 <error_at_line@@Base+0x4bb0>
    68b3:	0f 1f 44 00 00       	nop    DWORD PTR [rax+rax*1+0x0]
    68b8:	0f b6 45 9b          	movzx  eax,BYTE PTR [rbp-0x65]
    68bc:	45 31 d2             	xor    r10d,r10d
    68bf:	4a 8d 14 29          	lea    rdx,[rcx+r13*1]
    68c3:	49 83 c5 01          	add    r13,0x1
    68c7:	84 c0                	test   al,al
    68c9:	0f 84 c4 00 00 00    	je     6993 <error_at_line@@Base+0x5a2a>
    68cf:	80 7d 9f 00          	cmp    BYTE PTR [rbp-0x61],0x0
    68d3:	0f 85 7b fc ff ff    	jne    6554 <error_at_line@@Base+0x55eb>
    68d9:	0f b6 4d 9c          	movzx  ecx,BYTE PTR [rbp-0x64]
    68dd:	48 8b 75 a8          	mov    rsi,QWORD PTR [rbp-0x58]
    68e1:	eb 1b                	jmp    68fe <error_at_line@@Base+0x5995>
    68e3:	0f 1f 44 00 00       	nop    DWORD PTR [rax+rax*1+0x0]
    68e8:	4c 39 f0             	cmp    rax,r14
    68eb:	73 04                	jae    68f1 <error_at_line@@Base+0x5988>
    68ed:	45 88 24 07          	mov    BYTE PTR [r15+rax*1],r12b
    68f1:	46 0f b6 24 2e       	movzx  r12d,BYTE PTR [rsi+r13*1]
    68f6:	48 83 c3 04          	add    rbx,0x4
    68fa:	49 83 c5 01          	add    r13,0x1
    68fe:	44 89 d8             	mov    eax,r11d
    6901:	83 f0 01             	xor    eax,0x1
    6904:	20 c8                	and    al,cl
    6906:	74 2f                	je     6937 <error_at_line@@Base+0x59ce>
    6908:	4c 39 f3             	cmp    rbx,r14
    690b:	73 05                	jae    6912 <error_at_line@@Base+0x59a9>
    690d:	41 c6 04 1f 27       	mov    BYTE PTR [r15+rbx*1],0x27
    6912:	48 8d 7b 01          	lea    rdi,[rbx+0x1]
    6916:	4c 39 f7             	cmp    rdi,r14
    6919:	73 06                	jae    6921 <error_at_line@@Base+0x59b8>
    691b:	41 c6 44 1f 01 24    	mov    BYTE PTR [r15+rbx*1+0x1],0x24
    6921:	48 8d 7b 02          	lea    rdi,[rbx+0x2]
    6925:	4c 39 f7             	cmp    rdi,r14
    6928:	73 06                	jae    6930 <error_at_line@@Base+0x59c7>
    692a:	41 c6 44 1f 02 27    	mov    BYTE PTR [r15+rbx*1+0x2],0x27
    6930:	48 83 c3 03          	add    rbx,0x3
    6934:	41 89 c3             	mov    r11d,eax
    6937:	4c 39 f3             	cmp    rbx,r14
    693a:	73 05                	jae    6941 <error_at_line@@Base+0x59d8>
    693c:	41 c6 04 1f 5c       	mov    BYTE PTR [r15+rbx*1],0x5c
    6941:	48 8d 43 01          	lea    rax,[rbx+0x1]
    6945:	4c 39 f0             	cmp    rax,r14
    6948:	73 0e                	jae    6958 <error_at_line@@Base+0x59ef>
    694a:	44 89 e0             	mov    eax,r12d
    694d:	c0 e8 06             	shr    al,0x6
    6950:	83 c0 30             	add    eax,0x30
    6953:	41 88 44 1f 01       	mov    BYTE PTR [r15+rbx*1+0x1],al
    6958:	48 8d 43 02          	lea    rax,[rbx+0x2]
    695c:	4c 39 f0             	cmp    rax,r14
    695f:	73 11                	jae    6972 <error_at_line@@Base+0x5a09>
    6961:	44 89 e0             	mov    eax,r12d
    6964:	c0 e8 03             	shr    al,0x3
    6967:	83 e0 07             	and    eax,0x7
    696a:	83 c0 30             	add    eax,0x30
    696d:	41 88 44 1f 02       	mov    BYTE PTR [r15+rbx*1+0x2],al
    6972:	41 83 e4 07          	and    r12d,0x7
    6976:	48 8d 43 03          	lea    rax,[rbx+0x3]
    697a:	41 83 c4 30          	add    r12d,0x30
    697e:	49 39 d5             	cmp    r13,rdx
    6981:	0f 82 61 ff ff ff    	jb     68e8 <error_at_line@@Base+0x597f>
    6987:	c6 45 9d 00          	mov    BYTE PTR [rbp-0x63],0x0
    698b:	48 89 c3             	mov    rbx,rax
    698e:	e9 d3 f0 ff ff       	jmp    5a66 <error_at_line@@Base+0x4afd>
    6993:	44 89 d8             	mov    eax,r11d
    6996:	80 7d a0 00          	cmp    BYTE PTR [rbp-0x60],0x0
    699a:	74 0e                	je     69aa <error_at_line@@Base+0x5a41>
    699c:	4c 39 f3             	cmp    rbx,r14
    699f:	73 05                	jae    69a6 <error_at_line@@Base+0x5a3d>
    69a1:	41 c6 04 1f 5c       	mov    BYTE PTR [r15+rbx*1],0x5c
    69a6:	48 83 c3 01          	add    rbx,0x1
    69aa:	49 39 d5             	cmp    r13,rdx
    69ad:	73 61                	jae    6a10 <error_at_line@@Base+0x5aa7>
    69af:	84 c0                	test   al,al
    69b1:	74 3e                	je     69f1 <error_at_line@@Base+0x5a88>
    69b3:	4c 39 f3             	cmp    rbx,r14
    69b6:	73 05                	jae    69bd <error_at_line@@Base+0x5a54>
    69b8:	41 c6 04 1f 27       	mov    BYTE PTR [r15+rbx*1],0x27
    69bd:	48 8d 43 01          	lea    rax,[rbx+0x1]
    69c1:	4c 39 f0             	cmp    rax,r14
    69c4:	73 06                	jae    69cc <error_at_line@@Base+0x5a63>
    69c6:	41 c6 44 1f 01 27    	mov    BYTE PTR [r15+rbx*1+0x1],0x27
    69cc:	48 8d 43 02          	lea    rax,[rbx+0x2]
    69d0:	4c 39 f0             	cmp    rax,r14
    69d3:	72 4b                	jb     6a20 <error_at_line@@Base+0x5ab7>
    69d5:	48 8b 45 a8          	mov    rax,QWORD PTR [rbp-0x58]
    69d9:	48 83 c3 03          	add    rbx,0x3
    69dd:	46 0f b6 24 28       	movzx  r12d,BYTE PTR [rax+r13*1]
    69e2:	49 83 c5 01          	add    r13,0x1
    69e6:	49 39 d5             	cmp    r13,rdx
    69e9:	0f 83 5f 03 00 00    	jae    6d4e <error_at_line@@Base+0x5de5>
    69ef:	31 c0                	xor    eax,eax
    69f1:	4c 39 f3             	cmp    rbx,r14
    69f4:	0f 82 c5 05 00 00    	jb     6fbf <error_at_line@@Base+0x6056>
    69fa:	48 8b 4d a8          	mov    rcx,QWORD PTR [rbp-0x58]
    69fe:	48 83 c3 01          	add    rbx,0x1
    6a02:	46 0f b6 24 29       	movzx  r12d,BYTE PTR [rcx+r13*1]
    6a07:	49 83 c5 01          	add    r13,0x1
    6a0b:	49 39 d5             	cmp    r13,rdx
    6a0e:	72 9f                	jb     69af <error_at_line@@Base+0x5a46>
    6a10:	41 89 c3             	mov    r11d,eax
    6a13:	44 20 55 9d          	and    BYTE PTR [rbp-0x63],r10b
    6a17:	e9 fd f0 ff ff       	jmp    5b19 <error_at_line@@Base+0x4bb0>
    6a1c:	0f 1f 40 00          	nop    DWORD PTR [rax+0x0]
    6a20:	48 8b 45 a8          	mov    rax,QWORD PTR [rbp-0x58]
    6a24:	45 88 64 1f 02       	mov    BYTE PTR [r15+rbx*1+0x2],r12b
    6a29:	48 83 c3 03          	add    rbx,0x3
    6a2d:	46 0f b6 24 28       	movzx  r12d,BYTE PTR [rax+r13*1]
    6a32:	49 83 c5 01          	add    r13,0x1
    6a36:	31 c0                	xor    eax,eax
    6a38:	e9 6d ff ff ff       	jmp    69aa <error_at_line@@Base+0x5a41>
    6a3d:	0f 1f 00             	nop    DWORD PTR [rax]
    6a40:	31 d2                	xor    edx,edx
    6a42:	41 bc 76 00 00 00    	mov    r12d,0x76
    6a48:	e9 bb ef ff ff       	jmp    5a08 <error_at_line@@Base+0x4a9f>
    6a4d:	0f 1f 00             	nop    DWORD PTR [rax]
    6a50:	31 d2                	xor    edx,edx
    6a52:	41 bc 62 00 00 00    	mov    r12d,0x62
    6a58:	e9 ab ef ff ff       	jmp    5a08 <error_at_line@@Base+0x4a9f>
    6a5d:	0f 1f 00             	nop    DWORD PTR [rax]
    6a60:	31 d2                	xor    edx,edx
    6a62:	41 bc 66 00 00 00    	mov    r12d,0x66
    6a68:	e9 9b ef ff ff       	jmp    5a08 <error_at_line@@Base+0x4a9f>
    6a6d:	0f 1f 00             	nop    DWORD PTR [rax]
    6a70:	c6 45 9d 00          	mov    BYTE PTR [rbp-0x63],0x0
    6a74:	41 bc 5c 00 00 00    	mov    r12d,0x5c
    6a7a:	e9 a2 f0 ff ff       	jmp    5b21 <error_at_line@@Base+0x4bb8>
    6a7f:	90                   	nop
    6a80:	0f b6 55 9f          	movzx  edx,BYTE PTR [rbp-0x61]
    6a84:	80 f2 01             	xor    dl,0x1
    6a87:	74 0a                	je     6a93 <error_at_line@@Base+0x5b2a>
    6a89:	80 7d 9c 00          	cmp    BYTE PTR [rbp-0x64],0x0
    6a8d:	0f 85 2b f0 ff ff    	jne    5abe <error_at_line@@Base+0x4b55>
    6a93:	49 89 d8             	mov    r8,rbx
    6a96:	89 d0                	mov    eax,edx
    6a98:	4d 89 f2             	mov    r10,r14
    6a9b:	4d 89 fb             	mov    r11,r15
    6a9e:	48 83 bd 60 ff ff ff 	cmp    QWORD PTR [rbp-0xa0],0x0
    6aa5:	00 
    6aa6:	0f 84 c4 05 00 00    	je     7070 <error_at_line@@Base+0x6107>
    6aac:	84 c0                	test   al,al
    6aae:	0f 84 bc 05 00 00    	je     7070 <error_at_line@@Base+0x6107>
    6ab4:	48 8b 95 60 ff ff ff 	mov    rdx,QWORD PTR [rbp-0xa0]
    6abb:	0f b6 0a             	movzx  ecx,BYTE PTR [rdx]
    6abe:	84 c9                	test   cl,cl
    6ac0:	0f 84 aa 05 00 00    	je     7070 <error_at_line@@Base+0x6107>
    6ac6:	4c 89 c0             	mov    rax,r8
    6ac9:	4c 29 c2             	sub    rdx,r8
    6acc:	4c 39 d0             	cmp    rax,r10
    6acf:	73 04                	jae    6ad5 <error_at_line@@Base+0x5b6c>
    6ad1:	41 88 0c 03          	mov    BYTE PTR [r11+rax*1],cl
    6ad5:	48 83 c0 01          	add    rax,0x1
    6ad9:	0f b6 0c 02          	movzx  ecx,BYTE PTR [rdx+rax*1]
    6add:	84 c9                	test   cl,cl
    6adf:	75 eb                	jne    6acc <error_at_line@@Base+0x5b63>
    6ae1:	4c 39 d0             	cmp    rax,r10
    6ae4:	73 05                	jae    6aeb <error_at_line@@Base+0x5b82>
    6ae6:	41 c6 04 03 00       	mov    BYTE PTR [r11+rax*1],0x0
    6aeb:	48 8b 55 c8          	mov    rdx,QWORD PTR [rbp-0x38]
    6aef:	64 48 2b 14 25 28 00 	sub    rdx,QWORD PTR fs:0x28
    6af6:	00 00 
    6af8:	0f 85 64 06 00 00    	jne    7162 <error_at_line@@Base+0x61f9>
    6afe:	48 81 c4 b8 00 00 00 	add    rsp,0xb8
    6b05:	5b                   	pop    rbx
    6b06:	41 5c                	pop    r12
    6b08:	41 5d                	pop    r13
    6b0a:	41 5e                	pop    r14
    6b0c:	41 5f                	pop    r15
    6b0e:	5d                   	pop    rbp
    6b0f:	c3                   	ret
    6b10:	4c 39 f3             	cmp    rbx,r14
    6b13:	73 05                	jae    6b1a <error_at_line@@Base+0x5bb1>
    6b15:	41 c6 04 1f 27       	mov    BYTE PTR [r15+rbx*1],0x27
    6b1a:	48 8d 43 01          	lea    rax,[rbx+0x1]
    6b1e:	4c 39 f0             	cmp    rax,r14
    6b21:	73 06                	jae    6b29 <error_at_line@@Base+0x5bc0>
    6b23:	41 c6 44 1f 01 5c    	mov    BYTE PTR [r15+rbx*1+0x1],0x5c
    6b29:	48 8d 43 02          	lea    rax,[rbx+0x2]
    6b2d:	4c 39 f0             	cmp    rax,r14
    6b30:	73 06                	jae    6b38 <error_at_line@@Base+0x5bcf>
    6b32:	41 c6 44 1f 02 27    	mov    BYTE PTR [r15+rbx*1+0x2],0x27
    6b38:	48 83 c3 03          	add    rbx,0x3
    6b3c:	49 83 c5 01          	add    r13,0x1
    6b40:	41 bc 27 00 00 00    	mov    r12d,0x27
    6b46:	80 7d 82 00          	cmp    BYTE PTR [rbp-0x7e],0x0
    6b4a:	0f 85 d9 ee ff ff    	jne    5a29 <error_at_line@@Base+0x4ac0>
    6b50:	44 88 55 82          	mov    BYTE PTR [rbp-0x7e],r10b
    6b54:	45 31 db             	xor    r11d,r11d
    6b57:	e9 0a ef ff ff       	jmp    5a66 <error_at_line@@Base+0x4afd>
    6b5c:	41 8d 4c 24 bf       	lea    ecx,[r12-0x41]
    6b61:	b8 01 00 00 00       	mov    eax,0x1
    6b66:	48 bf ff ff ff 53 ff 	movabs rdi,0x3ffffff53ffffff
    6b6d:	ff ff 03 
    6b70:	48 d3 e0             	shl    rax,cl
    6b73:	48 85 f8             	test   rax,rdi
    6b76:	0f 85 33 02 00 00    	jne    6daf <error_at_line@@Base+0x5e46>
    6b7c:	a9 00 00 00 a4       	test   eax,0xa4000000
    6b81:	0f 85 62 f6 ff ff    	jne    61e9 <error_at_line@@Base+0x5280>
    6b87:	83 7d 84 02          	cmp    DWORD PTR [rbp-0x7c],0x2
    6b8b:	0f 84 69 fb ff ff    	je     66fa <error_at_line@@Base+0x5791>
    6b91:	80 7d 9b 00          	cmp    BYTE PTR [rbp-0x65],0x0
    6b95:	75 56                	jne    6bed <error_at_line@@Base+0x5c84>
    6b97:	0f b6 45 9e          	movzx  eax,BYTE PTR [rbp-0x62]
    6b9b:	31 d2                	xor    edx,edx
    6b9d:	88 45 a0             	mov    BYTE PTR [rbp-0x60],al
    6ba0:	31 c0                	xor    eax,eax
    6ba2:	e9 79 f6 ff ff       	jmp    6220 <error_at_line@@Base+0x52b7>
    6ba7:	41 89 c3             	mov    r11d,eax
    6baa:	31 d2                	xor    edx,edx
    6bac:	41 bc 30 00 00 00    	mov    r12d,0x30
    6bb2:	e9 69 f6 ff ff       	jmp    6220 <error_at_line@@Base+0x52b7>
    6bb7:	41 80 fc 7d          	cmp    r12b,0x7d
    6bbb:	0f 84 b5 f9 ff ff    	je     6576 <error_at_line@@Base+0x560d>
    6bc1:	c6 45 a0 00          	mov    BYTE PTR [rbp-0x60],0x0
    6bc5:	41 80 fc 7d          	cmp    r12b,0x7d
    6bc9:	0f 8e d3 fa ff ff    	jle    66a2 <error_at_line@@Base+0x5739>
    6bcf:	41 80 fc 7e          	cmp    r12b,0x7e
    6bd3:	0f 84 71 f1 ff ff    	je     5d4a <error_at_line@@Base+0x4de1>
    6bd9:	e9 86 ed ff ff       	jmp    5964 <error_at_line@@Base+0x49fb>
    6bde:	c6 45 9d 00          	mov    BYTE PTR [rbp-0x63],0x0
    6be2:	41 bc 5c 00 00 00    	mov    r12d,0x5c
    6be8:	e9 7e ee ff ff       	jmp    5a6b <error_at_line@@Base+0x4b02>
    6bed:	44 89 d8             	mov    eax,r11d
    6bf0:	c6 45 9d 00          	mov    BYTE PTR [rbp-0x63],0x0
    6bf4:	49 83 c5 01          	add    r13,0x1
    6bf8:	41 bc 5c 00 00 00    	mov    r12d,0x5c
    6bfe:	83 f0 01             	xor    eax,0x1
    6c01:	22 45 9c             	and    al,BYTE PTR [rbp-0x64]
    6c04:	e9 1c ee ff ff       	jmp    5a25 <error_at_line@@Base+0x4abc>
    6c09:	31 d2                	xor    edx,edx
    6c0b:	41 bc 08 00 00 00    	mov    r12d,0x8
    6c11:	20 55 9d             	and    BYTE PTR [rbp-0x63],dl
    6c14:	49 83 c5 01          	add    r13,0x1
    6c18:	44 89 d8             	mov    eax,r11d
    6c1b:	e9 f9 ee ff ff       	jmp    5b19 <error_at_line@@Base+0x4bb0>
    6c20:	31 d2                	xor    edx,edx
    6c22:	41 bc 0c 00 00 00    	mov    r12d,0xc
    6c28:	20 55 9d             	and    BYTE PTR [rbp-0x63],dl
    6c2b:	49 83 c5 01          	add    r13,0x1
    6c2f:	44 89 d8             	mov    eax,r11d
    6c32:	e9 e2 ee ff ff       	jmp    5b19 <error_at_line@@Base+0x4bb0>
    6c37:	31 d2                	xor    edx,edx
    6c39:	48 89 f3             	mov    rbx,rsi
    6c3c:	41 bc 30 00 00 00    	mov    r12d,0x30
    6c42:	e9 cf ed ff ff       	jmp    5a16 <error_at_line@@Base+0x4aad>
    6c47:	80 7d a0 00          	cmp    BYTE PTR [rbp-0x60],0x0
    6c4b:	c6 45 9d 00          	mov    BYTE PTR [rbp-0x63],0x0
    6c4f:	49 89 cd             	mov    r13,rcx
    6c52:	48 89 f3             	mov    rbx,rsi
    6c55:	41 bc 30 00 00 00    	mov    r12d,0x30
    6c5b:	0f 85 f7 ed ff ff    	jne    5a58 <error_at_line@@Base+0x4aef>
    6c61:	e9 00 ee ff ff       	jmp    5a66 <error_at_line@@Base+0x4afd>
    6c66:	0f b6 45 9b          	movzx  eax,BYTE PTR [rbp-0x65]
    6c6a:	31 d2                	xor    edx,edx
    6c6c:	31 c9                	xor    ecx,ecx
    6c6e:	e9 54 ed ff ff       	jmp    59c7 <error_at_line@@Base+0x4a5e>
    6c73:	31 c0                	xor    eax,eax
    6c75:	c6 45 9d 00          	mov    BYTE PTR [rbp-0x63],0x0
    6c79:	49 83 c5 01          	add    r13,0x1
    6c7d:	41 bc 07 00 00 00    	mov    r12d,0x7
    6c83:	83 f0 01             	xor    eax,0x1
    6c86:	44 21 d8             	and    eax,r11d
    6c89:	e9 8b ee ff ff       	jmp    5b19 <error_at_line@@Base+0x4bb0>
    6c8e:	48 8b 85 38 ff ff ff 	mov    rax,QWORD PTR [rbp-0xc8]
    6c95:	31 c9                	xor    ecx,ecx
    6c97:	4d 39 c5             	cmp    r13,r8
    6c9a:	72 1d                	jb     6cb9 <error_at_line@@Base+0x5d50>
    6c9c:	e9 56 04 00 00       	jmp    70f7 <error_at_line@@Base+0x618e>
    6ca1:	0f 1f 40 00          	nop    DWORD PTR [rax+0x0]
    6ca5:	66 66 2e 0f 1f 84 00 	data16 cs nop WORD PTR [rax+rax*1+0x0]
    6cac:	00 00 00 00 
    6cb0:	48 83 c1 01          	add    rcx,0x1
    6cb4:	48 39 c8             	cmp    rax,rcx
    6cb7:	74 07                	je     6cc0 <error_at_line@@Base+0x5d57>
    6cb9:	41 80 3c 09 00       	cmp    BYTE PTR [r9+rcx*1],0x0
    6cbe:	75 f0                	jne    6cb0 <error_at_line@@Base+0x5d47>
    6cc0:	0f b6 45 9b          	movzx  eax,BYTE PTR [rbp-0x65]
    6cc4:	48 83 f9 01          	cmp    rcx,0x1
    6cc8:	0f 87 42 03 00 00    	ja     7010 <error_at_line@@Base+0x60a7>
    6cce:	31 d2                	xor    edx,edx
    6cd0:	e9 f2 ec ff ff       	jmp    59c7 <error_at_line@@Base+0x4a5e>
    6cd5:	0f b6 45 9e          	movzx  eax,BYTE PTR [rbp-0x62]
    6cd9:	88 45 a0             	mov    BYTE PTR [rbp-0x60],al
    6cdc:	41 80 fc 3f          	cmp    r12b,0x3f
    6ce0:	0f 85 06 04 00 00    	jne    70ec <error_at_line@@Base+0x6183>
    6ce6:	83 7d 84 02          	cmp    DWORD PTR [rbp-0x7c],0x2
    6cea:	0f 85 34 f9 ff ff    	jne    6624 <error_at_line@@Base+0x56bb>
    6cf0:	c6 45 9d 00          	mov    BYTE PTR [rbp-0x63],0x0
    6cf4:	49 83 c5 01          	add    r13,0x1
    6cf8:	e9 34 f5 ff ff       	jmp    6231 <error_at_line@@Base+0x52c8>
    6cfd:	80 7d 9f 00          	cmp    BYTE PTR [rbp-0x61],0x0
    6d01:	0f 84 75 01 00 00    	je     6e7c <error_at_line@@Base+0x5f13>
    6d07:	48 83 7d 90 00       	cmp    QWORD PTR [rbp-0x70],0x0
    6d0c:	0f 84 28 03 00 00    	je     703a <error_at_line@@Base+0x60d1>
    6d12:	c6 45 a0 00          	mov    BYTE PTR [rbp-0x60],0x0
    6d16:	0f b6 55 9f          	movzx  edx,BYTE PTR [rbp-0x61]
    6d1a:	e9 c6 ec ff ff       	jmp    59e5 <error_at_line@@Base+0x4a7c>
    6d1f:	31 d2                	xor    edx,edx
    6d21:	41 bc 61 00 00 00    	mov    r12d,0x61
    6d27:	e9 dc ec ff ff       	jmp    5a08 <error_at_line@@Base+0x4a9f>
    6d2c:	c6 45 a0 00          	mov    BYTE PTR [rbp-0x60],0x0
    6d30:	e9 4f f8 ff ff       	jmp    6584 <error_at_line@@Base+0x561b>
    6d35:	4c 89 b5 58 ff ff ff 	mov    QWORD PTR [rbp-0xa8],r14
    6d3c:	48 83 c3 03          	add    rbx,0x3
    6d40:	45 31 db             	xor    r11d,r11d
    6d43:	45 31 f6             	xor    r14d,r14d
    6d46:	88 45 82             	mov    BYTE PTR [rbp-0x7e],al
    6d49:	e9 21 ed ff ff       	jmp    5a6f <error_at_line@@Base+0x4b06>
    6d4e:	45 31 db             	xor    r11d,r11d
    6d51:	31 c0                	xor    eax,eax
    6d53:	e9 bb fc ff ff       	jmp    6a13 <error_at_line@@Base+0x5aaa>
    6d58:	4c 39 f6             	cmp    rsi,r14
    6d5b:	73 05                	jae    6d62 <error_at_line@@Base+0x5df9>
    6d5d:	41 c6 04 37 30       	mov    BYTE PTR [r15+rsi*1],0x30
    6d62:	48 8d 43 02          	lea    rax,[rbx+0x2]
    6d66:	4c 39 f0             	cmp    rax,r14
    6d69:	73 06                	jae    6d71 <error_at_line@@Base+0x5e08>
    6d6b:	41 c6 44 1f 02 30    	mov    BYTE PTR [r15+rbx*1+0x2],0x30
    6d71:	48 8b 45 90          	mov    rax,QWORD PTR [rbp-0x70]
    6d75:	48 83 c3 03          	add    rbx,0x3
    6d79:	48 85 c0             	test   rax,rax
    6d7c:	0f 84 d2 02 00 00    	je     7054 <error_at_line@@Base+0x60eb>
    6d82:	31 d2                	xor    edx,edx
    6d84:	f6 40 06 01          	test   BYTE PTR [rax+0x6],0x1
    6d88:	0f 85 ae fe ff ff    	jne    6c3c <error_at_line@@Base+0x5cd3>
    6d8e:	0f b6 45 81          	movzx  eax,BYTE PTR [rbp-0x7f]
    6d92:	41 bc 30 00 00 00    	mov    r12d,0x30
    6d98:	e9 65 ed ff ff       	jmp    5b02 <error_at_line@@Base+0x4b99>
    6d9d:	c6 45 9d 00          	mov    BYTE PTR [rbp-0x63],0x0
    6da1:	41 89 c3             	mov    r11d,eax
    6da4:	41 bc 30 00 00 00    	mov    r12d,0x30
    6daa:	e9 b7 ec ff ff       	jmp    5a66 <error_at_line@@Base+0x4afd>
    6daf:	80 7d 9a 00          	cmp    BYTE PTR [rbp-0x66],0x0
    6db3:	0f 85 2a 03 00 00    	jne    70e3 <error_at_line@@Base+0x617a>
    6db9:	0f b6 55 9e          	movzx  edx,BYTE PTR [rbp-0x62]
    6dbd:	48 83 7d 90 00       	cmp    QWORD PTR [rbp-0x70],0x0
    6dc2:	0f 84 4a ec ff ff    	je     5a12 <error_at_line@@Base+0x4aa9>
    6dc8:	88 55 a0             	mov    BYTE PTR [rbp-0x60],dl
    6dcb:	e9 15 ec ff ff       	jmp    59e5 <error_at_line@@Base+0x4a7c>
    6dd0:	41 80 fc 7e          	cmp    r12b,0x7e
    6dd4:	0f 84 70 ef ff ff    	je     5d4a <error_at_line@@Base+0x4de1>
    6dda:	41 bc 7f 00 00 00    	mov    r12d,0x7f
    6de0:	e9 7f eb ff ff       	jmp    5964 <error_at_line@@Base+0x49fb>
    6de5:	48 83 f8 01          	cmp    rax,0x1
    6de9:	0f 84 13 03 00 00    	je     7102 <error_at_line@@Base+0x6199>
    6def:	48 8b 45 a8          	mov    rax,QWORD PTR [rbp-0x58]
    6df3:	49 01 c9             	add    r9,rcx
    6df6:	48 be 2b 00 00 00 02 	movabs rsi,0x20000002b
    6dfd:	00 00 00 
    6e00:	4a 8d 54 28 01       	lea    rdx,[rax+r13*1+0x1]
    6e05:	eb 09                	jmp    6e10 <error_at_line@@Base+0x5ea7>
    6e07:	48 83 c2 01          	add    rdx,0x1
    6e0b:	4c 39 ca             	cmp    rdx,r9
    6e0e:	74 1d                	je     6e2d <error_at_line@@Base+0x5ec4>
    6e10:	0f b6 02             	movzx  eax,BYTE PTR [rdx]
    6e13:	83 e8 5b             	sub    eax,0x5b
    6e16:	3c 21                	cmp    al,0x21
    6e18:	77 ed                	ja     6e07 <error_at_line@@Base+0x5e9e>
    6e1a:	48 0f a3 c6          	bt     rsi,rax
    6e1e:	0f 82 3c ed ff ff    	jb     5b60 <error_at_line@@Base+0x4bf7>
    6e24:	48 83 c2 01          	add    rdx,0x1
    6e28:	4c 39 ca             	cmp    rdx,r9
    6e2b:	75 e3                	jne    6e10 <error_at_line@@Base+0x5ea7>
    6e2d:	8b 7d bc             	mov    edi,DWORD PTR [rbp-0x44]
    6e30:	44 88 9d 68 ff ff ff 	mov    BYTE PTR [rbp-0x98],r11b
    6e37:	4c 89 85 70 ff ff ff 	mov    QWORD PTR [rbp-0x90],r8
    6e3e:	48 89 8d 78 ff ff ff 	mov    QWORD PTR [rbp-0x88],rcx
    6e45:	e8 66 9d ff ff       	call   bb0 <iswprint@plt>
    6e4a:	0f b6 4d 9b          	movzx  ecx,BYTE PTR [rbp-0x65]
    6e4e:	44 0f b6 55 99       	movzx  r10d,BYTE PTR [rbp-0x67]
    6e53:	85 c0                	test   eax,eax
    6e55:	b8 00 00 00 00       	mov    eax,0x0
    6e5a:	4c 8b 85 70 ff ff ff 	mov    r8,QWORD PTR [rbp-0x90]
    6e61:	44 0f b6 9d 68 ff ff 	movzx  r11d,BYTE PTR [rbp-0x98]
    6e68:	ff 
    6e69:	44 0f 44 d0          	cmove  r10d,eax
    6e6d:	0f 44 c1             	cmove  eax,ecx
    6e70:	48 8b 8d 78 ff ff ff 	mov    rcx,QWORD PTR [rbp-0x88]
    6e77:	e9 43 fa ff ff       	jmp    68bf <error_at_line@@Base+0x5956>
    6e7c:	c6 45 a0 00          	mov    BYTE PTR [rbp-0x60],0x0
    6e80:	0f b6 55 9a          	movzx  edx,BYTE PTR [rbp-0x66]
    6e84:	31 c0                	xor    eax,eax
    6e86:	e9 95 f3 ff ff       	jmp    6220 <error_at_line@@Base+0x52b7>
    6e8b:	0f b6 45 9f          	movzx  eax,BYTE PTR [rbp-0x61]
    6e8f:	c6 45 9a 00          	mov    BYTE PTR [rbp-0x66],0x0
    6e93:	31 db                	xor    ebx,ebx
    6e95:	c6 45 99 00          	mov    BYTE PTR [rbp-0x67],0x0
    6e99:	88 45 9e             	mov    BYTE PTR [rbp-0x62],al
    6e9c:	88 45 81             	mov    BYTE PTR [rbp-0x7f],al
    6e9f:	88 45 9b             	mov    BYTE PTR [rbp-0x65],al
    6ea2:	48 8d 05 83 49 00 00 	lea    rax,[rip+0x4983]        # b82c <error_at_line@@Base+0xa8c3>
    6ea9:	c6 45 9c 00          	mov    BYTE PTR [rbp-0x64],0x0
    6ead:	c6 45 83 00          	mov    BYTE PTR [rbp-0x7d],0x0
    6eb1:	48 c7 45 88 01 00 00 	mov    QWORD PTR [rbp-0x78],0x1
    6eb8:	00 
    6eb9:	48 89 85 60 ff ff ff 	mov    QWORD PTR [rbp-0xa0],rax
    6ec0:	e9 1b ea ff ff       	jmp    58e0 <error_at_line@@Base+0x4977>
    6ec5:	0f b6 45 9f          	movzx  eax,BYTE PTR [rbp-0x61]
    6ec9:	c6 45 9e 00          	mov    BYTE PTR [rbp-0x62],0x0
    6ecd:	c6 45 83 00          	mov    BYTE PTR [rbp-0x7d],0x0
    6ed1:	88 45 9a             	mov    BYTE PTR [rbp-0x66],al
    6ed4:	88 45 99             	mov    BYTE PTR [rbp-0x67],al
    6ed7:	88 45 9c             	mov    BYTE PTR [rbp-0x64],al
    6eda:	c6 45 81 00          	mov    BYTE PTR [rbp-0x7f],0x0
    6ede:	e9 f3 ef ff ff       	jmp    5ed6 <error_at_line@@Base+0x4f6d>
    6ee3:	0f b6 45 9f          	movzx  eax,BYTE PTR [rbp-0x61]
    6ee7:	c6 45 9e 00          	mov    BYTE PTR [rbp-0x62],0x0
    6eeb:	31 db                	xor    ebx,ebx
    6eed:	c6 45 83 00          	mov    BYTE PTR [rbp-0x7d],0x0
    6ef1:	88 45 9a             	mov    BYTE PTR [rbp-0x66],al
    6ef4:	88 45 99             	mov    BYTE PTR [rbp-0x67],al
    6ef7:	88 45 9c             	mov    BYTE PTR [rbp-0x64],al
    6efa:	48 8d 05 2d 49 00 00 	lea    rax,[rip+0x492d]        # b82e <error_at_line@@Base+0xa8c5>
    6f01:	c6 45 81 00          	mov    BYTE PTR [rbp-0x7f],0x0
    6f05:	48 c7 45 88 01 00 00 	mov    QWORD PTR [rbp-0x78],0x1
    6f0c:	00 
    6f0d:	48 89 85 60 ff ff ff 	mov    QWORD PTR [rbp-0xa0],rax
    6f14:	e9 c7 e9 ff ff       	jmp    58e0 <error_at_line@@Base+0x4977>
    6f19:	48 8b 4d a8          	mov    rcx,QWORD PTR [rbp-0x58]
    6f1d:	46 0f b6 64 29 02    	movzx  r12d,BYTE PTR [rcx+r13*1+0x2]
    6f23:	41 8d 54 24 df       	lea    edx,[r12-0x21]
    6f28:	80 fa 1d             	cmp    dl,0x1d
    6f2b:	0f 87 1f f7 ff ff    	ja     6650 <error_at_line@@Base+0x56e7>
    6f31:	b9 c1 51 00 38       	mov    ecx,0x380051c1
    6f36:	48 0f a3 d1          	bt     rcx,rdx
    6f3a:	0f 92 c2             	setb   dl
    6f3d:	84 d2                	test   dl,dl
    6f3f:	0f 84 33 01 00 00    	je     7078 <error_at_line@@Base+0x610f>
    6f45:	80 7d 9f 00          	cmp    BYTE PTR [rbp-0x61],0x0
    6f49:	0f 85 08 02 00 00    	jne    7157 <error_at_line@@Base+0x61ee>
    6f4f:	4c 39 f3             	cmp    rbx,r14
    6f52:	73 05                	jae    6f59 <error_at_line@@Base+0x5ff0>
    6f54:	41 c6 04 1f 3f       	mov    BYTE PTR [r15+rbx*1],0x3f
    6f59:	48 8d 53 01          	lea    rdx,[rbx+0x1]
    6f5d:	4c 39 f2             	cmp    rdx,r14
    6f60:	73 06                	jae    6f68 <error_at_line@@Base+0x5fff>
    6f62:	41 c6 44 1f 01 22    	mov    BYTE PTR [r15+rbx*1+0x1],0x22
    6f68:	48 8d 53 02          	lea    rdx,[rbx+0x2]
    6f6c:	4c 39 f2             	cmp    rdx,r14
    6f6f:	73 06                	jae    6f77 <error_at_line@@Base+0x600e>
    6f71:	41 c6 44 1f 02 22    	mov    BYTE PTR [r15+rbx*1+0x2],0x22
    6f77:	48 8d 53 03          	lea    rdx,[rbx+0x3]
    6f7b:	4c 39 f2             	cmp    rdx,r14
    6f7e:	73 06                	jae    6f86 <error_at_line@@Base+0x601d>
    6f80:	41 c6 44 1f 03 3f    	mov    BYTE PTR [r15+rbx*1+0x3],0x3f
    6f86:	48 83 c3 04          	add    rbx,0x4
    6f8a:	31 d2                	xor    edx,edx
    6f8c:	49 89 c5             	mov    r13,rax
    6f8f:	80 7d 9b 00          	cmp    BYTE PTR [rbp-0x65],0x0
    6f93:	0f 85 41 ea ff ff    	jne    59da <error_at_line@@Base+0x4a71>
    6f99:	c6 45 9d 00          	mov    BYTE PTR [rbp-0x63],0x0
    6f9d:	31 c0                	xor    eax,eax
    6f9f:	e9 7f f2 ff ff       	jmp    6223 <error_at_line@@Base+0x52ba>
    6fa4:	0f 1f 40 00          	nop    DWORD PTR [rax+0x0]
    6fa8:	31 d2                	xor    edx,edx
    6faa:	41 bc 07 00 00 00    	mov    r12d,0x7
    6fb0:	20 55 9d             	and    BYTE PTR [rbp-0x63],dl
    6fb3:	49 83 c5 01          	add    r13,0x1
    6fb7:	44 89 d8             	mov    eax,r11d
    6fba:	e9 5a eb ff ff       	jmp    5b19 <error_at_line@@Base+0x4bb0>
    6fbf:	48 8b 7d a8          	mov    rdi,QWORD PTR [rbp-0x58]
    6fc3:	45 88 24 1f          	mov    BYTE PTR [r15+rbx*1],r12b
    6fc7:	48 83 c3 01          	add    rbx,0x1
    6fcb:	46 0f b6 24 2f       	movzx  r12d,BYTE PTR [rdi+r13*1]
    6fd0:	49 83 c5 01          	add    r13,0x1
    6fd4:	e9 d1 f9 ff ff       	jmp    69aa <error_at_line@@Base+0x5a41>
    6fd9:	88 45 82             	mov    BYTE PTR [rbp-0x7e],al
    6fdc:	e9 19 f8 ff ff       	jmp    67fa <error_at_line@@Base+0x5891>
    6fe1:	31 d2                	xor    edx,edx
    6fe3:	41 bc 66 00 00 00    	mov    r12d,0x66
    6fe9:	49 8d 4d 01          	lea    rcx,[r13+0x1]
    6fed:	e9 24 ea ff ff       	jmp    5a16 <error_at_line@@Base+0x4aad>
    6ff2:	31 d2                	xor    edx,edx
    6ff4:	41 bc 62 00 00 00    	mov    r12d,0x62
    6ffa:	e9 13 ea ff ff       	jmp    5a12 <error_at_line@@Base+0x4aa9>
    6fff:	31 d2                	xor    edx,edx
    7001:	41 bc 76 00 00 00    	mov    r12d,0x76
    7007:	49 8d 4d 01          	lea    rcx,[r13+0x1]
    700b:	e9 06 ea ff ff       	jmp    5a16 <error_at_line@@Base+0x4aad>
    7010:	45 31 d2             	xor    r10d,r10d
    7013:	e9 a7 f8 ff ff       	jmp    68bf <error_at_line@@Base+0x5956>
    7018:	31 d2                	xor    edx,edx
    701a:	41 bc 72 00 00 00    	mov    r12d,0x72
    7020:	49 8d 4d 01          	lea    rcx,[r13+0x1]
    7024:	e9 ed e9 ff ff       	jmp    5a16 <error_at_line@@Base+0x4aad>
    7029:	31 d2                	xor    edx,edx
    702b:	41 bc 6e 00 00 00    	mov    r12d,0x6e
    7031:	49 8d 4d 01          	lea    rcx,[r13+0x1]
    7035:	e9 dc e9 ff ff       	jmp    5a16 <error_at_line@@Base+0x4aad>
    703a:	0f b6 55 9f          	movzx  edx,BYTE PTR [rbp-0x61]
    703e:	49 83 c5 01          	add    r13,0x1
    7042:	20 55 9d             	and    BYTE PTR [rbp-0x63],dl
    7045:	44 89 d8             	mov    eax,r11d
    7048:	e9 cc ea ff ff       	jmp    5b19 <error_at_line@@Base+0x4bb0>
    704d:	31 c0                	xor    eax,eax
    704f:	e9 6b f8 ff ff       	jmp    68bf <error_at_line@@Base+0x5956>
    7054:	80 7d a0 00          	cmp    BYTE PTR [rbp-0x60],0x0
    7058:	c6 45 9d 00          	mov    BYTE PTR [rbp-0x63],0x0
    705c:	49 89 cd             	mov    r13,rcx
    705f:	41 bc 30 00 00 00    	mov    r12d,0x30
    7065:	0f 85 ed e9 ff ff    	jne    5a58 <error_at_line@@Base+0x4aef>
    706b:	e9 f6 e9 ff ff       	jmp    5a66 <error_at_line@@Base+0x4afd>
    7070:	4c 89 c0             	mov    rax,r8
    7073:	e9 69 fa ff ff       	jmp    6ae1 <error_at_line@@Base+0x5b78>
    7078:	41 bc 3f 00 00 00    	mov    r12d,0x3f
    707e:	e9 4d e9 ff ff       	jmp    59d0 <error_at_line@@Base+0x4a67>
    7083:	0f b6 45 82          	movzx  eax,BYTE PTR [rbp-0x7e]
    7087:	49 89 d8             	mov    r8,rbx
    708a:	4d 89 f2             	mov    r10,r14
    708d:	4d 89 fb             	mov    r11,r15
    7090:	e9 09 fa ff ff       	jmp    6a9e <error_at_line@@Base+0x5b35>
    7095:	4d 89 fb             	mov    r11,r15
    7098:	c7 45 84 05 00 00 00 	mov    DWORD PTR [rbp-0x7c],0x5
    709f:	4d 89 c7             	mov    r15,r8
    70a2:	4c 8b b5 58 ff ff ff 	mov    r14,QWORD PTR [rbp-0xa8]
    70a9:	e9 02 e7 ff ff       	jmp    57b0 <error_at_line@@Base+0x4847>
    70ae:	49 89 d8             	mov    r8,rbx
    70b1:	4d 89 f2             	mov    r10,r14
    70b4:	4d 89 fb             	mov    r11,r15
    70b7:	b8 01 00 00 00       	mov    eax,0x1
    70bc:	e9 dd f9 ff ff       	jmp    6a9e <error_at_line@@Base+0x5b35>
    70c1:	31 d2                	xor    edx,edx
    70c3:	41 bc 61 00 00 00    	mov    r12d,0x61
    70c9:	49 8d 4d 01          	lea    rcx,[r13+0x1]
    70cd:	e9 44 e9 ff ff       	jmp    5a16 <error_at_line@@Base+0x4aad>
    70d2:	31 d2                	xor    edx,edx
    70d4:	41 bc 74 00 00 00    	mov    r12d,0x74
    70da:	49 8d 4d 01          	lea    rcx,[r13+0x1]
    70de:	e9 33 e9 ff ff       	jmp    5a16 <error_at_line@@Base+0x4aad>
    70e3:	49 83 c5 01          	add    r13,0x1
    70e7:	e9 45 f1 ff ff       	jmp    6231 <error_at_line@@Base+0x52c8>
    70ec:	41 bc 40 00 00 00    	mov    r12d,0x40
    70f2:	e9 6d e8 ff ff       	jmp    5964 <error_at_line@@Base+0x49fb>
    70f7:	0f b6 45 9b          	movzx  eax,BYTE PTR [rbp-0x65]
    70fb:	31 d2                	xor    edx,edx
    70fd:	e9 c5 e8 ff ff       	jmp    59c7 <error_at_line@@Base+0x4a5e>
    7102:	8b 7d bc             	mov    edi,DWORD PTR [rbp-0x44]
    7105:	44 88 9d 40 ff ff ff 	mov    BYTE PTR [rbp-0xc0],r11b
    710c:	4c 89 85 68 ff ff ff 	mov    QWORD PTR [rbp-0x98],r8
    7113:	44 88 95 70 ff ff ff 	mov    BYTE PTR [rbp-0x90],r10b
    711a:	48 89 85 78 ff ff ff 	mov    QWORD PTR [rbp-0x88],rax
    7121:	e8 8a 9a ff ff       	call   bb0 <iswprint@plt>
    7126:	44 0f b6 95 70 ff ff 	movzx  r10d,BYTE PTR [rbp-0x90]
    712d:	ff 
    712e:	4c 8b 85 68 ff ff ff 	mov    r8,QWORD PTR [rbp-0x98]
    7135:	85 c0                	test   eax,eax
    7137:	44 0f b6 9d 40 ff ff 	movzx  r11d,BYTE PTR [rbp-0xc0]
    713e:	ff 
    713f:	0f 85 7b f0 ff ff    	jne    61c0 <error_at_line@@Base+0x5257>
    7145:	0f b6 45 9b          	movzx  eax,BYTE PTR [rbp-0x65]
    7149:	48 8b 8d 78 ff ff ff 	mov    rcx,QWORD PTR [rbp-0x88]
    7150:	31 d2                	xor    edx,edx
    7152:	e9 70 e8 ff ff       	jmp    59c7 <error_at_line@@Base+0x4a5e>
    7157:	4d 89 fb             	mov    r11,r15
    715a:	4d 89 c7             	mov    r15,r8
    715d:	e9 7d ea ff ff       	jmp    5bdf <error_at_line@@Base+0x4c76>
    7162:	e8 89 97 ff ff       	call   8f0 <__stack_chk_fail@plt>
    7167:	66 0f 1f 84 00 00 00 	nop    WORD PTR [rax+rax*1+0x0]
    716e:	00 00 
    7170:	55                   	push   rbp
    7171:	31 c9                	xor    ecx,ecx
    7173:	48 89 e5             	mov    rbp,rsp
    7176:	41 57                	push   r15
    7178:	41 56                	push   r14
    717a:	41 55                	push   r13
    717c:	41 54                	push   r12
    717e:	49 89 fc             	mov    r12,rdi
    7181:	53                   	push   rbx
    7182:	48 83 ec 08          	sub    rsp,0x8
    7186:	4c 8b 77 18          	mov    r14,QWORD PTR [rdi+0x18]
    718a:	4c 2b 77 10          	sub    r14,QWORD PTR [rdi+0x10]
    718e:	4c 01 f6             	add    rsi,r14
    7191:	48 8b 47 30          	mov    rax,QWORD PTR [rdi+0x30]
    7195:	48 89 f2             	mov    rdx,rsi
    7198:	0f 92 c1             	setb   cl
    719b:	48 f7 da             	neg    rdx
    719e:	48 21 c2             	and    rdx,rax
    71a1:	48 01 f2             	add    rdx,rsi
    71a4:	40 0f 92 c6          	setb   sil
    71a8:	40 0f b6 f6          	movzx  esi,sil
    71ac:	48 09 f1             	or     rcx,rsi
    71af:	48 8d 70 10          	lea    rsi,[rax+0x10]
    71b3:	4c 89 f0             	mov    rax,r14
    71b6:	48 01 d6             	add    rsi,rdx
    71b9:	0f 92 c2             	setb   dl
    71bc:	48 c1 e8 03          	shr    rax,0x3
    71c0:	0f b6 d2             	movzx  edx,dl
    71c3:	48 83 c0 64          	add    rax,0x64
    71c7:	48 09 ca             	or     rdx,rcx
    71ca:	48 01 f0             	add    rax,rsi
    71cd:	72 03                	jb     71d2 <error_at_line@@Base+0x6269>
    71cf:	48 89 c6             	mov    rsi,rax
    71d2:	48 85 d2             	test   rdx,rdx
    71d5:	0f 85 0f 01 00 00    	jne    72ea <error_at_line@@Base+0x6381>
    71db:	49 8b 04 24          	mov    rax,QWORD PTR [r12]
    71df:	4d 8b 6c 24 08       	mov    r13,QWORD PTR [r12+0x8]
    71e4:	48 39 c6             	cmp    rsi,rax
    71e7:	48 0f 43 c6          	cmovae rax,rsi
    71eb:	48 89 c3             	mov    rbx,rax
    71ee:	49 8b 44 24 38       	mov    rax,QWORD PTR [r12+0x38]
    71f3:	41 f6 44 24 50 01    	test   BYTE PTR [r12+0x50],0x1
    71f9:	0f 85 a1 00 00 00    	jne    72a0 <error_at_line@@Base+0x6337>
    71ff:	48 89 df             	mov    rdi,rbx
    7202:	ff d0                	call   rax
    7204:	49 89 c7             	mov    r15,rax
    7207:	4d 85 ff             	test   r15,r15
    720a:	0f 84 da 00 00 00    	je     72ea <error_at_line@@Base+0x6381>
    7210:	4d 89 7c 24 08       	mov    QWORD PTR [r12+0x8],r15
    7215:	4d 89 6f 08          	mov    QWORD PTR [r15+0x8],r13
    7219:	49 8b 54 24 30       	mov    rdx,QWORD PTR [r12+0x30]
    721e:	48 29 d3             	sub    rbx,rdx
    7221:	49 8d 04 1f          	lea    rax,[r15+rbx*1]
    7225:	48 f7 d8             	neg    rax
    7228:	48 21 d0             	and    rax,rdx
    722b:	4c 89 f2             	mov    rdx,r14
    722e:	48 01 d8             	add    rax,rbx
    7231:	4c 01 f8             	add    rax,r15
    7234:	49 89 44 24 20       	mov    QWORD PTR [r12+0x20],rax
    7239:	49 89 07             	mov    QWORD PTR [r15],rax
    723c:	49 8d 47 10          	lea    rax,[r15+0x10]
    7240:	49 8b 74 24 10       	mov    rsi,QWORD PTR [r12+0x10]
    7245:	48 f7 d8             	neg    rax
    7248:	49 23 44 24 30       	and    rax,QWORD PTR [r12+0x30]
    724d:	49 8d 5c 07 10       	lea    rbx,[r15+rax*1+0x10]
    7252:	48 89 df             	mov    rdi,rbx
    7255:	e8 06 98 ff ff       	call   a60 <memcpy@plt>
    725a:	41 f6 44 24 50 02    	test   BYTE PTR [r12+0x50],0x2
    7260:	75 18                	jne    727a <error_at_line@@Base+0x6311>
    7262:	49 8d 55 10          	lea    rdx,[r13+0x10]
    7266:	48 f7 da             	neg    rdx
    7269:	49 23 54 24 30       	and    rdx,QWORD PTR [r12+0x30]
    726e:	49 8d 44 15 10       	lea    rax,[r13+rdx*1+0x10]
    7273:	49 39 44 24 10       	cmp    QWORD PTR [r12+0x10],rax
    7278:	74 3e                	je     72b8 <error_at_line@@Base+0x634f>
    727a:	49 89 5c 24 10       	mov    QWORD PTR [r12+0x10],rbx
    727f:	4c 01 f3             	add    rbx,r14
    7282:	41 80 64 24 50 fd    	and    BYTE PTR [r12+0x50],0xfd
    7288:	49 89 5c 24 18       	mov    QWORD PTR [r12+0x18],rbx
    728d:	48 83 c4 08          	add    rsp,0x8
    7291:	5b                   	pop    rbx
    7292:	41 5c                	pop    r12
    7294:	41 5d                	pop    r13
    7296:	41 5e                	pop    r14
    7298:	41 5f                	pop    r15
    729a:	5d                   	pop    rbp
    729b:	c3                   	ret
    729c:	0f 1f 40 00          	nop    DWORD PTR [rax+0x0]
    72a0:	49 8b 7c 24 48       	mov    rdi,QWORD PTR [r12+0x48]
    72a5:	48 89 de             	mov    rsi,rbx
    72a8:	ff d0                	call   rax
    72aa:	49 89 c7             	mov    r15,rax
    72ad:	e9 55 ff ff ff       	jmp    7207 <error_at_line@@Base+0x629e>
    72b2:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]
    72b8:	49 8b 45 08          	mov    rax,QWORD PTR [r13+0x8]
    72bc:	49 89 47 08          	mov    QWORD PTR [r15+0x8],rax
    72c0:	41 f6 44 24 50 01    	test   BYTE PTR [r12+0x50],0x1
    72c6:	74 18                	je     72e0 <error_at_line@@Base+0x6377>
    72c8:	49 8b 7c 24 48       	mov    rdi,QWORD PTR [r12+0x48]
    72cd:	4c 89 ee             	mov    rsi,r13
    72d0:	41 ff 54 24 40       	call   QWORD PTR [r12+0x40]
    72d5:	eb a3                	jmp    727a <error_at_line@@Base+0x6311>
    72d7:	66 0f 1f 84 00 00 00 	nop    WORD PTR [rax+rax*1+0x0]
    72de:	00 00 
    72e0:	4c 89 ef             	mov    rdi,r13
    72e3:	41 ff 54 24 40       	call   QWORD PTR [r12+0x40]
    72e8:	eb 90                	jmp    727a <error_at_line@@Base+0x6311>
    72ea:	48 8d 05 8f 7d 00 00 	lea    rax,[rip+0x7d8f]        # f080 <obstack_alloc_failed_handler@@Base>
    72f1:	ff 10                	call   QWORD PTR [rax]
    72f3:	66 90                	xchg   ax,ax
    72f5:	66 66 2e 0f 1f 84 00 	data16 cs nop WORD PTR [rax+rax*1+0x0]
    72fc:	00 00 00 00 
    7300:	55                   	push   rbp
    7301:	48 89 e5             	mov    rbp,rsp
    7304:	41 54                	push   r12
    7306:	53                   	push   rbx
    7307:	48 89 fb             	mov    rbx,rdi
    730a:	48 83 ec 10          	sub    rsp,0x10
    730e:	48 8b 47 30          	mov    rax,QWORD PTR [rdi+0x30]
    7312:	48 8b 57 28          	mov    rdx,QWORD PTR [rdi+0x28]
    7316:	49 89 c4             	mov    r12,rax
    7319:	49 29 d4             	sub    r12,rdx
    731c:	49 83 ec 01          	sub    r12,0x1
    7320:	48 39 d0             	cmp    rax,rdx
    7323:	0f 84 a7 00 00 00    	je     73d0 <error_at_line@@Base+0x6467>
    7329:	48 89 c1             	mov    rcx,rax
    732c:	48 f7 d9             	neg    rcx
    732f:	48 23 4b 48          	and    rcx,QWORD PTR [rbx+0x48]
    7333:	48 01 c8             	add    rax,rcx
    7336:	48 8b 8b 88 00 00 00 	mov    rcx,QWORD PTR [rbx+0x88]
    733d:	48 89 43 30          	mov    QWORD PTR [rbx+0x30],rax
    7341:	48 89 43 28          	mov    QWORD PTR [rbx+0x28],rax
    7345:	48 8b 83 90 00 00 00 	mov    rax,QWORD PTR [rbx+0x90]
    734c:	48 29 c8             	sub    rax,rcx
    734f:	48 83 f8 07          	cmp    rax,0x7
    7353:	76 3b                	jbe    7390 <error_at_line@@Base+0x6427>
    7355:	48 89 11             	mov    QWORD PTR [rcx],rdx
    7358:	48 8b 93 e0 00 00 00 	mov    rdx,QWORD PTR [rbx+0xe0]
    735f:	48 8b 83 e8 00 00 00 	mov    rax,QWORD PTR [rbx+0xe8]
    7366:	48 83 83 88 00 00 00 	add    QWORD PTR [rbx+0x88],0x8
    736d:	08 
    736e:	48 29 d0             	sub    rax,rdx
    7371:	48 83 f8 07          	cmp    rax,0x7
    7375:	76 39                	jbe    73b0 <error_at_line@@Base+0x6447>
    7377:	4c 89 22             	mov    QWORD PTR [rdx],r12
    737a:	48 83 83 e0 00 00 00 	add    QWORD PTR [rbx+0xe0],0x8
    7381:	08 
    7382:	48 83 03 01          	add    QWORD PTR [rbx],0x1
    7386:	48 83 c4 10          	add    rsp,0x10
    738a:	5b                   	pop    rbx
    738b:	41 5c                	pop    r12
    738d:	5d                   	pop    rbp
    738e:	c3                   	ret
    738f:	90                   	nop
    7390:	48 8d 7b 70          	lea    rdi,[rbx+0x70]
    7394:	be 08 00 00 00       	mov    esi,0x8
    7399:	48 89 55 e8          	mov    QWORD PTR [rbp-0x18],rdx
    739d:	e8 ce fd ff ff       	call   7170 <error_at_line@@Base+0x6207>
    73a2:	48 8b 8b 88 00 00 00 	mov    rcx,QWORD PTR [rbx+0x88]
    73a9:	48 8b 55 e8          	mov    rdx,QWORD PTR [rbp-0x18]
    73ad:	eb a6                	jmp    7355 <error_at_line@@Base+0x63ec>
    73af:	90                   	nop
    73b0:	48 8d bb c8 00 00 00 	lea    rdi,[rbx+0xc8]
    73b7:	be 08 00 00 00       	mov    esi,0x8
    73bc:	e8 af fd ff ff       	call   7170 <error_at_line@@Base+0x6207>
    73c1:	48 8b 93 e0 00 00 00 	mov    rdx,QWORD PTR [rbx+0xe0]
    73c8:	eb ad                	jmp    7377 <error_at_line@@Base+0x640e>
    73ca:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]
    73d0:	80 4f 68 02          	or     BYTE PTR [rdi+0x68],0x2
    73d4:	e9 50 ff ff ff       	jmp    7329 <error_at_line@@Base+0x63c0>
    73d9:	0f 1f 80 00 00 00 00 	nop    DWORD PTR [rax+0x0]
    73e0:	55                   	push   rbp
    73e1:	48 89 e5             	mov    rbp,rsp
    73e4:	41 56                	push   r14
    73e6:	53                   	push   rbx
    73e7:	48 83 ec 10          	sub    rsp,0x10
    73eb:	48 89 7d e8          	mov    QWORD PTR [rbp-0x18],rdi
    73ef:	e8 3c 94 ff ff       	call   830 <__fpending@plt>
    73f4:	48 8b 7d e8          	mov    rdi,QWORD PTR [rbp-0x18]
    73f8:	49 89 c6             	mov    r14,rax
    73fb:	8b 1f                	mov    ebx,DWORD PTR [rdi]
    73fd:	e8 9e 94 ff ff       	call   8a0 <fclose@plt>
    7402:	83 e3 20             	and    ebx,0x20
    7405:	75 29                	jne    7430 <error_at_line@@Base+0x64c7>
    7407:	85 c0                	test   eax,eax
    7409:	74 15                	je     7420 <error_at_line@@Base+0x64b7>
    740b:	4d 85 f6             	test   r14,r14
    740e:	75 2f                	jne    743f <error_at_line@@Base+0x64d6>
    7410:	e8 eb 93 ff ff       	call   800 <__errno_location@plt>
    7415:	83 38 09             	cmp    DWORD PTR [rax],0x9
    7418:	0f 95 c0             	setne  al
    741b:	0f b6 c0             	movzx  eax,al
    741e:	f7 d8                	neg    eax
    7420:	48 83 c4 10          	add    rsp,0x10
    7424:	5b                   	pop    rbx
    7425:	41 5e                	pop    r14
    7427:	5d                   	pop    rbp
    7428:	c3                   	ret
    7429:	0f 1f 80 00 00 00 00 	nop    DWORD PTR [rax+0x0]
    7430:	85 c0                	test   eax,eax
    7432:	75 0b                	jne    743f <error_at_line@@Base+0x64d6>
    7434:	e8 c7 93 ff ff       	call   800 <__errno_location@plt>
    7439:	c7 00 00 00 00 00    	mov    DWORD PTR [rax],0x0
    743f:	b8 ff ff ff ff       	mov    eax,0xffffffff
    7444:	eb da                	jmp    7420 <error_at_line@@Base+0x64b7>
    7446:	66 2e 0f 1f 84 00 00 	cs nop WORD PTR [rax+rax*1+0x0]
    744d:	00 00 00 
    7450:	55                   	push   rbp
    7451:	48 89 e5             	mov    rbp,rsp
    7454:	41 57                	push   r15
    7456:	41 56                	push   r14
    7458:	41 55                	push   r13
    745a:	41 54                	push   r12
    745c:	53                   	push   rbx
    745d:	48 83 e4 c0          	and    rsp,0xffffffffffffffc0
    7461:	4c 8d 9c 24 00 00 fc 	lea    r11,[rsp-0x40000]
    7468:	ff 
    7469:	48 81 ec 00 10 00 00 	sub    rsp,0x1000
    7470:	80 0c 24 00          	or     BYTE PTR [rsp],0x0
    7474:	4c 39 dc             	cmp    rsp,r11
    7477:	75 f0                	jne    7469 <error_at_line@@Base+0x6500>
    7479:	48 83 ec 40          	sub    rsp,0x40
    747d:	45 31 e4             	xor    r12d,r12d
    7480:	31 db                	xor    ebx,ebx
    7482:	64 4c 8b 2c 25 28 00 	mov    r13,QWORD PTR fs:0x28
    7489:	00 00 
    748b:	4c 89 ac 24 38 00 04 	mov    QWORD PTR [rsp+0x40038],r13
    7492:	00 
    7493:	41 89 f5             	mov    r13d,esi
    7496:	49 89 ff             	mov    r15,rdi
    7499:	0f 1f 80 00 00 00 00 	nop    DWORD PTR [rax+0x0]
    74a0:	ba 00 00 04 00       	mov    edx,0x40000
    74a5:	48 89 e6             	mov    rsi,rsp
    74a8:	44 89 ef             	mov    edi,r13d
    74ab:	c5 f8 77             	vzeroupper
    74ae:	e8 1d 95 ff ff       	call   9d0 <read@plt>
    74b3:	c5 c9 ef f6          	vpxor  xmm6,xmm6,xmm6
    74b7:	62 f1 7d 48 6f 2d 3f 	vmovdqa32 zmm5,ZMMWORD PTR [rip+0x533f]        # c800 <error_at_line@@Base+0xb897>
    74be:	53 00 00 
    74c1:	48 85 c0             	test   rax,rax
    74c4:	48 89 c1             	mov    rcx,rax
    74c7:	62 f3 4d 48 25 f6 ff 	vpternlogd zmm6,zmm6,zmm6,0xff
    74ce:	0f 8e cc 01 00 00    	jle    76a0 <error_at_line@@Base+0x6737>
    74d4:	49 01 c4             	add    r12,rax
    74d7:	48 83 f8 3f          	cmp    rax,0x3f
    74db:	0f 8e 7f 01 00 00    	jle    7660 <error_at_line@@Base+0x66f7>
    74e1:	48 89 c6             	mov    rsi,rax
    74e4:	48 89 e0             	mov    rax,rsp
    74e7:	48 c1 ee 06          	shr    rsi,0x6
    74eb:	48 8d 7e ff          	lea    rdi,[rsi-0x1]
    74ef:	48 c1 e6 06          	shl    rsi,0x6
    74f3:	48 01 e6             	add    rsi,rsp
    74f6:	66 2e 0f 1f 84 00 00 	cs nop WORD PTR [rax+rax*1+0x0]
    74fd:	00 00 00 
    7500:	62 f3 55 48 3f 00 00 	vpcmpeqb k0,zmm5,ZMMWORD PTR [rax]
    7507:	48 83 c0 40          	add    rax,0x40
    750b:	c4 e1 fb 93 d0       	kmovq  rdx,k0
    7510:	f3 48 0f b8 d2       	popcnt rdx,rdx
    7515:	48 01 d3             	add    rbx,rdx
    7518:	48 39 f0             	cmp    rax,rsi
    751b:	75 e3                	jne    7500 <error_at_line@@Base+0x6597>
    751d:	48 89 f8             	mov    rax,rdi
    7520:	48 f7 d8             	neg    rax
    7523:	48 c1 e0 06          	shl    rax,0x6
    7527:	48 8d 74 08 c0       	lea    rsi,[rax+rcx*1-0x40]
    752c:	48 8d 4c 24 40       	lea    rcx,[rsp+0x40]
    7531:	48 29 c1             	sub    rcx,rax
    7534:	48 8d 14 31          	lea    rdx,[rcx+rsi*1]
    7538:	48 89 c8             	mov    rax,rcx
    753b:	48 39 d1             	cmp    rcx,rdx
    753e:	0f 83 5c ff ff ff    	jae    74a0 <error_at_line@@Base+0x6537>
    7544:	48 83 ee 01          	sub    rsi,0x1
    7548:	48 83 fe 3e          	cmp    rsi,0x3e
    754c:	0f 86 2e 01 00 00    	jbe    7680 <error_at_line@@Base+0x6717>
    7552:	c5 d9 ef e4          	vpxor  xmm4,xmm4,xmm4
    7556:	66 2e 0f 1f 84 00 00 	cs nop WORD PTR [rax+rax*1+0x0]
    755d:	00 00 00 
    7560:	62 f3 55 48 3f 08 00 	vpcmpeqb k1,zmm5,ZMMWORD PTR [rax]
    7567:	48 83 c0 40          	add    rax,0x40
    756b:	62 f2 7d c9 1c c6    	vpabsb zmm0{k1}{z},zmm6
    7571:	62 f2 7d 48 30 c8    	vpmovzxbw zmm1,ymm0
    7577:	62 f3 fd 48 3b c0 01 	vextracti64x4 ymm0,zmm0,0x1
    757e:	62 f2 7d 48 33 d9    	vpmovzxwd zmm3,ymm1
    7584:	62 f3 fd 48 3b c9 01 	vextracti64x4 ymm1,zmm1,0x1
    758b:	62 f2 7d 48 30 c0    	vpmovzxbw zmm0,ymm0
    7591:	62 f2 7d 48 35 fb    	vpmovzxdq zmm7,ymm3
    7597:	62 f3 fd 48 3b db 01 	vextracti64x4 ymm3,zmm3,0x1
    759e:	62 f2 7d 48 33 c9    	vpmovzxwd zmm1,ymm1
    75a4:	62 f1 c5 48 d4 fc    	vpaddq zmm7,zmm7,zmm4
    75aa:	62 f2 7d 48 35 db    	vpmovzxdq zmm3,ymm3
    75b0:	62 f2 7d 48 35 e1    	vpmovzxdq zmm4,ymm1
    75b6:	62 f1 e5 48 d4 df    	vpaddq zmm3,zmm3,zmm7
    75bc:	62 f3 fd 48 3b c9 01 	vextracti64x4 ymm1,zmm1,0x1
    75c3:	62 f2 7d 48 33 d0    	vpmovzxwd zmm2,ymm0
    75c9:	62 f1 dd 48 d4 e3    	vpaddq zmm4,zmm4,zmm3
    75cf:	62 f2 7d 48 35 c9    	vpmovzxdq zmm1,ymm1
    75d5:	62 f2 7d 48 35 da    	vpmovzxdq zmm3,ymm2
    75db:	62 f1 f5 48 d4 cc    	vpaddq zmm1,zmm1,zmm4
    75e1:	62 f3 fd 48 3b c0 01 	vextracti64x4 ymm0,zmm0,0x1
    75e8:	62 f3 fd 48 3b d2 01 	vextracti64x4 ymm2,zmm2,0x1
    75ef:	62 f2 7d 48 33 c0    	vpmovzxwd zmm0,ymm0
    75f5:	62 f1 e5 48 d4 d9    	vpaddq zmm3,zmm3,zmm1
    75fb:	62 f2 7d 48 35 d2    	vpmovzxdq zmm2,ymm2
    7601:	62 f2 7d 48 35 e0    	vpmovzxdq zmm4,ymm0
    7607:	62 f1 ed 48 d4 d3    	vpaddq zmm2,zmm2,zmm3
    760d:	62 f3 fd 48 3b c0 01 	vextracti64x4 ymm0,zmm0,0x1
    7614:	62 f1 dd 48 d4 e2    	vpaddq zmm4,zmm4,zmm2
    761a:	62 f2 7d 48 35 c0    	vpmovzxdq zmm0,ymm0
    7620:	62 f1 fd 48 d4 e4    	vpaddq zmm4,zmm0,zmm4
    7626:	48 39 c1             	cmp    rcx,rax
    7629:	0f 85 31 ff ff ff    	jne    7560 <error_at_line@@Base+0x65f7>
    762f:	62 f3 fd 48 3b e1 01 	vextracti64x4 ymm1,zmm4,0x1
    7636:	c5 f5 d4 cc          	vpaddq ymm1,ymm1,ymm4
    763a:	c4 e3 7d 39 c8 01    	vextracti128 xmm0,ymm1,0x1
    7640:	c5 f9 d4 c1          	vpaddq xmm0,xmm0,xmm1
    7644:	c5 f1 73 d8 08       	vpsrldq xmm1,xmm0,0x8
    7649:	c5 f9 d4 c1          	vpaddq xmm0,xmm0,xmm1
    764d:	c4 e1 f9 7e c0       	vmovq  rax,xmm0
    7652:	48 01 c3             	add    rbx,rax
    7655:	e9 46 fe ff ff       	jmp    74a0 <error_at_line@@Base+0x6537>
    765a:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]
    7660:	48 8d 14 04          	lea    rdx,[rsp+rax*1]
    7664:	48 89 e0             	mov    rax,rsp
    7667:	48 39 d4             	cmp    rsp,rdx
    766a:	0f 83 30 fe ff ff    	jae    74a0 <error_at_line@@Base+0x6537>
    7670:	0f 1f 44 00 00       	nop    DWORD PTR [rax+rax*1+0x0]
    7675:	66 66 2e 0f 1f 84 00 	data16 cs nop WORD PTR [rax+rax*1+0x0]
    767c:	00 00 00 00 
    7680:	31 c9                	xor    ecx,ecx
    7682:	80 38 0a             	cmp    BYTE PTR [rax],0xa
    7685:	0f 94 c1             	sete   cl
    7688:	48 83 c0 01          	add    rax,0x1
    768c:	48 01 cb             	add    rbx,rcx
    768f:	48 39 d0             	cmp    rax,rdx
    7692:	72 ec                	jb     7680 <error_at_line@@Base+0x6717>
    7694:	e9 07 fe ff ff       	jmp    74a0 <error_at_line@@Base+0x6537>
    7699:	0f 1f 80 00 00 00 00 	nop    DWORD PTR [rax+0x0]
    76a0:	b8 00 00 00 00       	mov    eax,0x0
    76a5:	74 3a                	je     76e1 <error_at_line@@Base+0x6778>
    76a7:	c5 f8 77             	vzeroupper
    76aa:	e8 51 91 ff ff       	call   800 <__errno_location@plt>
    76af:	8b 00                	mov    eax,DWORD PTR [rax]
    76b1:	41 89 07             	mov    DWORD PTR [r15],eax
    76b4:	49 89 5f 08          	mov    QWORD PTR [r15+0x8],rbx
    76b8:	4d 89 67 10          	mov    QWORD PTR [r15+0x10],r12
    76bc:	48 8b 84 24 38 00 04 	mov    rax,QWORD PTR [rsp+0x40038]
    76c3:	00 
    76c4:	64 48 2b 04 25 28 00 	sub    rax,QWORD PTR fs:0x28
    76cb:	00 00 
    76cd:	75 17                	jne    76e6 <error_at_line@@Base+0x677d>
    76cf:	48 8d 65 d8          	lea    rsp,[rbp-0x28]
    76d3:	4c 89 f8             	mov    rax,r15
    76d6:	5b                   	pop    rbx
    76d7:	41 5c                	pop    r12
    76d9:	41 5d                	pop    r13
    76db:	41 5e                	pop    r14
    76dd:	41 5f                	pop    r15
    76df:	5d                   	pop    rbp
    76e0:	c3                   	ret
    76e1:	c5 f8 77             	vzeroupper
    76e4:	eb cb                	jmp    76b1 <error_at_line@@Base+0x6748>
    76e6:	e8 05 92 ff ff       	call   8f0 <__stack_chk_fail@plt>
    76eb:	0f 1f 44 00 00       	nop    DWORD PTR [rax+rax*1+0x0]
    76f0:	55                   	push   rbp
    76f1:	48 89 e5             	mov    rbp,rsp
    76f4:	41 57                	push   r15
    76f6:	41 56                	push   r14
    76f8:	41 55                	push   r13
    76fa:	41 54                	push   r12
    76fc:	53                   	push   rbx
    76fd:	48 83 e4 e0          	and    rsp,0xffffffffffffffe0
    7701:	4c 8d 9c 24 00 00 fc 	lea    r11,[rsp-0x40000]
    7708:	ff 
    7709:	48 81 ec 00 10 00 00 	sub    rsp,0x1000
    7710:	80 0c 24 00          	or     BYTE PTR [rsp],0x0
    7714:	4c 39 dc             	cmp    rsp,r11
    7717:	75 f0                	jne    7709 <error_at_line@@Base+0x67a0>
    7719:	48 83 ec 20          	sub    rsp,0x20
    771d:	45 31 e4             	xor    r12d,r12d
    7720:	31 db                	xor    ebx,ebx
    7722:	64 4c 8b 2c 25 28 00 	mov    r13,QWORD PTR fs:0x28
    7729:	00 00 
    772b:	4c 89 ac 24 18 00 04 	mov    QWORD PTR [rsp+0x40018],r13
    7732:	00 
    7733:	41 89 f5             	mov    r13d,esi
    7736:	49 89 ff             	mov    r15,rdi
    7739:	0f 1f 80 00 00 00 00 	nop    DWORD PTR [rax+0x0]
    7740:	ba 00 00 04 00       	mov    edx,0x40000
    7745:	48 89 e6             	mov    rsi,rsp
    7748:	44 89 ef             	mov    edi,r13d
    774b:	c5 f8 77             	vzeroupper
    774e:	e8 7d 92 ff ff       	call   9d0 <read@plt>
    7753:	c5 fd 6f 1d a5 50 00 	vmovdqa ymm3,YMMWORD PTR [rip+0x50a5]        # c800 <error_at_line@@Base+0xb897>
    775a:	00 
    775b:	48 85 c0             	test   rax,rax
    775e:	48 89 c1             	mov    rcx,rax
    7761:	0f 8e 99 01 00 00    	jle    7900 <error_at_line@@Base+0x6997>
    7767:	49 01 c4             	add    r12,rax
    776a:	48 83 f8 1f          	cmp    rax,0x1f
    776e:	0f 8e 54 01 00 00    	jle    78c8 <error_at_line@@Base+0x695f>
    7774:	48 89 c6             	mov    rsi,rax
    7777:	48 89 e0             	mov    rax,rsp
    777a:	48 c1 ee 05          	shr    rsi,0x5
    777e:	48 8d 7e ff          	lea    rdi,[rsi-0x1]
    7782:	48 c1 e6 05          	shl    rsi,0x5
    7786:	48 01 e6             	add    rsi,rsp
    7789:	90                   	nop
    778a:	66 66 2e 0f 1f 84 00 	data16 cs nop WORD PTR [rax+rax*1+0x0]
    7791:	00 00 00 00 
    7795:	66 66 2e 0f 1f 84 00 	data16 cs nop WORD PTR [rax+rax*1+0x0]
    779c:	00 00 00 00 
    77a0:	c5 e5 74 00          	vpcmpeqb ymm0,ymm3,YMMWORD PTR [rax]
    77a4:	48 83 c0 20          	add    rax,0x20
    77a8:	c5 fd d7 d0          	vpmovmskb edx,ymm0
    77ac:	f3 0f b8 d2          	popcnt edx,edx
    77b0:	48 01 d3             	add    rbx,rdx
    77b3:	48 39 f0             	cmp    rax,rsi
    77b6:	75 e8                	jne    77a0 <error_at_line@@Base+0x6837>
    77b8:	48 89 f8             	mov    rax,rdi
    77bb:	48 f7 d8             	neg    rax
    77be:	48 c1 e0 05          	shl    rax,0x5
    77c2:	48 8d 74 08 e0       	lea    rsi,[rax+rcx*1-0x20]
    77c7:	48 8d 4c 24 20       	lea    rcx,[rsp+0x20]
    77cc:	48 29 c1             	sub    rcx,rax
    77cf:	48 8d 14 31          	lea    rdx,[rcx+rsi*1]
    77d3:	48 89 c8             	mov    rax,rcx
    77d6:	48 39 d1             	cmp    rcx,rdx
    77d9:	0f 83 61 ff ff ff    	jae    7740 <error_at_line@@Base+0x67d7>
    77df:	48 83 ee 01          	sub    rsi,0x1
    77e3:	48 83 fe 1e          	cmp    rsi,0x1e
    77e7:	0f 86 f3 00 00 00    	jbe    78e0 <error_at_line@@Base+0x6977>
    77ed:	c4 e2 7d 1c 25 6a 50 	vpabsb ymm4,YMMWORD PTR [rip+0x506a]        # c860 <error_at_line@@Base+0xb8f7>
    77f4:	00 00 
    77f6:	c5 d1 ef ed          	vpxor  xmm5,xmm5,xmm5
    77fa:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]
    7800:	c5 e5 74 00          	vpcmpeqb ymm0,ymm3,YMMWORD PTR [rax]
    7804:	48 83 c0 20          	add    rax,0x20
    7808:	c5 fd db c4          	vpand  ymm0,ymm0,ymm4
    780c:	c4 e2 7d 30 c8       	vpmovzxbw ymm1,xmm0
    7811:	c4 e3 7d 39 c0 01    	vextracti128 xmm0,ymm0,0x1
    7817:	c4 e2 7d 33 d1       	vpmovzxwd ymm2,xmm1
    781c:	c4 e3 7d 39 c9 01    	vextracti128 xmm1,ymm1,0x1
    7822:	c4 e2 7d 30 c0       	vpmovzxbw ymm0,xmm0
    7827:	c4 e2 7d 35 fa       	vpmovzxdq ymm7,xmm2
    782c:	c4 e3 7d 39 d2 01    	vextracti128 xmm2,ymm2,0x1
    7832:	c4 e2 7d 33 c9       	vpmovzxwd ymm1,xmm1
    7837:	c5 c5 d4 ed          	vpaddq ymm5,ymm7,ymm5
    783b:	c4 e2 7d 35 d2       	vpmovzxdq ymm2,xmm2
    7840:	c4 e2 7d 33 f0       	vpmovzxwd ymm6,xmm0
    7845:	c5 ed d4 d5          	vpaddq ymm2,ymm2,ymm5
    7849:	c4 e2 7d 35 e9       	vpmovzxdq ymm5,xmm1
    784e:	c4 e3 7d 39 c0 01    	vextracti128 xmm0,ymm0,0x1
    7854:	c5 d5 d4 ea          	vpaddq ymm5,ymm5,ymm2
    7858:	c4 e3 7d 39 ca 01    	vextracti128 xmm2,ymm1,0x1
    785e:	c4 e2 7d 35 ce       	vpmovzxdq ymm1,xmm6
    7863:	c4 e2 7d 35 d2       	vpmovzxdq ymm2,xmm2
    7868:	c4 e2 7d 33 c0       	vpmovzxwd ymm0,xmm0
    786d:	c5 ed d4 d5          	vpaddq ymm2,ymm2,ymm5
    7871:	c4 e2 7d 35 e8       	vpmovzxdq ymm5,xmm0
    7876:	c4 e3 7d 39 c0 01    	vextracti128 xmm0,ymm0,0x1
    787c:	c5 f5 d4 d2          	vpaddq ymm2,ymm1,ymm2
    7880:	c4 e3 7d 39 f1 01    	vextracti128 xmm1,ymm6,0x1
    7886:	c4 e2 7d 35 c0       	vpmovzxdq ymm0,xmm0
    788b:	c4 e2 7d 35 c9       	vpmovzxdq ymm1,xmm1
    7890:	c5 f5 d4 ca          	vpaddq ymm1,ymm1,ymm2
    7894:	c5 d5 d4 e9          	vpaddq ymm5,ymm5,ymm1
    7898:	c5 fd d4 ed          	vpaddq ymm5,ymm0,ymm5
    789c:	48 39 c8             	cmp    rax,rcx
    789f:	0f 85 5b ff ff ff    	jne    7800 <error_at_line@@Base+0x6897>
    78a5:	c4 e3 7d 39 e8 01    	vextracti128 xmm0,ymm5,0x1
    78ab:	c5 f9 d4 c5          	vpaddq xmm0,xmm0,xmm5
    78af:	c5 f1 73 d8 08       	vpsrldq xmm1,xmm0,0x8
    78b4:	c5 f9 d4 c1          	vpaddq xmm0,xmm0,xmm1
    78b8:	c4 e1 f9 7e c0       	vmovq  rax,xmm0
    78bd:	48 01 c3             	add    rbx,rax
    78c0:	e9 7b fe ff ff       	jmp    7740 <error_at_line@@Base+0x67d7>
    78c5:	0f 1f 00             	nop    DWORD PTR [rax]
    78c8:	48 8d 14 04          	lea    rdx,[rsp+rax*1]
    78cc:	48 89 e0             	mov    rax,rsp
    78cf:	48 39 d4             	cmp    rsp,rdx
    78d2:	0f 83 68 fe ff ff    	jae    7740 <error_at_line@@Base+0x67d7>
    78d8:	0f 1f 84 00 00 00 00 	nop    DWORD PTR [rax+rax*1+0x0]
    78df:	00 
    78e0:	31 c9                	xor    ecx,ecx
    78e2:	80 38 0a             	cmp    BYTE PTR [rax],0xa
    78e5:	0f 94 c1             	sete   cl
    78e8:	48 83 c0 01          	add    rax,0x1
    78ec:	48 01 cb             	add    rbx,rcx
    78ef:	48 39 d0             	cmp    rax,rdx
    78f2:	72 ec                	jb     78e0 <error_at_line@@Base+0x6977>
    78f4:	e9 47 fe ff ff       	jmp    7740 <error_at_line@@Base+0x67d7>
    78f9:	0f 1f 80 00 00 00 00 	nop    DWORD PTR [rax+0x0]
    7900:	b8 00 00 00 00       	mov    eax,0x0
    7905:	74 3a                	je     7941 <error_at_line@@Base+0x69d8>
    7907:	c5 f8 77             	vzeroupper
    790a:	e8 f1 8e ff ff       	call   800 <__errno_location@plt>
    790f:	8b 00                	mov    eax,DWORD PTR [rax]
    7911:	41 89 07             	mov    DWORD PTR [r15],eax
    7914:	49 89 5f 08          	mov    QWORD PTR [r15+0x8],rbx
    7918:	4d 89 67 10          	mov    QWORD PTR [r15+0x10],r12
    791c:	48 8b 84 24 18 00 04 	mov    rax,QWORD PTR [rsp+0x40018]
    7923:	00 
    7924:	64 48 2b 04 25 28 00 	sub    rax,QWORD PTR fs:0x28
    792b:	00 00 
    792d:	75 17                	jne    7946 <error_at_line@@Base+0x69dd>
    792f:	48 8d 65 d8          	lea    rsp,[rbp-0x28]
    7933:	4c 89 f8             	mov    rax,r15
    7936:	5b                   	pop    rbx
    7937:	41 5c                	pop    r12
    7939:	41 5d                	pop    r13
    793b:	41 5e                	pop    r14
    793d:	41 5f                	pop    r15
    793f:	5d                   	pop    rbp
    7940:	c3                   	ret
    7941:	c5 f8 77             	vzeroupper
    7944:	eb cb                	jmp    7911 <error_at_line@@Base+0x69a8>
    7946:	e8 a5 8f ff ff       	call   8f0 <__stack_chk_fail@plt>
    794b:	0f 1f 44 00 00       	nop    DWORD PTR [rax+rax*1+0x0]
    7950:	55                   	push   rbp
    7951:	ba 05 00 00 00       	mov    edx,0x5
    7956:	48 8d 35 41 3d 00 00 	lea    rsi,[rip+0x3d41]        # b69e <error_at_line@@Base+0xa735>
    795d:	48 8d 3d 4b 3d 00 00 	lea    rdi,[rip+0x3d4b]        # b6af <error_at_line@@Base+0xa746>
    7964:	48 89 e5             	mov    rbp,rsp
    7967:	53                   	push   rbx
    7968:	50                   	push   rax
    7969:	8b 1d b5 76 00 00    	mov    ebx,DWORD PTR [rip+0x76b5]        # f024 <error_at_line@@Base+0xe0bb>
    796f:	e8 4c 8f ff ff       	call   8c0 <dcgettext@plt>
    7974:	48 8d 15 ba 3f 00 00 	lea    rdx,[rip+0x3fba]        # b935 <error_at_line@@Base+0xa9cc>
    797b:	31 f6                	xor    esi,esi
    797d:	89 df                	mov    edi,ebx
    797f:	48 89 c1             	mov    rcx,rax
    7982:	31 c0                	xor    eax,eax
    7984:	e8 e4 93 ff ff       	call   d6d <error@@Base>
    7989:	e8 62 8e ff ff       	call   7f0 <abort@plt>
    798e:	66 90                	xchg   ax,ax
    7990:	55                   	push   rbp
    7991:	48 89 e5             	mov    rbp,rsp
    7994:	41 57                	push   r15
    7996:	49 89 d7             	mov    r15,rdx
    7999:	41 56                	push   r14
    799b:	41 55                	push   r13
    799d:	41 54                	push   r12
    799f:	53                   	push   rbx
    79a0:	89 fb                	mov    ebx,edi
    79a2:	48 83 ec 38          	sub    rsp,0x38
    79a6:	48 89 75 c8          	mov    QWORD PTR [rbp-0x38],rsi
    79aa:	e8 51 8e ff ff       	call   800 <__errno_location@plt>
    79af:	4c 8b 2d ea 76 00 00 	mov    r13,QWORD PTR [rip+0x76ea]        # f0a0 <obstack_alloc_failed_handler@@Base+0x20>
    79b6:	49 89 c4             	mov    r12,rax
    79b9:	8b 00                	mov    eax,DWORD PTR [rax]
    79bb:	89 45 c4             	mov    DWORD PTR [rbp-0x3c],eax
    79be:	8b 05 5c 76 00 00    	mov    eax,DWORD PTR [rip+0x765c]        # f020 <error_at_line@@Base+0xe0b7>
    79c4:	39 c3                	cmp    ebx,eax
    79c6:	0f 8c de 00 00 00    	jl     7aaa <error_at_line@@Base+0x6b41>
    79cc:	48 63 d0             	movsxd rdx,eax
    79cf:	48 8d 0d ba 76 00 00 	lea    rcx,[rip+0x76ba]        # f090 <obstack_alloc_failed_handler@@Base+0x10>
    79d6:	31 ff                	xor    edi,edi
    79d8:	89 de                	mov    esi,ebx
    79da:	49 39 cd             	cmp    r13,rcx
    79dd:	49 89 d0             	mov    r8,rdx
    79e0:	49 0f 45 fd          	cmovne rdi,r13
    79e4:	49 d1 f8             	sar    r8,1
    79e7:	29 c6                	sub    esi,eax
    79e9:	49 01 d0             	add    r8,rdx
    79ec:	8d 46 01             	lea    eax,[rsi+0x1]
    79ef:	4d 89 c6             	mov    r14,r8
    79f2:	49 c1 e6 04          	shl    r14,0x4
    79f6:	49 83 fe 7f          	cmp    r14,0x7f
    79fa:	0f 8e 70 01 00 00    	jle    7b70 <error_at_line@@Base+0x6c07>
    7a00:	4c 89 c6             	mov    rsi,r8
    7a03:	48 29 d6             	sub    rsi,rdx
    7a06:	48 39 f0             	cmp    rax,rsi
    7a09:	7e 22                	jle    7a2d <error_at_line@@Base+0x6ac4>
    7a0b:	4c 8d 04 10          	lea    r8,[rax+rdx*1]
    7a0f:	b8 00 00 00 80       	mov    eax,0x80000000
    7a14:	49 39 c0             	cmp    r8,rax
    7a17:	0f 84 94 01 00 00    	je     7bb1 <error_at_line@@Base+0x6c48>
    7a1d:	4d 89 c6             	mov    r14,r8
    7a20:	b8 01 00 00 00       	mov    eax,0x1
    7a25:	49 c1 e6 04          	shl    r14,0x4
    7a29:	4c 0f 44 f0          	cmove  r14,rax
    7a2d:	4c 89 f6             	mov    rsi,r14
    7a30:	48 89 55 b0          	mov    QWORD PTR [rbp-0x50],rdx
    7a34:	4c 89 45 b8          	mov    QWORD PTR [rbp-0x48],r8
    7a38:	e8 73 90 ff ff       	call   ab0 <realloc@plt>
    7a3d:	49 89 c1             	mov    r9,rax
    7a40:	48 85 c0             	test   rax,rax
    7a43:	0f 84 68 01 00 00    	je     7bb1 <error_at_line@@Base+0x6c48>
    7a49:	48 8d 0d 40 76 00 00 	lea    rcx,[rip+0x7640]        # f090 <obstack_alloc_failed_handler@@Base+0x10>
    7a50:	48 89 05 49 76 00 00 	mov    QWORD PTR [rip+0x7649],rax        # f0a0 <obstack_alloc_failed_handler@@Base+0x20>
    7a57:	4c 8b 45 b8          	mov    r8,QWORD PTR [rbp-0x48]
    7a5b:	49 39 cd             	cmp    r13,rcx
    7a5e:	48 8b 55 b0          	mov    rdx,QWORD PTR [rbp-0x50]
    7a62:	0f 84 28 01 00 00    	je     7b90 <error_at_line@@Base+0x6c27>
    7a68:	48 89 d7             	mov    rdi,rdx
    7a6b:	4c 89 c0             	mov    rax,r8
    7a6e:	4c 89 f1             	mov    rcx,r14
    7a71:	4c 89 45 b0          	mov    QWORD PTR [rbp-0x50],r8
    7a75:	48 c1 e7 04          	shl    rdi,0x4
    7a79:	4c 89 4d b8          	mov    QWORD PTR [rbp-0x48],r9
    7a7d:	4c 39 f7             	cmp    rdi,r14
    7a80:	48 0f 43 cf          	cmovae rcx,rdi
    7a84:	48 29 d0             	sub    rax,rdx
    7a87:	31 f6                	xor    esi,esi
    7a89:	48 c1 e0 04          	shl    rax,0x4
    7a8d:	48 29 f9             	sub    rcx,rdi
    7a90:	48 89 c2             	mov    rdx,rax
    7a93:	4c 01 cf             	add    rdi,r9
    7a96:	e8 c5 90 ff ff       	call   b60 <__memset_chk@plt>
    7a9b:	4c 8b 45 b0          	mov    r8,QWORD PTR [rbp-0x50]
    7a9f:	4c 8b 6d b8          	mov    r13,QWORD PTR [rbp-0x48]
    7aa3:	44 89 05 76 75 00 00 	mov    DWORD PTR [rip+0x7576],r8d        # f020 <error_at_line@@Base+0xe0b7>
    7aaa:	45 8b 47 04          	mov    r8d,DWORD PTR [r15+0x4]
    7aae:	48 c1 e3 04          	shl    rbx,0x4
    7ab2:	49 8d 47 08          	lea    rax,[r15+0x8]
    7ab6:	41 8b 0f             	mov    ecx,DWORD PTR [r15]
    7ab9:	4c 01 eb             	add    rbx,r13
    7abc:	48 89 45 b0          	mov    QWORD PTR [rbp-0x50],rax
    7ac0:	49 89 c1             	mov    r9,rax
    7ac3:	41 83 c8 01          	or     r8d,0x1
    7ac7:	4c 8b 33             	mov    r14,QWORD PTR [rbx]
    7aca:	4c 8b 6b 08          	mov    r13,QWORD PTR [rbx+0x8]
    7ace:	44 89 45 b8          	mov    DWORD PTR [rbp-0x48],r8d
    7ad2:	41 ff 77 30          	push   QWORD PTR [r15+0x30]
    7ad6:	4c 89 f6             	mov    rsi,r14
    7ad9:	4c 89 ef             	mov    rdi,r13
    7adc:	41 ff 77 28          	push   QWORD PTR [r15+0x28]
    7ae0:	48 8b 55 c8          	mov    rdx,QWORD PTR [rbp-0x38]
    7ae4:	e8 67 dc ff ff       	call   5750 <error_at_line@@Base+0x47e7>
    7ae9:	59                   	pop    rcx
    7aea:	5e                   	pop    rsi
    7aeb:	4c 39 f0             	cmp    rax,r14
    7aee:	72 64                	jb     7b54 <error_at_line@@Base+0x6beb>
    7af0:	48 8d 70 01          	lea    rsi,[rax+0x1]
    7af4:	48 8d 05 05 76 00 00 	lea    rax,[rip+0x7605]        # f100 <error_print_progname@@Base+0x18>
    7afb:	48 89 33             	mov    QWORD PTR [rbx],rsi
    7afe:	49 39 c5             	cmp    r13,rax
    7b01:	74 10                	je     7b13 <error_at_line@@Base+0x6baa>
    7b03:	4c 89 ef             	mov    rdi,r13
    7b06:	48 89 75 a8          	mov    QWORD PTR [rbp-0x58],rsi
    7b0a:	e8 c1 8c ff ff       	call   7d0 <free@plt>
    7b0f:	48 8b 75 a8          	mov    rsi,QWORD PTR [rbp-0x58]
    7b13:	48 89 f7             	mov    rdi,rsi
    7b16:	48 89 75 a8          	mov    QWORD PTR [rbp-0x58],rsi
    7b1a:	e8 71 8f ff ff       	call   a90 <malloc@plt>
    7b1f:	49 89 c5             	mov    r13,rax
    7b22:	48 85 c0             	test   rax,rax
    7b25:	0f 84 86 00 00 00    	je     7bb1 <error_at_line@@Base+0x6c48>
    7b2b:	48 89 43 08          	mov    QWORD PTR [rbx+0x8],rax
    7b2f:	41 8b 0f             	mov    ecx,DWORD PTR [r15]
    7b32:	48 89 c7             	mov    rdi,rax
    7b35:	41 ff 77 30          	push   QWORD PTR [r15+0x30]
    7b39:	41 ff 77 28          	push   QWORD PTR [r15+0x28]
    7b3d:	48 8b 55 c8          	mov    rdx,QWORD PTR [rbp-0x38]
    7b41:	4c 8b 4d b0          	mov    r9,QWORD PTR [rbp-0x50]
    7b45:	44 8b 45 b8          	mov    r8d,DWORD PTR [rbp-0x48]
    7b49:	48 8b 75 a8          	mov    rsi,QWORD PTR [rbp-0x58]
    7b4d:	e8 fe db ff ff       	call   5750 <error_at_line@@Base+0x47e7>
    7b52:	58                   	pop    rax
    7b53:	5a                   	pop    rdx
    7b54:	8b 45 c4             	mov    eax,DWORD PTR [rbp-0x3c]
    7b57:	41 89 04 24          	mov    DWORD PTR [r12],eax
    7b5b:	48 8d 65 d8          	lea    rsp,[rbp-0x28]
    7b5f:	4c 89 e8             	mov    rax,r13
    7b62:	5b                   	pop    rbx
    7b63:	41 5c                	pop    r12
    7b65:	41 5d                	pop    r13
    7b67:	41 5e                	pop    r14
    7b69:	41 5f                	pop    r15
    7b6b:	5d                   	pop    rbp
    7b6c:	c3                   	ret
    7b6d:	0f 1f 00             	nop    DWORD PTR [rax]
    7b70:	be 08 00 00 00       	mov    esi,0x8
    7b75:	48 29 d6             	sub    rsi,rdx
    7b78:	48 39 f0             	cmp    rax,rsi
    7b7b:	7e 23                	jle    7ba0 <error_at_line@@Base+0x6c37>
    7b7d:	4c 8d 04 10          	lea    r8,[rax+rdx*1]
    7b81:	e9 97 fe ff ff       	jmp    7a1d <error_at_line@@Base+0x6ab4>
    7b86:	66 2e 0f 1f 84 00 00 	cs nop WORD PTR [rax+rax*1+0x0]
    7b8d:	00 00 00 
    7b90:	66 0f 6f 05 f8 74 00 	movdqa xmm0,XMMWORD PTR [rip+0x74f8]        # f090 <obstack_alloc_failed_handler@@Base+0x10>
    7b97:	00 
    7b98:	0f 11 00             	movups XMMWORD PTR [rax],xmm0
    7b9b:	e9 c8 fe ff ff       	jmp    7a68 <error_at_line@@Base+0x6aff>
    7ba0:	41 be 80 00 00 00    	mov    r14d,0x80
    7ba6:	41 b8 08 00 00 00    	mov    r8d,0x8
    7bac:	e9 7c fe ff ff       	jmp    7a2d <error_at_line@@Base+0x6ac4>
    7bb1:	e8 9a fd ff ff       	call   7950 <error_at_line@@Base+0x69e7>
    7bb6:	66 2e 0f 1f 84 00 00 	cs nop WORD PTR [rax+rax*1+0x0]
    7bbd:	00 00 00 
    7bc0:	f3 0f 1e fa          	endbr64
    7bc4:	55                   	push   rbp
    7bc5:	48 89 e5             	mov    rbp,rsp
    7bc8:	48 83 ec 10          	sub    rsp,0x10
    7bcc:	48 8b 05 bd 73 00 00 	mov    rax,QWORD PTR [rip+0x73bd]        # ef90 <error_at_line@@Base+0xe027>
    7bd3:	48 8b 38             	mov    rdi,QWORD PTR [rax]
    7bd6:	e8 05 f8 ff ff       	call   73e0 <error_at_line@@Base+0x6477>
    7bdb:	85 c0                	test   eax,eax
    7bdd:	0f 85 9c 92 ff ff    	jne    e7f <error@@Base+0x112>
    7be3:	48 8b 05 f6 73 00 00 	mov    rax,QWORD PTR [rip+0x73f6]        # efe0 <error_at_line@@Base+0xe077>
    7bea:	48 8b 38             	mov    rdi,QWORD PTR [rax]
    7bed:	e8 ee f7 ff ff       	call   73e0 <error_at_line@@Base+0x6477>
    7bf2:	85 c0                	test   eax,eax
    7bf4:	75 02                	jne    7bf8 <error_at_line@@Base+0x6c8f>
    7bf6:	c9                   	leave
    7bf7:	c3                   	ret
    7bf8:	8b 3d 26 74 00 00    	mov    edi,DWORD PTR [rip+0x7426]        # f024 <error_at_line@@Base+0xe0bb>
    7bfe:	48 89 5d f8          	mov    QWORD PTR [rbp-0x8],rbx
    7c02:	e8 19 8c ff ff       	call   820 <_exit@plt>
    7c07:	66 0f 1f 84 00 00 00 	nop    WORD PTR [rax+rax*1+0x0]
    7c0e:	00 00 
    7c10:	55                   	push   rbp
    7c11:	66 0f ef c0          	pxor   xmm0,xmm0
    7c15:	48 89 fe             	mov    rsi,rdi
    7c18:	31 ff                	xor    edi,edi
    7c1a:	48 89 e5             	mov    rbp,rsp
    7c1d:	48 83 ec 40          	sub    rsp,0x40
    7c21:	64 48 8b 14 25 28 00 	mov    rdx,QWORD PTR fs:0x28
    7c28:	00 00 
    7c2a:	48 89 55 f8          	mov    QWORD PTR [rbp-0x8],rdx
    7c2e:	31 d2                	xor    edx,edx
    7c30:	48 8d 55 c0          	lea    rdx,[rbp-0x40]
    7c34:	48 c7 45 c0 04 00 00 	mov    QWORD PTR [rbp-0x40],0x4
    7c3b:	00 
    7c3c:	0f 11 45 c8          	movups XMMWORD PTR [rbp-0x38],xmm0
    7c40:	0f 11 45 d8          	movups XMMWORD PTR [rbp-0x28],xmm0
    7c44:	0f 11 45 e8          	movups XMMWORD PTR [rbp-0x18],xmm0
    7c48:	e8 43 fd ff ff       	call   7990 <error_at_line@@Base+0x6a27>
    7c4d:	48 8b 55 f8          	mov    rdx,QWORD PTR [rbp-0x8]
    7c51:	64 48 2b 14 25 28 00 	sub    rdx,QWORD PTR fs:0x28
    7c58:	00 00 
    7c5a:	75 02                	jne    7c5e <error_at_line@@Base+0x6cf5>
    7c5c:	c9                   	leave
    7c5d:	c3                   	ret
    7c5e:	e8 8d 8c ff ff       	call   8f0 <__stack_chk_fail@plt>
    7c63:	66 90                	xchg   ax,ax
    7c65:	66 66 2e 0f 1f 84 00 	data16 cs nop WORD PTR [rax+rax*1+0x0]
    7c6c:	00 00 00 00 
    7c70:	55                   	push   rbp
    7c71:	66 0f ef c0          	pxor   xmm0,xmm0
    7c75:	48 89 fe             	mov    rsi,rdi
    7c78:	31 ff                	xor    edi,edi
    7c7a:	48 89 e5             	mov    rbp,rsp
    7c7d:	48 83 ec 40          	sub    rsp,0x40
    7c81:	66 0f 6f 0d f7 4b 00 	movdqa xmm1,XMMWORD PTR [rip+0x4bf7]        # c880 <error_at_line@@Base+0xb917>
    7c88:	00 
    7c89:	64 48 8b 14 25 28 00 	mov    rdx,QWORD PTR fs:0x28
    7c90:	00 00 
    7c92:	48 89 55 f8          	mov    QWORD PTR [rbp-0x8],rdx
    7c96:	31 d2                	xor    edx,edx
    7c98:	48 8d 55 c0          	lea    rdx,[rbp-0x40]
    7c9c:	48 c7 45 c0 03 00 00 	mov    QWORD PTR [rbp-0x40],0x3
    7ca3:	00 
    7ca4:	0f 11 4d c8          	movups XMMWORD PTR [rbp-0x38],xmm1
    7ca8:	0f 11 45 d8          	movups XMMWORD PTR [rbp-0x28],xmm0
    7cac:	0f 11 45 e8          	movups XMMWORD PTR [rbp-0x18],xmm0
    7cb0:	e8 db fc ff ff       	call   7990 <error_at_line@@Base+0x6a27>
    7cb5:	48 8b 55 f8          	mov    rdx,QWORD PTR [rbp-0x8]
    7cb9:	64 48 2b 14 25 28 00 	sub    rdx,QWORD PTR fs:0x28
    7cc0:	00 00 
    7cc2:	75 02                	jne    7cc6 <error_at_line@@Base+0x6d5d>
    7cc4:	c9                   	leave
    7cc5:	c3                   	ret
    7cc6:	e8 25 8c ff ff       	call   8f0 <__stack_chk_fail@plt>
    7ccb:	0f 1f 44 00 00       	nop    DWORD PTR [rax+rax*1+0x0]
    7cd0:	55                   	push   rbp
    7cd1:	49 89 f2             	mov    r10,rsi
    7cd4:	48 8d 35 f6 4a 00 00 	lea    rsi,[rip+0x4af6]        # c7d1 <error_at_line@@Base+0xb868>
    7cdb:	48 89 e5             	mov    rbp,rsp
    7cde:	41 56                	push   r14
    7ce0:	49 89 d6             	mov    r14,rdx
    7ce3:	41 55                	push   r13
    7ce5:	49 89 cd             	mov    r13,rcx
    7ce8:	41 54                	push   r12
    7cea:	53                   	push   rbx
    7ceb:	4c 89 c3             	mov    rbx,r8
    7cee:	48 83 ec 30          	sub    rsp,0x30
    7cf2:	80 3d 97 77 00 00 00 	cmp    BYTE PTR [rip+0x7797],0x0        # f490 <error_print_progname@@Base+0x3a8>
    7cf9:	64 4c 8b 24 25 28 00 	mov    r12,QWORD PTR fs:0x28
    7d00:	00 00 
    7d02:	4c 89 65 d8          	mov    QWORD PTR [rbp-0x28],r12
    7d06:	4d 89 cc             	mov    r12,r9
    7d09:	0f 85 c1 02 00 00    	jne    7fd0 <error_at_line@@Base+0x7067>
    7d0f:	80 3d 75 77 00 00 00 	cmp    BYTE PTR [rip+0x7775],0x0        # f48b <error_print_progname@@Base+0x3a3>
    7d16:	0f 85 34 02 00 00    	jne    7f50 <error_at_line@@Base+0x6fe7>
    7d1c:	80 3d 67 77 00 00 00 	cmp    BYTE PTR [rip+0x7767],0x0        # f48a <error_print_progname@@Base+0x3a2>
    7d23:	0f 85 a7 01 00 00    	jne    7ed0 <error_at_line@@Base+0x6f67>
    7d29:	80 3d 59 77 00 00 00 	cmp    BYTE PTR [rip+0x7759],0x0        # f489 <error_print_progname@@Base+0x3a1>
    7d30:	0f 85 1a 01 00 00    	jne    7e50 <error_at_line@@Base+0x6ee7>
    7d36:	80 3d 4b 77 00 00 00 	cmp    BYTE PTR [rip+0x774b],0x0        # f488 <error_print_progname@@Base+0x3a0>
    7d3d:	0f 85 8d 00 00 00    	jne    7dd0 <error_at_line@@Base+0x6e67>
    7d43:	4d 85 e4             	test   r12,r12
    7d46:	74 33                	je     7d7b <error_at_line@@Base+0x6e12>
    7d48:	be 0a 00 00 00       	mov    esi,0xa
    7d4d:	4c 89 e7             	mov    rdi,r12
    7d50:	e8 cb 8b ff ff       	call   920 <strchr@plt>
    7d55:	48 85 c0             	test   rax,rax
    7d58:	74 0b                	je     7d65 <error_at_line@@Base+0x6dfc>
    7d5a:	4c 89 e7             	mov    rdi,r12
    7d5d:	e8 0e ff ff ff       	call   7c70 <error_at_line@@Base+0x6d07>
    7d62:	49 89 c4             	mov    r12,rax
    7d65:	4c 89 e2             	mov    rdx,r12
    7d68:	48 8d 35 c5 3b 00 00 	lea    rsi,[rip+0x3bc5]        # b934 <error_at_line@@Base+0xa9cb>
    7d6f:	bf 02 00 00 00       	mov    edi,0x2
    7d74:	31 c0                	xor    eax,eax
    7d76:	e8 55 8d ff ff       	call   ad0 <__printf_chk@plt>
    7d7b:	48 8b 1d 0e 72 00 00 	mov    rbx,QWORD PTR [rip+0x720e]        # ef90 <error_at_line@@Base+0xe027>
    7d82:	48 8b 3b             	mov    rdi,QWORD PTR [rbx]
    7d85:	48 8b 47 28          	mov    rax,QWORD PTR [rdi+0x28]
    7d89:	48 3b 47 30          	cmp    rax,QWORD PTR [rdi+0x30]
    7d8d:	0f 83 2d 03 00 00    	jae    80c0 <error_at_line@@Base+0x7157>
    7d93:	48 8d 50 01          	lea    rdx,[rax+0x1]
    7d97:	48 89 57 28          	mov    QWORD PTR [rdi+0x28],rdx
    7d9b:	c6 00 0a             	mov    BYTE PTR [rax],0xa
    7d9e:	4c 8b 23             	mov    r12,QWORD PTR [rbx]
    7da1:	41 f6 04 24 20       	test   BYTE PTR [r12],0x20
    7da6:	0f 85 23 03 00 00    	jne    80cf <error_at_line@@Base+0x7166>
    7dac:	48 8b 45 d8          	mov    rax,QWORD PTR [rbp-0x28]
    7db0:	64 48 2b 04 25 28 00 	sub    rax,QWORD PTR fs:0x28
    7db7:	00 00 
    7db9:	0f 85 64 03 00 00    	jne    8123 <error_at_line@@Base+0x71ba>
    7dbf:	48 83 c4 30          	add    rsp,0x30
    7dc3:	5b                   	pop    rbx
    7dc4:	41 5c                	pop    r12
    7dc6:	41 5d                	pop    r13
    7dc8:	41 5e                	pop    r14
    7dca:	5d                   	pop    rbp
    7dcb:	c3                   	ret
    7dcc:	0f 1f 40 00          	nop    DWORD PTR [rax+0x0]
    7dd0:	c6 45 d4 00          	mov    BYTE PTR [rbp-0x2c],0x0
    7dd4:	48 8d 4d d4          	lea    rcx,[rbp-0x2c]
    7dd8:	48 bf 67 66 66 66 66 	movabs rdi,0x6666666666666667
    7ddf:	66 66 66 
    7de2:	48 85 db             	test   rbx,rbx
    7de5:	0f 88 75 02 00 00    	js     8060 <error_at_line@@Base+0x70f7>
    7deb:	66 2e 0f 1f 84 00 00 	cs nop WORD PTR [rax+rax*1+0x0]
    7df2:	00 00 00 
    7df5:	66 66 2e 0f 1f 84 00 	data16 cs nop WORD PTR [rax+rax*1+0x0]
    7dfc:	00 00 00 00 
    7e00:	48 89 d8             	mov    rax,rbx
    7e03:	48 83 e9 01          	sub    rcx,0x1
    7e07:	48 f7 ef             	imul   rdi
    7e0a:	48 89 d8             	mov    rax,rbx
    7e0d:	48 c1 f8 3f          	sar    rax,0x3f
    7e11:	48 c1 fa 02          	sar    rdx,0x2
    7e15:	48 29 c2             	sub    rdx,rax
    7e18:	48 8d 04 92          	lea    rax,[rdx+rdx*4]
    7e1c:	48 01 c0             	add    rax,rax
    7e1f:	48 29 c3             	sub    rbx,rax
    7e22:	83 c3 30             	add    ebx,0x30
    7e25:	88 19                	mov    BYTE PTR [rcx],bl
    7e27:	48 89 d3             	mov    rbx,rdx
    7e2a:	48 85 d2             	test   rdx,rdx
    7e2d:	75 d1                	jne    7e00 <error_at_line@@Base+0x6e97>
    7e2f:	8b 15 57 76 00 00    	mov    edx,DWORD PTR [rip+0x7657]        # f48c <error_print_progname@@Base+0x3a4>
    7e35:	bf 02 00 00 00       	mov    edi,0x2
    7e3a:	31 c0                	xor    eax,eax
    7e3c:	e8 8f 8c ff ff       	call   ad0 <__printf_chk@plt>
    7e41:	e9 fd fe ff ff       	jmp    7d43 <error_at_line@@Base+0x6dda>
    7e46:	66 2e 0f 1f 84 00 00 	cs nop WORD PTR [rax+rax*1+0x0]
    7e4d:	00 00 00 
    7e50:	c6 45 d4 00          	mov    BYTE PTR [rbp-0x2c],0x0
    7e54:	48 8d 7d d4          	lea    rdi,[rbp-0x2c]
    7e58:	49 b8 cd cc cc cc cc 	movabs r8,0xcccccccccccccccd
    7e5f:	cc cc cc 
    7e62:	0f 1f 84 00 00 00 00 	nop    DWORD PTR [rax+rax*1+0x0]
    7e69:	00 
    7e6a:	66 66 2e 0f 1f 84 00 	data16 cs nop WORD PTR [rax+rax*1+0x0]
    7e71:	00 00 00 00 
    7e75:	66 66 2e 0f 1f 84 00 	data16 cs nop WORD PTR [rax+rax*1+0x0]
    7e7c:	00 00 00 00 
    7e80:	4c 89 e8             	mov    rax,r13
    7e83:	48 83 ef 01          	sub    rdi,0x1
    7e87:	49 f7 e0             	mul    r8
    7e8a:	4c 89 e8             	mov    rax,r13
    7e8d:	48 c1 ea 03          	shr    rdx,0x3
    7e91:	48 8d 0c 92          	lea    rcx,[rdx+rdx*4]
    7e95:	48 01 c9             	add    rcx,rcx
    7e98:	48 29 c8             	sub    rax,rcx
    7e9b:	83 c0 30             	add    eax,0x30
    7e9e:	49 83 fd 09          	cmp    r13,0x9
    7ea2:	49 89 d5             	mov    r13,rdx
    7ea5:	88 07                	mov    BYTE PTR [rdi],al
    7ea7:	77 d7                	ja     7e80 <error_at_line@@Base+0x6f17>
    7ea9:	8b 15 dd 75 00 00    	mov    edx,DWORD PTR [rip+0x75dd]        # f48c <error_print_progname@@Base+0x3a4>
    7eaf:	48 89 f9             	mov    rcx,rdi
    7eb2:	31 c0                	xor    eax,eax
    7eb4:	bf 02 00 00 00       	mov    edi,0x2
    7eb9:	e8 12 8c ff ff       	call   ad0 <__printf_chk@plt>
    7ebe:	48 8d 35 0b 49 00 00 	lea    rsi,[rip+0x490b]        # c7d0 <error_at_line@@Base+0xb867>
    7ec5:	e9 6c fe ff ff       	jmp    7d36 <error_at_line@@Base+0x6dcd>
    7eca:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]
    7ed0:	c6 45 d4 00          	mov    BYTE PTR [rbp-0x2c],0x0
    7ed4:	48 8d 7d d4          	lea    rdi,[rbp-0x2c]
    7ed8:	49 b8 cd cc cc cc cc 	movabs r8,0xcccccccccccccccd
    7edf:	cc cc cc 
    7ee2:	0f 1f 84 00 00 00 00 	nop    DWORD PTR [rax+rax*1+0x0]
    7ee9:	00 
    7eea:	66 66 2e 0f 1f 84 00 	data16 cs nop WORD PTR [rax+rax*1+0x0]
    7ef1:	00 00 00 00 
    7ef5:	66 66 2e 0f 1f 84 00 	data16 cs nop WORD PTR [rax+rax*1+0x0]
    7efc:	00 00 00 00 
    7f00:	4c 89 f0             	mov    rax,r14
    7f03:	48 83 ef 01          	sub    rdi,0x1
    7f07:	49 f7 e0             	mul    r8
    7f0a:	4c 89 f0             	mov    rax,r14
    7f0d:	48 c1 ea 03          	shr    rdx,0x3
    7f11:	48 8d 0c 92          	lea    rcx,[rdx+rdx*4]
    7f15:	48 01 c9             	add    rcx,rcx
    7f18:	48 29 c8             	sub    rax,rcx
    7f1b:	83 c0 30             	add    eax,0x30
    7f1e:	49 83 fe 09          	cmp    r14,0x9
    7f22:	49 89 d6             	mov    r14,rdx
    7f25:	88 07                	mov    BYTE PTR [rdi],al
    7f27:	77 d7                	ja     7f00 <error_at_line@@Base+0x6f97>
    7f29:	8b 15 5d 75 00 00    	mov    edx,DWORD PTR [rip+0x755d]        # f48c <error_print_progname@@Base+0x3a4>
    7f2f:	48 89 f9             	mov    rcx,rdi
    7f32:	31 c0                	xor    eax,eax
    7f34:	bf 02 00 00 00       	mov    edi,0x2
    7f39:	e8 92 8b ff ff       	call   ad0 <__printf_chk@plt>
    7f3e:	48 8d 35 8b 48 00 00 	lea    rsi,[rip+0x488b]        # c7d0 <error_at_line@@Base+0xb867>
    7f45:	e9 df fd ff ff       	jmp    7d29 <error_at_line@@Base+0x6dc0>
    7f4a:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]
    7f50:	c6 45 d4 00          	mov    BYTE PTR [rbp-0x2c],0x0
    7f54:	48 8d 4d d4          	lea    rcx,[rbp-0x2c]
    7f58:	48 bf cd cc cc cc cc 	movabs rdi,0xcccccccccccccccd
    7f5f:	cc cc cc 
    7f62:	0f 1f 84 00 00 00 00 	nop    DWORD PTR [rax+rax*1+0x0]
    7f69:	00 
    7f6a:	66 66 2e 0f 1f 84 00 	data16 cs nop WORD PTR [rax+rax*1+0x0]
    7f71:	00 00 00 00 
    7f75:	66 66 2e 0f 1f 84 00 	data16 cs nop WORD PTR [rax+rax*1+0x0]
    7f7c:	00 00 00 00 
    7f80:	4c 89 d0             	mov    rax,r10
    7f83:	48 83 e9 01          	sub    rcx,0x1
    7f87:	48 f7 e7             	mul    rdi
    7f8a:	4c 89 d0             	mov    rax,r10
    7f8d:	48 c1 ea 03          	shr    rdx,0x3
    7f91:	4c 8d 04 92          	lea    r8,[rdx+rdx*4]
    7f95:	4d 01 c0             	add    r8,r8
    7f98:	4c 29 c0             	sub    rax,r8
    7f9b:	83 c0 30             	add    eax,0x30
    7f9e:	49 83 fa 09          	cmp    r10,0x9
    7fa2:	49 89 d2             	mov    r10,rdx
    7fa5:	88 01                	mov    BYTE PTR [rcx],al
    7fa7:	77 d7                	ja     7f80 <error_at_line@@Base+0x7017>
    7fa9:	8b 15 dd 74 00 00    	mov    edx,DWORD PTR [rip+0x74dd]        # f48c <error_print_progname@@Base+0x3a4>
    7faf:	bf 02 00 00 00       	mov    edi,0x2
    7fb4:	31 c0                	xor    eax,eax
    7fb6:	e8 15 8b ff ff       	call   ad0 <__printf_chk@plt>
    7fbb:	48 8d 35 0e 48 00 00 	lea    rsi,[rip+0x480e]        # c7d0 <error_at_line@@Base+0xb867>
    7fc2:	e9 55 fd ff ff       	jmp    7d1c <error_at_line@@Base+0x6db3>
    7fc7:	66 0f 1f 84 00 00 00 	nop    WORD PTR [rax+rax*1+0x0]
    7fce:	00 00 
    7fd0:	c6 45 d4 00          	mov    BYTE PTR [rbp-0x2c],0x0
    7fd4:	48 8d 4d d4          	lea    rcx,[rbp-0x2c]
    7fd8:	48 be cd cc cc cc cc 	movabs rsi,0xcccccccccccccccd
    7fdf:	cc cc cc 
    7fe2:	0f 1f 84 00 00 00 00 	nop    DWORD PTR [rax+rax*1+0x0]
    7fe9:	00 
    7fea:	66 66 2e 0f 1f 84 00 	data16 cs nop WORD PTR [rax+rax*1+0x0]
    7ff1:	00 00 00 00 
    7ff5:	66 66 2e 0f 1f 84 00 	data16 cs nop WORD PTR [rax+rax*1+0x0]
    7ffc:	00 00 00 00 
    8000:	48 89 f8             	mov    rax,rdi
    8003:	48 83 e9 01          	sub    rcx,0x1
    8007:	48 f7 e6             	mul    rsi
    800a:	48 89 f8             	mov    rax,rdi
    800d:	48 c1 ea 03          	shr    rdx,0x3
    8011:	4c 8d 04 92          	lea    r8,[rdx+rdx*4]
    8015:	4d 01 c0             	add    r8,r8
    8018:	4c 29 c0             	sub    rax,r8
    801b:	83 c0 30             	add    eax,0x30
    801e:	48 83 ff 09          	cmp    rdi,0x9
    8022:	48 89 d7             	mov    rdi,rdx
    8025:	88 01                	mov    BYTE PTR [rcx],al
    8027:	77 d7                	ja     8000 <error_at_line@@Base+0x7097>
    8029:	8b 15 5d 74 00 00    	mov    edx,DWORD PTR [rip+0x745d]        # f48c <error_print_progname@@Base+0x3a4>
    802f:	48 8d 35 9b 47 00 00 	lea    rsi,[rip+0x479b]        # c7d1 <error_at_line@@Base+0xb868>
    8036:	bf 02 00 00 00       	mov    edi,0x2
    803b:	31 c0                	xor    eax,eax
    803d:	4c 89 55 b8          	mov    QWORD PTR [rbp-0x48],r10
    8041:	e8 8a 8a ff ff       	call   ad0 <__printf_chk@plt>
    8046:	4c 8b 55 b8          	mov    r10,QWORD PTR [rbp-0x48]
    804a:	48 8d 35 7f 47 00 00 	lea    rsi,[rip+0x477f]        # c7d0 <error_at_line@@Base+0xb867>
    8051:	e9 b9 fc ff ff       	jmp    7d0f <error_at_line@@Base+0x6da6>
    8056:	66 2e 0f 1f 84 00 00 	cs nop WORD PTR [rax+rax*1+0x0]
    805d:	00 00 00 
    8060:	49 b8 67 66 66 66 66 	movabs r8,0x6666666666666667
    8067:	66 66 66 
    806a:	48 89 cf             	mov    rdi,rcx
    806d:	0f 1f 84 00 00 00 00 	nop    DWORD PTR [rax+rax*1+0x0]
    8074:	00 
    8075:	66 66 2e 0f 1f 84 00 	data16 cs nop WORD PTR [rax+rax*1+0x0]
    807c:	00 00 00 00 
    8080:	48 89 d8             	mov    rax,rbx
    8083:	48 89 f9             	mov    rcx,rdi
    8086:	48 83 ef 01          	sub    rdi,0x1
    808a:	49 f7 e8             	imul   r8
    808d:	48 89 d8             	mov    rax,rbx
    8090:	48 c1 f8 3f          	sar    rax,0x3f
    8094:	48 c1 fa 02          	sar    rdx,0x2
    8098:	48 29 c2             	sub    rdx,rax
    809b:	48 8d 04 92          	lea    rax,[rdx+rdx*4]
    809f:	8d 44 00 30          	lea    eax,[rax+rax*1+0x30]
    80a3:	29 d8                	sub    eax,ebx
    80a5:	48 89 d3             	mov    rbx,rdx
    80a8:	88 07                	mov    BYTE PTR [rdi],al
    80aa:	48 85 d2             	test   rdx,rdx
    80ad:	75 d1                	jne    8080 <error_at_line@@Base+0x7117>
    80af:	c6 47 ff 2d          	mov    BYTE PTR [rdi-0x1],0x2d
    80b3:	48 83 e9 02          	sub    rcx,0x2
    80b7:	e9 73 fd ff ff       	jmp    7e2f <error_at_line@@Base+0x6ec6>
    80bc:	0f 1f 40 00          	nop    DWORD PTR [rax+0x0]
    80c0:	be 0a 00 00 00       	mov    esi,0xa
    80c5:	e8 66 88 ff ff       	call   930 <__overflow@plt>
    80ca:	e9 cf fc ff ff       	jmp    7d9e <error_at_line@@Base+0x6e35>
    80cf:	e8 2c 87 ff ff       	call   800 <__errno_location@plt>
    80d4:	4c 89 e7             	mov    rdi,r12
    80d7:	44 8b 28             	mov    r13d,DWORD PTR [rax]
    80da:	e8 b1 8a ff ff       	call   b90 <fflush_unlocked@plt>
    80df:	48 8b 3b             	mov    rdi,QWORD PTR [rbx]
    80e2:	e8 99 87 ff ff       	call   880 <__fpurge@plt>
    80e7:	48 8b 3b             	mov    rdi,QWORD PTR [rbx]
    80ea:	e8 81 87 ff ff       	call   870 <clearerr_unlocked@plt>
    80ef:	ba 05 00 00 00       	mov    edx,0x5
    80f4:	31 ff                	xor    edi,edi
    80f6:	48 8d 35 3a 37 00 00 	lea    rsi,[rip+0x373a]        # b837 <error_at_line@@Base+0xa8ce>
    80fd:	e8 be 87 ff ff       	call   8c0 <dcgettext@plt>
    8102:	48 8b 55 d8          	mov    rdx,QWORD PTR [rbp-0x28]
    8106:	64 48 2b 14 25 28 00 	sub    rdx,QWORD PTR fs:0x28
    810d:	00 00 
    810f:	75 12                	jne    8123 <error_at_line@@Base+0x71ba>
    8111:	48 89 c2             	mov    rdx,rax
    8114:	44 89 ee             	mov    esi,r13d
    8117:	bf 01 00 00 00       	mov    edi,0x1
    811c:	31 c0                	xor    eax,eax
    811e:	e8 4a 8c ff ff       	call   d6d <error@@Base>
    8123:	e8 c8 87 ff ff       	call   8f0 <__stack_chk_fail@plt>
    8128:	0f 1f 84 00 00 00 00 	nop    DWORD PTR [rax+rax*1+0x0]
    812f:	00 
    8130:	55                   	push   rbp
    8131:	48 89 e5             	mov    rbp,rsp
    8134:	41 57                	push   r15
    8136:	41 56                	push   r14
    8138:	41 55                	push   r13
    813a:	41 54                	push   r12
    813c:	53                   	push   rbx
    813d:	4c 8d 9c 24 00 00 fc 	lea    r11,[rsp-0x40000]
    8144:	ff 
    8145:	48 81 ec 00 10 00 00 	sub    rsp,0x1000
    814c:	80 0c 24 00          	or     BYTE PTR [rsp],0x0
    8150:	4c 39 dc             	cmp    rsp,r11
    8153:	75 f0                	jne    8145 <error_at_line@@Base+0x71dc>
    8155:	48 81 ec b8 00 00 00 	sub    rsp,0xb8
    815c:	89 bd 74 ff fb ff    	mov    DWORD PTR [rbp-0x4008c],edi
    8162:	48 89 b5 30 ff fb ff 	mov    QWORD PTR [rbp-0x400d0],rsi
    8169:	64 48 8b 1c 25 28 00 	mov    rbx,QWORD PTR fs:0x28
    8170:	00 00 
    8172:	48 89 5d c8          	mov    QWORD PTR [rbp-0x38],rbx
    8176:	48 89 d3             	mov    rbx,rdx
    8179:	48 89 b5 28 ff fb ff 	mov    QWORD PTR [rbp-0x400d8],rsi
    8180:	48 85 f6             	test   rsi,rsi
    8183:	0f 84 c2 0a 00 00    	je     8c4b <error_at_line@@Base+0x7ce2>
    8189:	e8 42 87 ff ff       	call   8d0 <__ctype_get_mb_cur_max@plt>
    818e:	44 0f b6 25 f3 72 00 	movzx  r12d,BYTE PTR [rip+0x72f3]        # f489 <error_print_progname@@Base+0x3a1>
    8195:	00 
    8196:	0f b6 15 ee 72 00 00 	movzx  edx,BYTE PTR [rip+0x72ee]        # f48b <error_print_progname@@Base+0x3a3>
    819d:	48 83 f8 01          	cmp    rax,0x1
    81a1:	0f 86 d1 01 00 00    	jbe    8378 <error_at_line@@Base+0x740f>
    81a7:	44 0f b6 3d db 72 00 	movzx  r15d,BYTE PTR [rip+0x72db]        # f48a <error_print_progname@@Base+0x3a2>
    81ae:	00 
    81af:	44 89 e0             	mov    eax,r12d
    81b2:	83 f0 01             	xor    eax,0x1
    81b5:	44 09 f8             	or     eax,r15d
    81b8:	84 d2                	test   dl,dl
    81ba:	0f 84 74 01 00 00    	je     8334 <error_at_line@@Base+0x73cb>
    81c0:	84 c0                	test   al,al
    81c2:	0f 85 bd 03 00 00    	jne    8585 <error_at_line@@Base+0x761c>
    81c8:	8b bd 74 ff fb ff    	mov    edi,DWORD PTR [rbp-0x4008c]
    81ce:	b9 02 00 00 00       	mov    ecx,0x2
    81d3:	31 d2                	xor    edx,edx
    81d5:	31 f6                	xor    esi,esi
    81d7:	45 31 ff             	xor    r15d,r15d
    81da:	e8 d1 87 ff ff       	call   9b0 <posix_fadvise@plt>
    81df:	e8 ec 86 ff ff       	call   8d0 <__ctype_get_mb_cur_max@plt>
    81e4:	48 83 f8 01          	cmp    rax,0x1
    81e8:	0f 87 ba 03 00 00    	ja     85a8 <error_at_line@@Base+0x763f>
    81ee:	44 88 bd 78 ff fb ff 	mov    BYTE PTR [rbp-0x40088],r15b
    81f5:	45 31 f6             	xor    r14d,r14d
    81f8:	31 db                	xor    ebx,ebx
    81fa:	45 31 ed             	xor    r13d,r13d
    81fd:	48 c7 85 60 ff fb ff 	mov    QWORD PTR [rbp-0x400a0],0x0
    8204:	00 00 00 00 
    8208:	48 8d b5 c0 ff fb ff 	lea    rsi,[rbp-0x40040]
    820f:	45 31 ff             	xor    r15d,r15d
    8212:	4c 8d 25 6b 43 00 00 	lea    r12,[rip+0x436b]        # c584 <error_at_line@@Base+0xb61b>
    8219:	48 c7 85 80 ff fb ff 	mov    QWORD PTR [rbp-0x40080],0x0
    8220:	00 00 00 00 
    8224:	90                   	nop
    8225:	66 66 2e 0f 1f 84 00 	data16 cs nop WORD PTR [rax+rax*1+0x0]
    822c:	00 00 00 00 
    8230:	8b bd 74 ff fb ff    	mov    edi,DWORD PTR [rbp-0x4008c]
    8236:	ba 00 00 04 00       	mov    edx,0x40000
    823b:	48 89 b5 90 ff fb ff 	mov    QWORD PTR [rbp-0x40070],rsi
    8242:	e8 89 87 ff ff       	call   9d0 <read@plt>
    8247:	48 8b b5 90 ff fb ff 	mov    rsi,QWORD PTR [rbp-0x40070]
    824e:	48 85 c0             	test   rax,rax
    8251:	0f 84 65 04 00 00    	je     86bc <error_at_line@@Base+0x7753>
    8257:	0f 88 ab 09 00 00    	js     8c08 <error_at_line@@Base+0x7c9f>
    825d:	4c 8b 85 80 ff fb ff 	mov    r8,QWORD PTR [rbp-0x40080]
    8264:	48 01 85 60 ff fb ff 	add    QWORD PTR [rbp-0x400a0],rax
    826b:	48 89 f2             	mov    rdx,rsi
    826e:	48 01 f0             	add    rax,rsi
    8271:	0f 1f 40 00          	nop    DWORD PTR [rax+0x0]
    8275:	66 66 2e 0f 1f 84 00 	data16 cs nop WORD PTR [rax+rax*1+0x0]
    827c:	00 00 00 00 
    8280:	0f b6 3a             	movzx  edi,BYTE PTR [rdx]
    8283:	48 83 c2 01          	add    rdx,0x1
    8287:	8d 4f f7             	lea    ecx,[rdi-0x9]
    828a:	80 f9 17             	cmp    cl,0x17
    828d:	77 11                	ja     82a0 <error_at_line@@Base+0x7337>
    828f:	0f b6 c9             	movzx  ecx,cl
    8292:	49 63 0c 8c          	movsxd rcx,DWORD PTR [r12+rcx*4]
    8296:	4c 01 e1             	add    rcx,r12
    8299:	3e ff e1             	notrack jmp rcx
    829c:	0f 1f 40 00          	nop    DWORD PTR [rax+0x0]
    82a0:	48 8d 0d d9 70 00 00 	lea    rcx,[rip+0x70d9]        # f380 <error_print_progname@@Base+0x298>
    82a7:	0f b6 0c 39          	movzx  ecx,BYTE PTR [rcx+rdi*1]
    82ab:	49 01 ce             	add    r14,rcx
    82ae:	48 8d 0d cb 6f 00 00 	lea    rcx,[rip+0x6fcb]        # f280 <error_print_progname@@Base+0x198>
    82b5:	0f b6 0c 39          	movzx  ecx,BYTE PTR [rcx+rdi*1]
    82b9:	09 cb                	or     ebx,ecx
    82bb:	83 f3 01             	xor    ebx,0x1
    82be:	0f b6 db             	movzx  ebx,bl
    82c1:	49 01 df             	add    r15,rbx
    82c4:	89 cb                	mov    ebx,ecx
    82c6:	83 f3 01             	xor    ebx,0x1
    82c9:	0f 1f 80 00 00 00 00 	nop    DWORD PTR [rax+0x0]
    82d0:	48 39 c2             	cmp    rdx,rax
    82d3:	75 ab                	jne    8280 <error_at_line@@Base+0x7317>
    82d5:	4c 89 85 80 ff fb ff 	mov    QWORD PTR [rbp-0x40080],r8
    82dc:	e9 4f ff ff ff       	jmp    8230 <error_at_line@@Base+0x72c7>
    82e1:	0f 1f 80 00 00 00 00 	nop    DWORD PTR [rax+0x0]
    82e8:	49 83 c5 01          	add    r13,0x1
    82ec:	4d 39 f0             	cmp    r8,r14
    82ef:	4d 0f 4c c6          	cmovl  r8,r14
    82f3:	45 31 f6             	xor    r14d,r14d
    82f6:	31 db                	xor    ebx,ebx
    82f8:	eb d6                	jmp    82d0 <error_at_line@@Base+0x7367>
    82fa:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]
    8300:	4c 89 f7             	mov    rdi,r14
    8303:	31 db                	xor    ebx,ebx
    8305:	48 c1 ff 3f          	sar    rdi,0x3f
    8309:	48 c1 ef 3d          	shr    rdi,0x3d
    830d:	49 8d 0c 3e          	lea    rcx,[r14+rdi*1]
    8311:	83 e1 07             	and    ecx,0x7
    8314:	48 29 f9             	sub    rcx,rdi
    8317:	bf 08 00 00 00       	mov    edi,0x8
    831c:	48 29 cf             	sub    rdi,rcx
    831f:	49 01 fe             	add    r14,rdi
    8322:	eb ac                	jmp    82d0 <error_at_line@@Base+0x7367>
    8324:	0f 1f 40 00          	nop    DWORD PTR [rax+0x0]
    8328:	49 83 c6 01          	add    r14,0x1
    832c:	31 db                	xor    ebx,ebx
    832e:	eb a0                	jmp    82d0 <error_at_line@@Base+0x7367>
    8330:	31 db                	xor    ebx,ebx
    8332:	eb 9c                	jmp    82d0 <error_at_line@@Base+0x7367>
    8334:	80 3d 4d 71 00 00 00 	cmp    BYTE PTR [rip+0x714d],0x0        # f488 <error_print_progname@@Base+0x3a0>
    833b:	0f 85 7f fe ff ff    	jne    81c0 <error_at_line@@Base+0x7257>
    8341:	84 c0                	test   al,al
    8343:	0f 84 03 01 00 00    	je     844c <error_at_line@@Base+0x74e3>
    8349:	8b bd 74 ff fb ff    	mov    edi,DWORD PTR [rbp-0x4008c]
    834f:	31 d2                	xor    edx,edx
    8351:	31 f6                	xor    esi,esi
    8353:	b9 02 00 00 00       	mov    ecx,0x2
    8358:	e8 53 86 ff ff       	call   9b0 <posix_fadvise@plt>
    835d:	41 80 ff 01          	cmp    r15b,0x1
    8361:	74 09                	je     836c <error_at_line@@Base+0x7403>
    8363:	45 84 e4             	test   r12b,r12b
    8366:	0f 85 3c 0c 00 00    	jne    8fa8 <error_at_line@@Base+0x803f>
    836c:	44 89 fb             	mov    ebx,r15d
    836f:	eb 44                	jmp    83b5 <error_at_line@@Base+0x744c>
    8371:	0f 1f 80 00 00 00 00 	nop    DWORD PTR [rax+0x0]
    8378:	45 84 e4             	test   r12b,r12b
    837b:	0f 85 b6 00 00 00    	jne    8437 <error_at_line@@Base+0x74ce>
    8381:	44 0f b6 3d 01 71 00 	movzx  r15d,BYTE PTR [rip+0x7101]        # f48a <error_print_progname@@Base+0x3a2>
    8388:	00 
    8389:	45 84 ff             	test   r15b,r15b
    838c:	0f 85 a5 00 00 00    	jne    8437 <error_at_line@@Base+0x74ce>
    8392:	84 d2                	test   dl,dl
    8394:	0f 85 eb 01 00 00    	jne    8585 <error_at_line@@Base+0x761c>
    839a:	8b bd 74 ff fb ff    	mov    edi,DWORD PTR [rbp-0x4008c]
    83a0:	b9 02 00 00 00       	mov    ecx,0x2
    83a5:	31 d2                	xor    edx,edx
    83a7:	31 f6                	xor    esi,esi
    83a9:	0f b6 1d d8 70 00 00 	movzx  ebx,BYTE PTR [rip+0x70d8]        # f488 <error_print_progname@@Base+0x3a0>
    83b0:	e8 fb 85 ff ff       	call   9b0 <posix_fadvise@plt>
    83b5:	84 db                	test   bl,bl
    83b7:	0f 85 22 fe ff ff    	jne    81df <error_at_line@@Base+0x7276>
    83bd:	80 3d 66 6e 00 00 00 	cmp    BYTE PTR [rip+0x6e66],0x0        # f22a <error_print_progname@@Base+0x142>
    83c4:	0f 84 c9 0a 00 00    	je     8e93 <error_at_line@@Base+0x7f2a>
    83ca:	0f 8f 10 0b 00 00    	jg     8ee0 <error_at_line@@Base+0x7f77>
    83d0:	80 3d 52 6e 00 00 00 	cmp    BYTE PTR [rip+0x6e52],0x0        # f229 <error_print_progname@@Base+0x141>
    83d7:	0f 84 8d 08 00 00    	je     8c6a <error_at_line@@Base+0x7d01>
    83dd:	0f 8e b1 08 00 00    	jle    8c94 <error_at_line@@Base+0x7d2b>
    83e3:	8b b5 74 ff fb ff    	mov    esi,DWORD PTR [rbp-0x4008c]
    83e9:	48 8d bd a0 ff fb ff 	lea    rdi,[rbp-0x40060]
    83f0:	e8 fb f2 ff ff       	call   76f0 <error_at_line@@Base+0x6787>
    83f5:	48 8b 85 a8 ff fb ff 	mov    rax,QWORD PTR [rbp-0x40058]
    83fc:	44 8b a5 a0 ff fb ff 	mov    r12d,DWORD PTR [rbp-0x40060]
    8403:	48 89 85 48 ff fb ff 	mov    QWORD PTR [rbp-0x400b8],rax
    840a:	48 8b 85 b0 ff fb ff 	mov    rax,QWORD PTR [rbp-0x40050]
    8411:	45 85 e4             	test   r12d,r12d
    8414:	41 0f 94 c5          	sete   r13b
    8418:	48 89 85 60 ff fb ff 	mov    QWORD PTR [rbp-0x400a0],rax
    841f:	48 c7 85 58 ff fb ff 	mov    QWORD PTR [rbp-0x400a8],0x0
    8426:	00 00 00 00 
    842a:	45 31 ff             	xor    r15d,r15d
    842d:	31 db                	xor    ebx,ebx
    842f:	45 31 f6             	xor    r14d,r14d
    8432:	e9 b5 02 00 00       	jmp    86ec <error_at_line@@Base+0x7783>
    8437:	84 d2                	test   dl,dl
    8439:	0f 85 89 fd ff ff    	jne    81c8 <error_at_line@@Base+0x725f>
    843f:	80 3d 42 70 00 00 00 	cmp    BYTE PTR [rip+0x7042],0x0        # f488 <error_print_progname@@Base+0x3a0>
    8446:	0f 85 7c fd ff ff    	jne    81c8 <error_at_line@@Base+0x725f>
    844c:	80 3d 3d 70 00 00 00 	cmp    BYTE PTR [rip+0x703d],0x0        # f490 <error_print_progname@@Base+0x3a8>
    8453:	0f 85 c7 0b 00 00    	jne    9020 <error_at_line@@Base+0x80b7>
    8459:	44 8b 23             	mov    r12d,DWORD PTR [rbx]
    845c:	45 85 e4             	test   r12d,r12d
    845f:	7e 14                	jle    8475 <error_at_line@@Base+0x750c>
    8461:	8b bd 74 ff fb ff    	mov    edi,DWORD PTR [rbp-0x4008c]
    8467:	48 8d 73 08          	lea    rsi,[rbx+0x8]
    846b:	e8 50 87 ff ff       	call   bc0 <fstat@plt>
    8470:	89 03                	mov    DWORD PTR [rbx],eax
    8472:	41 89 c4             	mov    r12d,eax
    8475:	45 85 e4             	test   r12d,r12d
    8478:	0f 85 81 00 00 00    	jne    84ff <error_at_line@@Base+0x7596>
    847e:	8b 43 20             	mov    eax,DWORD PTR [rbx+0x20]
    8481:	25 00 d0 00 00       	and    eax,0xd000
    8486:	3d 00 80 00 00       	cmp    eax,0x8000
    848b:	75 72                	jne    84ff <error_at_line@@Base+0x7596>
    848d:	4c 8b 6b 38          	mov    r13,QWORD PTR [rbx+0x38]
    8491:	4d 85 ed             	test   r13,r13
    8494:	78 69                	js     84ff <error_at_line@@Base+0x7596>
    8496:	8b bd 74 ff fb ff    	mov    edi,DWORD PTR [rbp-0x4008c]
    849c:	ba 01 00 00 00       	mov    edx,0x1
    84a1:	31 f6                	xor    esi,esi
    84a3:	e8 a8 84 ff ff       	call   950 <lseek@plt>
    84a8:	49 89 c6             	mov    r14,rax
    84ab:	48 85 c0             	test   rax,rax
    84ae:	78 4f                	js     84ff <error_at_line@@Base+0x7596>
    84b0:	4c 89 e8             	mov    rax,r13
    84b3:	48 99                	cqo
    84b5:	48 f7 3d c4 6f 00 00 	idiv   QWORD PTR [rip+0x6fc4]        # f480 <error_print_progname@@Base+0x398>
    84bc:	48 89 95 60 ff fb ff 	mov    QWORD PTR [rbp-0x400a0],rdx
    84c3:	48 85 d2             	test   rdx,rdx
    84c6:	0f 84 ee 0a 00 00    	je     8fba <error_at_line@@Base+0x8051>
    84cc:	4d 39 f5             	cmp    r13,r14
    84cf:	7c 2e                	jl     84ff <error_at_line@@Base+0x7596>
    84d1:	4d 29 f5             	sub    r13,r14
    84d4:	4c 89 ad 60 ff fb ff 	mov    QWORD PTR [rbp-0x400a0],r13
    84db:	74 2d                	je     850a <error_at_line@@Base+0x75a1>
    84dd:	8b bd 74 ff fb ff    	mov    edi,DWORD PTR [rbp-0x4008c]
    84e3:	4c 89 ee             	mov    rsi,r13
    84e6:	ba 01 00 00 00       	mov    edx,0x1
    84eb:	41 bd 01 00 00 00    	mov    r13d,0x1
    84f1:	e8 5a 84 ff ff       	call   950 <lseek@plt>
    84f6:	48 85 c0             	test   rax,rax
    84f9:	0f 89 42 0a 00 00    	jns    8f41 <error_at_line@@Base+0x7fd8>
    84ff:	48 c7 85 60 ff fb ff 	mov    QWORD PTR [rbp-0x400a0],0x0
    8506:	00 00 00 00 
    850a:	44 8b ad 74 ff fb ff 	mov    r13d,DWORD PTR [rbp-0x4008c]
    8511:	b9 02 00 00 00       	mov    ecx,0x2
    8516:	31 d2                	xor    edx,edx
    8518:	31 f6                	xor    esi,esi
    851a:	44 89 ef             	mov    edi,r13d
    851d:	e8 8e 84 ff ff       	call   9b0 <posix_fadvise@plt>
    8522:	48 8b 9d 60 ff fb ff 	mov    rbx,QWORD PTR [rbp-0x400a0]
    8529:	eb 0e                	jmp    8539 <error_at_line@@Base+0x75d0>
    852b:	0f 1f 44 00 00       	nop    DWORD PTR [rax+rax*1+0x0]
    8530:	0f 88 f5 09 00 00    	js     8f2b <error_at_line@@Base+0x7fc2>
    8536:	48 01 c3             	add    rbx,rax
    8539:	ba 00 00 04 00       	mov    edx,0x40000
    853e:	48 8d b5 c0 ff fb ff 	lea    rsi,[rbp-0x40040]
    8545:	44 89 ef             	mov    edi,r13d
    8548:	e8 83 84 ff ff       	call   9d0 <read@plt>
    854d:	48 85 c0             	test   rax,rax
    8550:	75 de                	jne    8530 <error_at_line@@Base+0x75c7>
    8552:	48 89 9d 60 ff fb ff 	mov    QWORD PTR [rbp-0x400a0],rbx
    8559:	49 89 c6             	mov    r14,rax
    855c:	31 db                	xor    ebx,ebx
    855e:	45 31 ff             	xor    r15d,r15d
    8561:	48 c7 85 58 ff fb ff 	mov    QWORD PTR [rbp-0x400a8],0x0
    8568:	00 00 00 00 
    856c:	41 bd 01 00 00 00    	mov    r13d,0x1
    8572:	45 31 e4             	xor    r12d,r12d
    8575:	48 c7 85 48 ff fb ff 	mov    QWORD PTR [rbp-0x400b8],0x0
    857c:	00 00 00 00 
    8580:	e9 67 01 00 00       	jmp    86ec <error_at_line@@Base+0x7783>
    8585:	8b bd 74 ff fb ff    	mov    edi,DWORD PTR [rbp-0x4008c]
    858b:	31 d2                	xor    edx,edx
    858d:	31 f6                	xor    esi,esi
    858f:	b9 02 00 00 00       	mov    ecx,0x2
    8594:	e8 17 84 ff ff       	call   9b0 <posix_fadvise@plt>
    8599:	e8 32 83 ff ff       	call   8d0 <__ctype_get_mb_cur_max@plt>
    859e:	48 83 f8 01          	cmp    rax,0x1
    85a2:	0f 86 46 fc ff ff    	jbe    81ee <error_at_line@@Base+0x7285>
    85a8:	48 8d 85 c0 ff fb ff 	lea    rax,[rbp-0x40040]
    85af:	45 31 c9             	xor    r9d,r9d
    85b2:	45 31 e4             	xor    r12d,r12d
    85b5:	45 31 ed             	xor    r13d,r13d
    85b8:	48 c7 85 b8 ff fb ff 	mov    QWORD PTR [rbp-0x40048],0x0
    85bf:	00 00 00 00 
    85c3:	c6 85 90 ff fb ff 00 	mov    BYTE PTR [rbp-0x40070],0x0
    85ca:	48 c7 85 68 ff fb ff 	mov    QWORD PTR [rbp-0x40098],0x0
    85d1:	00 00 00 00 
    85d5:	48 c7 85 60 ff fb ff 	mov    QWORD PTR [rbp-0x400a0],0x0
    85dc:	00 00 00 00 
    85e0:	48 c7 85 58 ff fb ff 	mov    QWORD PTR [rbp-0x400a8],0x0
    85e7:	00 00 00 00 
    85eb:	48 c7 85 48 ff fb ff 	mov    QWORD PTR [rbp-0x400b8],0x0
    85f2:	00 00 00 00 
    85f6:	48 89 85 50 ff fb ff 	mov    QWORD PTR [rbp-0x400b0],rax
    85fd:	48 c7 85 80 ff fb ff 	mov    QWORD PTR [rbp-0x40080],0x0
    8604:	00 00 00 00 
    8608:	44 88 bd 3b ff fb ff 	mov    BYTE PTR [rbp-0x400c5],r15b
    860f:	90                   	nop
    8610:	b9 01 00 04 00       	mov    ecx,0x40001
    8615:	8b bd 74 ff fb ff    	mov    edi,DWORD PTR [rbp-0x4008c]
    861b:	48 8b 85 50 ff fb ff 	mov    rax,QWORD PTR [rbp-0x400b0]
    8622:	ba 00 00 04 00       	mov    edx,0x40000
    8627:	49 39 c9             	cmp    r9,rcx
    862a:	4c 89 8d 78 ff fb ff 	mov    QWORD PTR [rbp-0x40088],r9
    8631:	49 0f 43 c9          	cmovae rcx,r9
    8635:	4a 8d 34 08          	lea    rsi,[rax+r9*1]
    8639:	4c 29 ca             	sub    rdx,r9
    863c:	4c 29 c9             	sub    rcx,r9
    863f:	e8 fc 81 ff ff       	call   840 <__read_chk@plt>
    8644:	4c 8b 8d 78 ff fb ff 	mov    r9,QWORD PTR [rbp-0x40088]
    864b:	48 85 c0             	test   rax,rax
    864e:	0f 85 ec 04 00 00    	jne    8b40 <error_at_line@@Base+0x7bd7>
    8654:	4d 85 c9             	test   r9,r9
    8657:	0f 84 ae 08 00 00    	je     8f0b <error_at_line@@Base+0x7fa2>
    865d:	4c 8b bd 50 ff fb ff 	mov    r15,QWORD PTR [rbp-0x400b0]
    8664:	48 01 85 60 ff fb ff 	add    QWORD PTR [rbp-0x400a0],rax
    866b:	4e 8d 14 08          	lea    r10,[rax+r9*1]
    866f:	48 85 c0             	test   rax,rax
    8672:	0f 95 85 73 ff fb ff 	setne  BYTE PTR [rbp-0x4008d]
    8679:	4f 8d 34 17          	lea    r14,[r15+r10*1]
    867d:	45 84 e4             	test   r12b,r12b
    8680:	0f 85 f7 01 00 00    	jne    887d <error_at_line@@Base+0x7914>
    8686:	66 2e 0f 1f 84 00 00 	cs nop WORD PTR [rax+rax*1+0x0]
    868d:	00 00 00 
    8690:	41 0f b6 07          	movzx  eax,BYTE PTR [r15]
    8694:	84 c0                	test   al,al
    8696:	0f 88 44 03 00 00    	js     89e0 <error_at_line@@Base+0x7a77>
    869c:	8d 50 f7             	lea    edx,[rax-0x9]
    869f:	80 fa 17             	cmp    dl,0x17
    86a2:	0f 87 68 01 00 00    	ja     8810 <error_at_line@@Base+0x78a7>
    86a8:	48 8d 35 35 3f 00 00 	lea    rsi,[rip+0x3f35]        # c5e4 <error_at_line@@Base+0xb67b>
    86af:	0f b6 d2             	movzx  edx,dl
    86b2:	48 63 14 96          	movsxd rdx,DWORD PTR [rsi+rdx*4]
    86b6:	48 01 f2             	add    rdx,rsi
    86b9:	3e ff e2             	notrack jmp rdx
    86bc:	4c 89 bd 58 ff fb ff 	mov    QWORD PTR [rbp-0x400a8],r15
    86c3:	48 8b 9d 80 ff fb ff 	mov    rbx,QWORD PTR [rbp-0x40080]
    86ca:	45 31 e4             	xor    r12d,r12d
    86cd:	44 0f b6 bd 78 ff fb 	movzx  r15d,BYTE PTR [rbp-0x40088]
    86d4:	ff 
    86d5:	4c 89 ad 48 ff fb ff 	mov    QWORD PTR [rbp-0x400b8],r13
    86dc:	41 bd 01 00 00 00    	mov    r13d,0x1
    86e2:	4c 39 f3             	cmp    rbx,r14
    86e5:	49 0f 4c de          	cmovl  rbx,r14
    86e9:	45 31 f6             	xor    r14d,r14d
    86ec:	48 8b 85 60 ff fb ff 	mov    rax,QWORD PTR [rbp-0x400a0]
    86f3:	44 3a 3d 90 6d 00 00 	cmp    r15b,BYTE PTR [rip+0x6d90]        # f48a <error_print_progname@@Base+0x3a2>
    86fa:	4c 0f 42 f0          	cmovb  r14,rax
    86fe:	83 3d 73 6b 00 00 02 	cmp    DWORD PTR [rip+0x6b73],0x2        # f278 <error_print_progname@@Base+0x190>
    8705:	74 23                	je     872a <error_at_line@@Base+0x77c1>
    8707:	4c 8b 8d 30 ff fb ff 	mov    r9,QWORD PTR [rbp-0x400d0]
    870e:	49 89 d8             	mov    r8,rbx
    8711:	48 89 c1             	mov    rcx,rax
    8714:	4c 89 f2             	mov    rdx,r14
    8717:	48 8b b5 58 ff fb ff 	mov    rsi,QWORD PTR [rbp-0x400a8]
    871e:	48 8b bd 48 ff fb ff 	mov    rdi,QWORD PTR [rbp-0x400b8]
    8725:	e8 a6 f5 ff ff       	call   7cd0 <error_at_line@@Base+0x6d67>
    872a:	48 8b 05 3f 6b 00 00 	mov    rax,QWORD PTR [rip+0x6b3f]        # f270 <error_print_progname@@Base+0x188>
    8731:	31 c9                	xor    ecx,ecx
    8733:	48 ba 00 00 00 00 00 	movabs rdx,0x8000000000000000
    873a:	00 00 80 
    873d:	48 01 d0             	add    rax,rdx
    8740:	48 03 85 48 ff fb ff 	add    rax,QWORD PTR [rbp-0x400b8]
    8747:	0f 90 c1             	seto   cl
    874a:	48 01 d0             	add    rax,rdx
    874d:	08 0d 15 6b 00 00    	or     BYTE PTR [rip+0x6b15],cl        # f268 <error_print_progname@@Base+0x180>
    8753:	31 c9                	xor    ecx,ecx
    8755:	48 89 05 14 6b 00 00 	mov    QWORD PTR [rip+0x6b14],rax        # f270 <error_print_progname@@Base+0x188>
    875c:	48 8b 05 fd 6a 00 00 	mov    rax,QWORD PTR [rip+0x6afd]        # f260 <error_print_progname@@Base+0x178>
    8763:	48 01 d0             	add    rax,rdx
    8766:	48 03 85 58 ff fb ff 	add    rax,QWORD PTR [rbp-0x400a8]
    876d:	0f 90 c1             	seto   cl
    8770:	48 01 d0             	add    rax,rdx
    8773:	08 0d df 6a 00 00    	or     BYTE PTR [rip+0x6adf],cl        # f258 <error_print_progname@@Base+0x170>
    8779:	31 c9                	xor    ecx,ecx
    877b:	48 89 05 de 6a 00 00 	mov    QWORD PTR [rip+0x6ade],rax        # f260 <error_print_progname@@Base+0x178>
    8782:	48 8b 05 c7 6a 00 00 	mov    rax,QWORD PTR [rip+0x6ac7]        # f250 <error_print_progname@@Base+0x168>
    8789:	48 01 d0             	add    rax,rdx
    878c:	49 01 c6             	add    r14,rax
    878f:	49 8d 04 16          	lea    rax,[r14+rdx*1]
    8793:	0f 90 c1             	seto   cl
    8796:	08 0d ac 6a 00 00    	or     BYTE PTR [rip+0x6aac],cl        # f248 <error_print_progname@@Base+0x160>
    879c:	31 c9                	xor    ecx,ecx
    879e:	48 89 05 ab 6a 00 00 	mov    QWORD PTR [rip+0x6aab],rax        # f250 <error_print_progname@@Base+0x168>
    87a5:	48 8b 05 94 6a 00 00 	mov    rax,QWORD PTR [rip+0x6a94]        # f240 <error_print_progname@@Base+0x158>
    87ac:	48 01 d0             	add    rax,rdx
    87af:	48 03 85 60 ff fb ff 	add    rax,QWORD PTR [rbp-0x400a0]
    87b6:	0f 90 c1             	seto   cl
    87b9:	48 01 d0             	add    rax,rdx
    87bc:	08 0d 76 6a 00 00    	or     BYTE PTR [rip+0x6a76],cl        # f238 <error_print_progname@@Base+0x150>
    87c2:	48 39 1d 67 6a 00 00 	cmp    QWORD PTR [rip+0x6a67],rbx        # f230 <error_print_progname@@Base+0x148>
    87c9:	48 89 05 70 6a 00 00 	mov    QWORD PTR [rip+0x6a70],rax        # f240 <error_print_progname@@Base+0x158>
    87d0:	7d 07                	jge    87d9 <error_at_line@@Base+0x7870>
    87d2:	48 89 1d 57 6a 00 00 	mov    QWORD PTR [rip+0x6a57],rbx        # f230 <error_print_progname@@Base+0x148>
    87d9:	45 85 e4             	test   r12d,r12d
    87dc:	0f 85 57 08 00 00    	jne    9039 <error_at_line@@Base+0x80d0>
    87e2:	48 8b 45 c8          	mov    rax,QWORD PTR [rbp-0x38]
    87e6:	64 48 2b 04 25 28 00 	sub    rax,QWORD PTR fs:0x28
    87ed:	00 00 
    87ef:	0f 85 6b 08 00 00    	jne    9060 <error_at_line@@Base+0x80f7>
    87f5:	48 81 c4 b8 00 04 00 	add    rsp,0x400b8
    87fc:	44 89 e8             	mov    eax,r13d
    87ff:	5b                   	pop    rbx
    8800:	41 5c                	pop    r12
    8802:	41 5d                	pop    r13
    8804:	41 5e                	pop    r14
    8806:	41 5f                	pop    r15
    8808:	5d                   	pop    rbp
    8809:	c3                   	ret
    880a:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]
    8810:	0f be f8             	movsx  edi,al
    8813:	ba 01 00 00 00       	mov    edx,0x1
    8818:	45 31 e4             	xor    r12d,r12d
    881b:	89 f8                	mov    eax,edi
    881d:	48 8d 35 5c 6b 00 00 	lea    rsi,[rip+0x6b5c]        # f380 <error_print_progname@@Base+0x298>
    8824:	0f b6 9d 90 ff fb ff 	movzx  ebx,BYTE PTR [rbp-0x40070]
    882b:	0f b6 0c 06          	movzx  ecx,BYTE PTR [rsi+rax*1]
    882f:	49 01 cd             	add    r13,rcx
    8832:	48 8d 0d 47 6a 00 00 	lea    rcx,[rip+0x6a47]        # f280 <error_print_progname@@Base+0x198>
    8839:	0f b6 0c 01          	movzx  ecx,BYTE PTR [rcx+rax*1]
    883d:	09 cb                	or     ebx,ecx
    883f:	83 f1 01             	xor    ecx,0x1
    8842:	83 f3 01             	xor    ebx,0x1
    8845:	88 8d 90 ff fb ff    	mov    BYTE PTR [rbp-0x40070],cl
    884b:	0f b6 c3             	movzx  eax,bl
    884e:	48 01 85 58 ff fb ff 	add    QWORD PTR [rbp-0x400a8],rax
    8855:	66 66 2e 0f 1f 84 00 	data16 cs nop WORD PTR [rax+rax*1+0x0]
    885c:	00 00 00 00 
    8860:	49 01 d7             	add    r15,rdx
    8863:	48 83 85 80 ff fb ff 	add    QWORD PTR [rbp-0x40080],0x1
    886a:	01 
    886b:	4d 39 f7             	cmp    r15,r14
    886e:	0f 83 9c fd ff ff    	jae    8610 <error_at_line@@Base+0x76a7>
    8874:	45 84 e4             	test   r12b,r12b
    8877:	0f 84 13 fe ff ff    	je     8690 <error_at_line@@Base+0x7727>
    887d:	4b 8d 34 0f          	lea    rsi,[r15+r9*1]
    8881:	4c 89 f3             	mov    rbx,r14
    8884:	48 8d bd a0 ff fb ff 	lea    rdi,[rbp-0x40060]
    888b:	48 29 f3             	sub    rbx,rsi
    888e:	48 8d 8d b8 ff fb ff 	lea    rcx,[rbp-0x40048]
    8895:	48 89 da             	mov    rdx,rbx
    8898:	e8 33 cd ff ff       	call   55d0 <error_at_line@@Base+0x4667>
    889d:	48 39 c3             	cmp    rbx,rax
    88a0:	0f 83 4a 01 00 00    	jae    89f0 <error_at_line@@Base+0x7a87>
    88a6:	48 83 f8 fe          	cmp    rax,0xfffffffffffffffe
    88aa:	75 21                	jne    88cd <error_at_line@@Base+0x7964>
    88ac:	4d 89 f1             	mov    r9,r14
    88af:	4d 29 f9             	sub    r9,r15
    88b2:	49 81 f9 ff ff 03 00 	cmp    r9,0x3ffff
    88b9:	41 0f 9e c2          	setle  r10b
    88bd:	44 22 95 73 ff fb ff 	and    r10b,BYTE PTR [rbp-0x4008d]
    88c4:	45 89 d4             	mov    r12d,r10d
    88c7:	0f 85 43 02 00 00    	jne    8b10 <error_at_line@@Base+0x7ba7>
    88cd:	0f b6 9d 90 ff fb ff 	movzx  ebx,BYTE PTR [rbp-0x40070]
    88d4:	49 83 c7 01          	add    r15,0x1
    88d8:	45 31 c9             	xor    r9d,r9d
    88db:	48 c7 85 b8 ff fb ff 	mov    QWORD PTR [rbp-0x40048],0x0
    88e2:	00 00 00 00 
    88e6:	c6 85 90 ff fb ff 01 	mov    BYTE PTR [rbp-0x40070],0x1
    88ed:	83 f3 01             	xor    ebx,0x1
    88f0:	0f b6 db             	movzx  ebx,bl
    88f3:	48 01 9d 58 ff fb ff 	add    QWORD PTR [rbp-0x400a8],rbx
    88fa:	4d 39 f7             	cmp    r15,r14
    88fd:	0f 82 8d fd ff ff    	jb     8690 <error_at_line@@Base+0x7727>
    8903:	45 31 e4             	xor    r12d,r12d
    8906:	e9 05 fd ff ff       	jmp    8610 <error_at_line@@Base+0x76a7>
    890b:	0f 1f 44 00 00       	nop    DWORD PTR [rax+rax*1+0x0]
    8910:	ba 01 00 00 00       	mov    edx,0x1
    8915:	45 31 e4             	xor    r12d,r12d
    8918:	48 8b 85 68 ff fb ff 	mov    rax,QWORD PTR [rbp-0x40098]
    891f:	c6 85 90 ff fb ff 00 	mov    BYTE PTR [rbp-0x40070],0x0
    8926:	4c 39 e8             	cmp    rax,r13
    8929:	4c 0f 4d e8          	cmovge r13,rax
    892d:	4c 89 ad 68 ff fb ff 	mov    QWORD PTR [rbp-0x40098],r13
    8934:	45 31 ed             	xor    r13d,r13d
    8937:	e9 24 ff ff ff       	jmp    8860 <error_at_line@@Base+0x78f7>
    893c:	0f 1f 40 00          	nop    DWORD PTR [rax+0x0]
    8940:	ba 01 00 00 00       	mov    edx,0x1
    8945:	45 31 e4             	xor    r12d,r12d
    8948:	48 83 85 48 ff fb ff 	add    QWORD PTR [rbp-0x400b8],0x1
    894f:	01 
    8950:	eb c6                	jmp    8918 <error_at_line@@Base+0x79af>
    8952:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]
    8958:	ba 01 00 00 00       	mov    edx,0x1
    895d:	45 31 e4             	xor    r12d,r12d
    8960:	4c 89 e8             	mov    rax,r13
    8963:	c6 85 90 ff fb ff 00 	mov    BYTE PTR [rbp-0x40070],0x0
    896a:	48 c1 f8 3f          	sar    rax,0x3f
    896e:	48 c1 e8 3d          	shr    rax,0x3d
    8972:	49 8d 4c 05 00       	lea    rcx,[r13+rax*1+0x0]
    8977:	83 e1 07             	and    ecx,0x7
    897a:	48 29 c8             	sub    rax,rcx
    897d:	4d 8d 6c 05 08       	lea    r13,[r13+rax*1+0x8]
    8982:	e9 d9 fe ff ff       	jmp    8860 <error_at_line@@Base+0x78f7>
    8987:	66 0f 1f 84 00 00 00 	nop    WORD PTR [rax+rax*1+0x0]
    898e:	00 00 
    8990:	ba 01 00 00 00       	mov    edx,0x1
    8995:	45 31 e4             	xor    r12d,r12d
    8998:	c6 85 90 ff fb ff 00 	mov    BYTE PTR [rbp-0x40070],0x0
    899f:	49 83 c5 01          	add    r13,0x1
    89a3:	e9 b8 fe ff ff       	jmp    8860 <error_at_line@@Base+0x78f7>
    89a8:	0f 1f 84 00 00 00 00 	nop    DWORD PTR [rax+rax*1+0x0]
    89af:	00 
    89b0:	49 83 c7 01          	add    r15,0x1
    89b4:	48 83 85 80 ff fb ff 	add    QWORD PTR [rbp-0x40080],0x1
    89bb:	01 
    89bc:	c6 85 90 ff fb ff 00 	mov    BYTE PTR [rbp-0x40070],0x0
    89c3:	4d 39 f7             	cmp    r15,r14
    89c6:	0f 83 37 ff ff ff    	jae    8903 <error_at_line@@Base+0x799a>
    89cc:	41 0f b6 07          	movzx  eax,BYTE PTR [r15]
    89d0:	84 c0                	test   al,al
    89d2:	0f 89 c4 fc ff ff    	jns    869c <error_at_line@@Base+0x7733>
    89d8:	0f 1f 84 00 00 00 00 	nop    DWORD PTR [rax+rax*1+0x0]
    89df:	00 
    89e0:	45 31 e4             	xor    r12d,r12d
    89e3:	e9 95 fe ff ff       	jmp    887d <error_at_line@@Base+0x7914>
    89e8:	0f 1f 84 00 00 00 00 	nop    DWORD PTR [rax+rax*1+0x0]
    89ef:	00 
    89f0:	48 83 f8 01          	cmp    rax,0x1
    89f4:	48 8d bd b8 ff fb ff 	lea    rdi,[rbp-0x40048]
    89fb:	48 83 d0 00          	adc    rax,0x0
    89ff:	48 89 85 78 ff fb ff 	mov    QWORD PTR [rbp-0x40088],rax
    8a06:	e8 95 81 ff ff       	call   ba0 <mbsinit@plt>
    8a0b:	8b bd a0 ff fb ff    	mov    edi,DWORD PTR [rbp-0x40060]
    8a11:	48 8b 95 78 ff fb ff 	mov    rdx,QWORD PTR [rbp-0x40088]
    8a18:	85 c0                	test   eax,eax
    8a1a:	8d 47 f7             	lea    eax,[rdi-0x9]
    8a1d:	0f 94 c1             	sete   cl
    8a20:	83 f8 17             	cmp    eax,0x17
    8a23:	77 1b                	ja     8a40 <error_at_line@@Base+0x7ad7>
    8a25:	48 8d 35 18 3c 00 00 	lea    rsi,[rip+0x3c18]        # c644 <error_at_line@@Base+0xb6db>
    8a2c:	48 63 04 86          	movsxd rax,DWORD PTR [rsi+rax*4]
    8a30:	48 01 f0             	add    rax,rsi
    8a33:	3e ff e0             	notrack jmp rax
    8a36:	66 2e 0f 1f 84 00 00 	cs nop WORD PTR [rax+rax*1+0x0]
    8a3d:	00 00 00 
    8a40:	45 89 e2             	mov    r10d,r12d
    8a43:	41 83 f2 01          	xor    r10d,0x1
    8a47:	45 0f b6 d2          	movzx  r10d,r10b
    8a4b:	49 39 d2             	cmp    r10,rdx
    8a4e:	0f 84 11 06 00 00    	je     9065 <error_at_line@@Base+0x80fc>
    8a54:	80 3d 2d 6a 00 00 00 	cmp    BYTE PTR [rip+0x6a2d],0x0        # f488 <error_print_progname@@Base+0x3a0>
    8a5b:	0f 85 1f 01 00 00    	jne    8b80 <error_at_line@@Base+0x7c17>
    8a61:	48 89 95 40 ff fb ff 	mov    QWORD PTR [rbp-0x400c0],rdx
    8a68:	88 8d 78 ff fb ff    	mov    BYTE PTR [rbp-0x40088],cl
    8a6e:	89 bd 3c ff fb ff    	mov    DWORD PTR [rbp-0x400c4],edi
    8a74:	e8 77 80 ff ff       	call   af0 <iswspace@plt>
    8a79:	0f b6 8d 78 ff fb ff 	movzx  ecx,BYTE PTR [rbp-0x40088]
    8a80:	48 8b 95 40 ff fb ff 	mov    rdx,QWORD PTR [rbp-0x400c0]
    8a87:	85 c0                	test   eax,eax
    8a89:	75 4d                	jne    8ad8 <error_at_line@@Base+0x7b6f>
    8a8b:	0f b6 05 99 67 00 00 	movzx  eax,BYTE PTR [rip+0x6799]        # f22b <error_print_progname@@Base+0x143>
    8a92:	8b bd 3c ff fb ff    	mov    edi,DWORD PTR [rbp-0x400c4]
    8a98:	84 c0                	test   al,al
    8a9a:	0f 84 18 01 00 00    	je     8bb8 <error_at_line@@Base+0x7c4f>
    8aa0:	0f b6 9d 90 ff fb ff 	movzx  ebx,BYTE PTR [rbp-0x40070]
    8aa7:	41 89 cc             	mov    r12d,ecx
    8aaa:	45 31 c9             	xor    r9d,r9d
    8aad:	88 85 90 ff fb ff    	mov    BYTE PTR [rbp-0x40070],al
    8ab3:	83 f3 01             	xor    ebx,0x1
    8ab6:	0f b6 f3             	movzx  esi,bl
    8ab9:	48 01 b5 58 ff fb ff 	add    QWORD PTR [rbp-0x400a8],rsi
    8ac0:	e9 9b fd ff ff       	jmp    8860 <error_at_line@@Base+0x78f7>
    8ac5:	0f 1f 00             	nop    DWORD PTR [rax]
    8ac8:	41 89 cc             	mov    r12d,ecx
    8acb:	45 31 c9             	xor    r9d,r9d
    8ace:	e9 45 fe ff ff       	jmp    8918 <error_at_line@@Base+0x79af>
    8ad3:	0f 1f 44 00 00       	nop    DWORD PTR [rax+rax*1+0x0]
    8ad8:	c6 85 90 ff fb ff 00 	mov    BYTE PTR [rbp-0x40070],0x0
    8adf:	41 89 cc             	mov    r12d,ecx
    8ae2:	45 31 c9             	xor    r9d,r9d
    8ae5:	e9 76 fd ff ff       	jmp    8860 <error_at_line@@Base+0x78f7>
    8aea:	41 89 cc             	mov    r12d,ecx
    8aed:	45 31 c9             	xor    r9d,r9d
    8af0:	e9 a3 fe ff ff       	jmp    8998 <error_at_line@@Base+0x7a2f>
    8af5:	41 89 cc             	mov    r12d,ecx
    8af8:	45 31 c9             	xor    r9d,r9d
    8afb:	e9 48 fe ff ff       	jmp    8948 <error_at_line@@Base+0x79df>
    8b00:	41 89 cc             	mov    r12d,ecx
    8b03:	45 31 c9             	xor    r9d,r9d
    8b06:	e9 55 fe ff ff       	jmp    8960 <error_at_line@@Base+0x79f7>
    8b0b:	0f 1f 44 00 00       	nop    DWORD PTR [rax+rax*1+0x0]
    8b10:	48 8b bd 50 ff fb ff 	mov    rdi,QWORD PTR [rbp-0x400b0]
    8b17:	4c 89 ca             	mov    rdx,r9
    8b1a:	b9 01 00 04 00       	mov    ecx,0x40001
    8b1f:	4c 89 fe             	mov    rsi,r15
    8b22:	4c 89 8d 78 ff fb ff 	mov    QWORD PTR [rbp-0x40088],r9
    8b29:	e8 02 7f ff ff       	call   a30 <__memmove_chk@plt>
    8b2e:	4c 8b 8d 78 ff fb ff 	mov    r9,QWORD PTR [rbp-0x40088]
    8b35:	e9 d6 fa ff ff       	jmp    8610 <error_at_line@@Base+0x76a7>
    8b3a:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]
    8b40:	0f 89 17 fb ff ff    	jns    865d <error_at_line@@Base+0x76f4>
    8b46:	e8 b5 7c ff ff       	call   800 <__errno_location@plt>
    8b4b:	4c 8b b5 80 ff fb ff 	mov    r14,QWORD PTR [rbp-0x40080]
    8b52:	44 0f b6 bd 3b ff fb 	movzx  r15d,BYTE PTR [rbp-0x400c5]
    8b59:	ff 
    8b5a:	4c 89 eb             	mov    rbx,r13
    8b5d:	44 8b 20             	mov    r12d,DWORD PTR [rax]
    8b60:	45 85 e4             	test   r12d,r12d
    8b63:	41 0f 94 c5          	sete   r13b
    8b67:	48 8b 85 68 ff fb ff 	mov    rax,QWORD PTR [rbp-0x40098]
    8b6e:	48 39 d8             	cmp    rax,rbx
    8b71:	48 0f 4d d8          	cmovge rbx,rax
    8b75:	e9 72 fb ff ff       	jmp    86ec <error_at_line@@Base+0x7783>
    8b7a:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]
    8b80:	48 89 95 40 ff fb ff 	mov    QWORD PTR [rbp-0x400c0],rdx
    8b87:	88 8d 78 ff fb ff    	mov    BYTE PTR [rbp-0x40088],cl
    8b8d:	e8 ee 7e ff ff       	call   a80 <wcwidth@plt>
    8b92:	8b bd a0 ff fb ff    	mov    edi,DWORD PTR [rbp-0x40060]
    8b98:	48 8b 95 40 ff fb ff 	mov    rdx,QWORD PTR [rbp-0x400c0]
    8b9f:	89 c6                	mov    esi,eax
    8ba1:	89 c0                	mov    eax,eax
    8ba3:	0f b6 8d 78 ff fb ff 	movzx  ecx,BYTE PTR [rbp-0x40088]
    8baa:	4c 01 e8             	add    rax,r13
    8bad:	85 f6                	test   esi,esi
    8baf:	4c 0f 4f e8          	cmovg  r13,rax
    8bb3:	e9 a9 fe ff ff       	jmp    8a61 <error_at_line@@Base+0x7af8>
    8bb8:	81 ff a0 00 00 00    	cmp    edi,0xa0
    8bbe:	74 79                	je     8c39 <error_at_line@@Base+0x7cd0>
    8bc0:	81 ff 07 20 00 00    	cmp    edi,0x2007
    8bc6:	74 71                	je     8c39 <error_at_line@@Base+0x7cd0>
    8bc8:	81 ff 2f 20 00 00    	cmp    edi,0x202f
    8bce:	0f b6 9d 90 ff fb ff 	movzx  ebx,BYTE PTR [rbp-0x40070]
    8bd5:	41 89 cc             	mov    r12d,ecx
    8bd8:	40 0f 94 c6          	sete   sil
    8bdc:	81 ff 60 20 00 00    	cmp    edi,0x2060
    8be2:	0f 94 c0             	sete   al
    8be5:	45 31 c9             	xor    r9d,r9d
    8be8:	09 c6                	or     esi,eax
    8bea:	09 f3                	or     ebx,esi
    8bec:	83 f6 01             	xor    esi,0x1
    8bef:	83 f3 01             	xor    ebx,0x1
    8bf2:	40 88 b5 90 ff fb ff 	mov    BYTE PTR [rbp-0x40070],sil
    8bf9:	0f b6 c3             	movzx  eax,bl
    8bfc:	48 01 85 58 ff fb ff 	add    QWORD PTR [rbp-0x400a8],rax
    8c03:	e9 58 fc ff ff       	jmp    8860 <error_at_line@@Base+0x78f7>
    8c08:	4c 89 ad 48 ff fb ff 	mov    QWORD PTR [rbp-0x400b8],r13
    8c0f:	48 8b 9d 80 ff fb ff 	mov    rbx,QWORD PTR [rbp-0x40080]
    8c16:	4c 89 bd 58 ff fb ff 	mov    QWORD PTR [rbp-0x400a8],r15
    8c1d:	44 0f b6 bd 78 ff fb 	movzx  r15d,BYTE PTR [rbp-0x40088]
    8c24:	ff 
    8c25:	e8 d6 7b ff ff       	call   800 <__errno_location@plt>
    8c2a:	44 8b 20             	mov    r12d,DWORD PTR [rax]
    8c2d:	45 85 e4             	test   r12d,r12d
    8c30:	41 0f 94 c5          	sete   r13b
    8c34:	e9 a9 fa ff ff       	jmp    86e2 <error_at_line@@Base+0x7779>
    8c39:	c6 85 90 ff fb ff 00 	mov    BYTE PTR [rbp-0x40070],0x0
    8c40:	41 89 cc             	mov    r12d,ecx
    8c43:	45 31 c9             	xor    r9d,r9d
    8c46:	e9 15 fc ff ff       	jmp    8860 <error_at_line@@Base+0x78f7>
    8c4b:	ba 05 00 00 00       	mov    edx,0x5
    8c50:	48 8d 35 ec 2b 00 00 	lea    rsi,[rip+0x2bec]        # b843 <error_at_line@@Base+0xa8da>
    8c57:	31 ff                	xor    edi,edi
    8c59:	e8 62 7c ff ff       	call   8c0 <dcgettext@plt>
    8c5e:	48 89 85 28 ff fb ff 	mov    QWORD PTR [rbp-0x400d8],rax
    8c65:	e9 1f f5 ff ff       	jmp    8189 <error_at_line@@Base+0x7220>
    8c6a:	48 8d 3d f4 2b 00 00 	lea    rdi,[rip+0x2bf4]        # b865 <error_at_line@@Base+0xa8fc>
    8c71:	e8 fa c4 ff ff       	call   5170 <error_at_line@@Base+0x4207>
    8c76:	84 c0                	test   al,al
    8c78:	0f b6 05 a9 65 00 00 	movzx  eax,BYTE PTR [rip+0x65a9]        # f228 <error_print_progname@@Base+0x140>
    8c7f:	0f 85 ed 02 00 00    	jne    8f72 <error_at_line@@Base+0x8009>
    8c85:	84 c0                	test   al,al
    8c87:	0f 85 89 82 ff ff    	jne    f16 <error@@Base+0x1a9>
    8c8d:	c6 05 95 65 00 00 ff 	mov    BYTE PTR [rip+0x6595],0xff        # f229 <error_print_progname@@Base+0x141>
    8c94:	66 0f ef ed          	pxor   xmm5,xmm5
    8c98:	66 0f 76 c0          	pcmpeqd xmm0,xmm0
    8c9c:	31 db                	xor    ebx,ebx
    8c9e:	45 31 f6             	xor    r14d,r14d
    8ca1:	66 0f 6f f5          	movdqa xmm6,xmm5
    8ca5:	4c 8d ad c0 ff fb ff 	lea    r13,[rbp-0x40040]
    8cac:	48 c7 85 48 ff fb ff 	mov    QWORD PTR [rbp-0x400b8],0x0
    8cb3:	00 00 00 00 
    8cb7:	66 0f f8 f0          	psubb  xmm6,xmm0
    8cbb:	0f 29 ad 80 ff fb ff 	movaps XMMWORD PTR [rbp-0x40080],xmm5
    8cc2:	0f 29 b5 90 ff fb ff 	movaps XMMWORD PTR [rbp-0x40070],xmm6
    8cc9:	0f 1f 80 00 00 00 00 	nop    DWORD PTR [rax+0x0]
    8cd0:	8b bd 74 ff fb ff    	mov    edi,DWORD PTR [rbp-0x4008c]
    8cd6:	ba 00 00 04 00       	mov    edx,0x40000
    8cdb:	4c 89 ee             	mov    rsi,r13
    8cde:	e8 ed 7c ff ff       	call   9d0 <read@plt>
    8ce3:	49 89 c4             	mov    r12,rax
    8ce6:	48 85 c0             	test   rax,rax
    8ce9:	0f 8e 83 01 00 00    	jle    8e72 <error_at_line@@Base+0x7f09>
    8cef:	49 01 c6             	add    r14,rax
    8cf2:	4d 8d 7c 05 00       	lea    r15,[r13+rax*1+0x0]
    8cf7:	84 db                	test   bl,bl
    8cf9:	0f 85 39 01 00 00    	jne    8e38 <error_at_line@@Base+0x7ecf>
    8cff:	4d 39 fd             	cmp    r13,r15
    8d02:	0f 83 8f 02 00 00    	jae    8f97 <error_at_line@@Base+0x802e>
    8d08:	48 8d 40 ff          	lea    rax,[rax-0x1]
    8d0c:	48 83 f8 0e          	cmp    rax,0xe
    8d10:	0f 86 88 02 00 00    	jbe    8f9e <error_at_line@@Base+0x8035>
    8d16:	4c 89 e0             	mov    rax,r12
    8d19:	bb 0a 0a 0a 0a       	mov    ebx,0xa0a0a0a
    8d1e:	66 0f ef c0          	pxor   xmm0,xmm0
    8d22:	4c 89 ea             	mov    rdx,r13
    8d25:	66 0f 6e f3          	movd   xmm6,ebx
    8d29:	66 0f ef e4          	pxor   xmm4,xmm4
    8d2d:	66 0f ef d2          	pxor   xmm2,xmm2
    8d31:	48 83 e0 f0          	and    rax,0xfffffffffffffff0
    8d35:	49 8d 74 05 00       	lea    rsi,[r13+rax*1+0x0]
    8d3a:	66 0f 70 f6 00       	pshufd xmm6,xmm6,0x0
    8d3f:	90                   	nop
    8d40:	66 0f 6f ce          	movdqa xmm1,xmm6
    8d44:	48 83 c2 10          	add    rdx,0x10
    8d48:	66 0f 74 4a f0       	pcmpeqb xmm1,XMMWORD PTR [rdx-0x10]
    8d4d:	66 0f db 8d 90 ff fb 	pand   xmm1,XMMWORD PTR [rbp-0x40070]
    8d54:	ff 
    8d55:	66 0f 6f d9          	movdqa xmm3,xmm1
    8d59:	66 0f 60 9d 80 ff fb 	punpcklbw xmm3,XMMWORD PTR [rbp-0x40080]
    8d60:	ff 
    8d61:	66 0f 68 8d 80 ff fb 	punpckhbw xmm1,XMMWORD PTR [rbp-0x40080]
    8d68:	ff 
    8d69:	66 44 0f 6f c3       	movdqa xmm8,xmm3
    8d6e:	66 0f 69 dc          	punpckhwd xmm3,xmm4
    8d72:	66 0f 6f f9          	movdqa xmm7,xmm1
    8d76:	66 44 0f 61 c4       	punpcklwd xmm8,xmm4
    8d7b:	66 0f 61 fc          	punpcklwd xmm7,xmm4
    8d7f:	66 0f 69 cc          	punpckhwd xmm1,xmm4
    8d83:	66 45 0f 6f c8       	movdqa xmm9,xmm8
    8d88:	66 44 0f 6a c2       	punpckhdq xmm8,xmm2
    8d8d:	66 44 0f 62 ca       	punpckldq xmm9,xmm2
    8d92:	66 41 0f d4 c1       	paddq  xmm0,xmm9
    8d97:	66 41 0f d4 c0       	paddq  xmm0,xmm8
    8d9c:	66 44 0f 6f c3       	movdqa xmm8,xmm3
    8da1:	66 0f 6a da          	punpckhdq xmm3,xmm2
    8da5:	66 44 0f 62 c2       	punpckldq xmm8,xmm2
    8daa:	66 41 0f d4 c0       	paddq  xmm0,xmm8
    8daf:	66 0f d4 c3          	paddq  xmm0,xmm3
    8db3:	66 0f 6f df          	movdqa xmm3,xmm7
    8db7:	66 0f 6a fa          	punpckhdq xmm7,xmm2
    8dbb:	66 0f 62 da          	punpckldq xmm3,xmm2
    8dbf:	66 0f d4 c3          	paddq  xmm0,xmm3
    8dc3:	66 0f 6f d9          	movdqa xmm3,xmm1
    8dc7:	66 0f 6a ca          	punpckhdq xmm1,xmm2
    8dcb:	66 0f d4 c7          	paddq  xmm0,xmm7
    8dcf:	66 0f 62 da          	punpckldq xmm3,xmm2
    8dd3:	66 0f d4 c3          	paddq  xmm0,xmm3
    8dd7:	66 0f d4 c1          	paddq  xmm0,xmm1
    8ddb:	48 39 d6             	cmp    rsi,rdx
    8dde:	0f 85 5c ff ff ff    	jne    8d40 <error_at_line@@Base+0x7dd7>
    8de4:	66 0f 6f c8          	movdqa xmm1,xmm0
    8de8:	66 0f 73 d9 08       	psrldq xmm1,0x8
    8ded:	66 0f d4 c1          	paddq  xmm0,xmm1
    8df1:	66 48 0f 7e c2       	movq   rdx,xmm0
    8df6:	49 39 c4             	cmp    r12,rax
    8df9:	74 1a                	je     8e15 <error_at_line@@Base+0x7eac>
    8dfb:	4c 01 e8             	add    rax,r13
    8dfe:	66 90                	xchg   ax,ax
    8e00:	31 f6                	xor    esi,esi
    8e02:	80 38 0a             	cmp    BYTE PTR [rax],0xa
    8e05:	40 0f 94 c6          	sete   sil
    8e09:	48 83 c0 01          	add    rax,0x1
    8e0d:	48 01 f2             	add    rdx,rsi
    8e10:	4c 39 f8             	cmp    rax,r15
    8e13:	72 eb                	jb     8e00 <error_at_line@@Base+0x7e97>
    8e15:	48 01 95 48 ff fb ff 	add    QWORD PTR [rbp-0x400b8],rdx
    8e1c:	48 89 d0             	mov    rax,rdx
    8e1f:	48 c1 e0 04          	shl    rax,0x4
    8e23:	48 29 d0             	sub    rax,rdx
    8e26:	49 39 c4             	cmp    r12,rax
    8e29:	0f 9d c3             	setge  bl
    8e2c:	e9 9f fe ff ff       	jmp    8cd0 <error_at_line@@Base+0x7d67>
    8e31:	0f 1f 80 00 00 00 00 	nop    DWORD PTR [rax+0x0]
    8e38:	41 c6 07 0a          	mov    BYTE PTR [r15],0xa
    8e3c:	4c 89 ef             	mov    rdi,r13
    8e3f:	31 db                	xor    ebx,ebx
    8e41:	eb 0d                	jmp    8e50 <error_at_line@@Base+0x7ee7>
    8e43:	0f 1f 44 00 00       	nop    DWORD PTR [rax+rax*1+0x0]
    8e48:	48 83 c3 01          	add    rbx,0x1
    8e4c:	48 8d 78 01          	lea    rdi,[rax+0x1]
    8e50:	be 0a 00 00 00       	mov    esi,0xa
    8e55:	e8 a6 7b ff ff       	call   a00 <rawmemchr@plt>
    8e5a:	4c 39 f8             	cmp    rax,r15
    8e5d:	72 e9                	jb     8e48 <error_at_line@@Base+0x7edf>
    8e5f:	48 89 d8             	mov    rax,rbx
    8e62:	48 01 9d 48 ff fb ff 	add    QWORD PTR [rbp-0x400b8],rbx
    8e69:	48 c1 e0 04          	shl    rax,0x4
    8e6d:	48 29 d8             	sub    rax,rbx
    8e70:	eb b4                	jmp    8e26 <error_at_line@@Base+0x7ebd>
    8e72:	4c 89 b5 60 ff fb ff 	mov    QWORD PTR [rbp-0x400a0],r14
    8e79:	0f 84 e5 00 00 00    	je     8f64 <error_at_line@@Base+0x7ffb>
    8e7f:	e8 7c 79 ff ff       	call   800 <__errno_location@plt>
    8e84:	44 8b 20             	mov    r12d,DWORD PTR [rax]
    8e87:	45 85 e4             	test   r12d,r12d
    8e8a:	41 0f 94 c5          	sete   r13b
    8e8e:	e9 8c f5 ff ff       	jmp    841f <error_at_line@@Base+0x74b6>
    8e93:	48 8d 3d b8 29 00 00 	lea    rdi,[rip+0x29b8]        # b852 <error_at_line@@Base+0xa8e9>
    8e9a:	e8 d1 c2 ff ff       	call   5170 <error_at_line@@Base+0x4207>
    8e9f:	0f b6 1d 82 63 00 00 	movzx  ebx,BYTE PTR [rip+0x6382]        # f228 <error_print_progname@@Base+0x140>
    8ea6:	84 c0                	test   al,al
    8ea8:	74 4d                	je     8ef7 <error_at_line@@Base+0x7f8e>
    8eaa:	4c 8d 25 ff 65 00 00 	lea    r12,[rip+0x65ff]        # f4b0 <error_print_progname@@Base+0x3c8>
    8eb1:	41 f6 44 24 0d 80    	test   BYTE PTR [r12+0xd],0x80
    8eb7:	74 3e                	je     8ef7 <error_at_line@@Base+0x7f8e>
    8eb9:	48 8d 3d 9b 29 00 00 	lea    rdi,[rip+0x299b]        # b85b <error_at_line@@Base+0xa8f2>
    8ec0:	e8 ab c2 ff ff       	call   5170 <error_at_line@@Base+0x4207>
    8ec5:	84 c0                	test   al,al
    8ec7:	74 2e                	je     8ef7 <error_at_line@@Base+0x7f8e>
    8ec9:	41 f6 44 24 0e 20    	test   BYTE PTR [r12+0xe],0x20
    8ecf:	74 26                	je     8ef7 <error_at_line@@Base+0x7f8e>
    8ed1:	84 db                	test   bl,bl
    8ed3:	0f 85 97 01 00 00    	jne    9070 <error_at_line@@Base+0x8107>
    8ed9:	c6 05 4a 63 00 00 01 	mov    BYTE PTR [rip+0x634a],0x1        # f22a <error_print_progname@@Base+0x142>
    8ee0:	8b b5 74 ff fb ff    	mov    esi,DWORD PTR [rbp-0x4008c]
    8ee6:	48 8d bd a0 ff fb ff 	lea    rdi,[rbp-0x40060]
    8eed:	e8 5e e5 ff ff       	call   7450 <error_at_line@@Base+0x64e7>
    8ef2:	e9 fe f4 ff ff       	jmp    83f5 <error_at_line@@Base+0x748c>
    8ef7:	84 db                	test   bl,bl
    8ef9:	0f 85 ea 7f ff ff    	jne    ee9 <error@@Base+0x17c>
    8eff:	c6 05 24 63 00 00 ff 	mov    BYTE PTR [rip+0x6324],0xff        # f22a <error_print_progname@@Base+0x142>
    8f06:	e9 c5 f4 ff ff       	jmp    83d0 <error_at_line@@Base+0x7467>
    8f0b:	4c 89 eb             	mov    rbx,r13
    8f0e:	4c 8b b5 80 ff fb ff 	mov    r14,QWORD PTR [rbp-0x40080]
    8f15:	41 bd 01 00 00 00    	mov    r13d,0x1
    8f1b:	45 31 e4             	xor    r12d,r12d
    8f1e:	44 0f b6 bd 3b ff fb 	movzx  r15d,BYTE PTR [rbp-0x400c5]
    8f25:	ff 
    8f26:	e9 3c fc ff ff       	jmp    8b67 <error_at_line@@Base+0x7bfe>
    8f2b:	48 89 9d 60 ff fb ff 	mov    QWORD PTR [rbp-0x400a0],rbx
    8f32:	e8 c9 78 ff ff       	call   800 <__errno_location@plt>
    8f37:	44 8b 20             	mov    r12d,DWORD PTR [rax]
    8f3a:	45 85 e4             	test   r12d,r12d
    8f3d:	41 0f 94 c5          	sete   r13b
    8f41:	48 c7 85 58 ff fb ff 	mov    QWORD PTR [rbp-0x400a8],0x0
    8f48:	00 00 00 00 
    8f4c:	45 31 ff             	xor    r15d,r15d
    8f4f:	31 db                	xor    ebx,ebx
    8f51:	45 31 f6             	xor    r14d,r14d
    8f54:	48 c7 85 48 ff fb ff 	mov    QWORD PTR [rbp-0x400b8],0x0
    8f5b:	00 00 00 00 
    8f5f:	e9 88 f7 ff ff       	jmp    86ec <error_at_line@@Base+0x7783>
    8f64:	41 bd 01 00 00 00    	mov    r13d,0x1
    8f6a:	45 31 e4             	xor    r12d,r12d
    8f6d:	e9 ad f4 ff ff       	jmp    841f <error_at_line@@Base+0x74b6>
    8f72:	48 8d 15 37 65 00 00 	lea    rdx,[rip+0x6537]        # f4b0 <error_print_progname@@Base+0x3c8>
    8f79:	f6 42 0d 04          	test   BYTE PTR [rdx+0xd],0x4
    8f7d:	0f 84 02 fd ff ff    	je     8c85 <error_at_line@@Base+0x7d1c>
    8f83:	84 c0                	test   al,al
    8f85:	0f 85 38 7f ff ff    	jne    ec3 <error@@Base+0x156>
    8f8b:	c6 05 97 62 00 00 01 	mov    BYTE PTR [rip+0x6297],0x1        # f229 <error_print_progname@@Base+0x141>
    8f92:	e9 4c f4 ff ff       	jmp    83e3 <error_at_line@@Base+0x747a>
    8f97:	31 c0                	xor    eax,eax
    8f99:	e9 88 fe ff ff       	jmp    8e26 <error_at_line@@Base+0x7ebd>
    8f9e:	31 d2                	xor    edx,edx
    8fa0:	4c 89 e8             	mov    rax,r13
    8fa3:	e9 58 fe ff ff       	jmp    8e00 <error_at_line@@Base+0x7e97>
    8fa8:	80 3d e1 64 00 00 00 	cmp    BYTE PTR [rip+0x64e1],0x0        # f490 <error_print_progname@@Base+0x3a8>
    8faf:	0f 85 08 f4 ff ff    	jne    83bd <error_at_line@@Base+0x7454>
    8fb5:	e9 9f f4 ff ff       	jmp    8459 <error_at_line@@Base+0x74f0>
    8fba:	48 b9 ff ff ff ff ff 	movabs rcx,0x1fffffffffffffff
    8fc1:	ff ff 1f 
    8fc4:	48 8b 43 40          	mov    rax,QWORD PTR [rbx+0x40]
    8fc8:	48 8d 50 ff          	lea    rdx,[rax-0x1]
    8fcc:	48 83 c0 01          	add    rax,0x1
    8fd0:	48 39 d1             	cmp    rcx,rdx
    8fd3:	ba 01 02 00 00       	mov    edx,0x201
    8fd8:	48 0f 43 d0          	cmovae rdx,rax
    8fdc:	4c 89 e8             	mov    rax,r13
    8fdf:	48 89 d1             	mov    rcx,rdx
    8fe2:	48 99                	cqo
    8fe4:	48 f7 f9             	idiv   rcx
    8fe7:	49 29 d5             	sub    r13,rdx
    8fea:	4d 39 ee             	cmp    r14,r13
    8fed:	0f 8d 17 f5 ff ff    	jge    850a <error_at_line@@Base+0x75a1>
    8ff3:	8b bd 74 ff fb ff    	mov    edi,DWORD PTR [rbp-0x4008c]
    8ff9:	4c 89 ee             	mov    rsi,r13
    8ffc:	ba 01 00 00 00       	mov    edx,0x1
    9001:	4d 29 f5             	sub    r13,r14
    9004:	e8 47 79 ff ff       	call   950 <lseek@plt>
    9009:	48 85 c0             	test   rax,rax
    900c:	4c 0f 48 ad 60 ff fb 	cmovs  r13,QWORD PTR [rbp-0x400a0]
    9013:	ff 
    9014:	4c 89 ad 60 ff fb ff 	mov    QWORD PTR [rbp-0x400a0],r13
    901b:	e9 ea f4 ff ff       	jmp    850a <error_at_line@@Base+0x75a1>
    9020:	8b bd 74 ff fb ff    	mov    edi,DWORD PTR [rbp-0x4008c]
    9026:	b9 02 00 00 00       	mov    ecx,0x2
    902b:	31 d2                	xor    edx,edx
    902d:	31 f6                	xor    esi,esi
    902f:	e8 7c 79 ff ff       	call   9b0 <posix_fadvise@plt>
    9034:	e9 84 f3 ff ff       	jmp    83bd <error_at_line@@Base+0x7454>
    9039:	48 8b bd 28 ff fb ff 	mov    rdi,QWORD PTR [rbp-0x400d8]
    9040:	e8 2b ec ff ff       	call   7c70 <error_at_line@@Base+0x6d07>
    9045:	48 8d 15 e9 28 00 00 	lea    rdx,[rip+0x28e9]        # b935 <error_at_line@@Base+0xa9cc>
    904c:	44 89 e6             	mov    esi,r12d
    904f:	31 ff                	xor    edi,edi
    9051:	48 89 c1             	mov    rcx,rax
    9054:	31 c0                	xor    eax,eax
    9056:	e8 12 7d ff ff       	call   d6d <error@@Base>
    905b:	e9 82 f7 ff ff       	jmp    87e2 <error_at_line@@Base+0x7879>
    9060:	e8 8b 78 ff ff       	call   8f0 <__stack_chk_fail@plt>
    9065:	41 89 cc             	mov    r12d,ecx
    9068:	45 31 c9             	xor    r9d,r9d
    906b:	e9 ab f7 ff ff       	jmp    881b <error_at_line@@Base+0x78b2>
    9070:	e9 ce 7e ff ff       	jmp    f43 <error@@Base+0x1d6>
    9075:	66 2e 0f 1f 84 00 00 	cs nop WORD PTR [rax+rax*1+0x0]
    907c:	00 00 00 
    907f:	90                   	nop
    9080:	f3 0f 1e fa          	endbr64
    9084:	48 8b 15 b5 58 00 00 	mov    rdx,QWORD PTR [rip+0x58b5]        # e940 <error_at_line@@Base+0xd9d7>
    908b:	31 f6                	xor    esi,esi
    908d:	e9 9e 7a ff ff       	jmp    b30 <__cxa_atexit@plt>

Desensamblado de la sección .fini:

0000000000009094 <.fini>:
    9094:	f3 0f 1e fa          	endbr64
    9098:	48 83 ec 08          	sub    rsp,0x8
    909c:	48 83 c4 08          	add    rsp,0x8
    90a0:	c3                   	ret
