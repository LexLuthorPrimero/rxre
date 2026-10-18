typedef enum {
  PPCLK_GFXCLK,
  PPCLK_VCLK,
  PPCLK_DCLK,
  PPCLK_SOCCLK,
  PPCLK_UCLK,
  PPCLK_FCLK,
  PPCLK_COUNT,
} PPCLK_e;

typedef enum {
  POWER_SOURCE_AC,
  POWER_SOURCE_DC,
  POWER_SOURCE_COUNT,
} POWER_SOURCE_e;

typedef enum {
  AVFS_VOLTAGE_GFX = 0,
  AVFS_VOLTAGE_SOC,
  AVFS_VOLTAGE_COUNT,
} AVFS_VOLTAGE_TYPE_e;

typedef struct {
  uint32_t m;  // store in IEEE float format in this variable
  uint32_t b;  // store in IEEE float format in this variable
} LinearInt_t;

typedef struct {
  uint32_t a;  // store in IEEE float format in this variable
  uint32_t b;  // store in IEEE float format in this variable
  uint32_t c;  // store in IEEE float format in this variable
} QuadraticInt_t;

typedef struct {
  uint8_t   Enabled;
  uint8_t   Speed;
  uint8_t   Padding[2];
  uint32_t  SlaveAddress;
  uint8_t   ControllerPort;
  uint8_t   ControllerName;
  uint8_t   ThermalThrotter;
  uint8_t   I2cProtocol;
} I2cControllerConfig_t;

typedef struct {
  uint8_t        VoltageMode;         // 0 - AVFS only, 1- min(AVFS,SS), 2-SS only
  uint8_t        SnapToDiscrete;      // 0 - Fine grained DPM, 1 - Discrete DPM
  uint8_t        NumDiscreteLevels;   // Set to 2 (Fmin, Fmax) when using fine grained DPM, otherwise set to # discrete levels used
  uint8_t        padding;
  LinearInt_t    ConversionToAvfsClk; // Transfer function to AVFS Clock (GHz->GHz)
  QuadraticInt_t SsCurve;             // Slow-slow curve (GHz->V)
  uint16_t       SsFmin;              // Fmin for SS curve. If SS curve is selected, will use V@SSFmin for F <= Fmin
  uint16_t       Padding16;
} DpmDescriptor_t;

#define NUM_DCLK_DPM_LEVELS (8)

#define NUM_FCLK_DPM_LEVELS (8)

#define NUM_GFXCLK_DPM_LEVELS (16)

#define NUM_I2C_CONTROLLERS (8)

#define NUM_MP0CLK_DPM_LEVELS (2)

#define NUM_SOCCLK_DPM_LEVELS (8)

#define NUM_UCLK_DPM_LEVELS (4)

#define NUM_VCLK_DPM_LEVELS (8)

#define NUM_XGMI_LEVELS (2)

#define NUM_XGMI_PSTATE_LEVELS (4)

/* SUSTITUCION DECLARADA: ver la docstring. */
#define PPT_THROTTLER_COUNT 4
typedef struct { uint32_t a; uint32_t b; uint32_t c; } DroopInt_t;


#pragma pack(push, 1)
typedef struct {
  uint32_t Version;

  // SECTION: Feature Enablement
  uint32_t FeaturesToRun[2];

  // SECTION: Infrastructure Limits
  uint16_t SocketPowerLimitAc[PPT_THROTTLER_COUNT];
  uint16_t SocketPowerLimitAcTau[PPT_THROTTLER_COUNT];
  uint16_t TdcLimitSoc;             // Amps
  uint16_t TdcLimitSocTau;          // Time constant of LPF in ms
  uint16_t TdcLimitGfx;             // Amps
  uint16_t TdcLimitGfxTau;          // Time constant of LPF in ms

  uint16_t TedgeLimit;              // Celcius
  uint16_t ThotspotLimit;           // Celcius
  uint16_t TmemLimit;               // Celcius
  uint16_t Tvr_gfxLimit;            // Celcius
  uint16_t Tvr_memLimit;            // Celcius
  uint16_t Tvr_socLimit;            // Celcius
  uint32_t FitLimit;                // Failures in time (failures per million parts over the defined lifetime)

  uint16_t PpmPowerLimit;           // Switch this this power limit when temperature is above PpmTempThreshold
  uint16_t PpmTemperatureThreshold;

  // SECTION: Throttler settings
  uint32_t ThrottlerControlMask;   // See Throtter masks defines

  // SECTION: ULV Settings
  uint16_t  UlvVoltageOffsetGfx; // In mV(Q2)
  uint16_t  UlvPadding;          // Padding

  uint8_t  UlvGfxclkBypass;  // 1 to turn off/bypass Gfxclk during ULV, 0 to leave Gfxclk on during ULV
  uint8_t  Padding234[3];

  // SECTION: Voltage Control Parameters
  uint16_t     MinVoltageGfx;     // In mV(Q2) Minimum Voltage ("Vmin") of VDD_GFX
  uint16_t     MinVoltageSoc;     // In mV(Q2) Minimum Voltage ("Vmin") of VDD_SOC
  uint16_t     MaxVoltageGfx;     // In mV(Q2) Maximum Voltage allowable of VDD_GFX
  uint16_t     MaxVoltageSoc;     // In mV(Q2) Maximum Voltage allowable of VDD_SOC

  uint16_t     LoadLineResistanceGfx;   // In mOhms with 8 fractional bits
  uint16_t     LoadLineResistanceSoc;   // In mOhms with 8 fractional bits

  //SECTION: DPM Config 1
  DpmDescriptor_t DpmDescriptor[PPCLK_COUNT];

  uint16_t       FreqTableGfx      [NUM_GFXCLK_DPM_LEVELS  ];     // In MHz
  uint16_t       FreqTableVclk     [NUM_VCLK_DPM_LEVELS    ];     // In MHz
  uint16_t       FreqTableDclk     [NUM_DCLK_DPM_LEVELS    ];     // In MHz
  uint16_t       FreqTableSocclk   [NUM_SOCCLK_DPM_LEVELS  ];     // In MHz
  uint16_t       FreqTableUclk     [NUM_UCLK_DPM_LEVELS    ];     // In MHz
  uint16_t       FreqTableFclk     [NUM_FCLK_DPM_LEVELS    ];     // In MHz

  uint32_t       Paddingclks[16];

  // SECTION: DPM Config 2
  uint16_t       Mp0clkFreq        [NUM_MP0CLK_DPM_LEVELS];       // in MHz
  uint16_t       Mp0DpmVoltage     [NUM_MP0CLK_DPM_LEVELS];       // mV(Q2)

  // GFXCLK DPM
  uint16_t        GfxclkFidle;          // In MHz
  uint16_t        GfxclkSlewRate;       // for PLL babystepping???
  uint8_t         Padding567[4];
  uint16_t        GfxclkDsMaxFreq;      // In MHz
  uint8_t         GfxclkSource;         // 0 = PLL, 1 = AFLL
  uint8_t         Padding456;

  // GFXCLK Thermal DPM (formerly 'Boost' Settings)
  uint16_t     EnableTdpm;
  uint16_t     TdpmHighHystTemperature;
  uint16_t     TdpmLowHystTemperature;
  uint16_t     GfxclkFreqHighTempLimit; // High limit on GFXCLK when temperature is high, for reliability.

  // SECTION: Fan Control
  uint16_t     FanStopTemp;          //Celcius
  uint16_t     FanStartTemp;         //Celcius

  uint16_t     FanGainEdge;
  uint16_t     FanGainHotspot;
  uint16_t     FanGainVrGfx;
  uint16_t     FanGainVrSoc;
  uint16_t     FanGainVrMem;
  uint16_t     FanGainHbm;
  uint16_t     FanPwmMin;
  uint16_t     FanAcousticLimitRpm;
  uint16_t     FanThrottlingRpm;
  uint16_t     FanMaximumRpm;
  uint16_t     FanTargetTemperature;
  uint16_t     FanTargetGfxclk;
  uint8_t      FanZeroRpmEnable;
  uint8_t      FanTachEdgePerRev;
  uint8_t      FanTempInputSelect;
  uint8_t      padding8_Fan;

  // The following are AFC override parameters. Leave at 0 to use FW defaults.
  int16_t      FuzzyFan_ErrorSetDelta;
  int16_t      FuzzyFan_ErrorRateSetDelta;
  int16_t      FuzzyFan_PwmSetDelta;
  uint16_t     FuzzyFan_Reserved;


  // SECTION: AVFS
  // Overrides
  uint8_t           OverrideAvfsGb[AVFS_VOLTAGE_COUNT];
  uint8_t           Padding8_Avfs[2];

  QuadraticInt_t    qAvfsGb[AVFS_VOLTAGE_COUNT];              // GHz->V Override of fused curve
  DroopInt_t        dBtcGbGfxPll;       // GHz->V BtcGb
  DroopInt_t        dBtcGbGfxAfll;        // GHz->V BtcGb
  DroopInt_t        dBtcGbSoc;            // GHz->V BtcGb
  LinearInt_t       qAgingGb[AVFS_VOLTAGE_COUNT];          // GHz->V

  QuadraticInt_t    qStaticVoltageOffset[AVFS_VOLTAGE_COUNT]; // GHz->V

  uint16_t          DcTol[AVFS_VOLTAGE_COUNT];            // mV Q2

  uint8_t           DcBtcEnabled[AVFS_VOLTAGE_COUNT];
  uint8_t           Padding8_GfxBtc[2];

  uint16_t          DcBtcMin[AVFS_VOLTAGE_COUNT];       // mV Q2
  uint16_t          DcBtcMax[AVFS_VOLTAGE_COUNT];       // mV Q2

  uint16_t          DcBtcGb[AVFS_VOLTAGE_COUNT];        // mV Q2

  // SECTION: XGMI
  uint8_t           XgmiDpmPstates[NUM_XGMI_LEVELS]; // 2 DPM states, high and low.  0-P0, 1-P1, 2-P2, 3-P3.
  uint8_t           XgmiDpmSpare[2];

  // Temperature Dependent Vmin
  uint16_t     VDDGFX_TVmin;       //Celcius
  uint16_t     VDDSOC_TVmin;       //Celcius
  uint16_t     VDDGFX_Vmin_HiTemp; // mV Q2
  uint16_t     VDDGFX_Vmin_LoTemp; // mV Q2
  uint16_t     VDDSOC_Vmin_HiTemp; // mV Q2
  uint16_t     VDDSOC_Vmin_LoTemp; // mV Q2

  uint16_t     VDDGFX_TVminHystersis; // Celcius
  uint16_t     VDDSOC_TVminHystersis; // Celcius


  // SECTION: Advanced Options
  uint32_t          DebugOverrides;
  QuadraticInt_t    ReservedEquation0;
  QuadraticInt_t    ReservedEquation1;
  QuadraticInt_t    ReservedEquation2;
  QuadraticInt_t    ReservedEquation3;

  uint16_t     MinVoltageUlvGfx; // In mV(Q2)  Minimum Voltage ("Vmin") of VDD_GFX in ULV mode
  uint16_t     PaddingUlv;       // Padding

  // Total Power configuration, use defines from PwrConfig_e
  uint8_t      TotalPowerConfig;    //0-TDP, 1-TGP, 2-TCP Estimated, 3-TCP Measured
  uint8_t      TotalPowerSpare1;
  uint16_t     TotalPowerSpare2;

  // APCC Settings
  uint16_t     PccThresholdLow;
  uint16_t     PccThresholdHigh;
  uint32_t     PaddingAPCC[6];  //FIXME pending SPEC

  // OOB Settings
  uint16_t BasePerformanceCardPower;
  uint16_t MaxPerformanceCardPower;
  uint16_t BasePerformanceFrequencyCap;   //In Mhz
  uint16_t MaxPerformanceFrequencyCap;    //In Mhz

  // Per-Part Vmin
  uint16_t VDDGFX_VminLow;        // mv Q2
  uint16_t VDDGFX_TVminLow;       //Celcius
  uint16_t VDDGFX_VminLow_HiTemp; // mv Q2
  uint16_t VDDGFX_VminLow_LoTemp; // mv Q2

  // SECTION: Reserved
  uint32_t     Reserved[7];

  // SECTION: BOARD PARAMETERS

  // SVI2 Board Parameters
  uint16_t     MaxVoltageStepGfx; // In mV(Q2) Max voltage step that SMU will request. Multiple steps are taken if voltage change exceeds this value.
  uint16_t     MaxVoltageStepSoc; // In mV(Q2) Max voltage step that SMU will request. Multiple steps are taken if voltage change exceeds this value.

  uint8_t      VddGfxVrMapping;     // Use VR_MAPPING* bitfields
  uint8_t      VddSocVrMapping;     // Use VR_MAPPING* bitfields
  uint8_t      VddMemVrMapping;     // Use VR_MAPPING* bitfields
  uint8_t      BoardVrMapping;      // Use VR_MAPPING* bitfields

  uint8_t      GfxUlvPhaseSheddingMask; // set this to 1 to set PSI0/1 to 1 in ULV mode
  uint8_t      ExternalSensorPresent; // External RDI connected to TMON (aka TEMP IN)
  uint8_t      Padding8_V[2];

  // Telemetry Settings
  uint16_t     GfxMaxCurrent;   // in Amps
  int8_t       GfxOffset;       // in Amps
  uint8_t      Padding_TelemetryGfx;

  uint16_t     SocMaxCurrent;   // in Amps
  int8_t       SocOffset;       // in Amps
  uint8_t      Padding_TelemetrySoc;

  uint16_t     MemMaxCurrent;   // in Amps
  int8_t       MemOffset;       // in Amps
  uint8_t      Padding_TelemetryMem;

  uint16_t     BoardMaxCurrent;   // in Amps
  int8_t       BoardOffset;       // in Amps
  uint8_t      Padding_TelemetryBoardInput;

  // GPIO Settings
  uint8_t      VR0HotGpio;      // GPIO pin configured for VR0 HOT event
  uint8_t      VR0HotPolarity;  // GPIO polarity for VR0 HOT event
  uint8_t      VR1HotGpio;      // GPIO pin configured for VR1 HOT event
  uint8_t      VR1HotPolarity;  // GPIO polarity for VR1 HOT event

  // GFXCLK PLL Spread Spectrum
  uint8_t      PllGfxclkSpreadEnabled;   // on or off
  uint8_t      PllGfxclkSpreadPercent;   // Q4.4
  uint16_t     PllGfxclkSpreadFreq;      // kHz

  // UCLK Spread Spectrum
  uint8_t      UclkSpreadEnabled;   // on or off
  uint8_t      UclkSpreadPercent;   // Q4.4
  uint16_t     UclkSpreadFreq;      // kHz

  // FCLK Spread Spectrum
  uint8_t      FclkSpreadEnabled;   // on or off
  uint8_t      FclkSpreadPercent;   // Q4.4
  uint16_t     FclkSpreadFreq;      // kHz

  // GFXCLK Fll Spread Spectrum
  uint8_t      FllGfxclkSpreadEnabled;   // on or off
  uint8_t      FllGfxclkSpreadPercent;   // Q4.4
  uint16_t     FllGfxclkSpreadFreq;      // kHz

  // I2C Controller Structure
  I2cControllerConfig_t  I2cControllers[NUM_I2C_CONTROLLERS];

  // Memory section
  uint32_t     MemoryChannelEnabled; // For DRAM use only, Max 32 channels enabled bit mask.

  uint8_t      DramBitWidth; // For DRAM use only.  See Dram Bit width type defines
  uint8_t      PaddingMem[3];

  // Total board power
  uint16_t     TotalBoardPower;     //Only needed for TCP Estimated case, where TCP = TGP+Total Board Power
  uint16_t     BoardPadding;

  // SECTION: XGMI Training
  uint8_t           XgmiLinkSpeed   [NUM_XGMI_PSTATE_LEVELS];
  uint8_t           XgmiLinkWidth   [NUM_XGMI_PSTATE_LEVELS];

  uint16_t          XgmiFclkFreq    [NUM_XGMI_PSTATE_LEVELS];
  uint16_t          XgmiSocVoltage  [NUM_XGMI_PSTATE_LEVELS];

  // GPIO pins for I2C communications with 2nd controller for Input Telemetry Sequence
  uint8_t      GpioI2cScl;          // Serial Clock
  uint8_t      GpioI2cSda;          // Serial Data
  uint16_t     GpioPadding;

  // Platform input telemetry voltage coefficient
  uint32_t     BoardVoltageCoeffA;    // decode by /1000
  uint32_t     BoardVoltageCoeffB;    // decode by /1000

  uint32_t     BoardReserved[7];

  // Padding for MMHUB - do not modify this
  uint32_t     MmHubPadding[8]; // SMU internal use

} PPTable_t;
