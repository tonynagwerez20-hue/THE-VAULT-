"""Payload contract oracle and MQL source checks; not native parser execution."""
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[3]
SOURCE = (ROOT / 'MQL5/Include/External Context Compactor.mqh').read_text(encoding='utf-8-sig')
REQUIRED = {'news_valid', 'news_observed_ts', 'news_ts', 'news_active', 'news_released'}
BASE = [('news_valid', '1'), ('news_observed_ts', '1000'), ('news_ts', '0'),
        ('news_active', '0'), ('news_released', '0')]


def payload_valid(rows):
    # Independently specified wire contract: exact required set, one occurrence,
    # boolean 0/1, canonical nonnegative signed-64 timestamp; event flags need a time.
    fields = {}
    for key, value in rows:
        if key not in REQUIRED:
            continue
        if key in fields:
            return False
        if key in {'news_observed_ts', 'news_ts'}:
            if not value.isascii() or not value.isdecimal():
                return False
            n = int(value)
            if n > 2**63 - 1 or str(n) != value:
                return False
        elif value not in {'0', '1'}:
            return False
        fields[key] = value
    if fields.keys() != REQUIRED:
        return False
    return not ((fields['news_active'] == '1' or fields['news_released'] == '1')
                and int(fields['news_ts']) == 0)


def test_complete_confirmed_no_event_is_distinct_from_missing_payload():
    assert payload_valid(BASE)
    assert not payload_valid([])


@pytest.mark.parametrize('missing', sorted(REQUIRED))
def test_each_missing_required_field_is_rejected(missing):
    assert not payload_valid([(k,v) for k,v in BASE if k != missing])


@pytest.mark.parametrize('key', sorted(REQUIRED))
def test_duplicate_even_identical_field_is_rejected(key):
    assert not payload_valid(BASE + [(key, dict(BASE)[key])])


@pytest.mark.parametrize('value', ['', '-1', '1000junk', '1.0', '01000', '9223372036854775808'])
def test_invalid_timestamp_encoding_is_rejected(value):
    assert not payload_valid([(k, value if k == 'news_observed_ts' else v) for k,v in BASE])


@pytest.mark.parametrize('key', ['news_valid', 'news_active', 'news_released'])
def test_non_boolean_encoding_is_not_no_event(key):
    assert not payload_valid([(k, 'false' if k == key else v) for k,v in BASE])


def test_event_flags_require_event_timestamp():
    assert not payload_valid([(k, '1' if k == 'news_active' else v) for k,v in BASE])
    assert payload_valid([(k, '1' if k == 'news_active' else '1100' if k == 'news_ts' else v) for k,v in BASE])


def test_source_checks_completeness_duplicates_and_resets_before_open():
    reader = SOURCE.split('bool ReadExternalContext(', 1)[1].split('bool ExternalNewsFilterAllows(', 1)[0]
    assert reader.index('ctx.news_released            = false;') < reader.index('FileOpen(')
    assert reader.index('ctx.news_valid               = false;') < reader.index('FileOpen(')
    for index, key in enumerate(['news_valid', 'news_observed_ts', 'news_ts', 'news_active', 'news_released']):
        assert f'k=="{key}") news_bit={1 << index};' in reader
    assert 'if((news_fields & news_bit)!=0) news_payload_valid=false;' in reader
    assert 'if(!ExternalCanonicalTimestamp(v)) news_payload_valid=false;' in reader
    assert 'else if(v!="0" && v!="1") news_payload_valid=false;' in reader
    invalid = reader.split('if(!news_payload_valid || news_fields!=31', 1)[1].split('//--- Validate schema', 1)[0]
    assert 'ctx.news_valid=false;' in invalid
    assert 'ctx.news_observed_ts=0;' in invalid
    assert 'NEWS_PAYLOAD_INCOMPLETE_OR_INVALID' in invalid
