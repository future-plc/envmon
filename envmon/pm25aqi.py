import logging
import struct
from sensors import Sensor

AQI_ADDR = 0x12
"""
Sensor class for PM2.5 AQI sensor using i2c

Based on library provided by Adafruit
https://github.com/adafruit/Adafruit_CircuitPython_PM25

"""
class AQISensor(Sensor):
    def __init__(self, i2cbus, sensor_data, addr=AQI_ADDR):
        self.logger = logging.getLogger("envmon.AQI")
        self.logger.debug("Init AQI Sensor")
        super().__init__(i2cbus, addr, sensor_data)
        self._buffer = bytearray(32)

    def __repr__(self) -> str:
        return "PM2.5 AQI Sensor"

    def shutdown(self):
        ''' This sensor doesnt have a shutdown command'''
        pass

    def read(self) -> dict:
        self._read_raw(length=32)
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
            self._sensor_data.pm10 = results[0]
            self._sensor_data.pm25 = results[1]
            self._sensor_data.pm100 = results[2]
        except struct.error:
            buffer_str = str(self._buffer)
            self.logger.error("failed to unpack buffer")
            self.logger.error("Buffer: {}".format(buffer_str))
