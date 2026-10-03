```
CLASE      PROVEN · tablas CALCULADAS, no escritas a mano
FUENTE     corpus linux-7.1.3 · /var/tmp/rx550-incident-pre-reboot-dmesg.txt
GENERADO   report 1.0 · cada tabla lleva el comando que la produce
REGENERAR  una regeneracion sin cambios da un fichero byte-identico
UBICACION  /var/tmp/rx550/  (durable; sobrevivio a 3 reinicios)
```


## 1. Alcance

```
  correcciones indexadas  163
  numero maximo           199
  clases de error        14
```

## 2. Reparto por clase

_Una correccion puede pertenecer a varias clases; el reparto no suma 100%. Se parsean las filas con formato tabla; las correcciones 1-46 esta resumidas por clase en prosa y NO se cuentan aqui._

```
  F cero silencioso                           11
  J dos espacios de offset                    10
  N resolvia el ambito equivocado              9
  H filtro que parece prefijo                  8
  D mezclar generaciones                       7
  M mutex en fichero no en funcion             4
  K rendimiento                                3
  B citar file:N sin abrir                     2
  E primero que casa                           2
  L re.MULTILINE                               2
  C el test afirma una creencia                1
  G cobertura como prosa                       1
  I prediccion mas amplia                      1
  A nombre asumido -> 0 -> ausente             0
```

_clases sin asignar en las filas parseadas: A nombre asumido -> 0 -> ausente_

**112 correcciones sin clase asignada**: [47, 48, 49, 52, 53, 55, 56, 58, 59, 61, 64, 65, 66, 69, 72, 83, 84, 85, 88, 89, 95, 97, 99, 102, 105]…

_Eso no es un fallo del clasificador sino una senal: son filas cuyo texto no encaja en ninguna clase que yo haya definido, o sea que la taxonomia esta incompleta._

### Las tres clases dominantes

- **F cero silencioso**: 11 correcciones → [51, 60, 70, 79, 81, 96, 98, 113, 126, 122, 162]
- **J dos espacios de offset**: 10 correcciones → [68, 71, 80, 82, 86, 87, 91, 92, 93, 103]
- **N resolvia el ambito equivocado**: 9 correcciones → [57, 74, 82, 91, 92, 93, 101, 103, 122]
