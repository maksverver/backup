from FS  import StorageFS  as FS
from S3  import StorageS3  as S3
from FTP import StorageFTP as FTP

backends = { 'FS': FS, 'FTP': FTP, 'S3': S3 }
