break trace.c:19
run
set $ls = ls
set $p = (int (*)(const char*, char*))($ls + 0x4fa0)
p $p("a", "z")
p $p("a", "a")
p $p("z", "a")
p $p("1", "2")
p $p("${"a":"a"}", "${"b":"1"}")
quit
