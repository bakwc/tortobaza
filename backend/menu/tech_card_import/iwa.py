from google.protobuf.internal.decoder import _DecodeVarint32
from numbers_parser.generated.TSPArchiveMessages_pb2 import ArchiveInfo
from numbers_parser.iwafile import IWACompressedChunk


def iter_objects(data: bytes):
    blob = b"".join(IWACompressedChunk._decompress_all(data))
    offset = 0
    while offset < len(blob):
        length, position = _DecodeVarint32(blob, offset)
        header = ArchiveInfo()
        header.ParseFromString(blob[position : position + length])
        offset = position + length
        for info in header.message_infos:
            end = offset + info.length
            if end > len(blob):
                raise ValueError("IWA message extends past the archive")
            yield header.identifier, info.type, blob[offset:end]
            offset = end
