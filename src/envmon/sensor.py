import struct
import logging
import board
from adafruit_bus_device.i2c_device import I2CDevice

try:
    from busio import I2C  # pylint: disable=unused-import
except ImportError:
    pass

logger = logging.getLogger(__name__)

AQI_ADDR = 0x77


class Sensor():
    def __init__(self, i2cbus: I2C, addr):
        self.retries = 0
        self.addr = addr
        self.i2c_device = None

        self._buffer = None

        """
        Initiate a connection to the sensor
        """

        self._connected = self.open_connection()

    def open_connection(self):
        if self.retries > 5:
            # sensor probably not hooked up
            return

        try:
            self.i2c_device = I2CDevice(self.i2cbus, self.addr)
        except ValueError:
            logger.debug("Failed to connect to " + str(self))
            self.retries = self.retries + 1

    @property
    def connected(self):
        return self._connected

    def _get_i2c_raw(self) -> None:
        if self._buffer is None:
            raise NotImplementedError("Need to give this a bytearray buffer")
        if self._connected:
            with self.i2c_device as device:
                try:
                    device.readinto(self.buffer)
                except OSError as err:
                    logger.error(
                            "{} Sensor unable to get readings".format(str(self))
                            )
                    logger.error(err)
                    self._connected = False
        else:
            self.open_connection()


class AQISensor(Sensor):
    def __init__(self, i2cbus, addr=AQI_ADDR):
        super.__init__(i2cbus, addr)
        self._buffer = bytearray(32)

    def __repr__(self) -> str:
        return "PM2.5 AQI"

    def read(self) -> dict:
        self._get_i2c_raw()
        if not self._buffer[0:2] == b"BM":
            logger.error("Invalid header")

        frame_size = struct.unpack(">H", self._buffer[2:4])[0]
        if frame_size != 28:
            logger.error("Invalid Frame Size")

        checksum = struct.unpack(">H", self._buffer[30:32])[0]
        check = sum(self._buffer[0:30])
        if check != checksum:
            logger.error("Invalid checksum")

        results = struct.unpack(">HHHHHHHHHH", self._buffer[4:28])
        logger.debug(results)
