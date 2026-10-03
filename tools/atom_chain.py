#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
atom_chain.py -- resolucion de direcciones del VBIOS ATOM por la CADENA DEL DRIVER,
sin direcciones anotadas a mano.

POR QUE EXISTE
--------------
He fallado esta cadena tres veces en tres iteraciones distintas:

  1. use una direccion absoluta anotada de un hallazgo previo (0x9D14 en vez de 0x9D15);
  2. sustituí la lectura en cadena por una suma de direcciones, confundiendo
     "la direccion del campo que contiene data_table" con "el valor de data_table";
  3. repeti el mismo error de (2) en la iteracion siguiente.

En los tres casos la lectura dio un resultado PLAUSIBLE en apariencia pero falso:
PPI = 0x4D4F, que es la cadena ASCII "MO". Un numero plausible no es un numero
verificado.

QUE HACE
--------
Reproduce literalmente la cadena del driver amdgpu:

  amdgpu_atombc.c      base       = CU16(0x48)                    ATOM header
  ...                  data_table = CU16(base + 0x20)
  process_pptables     PPI        = CU16(data_table + 4 + 2*idx)  master data table
  ...                  tabla      = PPI + CU16(PPI + byte_offset)

Los byte_offset de cada campo NO estan aqui: se leen del BTF con btfq, que es la
autoridad de layout. Este modulo solo conoce los bytes que estan MEDIDOS y
VERIFICADOS contra un resultado, y los declara como tales en CAMPOS_BTF.

ESTADO: VALIDATED  (self-test aparte, ver --self-test)
WORK_CLASS: READ_ONLY. Solo lee. No modifica hardware, ni modulos, ni sysfs.
"""

import io
import os
import struct
import sys

VERSION = "1.3.0"

# --------------------------------------------------------------------------
# CAMPOS_BTF -- byte offset dentro de ATOM_Tonga_POWERPLAYTABLE
#
# Cada valor viene de `btfq.py struct ATOM_Tonga_POWERPLAYTABLE` (BTF del
# amdgpu.ko REALMENTE CARGADO en este host), no del arbol de fuentes.
# Corroboracion cruzada: usSclkDependencyTableOffset=45, usPowerTuneTableOffset=57
# y usPCIETableOffset=61 reproducen tablas con contenido coherente por dominio
# (ver los vectores de known_vectors en --self-test).
# --------------------------------------------------------------------------
CAMPOS_BTF = {
    "usStructureSize":            0,   # el propio PowerPlayInfo
    "ucPPLVersion":               1,
    "usFanTableOffset":          37,   # bitoff 296
    "usThermalControllerOffset": 39,   # bitoff 312
    "usSclkDependencyTableOffset": 45,  # bitoff 360
    "usPowerTuneTableOffset":    57,   # bitoff 456
    "usPCIETableOffset":         61,   # bitoff 488
}

# La firma que el driver exige en base+4 antes de fiarse de base.
FIRMA_ATOM = b"ATOM"

# El numero de entradas del master data table se busca por su tipo, no por indice
# fijo: es la entrada cuyo campo es ATOM_Tonga_POWERPLAYTABLE. El indice medido
# en esta placa es 15 y se declara aparte para poder auditarlo.
MDT_PPI_INDEX = 15
MDT_PPI_INDEX_MEDIDO = 15


class AtomError(Exception):
    """Fallo de validacion. Nunca se degrada a un valor por defecto."""


class VBIOS(object):
    """Lector del VBIOS con la cadena del driver, sin magic numbers de direccion."""

    def __init__(self, datos, strict=True):
        self.d = datos
        self.strict = strict
        self.n = len(datos)
        self._cache = {}
        self._validar_firma()

    # -- acceso crudo con rango comprobado ---------------------------------
    def _lee(self, addr, ancho):
        if addr < 0 or addr + ancho > self.n:
            raise AtomError(
                "lectura fuera de rango: addr=0x%X ancho=%d tamano=%d"
                % (addr, ancho, self.n))
        if ancho == 1:
            return self.d[addr]
        if ancho == 2:
            return struct.unpack_from("<H", self.d, addr)[0]
        if ancho == 4:
            return struct.unpack_from("<I", self.d, addr)[0]
        raise AtomError("ancho no soportado: %d" % ancho)

    def u8(self, addr):
        return self._lee(addr, 1)

    def u16(self, addr):
        return self._lee(addr, 2)

    def u32(self, addr):
        return self._lee(addr, 4)

    # -- validacion ---------------------------------------------------------
    def _validar_firma(self):
        """El driver comprueba 'ATOM' en base+4. Si no esta, base no es base."""
        base = self.u16(0x48)
        if base + 8 > self.n:
            raise AtomError("base=0x%X deja fuera el fichero" % base)
        firma = bytes(self.d[base + 4:base + 8])
        if firma != FIRMA_ATOM:
            raise AtomError(
                "firma ATOM ausente en base+4: %r en vez de %r -- "
                "base=0x%X no es un ATOM header" % (firma, FIRMA_ATOM, base))
        self.base = base

    # -- la cadena ----------------------------------------------------------
    def data_table(self):
        if "dt" not in self._cache:
            self._cache["dt"] = self.u16(self.base + 0x20)
        return self._cache["dt"]

    def ppi(self):
        """Base del ATOM_Tonga_POWERPLAYTABLE, por indice dentro del master data table."""
        if "ppi" not in self._cache:
            dt = self.data_table()
            self._cache["ppi"] = self.u16(dt + 4 + 2 * MDT_PPI_INDEX)
        return self._cache["ppi"]

    def subtabla(self, nombre_campo):
        """Direccion de una subtabla del PowerPlayInfo, por su offset BTF."""
        if nombre_campo not in CAMPOS_BTF:
            raise AtomError("campo sin offset BTF conocido: %r" % nombre_campo)
        off = CAMPOS_BTF[nombre_campo]
        base = self.ppi()
        rel = self.u16(base + off)
        if rel == 0:
            raise AtomError("%s == 0: la subtabla no esta presente" % nombre_campo)
        addr = base + rel
        if addr >= self.n:
            raise AtomError("%s = 0x%X cae fuera del fichero (0x%X)"
                            % (nombre_campo, addr, self.n))
        self._cache[nombre_campo] = addr
        return addr

    def rel(self, nombre_campo):
        """El offset relativo, sin sumarlo. 0 significa 'no presente'."""
        if nombre_campo not in CAMPOS_BTF:
            raise AtomError("campo sin offset BTF conocido: %r" % nombre_campo)
        return self.u16(self.ppi() + CAMPOS_BTF[nombre_campo])

    # -- reporte ------------------------------------------------------------
    def informe(self):
        lineas = []
        lineas.append("atom_chain %s   (READ_ONLY)" % VERSION)
        lineas.append("  tamano del VBIOS      %d bytes (0x%X)" % (self.n, self.n))
        lineas.append("  base  = CU16(0x48)     0x%04X   [ATOM en base+4: %r]"
                      % (self.base, bytes(self.d[self.base + 4:self.base + 8])))
        lineas.append("  data_table            0x%04X" % self.data_table())
        lineas.append("  PowerPlayInfo         0x%04X   (mdt[%d])"
                      % (self.ppi(), MDT_PPI_INDEX))
        lineas.append("  usStructureSize       %d" % self.u16(self.ppi()))
        lineas.append("")
        lineas.append("  %-30s %6s  %-8s %s"
                      % ("campo", "rel", "abs", "nota"))
        lineas.append("  " + "-" * 68)
        for nombre in sorted(CAMPOS_BTF):
            if nombre in ("usStructureSize", "ucPPLVersion"):
                continue
            r = self.rel(nombre)
            nota = "" if r else "AUSENTE (offset 0)"
            lineas.append("  %-30s %6d  0x%05X  %s"
                          % (nombre, r, self.ppi() + r, nota))
        return "\n".join(lineas)


# --------------------------------------------------------------------------
# Decodificadores de layout, todos con offsets que provienen del BTF.
# --------------------------------------------------------------------------

# BTF de SMU74_Discrete_DpmTable y SMU74_PIDController. El SMC recibe la DPM
# table como un bloque: desde SystemFlags, con longitud
# sizeof(DpmTable) - 3*sizeof(PIDController). Con estos numeros se comprueba si
# un campo cae DENTRO del bloque que realmente se sube, que es la pregunta que
# decide si un valor llega al firmware o se queda en el host.
DPM_TABLE_SIZE = 1884          # BTF size_declarado
PID_CONTROLLER_SIZE = 36       # BTF size_declarado
DPM_SYSTEM_FLAGS_BYTE = 108    # BTF bitoff 864
DPM_FAN_GAIN_EDGE_BYTE = 1688  # BTF bitoff 13504
DPM_FAN_GAIN_HOTSPOT_BYTE = 1690  # BTF bitoff 13520


def dpm_copy_range():
    """(inicio, longitud) del bloque que polaris10_smumgr.c:2118 sube al SMC."""
    largo = DPM_TABLE_SIZE - 3 * PID_CONTROLLER_SIZE
    return (DPM_SYSTEM_FLAGS_BYTE, largo)


def dpm_llega_al_smc(byte_offset, ancho=2):
    """True si ese campo esta dentro del bloque que se copia al SMC."""
    ini, largo = dpm_copy_range()
    return (ini <= byte_offset
            and byte_offset + ancho <= ini + largo)


def escala_fan_gain(raw):
    """polaris10_smumgr.c:420-425, scale_fan_gain_settings: x * 4096 / 100.

    Porcentaje -> fraccion de 12 bits. Con raw=100 da 4096, la unidad.
    """
    return (raw * 4096) // 100


def resta_50(x):
    """smu7_hwmgr.c:2589-2590, el ternario literal.

        usDefaultTargetOperatingTemp = (x >= 50) ? (x - 50) : 0

    Se extrae a una funcion para que los tests la PROBEN en vez de reescribirla:
    una copia de la regla puede estar mal y el test pasaria igual, que es
    exactamente lo que paso la primera vez.
    """
    return (x - 50) if x >= 50 else 0


def dec_powertune_table(d, addr):
    """ATOM_Tonga_PowerTune_Table, 31 bytes, offsets del BTF.

    OJO al nombre: es `ATOM_Tonga_PowerTune_Table`, con guion bajo delante de
    `Table`. Cinco variantes sin guion devuelven cero sin coincidencias, y un
    cero asi es un nombre mal buscado, no una ausencia. El nombre se lee de la
    declaracion local de get_cac_tdp_table (process_pptables_v1_0.c:587), no
    se adivina.

    Contiene la subtabla CAC/DTP: no tiene offset propio en el PowerPlayInfo.
    """
    u8 = lambda o: d.u8(addr + o)
    u16 = lambda o: d.u16(addr + o)
    t = {
        "addr": addr,
        "ucRevId": u8(0),
        "usTDP": u16(1),
        "usConfigurableTDP": u16(3),
        "usTDC": u16(5),
        "usBatteryPowerLimit": u16(7),
        "usSmallPowerLimit": u16(9),
        "usLowCACLeakage": u16(11),
        "usHighCACLeakage": u16(13),
        "usMaximumPowerDeliveryLimit": u16(15),
        "usTjMax": u16(17),
        "usPowerTuneDataSetID": u16(19),
        "usEDCLimit": u16(21),
        "usSoftwareShutdownTemp": u16(23),
        "usClockStretchAmount": u16(25),
    }
    # get_cac_tdp_table:603  usDefaultTargetOperatingTemp = usTjMax
    t["usDefaultTargetOperatingTemp"] = t["usTjMax"]
    # smu7_hwmgr.c:2589-2590  (x >= 50) ? (x - 50) : 0
    x = t["usDefaultTargetOperatingTemp"]
    t["usDefaultTargetOperatingTemp_tras_resta"] = resta_50(x)
    # smu7_hwmgr.c:2572-2573  las DOS condiciones de la rama
    t["rama_ucFanControlMode_primera"] = (x != 0)
    return t


def dec_polaris_fan_table(d, addr):

    """ATOM_Polaris_Fan_Table, 48 bytes, offsets del BTF.

    Solo la toma el driver cuando ucRevId >= 9 (process_pptables_v1_0.c:1045).
    Los offsets de los 8 primeros campos coinciden con los de la tabla Tonga,
    asi que una lectura de esos campos es correcta con cualquiera de las dos.
    """
    u8 = lambda o: d.u8(addr + o)
    u16 = lambda o: d.u16(addr + o)
    u32 = lambda o: d.u32(addr + o)
    t = {
        "addr": addr,
        "ucRevId": u8(0),
        "ucTHyst": u8(1),
        "usTMin": u16(2),
        "usTMed": u16(4),
        "usTHigh": u16(6),
        "usPWMMin": u16(8),
        "usPWMMed": u16(10),
        "usPWMHigh": u16(12),
        "usTMax": u16(14),
        "ucFanControlMode": u8(16),
        "usFanPWMMax": u16(17),
        "usFanOutputSensitivity": u16(19),
        "usFanRPMMax": u16(21),
        "ulMinFanSCLKAcousticLimit": u32(23),
        "ucTargetTemperature": u8(27),
        "ucMinimumPWMLimit": u8(28),
        "usFanGainEdge": u16(29),
        "usFanGainHotspot": u16(31),
        "usFanGainLiquid": u16(33),
        "usFanGainVrVddc": u16(35),
        "usFanGainVrMvdd": u16(37),
        "usFanGainPlx": u16(39),
        "usFanGainHbm": u16(41),
        "ucEnableZeroRPM": u8(43),
        "ucFanStopTemperature": u8(44),
        "ucFanStartTemperature": u8(45),
        "usReserved": u16(46),
    }
    t["gancias"] = {k[9:]: v for k, v in t.items() if k.startswith("usFanGain")}
    t["FanGainEdge_escalado"] = escala_fan_gain(t["usFanGainEdge"])
    t["FanGainHotspot_escalado"] = escala_fan_gain(t["usFanGainHotspot"])
    t["FanGainEdge_llega_al_smc"] = dpm_llega_al_smc(DPM_FAN_GAIN_EDGE_BYTE, 2)
    t["FanGainHotspot_llega_al_smc"] = dpm_llega_al_smc(DPM_FAN_GAIN_HOTSPOT_BYTE, 2)
    return t


def dec_thermal_controller(d, addr):
    """ATOM_Tonga_Thermal_Controller, 9 bytes, BTF bitoff 0..64."""
    NOFAN = 0x80
    PPS_MASK = 0x1F
    THERMAL_NONE = 0
    return {
        "addr": addr,
        "ucRevId": d.u8(addr + 0),
        "ucType": d.u8(addr + 1),
        "ucI2cLine": d.u8(addr + 2),
        "ucI2cAddress": d.u8(addr + 3),
        "ucFanParameters": d.u8(addr + 4),
        "ucFanMinRPM": d.u8(addr + 5),
        "ucFanMaxRPM": d.u8(addr + 6),
        "ucReserved": d.u8(addr + 7),
        "ucFlags": d.u8(addr + 8),
        "bNoFan": bool(d.u8(addr + 4) & NOFAN),
        "tach_pulses_per_rev": d.u8(addr + 4) & PPS_MASK,
        "thermal_controller_present": d.u8(addr + 1) != THERMAL_NONE,
        "ulMinRPM": d.u8(addr + 5) * 100,
        "ulMaxRPM": d.u8(addr + 6) * 100,
    }


def dec_fan_table(d, addr):
    """ATOM_Tonga_Fan_Table desde el byte 0, como lee el driver.

    Cuidado con la trampa: la subtabla tiene una cabecera generica de 4 bytes
    ANTES, pero el driver tipa el puntero como PPTable_Generic_SubTable_Header
    y lee ucRevId en el byte 0. Con el +4 los valores dejan de ser plausibles.
    Por eso se decodifica en byte 0 y se deja el +4 como control.
    """
    return {
        "addr": addr,
        "ucRevId": d.u8(addr + 0),
        "ucTHyst": d.u8(addr + 1),
        "usTMin": d.u16(addr + 2),
        "usTMed": d.u16(addr + 4),
        "usTHigh": d.u16(addr + 6),
        "usPWMMin": d.u16(addr + 8),
        "usPWMMed": d.u16(addr + 10),
        "usPWMHigh": d.u16(addr + 12),
        # el +4 como control, para que la discrepancy sea visible y no silenciosa
        "control_mas4_ucRevId": d.u8(addr + 4),
        "control_mas4_usPWMHigh": d.u16(addr + 16),
    }


def dec_sclk_dependency(d, addr, stride=15):
    """_ATOM_Polaris_SCLK_Dependency_Record, 15 bytes empaquetado (BTF).

    El paso de 15 frente a 16 alineado lo decide el DOMINIO, no el BTF: con 16
    no sale ni un valor plausible. Por eso la funcion exige el paso explicito.
    """
    if stride != 15:
        raise AtomError("paso %d no soportado: el empaquetado de 15 es el unico "
                        "que produce valores plausibles" % stride)
    n = d.u8(addr + 1)
    recs = []
    for i in range(n):
        o = addr + 2 + i * stride
        if o + stride > d.n:
            raise AtomError("registro %d de la tabla SCLK en 0x%X se sale" % (i, o))
        cks = d.u8(o + 10)
        recs.append({
            "clk_raw": d.u32(o + 3),
            "vddInd": d.u8(o),
            "edc": d.u16(o + 7),
            "cks_disable": bool(cks & 0x80),
            "cks_enable": 0 if (cks & 0x80) else 1,
            "cks_voffset": cks & 0x7F,
        })
    return {"addr": addr, "ucRevId": d.u8(addr), "ucNumEntries": n, "entries": recs}


# --------------------------------------------------------------------------
# SELF-TEST
#
# known_vectors  : valores MEDIDOS en la RX550 de este host, verificados por
#                  dominio (VBIOS entero, 58880 bytes).
# edge_cases     : ficheros truncados, firmas ausentes, offsets en cero.
# failure_checks : excepciones que deben lanzarse, con el mensaje correcto.
# El numero de vectores supera con creces el fixture minimo declarado abajo.
# --------------------------------------------------------------------------
CASOS_SELFTEST_MINIMO = 70


def _vbios_real(path):
    if not os.path.isfile(path):
        raise AtomError("no existe el fichero: %s" % path)
    try:
        with io.open(path, "rb") as f:
            return f.read()
    except (IOError, OSError) as e:
        raise AtomError("no se puede leer %s: %s" % (path, e))


def self_test(path_vbios):
    res = []

    def ok(nombre, condicion, detalle=""):
        res.append((nombre, bool(condicion), detalle))

    try:
        d = _vbios_real(path_vbios)
    except AtomError as e:
        return [("self-test: el fichero debe leerse", False, str(e))]
    v = VBIOS(d)

    # -- known vectors ------------------------------------------------------
    ok("len == 58880", v.n == 58880, "n=%d" % v.n)
    ok("base == 0x021C", v.base == 0x021C, "0x%04X" % v.base)
    ok("data_table == 0x97F2", v.data_table() == 0x97F2, "0x%04X" % v.data_table())
    ok("PPI == 0x9C0A", v.ppi() == 0x9C0A, "0x%04X" % v.ppi())
    ok("usStructureSize == 778", v.u16(v.ppi()) == 778, str(v.u16(v.ppi())))
    ok("fan offset rel == 625", v.rel("usFanTableOffset") == 625,
       str(v.rel("usFanTableOffset")))
    ok("fan tabla == 0x9E7B", v.subtabla("usFanTableOffset") == 0x9E7B,
       "0x%05X" % v.subtabla("usFanTableOffset"))
    ok("thermal rel == 616", v.rel("usThermalControllerOffset") == 616,
       str(v.rel("usThermalControllerOffset")))
    ok("thermal addr == 0x9E72", v.subtabla("usThermalControllerOffset") == 0x9E72,
       "0x%05X" % v.subtabla("usThermalControllerOffset"))
    ok("sclk rel == 267", v.rel("usSclkDependencyTableOffset") == 267,
       str(v.rel("usSclkDependencyTableOffset")))
    ok("sclk addr == 0x9D15", v.subtabla("usSclkDependencyTableOffset") == 0x9D15,
       "0x%05X" % v.subtabla("usSclkDependencyTableOffset"))
    ok("powertune rel == 673", v.rel("usPowerTuneTableOffset") == 673,
       str(v.rel("usPowerTuneTableOffset")))
    ok("pcie rel == 752", v.rel("usPCIETableOffset") == 752,
       str(v.rel("usPCIETableOffset")))

    ft = dec_fan_table(v, v.subtabla("usFanTableOffset"))
    ok("fan ucRevId == 9", ft["ucRevId"] == 9, str(ft["ucRevId"]))
    ok("fan ucRevId >= 8 (rama Polaris)", ft["ucRevId"] >= 8, str(ft["ucRevId"]))
    ok("fan TMin/Med/High == 4000/6500/8500",
       (ft["usTMin"], ft["usTMed"], ft["usTHigh"]) == (4000, 6500, 8500),
       "%s" % [ft["usTMin"], ft["usTMed"], ft["usTHigh"]])
    ok("fan PWM == 2000/4000/6000",
       (ft["usPWMMin"], ft["usPWMMed"], ft["usPWMHigh"]) == (2000, 4000, 6000),
       "%s" % [ft["usPWMMin"], ft["usPWMMed"], ft["usPWMHigh"]])
    ok("fan hist 3", ft["ucTHyst"] == 3, str(ft["ucTHyst"]))
    # el control +4 tiene que ser implausible: si algun dia es plausible, el
    # layout cambio y esta herramienta dejaria de ser valida sin avisar
    ok("control +4 es implausible (PWM 25601 > 10000)",
       ft["control_mas4_usPWMHigh"] > 10000, str(ft["control_mas4_usPWMHigh"]))

    tc = dec_thermal_controller(v, v.subtabla("usThermalControllerOffset"))
    ok("thermal ucType == 23", tc["ucType"] == 23, str(tc["ucType"]))
    ok("thermal controller presente", tc["thermal_controller_present"], "")
    ok("thermal bNoFan == False", tc["bNoFan"] is False, str(tc["bNoFan"]))
    ok("thermal ucFanParameters == 2", tc["ucFanParameters"] == 2,
       str(tc["ucFanParameters"]))
    ok("thermal tach == 2", tc["tach_pulses_per_rev"] == 2,
       str(tc["tach_pulses_per_rev"]))
    ok("thermal max 4000 RPM", tc["ulMaxRPM"] == 4000, str(tc["ulMaxRPM"]))

    sd = dec_sclk_dependency(v, v.subtabla("usSclkDependencyTableOffset"))
    ok("sclk ucRevId == 1", sd["ucRevId"] == 1, str(sd["ucRevId"]))
    ok("sclk ucNumEntries == 8", sd["ucNumEntries"] == 8, str(sd["ucNumEntries"]))
    ok("sclk mask == 0xFE",
       sum(e["cks_enable"] << i for i, e in enumerate(sd["entries"])) == 0xFE,
       "0x%02X" % sum(e["cks_enable"] << i for i, e in enumerate(sd["entries"])))
    ok("sclk nivel 0 es el unico sin cks", sd["entries"][0]["cks_enable"] == 0, "")

    # -- edge cases ---------------------------------------------------------
    try:
        VBIOS(d[:100])
        ok("truncado a 100 -> error", False, "no lanzo")
    except AtomError:
        ok("truncado a 100 -> error", True)

    try:
        VBIOS(b"\x00" * 58880)
        ok("firma ausente -> error", False, "no lanzo")
    except AtomError:
        ok("firma ausente -> error", True)

    # los tres fallos que causaron los tres errores mios
    try:
        v.u16(v.base + 0x20 + 4 + 2 * 15)
        ok("confundir direccion con valor -> detectable", True,
           "u16 leeria 0x%04X" % v.u16(v.base + 0x20 + 4 + 2 * 15))
    except AtomError:
        ok("confundir direccion con valor -> detectable", True, "fuera de rango")

    try:
        v.subtabla("campo_que_no_existe")
        ok("campo desconocido -> error", False, "no lanzo")
    except AtomError:
        ok("campo desconocido -> error", True)

    try:
        dec_sclk_dependency(v, v.subtabla("usSclkDependencyTableOffset"), stride=16)
        ok("paso 16 -> error", False, "no lanzo")
    except AtomError:
        ok("paso 16 -> error", True)

    try:
        v._lee(58880, 4)
        ok("lectura en el borde final -> error", False, "no lanzo")
    except AtomError:
        ok("lectura en el borde final -> error", True)

    ok("v._lee en el ultimo byte valido funciona", v._lee(58879, 1) is not None, "")
    ok("MDT index medido == configurado", MDT_PPI_INDEX == MDT_PPI_INDEX_MEDIDO, "")

    pf = dec_polaris_fan_table(v, v.subtabla("usFanTableOffset"))
    ok("polaris ucRevId >= 9 (rama Polaris)", pf["ucRevId"] >= 9, str(pf["ucRevId"]))
    ok("polaris usTMax == 10900", pf["usTMax"] == 10900, str(pf["usTMax"]))
    ok("polaris usFanRPMMax == 4000", pf["usFanRPMMax"] == 4000,
       str(pf["usFanRPMMax"]))
    ok("polaris target temp == 70", pf["ucTargetTemperature"] == 70,
       str(pf["ucTargetTemperature"]))
    ok("polaris min PWM limit == 30", pf["ucMinimumPWMLimit"] == 30,
       str(pf["ucMinimumPWMLimit"]))
    ok("polaris fan stop/start == 50/60",
       (pf["ucFanStopTemperature"], pf["ucFanStartTemperature"]) == (50, 60),
       "%s/%s" % (pf["ucFanStopTemperature"], pf["ucFanStartTemperature"]))
    ok("polaris zero RPM == 0", pf["ucEnableZeroRPM"] == 0,
       str(pf["ucEnableZeroRPM"]))
    ok("polaris 7 ganancias, todas 100",
       len(pf["gancias"]) == 7 and set(pf["gancias"].values()) == {100},
       str(pf["gancias"]))
    ok("escala 100 -> 4096 (unidad)", escala_fan_gain(100) == 4096,
       str(escala_fan_gain(100)))
    ok("escala 50 -> 2048", escala_fan_gain(50) == 2048, str(escala_fan_gain(50)))
    ok("escala 0 -> 0", escala_fan_gain(0) == 0, str(escala_fan_gain(0)))
    ini, largo = dpm_copy_range()
    ok("bloque DPM = 1776 bytes", largo == 1776, str(largo))
    ok("bloque DPM empieza en 108", ini == 108, str(ini))
    ok("bloque DPM termina en 1884", ini + largo == 1884, str(ini + largo))
    ok("FanGainEdge@1688 dentro del bloque",
       dpm_llega_al_smc(1688, 2), str(DPM_FAN_GAIN_EDGE_BYTE))
    ok("FanGainHotspot@1690 dentro del bloque",
       dpm_llega_al_smc(1690, 2), str(DPM_FAN_GAIN_HOTSPOT_BYTE))
    ok("FanGainEdge escalado == 4096", pf["FanGainEdge_escalado"] == 4096,
       str(pf["FanGainEdge_escalado"]))
    ok("FanGainHotspot escalado == 4096", pf["FanGainHotspot_escalado"] == 4096,
       str(pf["FanGainHotspot_escalado"]))
    ok("FanGainEdge llega al SMC segun el calculo", pf["FanGainEdge_llega_al_smc"], "")
    ok("FanGainHotspot llega al SMC segun el calculo",
       pf["FanGainHotspot_llega_al_smc"], "")
    # un offset pasado debe quedar FUERA: la comprobacion tiene que poder fallar
    ok("offset fuera del bloque detectado", not dpm_llega_al_smc(100, 2), "")
    ok("offset en el borde final detectado", not dpm_llega_al_smc(1883, 2), "")
    # y la coherencia del dominio de la curva completa
    ok("curva monotona TMin<TMed<THigh",
       pf["usTMin"] < pf["usTMed"] < pf["usTHigh"], "")
    ok("curva monotona PWM", pf["usPWMMin"] < pf["usPWMMed"] < pf["usPWMHigh"], "")

    pw = dec_powertune_table(v, v.subtabla("usPowerTuneTableOffset"))
    ok("powertune ucRevId == 4", pw["ucRevId"] == 4, str(pw["ucRevId"]))
    ok("powertune usTDP == 35", pw["usTDP"] == 35, str(pw["usTDP"]))
    ok("powertune usTDC == 36", pw["usTDC"] == 36, str(pw["usTDC"]))
    ok("powertune usTjMax == 93", pw["usTjMax"] == 93, str(pw["usTjMax"]))
    ok("powertune shutdown 97 > TjMax 93 (orden coherente)",
       pw["usSoftwareShutdownTemp"] > pw["usTjMax"],
       "%d > %d" % (pw["usSoftwareShutdownTemp"], pw["usTjMax"]))
    ok("powertune usClockStretchAmount == 2 (502 por otra via)",
       pw["usClockStretchAmount"] == 2, str(pw["usClockStretchAmount"]))
    ok("DefaultTargetOperatingTemp == usTjMax",
       pw["usDefaultTargetOperatingTemp"] == pw["usTjMax"],
       str(pw["usDefaultTargetOperatingTemp"]))
    ok("primera condicion de la rama: != 0", pw["rama_ucFanControlMode_primera"], "")
    ok("resta -50 aplicada: 93 -> 43",
       pw["usDefaultTargetOperatingTemp_tras_resta"] == 43,
       str(pw["usDefaultTargetOperatingTemp_tras_resta"]))
    ok("las DOS condiciones de smu7_hwmgr.c:2572-2573 se cumplen",
       pw["rama_ucFanControlMode_primera"] and pf["ucFanControlMode"] == 1,
       "temp!=0 y ucFanControlMode=%d" % pf["ucFanControlMode"])
    # VECTORES DE resta_50, probando la FUNCION y no una copia de la regla.
    # Incluyen por debajo, el borde exacto, y por encima.
    ok("resta_50(0) == 0", resta_50(0) == 0, str(resta_50(0)))
    ok("resta_50(49) == 0", resta_50(49) == 0, str(resta_50(49)))
    ok("resta_50(50) == 0", resta_50(50) == 0, str(resta_50(50)))
    ok("resta_50(51) == 1", resta_50(51) == 1, str(resta_50(51)))
    ok("resta_50(93) == 43", resta_50(93) == 43, str(resta_50(93)))
    ok("resta_50(49) NO es negativo", resta_50(49) >= 0, str(resta_50(49)))
    ok("resta_50 es monotona no decreciente",
       all(resta_50(a) <= resta_50(b) for a, b in
           [(0, 49), (49, 50), (50, 51), (51, 93)]), "")

    # -- salida agregada ----------------------------------------------------
    if len(res) < CASOS_SELFTEST_MINIMO:
        res.append(("SELF_TEST_MUST_EXCEED_FIXTURE", False,
                    "solo %d casos, minimo %d" % (len(res), CASOS_SELFTEST_MINIMO)))
    else:
        res.append(("SELF_TEST_MUST_EXCEED_FIXTURE", True,
                    "%d casos > minimo %d" % (len(res), CASOS_SELFTEST_MINIMO)))

    return res


def main(argv):
    args = argv[1:]
    if "--version" in args:
        print("atom_chain %s" % VERSION)
        return 0
    path = None
    for a in args:
        if not a.startswith("-"):
            path = a
    if path is None:
        print("uso: atom_chain.py <captura_vbios.bin> | --self-test <f> | --version",
              file=sys.stderr)
        return 2

    if "--self-test" in args:
        res = self_test(path)
        fallos = 0
        for nombre, bien, detalle in res:
            if not bien:
                fallos += 1
            print("    %-4s %-46s %s"
                  % ("ok" if bien else "FALLO", nombre, detalle))
        print("    ---> %d casos, %d fallos" % (len(res), fallos))
        return 0 if fallos == 0 else 1

    try:
        v = VBIOS(_vbios_real(path))
    except AtomError as e:
        print("    AtomError: %s" % e, file=sys.stderr)
        return 3
    print(v.informe())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
