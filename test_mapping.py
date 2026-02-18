#!/usr/bin/env python3
import sys
sys.path.insert(0, '/Users/taeheonshin/dev/python/saju')

from saju_engine import SajuEngine

engine = SajuEngine(
    "/Users/taeheonshin/dev/python/saju/data/manse_data.json",
    "/Users/taeheonshin/dev/python/saju/data/term_data.json",
    "/Users/taeheonshin/dev/python/saju/ft_strength_mapping.json"
)

test_cases = [
    {
        'birth_str': '1990-06-15 10:30',
        'gender': '남',
        'location': '서울',
        'use_yajas_i': True,
        'calendar_type': '양력',
        'expected_hash': '경오무인경자신사',
        'expected_status': '중화신약(中和身弱)'
    },
    {
        'birth_str': '1985-04-22 14:20',
        'gender': '여',
        'location': '부산',
        'use_yajas_i': True,
        'calendar_type': '양력',
        'expected_hash': '을사기축경자병자',
        'expected_status': '신약(身弱)'
    }
]

print("Testing Forteller mapping implementation...\n")

for i, test in enumerate(test_cases, 1):
    print(f"Test {i}: {test['birth_str']}")
    print(f"  Expected hash: {test['expected_hash']}")
    print(f"  Expected status: {test['expected_status']}")
    
    result = engine.analyze(
        test['birth_str'],
        test['gender'],
        test['location'],
        test['use_yajas_i'],
        test['calendar_type']
    )
    
    if 'error' in result:
        print(f"  ERROR: {result['error']}")
    else:
        pillars = result.get('pillars', [])
        if len(pillars) == 4:
            actual_hash = ''.join([
                pillars[0]['gan'], pillars[0]['ji'],
                pillars[1]['gan'], pillars[1]['ji'],
                pillars[2]['gan'], pillars[2]['ji'],
                pillars[3]['gan'], pillars[3]['ji']
            ])
            print(f"  Actual hash: {actual_hash}")
            print(f"  Actual status: {result.get('status', 'N/A')}")
            
            if actual_hash == test['expected_hash']:
                print(f"  ✓ Hash matches!")
            else:
                print(f"  ✗ Hash mismatch!")
            
            if result.get('status') == test['expected_status']:
                print(f"  ✓ Status matches!")
            else:
                print(f"  ✗ Status mismatch!")
    
    print()

print(f"Mapping table size: {len(engine.ft_mapping)} entries")
print(f"Sample keys: {list(engine.ft_mapping.keys())[:3]}")
print(f"Sample values: {list(engine.ft_mapping.values())[:3]}")
