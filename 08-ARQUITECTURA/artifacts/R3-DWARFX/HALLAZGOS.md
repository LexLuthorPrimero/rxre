# R3-DWARFX — el `.ko` compilado sí corresponde a la fuente actual, y ahora eso se puede comprobar

<!-- MEDIDO con tools/dwarfx.py. Artefacto: dwarfx.json.
     Regenerar: python3 tools/dwarfx.py --json > 08-ARQUITECTURA/artifacts/R3-DWARFX/dwarfx.json -->

```
AGENCIA=RX550-INVESTIGACION · AGENT RE/TOOLING
WORK_CLASS=validacion-de-instrumentacion
RUNTIME=NO · sin sudo · sin compilar · sin ejecutar el modulo · GPU=INTACTA
escritura=4 ficheros NUEVOS.  Ningun fichero existente modificado.
herramienta   tools/dwarfx.py 1.0.0
sha256        33c9254741bb882e
artefacto     08-ARQUITECTURA/artifacts/R3-DWARFX/dwarfx.json
sha256        b3f8f4aa5e30eedb
reproducible  a00e8a4a839b575b7f8efa32c300513311cc41f7c22205d58e5540ef23a3baf6
selftest      14 vectores, 0 fallos, rc=0   (HERMETICO: verificado en copia aislada y otro cwd)
```

## 0 · EL RESULTADO, PRIMERO

```
$ python3 tools/dwarfx.py
  493 structs en DWARF, 29 cabecera(s) leida(s), 650 comparaciones
  conteo: CABECERA_NO_LEIDA=446, COINCIDE=204

  COINCIDE: 204 de 204 miembros cuya cabecera se ha leido (100 %).
```

**El módulo compilado y las cabeceras del proyecto son la misma cosa**, verificado
miembro a miembro y línea a línea. Cero movidos, cero que el `.ko` tenga y la
cabecera ya no, cero que la cabecera tenga y el `.ko` no viera.

No es un resultado escritorio. Mientras esta trabajo corría, `git status` mostraba
`rx550_pdb0.h`, `rx550_gart_geom.h`, `rx550_vm_geom.h`, `rx550_target.c` y
`rx550_vmid1_pgt.c` modificados, y `rx550_drv.ko` recompilándose por debajo. La
pregunta «¿el `.ko` que estoy citando es de esta fuente?» era real y se
repetía. Ahora tiene respuesta y cuesta un comando.

## 1 · POR QUÉ `DW_AT_decl_line` Y NO `sizeof`

`DWARF` guarda, de cada miembro, **la línea del `.h` donde el compilador lo vio**.
Eso da la correspondencia sin compilar nada:

```
para cada miembro que el compilador recordó, ¿esa línea sigue siendo la línea de
ese miembro en la cabecera actual?
```

**`sizeof` no sirve para esto, y es tentador usarlo.** El DWARF lo generó el
compilador *desde* la cabecera, así que el tamaño coincide por construcción.
Contrastarlo sería medir el compilador contra sí mismo: un verde que no
informa de nada. Se dice en el propio informe, porque es el error que hace
sentido escribir.

## 2 · EL DENOMINADOR HONESTO

Hay 446 tipos en el `.ko` que vienen de cabeceras del **kernel**
(`/usr/src/kernels/…`, `fs.h`, `sched.h`, `module.h`…), no del proyecto. Un `.ko`
compila contra el kernel entero.

La primera versión imprimía `COINCIDE: 204 de 650`. Parece una cobertura del
31 %. Es un número sin significado: el denominador metía 446 tipos que no son
del proyecto y que esta herramienta no comprueba. Ahora el denominador son los
**204 miembros cuya cabecera se ha leído**, y sale 100 %.

Los 446 no se borran: se agrupan por fichero declarado y se dice que son
`NOT_DETERMINED`, no ausencia.

## 3 · TRES DEFECTOS PROPIOS QUE SALIERON AL APLICARLA

Se escriben porque un instrumento que no reporta sus errores no es un
instrumento, es una fuente de afirmaciones. Los tres los encontró el uso sobre
el `.ko` real, no la lectura.

### 3.1 · El parser de DWARF era FALSO por una suposición de formato

Buscaba `DW_AT_name` en la misma línea que el `DW_TAG_structure_type`. **No
está ahí.** El formato real es una línea por DIE y una por atributo, con la
relación establecida por la indentación.

Pasó sus vectores —porque el fixture se había escrito con la misma suposición
que el parser— y falló con el fichero real. **El fixture y el parser tenían el
mismo error, así que se validaban mutuamente.** El fixture se rehízo copiando
la salida real de `llvm-dwarfdump`, con sus tabuladores.

### 3.2 · La cabecera se elegía por «la última que declara el struct»

Con dos cabeceras que declaran el mismo struct —normal cuando un `.h` incluye a
otro— el veredicto salía de la que casara por casualidad. **Un acierto por
casualidad es peor que un fallo**, porque no se puede distinguir de uno.

Ahora la cabecera la dice el propio DWARF (`DW_AT_decl_file`), y si no está:

- **una sola** cabecera declara el struct → determinación única, se usa, y cada
  fila lleva `cabecera_por_declaracion: false` para que el lector lo sepa;
- **varias** → `CABECERA_AMBIGUA`, porque elegir una sería una decisión;
- **ninguna** → `CABECERA_NO_LEIDA`, y no se adivina.

### 3.3 · 121 falsos positivos que acusaban al `.ko` de estar viejo

`SOLO_EN_DWARF` significa «el `.ko` tiene un miembro que la cabecera ya no
tiene». Salió **121 veces**, y era falso las 121.

La causa: la regex de miembro exigía `;` al final de línea, y estas cabeceras
alinean un comentario **detrás** del punto y coma:

```c
uint64_t   dma_pa;   /* PA del sistema, la que va al registro */
```

**Un parser que no ve la propia fuente culpa a la fuente.** Se añadió
`_sin_comentarios()`, que quita `/* */` y `//` respetando literales.

Y quedaba **uno**, `rx550_gart_tlb.request`, que sí es un puntero a función:

```c
void   (*request)(void *ctx, unsigned vmid);
```

Forma que el patrón plano no cubre, porque tiene parámetros entre el nombre y
el `;`. Un falso positivo que acusa de *staleness* es el peor de los dos: alguien
se lo creería y reconstruiría por nada. Ambos casos tienen vector (`PTR_1`,
`PTR_2`).

## 4 · LO QUE ESTO NO DICE

- **No dice que el driver funcione.** Dice que el artefacto y la fuente son la
  misma cosa, que es la pregunta *previa*.
- **Solo ve los tipos que llegan hasta DWARF.** Un struct que nadie instancia
  puede no tener DIE, y eso sale como ausente, que no es lo mismo que correcto.
- **No calcula offsets desde la cabecera.** No compila nada. Si un offset está
  mal en la cabecera, esto no lo ve: ve que la *línea* coincide.
- **El parseo depende del formato de `llvm-dwarfdump`.** Si el formato cambia,
  esto ve menos structs y no lo avisa. Por eso el informe imprime cuántos ha
  visto: para que un cero sea visible en lugar de silencioso.

## 5 · VEREDICTOS

| veredicto | qué significa |
|---|---|
| `COINCIDE` | el compilador y la cabecera ponen el miembro en la misma línea |
| `LINEA_MOVIDA` | la cabecera se movió después del build; el `.ko` es anterior |
| `SOLO_EN_DWARF` | el `.ko` tiene un miembro que la cabecera ya no declara |
| `SOLO_EN_CABECERA` | la cabecera declara un miembro que el `.ko` no vio |
| `CABECERA_NO_LEIDA` | el tipo viene de un fichero que no está entre las cabeceras del proyecto |
| `CABECERA_AMBIGUA` | el struct aparece en varias cabeceras: elegir una sería una decisión |
| `SIN_LINEA` | el compilador no guardó línea: no hay con qué comparar |

```
ESTADO
  ficheros escritos    4, todos nuevos
  ficheros modificados 0
  GPU                  INTACTA
  sudo                 NO usado
  modulo ejecutado     NO
  commits              NINGUNO
```