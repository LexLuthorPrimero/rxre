# 1192 — El coste no son los campos que faltan: es que **nunca se escriben dos a la vez**. 1 hallazgo de 677 lleva dos o más. Y la escalera dice que las nueve reglas no tienen atajo

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=EVIDENCE-FORMAT-AUDIT + SELF-AUDIT
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   tools/rxre.py  (180 -> 188 vectores, rc=0)
CLASE=MEASUREMENT · SELF-AUDIT · ESTADO=MEDIDO
PRECEDE=1191 (que dio 0 de 9 reglas aplicables) y su "NO MEDIDO"
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST
```

## 0 · La lectura que había que corregir

`1191` dio el dato: **0 de 9 reglas son aplicables** a un hallazgo real, y 8 de los 17 campos que
necesitan no aparecen en ninguno de los 676. Leído tal cual, eso se traduce a un precio que
nadie paga:

```text
escribir 676 hallazgos × 17 campos = 11 492 campos nuevos
```

Esa lectura es **incorrecta**, y este hallazgo la corrige midiendo las dos cosas que la
sustituyen.

## 1 · ¿Cuántos campos hacen falta para desbloquear cuántas reglas?

Recorrido **por subconjuntos**, no con un codicioso: con 17 campos son 131072
combinaciones, y un codicioso puede quedarse corto sin que se note. El máximo está
**demostrado**, no a ojo.

```text
$ rxre escalera

ESCALERA  campos -> reglas desbloqueadas
   1 -> 0
   2 -> 1
   3 -> 2
   4 -> 3
   6 -> 4
   7 -> 5
   9 -> 6
  11 -> 7
  14 -> 8
  17 -> 9
```

Tres cosas se leen aquí:

```text
NO HAY ATAJO        para las nueve hacen falta los 17.  Cada regla mira su
                    propio vocabulario y ningun campo sirve para dos.

LA CURVA ES DURA    4 campos -> 3 reglas,  y 13 campos mas -> las 6 que faltan.
                    El esfuerzo no se reparte parejo.

NINGUN CAMPO SOSTIENE UNA REGLA ENTERA
                    las nueve reglas de 1 solo campo: 0 de 9
```

## 2 · El dato que cambia la acción: la co-ocurrencia

```text
$ rxre escalera | tail -4

LO QUE EL CUERPO YA HACE
  campos con presencia: estado, fuente, origen, rc, resultado, validado,
                        valor, veredicto, verificado
  maximo juntos en un hallazgo: 2
  hallazgos con 2 o mas: 1 de 677
```

Nueve campos **ya se escriben**. Y se escriben **solos**:

```text
  1 hallazgo de 677 lleva dos o mas
  el maximo de campos vivos en un mismo hallazgo: 2
```

> El cuerpo no tiene un formato de evidencia. Tiene campos sueltos, uno cada vez.

Y el giro que lo hace accionable:

```text
  los 4 campos con MAS presencia      fuente=8   estado=3   origen=2   valor=2
  y juntos desbloquean               3 reglas
```

Esos cuatro **ya se escriben**. Lo que no se hace es escribirlos en el mismo sitio. El
precio real de `1191` no son 11 492 campos nuevos: es declarar en la misma cabecera los que
ya se declaran.

## 3 · La autoauditoría, que es lo que lo hace incómoda

Antes de proponer un formato a nadie, lo comprobé sobre **mis** hallazgos:

```text
  $ sobre 06-INGENIERIA-INVERSA/findings/1181..1191-*.md   (11 ficheros)

    1181-layout-del-ib-de-shader-init.md              (ninguno)
    1182-condicionales-y-el-7-que-declara-el-driver.md  valor
    1183-perdida-de-ibref-y-reconstruccion-parcial.md (ninguno)
    1184-primera-observacion-en-vivo-de-la-rx550.md   (ninguno)
    1185-los-shaders-del-driver-son-codigo-gfx8.md    (ninguno)
    1186-rxre-y-la-frontera-duera-mal-planteada.md    (ninguno)
    1187-la-clave-ib-dentro-de-reconocible.md           estado
    1188-manifiesto-de-madurez-y-los-huecos-reales.md (ninguno)
    1189-toolreg-dos-programas-con-el-mismo-nombre.md (ninguno)
    1190-los-validadores-no-se-probaba-que-fallaran.md (ninguno)
    1191-las-nueve-reglas-no-alcanzan-al-corpus.md     validado

    campos de las nueve reglas en mis 11 hallazgos: 3 apariciones
```

**Tres en once**, y **8 de 11 no tienen ninguno**. La auditoría no es un reproche a otras
sesiones: **§11 EVIDENCE REGISTRY no lo cumple el agente que acaba de escribir que no se
cumple**. Eso convierte el hallazgo de una observación sobre los demás en una sobre el
método, que es donde puede corregirse.

## 4 · Lo que esto NO dice

```text
MEDIDO      la escalera (por subconjuntos, exhaustiva)
MEDIDO      la co-ocurrencia maxima y real por hallazgo
MEDIDO      mi propio incumplimiento, contado con la misma herramienta

NO MEDIDO   que escribir los campos vaya a producir verdad.  Un campo
            `fuente=estatico` escrito a mano es una DECLARACION,  y §82 dice
            que un comando ejecutado no es un claim probado.  Rellenar la
            cabecera hace las reglas ejecutables;  no las hace ciertas.

NO MEDIDO   que los 676 hallazgos sean correctos,  y no se toca su contenido

NO MEDIDO   el efecto de escribirlos:  no se ha escrito ni uno,  asi que la
            mejora en "reglas aplicables" es una PREDICCION,  no un resultado
```

Ese límite es el que separa esto de `AUTOMATION THEATER`: **no se ha escrito ningún campo
nuevo**, así que la única mejora medida aquí es la de saber qué falta.

## 5 · Procedimiento

```text
anadido     _reglas_desbloqueadas(campos)
            cobertura_minima()    escalera exhaustiva + el minimo para todas
            coocurrencia_de_campos()   maximo de campos vivos por hallazgo,
                                    y cuantos hallazgos llevan 2 o mas
            CLI `rxre escalera`

medido      escalera 1..17 campos -> 0..9 reglas;  monotona;  sin atajo
            campos vivos en el cuerpo: 9 de 17
            maximo juntos en un hallazgo: 2
            hallazgos con 2 o mas campos vivos: 1 de 677
            mis 11 hallazgos: 3 apariciones;  8 de 11 con ninguno

no hecho    escribir un solo campo nuevo en un solo hallazgo.  Es decision de
            formato del cuerpo,  y el limite de arriba dice que rellenarlo no
            convierte una declaracion en una verdad
escrituras  tools/rxre.py unicamente
runtime     RUNTIME=NOT_RUN.  Ni la RX550 ni la Intel.  i915 y amdgpu intactos
```
