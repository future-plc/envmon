import struct
import board
import logger
import logging
from adafruit_bus_device.i2c_device import I2CDevice

try:
    from busio import I2C  # pylint: disable=unused-import
except ImportError:
    pass

sensor_logger = logging.getLogger(__name__)

AQI_ADDR = 0x12


class Sensor():
    def __init__(self, i2cbus: I2C, addr):
        self.retries = 0
        self.addr = addr
        self.i2cbus = i2cbus
        self.i2c_device = None
        self._buffer = None
        self._connected = self.open_connection()
        if self.logger == None:
            self.logger = logger.getLogger("envmon.sensor")

    def open_connection(self):
        if self.retries > 5:
            # sensor probably not hooked up
            return

        try:
            self.i2c_device = I2CDevice(self.i2cbus, self.addr)
        except ValueError:
            logger.debug("Failed to connect")
            self.retries = self.retries + 1
            return False
        else:
            self.logger.debug("Connected")
            return True

    @property
    def connected(self):
        return self._connected

    def _get_i2c_raw(self) -> None:
        if self._buffer is None:
            raise NotImplementedError("Need to give this a bytearray buffer")
        if self._connected:
            with self.i2c_device as device:
                try:
                    device.readinto(self._buffer)
                except OSError as err:
                    self.logger.error(
                            "{} Sensor unable to get readings".format(str(self))
                            )
                    self.logger.error(err)
                    self._connected = False
        else:
            self.open_connection()


class AQISensor(Sensor):
    def __init__(self, i2cbus, addr=AQI_ADDR):
        self.logger = logging.getLogger("envmon.aqi_sensor")
        self.logger.debug("Init AQI Sensor")
        super().__init__(i2cbus, addr)
        self._buffer = bytearray(32)

    def __repr__(self) -> str:
        return "PM2.5 AQI Sensor"

    def read(self) -> dict:
        self._get_i2c_raw()
        header = self._buffer[0:2]
        if not header == b"BM":
            self.logger.error("Invalid header: {}".format(header))

        frame_size = struct.unpack(">H", self._buffer[2:4])[0]
        if frame_size != 28:
            self.logger.error("Invalid Frame Size: {}".format(frame_size))

        checksum = struct.unpack(">H", self._buffer[30:32])[0]
        check = sum(self._buffer[0:30])
        if check != checksum:
            self.logger.error("Invalid checksum")

        try:
            results = struct.unpack(">HHHHHHHHHHHH", self._buffer[4:28])
            self.logger.debug(results)
        except struct.error:
            buffer_str = str(self._buffer)
            logger.error("failed to unpack buffer")
            logger.error("Buffer: {}".format(buffer_str))
