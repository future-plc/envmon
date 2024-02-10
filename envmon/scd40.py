
import time
import struct
import logging
from sensors import Sensor, SensorData
from enum import Enum
from adafruit_bus_device import i2c_device

try:
    from typing import Tuple, Union
    from busio import I2C
except ImportError:
    pass


SCD4X_DEFAULT_ADDR = 0x62

class Cmd(Enum):
    REINIT = 0x3646
    FACTORYRESET = 0x3632
    FORCEDRECAL = 0x362F
    SELFTEST = 0x3639
    DATAREADY = 0xE4B8
    STOPPERIODICMEASUREMENT = 0x3F86
    STARTPERIODICMEASUREMENT = 0x21B1
    STARTLOWPOWERPERIODICMEASUREMENT = 0x21AC
    READMEASUREMENT = 0xEC05
    SERIALNUMBER = 0x3682
    GETTEMPOFFSET = 0x2318
    SETTEMPOFFSET = 0x241D
    GETALTITUDE = 0x2322
    SETALTITUDE = 0x2427
    SETPRESSURE = 0xE000
    PERSISTSETTINGS = 0x3615
    GETASCE = 0x2313
    SETASCE = 0x2416
    MEASURESINGLESHOT = 0x219D
    MEASURESINGLESHOTRHTONLY = 0x2196


class SCD40(Sensor):
    """
    CircuitPython helper class for using the SCD4X CO2 sensor

    :param ~busio.I2C i2c_bus: The I2C bus the SCD4X is connected to.
    :param int address: The I2C device address for the sensor. Default is :const:`0x62`

    **Quickstart: Importing and using the SCD4X**

        Here is an example of using the :class:`SCD4X` class.
        First you will need to import the libraries to use the sensor

        .. code-block:: python

            import board
            import adafruit_scd4x

        Once this is done you can define your `board.I2C` object and define your sensor object

        .. code-block:: python

            i2c = board.I2C()   # uses board.SCL and board.SDA
            scd = adafruit_scd4x.SCD4X(i2c)
            scd.start_periodic_measurement()

        Now you have access to the CO2, temperature and humidity using
        the :attr:`CO2`, :attr:`temperature` and :attr:`relative_humidity` attributes

        .. code-block:: python

            if scd.data_ready:
                temperature = scd.temperature
                relative_humidity = scd.relative_humidity
                co2_ppm_level = scd.CO2

    """

    def __init__(self, i2c_bus: I2C, sensor_data: SensorData, addr: int = SCD4X_DEFAULT_ADDR) -> None:
        self.logger = logging.getLogger("envmon.SCD40")
        super().__init__(i2c_bus, addr, sensor_data)
        self._interval = 10.0
        self._buffer = bytearray(18)
        self._cmd = bytearray(2)
        self._crc_buffer = bytearray(2)

        # cached readings
        self._temperature = None
        self._relative_humidity = None
        self._co2 = None

        self.stop_periodic_measurement()

    def read(self):
        co2 = self.CO2
        rel_humidity = self.relative_humidity
        self._sensor_data.co2 = co2
        self._sensor_data.humidity = rel_humidity

    @property
    def CO2(self) -> int:  # pylint:disable=invalid-name
        """Returns the CO2 concentration in PPM (parts per million)

        .. note::
            Between measurements, the most recent reading will be cached and returned.

        """
        if self.data_ready:
            self._read_data()
        return self._co2

    @property
    def temperature(self) -> float:
        """Returns the current temperature in degrees Celsius

        .. note::
            Between measurements, the most recent reading will be cached and returned.

        """
        if self.data_ready:
            self._read_data()
        return self._temperature

    @property
    def relative_humidity(self) -> float:
        """Returns the current relative humidity in %rH.

        .. note::
            Between measurements, the most recent reading will be cached and returned.

        """
        if self.data_ready:
            self._read_data()
        return self._relative_humidity

    def reinit(self) -> None:
        """Reinitializes the sensor by reloading user settings from EEPROM."""
        self.stop_periodic_measurement()
        self._send_cmd(Cmd.REINIT, delay_ms=20)

    def factory_reset(self) -> None:
        """Resets all configuration settings stored in the EEPROM and erases the
        FRC and ASC algorithm history."""
        self.stop_periodic_measurement()
        self._send_cmd(Cmd.FACTORYRESET, delay_ms=1200)

    def force_calibration(self, target_co2: int) -> None:
        """Forces the sensor to recalibrate with a given current CO2"""
        self.stop_periodic_measurement()
        self._set_command_value(Cmd.FORCEDRECAL, target_co2)
        time.sleep(0.5)
        self._read_reply(self._buffer, 3)
        correction = struct.unpack_from(">h", self._buffer[0:2])[0]
        if correction == 0xFFFF:
            raise RuntimeError(
                "Forced recalibration failed.\
            Make sure sensor is active for 3 minutes first"
            )

    @property
    def self_calibration_enabled(self) -> bool:
        """Enables or disables automatic self calibration (ASC). To work correctly, the sensor must
        be on and active for 7 days after enabling ASC, and exposed to fresh air for at least 1 hour
        per day. Consult the manufacturer's documentation for more information.

        .. note::
            This value will NOT be saved and will be reset on boot unless
            saved with persist_settings().

        """
        self._buffer = self._read_reply(delay=1, length=3, cmd=Cmd.GETASCE)
        return self._buffer[1] == 1

    @self_calibration_enabled.setter
    def self_calibration_enabled(self, enabled: bool) -> None:
        self._set_command_value(Cmd.SETASCE, enabled)

    def self_test(self) -> None:
        """Performs a self test, takes up to 10 seconds"""
        self.stop_periodic_measurement()
        self._buffer = self._read_reply(delay_ms=10, length=3, cmd=Cmd.SELFTEST)
        if (self._buffer[0] != 0) or (self._buffer[1] != 0):
            raise RuntimeError("Self test failed")

    def _read_data(self) -> None:
        """Reads the temp/hum/co2 from the sensor and caches it"""
        self._buffer = self._read_reply(delay_ms=1, length=9, cmd=Cmd.READMEASUREMENT)
        self._co2 = (self._buffer[0] << 8) | self._buffer[1]
        temp = (self._buffer[3] << 8) | self._buffer[4]
        self._temperature = -45 + 175 * (temp / 2**16)
        humi = (self._buffer[6] << 8) | self._buffer[7]
        self._relative_humidity = 100 * (humi / 2**16)

    @property
    def data_ready(self) -> bool:
        """Check the sensor to see if new data is available"""
        self._buffer = self._read_reply(delay_ms=1, length=3, cmd=Cmd.DATAREADY)
        return not ((self._buffer[0] & 0x07 == 0) and (self._buffer[1] == 0))

    @property
    def serial_number(self) -> Tuple[int, int, int, int, int, int]:
        """Request a 6-tuple containing the unique serial number for this sensor"""
        self._send_cmd(Cmd.SERIALNUMBER, delay_ms=1)
        self._read_reply(self._buffer, 9)
        return (
            self._buffer[0],
            self._buffer[1],
            self._buffer[3],
            self._buffer[4],
            self._buffer[6],
            self._buffer[7],
        )

    def stop_periodic_measurement(self) -> None:
        """Stop measurement mode"""
        self._send_cmd(Cmd.STOPPERIODICMEASUREMENT, delay_ms=500)

    def start_periodic_measurement(self) -> None:
        """Put sensor into working mode, about 5s per measurement

        .. note::
            Only the following commands will work once in working mode:

            * :attr:`CO2 <adafruit_scd4x.SCD4X.CO2>`
            * :attr:`temperature <adafruit_scd4x.SCD4X.temperature>`
            * :attr:`relative_humidity <adafruit_scd4x.SCD4X.relative_humidity>`
            * :meth:`data_ready() <adafruit_scd4x.SCD4x.data_ready>`
            * :meth:`reinit() <adafruit_scd4x.SCD4X.reinit>`
            * :meth:`factory_reset() <adafruit_scd4x.SCD4X.factory_reset>`
            * :meth:`force_calibration() <adafruit_scd4x.SCD4X.force_calibration>`
            * :meth:`self_test() <adafruit_scd4x.SCD4X.self_test>`
            * :meth:`set_ambient_pressure() <adafruit_scd4x.SCD4X.set_ambient_pressure>`

        """
        self._send_cmd(Cmd.STARTPERIODICMEASUREMENT)

    def start_low_periodic_measurement(self) -> None:
        """Put sensor into low power working mode, about 30s per measurement. See
        :meth:`start_periodic_measurement() <adafruit_scd4x.SCD4X.start_perodic_measurement>`
        for more details.
        """
        self._send_cmd(Cmd.STARTLOWPOWERPERIODICMEASUREMENT)

    def persist_settings(self) -> None:
        """Save temperature offset, altitude offset, and selfcal enable settings to EEPROM"""
        self._send_cmd(Cmd.PERSISTSETTINGS, delay_ms=800)

    def set_ambient_pressure(self, ambient_pressure: int) -> None:
        """Set the ambient pressure in hPa at any time to adjust CO2 calculations"""
        if ambient_pressure < 0 or ambient_pressure > 65535:
            raise AttributeError("`ambient_pressure` must be from 0~65535 hPascals")
        self._set_command_value(Cmd.SETPRESSURE, ambient_pressure)

    @property
    def temperature_offset(self) -> float:
        """Specifies the offset to be added to the reported measurements to account for a bias in
        the measured signal. Value is in degrees Celsius with a resolution of 0.01 degrees and a
        maximum value of 374 C

        .. note::
            This value will NOT be saved and will be reset on boot unless saved with
            persist_settings().

        """
        self._send_cmd(Cmd.GETTEMPOFFSET, delay_ms=0.001)
        self._read_reply(self._buffer, 3)
        temp = (self._buffer[0] << 8) | self._buffer[1]
        return 175.0 * temp / 2**16

    @temperature_offset.setter
    def temperature_offset(self, offset: Union[int, float]) -> None:
        if offset > 374:
            raise AttributeError(
                "Offset value must be less than or equal to 374 degrees Celsius"
            )
        temp = int(offset * 2**16 / 175)
        self._set_command_value(Cmd.SETTEMPOFFSET, temp)

    @property
    def altitude(self) -> int:
        """Specifies the altitude at the measurement location in meters above sea level. Setting
        this value adjusts the CO2 measurement calculations to account for the air pressure's effect
        on readings.

        .. note::
            This value will NOT be saved and will be reset on boot unless saved with
            persist_settings().
        """
        self._buffer = self._read_reply(delay_ms=1, length=3, raw=True, cmd=Cmd.GETALTITUDE)
        return (self._buffer[0] << 8) | self._buffer[1]

    @altitude.setter
    def altitude(self, height: int) -> None:
        if height > 65535:
            raise AttributeError("Height must be less than or equal to 65535 meters")
        self._set_command_value(Cmd.SETALTITUDE, height)

    def _check_buffer_crc(self, buf: bytearray) -> bool:
        for i in range(0, len(buf), 3):
            self._crc_buffer[0] = buf[i]
            self._crc_buffer[1] = buf[i + 1]
            if self._crc8(self._crc_buffer) != buf[i + 2]:
                raise RuntimeError("CRC check failed while reading data")
        return True

    def _set_command_value(self, cmd, value, delay_ms=0):
        self._buffer[0] = (cmd >> 8) & 0xFF
        self._buffer[1] = cmd & 0xFF
        self._crc_buffer[0] = self._buffer[2] = (value >> 8) & 0xFF
        self._crc_buffer[1] = self._buffer[3] = value & 0xFF
        self._buffer[4] = self._crc8(self._crc_buffer)
        with self.i2c_device as i2c:
            i2c.write(self._buffer, end=5)
        time.sleep(delay_ms * 1000)

    def _read_reply(self, buff, num):
        with self.i2c_device as i2c:
            i2c.readinto(buff, end=num)
        self._check_buffer_crc(self._buffer[0:num])

    @staticmethod
    def _crc8(buffer: bytearray) -> int:
        crc = 0xFF
        for byte in buffer:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = (crc << 1) ^ 0x31
                else:
                    crc = crc << 1
        return crc & 0xFF  # return the bottom 8 bits
