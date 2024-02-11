import math
import struct
import logging
from time import sleep
from enum import IntEnum
from sensors import Sensor
try:
    from typing import Optional

    # Used only for type annotations.
    from busio import SPI, I2C
    from digitalio import DigitalInOut

except ImportError:
    pass


#    I2C ADDRESS/BITS/SETTINGS
#    -----------------------------------------------------------------------


_CHIP_ID = 0x58
BMP280_ADDR = 0x77

class Register(IntEnum):
    """ BMP280 Register addresses """

    CHIPID = 0xD0
    DIG_T1 = 0x88
    SOFTRESET = 0xE0
    STATUS = 0xF3
    CTRL_MEAS = 0xF4
    CONFIG = 0xF5
    PRESSUREDATA = 0xF7
    TEMPDATA = 0xFA


class IIR_Filter(IntEnum):
    """
    IIR filter values

    Higher IIR filtering reduces response to rapid changes
    """
    DISABLE = 0
    X2 = 0x01
    X4 = 0x02
    X8 = 0x03
    X16 = 0x04


class Overscan(IntEnum):
    """
    Overscan register values

    Overscan combines Xn readings to reduce noise and increase resolution
    """
    DISABLE = 0x00
    X1 = 0x01
    X2 = 0x02
    X4 = 0x03
    X8 = 0x04
    X16 = 0x05


class Mode(IntEnum):
    """ mode values """
    SLEEP = 0x00
    FORCE = 0x01
    NORMAL = 0x03


class Standby(IntEnum):
    """
    standby timeconstant values
    TC_X[_Y] where X=milliseconds and Y=tenths of a millisecond
    """
    TC_0_5 = 0x00  # 0.5ms
    TC_10 = 0x06  # 10ms
    TC_20 = 0x07  # 20ms
    TC_62_5 = 0x01  # 62.5ms
    TC_125 = 0x02  # 125ms
    TC_250 = 0x03  # 250ms
    TC_500 = 0x04  # 500ms
    TC_1000 = 0x05  # 1000ms


class BMP280(Sensor):  # pylint: disable=invalid-name

    def __init__(self, i2cbus, sensor_data, addr=BMP280_ADDR, **kwargs) -> None:
        # Check device ID.
        self.logger = logging.getLogger("envmon.BMP280")
        super().__init__(i2cbus, addr, sensor_data)
        self._interval = kwargs.get("read_interval", 1.0)
        self._buffer = bytearray(4)
        chip_id = self._read_byte(Register.CHIPID)
        if _CHIP_ID != chip_id:
            self.logger.error("Failed to find BMP280! Chip ID 0x%x" % chip_id)
        # Set some reasonable defaults.
        self._iir_filter = IIR_Filter.DISABLE
        self._overscan_temperature = Overscan.X2
        self._overscan_pressure = Overscan.X16
        self._t_standby = Standby.TC_0_5
        self._mode = Mode.SLEEP
        self.reset()
        self._read_coefficients()
        self._write_ctrl_meas()
        self._write_config()
        self.sea_level_pressure = 1013.25
        """Pressure in hectoPascals at sea level. Used to calibrate `altitude`."""
        self._t_fine = None

    def shutdown(self):
        self._mode = Mode.SLEEP

    def _read_temperature(self) -> None:
        self.logger.debug("Reading Temperature")
        # perform one measurement
        if self.mode != Mode.NORMAL:
            self.mode = Mode.FORCE
            # Wait for conversion to complete
            while self._get_status() & 0x08:
                sleep(0.002)

        raw_temperature = (
            self._read24(Register.TEMPDATA) / 16
        )  # lowest 4 bits get dropped
        # print("raw temp: ", UT)
        var1 = (
            raw_temperature / 16384.0 - self._temp_calib[0] / 1024.0
        ) * self._temp_calib[1]
        # print(var1)
        var2 = (
            (raw_temperature / 131072.0 - self._temp_calib[0] / 8192.0)
            * (raw_temperature / 131072.0 - self._temp_calib[0] / 8192.0)
        ) * self._temp_calib[2]
        # print(var2)

        self._t_fine = int(var1 + var2)
        # print("t_fine: ", self.t_fine)


    def reset(self) -> None:
        """Soft reset the sensor"""
        self.logger.debug("Resetting")
        self._send_cmd(bytearray([Register.SOFTRESET, 0xB6]))
        sleep(0.004)  # Datasheet says 2ms.  Using 4ms just to be safe

    def _write_ctrl_meas(self) -> None:
        """
        Write the values to the ctrl_meas register in the device
        ctrl_meas sets the pressure and temperature data acquisition options
        """
        self.logger.debug("Setting ctrl_meas registers")
        self._send_cmd(bytearray([Register.CTRL_MEAS, self._ctrl_meas]))

    def _get_status(self) -> int:
        """Get the value from the status register in the device"""
        return self._read_byte(Register.STATUS)

    def _read_config(self) -> int:
        """Read the value from the config register in the device"""
        return self._read_byte(Register.CONFIG)

    def _write_config(self) -> None:
        """Write the value to the config register in the device"""
        normal_flag = False
        if self._mode == Mode.NORMAL:
            # Writes to the config register may be ignored while in Normal mode
            normal_flag = True
            self.mode = Mode.SLEEP  # So we switch to Sleep mode first
        self.logger.debug("Setting config registers")
        self._send_cmd(bytearray([Register.CONFIG, self._config]))
        if normal_flag:
            self.mode = Mode.NORMAL

    @property
    def mode(self) -> int:
        """
        Operation mode
        Allowed values are set in the MODE enum class
        """
        return self._mode

    @mode.setter
    def mode(self, value: int) -> None:
        if value not in Mode:
            raise ValueError("Mode '%s' not supported" % (value))
        self._mode = value
        self._write_ctrl_meas()

    @property
    def standby_period(self) -> int:
        """
        Control the inactive period when in Normal mode
        Allowed standby periods are set the STANDBY enum class
        """
        return self._t_standby

    @standby_period.setter
    def standby_period(self, value: int) -> None:
        if value not in Standby:
            raise ValueError("Standby Period '%s' not supported" % (value))
        if self._t_standby == value:
            return
        self._t_standby = value
        self._write_config()

    @property
    def overscan_temperature(self) -> int:
        """
        Temperature Oversampling
        Allowed values are set in the OVERSCAN enum class
        """
        return self._overscan_temperature

    @overscan_temperature.setter
    def overscan_temperature(self, value: int) -> None:
        if value not in Overscan:
            raise ValueError("Overscan value '%s' not supported" % (value))
        self._overscan_temperature = value
        self._write_ctrl_meas()

    @property
    def overscan_pressure(self) -> int:
        """
        Pressure Oversampling
        Allowed values are set in the OVERSCAN enum class
        """
        return self._overscan_pressure

    @overscan_pressure.setter
    def overscan_pressure(self, value: int) -> None:
        if value not in Overscan:
            raise ValueError("Overscan value '%s' not supported" % (value))
        self._overscan_pressure = value
        self._write_ctrl_meas()

    @property
    def iir_filter(self) -> int:
        """
        Controls the time constant of the IIR filter
        Allowed values are set in the IIR_Filter enum class
        """
        return self._iir_filter

    @iir_filter.setter
    def iir_filter(self, value: int) -> None:
        if value not in IIR_Filter:
            raise ValueError("IIR Filter '%s' not supported" % (value))
        self._iir_filter = value
        self._write_config()

    @property
    def _config(self) -> int:
        """Value to be written to the device's config register"""
        config = 0
        if self.mode == Mode.NORMAL:
            config += self._t_standby << 5
        if self._iir_filter:
            config += self._iir_filter << 2
        return config

    @property
    def _ctrl_meas(self) -> int:
        """Value to be written to the device's ctrl_meas register"""
        ctrl_meas = self.overscan_temperature << 5
        ctrl_meas += self.overscan_pressure << 2
        ctrl_meas += self.mode
        return ctrl_meas

    @property
    def measurement_time_typical(self) -> float:
        """Typical time in milliseconds required to complete a measurement in normal mode"""
        meas_time_ms = 1
        if self.overscan_temperature != Overscan.DISABLE:
            meas_time_ms += 2 * _BMP280_OVERSCANS.get(self.overscan_temperature)
        if self.overscan_pressure != Overscan.DISABLE:
            meas_time_ms += 2 * _BMP280_OVERSCANS.get(self.overscan_pressure) + 0.5
        return meas_time_ms

    @property
    def measurement_time_max(self) -> float:
        """Maximum time in milliseconds required to complete a measurement in normal mode"""
        meas_time_ms = 1.25
        if self.overscan_temperature != Overscan.DISABLE:
            meas_time_ms += 2.3 * _BMP280_OVERSCANS.get(self.overscan_temperature)
        if self.overscan_pressure != Overscan.DISABLE:
            meas_time_ms += 2.3 * _BMP280_OVERSCANS.get(self.overscan_pressure) + 0.575
        return meas_time_ms

    def read(self) -> float:
        ''' Intended to run from Event callback
        updates global sensordata object '''
        self._read_temperature()
        temperature_c = self._t_fine / 5120.0
        pressure_hpa = self.pressure
        self._sensor_data.temp_c = temperature_c
        self._sensor_data.pressure_hpa = pressure_hpa

    @property
    def temperature(self) -> float:
        """The compensated temperature in degrees Celsius."""
        self._read_temperature()
        return self._t_fine / 5120.0

    @property
    def pressure(self) -> Optional[float]:
        """
        The compensated pressure in hectoPascals.
        returns `None` if pressure measurement is disabled
        """

        # Algorithm from the BMP280 driver
        # https://github.com/BoschSensortec/BMP280_driver/blob/master/bmp280.c
        adc = self._read24(Register.PRESSUREDATA) / 16  # lowest 4 bits get dropped
        var1 = float(self._t_fine) / 2.0 - 64000.0
        var2 = var1 * var1 * self._pressure_calib[5] / 32768.0
        var2 = var2 + var1 * self._pressure_calib[4] * 2.0
        var2 = var2 / 4.0 + self._pressure_calib[3] * 65536.0
        var3 = self._pressure_calib[2] * var1 * var1 / 524288.0
        var1 = (var3 + self._pressure_calib[1] * var1) / 524288.0
        var1 = (1.0 + var1 / 32768.0) * self._pressure_calib[0]
        if not var1:  # avoid exception caused by division by zero
            raise ArithmeticError(
                "Invalid result possibly related to error while reading the calibration registers"
            )
        pressure = 1048576.0 - adc
        pressure = ((pressure - var2 / 4096.0) * 6250.0) / var1
        var1 = self._pressure_calib[8] * pressure * pressure / 2147483648.0
        var2 = pressure * self._pressure_calib[7] / 32768.0
        pressure = pressure + (var1 + var2 + self._pressure_calib[6]) / 16.0
        pressure /= 100

        return pressure

    @property
    def altitude(self) -> float:
        """The altitude based on the sea level pressure (:attr:`sea_level_pressure`)
        - which you must enter ahead of time)"""
        p = self.pressure  # in Si units for hPascal
        return 44330 * (1.0 - math.pow(p / self.sea_level_pressure, 0.1903))

    @altitude.setter
    def altitude(self, value: float) -> None:
        p = self.pressure  # in Si units for hPascal
        self.sea_level_pressure = p / math.pow(1.0 - value / 44330.0, 5.255)

    ####################### Internal helpers ################################

    def _read24(self, register):
        ret = 0.0
        for b in self._read_register(register, 3):
            ret *= 256
            ret += float(b & 0xFF)
        return ret

    def _read_coefficients(self) -> None:
        """Read & save the calibration coefficients"""
        coeff = self._read_register(Register.DIG_T1, 24)
        coeff = list(struct.unpack("<HhhHhhhhhhhh", bytes(coeff)))
        coeff = [float(i) for i in coeff]
        self.logger.debug("Reading calibration coefficients")
        self.logger.debug(coeff)
        # The temp_calib lines up with DIG_T# registers.
        self._temp_calib = coeff[:3]
        self._pressure_calib = coeff[3:]
        # print("%d %d %d" % (self._temp_calib[0], self._temp_calib[1], self._temp_calib[2]))
        # print("%d %d %d" % (self._pressure_calib[0], self._pressure_calib[1],
        #                     self._pressure_calib[2]))
        # print("%d %d %d" % (self._pressure_calib[3], self._pressure_calib[4],
        #                     self._pressure_calib[5]))
        # print("%d %d %d" % (self._pressure_calib[6], self._pressure_calib[7],
        #                     self._pressure_calib[8]))
