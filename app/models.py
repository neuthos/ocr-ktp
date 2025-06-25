from pydantic import BaseModel
from typing import Optional
from datetime import date

class KTPData(BaseModel):
    nik: Optional[str] = None
    nama: Optional[str] = None
    tempat_lahir: Optional[str] = None
    tanggal_lahir: Optional[date] = None
    jenis_kelamin: Optional[str] = None
    golongan_darah: Optional[str] = None
    alamat: Optional[str] = None
    rt_rw: Optional[str] = None
    kelurahan_desa: Optional[str] = None
    kecamatan: Optional[str] = None
    agama: Optional[str] = None
    status_perkawinan: Optional[str] = None
    pekerjaan: Optional[str] = None
    kewarganegaraan: Optional[str] = None
    berlaku_hingga: Optional[str] = None
    provinsi: Optional[str] = None
    kota: Optional[str] = None

class KTPResponse(BaseModel):
    success: bool
    message: str
    data: Optional[KTPData] = None

class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    error_code: Optional[str] = None