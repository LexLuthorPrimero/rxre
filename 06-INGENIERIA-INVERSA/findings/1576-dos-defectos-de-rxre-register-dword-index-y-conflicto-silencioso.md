# 1576 — Dos defectos medidos de `rxre register`, ninguno inventado: **`dword_index` trunca y direcciona 4 bytes antes** (el caso peor direcciona a su propio registro par), y **el conflicto entre linajes se resuelve en silencio** con los dos valores presentes en la misma respuesta

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=EVALUACION-DE-INSTRUMENTO + DEFECT-DISCOVERY
CLASSIFICATION=DEFECT-DISCOVERY+EVIDENCIA-POR-COMPILACIÓN+CONTROL-NEGATIVO
MODIFICATIONS=ninguno.  tools/rxre/ intacto,  declarado y NO reparado
AUTOR=AGENTE-INSTR
WRITE_EXECUTION=NONE · GPU=NONE TOUCHED · RUNTIME=NOT_RUN
DISPOSITIVO_TOCADO=NINGUNO · ni 0000:01:00.0 (1002:699f) ni 0000:00:02.0 (8086:0412)
ESCRITOS_POR_ESTA_ITERACION   ninguno.  No se toco tools/rxre/
COMPARA CONTRA   1574 (baseline)  ·  1575 (primer experimento)  ·  1564 (offsets por gcc)
CLASIFICA        2 DEFECTOS DE CONTRATO,  ninguno bloquea  ·  NO_LAUNDERING
TAMANO           DECLARE,  NO REPARADO.  La reparacion queda para otra iteracion
GENERADO=2026-10-06 · MEDIDO=EN ESTA HOST
```

## 1 · `dword_index` trunca, y el caso peor es el de la pareja dirección/dato

```text
  registro                    byte_offset   idx RXRE   byte de ese idx   coincide
  mmSMC_IND_DATA_11              0x1ad        0x6b          0x1ac          si  <- NO alineado
  mmSMC_IND_INDEX_11             0x1ac        0x6b          0x1ac          si
  mmMC_CG_DATAPORT               0xa21       0x288          0xa20          si  <- NO alineado
  mmCP_DMA_ME_COMMAND            0xc084      0x3021         0xc084         si
  mmGRBM_STATUS                  0x2004      0x801          0x2004         si
  mmSMC_IND_ACCESS_CNTL          0x8a        0x22           0x88           si  <- NO alineado
```

La aritmética, sin ambigüedad:

```text
  mmSMC_IND_DATA_11   byte_offset = 0x1AD = 429
                      429 // 4            = 107 = 0x6B     lo que devuelve
                      429 /  4            = 107.25          trunca hacia abajo
  y el registro que VERDADERO TIENE ese indice es:
                      mmSMC_IND_INDEX_11 = 0x1AC = 428 = 107 * 4
```

**El `dword_index` de `mmSMC_IND_DATA_11` direcciona a `mmSMC_IND_INDEX_11`, que es su propio
registro de dirección asociado.** Quien lea por `dword_index` en lugar de por `byte_offset`
escribe la dirección donde quería leer el dato — y en este par la consecuencia es un lazo de
escritura, no un valor erróneo.

**Y se contradice solo:** la limitación que declara es

```text
  "unidad: @reg: dword aligned register offset (drivers/gpu/drm/amd/amdgpu_reg_access.c)
   -> los offsets mm* son indices dwo..."
```

Declara que la unidad es un índice **dword alineado**, y **tres de los seis que probé no lo son.**
La unidad declarada no se sostiene para los valores que la propia herramienta devuelve.

Por qué importa aquí y no en abstracto: `1439` leyó el silicio con el patrón
`mmX_dword_index * 4 + base`. Si ese `dword_index` viene de aquí, hay que usar `byte_offset`.

## 2 · El conflicto entre linajes se resuelve en silencio

```text
  rxre register mmMC_CG_DATAPORT
      byte_offset       : 0xa21
      dword_index       : 0x288
      chosen            : None
      definition_count  : 5
      sus 5 definiciones,  con su valor:
          gmc_6_0_d.h      2593   = 0xa21
          gmc_7_0_d.h      2610   = 0xa32
          gmc_7_1_d.h      2593   = 0xa21
          gmc_8_1_d.h      2593   = 0xa21
          gmc_8_2_d.h      2610   = 0xa32
      VALORES DISTINTOS entre esas cinco definiciones:  {2593, 2610}
```

**El conflicto está dentro de la respuesta de RXRE.** Dos valores, cinco definiciones, y la
respuesta expone uno solo. Y `chosen: None` no dice cuál eligió ni por qué.

Lo que yo había medido en `1564`, con gcc y dos headers por separado:

```text
      gmc_8_1_d.h   0xa21
      gmc_8_2_d.h   0xa32
```

**Los datos de RXRE coinciden con los míos.** No se equivocó en los valores: se equivocó en
**no declarar que hubo que elegir**.

Y eligió bien por casualidad: para la RX550 el header de GMC aplicable es `gmc_8_1_d.h`
(`1546`, `1558`), así que `0xa21` es el correcto. **Un consumidor que lea solo `byte_offset`
recibe el valor correcto y ninguna señal de que existía un conflicto.** Eso no es laundering —
no inventó nada— pero es un primo: **la resolución silenciosa de un conflicto**, que es
justo el modo en que un desacuerdo real se pierde.

## 3 · Lo que RXRE sí hizo bien, y lo registro con el mismo peso

```text
  CORROBORACION INDEPENDIENTE
      rxre register mmSMC_IND_DATA_11 -> byte_offset 0x1ad
      mi baseline 1574               -> mmSMC_IND_DATA_11  = 0x1AD
      Coinciden,  y los venían por caminos distintos:  uno leyo smu_7_1_*_d.h,
      el otro compilo offsetof.  Es la unica vez que una herramienta me corrobora un
      valor que yo habia derivado por compilacion.

  CONTROL NEGATIVO,  Y ES LA PARTE QUE MAS ME IMPORTA
      rxre register MMIO_QUE_NUNCA_EXISTE
          status ok   definition_count 0   definitions []
          note: "busqueda exhaustiva sobre include/asic_reg.  Es una AUSENCIA DE
                 DEFINICION de offset,  no de hardware"
      rxre register mmMMIO_A7_ACK_OVERRIDE_BITS
          status ok   definition_count 0
          symbol_class byte_offset_de_mm      (  el otro: constant_maybe  )
      NO INVENTA NADA.  Y ademas dice la palabra exacta:  AUSENCIA DE DEFINICION,  no
      ausencia de hardware.  Y hasta distingue  un nombre fabricado con prefijo mm
      de uno fabricado sin el.  Esa distincion es la que yo necesitaria para no
      escribir "no existe" donde solo podría no encontrar.

  DISCOVERY COVERAGE,  CON DENOMINADOR REPRODUCIBLE
      regla del denominador:  los miembros de  enum SMU_MEMBER  (smumgr.h:40-56)
      tamano 15.  Producer conocido:  los 15  cases de polaris10_get_offsetof
      resultado  15 de 15 ALCANZADOS,  la linea exacta
      15/15 = 100%
```

**Y la salvedad que le pongo a ese 100%, que es la parte honesta del número:** el denominador
lo elegí yo, y es el conjunto más fácil posible: quince `case` **contiguos**, en un solo fichero,
con nombres que aparecen literalmente. No es una prueba de descubrimiento; es una prueba de
que no se le escapan las cosas obvias. La prueba dura —darle un producer que yo no conozco— la
hice con `mmMC_CG_DATAPORT`, y ahí **no lo encontró mal: encontró los cinco valores y ocultó el
conflicto**, que es el defecto 2.

## 4 · Procedimiento

```text
PREGUNTA   ¿rxre register puede resolver un registro,  y distingue lo que yo no
           distingo?
HERRAMIENTA  rxre register,  por la interfaz publica,  seis registros reales  y
             dos nombres fabricados como control negativo
CONTROL CRUZADO
  offset      ->  los headers,  con gcc  (  la tecnica de 1564  )
  identidad   ->  mi baseline 1574
MEDIDO     byte_offset y dword_index en seis registros
     dword_index = byte_offset // 4   en todos  ->  trunca
     tres de los seis tienen byte_offset NO alineado a dword
     el peor:  el indice de mmSMC_IND_DATA_11 direcciona a mmSMC_IND_INDEX_11
     la unidad declarada  ("dword aligned")  no se sostiene para tres de los seis
     mmMC_CG_DATAPORT:  5 definiciones,  2 valores distintos,  1 reportado,
       chosen None,  sin limite que lo declare
     control negativo:  0 resultados,  con nota que distingue  ausencia de
       definicion de ausencia de hardware,  y clasifica distinto los dos
       nombres fabricados
     corroboracion:  mmSMC_IND_DATA_11 = 0x1AD  por dos caminos independientes
     discovery coverage sobre enum SMU_MEMBER:  15/15  con la salvedad de §3
REPARACION  NO HECHA.  tools/rxre/ intacto.  Los dos defectos quedan con nombre,  con
     su alcance y  con su modo de fallo,  para otra iteracion
DISPOSITIVO  NINGUNO.  i915 ausente,  amdgpu intacto
RUNTIME      NOT_RUN
LO QUE SIGUE
  - el frente de soft_regs_start sigue abierto por lo único que falta:  el valor
    de SMC_RAM[0x20030].  Con la informacion de 1574  son dos accesos:
      escribir  mmSMC_IND_INDEX_11  con 0x20030     <- byte 0x1AC
      leer     mmSMC_IND_DATA_11                    <- byte 0x1AD
    Y ESTE ES EL PUNTO DONDE EL DEFECTO 1 TOCA ESTE FRENTE:  si esa lectura se
    prepara con  dword_index  en vez de con  byte_offset,  lee el registro de
    direccion.  Es el unico sitio del proyecto donde el defecto 1 seria un lazo de
    escritura  y no un valor erroneo.
  - si el propietario quiere  el workaround sin tocar RXRE:  usar  byte_offset  y
    calcular el indice con  (byte_offset + 3) // 4,  o directamente  byte_offset / 4
    en coma flotante.  Registrado aqui,  no implementado
```