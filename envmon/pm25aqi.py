import logging
import struct
from sensors import Sensor

AQI_ADDR = 0x12

class AQISensor(Sensor):
    def __init__(self, i2cbus, addr=AQI_ADDR):
        self.logger = logging.getLogger("envmon.aqi_sensor")
        self.logger.debug("Init AQI Sensor")
        super().__init__(i2cbus, addr)
        self._buffer = bytearray(32)

    def __repr__(self) -> str:
        return "PM2.5 AQI Sensor"

    def read(self) -> dict:
        self._read_raw()
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
            self.logger.error("failed to unpack buffer")
            self.logger.error("Buffer: {}".format(buffer_str))
