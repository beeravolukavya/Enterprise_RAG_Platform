import sys,os
sys.path.insert(0,os.path.abspath('backend'))
from core import chunks,extract

def test_chunk_overlap():
    text='x'*3500; parts=chunks(text)
    assert len(parts)==3 and parts[0][-240:]==parts[1][:240]

def test_empty():assert chunks(' \n ')==[]

def test_text():assert extract(b'hello','sample.txt')=='hello'

def test_bad_extension():
    import pytest
    with pytest.raises(ValueError):extract(b'bad','x.exe')
