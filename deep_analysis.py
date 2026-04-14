#!/usr/bin/env python3
"""Phase 2 검증: 전 설정 일치율 테스트"""
from saju_engine import SajuEngine
engine = SajuEngine('./data/manse_data.json', './data/term_data.json')

# test.md cases with FT reference for ALL 4 settings
test_cases = [
    ('#2', '1988-05-15 10:30', 'F', '서울',
     ('중화신강','중화신강','중화신약','중화신약'), ('목','목','토','토')),
    ('#3', '2026-01-25 23:40', 'M', '서울',
     ('신약','중화신약','극약','태약'), ('토','토','토','토')),
    ('#6', '2023-04-10 15:00', 'F', '서울',
     ('신강','신강','중화신강','신강'), ('목','목','목','목')),
    ('#7', '2024-10-20 11:31', 'M', '서울',
     ('신강','신강','중화신강','신강'), ('토','수','수','수')),
    ('#8', '2024-08-07 09:09', 'F', '서울',
     ('태약','태약','극약','태약'), ('금','금','수','수')),
    ('#9', '2024-12-21 18:20', 'M', '서울',
     ('중화신약','중화신약','신약','신약'), ('토','토','토','토')),
    ('#10', '2025-02-03 23:10', 'F', '서울',
     ('신약','신약','중화신강','중화신강'), ('수','금','토','토')),
    ('#13', '2025-07-24 10:00', 'M', '서울',
     ('신약','태약','태약','태약'), ('수','수','수','수')),
]

# forceteller.md cases (기본 only)
ft_cases = [
    ('#F1', '1948-07-15 12:30', 'M', '서울', ('중화신강',), ('목',)),
    ('#F2', '1949-05-20 08:45', 'F', '부산', ('태강',), ('수',)),
    ('#F5', '1952-03-03 01:15', 'M', '광주', ('태약',), ('토',)),
    ('#F6', '1953-06-25 10:00', 'F', '대전', ('중화신강',), ('수',)),
    ('#F8', '1955-08-15 15:40', 'F', '수원', ('중화신약',), ('토',)),
    ('#F11','1958-05-10 22:30', 'M', '청주', ('신약',), ('화',)),
    ('#F12','1959-10-31 09:20', 'F', '전주', ('신약',), ('목',)),
    ('#F14','1961-02-14 20:10', 'F', '안산', ('신약',), ('토',)),
    ('#F15','1962-03-21 04:45', 'M', '김해', ('태약',), ('화',)),
    ('#F17','1964-05-05 16:25', 'M', '제주', ('중화신약',), ('목',)),
    ('#F18','1965-11-30 12:00', 'F', '진주', ('중화신강',), ('수',)),
]

settings = [
    ('기본', False, False),
    ('Hap', True, False),
    ('Johoo', False, True),
    ('Adj', True, True),
]

total = 0
dir_match = 0
exact_match = 0
yong_match = 0

print(f"{'Case':<6} {'Set':<6} {'FT신강약':<10} {'내엔진':<14} {'방향':>4} {'FT용':<4} {'내용':<4} {'용O':>3}")
print('=' * 65)

for cid, birth, gender, loc, ft_strengths, ft_yongs in test_cases:
    for i, (sname, use_hap, use_johoo) in enumerate(settings):
        r = engine.analyze(birth, gender, location=loc, use_yajas_i=True,
                          use_hap_correction=use_hap, use_johoo_correction=use_johoo)
        my_s = r['status'].split('(')[0]
        ft_s = ft_strengths[i]
        ft_y = ft_yongs[i]
        my_y = r['yongsin_detail']['main_yongsin'][:1]
        
        ft_strong = ft_s in ['중화신강', '신강', '태강', '극왕']
        my_strong = my_s in ['중화신강', '신강', '태강', '극왕']
        
        d = 'O' if ft_strong == my_strong else 'X'
        e = 'O' if my_s == ft_s else 'X'
        y = 'O' if ft_y == my_y else 'X'
        
        total += 1
        if d == 'O': dir_match += 1
        if e == 'O': exact_match += 1
        if y == 'O': yong_match += 1
        
        print(f"{cid:<6} {sname:<6} {ft_s:<10} {my_s:<14} {d:>4} {ft_y:<4} {my_y:<4} {y:>3}")
    print('-' * 65)

# forceteller.md cases (기본 only)
for cid, birth, gender, loc, ft_strengths, ft_yongs in ft_cases:
    r = engine.analyze(birth, gender, location=loc, use_yajas_i=True)
    my_s = r['status'].split('(')[0]
    ft_s = ft_strengths[0]
    ft_y = ft_yongs[0]
    my_y = r['yongsin_detail']['main_yongsin'][:1]
    
    ft_strong = ft_s in ['중화신강', '신강', '태강', '극왕']
    my_strong = my_s in ['중화신강', '신강', '태강', '극왕']
    
    d = 'O' if ft_strong == my_strong else 'X'
    e = 'O' if my_s == ft_s else 'X'
    y = 'O' if ft_y == my_y else 'X'
    
    total += 1
    if d == 'O': dir_match += 1
    if e == 'O': exact_match += 1
    if y == 'O': yong_match += 1
    
    print(f"{cid:<6} {'기본':<6} {ft_s:<10} {my_s:<14} {d:>4} {ft_y:<4} {my_y:<4} {y:>3}")

print('=' * 65)
print(f"총 {total}건")
print(f"신강/신약 방향 일치: {dir_match}/{total} ({dir_match/total*100:.1f}%)")
print(f"신강/신약 정확 일치: {exact_match}/{total} ({exact_match/total*100:.1f}%)")
print(f"용신 일치: {yong_match}/{total} ({yong_match/total*100:.1f}%)")

# 설정별 분리 통계
print("\n--- 설정별 방향 일치율 ---")
for sname, _, _ in settings:
    s_total = 0
    s_dir = 0
    for cid, birth, gender, loc, ft_strengths, ft_yongs in test_cases:
        i = [s[0] for s in settings].index(sname)
        r = engine.analyze(birth, gender, location=loc, use_yajas_i=True,
                          use_hap_correction=settings[i][1], use_johoo_correction=settings[i][2])
        my_s = r['status'].split('(')[0]
        ft_s = ft_strengths[i]
        ft_strong = ft_s in ['중화신강', '신강', '태강', '극왕']
        my_strong = my_s in ['중화신강', '신강', '태강', '극왕']
        s_total += 1
        if ft_strong == my_strong: s_dir += 1
    print(f"  {sname}: {s_dir}/{s_total} ({s_dir/s_total*100:.0f}%)")
