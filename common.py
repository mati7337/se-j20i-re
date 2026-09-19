from abc import ABC, abstractmethod
import struct

# A bit more user friendly way of using structs

# Basic struct
#
# class Example(BaseStructure):
#     _byte_order_ = '>'
#     _fields_ = [
#         ('single_byte', 'B', default_value),
#         ('some_const_length_string', '16s'),
#         ('single_uint', 'I'),
#     ]
#
# test1 = Example(
#     some_const_length_string=b"1"*16
#     single_uint=123
# )
#
# print(f"Raw bytes: {test1.pack()}")
#
# print(f"Human readable: {test1}")
# print(f"Even more human readable: {test1.str_multiline()}")
#
# Unpacking from bytes:
# test2 = Example()
# test2.unpack(some_raw_bytes)
# test2.unpack(some_raw_bytes2, offset=0x10)
# Or:
# test2 = Example.from_bytes(some_raw_bytes)
# test2 = Example.from_bytes(some_raw_bytes, offset=0x10)

class BaseStructure(ABC):
    def __init__(self, **kwargs):
        self.init_from_dict(**kwargs)
        for field in self._fields_:
            if len(field) > 2:
                if not hasattr(self, field[0]):
                    setattr(self, field[0], field[2])

    def __str__(self):
        attr_list = []

        for field in self._fields_:
            key = field[0]
            val = self.field_val_str(field)
            attr_list.append(f"{key}={val}")

        return " ".join(attr_list)

    def field_val_str(self, field):
        # Returns the value of a field as str
        key = field[0]
        val = getattr(self, key)

        if type(val) is int:
            size = struct.calcsize(field[1])
            val_str = f"{val:x}".rjust(size*2, "0")
            return f"0x{val_str}"
        elif type(val) is tuple:
            hex_strings = [hex(i) for i in val]
            return f"({', '.join(hex_strings)})"
        elif type(val) is bytes:
            try:
                return val.decode()
            except UnicodeDecodeError:
                return val.hex()
        else:
            return str(val)

    def str_multiline(self):
        attr_list = []
        max_key_len = len( max(self._fields_, key=lambda x: len(x[0]))[0] )

        for field in self._fields_:
            key = field[0]
            val = self.field_val_str(field)
            attr_list.append(f"{key.ljust(max_key_len)}: {val}")

        return "\n".join(attr_list)

    def init_from_dict(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def pack(self):
        values = []
        for field in self._fields_:
            if isinstance(field[1], BaseStructure):
                values.append(getattr(self, field[0], 0).pack())
            else:
                values.append(getattr(self, field[0], 0))
        return struct.pack(self.format(), *values)

    #slopped
    def unpack(self, buf, offset=0):
        keys_vals = {}

        for field in self._fields_:
            name = field[0]
            fmt_or_struct = field[1]

            if isinstance(fmt_or_struct, BaseStructure):
                fmt_or_struct.unpack(buf, offset=offset)
                keys_vals[name] = fmt_or_struct
                offset += fmt_or_struct.size()
            else:
                fmt = self._byte_order_ + fmt_or_struct
                unpacked = struct.unpack_from(fmt, buf, offset=offset)
                keys_vals[name] = unpacked[0] if len(unpacked) == 1 else unpacked
                offset += struct.calcsize(fmt)

        self.init_from_dict(**keys_vals)
        return self

    @classmethod
    def size(cls):
        return struct.calcsize(cls.format())

    @classmethod
    def format(cls):
        pack_format = cls._byte_order_
        for field in cls._fields_:
            if isinstance(field[1], BaseStructure):
                pack_format += str(type(field[1]).size()) + 's'
            else:
                pack_format += field[1]
        return pack_format

    @classmethod
    def from_bytes(cls, buf, offset=0):
        obj = cls()
        return obj.unpack(buf, offset=offset)

    @property
    @abstractmethod
    def _byte_order_(self): pass

    @property
    @abstractmethod
    def _fields_(self): pass

class BaseStructureData(BaseStructure):
    """Same as BaseStructure but with the addition of variable length data after _fields_"""

    def __init__(self, **kwargs):
        data = kwargs.pop(self._data_field_, bytearray())
        setattr(self, self._data_field_, data)
        super().__init__(**kwargs)

    def __str__(self):
        data = self.field_val_str((self._data_field_, "s"))
        return f"{super().__str__()} {self._data_field_}={data}"

    def str_multiline(self):
        data = self.field_val_str((self._data_field_, "s"))
        return f"{super().str_multiline()}\n{self._data_field_}:\n{data}"

    def pack_header(self):
        return super().pack()

    def pack(self):
        return super().pack() + bytes(self.data)

    def unpack(self, buf, offset=0):
        super().unpack(buf, offset=offset)
        data_offset = offset + self.size()
        self.data = bytearray(buf[data_offset:])
        return self

    @property
    @abstractmethod
    def _data_field_(self): pass

# class BaseStructureDataWithSize(BaseStructure):
#     """
#     Similar to BaseStructureData but also automatically stores the size in the
#     _length_field_ field.
#     """
#
#     def __init__(self, **kwargs):
#         data = kwargs.pop(self._data_field_, bytearray())
#         setattr(self, self._data_field_, data)
#
#         super().__init__(**kwargs)
#
#         if not self._data_size_field in kwargs:
#             setattr(self, self._data_size_field_, len(data))
#
#     def pack(self):
#         setattr(self, self._length_field_, len(self.data))
#         return super().pack()
#
#     def unpack(self, buf, offset=0):
#         BaseStructure.unpack(self, buf, offset=offset)
#         data_offset = offset + self.size()
#         data_length = getattr(self, self._length_field_)
#         self.data = bytearray(buf[data_offset:data_offset + data_length])
#         return self
#
#     @property
#     @abstractmethod
#     def _data_field_(self): pass
#
#     @property
#     @abstractmethod
#     def _data_size_field_(self): pass
