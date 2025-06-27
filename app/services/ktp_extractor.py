import re
import math
import numpy as np
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from app.models import KTPData

def levenshtein(source: str, target: str) -> int:
    if len(source) < len(target):
        return levenshtein(target, source)
    
    if len(target) == 0:
        return len(source)
    
    source = np.array(tuple(source))
    target = np.array(tuple(target))
    
    previous_row = np.arange(target.size + 1)
    for s in source:
        current_row = previous_row + 1
        current_row[1:] = np.minimum(
            current_row[1:],
            np.add(previous_row[:-1], target != s))
        current_row[1:] = np.minimum(
            current_row[1:],
            current_row[0:-1] + 1)
        previous_row = current_row
    
    return previous_row[-1]

class KTPExtractor:
    def __init__(self):
        self.fields_config = [
            {'field_name': 'provinsi', 'keywords': 'provinsi', 'typo_tolerance': 2},
            {'field_name': 'kota', 'keywords': 'kabupaten', 'typo_tolerance': 2},
            {'field_name': 'nik', 'keywords': 'nik', 'typo_tolerance': 1},
            {'field_name': 'nama', 'keywords': 'nama', 'typo_tolerance': 2},
            {'field_name': 'ttl', 'keywords': 'tempat/tgl', 'typo_tolerance': 5},
            {'field_name': 'jenis_kelamin', 'keywords': 'kelamin', 'typo_tolerance': 3},
            {'field_name': 'gol_darah', 'keywords': 'darah', 'typo_tolerance': 3},
            {'field_name': 'alamat', 'keywords': 'alamat', 'typo_tolerance': 2},
            {'field_name': 'rt_rw', 'keywords': 'rt/rw', 'typo_tolerance': 3},
            {'field_name': 'kel_desa', 'keywords': 'kel/desa', 'typo_tolerance': 4},
            {'field_name': 'kecamatan', 'keywords': 'kecamatan', 'typo_tolerance': 3},
            {'field_name': 'agama', 'keywords': 'agama', 'typo_tolerance': 3},
            {'field_name': 'status_perkawinan', 'keywords': 'perkawinan', 'typo_tolerance': 4},
            {'field_name': 'pekerjaan', 'keywords': 'pekerjaan', 'typo_tolerance': 4},
            {'field_name': 'kewarganegaraan', 'keywords': 'kewarganegaraan', 'typo_tolerance': 4},
            {'field_name': 'berlaku_hingga', 'keywords': 'berlaku', 'typo_tolerance': 4}
        ]
        self.max_x = 9999
    
    def convert_format(self, text_response: dict) -> List[Dict]:
        ls_word = []
        if 'textAnnotations' in text_response:
            for text in text_response['textAnnotations']:
                if 'boundingPoly' not in text or 'vertices' not in text['boundingPoly']:
                    continue
                
                vertices = text['boundingPoly']['vertices']
                if len(vertices) < 4:
                    continue
                
                boxes = {
                    'label': text['description'],
                    'x1': vertices[0].get('x', 0),
                    'y1': vertices[0].get('y', 0),
                    'x2': vertices[1].get('x', 0),
                    'y2': vertices[1].get('y', 0),
                    'x3': vertices[2].get('x', 0),
                    'y3': vertices[2].get('y', 0),
                    'x4': vertices[3].get('x', 0),
                    'y4': vertices[3].get('y', 0)
                }
                boxes['w'] = boxes['x3'] - boxes['x1']
                boxes['h'] = boxes['y3'] - boxes['y1']
                ls_word.append(boxes)
        
        return ls_word
    
    def calc_degree(self, x1: float, y1: float, x2: float, y2: float) -> float:
        myradians = math.atan2(y1 - y2, x1 - x2)
        mydegrees = math.degrees(myradians)
        return mydegrees if mydegrees >= 0 else 360 + mydegrees
    
    def get_attribute_ktp(self, ls_word: List[Dict], field_name: str, field_keywords: str, typo_tolerance: int) -> Optional[str]:
        if not ls_word:
            return None
        
        
        if field_name == 'nama':
            ls_word = [word for word in ls_word if word['label'].lower() not in ['jawa', 'nusa']]
        
        
        new_ls_word = [word['label'].lower() for word in ls_word]
        ls_dist = [levenshtein(field_keywords, word) for word in new_ls_word]
        
        
        if '/' in field_keywords:
            alt_keywords = field_keywords.replace('/', ' ')
            ls_dist_alt = [levenshtein(alt_keywords, word) for word in new_ls_word]
            
            for i in range(len(ls_dist)):
                ls_dist[i] = min(ls_dist[i], ls_dist_alt[i])
        
        if np.min(ls_dist) > typo_tolerance:
            
            if field_name == 'kota' and field_keywords != 'kota':
                return self.get_attribute_ktp(ls_word, field_name, 'kota', 1)
            return None
        
        index = np.argmin(ls_dist)
        x, y = ls_word[index]['x1'], ls_word[index]['y1']
        degree = self.calc_degree(ls_word[index]['x1'], ls_word[index]['y1'], 
                                 ls_word[index]['x2'], ls_word[index]['y2'])
        
        
        ls_y = [abs(y - word['y1']) < 300 for word in ls_word]
        value_words = [ww for ww, val in zip(ls_word, ls_y) 
                      if val and abs(self.calc_degree(x, y, ww['x1'], ww['y1']) - degree) < 3]
        
        
        value_words = [val for val in value_words if len(val['label'].replace(' ', '').replace(':', '')) > 0]
        
        
        d = [levenshtein('gol.', str(val['label']).lower()) for val in value_words]
        if d and min(d) <= 1:
            idx = np.argmin(d)
            value_words.pop(idx)
        
        d = [levenshtein('darah', str(val['label']).lower()) for val in value_words]
        if d and min(d) <= 1:
            idx = np.argmin(d)
            value_words.pop(idx)
        
        
        if field_name == 'nik' and value_words:
            self.max_x = max([val['x2'] for val in value_words])
        
        elif field_name == 'kota':
            field_value = ' '.join([str(val['label']) for val in value_words]).strip()
            if field_keywords == 'kabupaten':
                return f'KABUPATEN {field_value}'
            else:
                return f'KOTA {field_value}'
        
        elif field_name == 'ttl':
            
            for keyword in ['lahir', 'tempat/tgl', 'tempat', 'tgl']:
                d = [levenshtein(keyword, str(val['label']).lower()) for val in value_words]
                if d and min(d) <= 2:
                    idx = np.argmin(d)
                    value_words.pop(idx)
                    break
        
        elif field_name == 'jenis_kelamin':
            for val in value_words:
                label_lower = str(val['label']).lower()
                if levenshtein('laki-laki', label_lower) <= 2:
                    return 'LAKI-LAKI'
                elif levenshtein('laki', label_lower) <= 1:
                    return 'LAKI-LAKI'
                elif levenshtein('wanita', label_lower) <= 2:
                    return 'PEREMPUAN'
                elif levenshtein('perempuan', label_lower) <= 2:
                    return 'PEREMPUAN'
            return None
        
        elif field_name == 'gol_darah':
            vals = [val['label'] for val in value_words if len(val['label']) <= 3]
            return vals[0] if vals else None
        
        elif field_name == 'pekerjaan':
            d = [levenshtein('kartu', str(val['label']).lower()) for val in value_words]
            if d and min(d) <= 2:
                idx = np.argmin(d)
                value_words.pop(idx)
            value_words = [val for val in value_words if val['x1'] <= self.max_x]
        
        elif field_name == 'kewarganegaraan':
            d = [levenshtein('wni', str(val['label']).lower()) for val in value_words]
            if d:
                return 'WNI'
            xlocs = [val['x1'] for val in value_words]
            if xlocs:
                idx = np.argmin(xlocs)
                return value_words[idx]['label']
            return None
        
        elif field_name == 'status_perkawinan':
            xlocs = [val['x1'] for val in value_words]
            if xlocs:
                idx = np.argmin(xlocs)
                field_value = value_words[idx]['label']
                if levenshtein('belum', field_value.lower()) <= 1:
                    return 'BELUM KAWIN'
                return field_value
            return None
        
        elif field_name == 'berlaku_hingga':
            d = [levenshtein('hingga', str(val['label']).lower()) for val in value_words]
            if d and min(d) <= 2:
                idx = np.argmin(d)
                value_words.pop(idx)
            xlocs = [val['x1'] for val in value_words]
            if xlocs:
                idx = np.argmin(xlocs)
                field_value = value_words[idx]['label']
                if levenshtein('seumur', field_value.lower()) <= 2:
                    return 'SEUMUR HIDUP'
                return field_value
            return None
        
        
        field_value = ' '.join([str(val['label']) for val in value_words]).strip()
        return field_value if field_value else None
    
    def extract_date(self, date_string: str) -> Optional[datetime]:
        if not date_string:
            return None
        
        try:
            
            regex = re.compile(r'(\d{1,2}-\d{1,2}-\d{4})')
            tgl = re.findall(regex, date_string)
            if tgl:
                date = datetime.strptime(tgl[0], '%d-%m-%Y')
            else:
                
                tgl = ''.join([n for n in date_string if n.isdigit()])
                if len(tgl) == 8:
                    date = datetime.strptime(f"{tgl[0:2]}-{tgl[2:4]}-{tgl[4:]}", '%d-%m-%Y')
                else:
                    return None
            
            
            if date.year < 1910 or date.year > 2100:
                return None
            
            return date
        except ValueError:
            return None
    
    def normalize_occupation(self, occ: str) -> str:
        if not occ:
            return occ
        
        occ_lower = occ.lower()
        
        occupation_mapping = {
            'mengurus rumah tangga': ('Mengurus Rumah Tangga', 6),
            'buruh harian lepas': ('Buruh Harian Lepas', 6),
            'pegawai negeri sipil': ('Pegawai Negeri Sipil', 5),
            'pelajar/mahasiswa': ('Pelajar/Mahasiswa', 4),
            'pelajar/mhs': ('Pelajar/Mahasiswa', 3),
            'belum/tidak bekerja': ('Belum/Tidak Bekerja', 5),
            'karyawan swasta': ('Karyawan Swasta', 4),
            'pegawai negeri': ('Pegawai Negeri', 4),
            'wiraswasta': ('Wiraswasta', 3),
            'peg negeri': ('Pegawai Negeri', 3),
            'peg swasta': ('Pegawai Swasta', 3)
        }
        
        for key, (value, tolerance) in occupation_mapping.items():
            if levenshtein(key, occ_lower) <= tolerance:
                return value
        
        return occ
    
    def extract_ktp_data(self, text_response: dict) -> KTPData:
        ls_word = self.convert_format(text_response)
        
        if not ls_word:
            return KTPData()
        
        
        self.max_x = 9999
        
        raw_result = {}
        
        
        for field in self.fields_config:
            field_value = self.get_attribute_ktp(
                ls_word, 
                field['field_name'], 
                field['keywords'], 
                field['typo_tolerance']
            )
            if field_value:
                field_value = str(field_value).replace(': ', '').replace(':', '')
            raw_result[field['field_name']] = field_value
        
        return self._process_extracted_data(raw_result)
    
    def _process_extracted_data(self, raw_result: Dict) -> KTPData:
        data = KTPData()
        
        
        if raw_result.get('nik'):
            data.nik = ''.join([i for i in raw_result['nik'] if i.isdigit()])
        
        
        if raw_result.get('nama'):
            data.nama = ''.join([i for i in raw_result['nama'] if not i.isdigit()]).replace('-', '').strip()
        
        
        if raw_result.get('jenis_kelamin') == 'LAKI-LAKI':
            data.jenis_kelamin = 'LAKI-LAKI'
        elif raw_result.get('jenis_kelamin') in ['WANITA', 'PEREMPUAN']:
            data.jenis_kelamin = 'PEREMPUAN'
        
        
        if raw_result.get('ttl'):
            ttls = raw_result['ttl'].split(', ')
            if len(ttls) >= 2:
                data.tempat_lahir = ttls[0]
                birth_date = self.extract_date(ttls[1])
                data.tanggal_lahir = birth_date.date() if birth_date else None
            elif len(ttls) == 1:
                data.tempat_lahir = ttls[0]
                
                birth_date = self.extract_date(raw_result['ttl'])
                data.tanggal_lahir = birth_date.date() if birth_date else None
        
        
        if data.tempat_lahir:
            
            data.tempat_lahir = re.sub(r'[/\\]\s*[TtIi]gl\s*', '', data.tempat_lahir)
            
            data.tempat_lahir = ''.join([i for i in data.tempat_lahir if i.isalpha() or i.isspace()])
            data.tempat_lahir = data.tempat_lahir.strip().upper()
        
        
        data.kewarganegaraan = 'INDONESIA' if raw_result.get('kewarganegaraan') == 'WNI' else raw_result.get('kewarganegaraan')
        
        
        marital_status = raw_result.get('status_perkawinan')
        if marital_status:
            ms_lower = marital_status.lower()
            if levenshtein('belum kawin', ms_lower) <= 2 or levenshtein('tidak kawin', ms_lower) <= 2:
                data.status_perkawinan = 'BELUM KAWIN'
            elif levenshtein('kawin', ms_lower) <= 1:
                data.status_perkawinan = 'KAWIN'
            elif any(levenshtein(status, ms_lower) <= 2 for status in ['janda', 'duda', 'cerai']):
                data.status_perkawinan = 'CERAI'
        
        
        data.pekerjaan = self.normalize_occupation(raw_result.get('pekerjaan'))
        
        
        if raw_result.get('gol_darah'):
            blood_type = ''.join([i for i in raw_result['gol_darah'] if not i.isdigit()]).strip()
            data.golongan_darah = blood_type.upper() if blood_type.lower() in ['a', 'b', 'ab', 'o'] else None
        
        
        data.provinsi = raw_result.get('provinsi')
        data.kota = raw_result.get('kota')
        data.alamat = raw_result.get('alamat')
        data.rt_rw = raw_result.get('rt_rw')
        data.kelurahan_desa = raw_result.get('kel_desa')
        data.kecamatan = raw_result.get('kecamatan')
        data.agama = raw_result.get('agama')
        data.berlaku_hingga = raw_result.get('berlaku_hingga')
        
        return data