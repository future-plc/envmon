import logging
from logging import Logger
import time
from dataclasses import dataclass
from adafruit_bus_device.i2c_device import I2CDevice

try:
    from busio import I2C  # pylint: disable=unused-import
    from typing import Optional, Union 
except ImportError:
    pass

logger: Logger = logging.getLogger(__name__)

SCD40_ADDR = 0x62


@dataclass
class SensorData():
    pm10: float = 0
    pm25: float = 0
    pm100: float = 0
    temp_c: float = 0
    humidity: float = 0
    pressure_hpa: float = 0
    co2: float = 0


class Sensor():
    def __init__(self, i2cbus: I2C, addr, sensor_data: SensorData):
        self.retries = 0
        self.addr = addr
        self.i2cbus = i2cbus
        self.i2c_device: Optional[I2CDevice] = None
        self._sensor_data = sensor_data
        self._interval = 5.0  # 5 seconds unless otherwise specified
        self._buffer = None
        self._connected = self.open_connection()
        if self.logger is None:
            self.logger = logging.getLogger("envmon.sensor")

    def open_connection(self):
        if self.retries > 5:
            # sensor probably not hooked up
            return

        try:
            self.i2c_device = I2CDevice(self.i2cbus, self.addr)
        except ValueError:
            self.logger.debug("Failed to connect")
            self.retries = self.retries + 1
            return False
        else:
            self.logger.debug("Connected")
            return True

    @property
    def connected(self) -> Optional[bool]:
        return self._connected

    @property
    def read_interval(self) -> float:
        return self._interval

    @read_interval.setter
    def read_interval(self, interval: float) -> None:
        self._interval = interval

    def reset(self):
        raise NotImplementedError("This class doesn't implement reset")

    def read(self):
        raise NotImplementedError("Subclasses of Sensor impl read function")

    def _read_raw(self, buffer: Optional[bytearray] = None, length=1) -> None:
        if self._buffer is None:
            raise NotImplementedError("Need to give this a bytearray buffer")
        if self._connected and self.i2c_device:
            with self.i2c_device as device:
                try:
                    if buffer is None:
                        device.readinto(self._buffer, end=length)
                    else:
                        device.readinto(buffer, end=length)

                except OSError as err:
                    self.logger.error("Unable to read from sensor")
                    self.logger.error(err)
                    self._connected = False
        else:
            self.open_connection()

    def _send_cmd(self, cmd: Optional[Union[bytearray, bytes]] = None, **kwargs) -> None:
        if self._connected and self.i2c_device:
            with self.i2c_device as device:
                if cmd is None:
                    if self._send_buffer is None:
                        raise NotImplementedError(
                            "Class needs to implement a send buffer"
                        )
                    cmd = self._send_buffer

                cmd = self.convert_16(cmd)
                device.write(cmd)
        time.sleep(kwargs.get("delay_ms", 0)/1000.0)

    @staticmethod
    def convert_16(val) -> Union[bytearray, bytes]:
        if isinstance(val, bytearray) or isinstance(val, bytes):
            return val
        ret: bytearray = bytearray(2)
        if not isinstance(val, int):
            val = int(val)
        ret[0] = (val >> 8) & 0xFF
        ret[1] = val & 0xFF
        return ret

    def _read_reply(
            self, delay_ms: int = 30,
            length: int = 1,
            **kwargs
    ):
        ''' Send command and read back whats recieved '''
        word_len = 2
        cmd = kwargs.get("cmd")
        self._send_cmd(cmd)

        time.sleep(round(delay_ms * 0.001, 3))

        # reply_buffer = bytearray(length * (word_len + 1))
        self._read_raw(length=length)
        data_buffer = []
        # if not kwargs.get("raw", False):
        #     self.logger.debug("me")
        #     for i in range(0, length * (word_len + 1), 3):
        #         data_buffer.append(struct.unpack_from(
        #             ">H", self._buffer[i:i+2])[0])
        # return data_buffer

    def _read_register(self, register: int, length: int) -> bytearray:
        register_value = bytearray(length)
        self._send_cmd(bytes([register & 0xFF]))
        self._read_raw(register_value, length=24)
        return register_value

    def _read_byte(self, register):
        return self._read_register(register, 1)[0]

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




