import struct
import board
import logger
import logging
import time
from equations import bytes_to_pressure
from adafruit_bus_device.i2c_device import I2CDevice

try:
    from busio import I2C  # pylint: disable=unused-import
    from typing import Optional, List
except ImportError:
    pass

sensor_logger = logging.getLogger(__name__)

AQI_ADDR = 0x12
SGP40_ADDR = None
BMP280_ADDR = None
SCD40_ADDR = 0x62
BMP_SEA_LEVEL_PRESSURE = 2971155.4124


class Sensor():
    def __init__(self, i2cbus: I2C, addr):
        self.retries = 0
        self.addr = addr
        self.i2cbus = i2cbus
        self.i2c_device = None
        self._buffer = None
        self._connected = self.open_connection()
        if self.logger is None:
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

    def _get_i2c_raw(self, buffer: bytearray = None, read_words: int = 1) -> None:
        if self._buffer is None:
            raise NotImplementedError("Need to give this a bytearray buffer")
        if self._connected:
            with self.i2c_device as device:
                try:
                    if buffer is None:
                        device.readinto(self._buffer)
                    else:
                        device.readinto(buffer, end=read_words)

                except OSError as err:
                    self.logger.error(err)
                    self._connected = False
        else:
            self.open_connection()

    def _send_i2c_raw(self, cmd: bytearray = None):
        if self._connected:
            with self.i2c_device as device:
                if cmd is not None:
                    if self._send_buffer is None:
                        raise NotImplementedError(
                                "Class needs to implement a send buffer"
                                )
                    device.write(self._send_buffer)
                else:
                    device.write(cmd)

    def _send_read_raw(
            self, delay_ms: int = 30,
            read_words: int = 1,
            **kwargs
            ) -> Optional[List[int]]:
        ''' Send command and read back whats recieved '''
        word_len = 2
        cmd = kwargs.get("cmd")
        self._send_i2c_raw(cmd)
        time.sleep(round(delay_ms * 0.001, 3))
        reply_buffer = bytearray(read_words * (word_len + 1))
        self._get_i2c_raw(reply_buffer)
        data_buffer = []
        for i in range(0, read_words * (word_len + 1), 3):
            data_buffer.append(struct.unpack_from(">H", reply_buffer[i:i+2])[0])
        return data_buffer

    def _read_register(self, register, length=3):
        self._send_read_raw(read_words=length-1, cmd=[register & 0xFF])



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


class SGP40(Sensor):

    def __init___(self, i2cbus, addr=SGP40_ADDR):
        self.logger = logging.getLogger("envmon.SGP40")
        super().__init__(i2cbus, addr)
        self._buffer = bytearray(2)
        self._send_buffer = bytearray(2)

    def init(self):
        test_command = bytearray([0x28, 0x0E])
        startup_test = self._send_read_raw(delay_ms=500, cmd=test_command)
        if startup_test[0] != 0xD400:
            self.logger("startup test failed")
        else:
            self.logger.debug("Init")


    def read(self):
        pass


class BMP280(Sensor):

    def __init__(self, i2cbus, addr=BMP280_ADDR):
        super().__init__(i2cbus, addr)
        self._buffer = None
        self._cal_buffer: list[float] = None
        self.sea_level_pressure = 1013.25
        pass

    def _initialize_settings(self) -> None:
        iir = 0x00
        overscan_temp = 0x02
        overscan_pressure = 0x05
        standby = 0x00
        self.mode = MODE_SLEEP
        self._reset()
        self._get_calibration()


    @property
    def mode(self) -> int:
        return self._mode

    @mode.setter
    def mode(self, mode) -> None:
        self._mode = mode
        self._update_ctrl()

    def _get_calibration(self) -> None:
        ''' Read calibration coefficients'''
        cal_coefficients = self._read_register(register=0x88, length=24)
        cal_coefficients = list(struct.unpack("<HhhHhhhhhhhh", bytes(cal_coefficients)))
        self._cal_buffer = [float(c) for c in cal_coefficients]
        self._temp_cal = self._cal_buffer[:3]
        self._pressure_cal = self._cal_buffer[3:]

    def read(self) -> tuple[float]:
        pressure_hpa = None
        temp_bytes = self._read_register(0x24)
        temp_raw = self._reg_to_float(temp_bytes) / 16
        temp_c = self._temp_raw_to_c(temp_raw)

        pressure_bytes = self._read_register(register=0xF7, length=3)
        pressure_raw = self._reg_to_float(pressure_bytes)
        pressure_hpa = bytes_to_pressure(pressure_raw, temp_raw, self._pressure_cal)

        return (temp_c, pressure_hpa)

    def _temp_raw_to_c(self, raw) -> float:
        var1 = (
            raw / 16384.0 - self._temp_cal[0] / 1024.0
        ) * self._temp_cal[1]
        var2 = (
            (raw / 131072.0 - self._temp_cal[0] / 8192.0)
            * (raw / 131072.0 - self._temp_cal[0] / 8192.0)
        ) * self._temp_cal[2]

        return int(var1 + var2) / 5120.0

    def _reg_to_float(self, reg_raw: bytearray) -> float:
        val = 0.0
        for b in reg_raw:
            val *= 256.0
            val += float(b & 0xFF)
        return val


    def _reset(self) -> None:
            """Soft reset the sensor"""
            self._send_i2c_raw(bytearray([0xE0, 0xB6]))
            time.sleep(0.004)
